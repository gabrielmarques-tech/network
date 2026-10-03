"""Parser da saída do tracert.exe (Windows) em um TracerouteResult.

Este módulo é responsável apenas por transformar o texto da saída do tracert
em um modelo estruturado. Ele não executa o comando, não acessa a rede e não
interpreta os dados: qualquer conclusão sobre a rede pertence à camada de
análise.

Idioma e acoplamento (importante):

- O parsing dos *hops* é baseado na estrutura da linha (número do salto no
  início seguido de três medições RTT) e **não** depende das frases em
  português.
- O parsing do *cabeçalho* atualmente considera o formato PT-BR do tracert do
  Windows (por exemplo, "Rastreando a rota para ... com no máximo N saltos:").
- Suporte a outros idiomas fica **fora do escopo da V1**.

Convenções importantes:

- ``0.0`` representa uma medição "inferior a 1 ms" (a saída mostra ``<1 ms``).
  Não significa latência exatamente zero.
- ``None`` em ``rtts_ms`` representa uma medição sem resposta (``*``).
- ``TracerouteResult.target`` representa sempre o destino informado pelo
  chamador (o alvo solicitado ao diagnóstico). O hostname resolvido que aparece
  no cabeçalho nunca sobrescreve o alvo.
"""

import re

from network_diagnostic.models.results import HopResult, TracerouteResult


class TracerouteParseError(Exception):
    """Erro levantado quando a saída do tracert não pode ser interpretada.

    Representa apenas falha de interpretação do formato da saída, nunca uma
    falha de rede. Não carrega conclusões como "todos os hops falharam" ou
    "a rede está fora"; tais conclusões pertencem à camada de análise.
    """


# Uma medição RTT individual: pode ser "*" (sem resposta) ou um tempo em ms,
# possivelmente prefixado por "<" para indicar "inferior a 1 ms".
_RTT_TOKEN = r"(?:\*|<\s*\d+\s*ms|\d+\s*ms)"

# Linha de hop: começa com o número do salto seguido de três medições RTT.
# Ex.: "1     1 ms     1 ms     1 ms  192.168.1.1"
# Ex.: "3     *        *        *     Esgotado o tempo limite do pedido."
# Ex.: "5     *       11 ms     3 ms  187-108-238-169.ufinet.com [187.108.238.169]"
HOP_PATTERN = re.compile(
    rf"^\s*(?P<hop_number>\d+)\s+"
    rf"(?P<rtt1>{_RTT_TOKEN})\s+"
    rf"(?P<rtt2>{_RTT_TOKEN})\s+"
    rf"(?P<rtt3>{_RTT_TOKEN})"
    rf"(?P<rest>.*)$"
)

# Hostname seguido do IP entre colchetes: "hostname [IP]".
HOSTNAME_ADDRESS_PATTERN = re.compile(
    r"(?P<hostname>\S+)\s*\[\s*(?P<address>[^\]]+?)\s*\]"
)

# Apenas um IP IPv4 isolado.
IPV4_PATTERN = re.compile(r"\b(?P<address>\d{1,3}(?:\.\d{1,3}){3})\b")

# Cabeçalho: "Rastreando a rota para dns.google [8.8.8.8] com no máximo 30 saltos:"
# A captura do alvo usa "hostname [IP]" ou o texto antes de " com ". O padrão é
# ancorado em "para" apenas como pista; a extração do alvo é estrutural.
HEADER_TARGET_PATTERN = re.compile(
    r"para\s+(?P<target>\S+)(?:\s*\[\s*[^\]]+?\s*\])?\s+com\s+"
    r"(?:no\s+m[aá]ximo(?:\s+de)?\s+)?(?P<max_hops>\d+)\s+salto",
    re.IGNORECASE,
)


def _parse_rtt(token: str) -> float | None:
    """Converte um token de medição RTT em um valor numérico.

    ``*`` vira ``None`` (sem resposta). ``<1 ms`` vira ``0.0`` (convenção:
    inferior a 1 ms). ``11 ms`` vira ``11.0``.
    """
    token = token.strip()
    if token == "*":
        return None
    # "<1 ms" -> 0.0 (inferior a 1 ms).
    if token.startswith("<"):
        return 0.0
    number_match = re.search(r"\d+", token)
    if number_match is None:
        return None
    return float(number_match.group())


