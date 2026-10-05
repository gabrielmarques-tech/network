"""Testes da camada de apresentação gráfica (GUI).

Estes testes validam apenas a lógica testável sem depender de uma janela
gráfica real: a função ``run_ping_diagnosis``, que é executada pela worker
thread. Verificam que ela chama a camada de aplicação, reutiliza o formatador
de texto existente e converte as exceções de domínio em mensagens na fila.

Nenhum teste executa ping real nem cria uma janela Tkinter. A camada de
aplicação (``diagnose_and_analyze_ping``) é substituída por mock via
monkeypatch.
"""

import queue

import pytest

from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.parsers.ping import PingParseError
from network_diagnostic.presentation import gui


def _fake_ping_analysis(target: str = "8.8.8.8") -> PingAnalysis:
    """Cria um PingAnalysis fictício, sem executar diagnóstico nem análise."""
    return PingAnalysis(
        target=target,
        packets_sent=4,
        packets_received=4,
        packet_loss_percent=0.0,
        min_latency_ms=2.0,
        avg_latency_ms=3.0,
        max_latency_ms=4.0,
        findings=(),
    )


def test_worker_repassa_target_e_exibe_resultado(monkeypatch) -> None:
    """O destino é repassado à aplicação e o PingAnalysis vai para a fila."""
    captured: dict[str, object] = {}
    result_queue: "queue.Queue[tuple[str, PingAnalysis | str]]" = queue.Queue()

    def fake_diagnose(target):
        captured["target"] = target
        return _fake_ping_analysis(target)

    monkeypatch.setattr(gui, "diagnose_and_analyze_ping", fake_diagnose)

    gui.run_ping_diagnosis("1.1.1.1", result_queue)

    kind, payload = result_queue.get_nowait()
    assert captured["target"] == "1.1.1.1"
    assert kind == "ok"
    assert payload == _fake_ping_analysis("1.1.1.1")
    assert result_queue.empty()


def test_worker_converte_erro_de_execucao(monkeypatch) -> None:
    """PingExecutionError vira uma mensagem de erro na fila."""
    message = "O comando 'ping' não foi encontrado no sistema."
    result_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

    def fake_diagnose(target):
        raise PingExecutionError(message)

    monkeypatch.setattr(gui, "diagnose_and_analyze_ping", fake_diagnose)

    gui.run_ping_diagnosis("8.8.8.8", result_queue)

    kind, text = result_queue.get_nowait()
    assert kind == "error"
    assert text == message


def test_worker_converte_erro_de_parsing(monkeypatch) -> None:
    """PingParseError vira uma mensagem de erro na fila."""
    message = "Não foi possível interpretar a saída do ping para '8.8.8.8'."
    result_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

    def fake_diagnose(target):
        raise PingParseError(message)

    monkeypatch.setattr(gui, "diagnose_and_analyze_ping", fake_diagnose)

    gui.run_ping_diagnosis("8.8.8.8", result_queue)

    kind, text = result_queue.get_nowait()
    assert kind == "error"
    assert text == message


def test_worker_nao_captura_excecoes_inesperadas(monkeypatch) -> None:
    """Exceções fora do domínio de ping são propagadas, não escondidas."""
    result_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

    def fake_diagnose(target):
        raise ValueError("falha inesperada")

    monkeypatch.setattr(gui, "diagnose_and_analyze_ping", fake_diagnose)

    with pytest.raises(ValueError):
        gui.run_ping_diagnosis("8.8.8.8", result_queue)

    assert result_queue.empty()
