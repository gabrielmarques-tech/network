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

from dataclasses import dataclass

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.models.results import PingResult


@dataclass(frozen=True)
class PingAnalysis:
    """Resultado da análise de uma execução de ping.

    Contêiner de dados imutável que agrega os achados derivados de um
    ``PingResult`` e os dados objetivos essenciais à apresentação. Não
    executa comandos, não acessa a rede e não contém lógica de diagnóstico.

    Ele carrega adiante duas coisas do resultado analisado:

    - os dados objetivos necessários à apresentação (contagens de pacotes,
      perda e latências mínima, média e máxima);
    - os achados interpretativos derivados desses dados.

    Os campos objetivos são copiados explicitamente do ``PingResult``. O
    contrato é intencionalmente pequeno e não inclui ``rtts_ms``.

    Campos:

    - ``target``: alvo analisado (o mesmo alvo da evidência de origem).
    - ``packets_sent``: quantidade de requisições enviadas.
    - ``packets_received``: quantidade de respostas recebidas.
    - ``packet_loss_percent``: percentual de perda observado.
    - ``min_latency_ms``: latência mínima em ms, ou ``None`` se indisponível.
    - ``avg_latency_ms``: latência média em ms, ou ``None`` se indisponível.
    - ``max_latency_ms``: latência máxima em ms, ou ``None`` se indisponível.
    - ``latency_amplitude_ms``: amplitude observada (max - min) dos RTTs em
      ms, ou ``None`` se houver menos de duas respostas.
    - ``findings``: tupla imutável de ``AnalysisFinding``.

    Os campos objetivos são opcionais apenas na amplitude: ela é aditiva e
    tem default ``None`` para não quebrar o contrato anterior. Sua posição é
    a última porque os demais campos não possuem default.
    """

    target: str
    packets_sent: int
    packets_received: int
    packet_loss_percent: float
    min_latency_ms: float | None
    avg_latency_ms: float | None
    max_latency_ms: float | None
    findings: tuple[AnalysisFinding, ...]
    latency_amplitude_ms: float | None = None


def _compute_latency_amplitude(rtts_ms: list[float]) -> float | None:
    """Calcula a amplitude observada (max - min) dos RTTs, em ms.

    Função pura: usa exclusivamente a lista de RTTs recebida. Com menos de
    duas respostas não há amplitude a observar e devolve ``None``. Duas ou
    mais respostas iguais resultam naturalmente em ``0.0``. Não interpreta o
    valor: amplitude maior ou menor não é classificada como problema.
    """
    if len(rtts_ms) < 2:
        return None
    return max(rtts_ms) - min(rtts_ms)


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
                    "maiores não indicam necessariamente problema. A amplitude "
                    "observada em ICMP não representa necessariamente a "
                    "experiência da aplicação."
                ),
            )
        )

    # Copia explícita dos campos objetivos do PingResult para o contrato da
    # análise: cada valor usado pelos achados é também repassado adiante para
    # a apresentação, sem recalcular nem reinterpretar nada. A amplitude é
    # calculada exclusivamente a partir dos RTTs observados.
    return PingAnalysis(
        target=result.target,
        packets_sent=result.packets_sent,
        packets_received=result.packets_received,
        packet_loss_percent=result.packet_loss_percent,
        min_latency_ms=result.min_latency_ms,
        avg_latency_ms=result.avg_latency_ms,
        max_latency_ms=result.max_latency_ms,
        findings=tuple(findings),
        latency_amplitude_ms=_compute_latency_amplitude(result.rtts_ms),
    )
