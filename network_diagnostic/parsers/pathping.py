"""Parser da saída do pathping.exe (Windows) em um PathpingResult.

Este módulo é responsável apenas por transformar o texto da saída do pathping
em um modelo estruturado. Ele não executa o comando, não acessa a rede e não
interpreta os dados: qualquer conclusão sobre a rede pertence à camada de
análise.

Idioma e acoplamento (importante):

- O parsing dos *saltos* é baseado na estrutura das linhas da seção de
  estatísticas (número do salto seguido de RTT e duas colunas de perda) e
  **não** depende das frases em português.
- O parsing do *cabeçalho* atualmente considera o formato PT-BR do pathping do
  Windows (por exemplo, "Rastreando a rota para ... com no máximo N saltos").
- Suporte a outros idiomas fica **fora do escopo da V1**.

Convenções importantes:

- A seção de estatísticas do pathping lista apenas os saltos que responderam.
  Um salto que aparece como ``* * *`` na seção de rota **não** gera um
  ``PathpingHop``: a ausência de estatística permanece como ausência de
  estatística e não é convertida em 100% de perda.
- O salto 0 representa o próprio computador de origem e **não** é incluído em
  ``PathpingResult.hops``, que começa no salto 1.
- As duas colunas de perda não são combinadas: a primeira vira
  ``source_loss_percent`` e a segunda vira ``link_loss_percent``.
- ``PathpingResult.target`` representa sempre o destino informado pelo
  chamador (o alvo solicitado ao diagnóstico). O endereço do cabeçalho nunca
  sobrescreve o alvo.
"""

import re

from network_diagnostic.models.results import PathpingHop, PathpingResult


class PathpingParseError(Exception):
    """Erro levantado quando a saída do pathping não pode ser interpretada.

    Representa apenas falha de interpretação do formato da saída, nunca uma
    falha de rede. Não carrega conclusões como "o destino não respondeu" ou
    "o vínculo está com perda"; tais conclusões pertencem à camada de análise.
    """


# Linha de salto da seção de estatísticas:
#   "   1    0ms     0/ 100 =  0%     0/ 100 =  0%  192.168.1.1"
# Estrutura: número do salto, RTT em ms e duas colunas "Perdido/Enviado = Pct%".
# O padrão exige o RTT ("Nms"), o que exclui naturalmente:
#   - o salto 0 (sem RTT na mesma linha);
#   - as linhas de vínculo (que não começam com o número do salto e possuem
#     apenas a segunda coluna seguida de "|");
#   - as linhas da seção de rota (apenas número do salto e endereço).
_STATS_HOP_PATTERN = re.compile(
    r"^\s*(?P<hop_number>\d+)\s+"
    r"(?P<rtt><?\s*\d+)\s*ms\s+"
    r"\d+\s*/\s*\d+\s*=\s*(?P<source_pct>\d+)\s*%\s+"
    r"\d+\s*/\s*\d+\s*=\s*(?P<link_pct>\d+)\s*%"
    r"(?P<address>.*)$"
)

# Cabeçalho: "Rastreando a rota para 100.64.1.172 com no máximo 30 saltos".
# A captura do alvo usa "hostname [IP]" ou o texto antes de " com ". O padrão é
# ancorado em "para" apenas como pista; a extração do alvo é estrutural.
_HEADER_TARGET_PATTERN = re.compile(
    r"para\s+(?P<target>\S+)(?:\s*\[\s*[^\]]+?\s*\])?\s+com\s+"
    r"(?:no\s+m[aá]ximo(?:\s+de)?\s+)?\d+\s+salto",
    re.IGNORECASE,
)


def _parse_rtt(token: str) -> float | None:
    """Converte o token de RTT da seção de estatísticas em um valor numérico.

    ``<1 ms`` vira ``0.0`` (convenção: inferior a 1 ms). ``11 ms`` vira
    ``11.0``. Retorna ``None`` se o token não contiver um número.
    """
    token = token.strip()
    if token.startswith("<"):
        return 0.0
    number_match = re.search(r"\d+", token)
    if number_match is None:
        return None
    return float(number_match.group())


def _parse_stats_hop_line(line: str) -> PathpingHop | None:
    """Converte uma linha de estatística em PathpingHop, ou None se não for.

    Retorna ``None`` para qualquer linha que não seja um salto com
    estatísticas, o que inclui o salto 0 e as linhas de vínculo (marcadas
    com ``|``).
    """
    match = _STATS_HOP_PATTERN.match(line)
    if match is None:
        return None

    address = match.group("address").strip()

    return PathpingHop(
        hop_number=int(match.group("hop_number")),
        rtt_ms=_parse_rtt(match.group("rtt")),
        source_loss_percent=float(match.group("source_pct")),
        link_loss_percent=float(match.group("link_pct")),
        address=address or None,
    )


def _parse_header_target(output: str) -> str | None:
    """Extrai o destino do cabeçalho PT-BR do pathping.

    Retorna ``None`` quando o cabeçalho não é reconhecido. O valor extraído é
    apenas uma reserva: ele só é usado como ``PathpingResult.target`` quando o
    chamador não informa um alvo.
    """
    header_match = _HEADER_TARGET_PATTERN.search(output)
    if header_match is None:
        return None
    return header_match.group("target")


def parse_pathping_output(
    output: str, target: str | None = None
) -> PathpingResult:
    """Converte a saída do pathping.exe em um PathpingResult.

    É uma função pura: recebe o texto da saída e devolve o modelo, sem executar
    comandos nem acessar a rede. Linhas que não representam saltos com
    estatísticas (cabeçalho, seção de rota, linhas de vínculo, rodapé e linhas
    em branco) são ignoradas.

    Semântica de ``target``:

    - O ``target`` informado pelo chamador tem **precedência** e representa o
      destino solicitado ao diagnóstico.
    - O endereço presente no cabeçalho **nunca** sobrescreve o alvo informado;
      ele só é usado como reserva quando ``target`` é ``None``.

    Reconhecimento do formato:

    - Uma saída com pelo menos um salto de estatística reconhecido é válida.
    - Uma saída com cabeçalho reconhecido mas sem saltos de estatística é
      válida e produz ``hops == []``.
    - Se **nem** saltos **nem** cabeçalho forem reconhecidos, levanta
      ``PathpingParseError`` (falha de formato, não de rede).
    """
    hops: list[PathpingHop] = []
    for line in output.splitlines():
        hop = _parse_stats_hop_line(line)
        if hop is not None:
            hops.append(hop)

    header_target = _parse_header_target(output)

    # Sem saltos e sem cabeçalho reconhecido: a entrada não é saída de pathping.
    # É uma falha de interpretação do formato, não uma conclusão sobre a rede.
    if not hops and header_target is None:
        raise PathpingParseError(
            "A saída não contém um cabeçalho ou salto reconhecível do pathping."
        )

    # Precedência: alvo informado pelo chamador > alvo do cabeçalho.
    if target is not None:
        resolved_target = target
    elif header_target is not None:
        resolved_target = header_target
    else:
        resolved_target = ""

    return PathpingResult(
        target=resolved_target,
        hops=hops,
    )