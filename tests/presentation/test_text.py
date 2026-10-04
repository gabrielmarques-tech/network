"""Testes da camada de apresentação textual.

Os objetos são montados diretamente a partir dos contratos já existentes em
``network_diagnostic.analysis`` — sem executar diagnósticos, sem rede e sem
parsing.
"""

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.analysis.traceroute import TracerouteAnalysis
from network_diagnostic.models.results import HopResult
from network_diagnostic.presentation.text import (
    format_ping_analysis,
    format_traceroute_analysis,
)


def _make_finding(
    code: str = "ping.no_loss",
    severity: Severity = Severity.INFO,
    summary: str = "Resumo de teste.",
    explanation: str = "Explicação de teste.",
    limitation: str = "Limitação de teste.",
) -> AnalysisFinding:
    """Constrói um ``AnalysisFinding`` diretamente, sem executar diagnósticos."""
    return AnalysisFinding(
        code=code,
        severity=severity,
        summary=summary,
        explanation=explanation,
        limitation=limitation,
    )


def _make_ping_analysis(**overrides: object) -> PingAnalysis:
    """Constrói um ``PingAnalysis`` com campos objetivos coerentes.

    Permite sobrescrever qualquer campo, inclusive os objetivos, sem executar
    nenhum diagnóstico.
    """
    data: dict[str, object] = {
        "target": "8.8.8.8",
        "packets_sent": 4,
        "packets_received": 4,
        "packet_loss_percent": 0.0,
        "min_latency_ms": 2.0,
        "avg_latency_ms": 3.0,
        "max_latency_ms": 4.0,
        "findings": (),
    }
    data.update(overrides)
    return PingAnalysis(**data)  # type: ignore[arg-type]


def test_ping_com_finding():
    finding = _make_finding(
        code="ping.total_loss",
        severity=Severity.CRITICAL,
        summary="Nenhuma resposta recebida.",
        explanation="Os pacotes enviados não retornaram resposta.",
        limitation="O alvo pode filtrar ICMP.",
    )
    analysis = _make_ping_analysis(
        target="8.8.8.8",
        packets_sent=4,
        packets_received=0,
        packet_loss_percent=100.0,
        min_latency_ms=None,
        avg_latency_ms=None,
        max_latency_ms=None,
        findings=(finding,),
    )

    text = format_ping_analysis(analysis)

    assert "Crítico" in text
    assert "ping.total_loss" in text
    assert "Nenhuma resposta recebida." in text
    assert "Os pacotes enviados não retornaram resposta." in text
    assert "O alvo pode filtrar ICMP." in text


def test_ping_com_multiplos_findings():
    first = _make_finding(
        code="ping.partial_loss",
        severity=Severity.WARNING,
        summary="Perda parcial.",
        explanation="Parte das requisições respondeu.",
    )
    second = _make_finding(
        code="ping.latency_observed",
        severity=Severity.INFO,
        summary="Latência observada.",
        explanation="Há uma média de latência válida.",
    )
    analysis = _make_ping_analysis(target="1.1.1.1", findings=(first, second))

    text = format_ping_analysis(analysis)

    assert "ping.partial_loss" in text
    assert "ping.latency_observed" in text
    assert "Atenção" in text
    assert "Informativo" in text


def test_ping_sem_findings():
    analysis = _make_ping_analysis(target="8.8.8.8", findings=())

    text = format_ping_analysis(analysis)

    assert isinstance(text, str)
    assert "Nenhum achado" in text


def test_finding_com_limitation():
    finding = _make_finding(limitation="O RTT depende da rota.")
    analysis = _make_ping_analysis(findings=(finding,))

    text = format_ping_analysis(analysis)

    assert "Limitação" in text
    assert "O RTT depende da rota." in text


def test_finding_sem_limitation_nao_exibe_rotulo():
    finding = _make_finding(limitation="")
    analysis = _make_ping_analysis(findings=(finding,))

    text = format_ping_analysis(analysis)

    assert "Limitação" not in text


def test_ping_mostra_dados_objetivos():
    """O bloco objetivo exibe os valores reais carregados na análise."""
    analysis = _make_ping_analysis(
        target="dns.google",
        packets_sent=5,
        packets_received=3,
        packet_loss_percent=40.0,
        min_latency_ms=10.0,
        avg_latency_ms=12.5,
        max_latency_ms=20.0,
    )

    text = format_ping_analysis(analysis)

    assert "Alvo: dns.google" in text
    assert "Pacotes enviados: 5" in text
    assert "Pacotes recebidos: 3" in text
    assert "Pacotes perdidos: 2" in text
    assert "Perda de pacotes: 40.0%" in text
    assert "Latência mínima: 10.0 ms" in text
    assert "Latência média: 12.5 ms" in text
    assert "Latência máxima: 20.0 ms" in text


def test_ping_perda_total_mostra_latencia_indisponivel():
    """Na perda total, latências None não são inventadas na apresentação."""
    analysis = _make_ping_analysis(
        packets_sent=4,
        packets_received=0,
        packet_loss_percent=100.0,
        min_latency_ms=None,
        avg_latency_ms=None,
        max_latency_ms=None,
    )

    text = format_ping_analysis(analysis)

    assert "Latência mínima: indisponível" in text
    assert "Latência média: indisponível" in text
    assert "Latência máxima: indisponível" in text
    assert "Latência mínima: None" not in text


def test_ping_evidencia_objetiva_antes_dos_findings():
    """O bloco objetivo aparece antes dos achados interpretativos."""
    finding = _make_finding(code="ping.no_loss")
    analysis = _make_ping_analysis(findings=(finding,))

    text = format_ping_analysis(analysis)

    assert text.index("Perda de pacotes:") < text.index("ping.no_loss")
    assert text.index("Alvo:") < text.index("ping.no_loss")


