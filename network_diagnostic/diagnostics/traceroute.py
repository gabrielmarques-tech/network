"""Executor do tracert.exe (Windows) para o diagnóstico de traceroute.

Este módulo é responsável por executar o comando tracert.exe e devolver
o resultado bruto do processo, além de coordenar a execução com o parser.

Ele não interpreta a saída, não identifica hops, não converte RTTs e não
cria modelos estruturados: essas tarefas pertencem, respectivamente, às
camadas de parsing e de análise. A função de orquestração apenas conecta o
executor ao parser, sem interpretar o significado dos hops.

Fluxo de execução bruta:

    tracert.exe → run_traceroute() → CompletedProcess[str]

Fluxo de orquestração:

    run_traceroute() → stdout bruto → parse_traceroute_output() → TracerouteResult

O retorno de ``run_traceroute`` é o próprio ``subprocess.CompletedProcess``
devolvido por ``subprocess.run``; o ``stdout`` não é analisado nem
transformado.
"""

import subprocess

from network_diagnostic.models.results import TracerouteResult
from network_diagnostic.parsers.traceroute import parse_traceroute_output


class TracerouteExecutionError(Exception):
    """Erro levantado quando o comando tracert não pôde ser executado."""


def run_traceroute(
    target: str,
    max_hops: int = 30,
    timeout_ms: int = 4000,
) -> subprocess.CompletedProcess[str]:
    """Executa o tracert.exe do Windows e devolve o resultado bruto.

    Monta o comando ``tracert -h <max_hops> -w <timeout_ms> <target>`` e o
    executa. Não interpreta a saída: apenas devolve o ``CompletedProcess``
    (stdout, stderr, returncode) sem transformar o ``stdout``.

    Parâmetros:

    - ``target``: destino informado ao diagnóstico (hostname ou IP).
    - ``max_hops``: número máximo de saltos (flag ``-h``).
    - ``timeout_ms``: tempo limite por resposta em milissegundos (flag ``-w``).

    A opção ``-d`` (não resolver nomes) é intencionalmente **omitida**, para
    preservar a possibilidade de o Windows retornar hostname e IP dos hops.

    Lança ``TracerouteExecutionError`` se o comando não puder ser iniciado
    (por exemplo, quando o ``tracert`` não é encontrado no sistema).
    """
    command = ["tracert", "-h", str(max_hops), "-w", str(timeout_ms), target]

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
        )
    except FileNotFoundError as error:
        # O binário não foi encontrado: é uma falha de execução local, não
        # uma conclusão sobre a rede.
        raise TracerouteExecutionError(
            "O comando 'tracert' não foi encontrado no sistema."
        ) from error


def collect_traceroute_result(
    target: str,
    max_hops: int = 30,
    timeout_ms: int = 4000,
) -> TracerouteResult:
    """Coleta a evidência estruturada de um traceroute.

    Orquestra o executor e o parser: executa o tracert, envia o ``stdout``
    bruto ao parser e devolve o ``TracerouteResult`` produzido por ele.

    Esta camada coordena executor e parser, mas não interpreta o significado
    dos hops, não analisa perda, RTT ou qualidade da rota. A interpretação
    estrutural do ``stdout`` continua sendo responsabilidade do parser.

    ``returncode`` e ``stderr`` não são inspecionados nem transformados aqui:
    um ``returncode`` diferente de zero não é tratado como conclusão de rede,
    e o ``stderr`` não é armazenado no resultado.

    O ``target`` informado pelo chamador é repassado ao parser para preservar
    o contrato de ``TracerouteResult.target`` (o alvo solicitado tem
    precedência sobre o hostname resolvido do cabeçalho).

    Lança ``TracerouteExecutionError`` se o comando não puder ser iniciado e
    ``TracerouteParseError`` se o ``stdout`` não puder ser interpretado. As
    exceções são propagadas sem captura; se o executor falhar, o parser não é
    chamado.
    """
    completed = run_traceroute(target, max_hops=max_hops, timeout_ms=timeout_ms)
    return parse_traceroute_output(completed.stdout, target=target)
