"""Testes para os contratos genéricos da camada de análise.

Estes testes validam o comportamento observável dos contêineres genéricos de
dados: os níveis de ``Severity``, a criação correta, a imutabilidade e a
igualdade por valor de ``AnalysisFinding``. Eles não testam execução de
diagnóstico nem parsing. Os contêineres específicos de cada diagnóstico (por
exemplo, ``PingAnalysis``) são testados nos seus próprios módulos.
"""

from dataclasses import FrozenInstanceError

import pytest

from network_diagnostic.analysis.findings import (
    AnalysisFinding,
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
