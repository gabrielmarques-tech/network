"""Analisador de traceroute da camada de análise (V1).

Este módulo interpreta uma evidência de traceroute já estruturada
(``TracerouteResult``) e produz um ``TracerouteAnalysis`` com achados
condicionais por salto. Ele é uma função pura: não executa comandos, não
acessa a rede, não lê arquivos, não faz parsing e não altera o modelo
recebido.

Responsabilidade:

    TracerouteResult  →  analyze_traceroute()  →  TracerouteAnalysis

Regras da V1 (por salto):

- ``traceroute.hop_no_response``: todas as medições RTT do salto são ``None``
  (``*``). Severidade ``WARNING``.
- ``traceroute.hop_partial_response``: o salto tem ao menos uma medição
  numérica e ao menos uma medição ``None``. Severidade ``INFO``.

Um salto com todas as medições numéricas não gera achado. Um salto sem
sondagens (``rtts_ms == []``) também não gera achado nesta V1: é tratado
como entrada sem dados para classificação.

A V1 não classifica a rota como boa ou ruim, não define limite de latência,
não aponta um salto como causa do problema e não conclui perda de pacotes:
essas afirmações exigiriam evidências que este módulo não possui. A ausência
de resposta a uma sondagem é apenas o que foi observado.

Os achados são produzidos em ordem determinística, seguindo a ordem dos
saltos em ``result.hops``.
"""

from dataclasses import dataclass

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.models.results import HopResult, TracerouteResult


@dataclass(frozen=True)
class TracerouteAnalysis:
    """Resultado da análise de uma execução de traceroute.

    Contêiner de dados imutável que agrega os achados derivados de um
    ``TracerouteResult``. Não executa comandos, não acessa a rede e não contém
    lógica de diagnóstico.

    Campos:

    - ``target``: alvo analisado (o mesmo alvo da evidência de origem).
    - ``findings``: tupla imutável de ``AnalysisFinding``.
    - ``hops``: tupla imutável com a evidência de rota coletada
      (``HopResult``), transportada do ``TracerouteResult`` de origem sem
      interpretação adicional. Cada hop é carregado exatamente como está no
      modelo, apenas para que a apresentação possa exibir a rota.
    """

    target: str
    findings: tuple[AnalysisFinding, ...]
    hops: tuple[HopResult, ...]


def _analyze_hop(hop: HopResult) -> AnalysisFinding | None:
    """Classifica um único salto, ou devolve ``None`` se não houver achado.

    Não executa operações externas e não altera o ``HopResult`` recebido.
    """
    rtts = hop.rtts_ms

    # Salto sem sondagens: entrada sem dados para classificação nesta V1.
    # Não é tratado como "sem resposta".
    if not rtts:
        return None

    has_response = any(rtt is not None for rtt in rtts)
    has_missing = any(rtt is None for rtt in rtts)

    # Todas as medições sem resposta.
    if not has_response:
        return AnalysisFinding(
            code="traceroute.hop_no_response",
            severity=Severity.WARNING,
            summary=(
                f"O salto {hop.hop_number} não respondeu às sondagens "
                "utilizadas pelo traceroute."
            ),
            explanation=(
                f"Todas as {len(rtts)} medições do salto {hop.hop_number} "
                "estão sem resposta (``*``) nesta execução."
            ),
            limitation=(
                "A ausência de resposta deste salto não significa perda de "
                "pacotes nem bloqueio de tráfego; equipamentos podem não "
                "responder às sondagens do traceroute mesmo encaminhando "
                "tráfego. Este salto não pode ser apontado como causa de um "
                "problema a partir desta evidência."
            ),
        )

    # Pelo menos uma medição numérica e pelo menos uma sem resposta.
    if has_missing:
        answered = sum(1 for rtt in rtts if rtt is not None)
        return AnalysisFinding(
            code="traceroute.hop_partial_response",
            severity=Severity.INFO,
            summary=(
                f"O salto {hop.hop_number} respondeu apenas parcialmente às "
                "sondagens."
            ),
            explanation=(
                f"{answered} de {len(rtts)} medições do salto "
                f"{hop.hop_number} retornaram resposta nesta execução."
            ),
            limitation=(
                "Respostas parciais às sondagens não são perda de pacotes e "
                "não indicam necessariamente problema neste salto; "
                "equipamentos podem responder apenas a parte das sondagens."
            ),
        )

    # Todas as medições numéricas: salto totalmente responsivo, sem achado.
    return None


def analyze_traceroute(result: TracerouteResult) -> TracerouteAnalysis:
    """Interpreta um ``TracerouteResult`` e devolve um ``TracerouteAnalysis``.

    Função pura e determinística: apenas lê o modelo recebido e produz os
    achados correspondentes, sem executar nenhuma operação externa e sem
    alterar o ``TracerouteResult``.

    Os achados seguem a ordem dos saltos em ``result.hops``. Saltos totalmente
    responsivos e saltos sem sondagens (``rtts_ms == []``) não geram achado.

    Além dos achados, a evidência de rota é transportada adiante em
    ``hops``: os ``HopResult`` são copiados de ``result.hops`` sem qualquer
    interpretação, para que a apresentação possa exibir a rota coletada.
    """
    findings: list[AnalysisFinding] = []

    for hop in result.hops:
        finding = _analyze_hop(hop)
        if finding is not None:
            findings.append(finding)

    return TracerouteAnalysis(
        target=result.target,
        findings=tuple(findings),
        hops=tuple(result.hops),
    )