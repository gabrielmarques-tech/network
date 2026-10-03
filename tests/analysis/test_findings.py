"""Testes para o modelo base da camada de análise.

Estes testes validam o comportamento observável dos contêineres de dados:
os níveis de ``Severity``, a criação correta, a imutabilidade e a igualdade
por valor. Eles não testam execução de diagnóstico, parsing nem regras de
análise (que ainda não existem).
"""

from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.analysis.findings import (
    AnalysisFinding,
    PingAnalysis,
    Severity,
)


def make_finding(**overrides: object) -> AnalysisFinding:
    """Cria um AnalysisFinding padrão, permitindo sobrescrever campos."""
    data: dict[str, object] = {
        "code": "ping.total_loss",
        "severity": Severity.CRITICAL,
        "summary": "Não houve resposta a nenhum pacote.",
        "explanation": "Nenhuma resposta foi recebida para os pacotes enviados.",
        "limitation": "ICMP pode ser filtrado; a ausência de resposta não prova que o alvo está indisponível.",
    }
    data.update(overrides)
    return AnalysisFinding(**data)  # type: ignore[arg-type]


def test_severity_has_exactly_expected_members() -> None:
    """Severity possui exatamente INFO, WARNING e CRITICAL."""
    assert {member.name for member in Severity} == {"INFO", "WARNING", "CRITICAL"}


def test_analysis_finding_stores_attributes_as_given() -> None:
    """AnalysisFinding armazena os campos exatamente como informados."""
    finding = AnalysisFinding(
        code="ping.total_loss",
        severity=Severity.CRITICAL,
        summary="Não houve resposta a nenhum pacote.",
        explanation="Nenhuma resposta foi recebida para os pacotes enviados.",
        limitation="A ausência de resposta não prova indisponibilidade do alvo.",
    )

    assert finding.code == "ping.total_loss"
    assert finding.severity is Severity.CRITICAL
    assert finding.summary == "Não houve resposta a nenhum pacote."
    assert finding.explanation == "Nenhuma resposta foi recebida para os pacotes enviados."
    assert finding.limitation == "A ausência de resposta não prova indisponibilidade do alvo."


def test_analysis_finding_accepts_each_severity() -> None:
    """AnalysisFinding aceita qualquer nível de Severity."""
    for severity in Severity:
        assert make_finding(severity=severity).severity is severity


def test_analysis_finding_is_immutable() -> None:
    """A tentativa de alterar um campo levanta FrozenInstanceError."""
    finding = make_finding()

    with pytest.raises(FrozenInstanceError):
        finding.code = "outro.codigo"  # type: ignore[misc]


def test_analysis_finding_equality_by_value() -> None:
    """Dois achados com os mesmos campos são iguais por valor."""
    assert make_finding() == make_finding()
    assert make_finding() != make_finding(severity=Severity.WARNING)


def test_ping_analysis_stores_attributes_as_given() -> None:
    """PingAnalysis armazena target e findings como informados."""
    finding = make_finding()
    analysis = PingAnalysis(target="8.8.8.8", findings=(finding,))

    assert analysis.target == "8.8.8.8"
    assert analysis.findings == (finding,)


def test_ping_analysis_findings_accepts_tuple() -> None:
    """PingAnalysis.findings aceita uma tupla de AnalysisFinding."""
    findings = (make_finding(), make_finding(code="ping.high_latency"))
    analysis = PingAnalysis(target="8.8.8.8", findings=findings)

    assert isinstance(analysis.findings, tuple)
    assert all(isinstance(item, AnalysisFinding) for item in analysis.findings)


def test_ping_analysis_findings_accepts_empty_tuple() -> None:
    """A tupla de achados pode ser vazia."""
    analysis = PingAnalysis(target="8.8.8.8", findings=())

    assert analysis.findings == ()


def test_ping_analysis_is_immutable() -> None:
    """A tentativa de alterar um campo levanta FrozenInstanceError."""
    analysis = PingAnalysis(target="8.8.8.8", findings=())

    with pytest.raises(FrozenInstanceError):
        analysis.target = "1.1.1.1"  # type: ignore[misc]


def test_ping_analysis_equality_by_value() -> None:
    """Duas análises com os mesmos campos são iguais por valor."""
    assert (
        PingAnalysis(target="8.8.8.8", findings=())
        == PingAnalysis(target="8.8.8.8", findings=())
    )
    assert (
        PingAnalysis(target="8.8.8.8", findings=())
        != PingAnalysis(target="1.1.1.1", findings=())
    )