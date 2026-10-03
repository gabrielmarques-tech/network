"""Testes da camada de apresentação de linha de comando (CLI).

Estes testes validam apenas a orquestração feita por ``cli.main``: se o
destino informado é repassado ao fluxo existente, se o resultado é
apresentado e se um erro de execução vira mensagem e código de saída não
nulo.

Nenhum teste executa ping real ou acessa a rede: ``diagnose_and_analyze_ping``
e ``format_ping_analysis`` são substituídos por mock via monkeypatch.
"""

import pytest

from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.presentation import cli


def _fake_analysis(target: str = "8.8.8.8") -> PingAnalysis:
    """Cria um PingAnalysis fictício, sem executar diagnóstico nem análise."""
    return PingAnalysis(target=target, findings=())


def test_main_repassa_target_ao_fluxo(monkeypatch) -> None:
    """O destino informado é repassado à camada de aplicação."""
    captured: dict[str, object] = {}

    def fake_diagnose(target):
        captured["target"] = target
        return _fake_analysis(target)

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)
    monkeypatch.setattr(cli, "format_ping_analysis", lambda analysis: "texto")

    exit_code = cli.main(["8.8.8.8"])

    assert captured["target"] == "8.8.8.8"
    assert exit_code == 0


def test_main_exibe_resultado_formatado(monkeypatch, capsys) -> None:
    """O texto produzido pela apresentação é exibido no terminal."""
    analysis = _fake_analysis("1.1.1.1")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", lambda target: analysis)

    def fake_format(received):
        captured["analysis"] = received
        return "RESULTADO FORMATADO"

    monkeypatch.setattr(cli, "format_ping_analysis", fake_format)

    cli.main(["1.1.1.1"])

    assert captured["analysis"] is analysis
    assert "RESULTADO FORMATADO" in capsys.readouterr().out


def test_main_trata_erro_de_execucao(monkeypatch, capsys) -> None:
    """PingExecutionError vira mensagem e código de saída 1, sem formatar."""
    message = "O comando 'ping' não foi encontrado no sistema."
    analysis_was_formatted: dict[str, bool] = {"called": False}

    def fake_diagnose(target):
        raise PingExecutionError(message)

    def fake_format(analysis):
        analysis_was_formatted["called"] = True
        return ""

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)
    monkeypatch.setattr(cli, "format_ping_analysis", fake_format)

    exit_code = cli.main(["8.8.8.8"])

    assert exit_code == 1
    assert analysis_was_formatted["called"] is False
    assert message in capsys.readouterr().out


def test_main_argumento_ausente_encerra_com_erro() -> None:
    """A ausência do destino faz o argparse encerrar com código 2."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])

    assert excinfo.value.code == 2