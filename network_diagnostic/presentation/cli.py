"""Ponto de entrada de linha de comando (V1).

Este módulo conecta a entrada do usuário às camadas já existentes do
projeto. Ele é uma camada fina de apresentação/orquestração: não executa
comandos, não faz parsing, não interpreta resultados e não contém regras de
diagnóstico de rede (por exemplo, não decide se há perda, se a latência está
alta ou se o problema está na rede local).

A CLI é organizada em subcomandos, um por diagnóstico disponível nesta V1:

    python -m network_diagnostic ping <target>
    python -m network_diagnostic traceroute <target>

Cada subcomando tem apenas um argumento posicional obrigatório (``target``).
Parâmetros internos da camada de aplicação (como ``count``, ``max_hops`` e
``timeout_ms``) permanecem com seus valores padrão e não são expostos aqui.

Fluxo de cada subcomando:

    destino informado pelo usuário
        → diagnose_and_analyze_*()  (camada de aplicação)
        → format_*_analysis()       (camada de apresentação)
        → texto exibido no terminal

Toda a interpretação de rede permanece nas camadas de diagnóstico e análise.
"""

import argparse
from collections.abc import Sequence

from network_diagnostic.application.ping import diagnose_and_analyze_ping
from network_diagnostic.application.traceroute import (
    diagnose_and_analyze_traceroute,
)
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.diagnostics.traceroute import TracerouteExecutionError
from network_diagnostic.parsers.ping import PingParseError
from network_diagnostic.parsers.traceroute import TracerouteParseError
from network_diagnostic.presentation.text import (
    format_ping_analysis,
    format_traceroute_analysis,
)

_TARGET_HELP = "Destino do diagnóstico (por exemplo, um IP ou um nome de host)."


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

    traceroute_parser = subparsers.add_parser(
        "traceroute",
        help="Executa um diagnóstico de traceroute.",
        description=(
            "Executa um diagnóstico de traceroute e apresenta os achados "
            "da análise."
        ),
    )
    traceroute_parser.add_argument("target", help=_TARGET_HELP)

    return parser


def _handle_ping(target: str) -> int:
    """Executa o subcomando ``ping`` e devolve o código de saída.

    Aciona a camada de aplicação (que compõe diagnóstico e análise) e
    apresenta o texto produzido pela camada de apresentação. Não interpreta
    a rede: apenas orquestra e exibe.

    Captura apenas as exceções do domínio de ping (execução e parsing). As
    demais exceções são propagadas, para não esconder falhas.
    """
    try:
        analysis = diagnose_and_analyze_ping(target)
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


def main(argv: Sequence[str] | None = None) -> int:
    """Executa o fluxo da CLI e devolve o código de saída.

    Interpreta o subcomando escolhido e despacha para o handler
    correspondente. Esta função não interpreta a rede: apenas orquestra as
    camadas existentes e exibe o resultado.

    Devolve ``0`` em caso de sucesso e ``1`` quando o comando de diagnóstico
    não pôde ser executado ou quando a sua saída não pôde ser interpretada.
    Erros de argumentos são tratados pelo ``argparse`` (encerram com código
    de saída ``2``).

    O parâmetro ``argv`` permite injetar argumentos nos testes; quando é
    ``None``, o ``argparse`` lê de ``sys.argv``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "ping":
        return _handle_ping(args.target)

    # Único subcomando restante nesta V1.
    return _handle_traceroute(args.target)
