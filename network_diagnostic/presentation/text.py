"""Camada de apresentação textual (V1).

Este módulo transforma objetos da camada de análise em texto legível para o
usuário. Ele é composto apenas por funções puras: não executa comandos, não
acessa a rede, não lê arquivos, não faz parsing, não cria novos achados e não
altera os objetos recebidos.

Responsabilidade:

    PingAnalysis        →  format_ping_analysis()        →  str
    TracerouteAnalysis  →  format_traceroute_analysis()  →  str

Para o ping, o texto exibe primeiro o bloco de evidência objetiva carregado
pela análise e, em seguida, os achados. Para o traceroute, exibe apenas os
achados. Em ambos os casos o texto reproduz somente o que já existe nos
objetos de análise (severidade, código, resumo, explicação e, quando
preenchida, a limitação), preservando a ordem em que os achados foram
produzidos pela camada de análise.
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

# Marcador textual para latências indisponíveis (por exemplo, na perda total).
# Quando min/avg/max_latency_ms são None, a apresentação não inventa um
# número: informa explicitamente que o valor está indisponível.
_LATENCY_UNAVAILABLE = "indisponível"


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


def _format_findings(findings: tuple[AnalysisFinding, ...]) -> str:
    """Formata a lista de achados, preservando a ordem recebida.

    Função pura e determinística: quando não há achados, devolve a mensagem
    genérica; caso contrário, junta cada achado já formatado.
    """
    if not findings:
        return "Nenhum achado de análise foi produzido para esta execução."
    return "\n".join(_format_finding(finding) for finding in findings)


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


def _format_latency(value: float | None) -> str:
    """Formata um valor de latência em ms, ou um marcador de indisponibilidade.

    Função pura: quando ``value`` é ``None`` devolve o marcador textual;
    caso contrário, devolve o valor seguido de ``ms``. Não fabrica números.
    """
    if value is None:
        return _LATENCY_UNAVAILABLE
    return f"{value} ms"


def _format_ping_objective(analysis: PingAnalysis) -> str:
    """Monta o bloco de evidência objetiva de um ``PingAnalysis``.

    Função pura: usa apenas os campos objetivos carregados na análise. Os
    pacotes perdidos são derivados de ``packets_sent - packets_received``,
    pois é uma operação determinística sobre dados já existentes.
    """
    packets_lost = analysis.packets_sent - analysis.packets_received
    return "\n".join(
        [
            f"Alvo: {analysis.target}",
            f"Pacotes enviados: {analysis.packets_sent}",
            f"Pacotes recebidos: {analysis.packets_received}",
            f"Pacotes perdidos: {packets_lost}",
            f"Perda de pacotes: {analysis.packet_loss_percent}%",
            f"Latência mínima: {_format_latency(analysis.min_latency_ms)}",
            f"Latência média: {_format_latency(analysis.avg_latency_ms)}",
            f"Latência máxima: {_format_latency(analysis.max_latency_ms)}",
        ]
    )


def format_ping_analysis(analysis: PingAnalysis) -> str:
    """Formata um ``PingAnalysis`` em texto legível para o usuário.

    Função pura: recebe apenas o objeto de análise e devolve uma ``str``.
    Não executa comandos, não acessa a rede, não faz parsing, não cria novos
    achados e não altera o objeto recebido.

    A saída apresenta primeiro o bloco de evidência objetiva e, em seguida,
    os achados interpretativos, preservando a ordem em que foram produzidos
    pela camada de análise. Diferentemente de ``TracerouteAnalysis``, o
    contrato de ``PingAnalysis`` carrega dados objetivos além dos achados.
    """
    objective = _format_ping_objective(analysis)
    findings_text = _format_findings(analysis.findings)
    return f"{objective}\n{findings_text}"


def format_traceroute_analysis(analysis: TracerouteAnalysis) -> str:
    """Formata um ``TracerouteAnalysis`` em texto legível para o usuário.

    Função pura: recebe apenas o objeto de análise e devolve uma ``str``.
    Não executa comandos, não acessa a rede, não faz parsing, não cria novos
    achados e não altera o objeto recebido.
    """
    return _format_analysis(analysis.target, analysis.findings)