"""Camada de aplicação (use case) para o diagnóstico de pathping.

Este módulo compõe, em uma única operação, a coleta de evidência
(``diagnostics``) e a sua interpretação (``analysis``). Ele é uma camada
fina: não executa subprocess, não faz parsing, não interpreta o resultado,
não cria modelos e não duplica regras de análise.

Fluxo:

    collect_pathping_result() -> PathpingResult
        -> analyze_pathping() -> PathpingAnalysis

Qualquer exceção levantada pela camada de diagnóstico ou de análise é
propagada sem tratamento, para não esconder falhas.

Observação: o pathping.exe pode levar bastante tempo para concluir, pois
realiza várias sondagens. Esta camada não adiciona timeout próprio; apenas
repassa ``timeout_ms`` ao diagnóstico.
"""

from network_diagnostic.analysis.pathping import (
    PathpingAnalysis,
    analyze_pathping,
)
from network_diagnostic.diagnostics.pathping import collect_pathping_result


def diagnose_and_analyze_pathping(
    target: str,
    max_hops: int = 30,
    timeout_ms: int = 4000,
) -> PathpingAnalysis:
    """Executa o diagnóstico de pathping e analisa o resultado.

    Chama ``collect_pathping_result`` para coletar o ``PathpingResult`` e
    repassa esse resultado exatamente como recebido para ``analyze_pathping``,
    devolvendo o ``PathpingAnalysis`` produzido.

    Os defaults são os mesmos de ``collect_pathping_result``
    (``max_hops=30`` e ``timeout_ms=4000``). Esta função não interpreta o
    resultado nem trata exceções: apenas encadeia as duas camadas.
    """
    result = collect_pathping_result(
        target, max_hops=max_hops, timeout_ms=timeout_ms
    )
    return analyze_pathping(result)