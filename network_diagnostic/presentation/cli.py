"""Ponto de entrada de linha de comando (V1).

Este módulo conecta a entrada do usuário às camadas já existentes do
projeto. Ele é uma camada fina de apresentação/orquestração: não executa
comandos, não faz parsing, não interpreta resultados e não contém regras de
diagnóstico de rede (por exemplo, não decide se há perda, se a latência está
alta ou se o problema está na rede local).

A CLI é organizada em subcomandos, um por diagnóstico disponível nesta V1:

    python -m network_diagnostic ping <target>
    python -m network_diagnostic traceroute <target>
    python -m network_diagnostic pathping <target>

Cada subcomando tem um argumento posicional obrigatório (``target``).
O subcomando ``ping`` expõe ainda o argumento opcional ``--count``, que
permite ao técnico ajustar a quantidade de pacotes ICMP; quando omitido,
assume o mesmo default da camada de aplicação (4), preservando o
comportamento anterior. Os demais parâmetros internos da camada de aplicação
(como ``max_hops`` e ``timeout_ms`` do traceroute e do pathping) permanecem
com seus valores padrão e não são expostos aqui.

Fluxo de cada subcomando:

    destino informado pelo usuário
        → diagnose_and_analyze_*()  (camada de aplicação)
        → format_*_analysis()       (camada de apresentação)
        → texto exibido no terminal

Toda a interpretação de rede permanece nas camadas de diagnóstico e análise.
"""

import argparse
from collections.abc import Sequence

from network_diagnostic.application.pathping import (
    diagnose_and_analyze_pathping,
)
from network_diagnostic.application.ping import diagnose_and_analyze_ping
from network_diagnostic.application.traceroute import (
    diagnose_and_analyze_traceroute,
)
from network_diagnostic.diagnostics.pathping import PathpingExecutionError
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.diagnostics.traceroute import TracerouteExecutionError
from network_diagnostic.parsers.pathping import PathpingParseError
from network_diagnostic.parsers.ping import PingParseError
from network_diagnostic.parsers.traceroute import TracerouteParseError
from network_diagnostic.presentation.text import (
    format_pathping_analysis,
    format_ping_analysis,
    format_traceroute_analysis,
)

_TARGET_HELP = "Destino do diagnóstico (por exemplo, um IP ou um nome de host)."

# Quantidade padrão de pacotes ICMP do subcomando ping. Mantém o mesmo
# default da camada de aplicação (diagnose_and_analyze_ping), de modo que o
# comportamento atual permanece inalterado quando o usuário omite --count.
_DEFAULT_PING_COUNT = 4


def _positive_int(value: str) -> int:
    """Converte ``value`` em inteiro, exigindo que seja positivo.

    Usado como ``type`` de um argumento do argparse: a validação acontece
    durante o parsing, antes de qualquer diagnóstico ser acionado. Assim, um
    valor inválido (não inteiro ou menor ou igual a zero) é rejeitado pelo
    argparse com código de saída 2, sem executar o ping.

    Levanta ``argparse.ArgumentTypeError`` quando o valor não é um inteiro
    positivo válido.
    """
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"valor inválido para inteiro: {value!r}"
        ) from None

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "o valor deve ser um inteiro positivo (maior que zero)"
        )

    return parsed


