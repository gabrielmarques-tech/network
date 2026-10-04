"""Testes para o executor do pathping (run_pathping).

Estes testes validam apenas a camada de execução: a montagem do comando, os
argumentos repassados ao subprocess.run e o retorno do resultado bruto. Nenhum
teste executa o pathping real ou acessa a rede; o subprocess.run é substituído
por mock via monkeypatch.
"""

import subprocess

import pytest

from network_diagnostic.diagnostics.pathping import (
    PathpingExecutionError,
    run_pathping,
)


# Saída bruta fictícia do pathping (não é parseada por esta camada).
RAW_OUTPUT = (
    "Rastreando a rota para 100.64.1.172 com no máximo 30 saltos\n"
    "\n"
    "Calculando estatísticas para 75 segundos...\n"
    "\n"
    "            Origem aqui      Este nó/Vínculo\n"
    "\n"
    "    1    0ms     0/ 100 =  0%     0/ 100 =  0%  192.168.1.1\n"
)


def test_run_pathping_calls_subprocess_with_expected_args(monkeypatch) -> None:
    """run_pathping monta o comando e repassa as opções corretas."""
    captured: dict[str, object] = {}

    # CompletedProcess fictício: não executa nenhum comando de rede real.
    fake_completed = subprocess.CompletedProcess(
        args=["pathping", "-h", "30", "-w", "4000", "100.64.1.172"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return fake_completed

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.pathping.subprocess.run", fake_run
    )

    run_pathping("100.64.1.172")

    assert captured["command"] == [
        "pathping",
        "-h",
        "30",
        "-w",
        "4000",
        "100.64.1.172",
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "shell": False,
    }


def test_run_pathping_uses_custom_parameters(monkeypatch) -> None:
    """max_hops e timeout_ms informados são usados no comando."""
    captured: dict[str, object] = {}

    fake_completed = subprocess.CompletedProcess(
        args=["pathping", "-h", "5", "-w", "1000", "100.64.1.172"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        return fake_completed

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.pathping.subprocess.run", fake_run
    )

    run_pathping("100.64.1.172", max_hops=5, timeout_ms=1000)

    assert captured["command"] == [
        "pathping",
        "-h",
        "5",
        "-w",
        "1000",
        "100.64.1.172",
    ]


def test_run_pathping_returns_completed_process_unchanged(monkeypatch) -> None:
    """O CompletedProcess devolvido por subprocess.run é retornado sem alteração."""
    fake_completed = subprocess.CompletedProcess(
        args=["pathping", "-h", "30", "-w", "4000", "100.64.1.172"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.pathping.subprocess.run",
        lambda command, **kwargs: fake_completed,
    )

    result = run_pathping("100.64.1.172")

    assert result is fake_completed


def test_run_pathping_preserves_stdout(monkeypatch) -> None:
    """O stdout é preservado exatamente, sem parsing ou transformação."""
    fake_completed = subprocess.CompletedProcess(
        args=["pathping", "-h", "30", "-w", "4000", "100.64.1.172"],
        returncode=0,
        stdout=RAW_OUTPUT,
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.pathping.subprocess.run",
        lambda command, **kwargs: fake_completed,
    )

    result = run_pathping("100.64.1.172")

    assert result.stdout == RAW_OUTPUT


def test_run_pathping_missing_binary_raises(monkeypatch) -> None:
    """FileNotFoundError ao executar o comando vira PathpingExecutionError."""

    def fake_run(command, **kwargs):
        raise FileNotFoundError("pathping não encontrado")

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.pathping.subprocess.run", fake_run
    )

    with pytest.raises(PathpingExecutionError):
        run_pathping("100.64.1.172")