"""Testes para a análise de ping da V1 (``analyze_ping`` e ``PingAnalysis``).

Estes testes validam o comportamento observável da interpretação de um
``PingResult`` já estruturado e do contêiner ``PingAnalysis`` que agrega os
achados e os dados objetivos. Nenhum teste executa ping real ou acessa a
rede: os ``PingResult`` são criados em memória a partir de fixtures simples.

As regras da V1 são exatamente quatro condições: ``ping.no_loss``,
``ping.partial_loss``, ``ping.total_loss`` e ``ping.latency_observed``.
"""

from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.ping import PingAnalysis, analyze_ping
from network_diagnostic.models.results import PingResult


def make_result(**overrides: object) -> PingResult:
    """Cria um PingResult válido para os testes."""
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "packets_sent": 10,
        "packets_received": 10,
        "packet_loss_percent": 0.0,
        "min_latency_ms": 10.0,
        "avg_latency_ms": 20.0,
        "max_latency_ms": 30.0,
        "rtts_ms": [10.0, 20.0, 30.0],
    }
    data.update(overrides)
    return PingResult(**data)  # type: ignore[arg-type]


def make_analysis(**overrides: object) -> PingAnalysis:
    """Cria um PingAnalysis válido para os testes.

    Preenche os campos objetivos com valores coerentes e permite sobrescrever
    qualquer um deles.
    """
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "packets_sent": 10,
        "packets_received": 10,
        "packet_loss_percent": 0.0,
        "min_latency_ms": 10.0,
        "avg_latency_ms": 20.0,
        "max_latency_ms": 30.0,
        "findings": (),
    }
    data.update(overrides)
    return PingAnalysis(**data)  # type: ignore[arg-type]


def make_total_loss_result(**overrides: object) -> PingResult:
    """Cria um PingResult representando perda total."""
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "packets_sent": 10,
        "packets_received": 0,
        "packet_loss_percent": 100.0,
        "min_latency_ms": None,
        "avg_latency_ms": None,
        "max_latency_ms": None,
        "rtts_ms": [],
    }
    data.update(overrides)
    return PingResult(**data)  # type: ignore[arg-type]


