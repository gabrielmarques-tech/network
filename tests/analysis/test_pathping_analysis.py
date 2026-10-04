"""Testes para a análise de pathping da V1.

Estes testes validam o comportamento observável da interpretação de um
``PathpingResult`` já estruturado e do contêiner ``PathpingAnalysis``.
Nenhum teste executa pathping real ou acessa a rede: os modelos são criados
em memória a partir de fixtures simples.

As regras da V1 são exatamente duas condições por salto:
``pathping.hop_link_loss`` (``WARNING``, coluna do próprio nó/vínculo) e
``pathping.source_loss_observed`` (``INFO``, coluna "Origem aqui"). Saltos
sem perda observada não geram achado.
"""

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.pathping import (
    PathpingAnalysis,
    analyze_pathping,
)
from network_diagnostic.models.results import PathpingHop, PathpingResult


def make_hop(**overrides: object) -> PathpingHop:
    """Cria um PathpingHop válido (sem perda) para os testes."""
    data: dict[str, object] = {
        "hop_number": 1,
        "rtt_ms": 0.0,
        "source_loss_percent": 0.0,
        "link_loss_percent": 0.0,
        "address": "192.168.1.1",
    }
    data.update(overrides)
    return PathpingHop(**data)  # type: ignore[arg-type]


def make_result(
    hops: list[PathpingHop] | None = None, **overrides: object
) -> PathpingResult:
    """Cria um PathpingResult válido para os testes."""
    data: dict[str, object] = {
        "target": "100.64.1.172",
        "hops": [make_hop()] if hops is None else hops,
    }
    data.update(overrides)
    return PathpingResult(**data)  # type: ignore[arg-type]


def codes(analysis: PathpingAnalysis) -> list[str]:
    """Retorna os códigos dos achados na ordem produzida."""
    return [finding.code for finding in analysis.findings]


def test_no_loss_generates_no_findings():
    result = make_result(
        hops=[
            make_hop(hop_number=1, source_loss_percent=0.0, link_loss_percent=0.0),
            make_hop(hop_number=2, source_loss_percent=0.0, link_loss_percent=0.0),
        ]
    )

    analysis = analyze_pathping(result)

    assert analysis.findings == ()
    assert codes(analysis) == []


def test_link_loss_generates_link_finding_warning():
    result = make_result(
        hops=[make_hop(hop_number=3, source_loss_percent=0.0, link_loss_percent=5.0)]
    )

    analysis = analyze_pathping(result)

    assert codes(analysis) == ["pathping.hop_link_loss"]
    assert analysis.findings[0].severity is Severity.WARNING


def test_source_loss_generates_source_finding_info():
    result = make_result(
        hops=[make_hop(hop_number=2, source_loss_percent=10.0, link_loss_percent=0.0)]
    )

    analysis = analyze_pathping(result)

    assert codes(analysis) == ["pathping.source_loss_observed"]
    assert analysis.findings[0].severity is Severity.INFO


def test_both_losses_generate_both_findings():
    result = make_result(
        hops=[make_hop(hop_number=4, source_loss_percent=25.0, link_loss_percent=25.0)]
    )

    analysis = analyze_pathping(result)

    assert codes(analysis) == [
        "pathping.hop_link_loss",
        "pathping.source_loss_observed",
    ]


def test_distinction_between_local_and_accumulated_loss_is_preserved():
    """Perda de vínculo e perda acumulada produzem achados distintos."""
    result = make_result(
        hops=[make_hop(hop_number=2, source_loss_percent=50.0, link_loss_percent=1.0)]
    )

    analysis = analyze_pathping(result)

    assert "pathping.hop_link_loss" in codes(analysis)
    assert "pathping.source_loss_observed" in codes(analysis)
    # Os dois achados são independentes e não são fundidos em um único código.
    assert len(analysis.findings) == 2


def test_none_loss_does_not_generate_finding():
    result = make_result(
        hops=[
            make_hop(
                hop_number=1,
                source_loss_percent=None,
                link_loss_percent=None,
            )
        ]
    )

    analysis = analyze_pathping(result)

    assert analysis.findings == ()


def test_empty_hops_generates_empty_findings():
    result = make_result(hops=[])

    analysis = analyze_pathping(result)

    assert analysis.hops == ()
    assert analysis.findings == ()


