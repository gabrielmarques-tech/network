"""Ponto de entrada de linha de comando (V1).

Este módulo conecta a entrada do usuário às camadas já existentes do
projeto. Ele é uma camada fina de apresentação/orquestração: não executa
comandos, não faz parsing, não interpreta resultados e não contém regras de
diagnóstico de rede (por exemplo, não decide se há perda, se a latência está
alta ou se o problema está na rede local).

Fluxo desta V1:

    destino informado pelo usuário
        → diagnose_and_analyze_ping()  (camada de aplicação)
        → format_ping_analysis()       (camada de apresentação)
        → texto exibido no terminal

Toda a interpretação de rede permanece nas camadas de diagnóstico e análise.
"""

import argparse
from collections.abc import Sequence

from network_diagnostic.application.ping import diagnose_and_analyze_ping
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.presentation.text import format_ping_analysis


def _build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        prog="network_diagnostic",
        description=(
            "Executa um diagnóstico de ping e apresenta os achados da análise."
        ),
    )
    parser.add_argument(
        "target",
        help="Destino do diagnóstico (por exemplo, um IP ou um nome de host).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Executa o fluxo mínimo da CLI e devolve o código de saída.

    Recebe o destino pela linha de comando, aciona a camada de aplicação
    (que compõe o diagnóstico e a análise) e apresenta o texto produzido
    pela camada de apresentação. Esta função não interpreta a rede: apenas
    orquestra as camadas existentes e exibe o resultado.

    Devolve ``0`` em caso de sucesso e ``1`` quando o comando de diagnóstico
    não pôde ser executado (``PingExecutionError``). Erros de argumentos são
    tratados pelo ``argparse`` (encerram com código de saída ``2``).

    O parâmetro ``argv`` permite injetar argumentos nos testes; quando é
    ``None``, o ``argparse`` lê de ``sys.argv``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        analysis = diagnose_and_analyze_ping(args.target)
    except PingExecutionError as error:
        print(f"Erro: {error}")
        return 1

    print(format_ping_analysis(analysis))
    return 0