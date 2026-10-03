"""Testes de composição da camada de aplicação para traceroute.

Estes testes validam apenas a composição entre ``diagnostics`` e
``analysis`` feita por ``diagnose_and_analyze_traceroute``: se o diagnóstico
é chamado com os parâmetros corretos, se o ``TracerouteResult`` é repassado
exatamente à análise, se o ``TracerouteAnalysis`` é retornado e se as
exceções são propagadas.

Nenhum teste executa tracert real ou acessa a rede: tanto
``collect_traceroute_result`` quanto ``analyze_traceroute`` são substituídos
por mock via monkeypatch.
"""

import pytest

from network_diagnostic.application import traceroute as application_traceroute
from network_diagnostic.application.traceroute import diagnose_and_analyze_traceroute
from network_diagnostic.analysis.traceroute import TracerouteAnalysis
from network_diagnostic.models.results import HopResult, TracerouteResult


def _fake_traceroute_result(target: str = "8.8.8.8") -> TracerouteResult:
    """Cria um TracerouteResult fictício, sem executar nenhum comando real."""
    return TracerouteResult(
        target=target,
        max_hops=30,
        hops=[HopResult(1, [1.0, 1.0, 1.0], "192.168.1.1", None)],
    )


def test_application_calls_diagnostics_with_expected_params(monkeypatch) -> None:
    """Repassa target, max_hops e timeout_ms ao diagnóstico."""
    captured: dict[str, object] = {}

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        captured["target"] = target
        captured["max_hops"] = max_hops
        captured["timeout_ms"] = timeout_ms
        return _fake_traceroute_result(target)

    monkeypatch.setattr(application_traceroute, "collect_traceroute_result", fake_collect)
    monkeypatch.setattr(
        application_traceroute,
        "analyze_traceroute",
        lambda result: TracerouteAnalysis(result.target, ()),
    )

    diagnose_and_analyze_traceroute("8.8.8.8", max_hops=15, timeout_ms=2000)

    assert captured["target"] == "8.8.8.8"
    assert captured["max_hops"] == 15
    assert captured["timeout_ms"] == 2000


def test_application_forwards_defaults(monkeypatch) -> None:
    """Os defaults max_hops=30 e timeout_ms=4000 são encaminhados."""
    captured: dict[str, object] = {}

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        captured["max_hops"] = max_hops
        captured["timeout_ms"] = timeout_ms
        return _fake_traceroute_result(target)

    monkeypatch.setattr(application_traceroute, "collect_traceroute_result", fake_collect)
    monkeypatch.setattr(
        application_traceroute,
        "analyze_traceroute",
        lambda result: TracerouteAnalysis(result.target, ()),
    )

    diagnose_and_analyze_traceroute("8.8.8.8")

    assert captured["max_hops"] == 30
    assert captured["timeout_ms"] == 4000


def test_application_passes_result_exactly_to_analysis(monkeypatch) -> None:
    """O mesmo TracerouteResult do diagnóstico é enviado à análise."""
    expected = _fake_traceroute_result()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        application_traceroute,
        "collect_traceroute_result",
        lambda target, max_hops=30, timeout_ms=4000: expected,
    )

    def fake_analyze(result):
        captured["result"] = result
        return TracerouteAnalysis(result.target, ())

    monkeypatch.setattr(application_traceroute, "analyze_traceroute", fake_analyze)

    diagnose_and_analyze_traceroute("8.8.8.8")

    assert captured["result"] is expected


def test_application_returns_analysis_result_unchanged(monkeypatch) -> None:
    """O mesmo TracerouteAnalysis produzido pela análise é retornado."""
    expected = TracerouteAnalysis(target="8.8.8.8", findings=())

    monkeypatch.setattr(
        application_traceroute,
        "collect_traceroute_result",
        lambda target, max_hops=30, timeout_ms=4000: _fake_traceroute_result(target),
    )
    monkeypatch.setattr(application_traceroute, "analyze_traceroute", lambda result: expected)

    result = diagnose_and_analyze_traceroute("8.8.8.8")

    assert result is expected


def test_application_propagates_diagnostics_error(monkeypatch) -> None:
    """Exceção vinda do diagnóstico é propagada sem captura."""

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        raise RuntimeError("falha no diagnóstico")

    monkeypatch.setattr(application_traceroute, "collect_traceroute_result", fake_collect)
    monkeypatch.setattr(
        application_traceroute,
        "analyze_traceroute",
        lambda result: TracerouteAnalysis(result.target, ()),
    )

    with pytest.raises(RuntimeError):
        diagnose_and_analyze_traceroute("8.8.8.8")


def test_application_propagates_analysis_error(monkeypatch) -> None:
    """Exceção vinda da análise é propagada sem captura."""

    def fake_analyze(result):
        raise ValueError("falha na análise")

    monkeypatch.setattr(
        application_traceroute,
        "collect_traceroute_result",
        lambda target, max_hops=30, timeout_ms=4000: _fake_traceroute_result(target),
    )
    monkeypatch.setattr(application_traceroute, "analyze_traceroute", fake_analyze)

    with pytest.raises(ValueError):
        diagnose_and_analyze_traceroute("8.8.8.8")


def test_application_does_not_call_analysis_when_diagnostics_fails(monkeypatch) -> None:
    """A análise não é chamada quando o diagnóstico falha."""
    analysis_called: dict[str, bool] = {"called": False}

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        raise RuntimeError("falha no diagnóstico")

    def fake_analyze(result):
        analysis_called["called"] = True
        return TracerouteAnalysis(result.target, ())

    monkeypatch.setattr(application_traceroute, "collect_traceroute_result", fake_collect)
    monkeypatch.setattr(application_traceroute, "analyze_traceroute", fake_analyze)

    with pytest.raises(RuntimeError):
        diagnose_and_analyze_traceroute("8.8.8.8")

    assert analysis_called["called"] is False