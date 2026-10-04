"""Executor do pathping.exe (Windows) para o diagnóstico de pathping.

Este módulo é responsável por executar o comando pathping.exe e devolver o
resultado bruto do processo, além de coordenar a execução com o parser.

Ele não interpreta a saída, não identifica saltos, não converte RTTs nem as
colunas de perda e não cria modelos estruturados: essas tarefas pertencem,
respectivamente, às camadas de parsing e de análise. A função de orquestração
apenas conecta o executor ao parser, sem interpretar o significado dos saltos.

Fluxo de execução bruta:

    pathping.exe → run_pathping() → CompletedProcess[str]

Fluxo de orquestração:

    run_pathping() → stdout bruto → parse_pathping_output() → PathpingResult

O retorno de ``run_pathping`` é o próprio ``subprocess.CompletedProcess``
devolvido por ``subprocess.run``; o ``stdout`` não é analisado nem
transformado.

Observação sobre o tempo de execução: o pathping.exe costuma demorar bastante
para concluir, porque realiza múltiplas sondagens ao longo de vários segundos
(por exemplo, o cabeçalho costuma anunciar "Calculando estatísticas para N
segundos..."). Esta camada **não** impõe um timeout artificial adicional; ela
apenas documenta essa característica, para que o chamador esteja ciente de que
a operação pode levar bastante tempo.
"""

import subprocess

from network_diagnostic.models.results import PathpingResult
from network_diagnostic.parsers.pathping import parse_pathping_output


class PathpingExecutionError(Exception):
    """Erro levantado quando o comando pathping não pôde ser executado."""


def run_pathping(
    target: str,
    max_hops: int = 30,
    timeout_ms: int = 4000,
) -> subprocess.CompletedProcess[str]:
    """Executa o pathping.exe do Windows e devolve o resultado bruto.

    Monta o comando ``pathping -h <max_hops> -w <timeout_ms> <target>`` e o
    executa. Não interpreta a saída: apenas devolve o ``CompletedProcess``
    (stdout, stderr, returncode) sem transformar o ``stdout``.

    Parâmetros:

    - ``target``: destino informado ao diagnóstico (hostname ou IP).
    - ``max_hops``: número máximo de saltos (flag ``-h``).
    - ``timeout_ms``: tempo limite por resposta em milissegundos (flag ``-w``).

    A opção ``-n`` (não resolver nomes) é intencionalmente **omitida**, para
    preservar a possibilidade de o Windows retornar hostname e IP dos saltos.
    Nesta versão as opções ``-q`` e ``-p`` não são expostas.

    Atenção: o pathping.exe pode levar bastante tempo para concluir, pois
    realiza várias sondagens. Esta função não aplica um timeout artificial
    adicional; a espera é a do próprio comando.

    Lança ``PathpingExecutionError`` se o comando não puder ser iniciado
    (por exemplo, quando o ``pathping`` não é encontrado no sistema).
    """
    command = ["pathping", "-h", str(max_hops), "-w", str(timeout_ms), target]

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
        raise PathpingExecutionError(
            "O comando 'pathping' não foi encontrado no sistema."
        ) from error


def collect_pathping_result(
    target: str,
    max_hops: int = 30,
    timeout_ms: int = 4000,
) -> PathpingResult:
    """Coleta a evidência estruturada de um pathping.

    Orquestra o executor e o parser: executa o pathping, envia o ``stdout``
    bruto ao parser e devolve o ``PathpingResult`` produzido por ele.

    Esta camada coordena executor e parser, mas não interpreta o significado
    dos saltos, não analisa perda, RTT ou qualidade da rota. A interpretação
    estrutural do ``stdout`` continua sendo responsabilidade do parser.

    ``returncode`` e ``stderr`` não são inspecionados nem transformados aqui:
    um ``returncode`` diferente de zero não é tratado como conclusão de rede,
    e o ``stderr`` não é armazenado no resultado.

    O ``target`` informado pelo chamador é repassado ao parser para preservar
    o contrato de ``PathpingResult.target`` (o alvo solicitado tem precedência
    sobre o destino resolvido do cabeçalho).

    Lança ``PathpingExecutionError`` se o comando não puder ser iniciado e
    ``PathpingParseError`` se o ``stdout`` não puder ser interpretado. As
    exceções são propagadas sem captura; se o executor falhar, o parser não é
    chamado.
    """
    completed = run_pathping(target, max_hops=max_hops, timeout_ms=timeout_ms)
    return parse_pathping_output(completed.stdout, target=target)