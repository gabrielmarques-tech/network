"""Interface gráfica (V2) do Network Diagnostic Tool.

Este módulo é uma camada de apresentação: monta uma janela Tkinter/ttk que
permite informar um destino (IP ou hostname) e executar o diagnóstico de
``ping``, exibindo o resultado de forma estruturada. Ele não executa
subprocess, não faz parsing e não interpreta a rede: essas responsabilidades
continuam nas camadas já existentes.

Fluxo:

    campo de destino
        → diagnose_and_analyze_ping()  (camada de aplicação)
        → PingAnalysis                 (objeto trafegado pela fila)
        → format_ping_analysis()       (bloco de detalhes em texto)
        → widgets da janela            (faixa de estado, cartões e achados)

O diagnóstico roda em uma *worker thread* para não congelar a interface. A
thread de trabalho não acessa widgets do Tkinter: ela apenas deposita o
``PingAnalysis`` (em caso de sucesso) ou a mensagem de erro (em caso de
falha de domínio) em uma ``queue.Queue``. A thread principal verifica essa
fila periodicamente com ``root.after(...)`` e atualiza a interface.

Esta versão exibe apenas o diagnóstico de ping. Traceroute e pathping
permanecem fora do escopo desta etapa.
"""

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from network_diagnostic.analysis.findings import AnalysisFinding, Severity
from network_diagnostic.analysis.ping import PingAnalysis
from network_diagnostic.application.ping import diagnose_and_analyze_ping
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.parsers.ping import PingParseError
from network_diagnostic.presentation.text import format_ping_analysis

# Intervalo (em milissegundos) com que a thread principal verifica a fila de
# resultados em busca de uma resposta da worker thread.
_POLL_INTERVAL_MS = 100

# Identificadores do tipo de mensagem trafegada na fila. Em sucesso, o
# conteúdo é o ``PingAnalysis``; em erro, é a mensagem textual do domínio.
_KIND_OK = "ok"
_KIND_ERROR = "error"

# Marcador textual exibido quando um valor numérico está indisponível. A GUI
# não inventa números: mostra explicitamente que o valor não existe.
_UNAVAILABLE = "—"

# Cores da faixa de estado. O sucesso é deliberadamente neutro (cinza), não
# verde: a apresentação não deve sugerir interpretação que a análise não fez.
_STATUS_NEUTRAL_COLOR = "#333333"
_STATUS_ERROR_COLOR = "#cc0000"

# Apresentação visual de cada severidade: marcador, rótulo em português e
# cor. A severidade vem exclusivamente do campo ``Severity`` do achado; a GUI
# não cria nem reclassifica severidade.
_SEVERITY_STYLES: dict[Severity, tuple[str, str, str]] = {
    Severity.INFO: ("●", "Informativo", "#555555"),
    Severity.WARNING: ("▲", "Atenção", "#b8860b"),
    Severity.CRITICAL: ("■", "Crítico", "#cc0000"),
}

# Largura de quebra de linha (em pixels) para o resumo de cada achado.
_FINDING_SUMMARY_WRAP = 520

# Fonte dos valores numéricos exibidos nos cartões de resumo. É apenas
# destaque visual; o conteúdo continua vindo exclusivamente da análise.
_CARD_VALUE_FONT = ("TkDefaultFont", 14, "bold")


def run_ping_diagnosis(
    target: str,
    result_queue: "queue.Queue[tuple[str, PingAnalysis | str]]",
) -> None:
    """Executa o diagnóstico de ping e deposita o resultado na fila.

    Esta é a função alvo da *worker thread*. Ela não acessa widgets do
    Tkinter: apenas chama a camada de aplicação e coloca o objeto devolvido
    na ``result_queue``.

    Em caso de sucesso coloca ``("ok", analysis)`` — o ``PingAnalysis`` já
    pronto, sem formatar texto. Em caso de erro de execução ou de parsing
    coloca ``("error", mensagem)``. Assim como a CLI, captura apenas as
    exceções do domínio de ping (``PingExecutionError`` e ``PingParseError``);
    as demais exceções são propagadas, para não esconder falhas.
    """
    try:
        analysis = diagnose_and_analyze_ping(target)
    except (PingExecutionError, PingParseError) as error:
        result_queue.put((_KIND_ERROR, str(error)))
        return

    result_queue.put((_KIND_OK, analysis))


