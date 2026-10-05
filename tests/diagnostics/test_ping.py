"""Testes para a execução e a orquestração do diagnóstico de ping.

Estes testes validam a execução do comando (com subprocess substituído por
mock) e a orquestração feita por diagnose_ping. Nenhum teste executa ping real
ou acessa a rede. O parsing da saída é testado em tests/parsers/test_ping.py.
"""

import subprocess
import sys

import pytest

from network_diagnostic.diagnostics.ping import (
    PingExecutionError,
    diagnose_ping,
    run_ping,
)
from network_diagnostic.models.results import PingResult
from network_diagnostic.parsers.ping import PingParseError


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
        "encoding": "oem",
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


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="O codec 'oem' e a codepage OEM só existem no Windows.",
)
def test_run_ping_decodes_stdout_using_oem_encoding(monkeypatch) -> None:
    """run_ping decodifica a saída com a codepage OEM do console.

    Protege o contrato de encoding: o ping.exe escreve na codepage OEM, não na
    codepage preferida do sistema. O teste substitui subprocess.run por um que
    repassa os mesmos kwargs a um subprocess de verdade que apenas escreve
    bytes na codepage OEM de um texto acentuado, sem acessar a rede nem
    executar ping.exe. Confirma que run_ping (com encoding="oem") decodifica
    corretamente esses bytes.
    """
    expected_text = "Página de código ativa"
    oem_bytes = expected_text.encode("oem")

    real_run = subprocess.run

    def fake_run(command, **kwargs):
        # Repassa os kwargs reais (incluindo encoding="oem") a um subprocess
        # que apenas emite os bytes OEM; nenhum comando de rede é executado.
        child = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(bytes.fromhex('%s'))"
            % oem_bytes.hex(),
        ]
        return real_run(child, **kwargs)

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.ping.subprocess.run", fake_run
    )

    result = run_ping("8.8.8.8")

    assert result.stdout == expected_text