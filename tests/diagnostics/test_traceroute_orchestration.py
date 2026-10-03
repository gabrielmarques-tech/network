"""Testes para a orquestração entre o executor e o parser do tracert.

Estes testes validam apenas a camada de orquestração
(``collect_traceroute_result``): se o executor é chamado com os parâmetros
corretos, se o ``stdout`` bruto é repassado exatamente ao parser e se o
resultado do parser é retornado tal como produzido.

Nenhum teste executa o tracert real ou acessa a rede: tanto ``run_traceroute``
quanto ``parse_traceroute_output`` são substituídos por mock via monkeypatch.
"""

import subprocess

import pytest

from network_diagnostic.diagnostics import traceroute as traceroute_module
from network_diagnostic.diagnostics.traceroute import (
    TracerouteExecutionError,
    collect_traceroute_result,
)
from network_diagnostic.models.results import HopResult, TracerouteResult
from network_diagnostic.parsers.traceroute import TracerouteParseError


# Saída bruta fictícia do tracert (não é interpretada por esta camada).
RAW_OUTPUT = (
    "Rastreando a rota para 8.8.8.8 com no máximo 30 saltos:\n"
    "  1     1 ms     1 ms     1 ms  192.168.1.1\n"
    "  2     *        *        *     Esgotado o tempo limite do pedido.\n"
)


def _fake_completed(stdout: str = RAW_OUTPUT) -> subprocess.CompletedProcess[str]:
    """Cria um CompletedProcess fictício, sem executar comando real."""
    return subprocess.CompletedProcess(
        args=["tracert", "-h", "30", "-w", "4000", "8.8.8.8"],
        returncode=0,
        stdout=stdout,
        stderr="",
    )


def test_orchestration_calls_run_traceroute_with_expected_params(monkeypatch) -> None:
    """collect_traceroute_result repassa target, max_hops e timeout_ms."""
    captured: dict[str, object] = {}

    def fake_run_traceroute(target, max_hops, timeout_ms):
        captured["target"] = target
        captured["max_hops"] = max_hops
        captured["timeout_ms"] = timeout_ms
        return _fake_completed()

    monkeypatch.setattr(
        traceroute_module, "run_traceroute", fake_run_traceroute
    )
    # O parser é substituído para isolar a verificação dos parâmetros.
    monkeypatch.setattr(
        traceroute_module,
        "parse_traceroute_output",
        lambda output, target=None: TracerouteResult(target, 30, []),
    )

    collect_traceroute_result("8.8.8.8", max_hops=15, timeout_ms=2000)

    assert captured["target"] == "8.8.8.8"
    assert captured["max_hops"] == 15
    assert captured["timeout_ms"] == 2000


def test_orchestration_passes_exact_stdout_to_parser(monkeypatch) -> None:
    """O stdout exato devolvido pelo executor é enviado ao parser."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        traceroute_module, "run_traceroute", lambda target, **kwargs: _fake_completed()
    )

    def fake_parse(output, target=None):
        captured["output"] = output
        return TracerouteResult(target, 30, [])

    monkeypatch.setattr(traceroute_module, "parse_traceroute_output", fake_parse)

    collect_traceroute_result("8.8.8.8")

    assert captured["output"] == RAW_OUTPUT


def test_orchestration_passes_target_to_parser(monkeypatch) -> None:
    """O target informado pelo chamador é repassado ao parser."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        traceroute_module, "run_traceroute", lambda target, **kwargs: _fake_completed()
    )

    def fake_parse(output, target=None):
        captured["target"] = target
        return TracerouteResult(target, 30, [])

    monkeypatch.setattr(traceroute_module, "parse_traceroute_output", fake_parse)

    collect_traceroute_result("8.8.8.8")

    assert captured["target"] == "8.8.8.8"


def test_orchestration_returns_parser_result_unchanged(monkeypatch) -> None:
    """O mesmo TracerouteResult produzido pelo parser é retornado."""
    expected = TracerouteResult(
        target="8.8.8.8",
        max_hops=30,
        hops=[HopResult(1, [1.0, 1.0, 1.0], "192.168.1.1", None)],
    )

    monkeypatch.setattr(
        traceroute_module, "run_traceroute", lambda target, **kwargs: _fake_completed()
    )
    monkeypatch.setattr(
        traceroute_module,
        "parse_traceroute_output",
        lambda output, target=None: expected,
    )

    result = collect_traceroute_result("8.8.8.8")

    assert result is expected


def test_orchestration_propagates_execution_error(monkeypatch) -> None:
    """TracerouteExecutionError do executor é propagado sem captura."""

    def fake_run_traceroute(target, **kwargs):
        raise TracerouteExecutionError("tracert não encontrado")

    monkeypatch.setattr(
        traceroute_module, "run_traceroute", fake_run_traceroute
    )

    with pytest.raises(TracerouteExecutionError):
        collect_traceroute_result("8.8.8.8")


def test_orchestration_does_not_call_parser_when_executor_fails(monkeypatch) -> None:
    """O parser não é chamado quando o executor falha."""
    parser_called: dict[str, bool] = {"called": False}

    def fake_run_traceroute(target, **kwargs):
        raise TracerouteExecutionError("falha de execução")

    def fake_parse(output, target=None):
        parser_called["called"] = True
        return TracerouteResult(target, 30, [])

    monkeypatch.setattr(
        traceroute_module, "run_traceroute", fake_run_traceroute
    )
    monkeypatch.setattr(traceroute_module, "parse_traceroute_output", fake_parse)

    with pytest.raises(TracerouteExecutionError):
        collect_traceroute_result("8.8.8.8")

    assert parser_called["called"] is False


def test_orchestration_propagates_parse_error(monkeypatch) -> None:
    """TracerouteParseError do parser é propagado sem captura."""
    monkeypatch.setattr(
        traceroute_module, "run_traceroute", lambda target, **kwargs: _fake_completed()
    )

    def fake_parse(output, target=None):
        raise TracerouteParseError("saída não reconhecida")

    monkeypatch.setattr(traceroute_module, "parse_traceroute_output", fake_parse)

    with pytest.raises(TracerouteParseError):
        collect_traceroute_result("8.8.8.8")