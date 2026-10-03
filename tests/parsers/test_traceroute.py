"""Testes para o parser da saída do tracert.exe.

Estes testes usam strings fixas que imitam a saída real do tracert do Windows
em português. Nenhum teste executa o comando tracert nem acessa a rede.
"""

import pytest

from network_diagnostic.models.results import HopResult, TracerouteResult
from network_diagnostic.parsers.traceroute import (
    TracerouteParseError,
    parse_traceroute_output,
)


# Saída semelhante à capturada de "tracert -4 8.8.8.8".
TRACERT_8_8_8_8_OUTPUT = """\
Rastreando a rota para dns.google [8.8.8.8] com no máximo 30 saltos:

  1     1 ms     1 ms     1 ms  192.168.1.1
  2     3 ms     2 ms     2 ms  10.0.0.1
  3     *        *        *     Esgotado o tempo limite do pedido.
  4     *       11 ms     3 ms  187-108-238-169.ufinet.com [187.108.238.169]
  5     6 ms     3 ms     3 ms  72.14.219.181
  6     7 ms     6 ms     8 ms  8.8.8.8

Rastreamento concluído.
"""

# Saída semelhante à capturada de "tracert google.com".
TRACERT_GOOGLE_OUTPUT = """\
Rastreando a rota para google.com [142.250.79.142] com no máximo 30 saltos:

  1     <1 ms    <1 ms    <1 ms  192.168.1.1
  2     2 ms     2 ms     2 ms  10.0.0.1
  3    11 ms    10 ms    12 ms  dns.google [8.8.8.8]
  4     *        *        *     Esgotado o tempo limite do pedido.
  5    13 ms    12 ms    14 ms  142.250.79.142

Rastreamento concluído.
"""


def test_parse_three_normal_rtts() -> None:
    """Um hop com três RTTs normais é convertido para floats."""
    output = "1     1 ms     1 ms     1 ms  192.168.1.1"

    result = parse_traceroute_output(output)

    assert result.hops[0].rtts_ms == [1.0, 1.0, 1.0]


def test_parse_sub_millisecond_rtt_becomes_zero() -> None:
    """<1 ms vira 0.0, representando 'inferior a 1 ms'."""
    output = "1     1 ms    <1 ms    <1 ms  192.168.1.1"

    result = parse_traceroute_output(output)

    assert result.hops[0].rtts_ms == [1.0, 0.0, 0.0]


def test_parse_full_timeout_gives_three_none() -> None:
    """'* * *' produz rtts_ms=[None, None, None] e sem endereço."""
    output = "3     *        *        *     Esgotado o tempo limite do pedido."

    result = parse_traceroute_output(output)

    hop = result.hops[0]
    assert hop.rtts_ms == [None, None, None]
    assert hop.address is None
    assert hop.hostname is None


def test_parse_partial_timeout_with_hostname_and_address() -> None:
    """Timeout parcial mantém None na posição e extrai hostname e IP."""
    output = (
        "5     *       11 ms     3 ms  "
        "187-108-238-169.ufinet.com [187.108.238.169]"
    )

    result = parse_traceroute_output(output)

    hop = result.hops[0]
    assert hop.rtts_ms == [None, 11.0, 3.0]
    assert hop.hostname == "187-108-238-169.ufinet.com"
    assert hop.address == "187.108.238.169"


def test_parse_only_ip() -> None:
    """Um hop com apenas IP produz hostname=None e address preenchido."""
    output = "6     3 ms     3 ms     3 ms  72.14.219.181"

    result = parse_traceroute_output(output)

    hop = result.hops[0]
    assert hop.hostname is None
    assert hop.address == "72.14.219.181"


def test_parse_hostname_and_address() -> None:
    """Um hop no formato 'hostname [IP]' extrai ambos os campos."""
    output = "10     4 ms     3 ms     4 ms  dns.google [8.8.8.8]"

    result = parse_traceroute_output(output)

    hop = result.hops[0]
    assert hop.hostname == "dns.google"
    assert hop.address == "8.8.8.8"


def test_parse_preserves_hop_order() -> None:
    """A ordem dos saltos na saída é preservada na lista de hops."""
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT)

    assert [hop.hop_number for hop in result.hops] == [1, 2, 3, 4, 5, 6]


def test_parse_header_with_hostname_and_ip() -> None:
    """O cabeçalho extrai o alvo (hostname) e o limite de saltos."""
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT)

    assert result.target == "dns.google"
    assert result.max_hops == 30


def test_parse_header_target() -> None:
    """O alvo informado no cabeçalho é preservado em TracerouteResult.target."""
    result = parse_traceroute_output(TRACERT_GOOGLE_OUTPUT)

    assert result.target == "google.com"


def test_parse_ignores_unrelated_lines() -> None:
    """Linhas de cabeçalho, rodapé e vazias não viram hops."""
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT)

    # Nenhuma linha não-hop deve virar HopResult.
    assert len(result.hops) == 6
    assert all(isinstance(hop, HopResult) for hop in result.hops)


def test_parse_empty_hops() -> None:
    """Saída sem linhas de hop produz lista vazia de hops."""
    output = (
        "Rastreando a rota para dns.google [8.8.8.8] com no máximo 30 saltos:\n"
        "\n"
        "Rastreamento concluído.\n"
    )

    result = parse_traceroute_output(output)

    assert result.hops == []


def test_parse_multiple_hops() -> None:
    """Uma saída com múltiplos hops gera o mesmo número de HopResult."""
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT)

    assert len(result.hops) == 6


