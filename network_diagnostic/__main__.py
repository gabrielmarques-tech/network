"""Ponto de entrada para execução via ``python -m network_diagnostic``.

Este arquivo é apenas um adaptador: ele delega toda a lógica para
``network_diagnostic.presentation.cli.main``.
"""

from network_diagnostic.presentation.cli import main

if __name__ == "__main__":
    raise SystemExit(main())