"""Executor do tracert.exe (Windows) para o diagnóstico de traceroute.

Este módulo é responsável apenas por executar o comando tracert.exe e devolver
o resultado bruto do processo. Ele não interpreta a saída, não identifica hops,
não converte RTTs e não cria modelos estruturados: essas tarefas pertencem,
respectivamente, às camadas de parsing e de análise.

Fluxo:

    tracert.exe → run_traceroute() → CompletedProcess[str]

O retorno é o próprio ``subprocess.CompletedProcess`` devolvido por
``subprocess.run``; o ``stdout`` não é analisado nem transformado.
"""

import subprocess


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