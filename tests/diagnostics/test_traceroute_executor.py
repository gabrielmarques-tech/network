"""Testes para o executor do tracert (run_traceroute).

Estes testes validam apenas a camada de execução: a montagem do comando, os
argumentos repassados ao subprocess.run e o retorno do resultado bruto. Nenhum
teste executa o tracert real ou acessa a rede; o subprocess.run é substituído
por mock via monkeypatch.
"""

import subprocess

import pytest

from network_diagnostic.diagnostics.traceroute import (
    TracerouteExecutionError,
    run_traceroute,
)


# Saída bruta fictícia do tracert (não é parseada por esta camada).
RAW_OUTPUT = (
    "Rastreando a rota para 8.8.8.8 com no máximo 30 saltos:\n"
    "  1     1 ms     1 ms     1 ms  192.168.1.1\n"
    "  2     *        *        *     Esgotado o tempo limite do pedido.\n"
)


def test_run_traceroute_calls_subprocess_with_expected_args(monkeypatch) -> None:
    """run_traceroute monta o comando e repassa as opções corretas."""
    captured: dict[str, object] = {}

    # CompletedProcess fictício: não executa nenhum comando de rede real.
    fake_completed = subprocess.CompletedProcess(
        args=["tracert", "-h", "30", "-w", "4000", "8.8.8.8"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return fake_completed

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.traceroute.subprocess.run", fake_run
    )

    run_traceroute("8.8.8.8")

    assert captured["command"] == [
        "tracert",
        "-h",
        "30",
        "-w",
        "4000",
        "8.8.8.8",
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "shell": False,
    }


def test_run_traceroute_returns_completed_process_unchanged(monkeypatch) -> None:
    """O CompletedProcess devolvido por subprocess.run é retornado sem alteração."""
    fake_completed = subprocess.CompletedProcess(
        args=["tracert", "-h", "30", "-w", "4000", "8.8.8.8"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.traceroute.subprocess.run",
        lambda command, **kwargs: fake_completed,
    )

    result = run_traceroute("8.8.8.8")

    assert result is fake_completed


def test_run_traceroute_preserves_stdout(monkeypatch) -> None:
    """O stdout é preservado exatamente, sem parsing ou transformação."""
    fake_completed = subprocess.CompletedProcess(
        args=["tracert", "-h", "30", "-w", "4000", "8.8.8.8"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.traceroute.subprocess.run",
        lambda command, **kwargs: fake_completed,
    )

    result = run_traceroute("8.8.8.8")

    assert result.stdout == RAW_OUTPUT


def test_run_traceroute_missing_binary_raises(monkeypatch) -> None:
    """FileNotFoundError ao executar o comando vira TracerouteExecutionError."""

    def fake_run(command, **kwargs):
        raise FileNotFoundError("tracert não encontrado")

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.traceroute.subprocess.run", fake_run
    )

    with pytest.raises(TracerouteExecutionError):
        run_traceroute("8.8.8.8")