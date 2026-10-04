"""Testes para a orquestração entre o executor e o parser do pathping.

Estes testes validam apenas a camada de orquestração
(``collect_pathping_result``): se o executor é chamado com os parâmetros
corretos, se o ``stdout`` bruto é repassado exatamente ao parser e se o
resultado do parser é retornado tal como produzido.

Nenhum teste executa o pathping real ou acessa a rede: tanto ``run_pathping``
quanto ``parse_pathping_output`` são substituídos por mock via monkeypatch.
"""

import subprocess

import pytest

from network_diagnostic.diagnostics import pathping as pathping_module
from network_diagnostic.diagnostics.pathping import (
    PathpingExecutionError,
    collect_pathping_result,
)
from network_diagnostic.models.results import PathpingHop, PathpingResult
from network_diagnostic.parsers.pathping import PathpingParseError


# Saída bruta fictícia do pathping (não é interpretada por esta camada).
RAW_OUTPUT = (
    "Rastreando a rota para 100.64.1.172 com no máximo 30 saltos\n"
    "\n"
    "Calculando estatísticas para 75 segundos...\n"
    "\n"
    "    1    0ms     0/ 100 =  0%     0/ 100 =  0%  192.168.1.1\n"
)


def _fake_completed(stdout: str = RAW_OUTPUT) -> subprocess.CompletedProcess[str]:
    """Cria um CompletedProcess fictício, sem executar comando real."""
    return subprocess.CompletedProcess(
        args=["pathping", "-h", "30", "-w", "4000", "100.64.1.172"],
        returncode=0,
        stdout=stdout,
        stderr="",
    )


def test_orchestration_calls_run_pathping_with_expected_params(monkeypatch) -> None:
    """collect_pathping_result repassa target, max_hops e timeout_ms."""
    captured: dict[str, object] = {}

    def fake_run_pathping(target, max_hops, timeout_ms):
        captured["target"] = target
        captured["max_hops"] = max_hops
        captured["timeout_ms"] = timeout_ms
        return _fake_completed()

    monkeypatch.setattr(pathping_module, "run_pathping", fake_run_pathping)
    # O parser é substituído para isolar a verificação dos parâmetros.
    monkeypatch.setattr(
        pathping_module,
        "parse_pathping_output",
        lambda output, target=None: PathpingResult(target, []),
    )

    collect_pathping_result("100.64.1.172", max_hops=15, timeout_ms=2000)

    assert captured["target"] == "100.64.1.172"
    assert captured["max_hops"] == 15
    assert captured["timeout_ms"] == 2000


def test_orchestration_passes_exact_stdout_to_parser(monkeypatch) -> None:
    """O stdout exato devolvido pelo executor é enviado ao parser."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        pathping_module, "run_pathping", lambda target, **kwargs: _fake_completed()
    )

    def fake_parse(output, target=None):
        captured["output"] = output
        return PathpingResult(target, [])

    monkeypatch.setattr(pathping_module, "parse_pathping_output", fake_parse)

    collect_pathping_result("100.64.1.172")

    assert captured["output"] == RAW_OUTPUT


def test_orchestration_passes_target_to_parser(monkeypatch) -> None:
    """O target informado pelo chamador é repassado ao parser."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        pathping_module, "run_pathping", lambda target, **kwargs: _fake_completed()
    )

    def fake_parse(output, target=None):
        captured["target"] = target
        return PathpingResult(target, [])

    monkeypatch.setattr(pathping_module, "parse_pathping_output", fake_parse)

    collect_pathping_result("100.64.1.172")

    assert captured["target"] == "100.64.1.172"


def test_orchestration_returns_parser_result_unchanged(monkeypatch) -> None:
    """O mesmo PathpingResult produzido pelo parser é retornado."""
    expected = PathpingResult(
        target="100.64.1.172",
        hops=[PathpingHop(1, 0.0, 0.0, 0.0, "192.168.1.1")],
    )

    monkeypatch.setattr(
        pathping_module, "run_pathping", lambda target, **kwargs: _fake_completed()
    )
    monkeypatch.setattr(
        pathping_module,
        "parse_pathping_output",
        lambda output, target=None: expected,
    )

    result = collect_pathping_result("100.64.1.172")

    assert result is expected


def test_orchestration_propagates_execution_error(monkeypatch) -> None:
    """PathpingExecutionError do executor é propagado sem captura."""

    def fake_run_pathping(target, **kwargs):
        raise PathpingExecutionError("pathping não encontrado")

    monkeypatch.setattr(pathping_module, "run_pathping", fake_run_pathping)

    with pytest.raises(PathpingExecutionError):
        collect_pathping_result("100.64.1.172")


def test_orchestration_does_not_call_parser_when_executor_fails(monkeypatch) -> None:
    """O parser não é chamado quando o executor falha."""
    parser_called: dict[str, bool] = {"called": False}

    def fake_run_pathping(target, **kwargs):
        raise PathpingExecutionError("falha de execução")

    def fake_parse(output, target=None):
        parser_called["called"] = True
        return PathpingResult(target, [])

    monkeypatch.setattr(pathping_module, "run_pathping", fake_run_pathping)
    monkeypatch.setattr(pathping_module, "parse_pathping_output", fake_parse)

    with pytest.raises(PathpingExecutionError):
        collect_pathping_result("100.64.1.172")

    assert parser_called["called"] is False


def test_orchestration_propagates_parse_error(monkeypatch) -> None:
    """PathpingParseError do parser é propagado sem captura."""
    monkeypatch.setattr(
        pathping_module, "run_pathping", lambda target, **kwargs: _fake_completed()
    )

    def fake_parse(output, target=None):
        raise PathpingParseError("saída não reconhecida")

    monkeypatch.setattr(pathping_module, "parse_pathping_output", fake_parse)

    with pytest.raises(PathpingParseError):
        collect_pathping_result("100.64.1.172")