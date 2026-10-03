"""Modelo base da camada de análise.

Este módulo define o contrato mínimo e reutilizável para representar
achados (findings) derivados de evidências de rede já estruturadas.

Ele contém apenas tipos/estruturas de dados: não executa comandos, não
acessa a rede, não faz parsing e não interpreta resultados. As regras de
diagnóstico (o que cada evidência significa) pertencem aos analisadores
específicos de cada diagnóstico, como um futuro ``analyze_ping``.

Os achados são intencionalmente condicionais: cada um descreve o que foi
observado e explicita suas limitações, sem afirmar causa raiz ou conclusões
absolutas sobre a rede.
"""

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Nível de severidade de um achado de análise.

    Os três níveis são deliberadamente poucos e graduados, evitando uma
    classificação binária de "ok/falha".
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AnalysisFinding:
    """Um achado derivado da interpretação de uma evidência de rede.

    Contêiner de dados imutável que representa uma afirmação condicional
    sobre o que foi observado. Ele não executa comandos, não acessa a rede
    e não contém lógica de diagnóstico.

    Campos:

    - ``code``: identificador estável do achado (ex.: ``"ping.total_loss"``).
    - ``severity``: nível de severidade (``Severity``).
    - ``summary``: afirmação curta e condicional sobre o observado.
    - ``explanation``: detalhe do que a evidência sugere.
    - ``limitation``: incerteza ou o que **não** se pode concluir.
    """

    code: str
    severity: Severity
    summary: str
    explanation: str
    limitation: str


@dataclass(frozen=True)
class PingAnalysis:
    """Resultado da análise de uma execução de ping.

    Contêiner de dados imutável que agrega os achados derivados de um
    ``PingResult``. Não executa comandos, não acessa a rede e não contém
    lógica de diagnóstico.

    Campos:

    - ``target``: alvo analisado (o mesmo alvo da evidência de origem).
    - ``findings``: tupla imutável de ``AnalysisFinding``.
    """

    target: str
    findings: tuple[AnalysisFinding, ...]