"""Testes para o parser da saída do pathping.exe.

Estes testes usam strings fixas que imitam a saída real do pathping do Windows
em português. Nenhum teste executa o comando pathping nem acessa a rede.

As saídas abaixo são reconstruídas em múltiplas linhas, como o pathping real as
emite. Os dados (alvos, RTTs, perdas e endereços) vêm dos casos reais fornecidos.
"""

import pytest

from network_diagnostic.models.results import PathpingHop, PathpingResult
from network_diagnostic.parsers.pathping import (
    PathpingParseError,
    parse_pathping_output,
)


# Caso 1: o destino responde. "pathping 100.64.1.172".
PATH_100_64_1_172_OUTPUT = """\
Rastreando a rota para 100.64.1.172 com no máximo 30 saltos

    0  LAPTOP-ASUJKFIE [192.168.1.100]
    1  192.168.1.1
    2  172.17.10.1
    3  100.64.1.172

Calculando estatísticas para 75 segundos...

            Origem aqui      Este nó/Vínculo
             Perdido/Enviado Perdido/Enviado
Salto RTT        = Pct            = Pct       Endereço
    0                                           LAPTOP-ASUJKFIE [192.168.1.100]
                                  0/ 100 =  0%   |
    1    0ms     0/ 100 =  0%     0/ 100 =  0%  192.168.1.1
                                  0/ 100 =  0%   |
    2    2ms     0/ 100 =  0%     0/ 100 =  0%  172.17.10.1
                                  0/ 100 =  0%   |
    3    3ms     0/ 100 =  0%     0/ 100 =  0%  100.64.1.172

Rastreamento concluído.
"""

# Caso 2: o destino não responde. "pathping 100.64.8.9".
PATH_100_64_8_9_OUTPUT = """\
Rastreando a rota para 100.64.8.9 com no máximo 30 saltos

    0  LAPTOP-ASUJKFIE [192.168.1.100]
    1  192.168.1.1
    2  172.17.10.1
    3     *        *        *

Calculando estatísticas para 50 segundos...

            Origem aqui      Este nó/Vínculo
             Perdido/Enviado Perdido/Enviado
Salto RTT        = Pct            = Pct       Endereço
    0                                           LAPTOP-ASUJKFIE [192.168.1.100]
                                  0/ 100 =  0%   |
    1    1ms     0/ 100 =  0%     0/ 100 =  0%  192.168.1.1
                                  0/ 100 =  0%   |
    2    2ms     0/ 100 =  0%     0/ 100 =  0%  172.17.10.1

Rastreamento concluído.
"""


# --- Caso 1: destino responde ----------------------------------------------


def test_case1_target() -> None:
    """O alvo do cabeçalho é usado quando o chamador não informa um."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert result.target == "100.64.1.172"


def test_case1_hop_count() -> None:
    """O caso 1 produz três saltos estatísticos (1, 2 e 3)."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert len(result.hops) == 3


def test_case1_addresses() -> None:
    """Os endereços dos saltos são extraídos na ordem correta."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert [hop.address for hop in result.hops] == [
        "192.168.1.1",
        "172.17.10.1",
        "100.64.1.172",
    ]


def test_case1_rtt() -> None:
    """O RTT de cada salto é convertido para float."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert [hop.rtt_ms for hop in result.hops] == [0.0, 2.0, 3.0]


def test_case1_source_loss() -> None:
    """A coluna 'Origem aqui' vira source_loss_percent."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert [hop.source_loss_percent for hop in result.hops] == [0.0, 0.0, 0.0]


def test_case1_link_loss() -> None:
    """A coluna 'Este nó/Vínculo' vira link_loss_percent."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert [hop.link_loss_percent for hop in result.hops] == [0.0, 0.0, 0.0]


def test_case1_destination_present() -> None:
    """O destino final aparece como último salto."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert result.hops[-1].address == "100.64.1.172"


def test_case1_does_not_include_hop_zero() -> None:
    """O salto 0 (computador de origem) não entra em hops."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    assert all(hop.hop_number != 0 for hop in result.hops)
    assert [hop.hop_number for hop in result.hops] == [1, 2, 3]


# --- Caso 2: destino não responde ------------------------------------------


