"""Testes para o parser da saída do ping.exe.

Estes testes validam a transformação da saída PT-BR do ping.exe do Windows em
um PingResult. Eles usam strings fixas que imitam a saída real do ping e não
executam o comando nem acessam a rede. Nenhuma interpretação de rede é feita
aqui: isso pertence à camada de análise.
"""

import pytest

from network_diagnostic.models.results import PingResult
from network_diagnostic.parsers.ping import (
    PingParseError,
    parse_ping_output,
)


# Saída real capturada do ping.exe do Windows (PT-BR) com sucesso total.
SUCCESS_OUTPUT = """Disparando 8.8.8.8 com 32 bytes de dados:
Resposta de 8.8.8.8: bytes=32 tempo=4ms TTL=116
Resposta de 8.8.8.8: bytes=32 tempo=3ms TTL=116
Resposta de 8.8.8.8: bytes=32 tempo=3ms TTL=116
Resposta de 8.8.8.8: bytes=32 tempo=2ms TTL=116
Estatísticas do Ping para 8.8.8.8:
Pacotes: Enviados = 4, Recebidos = 4, Perdidos = 0 (0% de
perda),
Aproximar um número redondo de vezes em milissegundos:
Mínimo = 2ms, Máximo = 4ms, Média = 3ms"""

# Saída real capturada do ping.exe do Windows (PT-BR) com perda total.
TOTAL_LOSS_OUTPUT = """Disparando 192.0.2.1 com 32 bytes de dados:
Esgotado o tempo limite do pedido.
Esgotado o tempo limite do pedido.
Esgotado o tempo limite do pedido.
Esgotado o tempo limite do pedido.
Estatísticas do Ping para 192.0.2.1:
Pacotes: Enviados = 4, Recebidos = 0, Perdidos = 4 (100% de
perda),"""


def test_parse_ping_output_success() -> None:
    """Interpreta a saída de sucesso e compara o PingResult por valor."""
    result = parse_ping_output(SUCCESS_OUTPUT, "8.8.8.8")

    expected = PingResult(
        target="8.8.8.8",
        packets_sent=4,
        packets_received=4,
        packet_loss_percent=0.0,
        min_latency_ms=2.0,
        avg_latency_ms=3.0,
        max_latency_ms=4.0,
        rtts_ms=[4.0, 3.0, 3.0, 2.0],
    )

    assert result == expected
    assert result.success is True


def test_parse_ping_output_extracts_rtts_in_order() -> None:
    """Garante que os RTTs individuais são extraídos na ordem correta."""
    result = parse_ping_output(SUCCESS_OUTPUT, "8.8.8.8")

    assert result.rtts_ms == [4.0, 3.0, 3.0, 2.0]


def test_parse_ping_output_total_loss() -> None:
    """Perda total é um resultado válido e não levanta exceção."""
    result = parse_ping_output(TOTAL_LOSS_OUTPUT, "192.0.2.1")

    assert result.target == "192.0.2.1"
    assert result.packets_sent == 4
    assert result.packets_received == 0
    assert result.packet_loss_percent == 100.0
    assert result.min_latency_ms is None
    assert result.avg_latency_ms is None
    assert result.max_latency_ms is None
    assert result.rtts_ms == []
    assert result.success is False


@pytest.mark.parametrize(
    "invalid_output",
    [
        "",  # string vazia
        "Esta é apenas uma linha qualquer sem formato de ping.",  # texto genérico
        "Pacotes: Enviados = 4, Perdidos = 0 (0% de perda),",  # sem "Recebidos ="
        (  # saída em inglês
            "Pinging 8.8.8.8 with 32 bytes of data:\n"
            "Reply from 8.8.8.8: bytes=32 time=4ms TTL=116\n"
            "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),"
        ),
    ],
)
def test_parse_ping_output_invalid_raises(invalid_output: str) -> None:
    """Saídas fora do formato PT-BR esperado levantam PingParseError."""
    with pytest.raises(PingParseError):
        parse_ping_output(invalid_output, "8.8.8.8")