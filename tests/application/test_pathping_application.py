"""Testes de composição da camada de aplicação para pathping.

Estes testes validam apenas a composição entre ``diagnostics`` e
``analysis`` feita por ``diagnose_and_analyze_pathping``: se o diagnóstico
é chamado com os parâmetros corretos, se o ``PathpingResult`` é repassado
exatamente à análise, se o ``PathpingAnalysis`` é retornado e se as
exceções são propagadas.

Nenhum teste executa pathping real ou acessa a rede: tanto
``collect_pathping_result`` quanto ``analyze_pathping`` são substituídos
por mock via monkeypatch.
"""

import pytest

from network_diagnostic.application import pathping as application_pathping
from network_diagnostic.application.pathping import diagnose_and_analyze_pathping
from network_diagnostic.analysis.pathping import PathpingAnalysis
from network_diagnostic.models.results import PathpingHop, PathpingResult


def _fake_pathping_result(target: str = "100.64.1.172") -> PathpingResult:
    """Cria um PathpingResult fictício, sem executar nenhum comando real."""
    return PathpingResult(
        target=target,
        hops=[PathpingHop(1, 0.0, 0.0, 0.0, "192.168.1.1")],
    )


def test_application_calls_diagnostics_with_expected_params(monkeypatch) -> None:
    """Repassa target, max_hops e timeout_ms ao diagnóstico."""
    captured: dict[str, object] = {}

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        captured["target"] = target
        captured["max_hops"] = max_hops
        captured["timeout_ms"] = timeout_ms
        return _fake_pathping_result(target)

    monkeypatch.setattr(
        application_pathping, "collect_pathping_result", fake_collect
    )
    monkeypatch.setattr(
        application_pathping,
        "analyze_pathping",
        lambda result: PathpingAnalysis(result.target, (), ()),
    )

    diagnose_and_analyze_pathping("100.64.1.172", max_hops=15, timeout_ms=2000)

    assert captured["target"] == "100.64.1.172"
    assert captured["max_hops"] == 15
    assert captured["timeout_ms"] == 2000


def test_application_forwards_defaults(monkeypatch) -> None:
    """Os defaults max_hops=30 e timeout_ms=4000 são encaminhados."""
    captured: dict[str, object] = {}

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        captured["max_hops"] = max_hops
        captured["timeout_ms"] = timeout_ms
        return _fake_pathping_result(target)

    monkeypatch.setattr(
        application_pathping, "collect_pathping_result", fake_collect
    )
    monkeypatch.setattr(
        application_pathping,
        "analyze_pathping",
        lambda result: PathpingAnalysis(result.target, (), ()),
    )

    diagnose_and_analyze_pathping("100.64.1.172")

    assert captured["max_hops"] == 30
    assert captured["timeout_ms"] == 4000


def test_application_passes_result_exactly_to_analysis(monkeypatch) -> None:
    """O mesmo PathpingResult do diagnóstico é enviado à análise."""
    expected = _fake_pathping_result()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        application_pathping,
        "collect_pathping_result",
        lambda target, max_hops=30, timeout_ms=4000: expected,
    )

    def fake_analyze(result):
        captured["result"] = result
        return PathpingAnalysis(result.target, (), ())

    monkeypatch.setattr(application_pathping, "analyze_pathping", fake_analyze)

    diagnose_and_analyze_pathping("100.64.1.172")

    assert captured["result"] is expected


def test_application_returns_analysis_result_unchanged(monkeypatch) -> None:
    """O mesmo PathpingAnalysis produzido pela análise é retornado."""
    expected = PathpingAnalysis(target="100.64.1.172", findings=(), hops=())

    monkeypatch.setattr(
        application_pathping,
        "collect_pathping_result",
        lambda target, max_hops=30, timeout_ms=4000: _fake_pathping_result(target),
    )
    monkeypatch.setattr(
        application_pathping, "analyze_pathping", lambda result: expected
    )

    result = diagnose_and_analyze_pathping("100.64.1.172")

    assert result is expected


def test_application_propagates_diagnostics_error(monkeypatch) -> None:
    """Exceção vinda do diagnóstico é propagada sem captura."""

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        raise RuntimeError("falha no diagnóstico")

    monkeypatch.setattr(
        application_pathping, "collect_pathping_result", fake_collect
    )
    monkeypatch.setattr(
        application_pathping,
        "analyze_pathping",
        lambda result: PathpingAnalysis(result.target, (), ()),
    )

    with pytest.raises(RuntimeError):
        diagnose_and_analyze_pathping("100.64.1.172")


def test_application_propagates_analysis_error(monkeypatch) -> None:
    """Exceção vinda da análise é propagada sem captura."""

    def fake_analyze(result):
        raise ValueError("falha na análise")

    monkeypatch.setattr(
        application_pathping,
        "collect_pathping_result",
        lambda target, max_hops=30, timeout_ms=4000: _fake_pathping_result(target),
    )
    monkeypatch.setattr(application_pathping, "analyze_pathping", fake_analyze)

    with pytest.raises(ValueError):
        diagnose_and_analyze_pathping("100.64.1.172")


def test_application_does_not_call_analysis_when_diagnostics_fails(monkeypatch) -> None:
    """A análise não é chamada quando o diagnóstico falha."""
    analysis_called: dict[str, bool] = {"called": False}

    def fake_collect(target, max_hops=30, timeout_ms=4000):
        raise RuntimeError("falha no diagnóstico")

    def fake_analyze(result):
        analysis_called["called"] = True
        return PathpingAnalysis(result.target, (), ())

    monkeypatch.setattr(
        application_pathping, "collect_pathping_result", fake_collect
    )
    monkeypatch.setattr(application_pathping, "analyze_pathping", fake_analyze)

    with pytest.raises(RuntimeError):
        diagnose_and_analyze_pathping("100.64.1.172")

    assert analysis_called["called"] is False