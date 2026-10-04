"""Analisador de pathping da camada de análise (V1).

Este módulo interpreta uma evidência de pathping já estruturada
(``PathpingResult``) e produz um ``PathpingAnalysis`` com achados condicionais
por salto. Ele é uma função pura: não executa comandos, não acessa a rede,
não lê arquivos, não faz parsing e não altera o modelo recebido.

Responsabilidade:

    PathpingResult  →  analyze_pathping()  →  PathpingAnalysis

Regras da V1 (por salto):

- ``pathping.hop_link_loss``: a perda observada na coluna do próprio
  salto/vínculo (``link_loss_percent``) é maior que zero. Severidade
  ``WARNING``.
- ``pathping.source_loss_observed``: a perda acumulada observada entre a
  origem e o salto (``source_loss_percent``) é maior que zero. Severidade
  ``INFO``.

As duas colunas são medições diferentes e **não** são combinadas: a primeira
representa a perda acumulada da origem até o salto e a segunda a perda
observada especificamente naquele nó/vínculo. Um valor ausente (``None``) não
gera achado.

A V1 não classifica a rota como boa ou ruim, não aponta um salto como causa
raiz, não define limiar de latência, não conclui perda de tráfego de aplicação
e não infere que o destino foi alcançado: essas afirmações exigiriam
evidências que este módulo não possui. A perda observada em ICMP é apenas o
que foi medido.

Os achados são produzidos em ordem determinística, seguindo a ordem dos saltos
em ``result.hops``. Para cada salto, o achado de vínculo é produzido antes do
achado de perda acumulada, quando ambos se aplicam.
"""

from dataclasses import dataclass

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.models.results import PathpingHop, PathpingResult


@dataclass(frozen=True)
class PathpingAnalysis:
    """Resultado da análise de uma execução de pathping.

    Contêiner de dados imutável que agrega os achados derivados de um
    ``PathpingResult``. Não executa comandos, não acessa a rede e não contém
    lógica de diagnóstico.

    Campos:

    - ``target``: alvo analisado (o mesmo alvo da evidência de origem).
    - ``findings``: tupla imutável de ``AnalysisFinding``.
    - ``hops``: tupla imutável com a evidência dos saltos coletados
      (``PathpingHop``), transportada do ``PathpingResult`` de origem sem
      interpretação adicional. Cada salto é carregado exatamente como está no
      modelo, apenas para que a apresentação possa exibir a evidência, na
      ordem original.
    """

    target: str
    findings: tuple[AnalysisFinding, ...]
    hops: tuple[PathpingHop, ...]


def _analyze_hop(hop: PathpingHop) -> list[AnalysisFinding]:
    """Classifica um único salto, devolvendo a lista de achados aplicáveis.

    Função pura: não executa operações externas e não altera o ``PathpingHop``
    recebido. Um salto pode gerar zero, um ou dois achados, pois as duas
    colunas de perda são condições independentes. Valores ausentes (``None``)
    não geram achado. A ordem é: primeiro o achado de vínculo, depois o de
    perda acumulada.
    """
    findings: list[AnalysisFinding] = []

    # Coluna do próprio nó/vínculo: perda observada especificamente aqui.
    if hop.link_loss_percent is not None and hop.link_loss_percent > 0:
        findings.append(
            AnalysisFinding(
                code="pathping.hop_link_loss",
                severity=Severity.WARNING,
                summary=(
                    f"Perda observada no vínculo do salto {hop.hop_number} "
                    f"({hop.link_loss_percent}%)."
                ),
                explanation=(
                    f"A coluna correspondente ao próprio salto/vínculo indica "
                    f"{hop.link_loss_percent}% de perda observada no salto "
                    f"{hop.hop_number}."
                ),
                limitation=(
                    "A perda de ICMP observada neste salto não prova que o "
                    "equipamento ou o vínculo seja a causa de uma degradação "
                    "do tráfego; equipamentos podem responder às sondagens "
                    "com prioridade baixa. Esta evidência também não comprova "
                    "perda do tráfego de aplicação."
                ),
            )
        )

    # Coluna "Origem aqui": perda acumulada da origem até este salto.
    if hop.source_loss_percent is not None and hop.source_loss_percent > 0:
        findings.append(
            AnalysisFinding(
                code="pathping.source_loss_observed",
                severity=Severity.INFO,
                summary=(
                    f"Perda acumulada observada até o salto "
                    f"{hop.hop_number} ({hop.source_loss_percent}%)."
                ),
                explanation=(
                    f"A coluna 'Origem aqui' indica {hop.source_loss_percent}% "
                    f"de perda acumulada entre a origem e o salto "
                    f"{hop.hop_number}."
                ),
                limitation=(
                    "A perda acumulada observada em ICMP não representa "
                    "necessariamente perda do tráfego de aplicação e não "
                    "permite apontar um salto como causa do problema. Ela "
                    "também não indica que o destino foi alcançado nem que a "
                    "rota esteja degradada."
                ),
            )
        )

    return findings


def analyze_pathping(result: PathpingResult) -> PathpingAnalysis:
    """Interpreta um ``PathpingResult`` e devolve um ``PathpingAnalysis``.

    Função pura e determinística: apenas lê o modelo recebido e produz os
    achados correspondentes, sem executar nenhuma operação externa e sem
    alterar o ``PathpingResult``.

    Os achados seguem a ordem dos saltos em ``result.hops``; para cada salto,
    o achado de vínculo vem antes do achado de perda acumulada. Saltos sem
    perda observada não geram achado. Sem saltos, a análise é válida e
    devolve ``hops`` e ``findings`` vazios.

    Além dos achados, a evidência dos saltos é transportada adiante em
    ``hops``: os ``PathpingHop`` são copiados de ``result.hops`` sem qualquer
    interpretação, para que a apresentação possa exibir a evidência coletada.
    """
    findings: list[AnalysisFinding] = []

    for hop in result.hops:
        findings.extend(_analyze_hop(hop))

    return PathpingAnalysis(
        target=result.target,
        findings=tuple(findings),
        hops=tuple(result.hops),
    )