"""Modelos de dados para os resultados de diagnóstico de rede.

Este módulo define contêineres estruturados que representam as evidências
coletadas pela camada de diagnóstico. Os modelos são intencionalmente mantidos
como contêineres de dados simples e imutáveis: eles não executam comandos, não
fazem parsing da saída e não interpretam os resultados.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PingResult:
    """Resultado estruturado de uma execução de ping.

    Este é um contêiner de dados simples que representa as evidências coletadas
    a partir de um comando de ping. Ele não executa o comando, não faz parsing da
    sua saída e não analisa os resultados.
    """

    target: str
    packets_sent: int
    packets_received: int
    packet_loss_percent: float
    min_latency_ms: float | None
    avg_latency_ms: float | None
    max_latency_ms: float | None
    rtts_ms: list[float]

    @property
    def success(self) -> bool:
        """Indica se o ping recebeu ao menos uma resposta válida."""
        return self.packets_received > 0