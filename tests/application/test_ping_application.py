"""Testes de composição da camada de aplicação para ping.

Estes testes validam apenas a composição entre ``diagnostics`` e
``analysis`` feita por ``diagnose_and_analyze_ping``: se o diagnóstico é
chamado com os parâmetros corretos, se o ``PingResult`` é repassado
exatamente à análise, se o ``PingAnalysis`` é retornado e se as exceções são
propagadas.

Nenhum teste executa ping real ou acessa a rede: tanto ``diagnose_ping``
quanto ``analyze_ping`` são substituídos por mock via monkeypatch.
"""

import pytest

from network_diagnostic.application import ping as application_ping
from network_diagnostic.application.ping import diagnose_and_analyze_ping
from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.models.results import PingResult


def _fake_ping_result(target: str = "8.8.8.8") -> PingResult:
    """Cria um PingResult fictício, sem executar nenhum comando real."""
    return PingResult(
        target=target,
        packets_sent=4,
        packets_received=4,
        packet_loss_percent=0.0,
        min_latency_ms=2.0,
        avg_latency_ms=3.0,
        max_latency_ms=4.0,
        rtts_ms=[4.0, 3.0, 3.0, 2.0],
    )


def _empty_analysis(result: PingResult) -> PingAnalysis:
    """Cria um PingAnalysis vazio a partir de um resultado, sem análise real.

    Copia os campos objetivos do resultado apenas para manter a assinatura
    correta do contêiner; os achados ficam vazios.
    """
    return PingAnalysis(
        target=result.target,
        packets_sent=result.packets_sent,
        packets_received=result.packets_received,
        packet_loss_percent=result.packet_loss_percent,
        min_latency_ms=result.min_latency_ms,
        avg_latency_ms=result.avg_latency_ms,
        max_latency_ms=result.max_latency_ms,
        findings=(),
    )


def test_application_calls_diagnose_with_expected_params(monkeypatch) -> None:
    """diagnose_and_analyze_ping repassa target e count ao diagnóstico."""
    captured: dict[str, object] = {}

    def fake_diagnose(target, count=4):
        captured["target"] = target
        captured["count"] = count
        return _fake_ping_result(target)

    monkeypatch.setattr(application_ping, "diagnose_ping", fake_diagnose)
    monkeypatch.setattr(application_ping, "analyze_ping", lambda result: _empty_analysis(result))

    diagnose_and_analyze_ping("8.8.8.8", count=7)

    assert captured["target"] == "8.8.8.8"
    assert captured["count"] == 7


def test_application_forwards_default_count(monkeypatch) -> None:
    """O default count=4 é encaminhado ao diagnóstico."""
    captured: dict[str, object] = {}

    def fake_diagnose(target, count=4):
        captured["count"] = count
        return _fake_ping_result(target)

    monkeypatch.setattr(application_ping, "diagnose_ping", fake_diagnose)
    monkeypatch.setattr(application_ping, "analyze_ping", lambda result: _empty_analysis(result))

    diagnose_and_analyze_ping("8.8.8.8")

    assert captured["count"] == 4


def test_application_passes_result_exactly_to_analysis(monkeypatch) -> None:
    """O mesmo PingResult do diagnóstico é enviado à análise."""
    expected = _fake_ping_result()
    captured: dict[str, object] = {}

    monkeypatch.setattr(application_ping, "diagnose_ping", lambda target, count=4: expected)

    def fake_analyze(result):
        captured["result"] = result
        return _empty_analysis(result)

    monkeypatch.setattr(application_ping, "analyze_ping", fake_analyze)

    diagnose_and_analyze_ping("8.8.8.8")

    assert captured["result"] is expected


def test_application_returns_analysis_result_unchanged(monkeypatch) -> None:
    """O mesmo PingAnalysis produzido pela análise é retornado."""
    expected = _empty_analysis(_fake_ping_result())

    monkeypatch.setattr(application_ping, "diagnose_ping", lambda target, count=4: _fake_ping_result(target))
    monkeypatch.setattr(application_ping, "analyze_ping", lambda result: expected)

    result = diagnose_and_analyze_ping("8.8.8.8")

    assert result is expected


def test_application_propagates_diagnostics_error(monkeypatch) -> None:
    """Exceção vinda do diagnóstico é propagada sem captura."""

    def fake_diagnose(target, count=4):
        raise RuntimeError("falha no diagnóstico")

    monkeypatch.setattr(application_ping, "diagnose_ping", fake_diagnose)
    monkeypatch.setattr(application_ping, "analyze_ping", lambda result: _empty_analysis(result))

    with pytest.raises(RuntimeError):
        diagnose_and_analyze_ping("8.8.8.8")


def test_application_propagates_analysis_error(monkeypatch) -> None:
    """Exceção vinda da análise é propagada sem captura."""

    def fake_analyze(result):
        raise ValueError("falha na análise")

    monkeypatch.setattr(application_ping, "diagnose_ping", lambda target, count=4: _fake_ping_result(target))
    monkeypatch.setattr(application_ping, "analyze_ping", fake_analyze)

    with pytest.raises(ValueError):
        diagnose_and_analyze_ping("8.8.8.8")


def test_application_does_not_call_analysis_when_diagnostics_fails(monkeypatch) -> None:
    """A análise não é chamada quando o diagnóstico falha."""
    analysis_called: dict[str, bool] = {"called": False}

    def fake_diagnose(target, count=4):
        raise RuntimeError("falha no diagnóstico")

    def fake_analyze(result):
        analysis_called["called"] = True
        return _empty_analysis(result)

    monkeypatch.setattr(application_ping, "diagnose_ping", fake_diagnose)
    monkeypatch.setattr(application_ping, "analyze_ping", fake_analyze)

    with pytest.raises(RuntimeError):
        diagnose_and_analyze_ping("8.8.8.8")

    assert analysis_called["called"] is False