def test_parse_does_not_interpret_timeout_as_network_failure() -> None:
    """Um hop com '*' é representado como None, sem inferir falha de rede."""
    output = "3     *        *        *     Esgotado o tempo limite do pedido."

    result = parse_traceroute_output(output)

    hop = result.hops[0]
    # O parser apenas representa a evidência observada.
    assert hop.rtts_ms == [None, None, None]
    assert hop.address is None
    assert not hasattr(hop, "failed")
    assert not hasattr(hop, "is_failure")


def test_parse_full_8_8_8_8_output() -> None:
    """Valida a saída completa semelhante ao tracert 8.8.8.8."""
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT)

    expected = TracerouteResult(
        target="dns.google",
        max_hops=30,
        hops=[
            HopResult(1, [1.0, 1.0, 1.0], "192.168.1.1", None),
            HopResult(2, [3.0, 2.0, 2.0], "10.0.0.1", None),
            HopResult(3, [None, None, None], None, None),
            HopResult(
                4,
                [None, 11.0, 3.0],
                "187.108.238.169",
                "187-108-238-169.ufinet.com",
            ),
            HopResult(5, [6.0, 3.0, 3.0], "72.14.219.181", None),
            HopResult(6, [7.0, 6.0, 8.0], "8.8.8.8", None),
        ],
    )

    assert result == expected


def test_parse_full_google_output() -> None:
    """Valida a saída completa semelhante ao tracert google.com."""
    result = parse_traceroute_output(TRACERT_GOOGLE_OUTPUT)

    expected = TracerouteResult(
        target="google.com",
        max_hops=30,
        hops=[
            HopResult(1, [0.0, 0.0, 0.0], "192.168.1.1", None),
            HopResult(2, [2.0, 2.0, 2.0], "10.0.0.1", None),
            HopResult(3, [11.0, 10.0, 12.0], "8.8.8.8", "dns.google"),
            HopResult(4, [None, None, None], None, None),
            HopResult(5, [13.0, 12.0, 14.0], "142.250.79.142", None),
        ],
    )

    assert result == expected


def test_parse_falls_back_to_provided_target() -> None:
    """Sem cabeçalho reconhecível, usa o target informado pelo chamador."""
    output = "1     1 ms     1 ms     1 ms  192.168.1.1"

    result = parse_traceroute_output(output, target="8.8.8.8")

    assert result.target == "8.8.8.8"


# --- Semântica de target ---------------------------------------------------
# Contrato de TracerouteResult.target:
# - o target informado pelo chamador sempre prevalece;
# - o hostname resolvido do cabeçalho nunca sobrescreve o target informado;
# - o destino extraído do cabeçalho só é usado como fallback quando
#   target é None.


def test_parse_explicit_target_prevails_over_header_hostname_and_ip() -> None:
    """Caso 1: com cabeçalho 'dns.google [8.8.8.8]', o target informado vence."""
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT, target="8.8.8.8")

    assert result.target == "8.8.8.8"


def test_parse_explicit_target_prevails_with_google_output() -> None:
    """Caso 2: com a saída do Google, o target informado vence o cabeçalho."""
    result = parse_traceroute_output(TRACERT_GOOGLE_OUTPUT, target="google.com")

    assert result.target == "google.com"


def test_parse_header_target_used_when_caller_omits_target() -> None:
    """Caso 3: sem target informado, usa o destino do cabeçalho como fallback."""
    result = parse_traceroute_output(TRACERT_GOOGLE_OUTPUT)

    assert result.target == "google.com"


def test_parse_explicit_target_differs_from_resolved_header_hostname() -> None:
    """Caso 4: o target do chamador prevalece mesmo diferente do hostname.

    O cabeçalho contém o hostname resolvido ``dns.google``, mas o chamador
    informou ``"8.8.8.8"``. O valor do argumento é o contrato de
    ``TracerouteResult.target``; o hostname resolvido do cabeçalho não o
    substitui.
    """
    result = parse_traceroute_output(TRACERT_8_8_8_8_OUTPUT, target="8.8.8.8")

    assert result.target == "8.8.8.8"
    assert result.target != "dns.google"

# --- TracerouteParseError --------------------------------------------------
# A exceção representa apenas falha de interpretação do formato da saída.
# Ela NÃO é levantada quando há um cabeçalho reconhecido (mesmo sem hops) nem
# quando há ao menos um hop reconhecido (mesmo sem resposta).


def test_parse_raises_on_non_tracert_output() -> None:
    """Entrada que não é saída de tracert levanta TracerouteParseError."""
    output = "isso não é uma saída de tracert"

    with pytest.raises(TracerouteParseError):
        parse_traceroute_output(output)


def test_parse_header_without_hops_is_valid() -> None:
    """Cabeçalho válido sem hops é válido e produz hops == [] (sem exceção)."""
    output = (
        "Rastreando a rota para dns.google [8.8.8.8] com no máximo 30 saltos:\n"
        "\n"
        "Rastreamento concluído.\n"
    )

    result = parse_traceroute_output(output)

    assert result.hops == []
    assert result.target == "dns.google"
    assert result.max_hops == 30


def test_parse_all_timeout_hop_is_valid() -> None:
    """Hop totalmente sem resposta é válido e não levanta exceção."""
    output = "3     *        *        *     Esgotado o tempo limite do pedido."

    result = parse_traceroute_output(output)

    assert len(result.hops) == 1
    hop = result.hops[0]
    assert hop.hop_number == 3
    assert hop.rtts_ms == [None, None, None]