def make_finding(**overrides: object) -> AnalysisFinding:
    """Cria um AnalysisFinding padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "code": "ping.total_loss",
        "severity": Severity.CRITICAL,
        "summary": "Não houve resposta a nenhum pacote.",
        "explanation": "Nenhuma resposta foi recebida para os pacotes enviados.",
        "limitation": "ICMP pode ser filtrado; a ausência de resposta não prova que o alvo está indisponível.",
    }
    data.update(overrides)
    return AnalysisFinding(**data)  # type: ignore[arg-type]


def codes(analysis) -> list[str]:
    """Retorna os códigos dos achados na ordem produzida."""
    return [finding.code for finding in analysis.findings]


def test_no_loss_generates_no_loss_finding():
    result = make_result()

    analysis = analyze_ping(result)

    assert codes(analysis) == ["ping.no_loss", "ping.latency_observed"]
    assert analysis.findings[0].severity is Severity.INFO


def test_no_loss_also_generates_latency_finding_when_avg_exists():
    result = make_result(
        avg_latency_ms=18.5,
        min_latency_ms=10.0,
        max_latency_ms=25.0,
        rtts_ms=[10.0, 18.5, 25.0],
    )

    analysis = analyze_ping(result)

    latency = analysis.findings[1]

    assert latency.code == "ping.latency_observed"
    assert latency.severity is Severity.INFO
    assert "18.5" in latency.summary
    assert "10.0" in latency.explanation
    assert "25.0" in latency.explanation


def test_partial_loss_generates_partial_loss_finding():
    result = make_result(
        packets_received=7,
        packet_loss_percent=30.0,
    )

    analysis = analyze_ping(result)

    assert codes(analysis) == ["ping.partial_loss", "ping.latency_observed"]
    assert analysis.findings[0].severity is Severity.WARNING
    assert "30.0%" in analysis.findings[0].summary


def test_partial_loss_keeps_latency_finding_when_avg_exists():
    result = make_result(
        packets_received=8,
        packet_loss_percent=20.0,
        min_latency_ms=11.0,
        avg_latency_ms=22.0,
        max_latency_ms=40.0,
        rtts_ms=[11.0, 22.0, 40.0],
    )

    analysis = analyze_ping(result)

    assert codes(analysis) == ["ping.partial_loss", "ping.latency_observed"]


def test_partial_loss_boundary_just_above_zero():
    result = make_result(
        packets_received=9,
        packet_loss_percent=0.1,
    )

    analysis = analyze_ping(result)

    assert codes(analysis)[0] == "ping.partial_loss"
    assert analysis.findings[0].severity is Severity.WARNING


def test_partial_loss_boundary_just_below_hundred():
    result = make_result(
        packets_received=1,
        packet_loss_percent=99.9,
    )

    analysis = analyze_ping(result)

    assert codes(analysis)[0] == "ping.partial_loss"
    assert analysis.findings[0].severity is Severity.WARNING


def test_total_loss_generates_only_total_loss_finding():
    result = make_total_loss_result()

    analysis = analyze_ping(result)

    assert codes(analysis) == ["ping.total_loss"]
    assert analysis.findings[0].severity is Severity.CRITICAL


def test_total_loss_does_not_generate_latency_finding():
    result = make_total_loss_result()

    analysis = analyze_ping(result)

    assert all(
        finding.code != "ping.latency_observed"
        for finding in analysis.findings
    )


def test_latency_finding_reports_observed_values():
    result = make_result(
        min_latency_ms=5.0,
        avg_latency_ms=12.5,
        max_latency_ms=30.0,
        rtts_ms=[5.0, 12.5, 30.0],
    )

    analysis = analyze_ping(result)

    latency = analysis.findings[-1]

    assert latency.code == "ping.latency_observed"
    assert "12.5" in latency.summary
    assert "5.0" in latency.explanation
    assert "30.0" in latency.explanation
    assert "3 respostas" in latency.explanation


def test_no_latency_finding_when_avg_is_none():
    result = make_result(
        avg_latency_ms=None,
        min_latency_ms=None,
        max_latency_ms=None,
        rtts_ms=[],
    )

    analysis = analyze_ping(result)

    assert "ping.latency_observed" not in codes(analysis)


def test_severities_are_correct():
    no_loss = analyze_ping(make_result())
    partial_loss = analyze_ping(
        make_result(
            packets_received=5,
            packet_loss_percent=50.0,
        )
    )
    total_loss = analyze_ping(make_total_loss_result())

    assert no_loss.findings[0].severity is Severity.INFO
    assert partial_loss.findings[0].severity is Severity.WARNING
    assert total_loss.findings[0].severity is Severity.CRITICAL


def test_latency_severity_is_info():
    analysis = analyze_ping(make_result())

    latency = next(
        finding
        for finding in analysis.findings
        if finding.code == "ping.latency_observed"
    )

    assert latency.severity is Severity.INFO


def test_target_is_preserved():
    result = make_result(target="dns.google")

    analysis = analyze_ping(result)

    assert analysis.target == "dns.google"


def test_target_appears_in_messages():
    result = make_result(target="dns.google")

    analysis = analyze_ping(result)

    assert "dns.google" in analysis.findings[0].explanation


def test_messages_use_real_values_for_partial_loss():
    result = make_result(
        packets_sent=20,
        packets_received=15,
        packet_loss_percent=25.0,
    )

    analysis = analyze_ping(result)

    finding = analysis.findings[0]

    assert "25.0%" in finding.summary
    assert "15 de 20" in finding.explanation


def test_messages_use_real_values_for_total_loss():
    result = make_total_loss_result(
        target="1.1.1.1",
        packets_sent=4,
    )

    analysis = analyze_ping(result)

    finding = analysis.findings[0]

    assert "1.1.1.1" in finding.summary
    assert "4 pacotes enviados" in finding.explanation


def test_all_findings_have_limitation():
    analysis = analyze_ping(make_result())

    assert all(finding.limitation for finding in analysis.findings)


def test_no_high_latency_finding_exists():
    result = make_result(
        avg_latency_ms=500.0,
        min_latency_ms=400.0,
        max_latency_ms=600.0,
        rtts_ms=[400.0, 500.0, 600.0],
    )

    analysis = analyze_ping(result)

    assert "ping.high_latency" not in codes(analysis)
    assert "ping.latency_observed" in codes(analysis)


def test_empty_rtts_and_none_latency_do_not_raise():
    result = make_result(
        avg_latency_ms=None,
        min_latency_ms=None,
        max_latency_ms=None,
        rtts_ms=[],
    )

    analysis = analyze_ping(result)

    assert analysis.findings


def test_findings_order_is_deterministic():
    result = make_result()

    first = analyze_ping(result)
    second = analyze_ping(result)

    assert codes(first) == codes(second)


def test_findings_is_a_tuple():
    analysis = analyze_ping(make_result())

    assert isinstance(analysis.findings, tuple)


def test_does_not_mutate_result():
    result = make_result()

    original = PingResult(
        target=result.target,
        packets_sent=result.packets_sent,
        packets_received=result.packets_received,
        packet_loss_percent=result.packet_loss_percent,
        min_latency_ms=result.min_latency_ms,
        avg_latency_ms=result.avg_latency_ms,
        max_latency_ms=result.max_latency_ms,
        rtts_ms=list(result.rtts_ms),
    )

    analyze_ping(result)

    assert result == original


# ---------------------------------------------------------------------------
# Dados objetivos carregados adiante por analyze_ping
# ---------------------------------------------------------------------------


def test_analyze_ping_preserves_objective_fields() -> None:
    """analyze_ping copia os campos objetivos do PingResult para a análise."""
    result = make_result(
        target="dns.google",
        packets_sent=10,
        packets_received=8,
        packet_loss_percent=20.0,
        min_latency_ms=11.0,
        avg_latency_ms=22.0,
        max_latency_ms=40.0,
    )

    analysis = analyze_ping(result)

    assert analysis.target == "dns.google"
    assert analysis.packets_sent == 10
    assert analysis.packets_received == 8
    assert analysis.packet_loss_percent == 20.0
    assert analysis.min_latency_ms == 11.0
    assert analysis.avg_latency_ms == 22.0
    assert analysis.max_latency_ms == 40.0


def test_analyze_ping_preserves_none_latencies_on_total_loss() -> None:
    """Na perda total, as latências None são preservadas como None."""
    result = make_total_loss_result()

    analysis = analyze_ping(result)

    assert analysis.min_latency_ms is None
    assert analysis.avg_latency_ms is None
    assert analysis.max_latency_ms is None


# ---------------------------------------------------------------------------
# Contêiner PingAnalysis
# ---------------------------------------------------------------------------


def test_ping_analysis_stores_attributes_as_given() -> None:
    """PingAnalysis armazena os campos como informados."""
    finding = make_finding()
    analysis = PingAnalysis(
        target="8.8.8.8",
        packets_sent=4,
        packets_received=4,
        packet_loss_percent=0.0,
        min_latency_ms=10.0,
        avg_latency_ms=12.0,
        max_latency_ms=14.0,
        findings=(finding,),
    )

    assert analysis.target == "8.8.8.8"
    assert analysis.packets_sent == 4
    assert analysis.packets_received == 4
    assert analysis.packet_loss_percent == 0.0
    assert analysis.min_latency_ms == 10.0
    assert analysis.avg_latency_ms == 12.0
    assert analysis.max_latency_ms == 14.0
    assert analysis.findings == (finding,)


def test_ping_analysis_findings_accepts_tuple() -> None:
    """PingAnalysis.findings aceita uma tupla de AnalysisFinding."""
    findings = (make_finding(), make_finding(code="ping.high_latency"))
    analysis = make_analysis(findings=findings)

    assert isinstance(analysis.findings, tuple)
    assert all(isinstance(item, AnalysisFinding) for item in analysis.findings)


def test_ping_analysis_findings_accepts_empty_tuple() -> None:
    """A tupla de achados pode ser vazia."""
    analysis = make_analysis(findings=())

    assert analysis.findings == ()


def test_ping_analysis_is_immutable() -> None:
    """A tentativa de alterar um campo levanta FrozenInstanceError."""
    analysis = make_analysis()

    with pytest.raises(FrozenInstanceError):
        analysis.target = "1.1.1.1"  # type: ignore[misc]


def test_ping_analysis_equality_by_value() -> None:
    """Duas análises com os mesmos campos são iguais por valor."""
    assert make_analysis() == make_analysis()
    assert make_analysis() != make_analysis(target="1.1.1.1")
    assert make_analysis() != make_analysis(packet_loss_percent=50.0)