def test_order_is_deterministic_and_follows_hop_order():
    result = make_result(
        hops=[
            make_hop(hop_number=1, source_loss_percent=0.0, link_loss_percent=0.0),
            make_hop(hop_number=2, source_loss_percent=0.0, link_loss_percent=5.0),
            make_hop(hop_number=3, source_loss_percent=10.0, link_loss_percent=0.0),
            make_hop(hop_number=4, source_loss_percent=20.0, link_loss_percent=20.0),
        ]
    )

    first = analyze_pathping(result)
    second = analyze_pathping(result)

    assert codes(first) == [
        "pathping.hop_link_loss",
        "pathping.source_loss_observed",
        "pathping.hop_link_loss",
        "pathping.source_loss_observed",
    ]
    assert codes(first) == codes(second)


def test_target_is_preserved():
    result = make_result(target="100.64.8.9")

    analysis = analyze_pathping(result)

    assert analysis.target == "100.64.8.9"


def test_hops_are_transported_in_original_order():
    hops = [
        make_hop(hop_number=1, address="192.168.1.1"),
        make_hop(hop_number=2, address="172.17.10.1"),
        make_hop(hop_number=3, address="100.64.1.172"),
    ]
    result = make_result(hops=hops)

    analysis = analyze_pathping(result)

    assert analysis.hops == tuple(hops)
    assert [hop.hop_number for hop in analysis.hops] == [1, 2, 3]


def test_does_not_mutate_result():
    result = make_result(
        hops=[
            make_hop(hop_number=1, source_loss_percent=0.0, link_loss_percent=0.0),
            make_hop(hop_number=2, source_loss_percent=10.0, link_loss_percent=5.0),
        ]
    )
    original = deepcopy(result)

    analyze_pathping(result)

    assert result == original


def test_findings_is_a_tuple():
    analysis = analyze_pathping(make_result())

    assert isinstance(analysis.findings, tuple)


def test_hops_is_a_tuple_of_pathping_hop():
    analysis = analyze_pathping(make_result())

    assert isinstance(analysis.hops, tuple)
    assert all(isinstance(hop, PathpingHop) for hop in analysis.hops)


def test_all_findings_have_limitation():
    result = make_result(
        hops=[
            make_hop(hop_number=1, source_loss_percent=10.0, link_loss_percent=5.0),
            make_hop(hop_number=2, source_loss_percent=20.0, link_loss_percent=20.0),
        ]
    )

    analysis = analyze_pathping(result)

    assert analysis.findings
    assert all(finding.limitation for finding in analysis.findings)


def test_link_messages_do_not_claim_confirmed_cause():
    result = make_result(
        hops=[make_hop(hop_number=3, link_loss_percent=5.0, source_loss_percent=0.0)]
    )

    finding = analyze_pathping(result).findings[0]

    # O resumo e a explicação não afirmam causa comprovada.
    assert "causa" not in finding.summary.lower()
    assert "causa" not in finding.explanation.lower()
    # A limitação deixa explícito que a perda de ICMP não prova a causa.
    assert "não prova" in finding.limitation.lower()


def test_source_messages_do_not_claim_application_traffic_loss():
    result = make_result(
        hops=[make_hop(hop_number=2, source_loss_percent=10.0, link_loss_percent=0.0)]
    )

    finding = analyze_pathping(result).findings[0]

    assert "tráfego de aplicação" not in finding.summary.lower()
    assert "tráfego de aplicação" not in finding.explanation.lower()


def test_messages_do_not_claim_destination_reached():
    result = make_result(
        hops=[
            make_hop(hop_number=1, source_loss_percent=10.0, link_loss_percent=5.0)
        ]
    )

    analysis = analyze_pathping(result)

    for finding in analysis.findings:
        assert "alcançado" not in finding.summary.lower()
        assert "alcançado" not in finding.explanation.lower()


def test_pathping_analysis_stores_attributes_as_given():
    hop = make_hop()
    analysis = PathpingAnalysis(target="100.64.1.172", findings=(), hops=(hop,))

    assert analysis.target == "100.64.1.172"
    assert analysis.findings == ()
    assert analysis.hops == (hop,)


def test_pathping_analysis_is_immutable():
    analysis = PathpingAnalysis(target="100.64.1.172", findings=(), hops=())

    with pytest.raises(FrozenInstanceError):
        analysis.target = "8.8.8.8"  # type: ignore[misc]


def test_pathping_analysis_equality_by_value():
    assert (
        PathpingAnalysis(target="100.64.1.172", findings=(), hops=())
        == PathpingAnalysis(target="100.64.1.172", findings=(), hops=())
    )
    assert (
        PathpingAnalysis(target="100.64.1.172", findings=(), hops=())
        != PathpingAnalysis(target="100.64.8.9", findings=(), hops=())
    )