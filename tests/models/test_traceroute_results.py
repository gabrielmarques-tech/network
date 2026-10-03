"""Testes para as classes HopResult e TracerouteResult.

Estes testes validam o comportamento real dos contêineres de dados:
armazenamento de campos, imutabilidade e igualdade por valor. Eles não testam
execução do tracert, parsing nem análise.
"""

from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.models.results import HopResult, TracerouteResult


def make_hop(**overrides: object) -> HopResult:
    """Cria um HopResult padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "hop_number": 1,
        "rtts_ms": [1.0, 1.0, 1.0],
        "address": "192.168.1.1",
        "hostname": None,
    }
    data.update(overrides)
    return HopResult(**data)  # type: ignore[arg-type]


def test_hop_stores_attributes_as_given() -> None:
    hop = HopResult(
        hop_number=10,
        rtts_ms=[3.0, 3.0, 3.0],
        address="8.8.8.8",
        hostname="dns.google",
    )

    assert hop.hop_number == 10
    assert hop.rtts_ms == [3.0, 3.0, 3.0]
    assert hop.address == "8.8.8.8"
    assert hop.hostname == "dns.google"


def test_hop_accepts_full_rtts() -> None:
    hop = make_hop(rtts_ms=[1.0, 2.0, 3.0])

    assert hop.rtts_ms == [1.0, 2.0, 3.0]


def test_hop_accepts_partial_rtts() -> None:
    # Neste caso existe uma posição correspondente sem resposta (None).
    hop = make_hop(rtts_ms=[3.0, None, 5.0])

    assert hop.rtts_ms == [3.0, None, 5.0]


def test_hop_accepts_empty_rtts() -> None:
    # Lista vazia representa o caso "* * *", sem resposta em nenhuma sondagem.
    hop = make_hop(rtts_ms=[])

    assert hop.rtts_ms == []


def test_hop_accepts_none_address() -> None:
    hop = make_hop(address=None)

    assert hop.address is None


def test_hop_accepts_none_hostname() -> None:
    hop = make_hop(hostname=None)

    assert hop.hostname is None


def test_hop_accepts_hostname_and_address_together() -> None:
    hop = make_hop(hostname="dns.google", address="8.8.8.8")

    assert hop.hostname == "dns.google"
    assert hop.address == "8.8.8.8"


def test_hop_is_immutable() -> None:
    hop = make_hop()

    with pytest.raises(FrozenInstanceError):
        hop.hop_number = 2  # type: ignore[misc]


def test_hop_equality_by_value() -> None:
    assert make_hop() == make_hop()
    assert make_hop() != make_hop(hop_number=2)


def test_hop_preserves_rtt_order() -> None:
    hop = make_hop(rtts_ms=[3.0, None, 1.0])

    assert hop.rtts_ms == [3.0, None, 1.0]


def make_traceroute(**overrides: object) -> TracerouteResult:
    """Cria um TracerouteResult padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "max_hops": 30,
        "hops": [
            HopResult(
                hop_number=1,
                rtts_ms=[1.0, 1.0, 1.0],
                address="192.168.1.1",
                hostname=None,
            ),
            HopResult(
                hop_number=2,
                rtts_ms=[],
                address=None,
                hostname=None,
            ),
        ],
    }
    data.update(overrides)
    return TracerouteResult(**data)  # type: ignore[arg-type]


def test_traceroute_stores_attributes_as_given() -> None:
    result = make_traceroute()

    assert result.target == "8.8.8.8"
    assert result.max_hops == 30
    assert len(result.hops) == 2


def test_traceroute_accepts_list_of_hops() -> None:
    result = make_traceroute()

    assert isinstance(result.hops, list)
    assert all(isinstance(hop, HopResult) for hop in result.hops)


def test_traceroute_preserves_hop_order() -> None:
    hops = [
        HopResult(hop_number=1, rtts_ms=[1.0], address="10.0.0.1", hostname=None),
        HopResult(hop_number=2, rtts_ms=[2.0], address="10.0.0.2", hostname=None),
        HopResult(hop_number=3, rtts_ms=[3.0], address="10.0.0.3", hostname=None),
    ]
    result = make_traceroute(hops=hops)

    assert [hop.hop_number for hop in result.hops] == [1, 2, 3]


def test_traceroute_accepts_empty_hops() -> None:
    result = make_traceroute(hops=[])

    assert result.hops == []


def test_traceroute_is_immutable() -> None:
    result = make_traceroute()

    with pytest.raises(FrozenInstanceError):
        result.target = "1.1.1.1"  # type: ignore[misc]


def test_traceroute_equality_by_value() -> None:
    assert make_traceroute() == make_traceroute()
    assert make_traceroute() != make_traceroute(max_hops=64)