"""Camada de apresentação textual (V1).

Este módulo transforma objetos da camada de análise em texto legível para o
usuário. Ele é composto apenas por funções puras: não executa comandos, não
acessa a rede, não lê arquivos, não faz parsing, não cria novos achados e não
altera os objetos recebidos.

Responsabilidade:

    PingAnalysis        →  format_ping_analysis()        →  str
    TracerouteAnalysis  →  format_traceroute_analysis()  →  str

O texto reproduz apenas o que já existe nos achados (severidade, código,
resumo, explicação e, quando preenchida, a limitação), preservando a ordem em
que os achados foram produzidos pela camada de análise.
"""

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.analysis.traceroute import TracerouteAnalysis

# Rótulos visuais em português para cada nível de severidade existente.
_SEVERITY_LABELS: dict[Severity, str] = {
    Severity.INFO: "Informativo",
    Severity.WARNING: "Atenção",
    Severity.CRITICAL: "Crítico",
}


def _format_finding(finding: AnalysisFinding) -> str:
    """Formata um único achado em texto.

    Função pura: apenas lê o achado recebido e devolve texto, sem executar
    operações externas e sem alterar o objeto. A limitação só é exibida
    quando estiver preenchida.
    """
    lines = [
        f"[{_SEVERITY_LABELS[finding.severity]}] {finding.code}",
        f"  Resumo: {finding.summary}",
        f"  Explicação: {finding.explanation}",
    ]

    if finding.limitation:
        lines.append(f"  Limitação: {finding.limitation}")

    return "\n".join(lines)


def _format_analysis(target: str, findings: tuple[AnalysisFinding, ...]) -> str:
    """Monta o texto de uma análise a partir de seu alvo e achados.

    Função pura e determinística: preserva a ordem dos achados recebidos e
    não produz nenhuma informação que não esteja contida neles.
    """
    lines = [f"Alvo: {target}"]

    if not findings:
        lines.append("Nenhum achado de análise foi produzido para esta execução.")
    else:
        for finding in findings:
            lines.append(_format_finding(finding))

    return "\n".join(lines)


def format_ping_analysis(analysis: PingAnalysis) -> str:
    """Formata um ``PingAnalysis`` em texto legível para o usuário.

    Função pura: recebe apenas o objeto de análise e devolve uma ``str``.
    Não executa comandos, não acessa a rede, não faz parsing, não cria novos
    achados e não altera o objeto recebido.
    """
    return _format_analysis(analysis.target, analysis.findings)


def format_traceroute_analysis(analysis: TracerouteAnalysis) -> str:
    """Formata um ``TracerouteAnalysis`` em texto legível para o usuário.

    Função pura: recebe apenas o objeto de análise e devolve uma ``str``.
    Não executa comandos, não acessa a rede, não faz parsing, não cria novos
    achados e não altera o objeto recebido.
    """
    return _format_analysis(analysis.target, analysis.findings)