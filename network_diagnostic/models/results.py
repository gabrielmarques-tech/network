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


@dataclass(frozen=True)
class HopResult:
    """Resultado estruturado de um único salto de traceroute.

    Contêiner de dados simples que representa a evidência coletada de um salto
    do tracert.exe do Windows. Não executa comandos, não faz parsing da saída e
    não interpreta os resultados.
    """

    hop_number: int
    rtts_ms: list[float | None]
    address: str | None
    hostname: str | None


@dataclass(frozen=True)
class TracerouteResult:
    """Resultado estruturado de uma execução de traceroute.

    Contêiner de dados simples que representa as evidências coletadas a partir
    de um comando de traceroute. Não executa o comando, não faz parsing da sua
    saída e não analisa os resultados.
    """

    target: str
    max_hops: int
    hops: list[HopResult]


@dataclass(frozen=True)
class PathpingHop:
    """Resultado estruturado das estatísticas de um único salto do pathping.

    Contêiner de dados simples que representa a evidência coletada da seção de
    estatísticas do pathping.exe do Windows. Não executa comandos, não faz
    parsing da saída e não interpreta os resultados.

    As duas colunas de perda são mantidas separadas porque representam medições
    diferentes:

    - ``source_loss_percent`` corresponde à coluna "Origem aqui" (perda
      acumulada da origem até este salto).
    - ``link_loss_percent`` corresponde à coluna "Este nó/Vínculo" (perda
      observada especificamente neste nó ou vínculo).
    """

    hop_number: int
    rtt_ms: float | None
    source_loss_percent: float | None
    link_loss_percent: float | None
    address: str | None


@dataclass(frozen=True)
class PathpingResult:
    """Resultado estruturado de uma execução de pathping.

    Contêiner de dados simples que representa as evidências coletadas a partir
    da seção de estatísticas de um comando pathping. Não executa o comando, não
    faz parsing da sua saída e não analisa os resultados.

    ``hops`` contém apenas os saltos com estatísticas (a partir do salto 1). O
    salto 0, que representa o próprio computador de origem, não é incluído.
    """

    target: str
    hops: list[PathpingHop]