"""Analisador de ping da camada de análise (V1).

Este módulo interpreta uma evidência de ping já estruturada (``PingResult``)
e produz um ``PingAnalysis`` com achados condicionais. Ele é uma função pura:
não executa comandos, não acessa a rede, não lê arquivos, não faz parsing e
não altera o modelo recebido.

Responsabilidade:

    PingResult  →  analyze_ping()  →  PingAnalysis

Regras da V1 (exatamente quatro condições):

- ``ping.no_loss``: nenhuma perda observada (``packet_loss_percent == 0``).
- ``ping.partial_loss``: perda parcial (``0 < packet_loss_percent < 100``).
- ``ping.total_loss``: perda total (``packet_loss_percent == 100``).
- ``ping.latency_observed``: há uma média de latência válida.

A latência é apenas informada, nunca classificada como alta ou baixa: a V1
não usa limiar, pois o RTT depende da distância e da rota até o alvo.

Os achados são produzidos em ordem determinística: a condição de perda vem
primeiro e, quando aplicável, ``ping.latency_observed`` vem em seguida.
"""

from network_diagnostic.analysis.findings import (
    AnalysisFinding,
    PingAnalysis,
    Severity,
)
from network_diagnostic.models.results import PingResult


def analyze_ping(result: PingResult) -> PingAnalysis:
    """Interpreta um ``PingResult`` e devolve um ``PingAnalysis``.

    Função pura e determinística: apenas lê o modelo recebido e produz os
    achados correspondentes, sem executar nenhuma operação externa e sem
    alterar o ``PingResult``.

    A ordem dos achados é sempre a mesma: primeiro a condição de perda
    (``no_loss``, ``partial_loss`` ou ``total_loss``) e, quando houver média
    de latência válida, ``latency_observed`` em seguida. Na perda total não
    há achado de latência, porque não existem respostas.
    """
    findings: list[AnalysisFinding] = []

    # Condição de perda: exatamente uma das três se aplica.
    if result.packet_loss_percent == 0:
        findings.append(
            AnalysisFinding(
                code="ping.no_loss",
                severity=Severity.INFO,
                summary="Nenhuma perda de pacotes observada nesta amostra.",
                explanation=(
                    f"Todas as {result.packets_sent} requisições enviadas a "
                    f"{result.target} receberam resposta."
                ),
                limitation=(
                    "Refere-se apenas a esta execução; não representa a "
                    "qualidade da conexão ao longo do tempo."
                ),
            )
        )
    elif result.packet_loss_percent == 100:
        findings.append(
            AnalysisFinding(
                code="ping.total_loss",
                severity=Severity.CRITICAL,
                summary=f"Nenhuma resposta recebida de {result.target} nesta execução.",
                explanation=(
                    f"Os {result.packets_sent} pacotes enviados não retornaram "
                    f"resposta; a conectividade com {result.target} não foi "
                    "confirmada pelo ICMP."
                ),
                limitation=(
                    "O alvo ou um equipamento no caminho pode filtrar ICMP; a "
                    "ausência de resposta não prova que o destino esteja "
                    "inacessível."
                ),
            )
        )
    else:
        # 0 < packet_loss_percent < 100.
        findings.append(
            AnalysisFinding(
                code="ping.partial_loss",
                severity=Severity.WARNING,
                summary=(
                    f"Perda de pacotes parcial observada "
                    f"({result.packet_loss_percent}%)."
                ),
                explanation=(
                    f"{result.packets_received} de {result.packets_sent} "
                    f"requisições a {result.target} receberam resposta."
                ),
                limitation=(
                    "Roteadores e hosts podem tratar ICMP com prioridade baixa; "
                    "a perda observada não comprova perda de tráfego de "
                    "aplicação."
                ),
            )
        )

    # Latência observada: apenas informativa, sem limiar. A perda total é uma
    # condição suficiente para não haver achado de latência: nesse caso não
    # existem respostas. A checagem de avg_latency_ms is not None cobre o caso
    # normal (perda total -> None) e é mantida como contrato explícito, de
    # modo que um PingResult inconsistente com perda total não gere o achado.
    if result.packet_loss_percent != 100 and result.avg_latency_ms is not None:
        findings.append(
            AnalysisFinding(
                code="ping.latency_observed",
                severity=Severity.INFO,
                summary=f"Latência média observada de {result.avg_latency_ms} ms.",
                explanation=(
                    f"RTT mínimo {result.min_latency_ms} ms, "
                    f"máximo {result.max_latency_ms} ms, "
                    f"média {result.avg_latency_ms} ms, "
                    f"considerando {len(result.rtts_ms)} respostas."
                ),
                limitation=(
                    "O RTT depende da distância e da rota até o alvo; valores "
                    "maiores não indicam necessariamente problema."
                ),
            )
        )

    return PingAnalysis(target=result.target, findings=tuple(findings))