"""Testes da camada de apresentação de linha de comando (CLI).

Estes testes validam apenas a orquestração feita por ``cli.main``: se o
subcomando e o destino informado são repassados ao fluxo existente, se o
resultado é apresentado e se um erro de execução ou de parsing vira mensagem
e código de saída não nulo.

Nenhum teste executa ping ou traceroute real ou acessa a rede. A maioria dos
testes substitui por mock as funções da camada de aplicação e da camada de
apresentação via monkeypatch. Um único teste de integração executa as camadas
reais de ponta a ponta, mockando somente a fronteira de execução
(``subprocess.run``) do diagnóstico de ping.
"""

import subprocess

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

    def fake_diagnose(target, count=4):
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

    monkeypatch.setattr(
        cli, "diagnose_and_analyze_ping", lambda target, count=4: analysis
    )

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

    def fake_diagnose(target, count=4):
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

    def fake_diagnose(target, count=4):
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


def test_ping_usa_count_padrao_quando_omitido(monkeypatch) -> None:
    """Sem --count, o default 4 é repassado à camada de aplicação."""
    captured: dict[str, object] = {}

    def fake_diagnose(target, count=4):
        captured["count"] = count
        return _fake_ping_analysis(target)

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)
    monkeypatch.setattr(cli, "format_ping_analysis", lambda analysis: "texto")

    cli.main(["ping", "8.8.8.8"])

    assert captured["count"] == 4


def test_ping_repassa_count_informado(monkeypatch) -> None:
    """O --count informado é repassado exatamente à camada de aplicação."""
    captured: dict[str, object] = {}

    def fake_diagnose(target, count=4):
        captured["target"] = target
        captured["count"] = count
        return _fake_ping_analysis(target)

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)
    monkeypatch.setattr(cli, "format_ping_analysis", lambda analysis: "texto")

    exit_code = cli.main(["ping", "8.8.8.8", "--count", "10"])

    assert captured["target"] == "8.8.8.8"
    assert captured["count"] == 10
    assert exit_code == 0


@pytest.mark.parametrize("invalid_count", ["0", "-3", "abc", "2.5"])
def test_ping_rejeita_count_invalido(monkeypatch, invalid_count) -> None:
    """Um --count inválido faz o argparse encerrar com código 2 sem diagnóstico."""
    diagnose_called: dict[str, bool] = {"called": False}

    def fake_diagnose(target, count=4):
        diagnose_called["called"] = True
        return _fake_ping_analysis(target)

    monkeypatch.setattr(cli, "diagnose_and_analyze_ping", fake_diagnose)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["ping", "8.8.8.8", "--count", invalid_count])

    assert excinfo.value.code == 2
    assert diagnose_called["called"] is False


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


def test_comando_inesperado_retorna_2_sem_acionar_handler(monkeypatch) -> None:
    """Um ``command`` sem despacho explícito devolve 2 sem acionar handlers.

    Injeta um parser falso cujo ``parse_args`` devolve um subcomando que não
    existe no argparse real, para exercitar apenas o despacho de ``main`` —
    sem registrar um terceiro subcomando no argparse. Garante que o valor
    inesperado não seja encaminhado implicitamente a nenhum handler.
    """
    handlers_called: dict[str, bool] = {"ping": False, "traceroute": False}

    class _FakeArgs:
        command = "comando-inesperado"
        target = "8.8.8.8"

    class _FakeParser:
        def parse_args(self, argv):
            return _FakeArgs()

    def fake_handle_ping(target):
        handlers_called["ping"] = True
        return 0

    def fake_handle_traceroute(target):
        handlers_called["traceroute"] = True
        return 0

    monkeypatch.setattr(cli, "_build_parser", lambda: _FakeParser())
    monkeypatch.setattr(cli, "_handle_ping", fake_handle_ping)
    monkeypatch.setattr(cli, "_handle_traceroute", fake_handle_traceroute)

    exit_code = cli.main([])

    assert exit_code == 2
    assert handlers_called == {"ping": False, "traceroute": False}


# ---------------------------------------------------------------------------
# Teste de integração (fluxo real, subprocess mockado)
# ---------------------------------------------------------------------------


# Saída PT-BR do ping.exe com sucesso total, compatível com o parser atual.
_PING_SUCCESS_OUTPUT = """Disparando 8.8.8.8 com 32 bytes de dados:
Resposta de 8.8.8.8: bytes=32 tempo=4ms TTL=116
Resposta de 8.8.8.8: bytes=32 tempo=3ms TTL=116
Resposta de 8.8.8.8: bytes=32 tempo=3ms TTL=116
Resposta de 8.8.8.8: bytes=32 tempo=2ms TTL=116
Estatísticas do Ping para 8.8.8.8:
Pacotes: Enviados = 4, Recebidos = 4, Perdidos = 0 (0% de
perda),
Aproximar um número redondo de vezes em milissegundos:
Mínimo = 2ms, Máximo = 4ms, Média = 3ms"""


def test_ping_fluxo_completo_de_integracao(monkeypatch, capsys) -> None:
    """Exercita o fluxo real de ponta a ponta, mockando só o subprocess.

    Executa de verdade a CLI, a application, os diagnostics (incluindo a
    montagem do comando em ``run_ping``), o parser, o modelo, a análise e a
    apresentação. Apenas a fronteira de execução real do sistema operacional
    (``network_diagnostic.diagnostics.ping.subprocess.run``) é substituída,
    para impedir a execução do ping.exe. Verifica o código de saída, o alvo
    e os códigos de achado estáveis produzidos pela análise real.
    """
    fake_completed = subprocess.CompletedProcess(
        args=["ping", "-n", "4", "8.8.8.8"],
        returncode=0,
        stdout=_PING_SUCCESS_OUTPUT,
        stderr="",
    )

    monkeypatch.setattr(
        "network_diagnostic.diagnostics.ping.subprocess.run",
        lambda command, **kwargs: fake_completed,
    )

    exit_code = cli.main(["ping", "8.8.8.8"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Alvo: 8.8.8.8" in output
    assert "ping.no_loss" in output
    assert "ping.latency_observed" in output
