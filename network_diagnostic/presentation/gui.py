"""Interface gráfica mínima (V1) do Network Diagnostic Tool.

Este módulo é uma camada de apresentação: ele monta uma janela Tkinter que
permite informar um destino (IP ou hostname) e executar o diagnóstico de
``ping``, exibindo o resultado formatado. Ele não executa subprocess, não
faz parsing e não interpreta a rede: essas responsabilidades continuam nas
camadas já existentes.

Fluxo:

    campo de destino
        → diagnose_and_analyze_ping()   (camada de aplicação)
        → format_ping_analysis()        (camada de apresentação textual)
        → área de texto da janela

O diagnóstico roda em uma *worker thread* para não congelar a interface. A
thread de trabalho não acessa widgets do Tkinter: ela apenas deposita o
resultado em uma ``queue.Queue``. A thread principal verifica essa fila
periodicamente com ``root.after(...)`` e atualiza a interface.

Este primeiro incremento expõe somente o diagnóstico de ping. Traceroute e
pathping permanecem fora do escopo desta etapa.
"""

import queue
import threading
import tkinter as tk
from tkinter import scrolledtext

from network_diagnostic.application.ping import diagnose_and_analyze_ping
from network_diagnostic.diagnostics.ping import PingExecutionError
from network_diagnostic.parsers.ping import PingParseError
from network_diagnostic.presentation.text import format_ping_analysis

# Intervalo (em milissegundos) com que a thread principal verifica a fila de
# resultados em busca de uma resposta da worker thread.
_POLL_INTERVAL_MS = 100

# Identificadores do tipo de mensagem trafegada na fila.
_KIND_OK = "ok"
_KIND_ERROR = "error"


def run_ping_diagnosis(
    target: str,
    result_queue: "queue.Queue[tuple[str, str]]",
) -> None:
    """Executa o diagnóstico de ping e deposita o resultado na fila.

    Esta é a função alvo da *worker thread*. Ela não acessa widgets do
    Tkinter: apenas chama a camada de aplicação, formata o texto com a
    apresentação existente e coloca o resultado na ``result_queue``.

    Em caso de sucesso coloca ``("ok", texto_formatado)``; em caso de erro de
    execução ou de parsing coloca ``("error", mensagem)``. Assim como a CLI,
    captura apenas as exceções do domínio de ping (``PingExecutionError`` e
    ``PingParseError``); as demais exceções são propagadas, para não esconder
    falhas.
    """
    try:
        analysis = diagnose_and_analyze_ping(target)
    except (PingExecutionError, PingParseError) as error:
        result_queue.put((_KIND_ERROR, str(error)))
        return

    result_queue.put((_KIND_OK, format_ping_analysis(analysis)))


def main() -> None:
    """Monta a janela, liga os eventos e inicia o loop da interface.

    A janela contém um campo de destino, um botão "Diagnosticar" e uma área
    de texto somente leitura para exibir o resultado. Toda a lógica de rede
    permanece nas camadas existentes; esta função apenas orquestra a
    interface.
    """
    root = tk.Tk()
    root.title("Network Diagnostic Tool")
    root.geometry("640x420")

    # Linha superior: rótulo, campo de destino e botão de diagnóstico.
    top_frame = tk.Frame(root)
    top_frame.pack(fill=tk.X, padx=8, pady=8)

    tk.Label(top_frame, text="Destino:").pack(side=tk.LEFT)

    target_entry = tk.Entry(top_frame)
    target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

    diagnose_button = tk.Button(top_frame, text="Diagnosticar")
    diagnose_button.pack(side=tk.LEFT)

    # Área de resultado: somente leitura, com rolagem.
    result_text = scrolledtext.ScrolledText(root, wrap=tk.WORD)
    result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
    result_text.configure(state=tk.DISABLED)

    # Fila usada pela worker thread para enviar o resultado à thread principal.
    result_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()

    def show_result(text: str) -> None:
        """Substitui o conteúdo da área de resultado pelo texto recebido.

        Função de apoio da thread principal: alterna o widget para editável,
        troca o conteúdo e o devolve ao estado somente leitura.
        """
        result_text.configure(state=tk.NORMAL)
        result_text.delete("1.0", tk.END)
        result_text.insert("1.0", text)
        result_text.configure(state=tk.DISABLED)

    def poll_queue() -> None:
        """Verifica a fila e atualiza a interface quando há resultado.

        Executada pela thread principal via ``root.after``. Enquanto a fila
        estiver vazia, reagenda a si mesma. Quando há um resultado, exibe-o e
        reabilita o botão de diagnóstico.
        """
        try:
            kind, text = result_queue.get_nowait()
        except queue.Empty:
            root.after(_POLL_INTERVAL_MS, poll_queue)
            return

        show_result(text)
        diagnose_button.configure(state=tk.NORMAL)

    def start_diagnosis() -> None:
        """Inicia o diagnóstico a partir do destino informado.

        Função ligada ao botão. Rejeita destino vazio, desabilita o botão,
        inicia a worker thread e agenda a primeira verificação da fila.
        """
        target = target_entry.get().strip()
        if not target:
            show_result("Informe um destino para o diagnóstico.")
            return

        diagnose_button.configure(state=tk.DISABLED)
        show_result("Executando diagnóstico...")

        worker = threading.Thread(
            target=run_ping_diagnosis,
            args=(target, result_queue),
            daemon=True,
        )
        worker.start()

        root.after(_POLL_INTERVAL_MS, poll_queue)

    diagnose_button.configure(command=start_diagnosis)

    root.mainloop()


if __name__ == "__main__":
    main()
