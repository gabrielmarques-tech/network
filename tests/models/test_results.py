"""Testes para a classe PingResult.

Estes testes validam o comportamento real do contêiner de dados PingResult:
armazenamento de campos, a propriedade calculada success, a imutabilidade e a
igualdade por valor. Eles não testam execução de ping, parsing nem análise.
"""

from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.models.results import PingResult


def make_result(**overrides: object) -> PingResult:
    """Cria um PingResult de sucesso, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "packets_sent": 4,
        "packets_received": 4,
        "packet_loss_percent": 0.0,
        "min_latency_ms": 10.5,
        "avg_latency_ms": 12.0,
        "max_latency_ms": 14.2,
        "rtts_ms": [10.5, 11.3, 12.0, 14.2],
    }
    data.update(overrides)
    return PingResult(**data)  # type: ignore[arg-type]


def test_stores_attributes_as_given() -> None:
    result = make_result()

    assert result.target == "8.8.8.8"
    assert result.packets_sent == 4
    assert result.packets_received == 4
    assert result.packet_loss_percent == 0.0
    assert result.min_latency_ms == 10.5
    assert result.avg_latency_ms == 12.0
    assert result.max_latency_ms == 14.2
    assert result.rtts_ms == [10.5, 11.3, 12.0, 14.2]


def test_success_is_true_when_replies_received() -> None:
    result = make_result(packets_received=3)

    assert result.success is True


def test_success_is_false_when_no_replies_received() -> None:
    result = make_result(packets_received=0)

    assert result.success is False


def test_success_boundary() -> None:
    # A comparação é estrita (>), então 0 é falha e 1 é sucesso.
    assert make_result(packets_received=0).success is False
    assert make_result(packets_received=1).success is True


def test_accepts_none_latencies_on_total_failure() -> None:
    result = make_result(
        packets_received=0,
        packet_loss_percent=100.0,
        min_latency_ms=None,
        avg_latency_ms=None,
        max_latency_ms=None,
        rtts_ms=[],
    )

    assert result.min_latency_ms is None
    assert result.avg_latency_ms is None
    assert result.max_latency_ms is None
    assert result.rtts_ms == []


def test_is_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.target = "1.1.1.1"  # type: ignore[misc]


def test_equality_by_value() -> None:
    assert make_result() == make_result()
    assert make_result() != make_result(packets_received=3)