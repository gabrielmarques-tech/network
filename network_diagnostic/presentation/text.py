"""Camada de apresentação textual (V1).

Este módulo transforma objetos da camada de análise em texto legível para o
usuário. Ele é composto apenas por funções puras: não executa comandos, não
acessa a rede, não lê arquivos, não faz parsing, não cria novos achados e não
altera os objetos recebidos.

Responsabilidade:

    PingAnalysis        →  format_ping_analysis()        →  str
    TracerouteAnalysis  →  format_traceroute_analysis()  →  str
    PathpingAnalysis    →  format_pathping_analysis()    →  str

Para o ping, o texto exibe primeiro o bloco de evidência objetiva carregado
pela análise e, em seguida, os achados. Para o traceroute e o pathping, exibe
o alvo, o bloco da evidência coletada (rota ou saltos, sem interpretação) e,
em seguida, os achados. Em todos os casos o texto reproduz somente o que já
existe nos objetos de análise (severidade, código, resumo, explicação e,
quando preenchida, a limitação), preservando a ordem em que os achados foram
produzidos pela camada de análise. A evidência não recebe severidade nem
diagnóstico: é exibida apenas como evidência.
"""

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.pathping import PathpingAnalysis
from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.analysis.traceroute import TracerouteAnalysis
from network_diagnostic.models.results import HopResult, PathpingHop

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


def _format_analysis(
    target: str,
    findings: tuple[AnalysisFinding, ...],
    evidence: str | None = None,
) -> str:
    """Monta o texto de uma análise a partir de seu alvo, evidência e achados.

    Função pura e determinística: preserva a ordem dos achados recebidos e
    não produz nenhuma informação que não esteja contida neles. O bloco de
    evidência é opcional: quando ``evidence`` é ``None`` o comportamento é
    idêntico ao anterior, exibindo apenas alvo e achados.
    """
    lines = [f"Alvo: {target}"]

    if evidence is not None:
        lines.append(evidence)

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


def _format_rtt(value: float | None) -> str:
    """Formata uma medição RTT de um hop para exibição na rota.

    Função pura: quando ``value`` é ``None`` (sondagem sem resposta) devolve
    ``*``; caso contrário devolve o valor seguido de ``ms``. O valor do modelo
    é preservado como está (por exemplo, ``0.0 ms``); a apresentação não
    reinterpreta a convenção de ``<1 ms`` nesta etapa.
    """
    if value is None:
        return "*"
    return f"{value} ms"


def _format_hop_identifier(hop: HopResult) -> str:
    """Identifica um hop a partir de hostname e/ou endereço.

    Função pura, apenas de formatação: combina o que existir no modelo, sem
    inventar informação. As combinações possíveis são ``hostname [address]``
    (ambos), ``hostname`` (só nome), ``address`` (só IP) e um rótulo neutro
    quando nenhum dos dois existe.
    """
    if hop.hostname and hop.address:
        return f"{hop.hostname} [{hop.address}]"
    if hop.hostname:
        return hop.hostname
    if hop.address:
        return hop.address
    return "(sem identificação)"


def _format_hop_line(hop: HopResult) -> str:
    """Monta a linha de um único hop da rota.

    Função pura: exibe número do hop, identificação e as três medições RTT.
    A linha é apenas evidência: não recebe severidade nem interpretação.
    """
    rtts = hop.rtts_ms
    rtt_columns = "   ".join(_format_rtt(rtt) for rtt in rtts)
    identifier = _format_hop_identifier(hop)
    return f"  {hop.hop_number}  {identifier}  {rtt_columns}"


def _format_route(hops: tuple[HopResult, ...]) -> str:
    """Monta o bloco textual da rota coletada.

    Função pura e determinística: preserva a ordem dos hops recebidos e não
    produz nenhuma informação que não esteja neles. Quando não há hops,
    informa explicitamente que a rota não foi coletada, sem inventar dados.
    """
    lines = ["Rota:"]
    if not hops:
        lines.append("  Nenhum hop foi coletado nesta execução.")
    else:
        for hop in hops:
            lines.append(_format_hop_line(hop))
    return "\n".join(lines)


def _format_percent(value: float | None) -> str:
    """Formata um percentual de perda, ou um marcador de indisponibilidade.

    Função pura: quando ``value`` é ``None`` (coluna de perda ausente no
    modelo, como no salto sem estatística) devolve o mesmo marcador textual
    usado para latências indisponíveis; caso contrário, devolve o valor
    seguido de ``%``. Não fabrica números.
    """
    if value is None:
        return _LATENCY_UNAVAILABLE
    return f"{value}%"


def _format_pathping_hop_line(hop: PathpingHop) -> str:
    """Monta a linha de evidência de um único salto do pathping.

    Função pura: exibe número do salto, identificação, RTT e as duas colunas
    de perda (acumulada, "Origem", e do próprio nó/vínculo, "Enlace"). A
    linha é apenas evidência: não recebe severidade nem interpretação. Valores
    ausentes usam as convenções já existentes (``*`` para RTT e o marcador de
    indisponibilidade para percentuais), nunca ``None``.
    """
    identifier = hop.address if hop.address else "(sem identificação)"
    rtt = _format_rtt(hop.rtt_ms)
    source = _format_percent(hop.source_loss_percent)
    link = _format_percent(hop.link_loss_percent)
    return (
        f"  {hop.hop_number}  {identifier}  {rtt}  "
        f"Origem: {source}  Enlace: {link}"
    )


def _format_pathping_hops(hops: tuple[PathpingHop, ...]) -> str:
    """Monta o bloco textual da evidência de saltos do pathping.

    Função pura e determinística: preserva a ordem dos saltos recebidos e não
    produz nenhuma informação que não esteja neles. Quando não há saltos,
    informa explicitamente que nenhum salto foi coletado, sem inventar dados.
    """
    lines = ["Saltos:"]
    if not hops:
        lines.append("  Nenhum salto foi coletado nesta execução.")
    else:
        for hop in hops:
            lines.append(_format_pathping_hop_line(hop))
    return "\n".join(lines)


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
            f"Amplitude de latência: "
            f"{_format_latency(analysis.latency_amplitude_ms)}",
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

    A saída apresenta o alvo, o bloco da rota coletada (evidência, sem
    interpretação) e, em seguida, os achados. A rota é montada por
    ``_format_route`` e entregue a ``_format_analysis`` como um bloco
    opcional; nenhum hop é reclassificado e nenhuma severidade é atribuída
    à rota.
    """
    route = _format_route(analysis.hops)
    return _format_analysis(analysis.target, analysis.findings, evidence=route)


def format_pathping_analysis(analysis: PathpingAnalysis) -> str:
    """Formata um ``PathpingAnalysis`` em texto legível para o usuário.

    Função pura: recebe apenas o objeto de análise e devolve uma ``str``.
    Não executa comandos, não acessa a rede, não faz parsing, não cria novos
    achados e não altera o objeto recebido.

    A saída apresenta o alvo, o bloco da evidência de saltos (número,
    identificação, RTT e as colunas Origem/Enlace, sem interpretação) e, em
    seguida, os achados. O bloco de saltos é montado por
    ``_format_pathping_hops`` e entregue a ``_format_analysis`` como um bloco
    opcional, garantindo que a evidência apareça antes dos achados. Nenhum
    salto é reclassificado e nenhuma severidade é atribuída à evidência.
    """
    hops = _format_pathping_hops(analysis.hops)
    return _format_analysis(analysis.target, analysis.findings, evidence=hops)