class _DiagnosticWindow:
    """Janela principal do diagnóstico de ping.

    Concentra a montagem dos widgets, o controle dos estados da interface
    (inicial, executando, concluído e erro) e a conversão do ``PingAnalysis``
    recebido pela fila em widgets de apresentação. Não executa comandos, não
    faz parsing e não cria achados: apenas exibe o que a camada de análise já
    produziu.
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._result_queue: "queue.Queue[tuple[str, PingAnalysis | str]]" = (
            queue.Queue()
        )
        # Indica se há um diagnóstico em andamento. Serve para impedir
        # execução simultânea tanto pelo botão quanto pela tecla Enter,
        # já que o botão desabilitado sozinho não bloqueia a tecla.
        self._running = False
        self._build_widgets()

    def _build_widgets(self) -> None:
        """Monta os widgets da janela e define o estado inicial."""
        self._root.title("Network Diagnostic Tool")
        self._root.geometry("720x560")

        container = ttk.Frame(self._root, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        # Linha superior: rótulo, campo de destino e botão de diagnóstico.
        top_frame = ttk.Frame(container)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Destino:").pack(side=tk.LEFT)

        self._target_entry = ttk.Entry(top_frame)
        self._target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        # Enter no campo de destino equivale a clicar em "Diagnosticar".
        self._target_entry.bind("<Return>", self._on_enter)

        self._diagnose_button = ttk.Button(
            top_frame, text="Diagnosticar", command=self._start_diagnosis
        )
        self._diagnose_button.pack(side=tk.LEFT)

        # Faixa de estado.
        self._status_label = ttk.Label(container, text="", anchor="w")
        self._status_label.pack(fill=tk.X, pady=(8, 4))

        # Resumo: três cartões lado a lado (perda, latência média e pacotes).
        # Cada cartão apenas destaca visualmente um valor da análise; nenhum
        # deles emite julgamento sobre o resultado.
        summary = ttk.Frame(container)
        summary.pack(fill=tk.X)

        self._loss_value_var = tk.StringVar(value=_UNAVAILABLE)
        self._latency_value_var = tk.StringVar(value=_UNAVAILABLE)
        self._packets_value_var = tk.StringVar(value=_UNAVAILABLE)

        self._add_summary_card(summary, 0, "PERDA", self._loss_value_var)
        self._add_summary_card(summary, 1, "LATÊNCIA MÉDIA", self._latency_value_var)
        self._add_summary_card(summary, 2, "PACOTES", self._packets_value_var)

        # Distribui os três cartões igualmente na largura disponível.
        for column in range(3):
            summary.columnconfigure(column, weight=1, uniform="summary")

        # Achados: contêiner reconstruído a cada execução.
        findings_section = ttk.LabelFrame(container, text="Achados", padding=8)
        findings_section.pack(fill=tk.X, pady=(8, 0))
        self._findings_container = ttk.Frame(findings_section)
        self._findings_container.pack(fill=tk.X)

        # Detalhes: texto completo produzido pela apresentação textual.
        details_section = ttk.LabelFrame(container, text="Detalhes", padding=8)
        details_section.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._details_text = scrolledtext.ScrolledText(
            details_section, wrap=tk.WORD, height=10
        )
        self._details_text.pack(fill=tk.BOTH, expand=True)
        self._details_text.configure(state=tk.DISABLED)

        self._clear_results()
        self._set_status("Informe um destino e clique em Diagnosticar.")
        # O campo de destino recebe o foco assim que a janela é construída.
        self._focus_target()

    @staticmethod
    def _add_summary_card(
        parent: ttk.Frame,
        column: int,
        title: str,
        value_var: tk.StringVar,
    ) -> None:
        """Adiciona um cartão (título + valor) à faixa de resumo.

        O cartão é apenas um contêiner visual: o título identifica a
        métrica e o valor é lido diretamente da variável fornecida, que por
        sua vez só recebe dados da análise. Nenhum julgamento é exibido.
        """
        card = ttk.Frame(parent, relief="groove", borderwidth=1, padding=8)
        card.grid(row=0, column=column, sticky="nsew", padx=4)

        ttk.Label(card, text=title, anchor="center").pack(fill=tk.X)
        ttk.Label(
            card,
            textvariable=value_var,
            anchor="center",
            font=_CARD_VALUE_FONT,
        ).pack(fill=tk.X, pady=(6, 0))

    def _set_status(self, message: str, error: bool = False) -> None:
        """Atualiza a faixa de estado.

        O sucesso usa a cor neutra; apenas o estado de erro recebe a cor de
        alerta. A cor não expressa severidade de rede: ela descreve o estado
        da própria interface.
        """
        color = _STATUS_ERROR_COLOR if error else _STATUS_NEUTRAL_COLOR
        self._status_label.configure(text=message, foreground=color)

    def _set_running(self, running: bool) -> None:
        """Liga/desliga o estado "executando" da interface.

        Durante a execução o botão fica desabilitado e o cursor de espera é
        aplicado. Ao final, o botão volta ao normal e o cursor é restaurado.
        A flag ``_running`` é a fonte da verdade para impedir execução
        simultânea, inclusive via tecla Enter.
        """
        self._running = running
        if running:
            self._diagnose_button.configure(state=tk.DISABLED)
            self._root.configure(cursor="watch")
        else:
            self._diagnose_button.configure(state=tk.NORMAL)
            self._root.configure(cursor="")

    def _focus_target(self) -> None:
        """Devolve o foco ao campo de destino e seleciona seu conteúdo."""
        self._target_entry.focus_set()
        self._target_entry.selection_range(0, tk.END)

    def _on_enter(self, event: tk.Event) -> None:
        """Trata a tecla Enter pressionada no campo de destino.

        Redireciona para o mesmo fluxo do botão. A proteção contra execução
        simultânea é garantida dentro de ``_start_diagnosis`` (via flag
        ``_running``), portanto o Enter não inicia dois diagnósticos.
        """
        self._start_diagnosis()

    def _clear_findings(self) -> None:
        """Remove os widgets de achados da execução anterior."""
        for child in self._findings_container.winfo_children():
            child.destroy()

    def _clear_results(self) -> None:
        """Limpa resumo, achados e detalhes, voltando ao estado neutro."""
        self._loss_value_var.set(_UNAVAILABLE)
        self._latency_value_var.set(_UNAVAILABLE)
        self._packets_value_var.set(_UNAVAILABLE)
        self._clear_findings()
        self._set_details("")

    def _set_details(self, text: str) -> None:
        """Substitui o conteúdo da área de detalhes pelo texto recebido."""
        self._details_text.configure(state=tk.NORMAL)
        self._details_text.delete("1.0", tk.END)
        self._details_text.insert("1.0", text)
        self._details_text.configure(state=tk.DISABLED)

    def _render_analysis(self, analysis: PingAnalysis) -> None:
        """Preenche resumo, achados e detalhes a partir do ``PingAnalysis``.

        Apenas copia os valores já presentes na análise para os widgets. Não
        recalcula, não interpreta e não cria novos achados.
        """
        self._loss_value_var.set(f"{analysis.packet_loss_percent}%")

        average = analysis.avg_latency_ms
        if average is None:
            self._latency_value_var.set(_UNAVAILABLE)
        else:
            self._latency_value_var.set(f"{average} ms")

        self._packets_value_var.set(
            f"{analysis.packets_received}/{analysis.packets_sent}"
        )

        self._render_findings(analysis.findings)
        self._set_details(format_ping_analysis(analysis))

    def _render_findings(self, findings: tuple[AnalysisFinding, ...]) -> None:
        """Desenha um achado por linha, com marcador, rótulo e resumo.

        O marcador, o rótulo e a cor vêm exclusivamente de ``Severity``. O
        resumo é o texto já produzido pela camada de análise.
        """
        self._clear_findings()

        if not findings:
            ttk.Label(
                self._findings_container,
                text="Nenhum achado de análise foi produzido para esta execução.",
            ).pack(anchor="w")
            return

        for finding in findings:
            marker, label, color = _SEVERITY_STYLES[finding.severity]

            row = ttk.Frame(self._findings_container)
            row.pack(fill=tk.X, anchor="w", pady=2)

            ttk.Label(row, text=marker, foreground=color).grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(row, text=label, foreground=color).grid(
                row=0, column=1, sticky="w", padx=(4, 8)
            )
            ttk.Label(
                row,
                text=finding.summary,
                wraplength=_FINDING_SUMMARY_WRAP,
                justify="left",
            ).grid(row=0, column=2, sticky="w")
            row.columnconfigure(2, weight=1)

    def _start_diagnosis(self) -> None:
        """Inicia o diagnóstico a partir do destino informado.

        Ligada ao botão e à tecla Enter. Se já houver um diagnóstico em
        andamento, retorna sem iniciar outro (proteção contra execução
        simultânea). Caso contrário, rejeita destino vazio, limpa os
        resultados anteriores, entra no estado "executando", dispara a worker
        thread e agenda a primeira verificação da fila.
        """
        if self._running:
            return

        target = self._target_entry.get().strip()
        if not target:
            self._clear_results()
            self._set_status("Informe um destino para o diagnóstico.", error=True)
            self._focus_target()
            return

        self._clear_results()
        self._set_status("Executando diagnóstico...")
        self._set_running(True)

        worker = threading.Thread(
            target=run_ping_diagnosis,
            args=(target, self._result_queue),
            daemon=True,
        )
        worker.start()

        self._root.after(_POLL_INTERVAL_MS, self._poll_queue)

    def _poll_queue(self) -> None:
        """Verifica a fila e atualiza a interface quando há resultado.

        Executada pela thread principal via ``root.after``. Enquanto a fila
        estiver vazia, reagenda a si mesma. Quando há um resultado, sai do
        estado "executando", exibe-o e devolve o foco ao campo de destino.
        """
        try:
            kind, payload = self._result_queue.get_nowait()
        except queue.Empty:
            self._root.after(_POLL_INTERVAL_MS, self._poll_queue)
            return

        self._set_running(False)

        if kind == _KIND_OK and isinstance(payload, PingAnalysis):
            self._render_analysis(payload)
            self._set_status("Diagnóstico concluído.")
        else:
            self._set_status(f"Erro: {payload}", error=True)

        self._focus_target()


def main() -> None:
    """Cria a janela, liga os eventos e inicia o loop da interface."""
    root = tk.Tk()
    _DiagnosticWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
