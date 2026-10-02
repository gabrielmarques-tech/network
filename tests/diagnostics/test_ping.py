"""Testes para o diagnóstico de ping.

Estes testes validam o parsing da saída PT-BR do ping.exe do Windows, a
execução do comando (com subprocess substituído por mock) e a orquestração
feita por diagnose_ping. Nenhum teste executa ping real ou acessa a rede.
"""

import subprocess

import pytest

from network_diagnostic.diagnostics.ping import (
    PingExecutionError,
    PingParseError,
    diagnose_ping,
    parse_ping_output,
    run_ping,
)
from network_diagnostic.models.results import PingResult


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


def test_run_ping_calls_subprocess_with_expected_args(monkeypatch) -> None:
    """run_ping monta o comando e repassa as opções corretas ao subprocess."""
    captured: dict[str, object] = {}

    # CompletedProcess fictício: não executa nenhum comando de rede real.
    fake_completed = subprocess.CompletedProcess(
        args=["ping", "-n", "7", "8.8.8.8"],
        returncode=0,
        stdout=SUCCESS_OUTPUT,
        stderr="",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return fake_completed

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.ping.subprocess.run", fake_run
    )

    result = run_ping("8.8.8.8", count=7)

    assert captured["command"] == ["ping", "-n", "7", "8.8.8.8"]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "shell": False,
    }
    assert result is fake_completed


def test_diagnose_ping_runs_and_parses(monkeypatch) -> None:
    """diagnose_ping executa o run_ping e devolve o PingResult esperado."""
    fake_completed = subprocess.CompletedProcess(
        args=["ping", "-n", "4", "8.8.8.8"],
        returncode=0,
        stdout=SUCCESS_OUTPUT,
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.ping.run_ping",
        lambda target, count=4: fake_completed,
    )

    result = diagnose_ping("8.8.8.8")

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


def test_diagnose_ping_execution_error(monkeypatch) -> None:
    """Falha ao executar o ping vira PingExecutionError."""

    def fake_run_ping(target, count=4):
        raise FileNotFoundError("ping não encontrado")

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.ping.run_ping", fake_run_ping
    )

    with pytest.raises(PingExecutionError):
        diagnose_ping("8.8.8.8")


def test_diagnose_ping_parse_error(monkeypatch) -> None:
    """Saída inválida do ping vira PingParseError propagado por diagnose_ping."""
    fake_completed = subprocess.CompletedProcess(
        args=["ping", "-n", "4", "8.8.8.8"],
        returncode=0,
        stdout="saída inválida sem formato de ping",
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.ping.run_ping",
        lambda target, count=4: fake_completed,
    )

    with pytest.raises(PingParseError):
        diagnose_ping("8.8.8.8")