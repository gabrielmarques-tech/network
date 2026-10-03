"""Camada de aplicação (use case) para o diagnóstico de traceroute.

Este módulo compõe, em uma única operação, a coleta de evidência
(``diagnostics``) e a sua interpretação (``analysis``). Ele é uma camada
fina: não executa subprocess, não faz parsing, não interpreta o resultado,
não cria modelos e não duplica regras de análise.

Fluxo:

    collect_traceroute_result() -> TracerouteResult
        -> analyze_traceroute() -> TracerouteAnalysis

Qualquer exceção levantada pela camada de diagnóstico ou de análise é
propagada sem tratamento, para não esconder falhas.
"""

from network_diagnostic.analysis.traceroute import (
    TracerouteAnalysis,
    analyze_traceroute,
)
from network_diagnostic.diagnostics.traceroute import collect_traceroute_result


def diagnose_and_analyze_traceroute(
    target: str,
    max_hops: int = 30,
    timeout_ms: int = 4000,
) -> TracerouteAnalysis:
    """Executa o diagnóstico de traceroute e analisa o resultado.

    Chama ``collect_traceroute_result`` para coletar o ``TracerouteResult``
    e repassa esse resultado exatamente como recebido para
    ``analyze_traceroute``, devolvendo o ``TracerouteAnalysis`` produzido.

    Os defaults são os mesmos de ``collect_traceroute_result``
    (``max_hops=30`` e ``timeout_ms=4000``). Esta função não interpreta o
    resultado nem trata exceções: apenas encadeia as duas camadas.
    """
    result = collect_traceroute_result(
        target, max_hops=max_hops, timeout_ms=timeout_ms
    )
    return analyze_traceroute(result)