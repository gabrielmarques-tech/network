"""Diagnóstico de ping para Windows.

Este módulo executa o comando ping.exe e converte a sua saída em um
PingResult estruturado. Ele apenas coleta e organiza a evidência: não
interpreta os resultados e não faz conclusões de rede (essas pertencem à
camada de análise).

Limitação conhecida: nesta primeira versão o parsing reconhece apenas a saída
em português (PT-BR) do ping.exe do Windows.
"""

import re
import subprocess

from network_diagnostic.models.results import PingResult


class PingExecutionError(Exception):
    """Erro levantado quando o comando de ping não pôde ser executado."""


class PingParseError(Exception):
    """Erro levantado quando a saída do ping não pode ser interpretada."""


# Padrões separados, cada um responsável por uma informação da saída PT-BR.
# Ex.: "Pacotes: Enviados = 4, Recebidos = 4, Perdidos = 0 (0% perdidos),"
packets_pattern = re.compile(
    r"Enviados\s*=\s*(?P<sent>\d+).*?"
    r"Recebidos\s*=\s*(?P<received>\d+).*?"
    r"Perdidos\s*=\s*\d+\s*\((?P<loss_percent>\d+)%",
    re.DOTALL,
)

# Ex.: "Mínimo = 10ms, Máximo = 20ms, Média = 15ms"
latency_pattern = re.compile(
    r"M[ií]nimo\s*=\s*(?P<min>\d+)ms.*?"
    r"M[aá]ximo\s*=\s*(?P<max>\d+)ms.*?"
    r"M[eé]dia\s*=\s*(?P<avg>\d+)ms",
    re.DOTALL,
)

# Ex.: "Resposta de 8.8.8.8: bytes=32 tempo=10ms TTL=118"
rtt_pattern = re.compile(r"tempo[=<]\s*(?P<rtt>\d+)ms")


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


def parse_ping_output(output: str, target: str) -> PingResult:
    """Converte a saída PT-BR do ping.exe em um PingResult.

    É uma função pura: recebe o texto da saída e devolve o modelo, sem
    executar comandos nem acessar a rede. Se os contadores essenciais não
    forem encontrados, levanta PingParseError.
    """
    packets_match = packets_pattern.search(output)
    if packets_match is None:
        raise PingParseError(
            f"Não foi possível interpretar a saída do ping para '{target}'."
        )

    packets_sent = int(packets_match.group("sent"))
    packets_received = int(packets_match.group("received"))
    packet_loss_percent = float(packets_match.group("loss_percent"))

    latency_match = latency_pattern.search(output)
    if latency_match is not None:
        min_latency_ms: float | None = float(latency_match.group("min"))
        avg_latency_ms: float | None = float(latency_match.group("avg"))
        max_latency_ms: float | None = float(latency_match.group("max"))
    else:
        # Sem estatísticas de latência (ex.: perda total).
        min_latency_ms = None
        avg_latency_ms = None
        max_latency_ms = None

    rtts_ms = [float(value) for value in rtt_pattern.findall(output)]

    return PingResult(
        target=target,
        packets_sent=packets_sent,
        packets_received=packets_received,
        packet_loss_percent=packet_loss_percent,
        min_latency_ms=min_latency_ms,
        avg_latency_ms=avg_latency_ms,
        max_latency_ms=max_latency_ms,
        rtts_ms=rtts_ms,
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