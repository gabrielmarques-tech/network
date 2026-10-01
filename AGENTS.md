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

## Current Priority

The current feature being developed is:

Ping diagnostic.

Do not start implementing traceroute, DNS, MTU or other diagnostics
until the current feature has been completed, tested and committed.

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