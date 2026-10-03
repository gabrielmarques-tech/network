"""Testes da camada de apresentação textual.

Os objetos são montados diretamente a partir dos contratos já existentes em
``network_diagnostic.analysis`` — sem executar diagnósticos, sem rede e sem
parsing.
"""

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.analysis.traceroute import TracerouteAnalysis
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


def test_ping_com_finding():
    finding = _make_finding(
        code="ping.total_loss",
        severity=Severity.CRITICAL,
        summary="Nenhuma resposta recebida.",
        explanation="Os pacotes enviados não retornaram resposta.",
        limitation="O alvo pode filtrar ICMP.",
    )
    analysis = PingAnalysis(target="8.8.8.8", findings=(finding,))

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
    analysis = PingAnalysis(target="1.1.1.1", findings=(first, second))

    text = format_ping_analysis(analysis)

    assert "ping.partial_loss" in text
    assert "ping.latency_observed" in text
    assert "Atenção" in text
    assert "Informativo" in text


def test_ping_sem_findings():
    analysis = PingAnalysis(target="8.8.8.8", findings=())

    text = format_ping_analysis(analysis)

    assert isinstance(text, str)
    assert "Nenhum achado" in text


def test_finding_com_limitation():
    finding = _make_finding(limitation="O RTT depende da rota.")
    analysis = PingAnalysis(target="8.8.8.8", findings=(finding,))

    text = format_ping_analysis(analysis)

    assert "Limitação" in text
    assert "O RTT depende da rota." in text


def test_finding_sem_limitation_nao_exibe_rotulo():
    finding = _make_finding(limitation="")
    analysis = PingAnalysis(target="8.8.8.8", findings=(finding,))

    text = format_ping_analysis(analysis)

    assert "Limitação" not in text


def test_traceroute_com_finding():
    finding = _make_finding(
        code="traceroute.hop_no_response",
        severity=Severity.WARNING,
        summary="O salto 3 não respondeu às sondagens.",
        explanation="Todas as medições do salto 3 estão sem resposta.",
        limitation="Isso não significa perda de pacotes.",
    )
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=(finding,))

    text = format_traceroute_analysis(analysis)

    assert "Atenção" in text
    assert "traceroute.hop_no_response" in text
    assert "O salto 3 não respondeu às sondagens." in text
    assert "Todas as medições do salto 3 estão sem resposta." in text
    assert "Isso não significa perda de pacotes." in text


def test_traceroute_sem_findings():
    analysis = TracerouteAnalysis(target="8.8.8.8", findings=())

    text = format_traceroute_analysis(analysis)

    assert isinstance(text, str)
    assert "Nenhum achado" in text


def test_preservacao_da_ordem():
    first = _make_finding(code="ping.partial_loss")
    second = _make_finding(code="ping.latency_observed")
    third = _make_finding(code="ping.no_loss")
    analysis = PingAnalysis(target="8.8.8.8", findings=(first, second, third))

    text = format_ping_analysis(analysis)

    assert text.index("ping.partial_loss") < text.index("ping.latency_observed")
    assert text.index("ping.latency_observed") < text.index("ping.no_loss")


def test_retorno_como_str():
    ping_analysis = PingAnalysis(target="8.8.8.8", findings=(_make_finding(),))
    traceroute_analysis = TracerouteAnalysis(
        target="8.8.8.8", findings=(_make_finding(code="traceroute.hop_no_response"),)
    )

    assert isinstance(format_ping_analysis(ping_analysis), str)
    assert isinstance(format_traceroute_analysis(traceroute_analysis), str)