def _build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos da linha de comando.

    O parser principal exige um subcomando; cada subcomando recebe um único
    argumento posicional obrigatório ``target``.
    """
    parser = argparse.ArgumentParser(
        prog="network_diagnostic",
        description=(
            "Executa diagnósticos de rede e apresenta os achados da análise."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Diagnóstico a executar.",
    )

    ping_parser = subparsers.add_parser(
        "ping",
        help="Executa um diagnóstico de ping.",
        description=(
            "Executa um diagnóstico de ping e apresenta os achados da análise."
        ),
    )
    ping_parser.add_argument("target", help=_TARGET_HELP)
    ping_parser.add_argument(
        "--count",
        type=_positive_int,
        default=_DEFAULT_PING_COUNT,
        help=(
            "Quantidade de pacotes ICMP a enviar (inteiro positivo; "
            "padrão: %(default)s)."
        ),
    )

    traceroute_parser = subparsers.add_parser(
        "traceroute",
        help="Executa um diagnóstico de traceroute.",
        description=(
            "Executa um diagnóstico de traceroute e apresenta os achados "
            "da análise."
        ),
    )
    traceroute_parser.add_argument("target", help=_TARGET_HELP)

    pathping_parser = subparsers.add_parser(
        "pathping",
        help="Executa um diagnóstico de pathping.",
        description=(
            "Executa um diagnóstico de pathping e apresenta os achados "
            "da análise."
        ),
    )
    pathping_parser.add_argument("target", help=_TARGET_HELP)

    return parser


def _handle_ping(target: str, count: int) -> int:
    """Executa o subcomando ``ping`` e devolve o código de saída.

    Aciona a camada de aplicação (que compõe diagnóstico e análise) e
    apresenta o texto produzido pela camada de apresentação. Não interpreta
    a rede: apenas orquestra e exibe.

    ``count`` é repassado sem alteração a ``diagnose_and_analyze_ping``; a
    validação do valor é feita pelo ``argparse`` (via ``_positive_int``) antes
    de o diagnóstico ser acionado.

    Captura apenas as exceções do domínio de ping (execução e parsing). As
    demais exceções são propagadas, para não esconder falhas.
    """
    try:
        analysis = diagnose_and_analyze_ping(target, count=count)
    except (PingExecutionError, PingParseError) as error:
        print(f"Erro: {error}")
        return 1

    print(format_ping_analysis(analysis))
    return 0


def _handle_traceroute(target: str) -> int:
    """Executa o subcomando ``traceroute`` e devolve o código de saída.

    Aciona a camada de aplicação (que compõe diagnóstico e análise) e
    apresenta o texto produzido pela camada de apresentação. Não interpreta
    a rede: apenas orquestra e exibe.

    Captura apenas as exceções do domínio de traceroute (execução e
    parsing). As demais exceções são propagadas, para não esconder falhas.
    """
    try:
        analysis = diagnose_and_analyze_traceroute(target)
    except (TracerouteExecutionError, TracerouteParseError) as error:
        print(f"Erro: {error}")
        return 1

    print(format_traceroute_analysis(analysis))
    return 0


def _handle_pathping(target: str) -> int:
    """Executa o subcomando ``pathping`` e devolve o código de saída.

    Aciona a camada de aplicação (que compõe diagnóstico e análise) e
    apresenta o texto produzido pela camada de apresentação. Não interpreta
    a rede: apenas orquestra e exibe.

    Captura apenas as exceções do domínio de pathping (execução e parsing).
    As demais exceções são propagadas, para não esconder falhas. O
    ``returncode`` do processo não é inspecionado aqui.
    """
    try:
        analysis = diagnose_and_analyze_pathping(target)
    except (PathpingExecutionError, PathpingParseError) as error:
        print(f"Erro: {error}")
        return 1

    print(format_pathping_analysis(analysis))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Executa o fluxo da CLI e devolve o código de saída.

    Interpreta o subcomando escolhido e despacha para o handler
    correspondente. Esta função não interpreta a rede: apenas orquestra as
    camadas existentes e exibe o resultado.

    Devolve ``0`` em caso de sucesso e ``1`` quando o comando de diagnóstico
    não pôde ser executado ou quando a sua saída não pôde ser interpretada.
    Erros de argumentos são tratados pelo ``argparse`` (encerram com código
    de saída ``2``); um subcomando reconhecido sem despacho explícito também
    devolve ``2``, sem acionar nenhum handler.

    O parâmetro ``argv`` permite injetar argumentos nos testes; quando é
    ``None``, o ``argparse`` lê de ``sys.argv``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "ping":
        return _handle_ping(args.target, args.count)

    if args.command == "traceroute":
        return _handle_traceroute(args.target)

    if args.command == "pathping":
        return _handle_pathping(args.target)

    # Subcomando reconhecido pelo argparse, mas sem despacho explícito
    # associado. Não deve cair implicitamente em nenhum handler existente.
    return 2