def test_ping_mostra_amplitude_de_latencia():
    """A amplitude de latência é exibida no bloco objetivo quando presente."""
    analysis = _make_ping_analysis(latency_amplitude_ms=20.0)

    text = format_ping_analysis(analysis)

    assert "Amplitude de latência: 20.0 ms" in text


def test_ping_amplitude_indisponivel_quando_none():
    """Sem amplitude observável, a apresentação informa indisponível."""
    analysis = _make_ping_analysis(latency_amplitude_ms=None)

    text = format_ping_analysis(analysis)

    assert "Amplitude de latência: indisponível" in text
    assert "Amplitude de latência: None" not in text


def test_ping_amplitude_antes_dos_findings():
    """A amplitude aparece no bloco objetivo, antes dos achados."""
    finding = _make_finding(code="ping.no_loss")
    analysis = _make_ping_analysis(
        latency_amplitude_ms=20.0,
        findings=(finding,),
    )

    text = format_ping_analysis(analysis)

    assert text.index("Amplitude de latência:") < text.index("ping.no_loss")


def _make_hop(**overrides: object) -> HopResult:
    """Constrói um ``HopResult`` diretamente, sem executar diagnósticos."""
    data: dict[str, object] = {
        "hop_number": 1,
        "rtts_ms": [1.0, 2.0, 3.0],
        "address": "192.168.1.1",
        "hostname": None,
    }
    data.update(overrides)
    return HopResult(**data)  # type: ignore[arg-type]


def test_traceroute_com_finding():
    finding = _make_finding(
        code="traceroute.hop_no_response",
        severity=Severity.WARNING,
        summary="O salto 3 não respondeu às sondagens.",
        explanation="Todas as medições do salto 3 estão sem resposta.",
        limitation="Isso não significa perda de pacotes.",
    )
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=(finding,), hops=())

    text = format_traceroute_analysis(analysis)

    assert "Atenção" in text
    assert "traceroute.hop_no_response" in text
    assert "O salto 3 não respondeu às sondagens." in text
    assert "Todas as medições do salto 3 estão sem resposta." in text
    assert "Isso não significa perda de pacotes." in text


def test_traceroute_sem_findings():
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=(), hops=())

    text = format_traceroute_analysis(analysis)

    assert isinstance(text, str)
    assert "Nenhum achado" in text


def test_traceroute_mostra_numero_e_endereco_do_hop():
    """A rota exibe o número do hop e o endereço quando disponível."""
    analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(),
        hops=(_make_hop(hop_number=2, address="10.0.0.1", hostname=None),),
    )

    text = format_traceroute_analysis(analysis)

    assert "Rota:" in text
    assert "2" in text
    assert "10.0.0.1" in text


def test_traceroute_mostra_hostname_com_endereco():
    """Com hostname e endereço, a identificação é 'hostname [address]'."""
    analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(),
        hops=(
            _make_hop(address="8.8.8.8", hostname="dns.google"),
        ),
    )

    text = format_traceroute_analysis(analysis)

    assert "dns.google [8.8.8.8]" in text


def test_traceroute_mostra_somente_hostname():
    """Sem endereço, a identificação é apenas o hostname."""
    analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(),
        hops=(_make_hop(address=None, hostname="router.local"),),
    )

    text = format_traceroute_analysis(analysis)

    assert "router.local" in text


def test_traceroute_mostra_os_tres_rtts():
    """Os três RTTs do hop são exibidos."""
    analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(),
        hops=(_make_hop(rtts_ms=[8.0, 7.0, 9.0]),),
    )

    text = format_traceroute_analysis(analysis)

    assert "8.0 ms" in text
    assert "7.0 ms" in text
    assert "9.0 ms" in text


def test_traceroute_rtt_none_vira_asterisco():
    """Uma sondagem sem resposta (None) é exibida como '*'."""
    analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(),
        hops=(_make_hop(rtts_ms=[3.0, None, 3.0]),),
    )

    text = format_traceroute_analysis(analysis)

    assert "*" in text
    assert "None" not in text


def test_traceroute_rota_aparece_antes_dos_findings():
    """O bloco de rota é exibido antes dos achados."""
    finding = _make_finding(code="traceroute.hop_no_response")
    analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(finding,),
        hops=(_make_hop(address="10.0.0.1"),),
    )

    text = format_traceroute_analysis(analysis)

    assert text.index("Rota:") < text.index("traceroute.hop_no_response")


def test_traceroute_sem_hops_nao_quebra():
    """Sem hops, a saída informa a ausência de rota sem quebrar."""
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=(), hops=())

    text = format_traceroute_analysis(analysis)

    assert isinstance(text, str)
    assert "Rota:" in text
    assert "Nenhum hop" in text


def test_preservacao_da_ordem():
    first = _make_finding(code="ping.partial_loss")
    second = _make_finding(code="ping.latency_observed")
    third = _make_finding(code="ping.no_loss")
    analysis = _make_ping_analysis(findings=(first, second, third))

    text = format_ping_analysis(analysis)

    assert text.index("ping.partial_loss") < text.index("ping.latency_observed")
    assert text.index("ping.latency_observed") < text.index("ping.no_loss")


def test_retorno_como_str():
    ping_analysis = _make_ping_analysis(findings=(_make_finding(),))
    traceroute_analysis = TracerouteAnalysis(
        target="8.8.8.8",
        findings=(_make_finding(code="traceroute.hop_no_response"),),
        hops=(),
    )

    assert isinstance(format_ping_analysis(ping_analysis), str)
    assert isinstance(format_traceroute_analysis(traceroute_analysis), str)
