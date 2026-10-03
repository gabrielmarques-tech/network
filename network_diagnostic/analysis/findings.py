"""Contratos genéricos da camada de análise.

Este módulo define o vocabulário mínimo e reutilizável para representar
achados (findings) derivados de evidências de rede já estruturadas:
``Severity`` e ``AnalysisFinding``.

Ele contém apenas tipos/estruturas de dados genéricos, comuns a todos os
diagnósticos: não executa comandos, não acessa a rede, não faz parsing e não
interpreta resultados. As regras de diagnóstico e os agregados específicos de
cada diagnóstico pertencem aos seus próprios módulos (por exemplo,
``analyze_ping`` e ``PingAnalysis`` em ``network_diagnostic.analysis.ping``).
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
