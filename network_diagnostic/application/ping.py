"""Camada de aplicação (use case) para o diagnóstico de ping.

Este módulo compõe, em uma única operação, a coleta de evidência
(``diagnostics``) e a sua interpretação (``analysis``). Ele é uma camada
fina: não executa subprocess, não faz parsing, não interpreta o resultado,
não cria modelos e não duplica regras de análise.

Fluxo:

    diagnose_ping() -> PingResult -> analyze_ping() -> PingAnalysis

Qualquer exceção levantada pela camada de diagnóstico ou de análise é
propagada sem tratamento, para não esconder falhas.
"""

from network_diagnostic.analysis.ping import PingAnalysis, analyze_ping
from network_diagnostic.diagnostics.ping import diagnose_ping


def diagnose_and_analyze_ping(target: str, count: int = 4) -> PingAnalysis:
    """Executa o diagnóstico de ping e analisa o resultado.

    Chama ``diagnose_ping`` para coletar o ``PingResult`` e repassa esse
    resultado exatamente como recebido para ``analyze_ping``, devolvendo o
    ``PingAnalysis`` produzido.

    Os defaults são os mesmos de ``diagnose_ping`` (``count=4``). Esta função
    não interpreta o resultado nem trata exceções: apenas encadeia as duas
    camadas.
    """
    result = diagnose_ping(target, count=count)
    return analyze_ping(result)