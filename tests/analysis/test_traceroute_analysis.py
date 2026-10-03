"""Testes para a análise de traceroute da V1.

Estes testes validam o comportamento observável da interpretação de um
``TracerouteResult`` já estruturado e do contêiner ``TracerouteAnalysis``.
Nenhum teste executa traceroute real ou acessa a rede: os modelos são
criados em memória a partir de fixtures simples.

As regras da V1 são exatamente duas condições por salto:
``traceroute.hop_no_response`` (``WARNING``) e
``traceroute.hop_partial_response`` (``INFO``). Saltos totalmente responsivos
e saltos sem sondagens não geram achado.
"""

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.traceroute import (
    TracerouteAnalysis,
    analyze_traceroute,
)
from network_diagnostic.models.results import HopResult, TracerouteResult


def make_hop(**overrides: object) -> HopResult:
    """Cria um HopResult válido (totalmente responsivo) para os testes."""
    data: dict[str, object] = {
        "hop_number": 1,
        "rtts_ms": [1.0, 2.0, 3.0],
        "address": "192.168.1.1",
        "hostname": None,
    }
    data.update(overrides)
    return HopResult(**data)  # type: ignore[arg-type]


def make_result(
    hops: list[HopResult] | None = None, **overrides: object
) -> TracerouteResult:
    """Cria um TracerouteResult válido para os testes."""
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "max_hops": 30,
        "hops": [make_hop()] if hops is None else hops,
    }
    data.update(overrides)
    return TracerouteResult(**data)  # type: ignore[arg-type]