def _parse_host_and_address(rest: str) -> tuple[str | None, str | None]:
    """Extrai (hostname, address) a partir do restante da linha de hop.

    Retorna ``("dns.google", "8.8.8.8")`` para ``dns.google [8.8.8.8]`` e
    ``(None, "192.168.1.1")`` para apenas um IP. Quando nada é reconhecido,
    retorna ``(None, None)``.
    """
    rest = rest.strip()
    if not rest:
        return None, None

    host_match = HOSTNAME_ADDRESS_PATTERN.search(rest)
    if host_match is not None:
        hostname = host_match.group("hostname").strip()
        address = host_match.group("address").strip()
        return hostname, address

    ip_match = IPV4_PATTERN.search(rest)
    if ip_match is not None:
        return None, ip_match.group("address")

    return None, None


def _parse_hop_line(line: str) -> HopResult | None:
    """Converte uma linha de hop em HopResult, ou None se não for um hop."""
    match = HOP_PATTERN.match(line)
    if match is None:
        return None

    hop_number = int(match.group("hop_number"))
    rtts_ms = [
        _parse_rtt(match.group("rtt1")),
        _parse_rtt(match.group("rtt2")),
        _parse_rtt(match.group("rtt3")),
    ]
    hostname, address = _parse_host_and_address(match.group("rest"))

    return HopResult(
        hop_number=hop_number,
        rtts_ms=rtts_ms,
        address=address,
        hostname=hostname,
    )


def _parse_header(output: str) -> tuple[str | None, int | None]:
    """Extrai (header_target, max_hops) do cabeçalho PT-BR do tracert.

    Retorna ``(None, None)`` quando o cabeçalho não é reconhecido. O
    ``header_target`` é apenas um valor de reserva: ele só é usado como
    ``TracerouteResult.target`` quando o chamador não informa um alvo.
    """
    header_match = HEADER_TARGET_PATTERN.search(output)
    if header_match is None:
        return None, None

    header_target = header_match.group("target")
    max_hops = int(header_match.group("max_hops"))
    return header_target, max_hops


def parse_traceroute_output(
    output: str, target: str | None = None
) -> TracerouteResult:
    """Converte a saída do tracert.exe em um TracerouteResult.

    É uma função pura: recebe o texto da saída e devolve o modelo, sem executar
    comandos nem acessar a rede. Linhas que não representam saltos (cabeçalho,
    mensagem final, linhas em branco) são ignoradas.

    Semântica de ``target``:

    - O ``target`` informado pelo chamador tem **precedência** e representa o
      destino solicitado ao diagnóstico.
    - O hostname resolvido presente no cabeçalho **nunca** sobrescreve o alvo
      informado; ele só é usado como reserva quando ``target`` é ``None``.

    Reconhecimento do formato:

    - Uma saída com pelo menos um hop reconhecido é sempre válida, mesmo que
      todos os RTTs sejam ``*`` (sem resposta).
    - Uma saída com cabeçalho reconhecido mas sem hops é válida e produz
      ``hops == []``.
    - Se **nem** hops **nem** cabeçalho forem reconhecidos, levanta
      ``TracerouteParseError`` (falha de formato, não de rede).
    """
    hops: list[HopResult] = []
    for line in output.splitlines():
        hop = _parse_hop_line(line)
        if hop is not None:
            hops.append(hop)

    header_target, header_max_hops = _parse_header(output)

    # Sem hops e sem cabeçalho reconhecido: a entrada não é saída de tracert.
    # É uma falha de interpretação do formato, não uma conclusão sobre a rede.
    if not hops and header_target is None:
        raise TracerouteParseError(
            "A saída não contém um cabeçalho ou hop reconhecível do tracert."
        )

    # Precedência: alvo informado pelo chamador > alvo do cabeçalho.
    if target is not None:
        resolved_target = target
    elif header_target is not None:
        resolved_target = header_target
    else:
        resolved_target = ""

    resolved_max_hops = header_max_hops if header_max_hops is not None else 30

    return TracerouteResult(
        target=resolved_target,
        max_hops=resolved_max_hops,
        hops=hops,
    )
