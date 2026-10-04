"""Testes para as classes PathpingHop e PathpingResult.

Estes testes validam o comportamento real dos contêineres de dados:
armazenamento de campos, imutabilidade e igualdade por valor. Eles não testam
execução do pathping, parsing nem análise.
"""

from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.models.results import PathpingHop, PathpingResult


def make_hop(**overrides: object) -> PathpingHop:
    """Cria um PathpingHop padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "hop_number": 1,
        "rtt_ms": 1.0,
        "source_loss_percent": 0.0,
        "link_loss_percent": 0.0,
        "address": "192.168.1.1",
    }
    data.update(overrides)
    return PathpingHop(**data)  # type: ignore[arg-type]


def test_hop_stores_attributes_as_given() -> None:
    hop = PathpingHop(
        hop_number=3,
        rtt_ms=3.0,
        source_loss_percent=0.0,
        link_loss_percent=25.0,
        address="100.64.1.172",
    )

    assert hop.hop_number == 3
    assert hop.rtt_ms == 3.0
    assert hop.source_loss_percent == 0.0
    assert hop.link_loss_percent == 25.0
    assert hop.address == "100.64.1.172"


def test_hop_keeps_two_loss_columns_separate() -> None:
    # As duas colunas de perda são medições distintas e não devem ser fundidas.
    hop = make_hop(source_loss_percent=10.0, link_loss_percent=50.0)

    assert hop.source_loss_percent == 10.0
    assert hop.link_loss_percent == 50.0


def test_hop_has_no_generic_loss_field() -> None:
    # Não deve existir um campo genérico único de perda.
    hop = make_hop()

    assert not hasattr(hop, "loss_percent")


def test_hop_accepts_none_rtt() -> None:
    hop = make_hop(rtt_ms=None)

    assert hop.rtt_ms is None


def test_hop_accepts_none_losses() -> None:
    hop = make_hop(source_loss_percent=None, link_loss_percent=None)

    assert hop.source_loss_percent is None
    assert hop.link_loss_percent is None


def test_hop_accepts_none_address() -> None:
    hop = make_hop(address=None)

    assert hop.address is None


def test_hop_is_immutable() -> None:
    hop = make_hop()

    with pytest.raises(FrozenInstanceError):
        hop.hop_number = 2  # type: ignore[misc]


def test_hop_equality_by_value() -> None:
    assert make_hop() == make_hop()
    assert make_hop() != make_hop(hop_number=2)


def make_result(**overrides: object) -> PathpingResult:
    """Cria um PathpingResult padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "target": "100.64.1.172",
        "hops": [
            PathpingHop(
                hop_number=1,
                rtt_ms=1.0,
                source_loss_percent=0.0,
                link_loss_percent=0.0,
                address="192.168.1.1",
            ),
            PathpingHop(
                hop_number=2,
                rtt_ms=None,
                source_loss_percent=None,
                link_loss_percent=None,
                address=None,
            ),
        ],
    }
    data.update(overrides)
    return PathpingResult(**data)  # type: ignore[arg-type]


def test_result_stores_attributes_as_given() -> None:
    result = make_result()

    assert result.target == "100.64.1.172"
    assert len(result.hops) == 2


def test_result_accepts_list_of_hops() -> None:
    result = make_result()

    assert isinstance(result.hops, list)
    assert all(isinstance(hop, PathpingHop) for hop in result.hops)


def test_result_preserves_hop_order() -> None:
    hops = [
        PathpingHop(1, 1.0, 0.0, 0.0, "10.0.0.1"),
        PathpingHop(2, 2.0, 0.0, 0.0, "10.0.0.2"),
        PathpingHop(3, 3.0, 0.0, 0.0, "10.0.0.3"),
    ]
    result = make_result(hops=hops)

    assert [hop.hop_number for hop in result.hops] == [1, 2, 3]


def test_result_accepts_empty_hops() -> None:
    result = make_result(hops=[])

    assert result.hops == []


def test_result_is_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.target = "1.1.1.1"  # type: ignore[misc]


def test_result_equality_by_value() -> None:
    assert make_result() == make_result()
    assert make_result() != make_result(target="8.8.8.8")