def make_finding(**overrides: object) -> AnalysisFinding:
    """Cria um AnalysisFinding padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "code": "traceroute.hop_no_response",
        "severity": Severity.WARNING,
        "summary": "O salto não respondeu às sondagens.",
        "explanation": "Todas as medições estão sem resposta.",
        "limitation": "Isso não significa perda de pacotes.",
    }
    data.update(overrides)
    return AnalysisFinding(**data)  # type: ignore[arg-type]


def codes(analysis: TracerouteAnalysis) -> list[str]:
    """Retorna os códigos dos achados na ordem produzida."""
    return [finding.code for finding in analysis.findings]


def test_all_numeric_hops_generate_no_findings():
    result = make_result(
        hops=[
            make_hop(hop_number=1, rtts_ms=[1.0, 1.0, 1.0]),
            make_hop(hop_number=2, rtts_ms=[5.0, 6.0, 7.0]),
        ]
    )

    analysis = analyze_traceroute(result)

    assert analysis.findings == ()
    assert codes(analysis) == []


def test_hop_all_none_generates_no_response_warning():
    result = make_result(hops=[make_hop(hop_number=3, rtts_ms=[None, None, None])])

    analysis = analyze_traceroute(result)

    assert codes(analysis) == ["traceroute.hop_no_response"]
    assert analysis.findings[0].severity is Severity.WARNING


def test_hop_partial_generates_partial_response_info():
    result = make_result(hops=[make_hop(hop_number=4, rtts_ms=[10.0, None, 12.0])])

    analysis = analyze_traceroute(result)

    assert codes(analysis) == ["traceroute.hop_partial_response"]
    assert analysis.findings[0].severity is Severity.INFO


def test_multiple_hops_preserve_order():
    result = make_result(
        hops=[
            make_hop(hop_number=1, rtts_ms=[1.0, 1.0, 1.0]),     # sem achado
            make_hop(hop_number=2, rtts_ms=[None, None, None]),  # no_response
            make_hop(hop_number=3, rtts_ms=[10.0, None, 12.0]),  # partial
            make_hop(hop_number=4, rtts_ms=[8.0, 9.0, 10.0]),    # sem achado
            make_hop(hop_number=5, rtts_ms=[None, 2.0, None]),   # partial
        ]
    )

    analysis = analyze_traceroute(result)

    assert codes(analysis) == [
        "traceroute.hop_no_response",
        "traceroute.hop_partial_response",
        "traceroute.hop_partial_response",
    ]


def test_empty_rtts_generates_no_finding():
    result = make_result(hops=[make_hop(hop_number=1, rtts_ms=[])])

    analysis = analyze_traceroute(result)

    assert analysis.findings == ()


def test_empty_rtts_is_not_treated_as_no_response():
    result = make_result(hops=[make_hop(hop_number=1, rtts_ms=[])])

    analysis = analyze_traceroute(result)

    assert "traceroute.hop_no_response" not in codes(analysis)


def test_single_numeric_and_two_none_is_partial():
    result = make_result(hops=[make_hop(hop_number=2, rtts_ms=[3.0, None, None])])

    analysis = analyze_traceroute(result)

    assert codes(analysis) == ["traceroute.hop_partial_response"]


def test_target_is_preserved():
    result = make_result(target="dns.google")

    analysis = analyze_traceroute(result)

    assert analysis.target == "dns.google"


def test_does_not_mutate_result():
    result = make_result(
        hops=[
            make_hop(hop_number=1, rtts_ms=[1.0, 2.0, 3.0]),
            make_hop(hop_number=2, rtts_ms=[None, None, None]),
            make_hop(hop_number=3, rtts_ms=[10.0, None, 12.0]),
        ]
    )
    original = deepcopy(result)

    analyze_traceroute(result)

    assert result == original


def test_findings_is_a_tuple():
    analysis = analyze_traceroute(make_result())

    assert isinstance(analysis.findings, tuple)


def test_all_findings_have_limitation():
    result = make_result(
        hops=[
            make_hop(hop_number=1, rtts_ms=[None, None, None]),
            make_hop(hop_number=2, rtts_ms=[10.0, None, 12.0]),
        ]
    )

    analysis = analyze_traceroute(result)

    assert all(finding.limitation for finding in analysis.findings)


def test_order_is_deterministic():
    result = make_result(
        hops=[
            make_hop(hop_number=1, rtts_ms=[None, None, None]),
            make_hop(hop_number=2, rtts_ms=[10.0, None, 12.0]),
        ]
    )

    first = analyze_traceroute(result)
    second = analyze_traceroute(result)

    assert codes(first) == codes(second)


def test_no_response_messages_do_not_claim_packet_loss():
    result = make_result(hops=[make_hop(hop_number=1, rtts_ms=[None, None, None])])

    finding = analyze_traceroute(result).findings[0]

    assert "perda de pacotes" not in finding.summary.lower()
    assert "bloqueio" not in finding.summary.lower()
    # A limitation deve explicitar o que NÃO se pode concluir.
    assert "não significa perda de pacotes" in finding.limitation.lower()


def test_partial_messages_do_not_claim_packet_loss():
    result = make_result(hops=[make_hop(hop_number=1, rtts_ms=[10.0, None, 12.0])])

    finding = analyze_traceroute(result).findings[0]

    assert "perda de pacotes" not in finding.summary.lower()
    assert "perda de pacotes" not in finding.explanation.lower()


def test_traceroute_analysis_stores_attributes_as_given() -> None:
    """TracerouteAnalysis armazena target e findings como informados."""
    finding = make_finding()
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=(finding,))

    assert analysis.target == "8.8.8.8"
    assert analysis.findings == (finding,)


def test_traceroute_analysis_findings_accepts_tuple() -> None:
    """TracerouteAnalysis.findings aceita uma tupla de AnalysisFinding."""
    findings = (
        make_finding(),
        make_finding(code="traceroute.hop_partial_response"),
    )
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=findings)

    assert isinstance(analysis.findings, tuple)
    assert all(isinstance(item, AnalysisFinding) for item in analysis.findings)


def test_traceroute_analysis_findings_accepts_empty_tuple() -> None:
    """A tupla de achados pode ser vazia."""
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=())

    assert analysis.findings == ()


def test_traceroute_analysis_is_immutable() -> None:
    """A tentativa de alterar um campo levanta FrozenInstanceError."""
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=())

    with pytest.raises(FrozenInstanceError):
        analysis.target = "1.1.1.1"  # type: ignore[misc]


def test_traceroute_analysis_equality_by_value() -> None:
    """Duas análises com os mesmos campos são iguais por valor."""
    assert (
        TracerouteAnalysis(target="8.8.8.8", findings=())
        == TracerouteAnalysis(target="8.8.8.8", findings=())
    )
    assert (
        TracerouteAnalysis(target="8.8.8.8", findings=())
        != TracerouteAnalysis(target="1.1.1.1", findings=())
    )