# Network Diagnostic Tool - AI Development Rules

## Project Purpose

This project is a Python CLI application for diagnosing network
connectivity, packet loss, latency, DNS, routing and MTU problems.

The project is inspired by real ISP troubleshooting scenarios.

## Development Rules

1. Do not add features outside the current scope without asking.
2. Do not introduce AI into the project.
3. Do not create a web interface during V1.
4. Do not add unnecessary dependencies.
5. Prefer Python standard library when appropriate.
6. Keep diagnostic execution separate from result parsing.
7. Keep parsing separate from diagnostic analysis.
8. Use type hints.
9. Write tests for important behavior.
10. Do not remove tests just to make the project pass.
11. Do not hide errors with broad exception handling.
12. Do not make unsupported network conclusions.
13. Explain architectural decisions before implementing complex changes.
14. Do not rewrite unrelated files.
15. Keep changes small and focused.

## Layer Responsibilities

The project separates responsibilities across layers. These boundaries
must be respected:

- `presentation/` — responsible for the CLI (argument parsing and dispatch)
  and for converting analysis objects into readable text. It does not
  execute commands, does not parse command output and does not interpret the
  network.
- `application/` — responsible for composing diagnostic execution with the
  analysis of its result as a single use case. It is a thin layer and does
  not run subprocesses, parse output or duplicate analysis rules.
- `diagnostics/` — responsible for executing and orchestrating
  diagnostics (running commands, collecting raw output, coordinating the
  call to the parser).
- `parsers/` — responsible for transforming raw command output into
  structured data. Parsers are pure functions.
- `models/` — responsible for representing structured results as simple,
  immutable data containers.
- `analysis/` — responsible for interpreting structured results without
  executing commands or performing parsing, producing structured
  interpretative findings.

The diagnostic layer collects information. The analysis layer interprets
information. These responsibilities must not be mixed.

## Current Priority

The project is being developed incrementally.

The ping, traceroute and pathping diagnostics, their parsers, the result
models `PingResult`, `HopResult`, `TracerouteResult`, `PathpingHop` and
`PathpingResult`, the `analysis/` layer (with analyses for ping, traceroute
and pathping), the `application/` layer, the CLI and the result presentation
have been implemented and tested. Note that the pathping implementation is
currently only partially committed: part of it is in the working tree and
has not been committed yet.

The current focus is to consolidate and refine what already exists, keeping
changes small and evidence-based. Do not introduce new diagnostics or layers
beyond the established scope without prior discussion.

Do not start implementing DNS, MTU or ipconfig until a next step has been
agreed and the current work has been completed, tested and committed.

## Git Rules

Before making a significant change:

1. Check git status.
2. Check the current branch.
3. Implement the change.
4. Run tests.
5. Review the changed files.
6. Check git diff.
7. Commit only after validation.

Use meaningful commit messages.

Examples:

feat: implement ping diagnostic
test: add ping parser tests
fix: handle ping timeout
refactor: separate ping parsing logic

Never make unrelated changes in the same commit.

### Idioma do código

- Comentários e docstrings do código-fonte devem ser escritos em português.
- Nomes de variáveis, funções, classes, módulos e arquivos devem permanecer em inglês, seguindo as convenções do ecossistema Python.
- Mensagens exibidas pelo programa ao usuário devem ser escritas em português.
- Não escrever comentários ou docstrings em inglês apenas por convenção.
- Termos técnicos que façam parte da API, biblioteca ou comando utilizado podem permanecer em inglês quando a tradução prejudicar a clareza.
- O código deve continuar seguindo as convenções profissionais do Python, mesmo quando a documentação estiver em português.

Este projeto é um projeto de estudo e portfólio de Python e redes.

O usuário está aprendendo programação e não deve receber código simplesmente para copiar sem entender.

Antes de implementar mudanças relevantes:
1. explique o problema;
2. explique a arquitetura e as decisões;
3. apresente a implementação;
4. explique o código em português;
5. permita que o usuário execute e teste;
6. revise os resultados antes do próximo passo.

O usuário prefere comentários e docstrings do código em português.
Nomes de variáveis, funções, classes, módulos e arquivos devem permanecer em inglês.

DeepSeek é utilizado como assistente de implementação, mas suas alterações devem ser verificadas no disco, testadas e revisadas antes de serem aceitas.

Não adicionar funcionalidades fora do escopo definido no README e AGENTS.md sem discussão prévia.

Não avançar para uma nova etapa enquanto o usuário não compreender suficientemente a etapa atual.