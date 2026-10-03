"""Diagnóstico de ping para Windows.

Este módulo executa o comando ping.exe e coordena a produção de um
PingResult estruturado. Ele apenas coleta e organiza a evidência: não
interpreta os resultados e não faz conclusões de rede (essas pertencem à
camada de análise).

A transformação da saída bruta em dados estruturados é responsabilidade da
camada de parsing (``network_diagnostic.parsers.ping``).
"""

import subprocess

from network_diagnostic.models.results import PingResult
from network_diagnostic.parsers.ping import parse_ping_output


class PingExecutionError(Exception):
    """Erro levantado quando o comando de ping não pôde ser executado."""


def run_ping(target: str, count: int = 4) -> subprocess.CompletedProcess[str]:
    """Executa o ping.exe do Windows e devolve o resultado bruto.

    Não interpreta a saída: apenas executa o comando e devolve o
    CompletedProcess (stdout, stderr, returncode).
    """
    command = ["ping", "-n", str(count), target]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=False,
    )


def diagnose_ping(target: str, count: int = 4) -> PingResult:
    """Executa o ping de um alvo e devolve o resultado estruturado.

    Orquestra a execução e o parsing. Não faz conclusões de rede: apenas
    coleta a evidência e a estrutura em um PingResult.
    """
    try:
        completed = run_ping(target, count)
    except FileNotFoundError as error:
        raise PingExecutionError(
            "O comando 'ping' não foi encontrado no sistema."
        ) from error

    return parse_ping_output(completed.stdout, target)