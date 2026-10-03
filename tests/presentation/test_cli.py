"""Testes da camada de apresentação de linha de comando (CLI).

Estes testes validam apenas a orquestração feita por ``cli.main``: se o
subcomando e o destino informado são repassados ao fluxo existente, se o
resultado é apresentado e se um erro de execução ou de parsing vira mensagem
e código de saída não nulo.

Nenhum teste executa ping ou traceroute real ou acessa a rede: as funções da
camada de aplicação e da camada de apresentação são substituídas por mock via
monkeypatch.
"""

import pytest

from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.analysis.traceroute import TracerouteAnalysis
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.diagnostics.traceroute import TracerouteExecutionError
from network_diagnostic.parsers.ping import PingParseError
from network_diagnostic.parsers.traceroute import TracerouteParseError
from network_diagnostic.presentation import cli


def _fake_ping_analysis(target: str = "8.8.8.8") -> PingAnalysis:
    """Cria um PingAnalysis fictício, sem executar diagnóstico nem análise."""
    return PingAnalysis(target=target, findings=())


def _fake_traceroute_analysis(target: str = "8.8.8.8") -> TracerouteAnalysis:
    """Cria um TracerouteAnalysis fictício, sem executar diagnóstico nem análise."""
    return TracerouteAnalysis(target=target, findings=())


# ---------------------------------------------------------------------------
# Subcomando ping
# ---------------------------------------------------------------------------


def test_ping_repassa_target_ao_fluxo(monkeypatch) -> None:
    """O destino informado é repassado à camada de aplicação."""
    captured: dict[str, object] = {}

    def fake_diagnose(target):
        captured["target"] = target
        return _fake_ping_analysis(target)

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)
    monkeypatch.setattr(cli, "format_ping_analysis", lambda analysis: "texto")

    exit_code = cli.main(["ping", "8.8.8.8"])

    assert captured["target"] == "8.8.8.8"
    assert exit_code == 0


def test_ping_exibe_resultado_formatado(monkeypatch, capsys) -> None:
    """O texto produzido pela apresentação é exibido no terminal."""
    analysis = _fake_ping_analysis("1.1.1.1")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", lambda target: analysis)

    def fake_format(received):
        captured["analysis"] = received
        return "RESULTADO FORMATADO"

    monkeypatch.setattr(cli, "format_ping_analysis", fake_format)

    cli.main(["ping", "1.1.1.1"])

    assert captured["analysis"] is analysis
    assert "RESULTADO FORMATADO" in capsys.readouterr().out


def test_ping_trata_erro_de_execucao(monkeypatch, capsys) -> None:
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

    exit_code = cli.main(["ping", "8.8.8.8"])

    assert exit_code == 1
    assert analysis_was_formatted["called"] is False
    assert message in capsys.readouterr().out


def test_ping_trata_erro_de_parsing(monkeypatch, capsys) -> None:
    """PingParseError vira mensagem e código de saída 1, sem formatar."""
    message = "Não foi possível interpretar a saída do ping para '8.8.8.8'."
    analysis_was_formatted: dict[str, bool] = {"called": False}

    def fake_diagnose(target):
        raise PingParseError(message)

    def fake_format(analysis):
        analysis_was_formatted["called"] = True
        return ""

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)
    monkeypatch.setattr(cli, "format_ping_analysis", fake_format)

    exit_code = cli.main(["ping", "8.8.8.8"])

    assert exit_code == 1
    assert analysis_was_formatted["called"] is False
    assert message in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Subcomando traceroute
# ---------------------------------------------------------------------------


def test_traceroute_repassa_target_ao_fluxo(monkeypatch) -> None:
    """O destino informado é repassado à camada de aplicação."""
    captured: dict[str, object] = {}

    def fake_diagnose(target):
        captured["target"] = target
        return _fake_traceroute_analysis(target)

    monkeypatch.setattr(cli, "diagnose_and_analyze_traceroute", fake_diagnose)
    monkeypatch.setattr(cli, "format_traceroute_analysis", lambda analysis: "texto")

    exit_code = cli.main(["traceroute", "8.8.8.8"])

    assert captured["target"] == "8.8.8.8"
    assert exit_code == 0


def test_traceroute_exibe_resultado_formatado(monkeypatch, capsys) -> None:
    """O texto produzido pela apresentação é exibido no terminal."""
    analysis = _fake_traceroute_analysis("dns.google")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli, "diagnose_and_analyze_traceroute", lambda target: analysis
    )

    def fake_format(received):
        captured["analysis"] = received
        return "ROTA FORMATADA"

    monkeypatch.setattr(cli, "format_traceroute_analysis", fake_format)

    cli.main(["traceroute", "dns.google"])

    assert captured["analysis"] is analysis
    assert "ROTA FORMATADA" in capsys.readouterr().out


def test_traceroute_trata_erro_de_execucao(monkeypatch, capsys) -> None:
    """TracerouteExecutionError vira mensagem e código de saída 1, sem formatar."""
    message = "O comando 'tracert' não foi encontrado no sistema."
    analysis_was_formatted: dict[str, bool] = {"called": False}

    def fake_diagnose(target):
        raise TracerouteExecutionError(message)

    def fake_format(analysis):
        analysis_was_formatted["called"] = True
        return ""

    monkeypatch.setattr(cli, "diagnose_and_analyze_traceroute", fake_diagnose)
    monkeypatch.setattr(cli, "format_traceroute_analysis", fake_format)

    exit_code = cli.main(["traceroute", "8.8.8.8"])

    assert exit_code == 1
    assert analysis_was_formatted["called"] is False
    assert message in capsys.readouterr().out


def test_traceroute_trata_erro_de_parsing(monkeypatch, capsys) -> None:
    """TracerouteParseError vira mensagem e código de saída 1, sem formatar."""
    message = "A saída não contém um cabeçalho ou hop reconhecível do tracert."
    analysis_was_formatted: dict[str, bool] = {"called": False}

    def fake_diagnose(target):
        raise TracerouteParseError(message)

    def fake_format(analysis):
        analysis_was_formatted["called"] = True
        return ""

    monkeypatch.setattr(cli, "diagnose_and_analyze_traceroute", fake_diagnose)
    monkeypatch.setattr(cli, "format_traceroute_analysis", fake_format)

    exit_code = cli.main(["traceroute", "8.8.8.8"])

    assert exit_code == 1
    assert analysis_was_formatted["called"] is False
    assert message in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Erros de uso da CLI
# ---------------------------------------------------------------------------


def test_ausencia_de_subcomando_encerra_com_erro() -> None:
    """A ausência de subcomando faz o argparse encerrar com código 2."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])

    assert excinfo.value.code == 2


def test_ausencia_de_target_encerra_com_erro() -> None:
    """A ausência do destino faz o argparse encerrar com código 2."""
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["ping"])

    assert excinfo.value.code == 2