def test_case2_target() -> None:
    """O alvo do cabeçalho é usado quando o chamador não informa um."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert result.target == "100.64.8.9"


def test_case2_hop_count() -> None:
    """O caso 2 produz apenas dois saltos estatísticos (1 e 2)."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert len(result.hops) == 2


def test_case2_addresses() -> None:
    """Os endereços dos saltos estatísticos são extraídos na ordem correta."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert [hop.address for hop in result.hops] == ["192.168.1.1", "172.17.10.1"]


def test_case2_rtt() -> None:
    """O RTT de cada salto estatístico é convertido para float."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert [hop.rtt_ms for hop in result.hops] == [1.0, 2.0]


def test_case2_losses() -> None:
    """As duas colunas de perda são preservadas separadamente."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert [hop.source_loss_percent for hop in result.hops] == [0.0, 0.0]
    assert [hop.link_loss_percent for hop in result.hops] == [0.0, 0.0]


def test_case2_destination_absent_from_hops() -> None:
    """O destino 100.64.8.9 não aparece como salto estatístico."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert all(hop.address != "100.64.8.9" for hop in result.hops)


def test_case2_no_artificial_hop_three() -> None:
    """O salto 3 ('* * *') não é criado artificialmente."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert all(hop.hop_number != 3 for hop in result.hops)


def test_case2_timeout_not_converted_to_loss() -> None:
    """A ausência de estatística não é convertida em 100% de perda."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    # Nenhum salto estatístico tem 100% de perda inventado a partir de '* * *'.
    assert all(hop.source_loss_percent != 100.0 for hop in result.hops)
    assert all(hop.link_loss_percent != 100.0 for hop in result.hops)


# --- Semântica de target ---------------------------------------------------


def test_explicit_target_prevails_over_header() -> None:
    """O target informado pelo chamador prevalece sobre o do cabeçalho."""
    result = parse_pathping_output(
        PATH_100_64_1_172_OUTPUT, target="10.0.0.1"
    )

    assert result.target == "10.0.0.1"
    assert result.target != "100.64.1.172"


def test_header_target_used_when_caller_omits_target() -> None:
    """Sem target informado, usa o destino do cabeçalho."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    assert result.target == "100.64.8.9"


# --- Saída completa --------------------------------------------------------


def test_full_case1_output() -> None:
    """Valida a saída completa do caso 1."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    expected = PathpingResult(
        target="100.64.1.172",
        hops=[
            PathpingHop(1, 0.0, 0.0, 0.0, "192.168.1.1"),
            PathpingHop(2, 2.0, 0.0, 0.0, "172.17.10.1"),
            PathpingHop(3, 3.0, 0.0, 0.0, "100.64.1.172"),
        ],
    )

    assert result == expected


def test_full_case2_output() -> None:
    """Valida a saída completa do caso 2."""
    result = parse_pathping_output(PATH_100_64_8_9_OUTPUT)

    expected = PathpingResult(
        target="100.64.8.9",
        hops=[
            PathpingHop(1, 1.0, 0.0, 0.0, "192.168.1.1"),
            PathpingHop(2, 2.0, 0.0, 0.0, "172.17.10.1"),
        ],
    )

    assert result == expected


# --- Parser neutro ---------------------------------------------------------


def test_parser_does_not_add_status_fields() -> None:
    """O parser não cria campos de status ou interpretação."""
    result = parse_pathping_output(PATH_100_64_1_172_OUTPUT)

    hop = result.hops[0]
    assert not hasattr(hop, "status")
    assert not hasattr(hop, "severity")
    assert not hasattr(result, "status")


# --- PathpingParseError ----------------------------------------------------


def test_parse_raises_on_non_pathping_output() -> None:
    """Entrada que não é saída de pathping levanta PathpingParseError."""
    output = "isso não é uma saída de pathping"

    with pytest.raises(PathpingParseError):
        parse_pathping_output(output)


def test_parse_header_without_stats_hops_is_valid() -> None:
    """Cabeçalho válido sem saltos estatísticos produz hops == []."""
    output = (
        "Rastreando a rota para 100.64.1.172 com no máximo 30 saltos\n"
        "\n"
        "Rastreamento concluído.\n"
    )

    result = parse_pathping_output(output)

    assert result.hops == []
    assert result.target == "100.64.1.172"