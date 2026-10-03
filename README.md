# Network Diagnostic Tool

CLI tool for diagnosing network connectivity, packet loss, latency and routing issues using Windows network utilities.

## Status

🚧 In development

## Overview

The Network Diagnostic Tool is a Python-based command-line application designed to assist in the diagnosis of network connectivity problems.

The project was inspired by real-world ISP troubleshooting scenarios, where it is necessary to collect network evidence before determining whether a problem is related to the local network, gateway, routing, DNS, packet loss, latency or an external destination.

The tool aims to automate the collection and organization of diagnostic information using native Windows network utilities.

## Main Objectives

The project aims to:

* Test network connectivity
* Measure packet loss
* Measure network latency
* Analyze latency variation
* Inspect network routing
* Perform DNS diagnostics
* Inspect local network configuration
* Test MTU-related problems
* Collect diagnostic evidence
* Generate a structured diagnostic result
* Provide cautious technical interpretations based on collected evidence

The tool should prioritize **evidence-based diagnostics rather than assumptions**.

## Core Diagnostic Tools

The tool uses native Windows utilities. Currently implemented:

* `ping`
* `tracert`

Planned but **not implemented yet**:

* `nslookup`
* `ipconfig`
* `arp`
* `pathping`

Additional diagnostic capabilities may be added in future versions.

## Project Scope

### Version 1

Implemented so far:

1. Ping diagnostics
2. Traceroute diagnostics
3. Basic diagnostic analysis of ping and traceroute results
4. Structured diagnostic results
5. Automated tests

Planned for V1, but **not implemented yet**:

* DNS diagnostics
* Local IP configuration diagnostics
* MTU diagnostics

### Future Versions

Possible future improvements include:

* Testing multiple client devices
* Comparing results from multiple network endpoints
* Detecting patterns across multiple clients
* Historical diagnostic records
* JSON reports
* CSV reports
* Automated monitoring
* Alerts
* Web dashboard
* API
* Integration with network monitoring systems

These features are intentionally outside the initial scope.

## Current Development Stage

The project is being developed incrementally. At the current stage:

**Already implemented, tested and committed:**

* `PingResult`, `HopResult` and `TracerouteResult` structured result models
* Ping execution and ping parsing
* Traceroute execution, parsing and orchestration
* The `analysis/` layer, with analyzers for ping and traceroute that
  produce structured interpretative findings (`AnalysisFinding`, `Severity`)
* The `application/` layer, which composes diagnosis and analysis
* The `presentation/` layer, which formats analyses as terminal text
* A CLI entry point (`python -m network_diagnostic`)
* Automated tests for the above (154 tests passing)

**Not implemented yet:**

* DNS diagnostics
* IP configuration diagnostics
* MTU diagnostics
* Pathping diagnostics
* `nslookup`, `ipconfig` and `arp` based diagnostics

## Command-Line Usage

The CLI is available through the package module. Currently there are two
subcommands, `ping` and `traceroute`, each taking a single required positional
`target` (an IP address or hostname):

```text
python -m network_diagnostic ping <target>
python -m network_diagnostic traceroute <target>
```

Each subcommand runs the diagnostic, analyzes the result and prints the
findings to the terminal. Internal parameters of the application layer (such as
`count`, `max_hops` and `timeout_ms`) are not exposed on the CLI yet and use
their default values.

Exit codes:

* `0` — the diagnostic ran successfully.
* `1` — execution or parsing error.
* `2` — argument/usage error, or a recognized subcommand without an explicit
dispatch (handled by `argparse` for usage errors).

## Architecture

The project is organized into separate layers. The structure below reflects
the files and directories that currently exist on disk.

```text
network_diagnostic/
│
├── __main__.py        ← entry point for `python -m network_diagnostic`
│
├── presentation/      ← CLI parsing and text formatting
│   ├── cli.py
│   └── text.py
│
├── application/       ← use cases that compose diagnosis and analysis
│   ├── ping.py
│   └── traceroute.py
│
├── diagnostics/       ← executes and orchestrates diagnostics
│   ├── ping.py
│   └── traceroute.py
│
├── parsers/           ← transforms raw command output into structured data
│   ├── ping.py
│   └── traceroute.py
│
├── models/            ← represents structured results
│   └── results.py
│
└── analysis/          ← interprets structured results
    ├── findings.py
    ├── ping.py
    └── traceroute.py
```

Note: the ping parser lives in `parsers/ping.py` and the traceroute parser
lives in `parsers/traceroute.py`.

### Presentation

Responsible for the CLI and for turning analysis objects into readable text.
`presentation/cli.py` parses arguments and dispatches to the application layer;
`presentation/text.py` contains pure formatting functions. This layer does not
execute commands, does not parse command output and does not interpret the
network.

### Application

Responsible for composing the diagnostic execution with the analysis of its
result as a single use case. It is a thin layer: it does not run subprocesses,
does not parse output and does not duplicate analysis rules.

### Diagnostics

Responsible for executing network diagnostic commands and orchestrating their
collection (running commands, collecting raw output and coordinating the call
to the parser).

### Parsers

Responsible for transforming raw command output into structured data. Parsers
are pure functions: they receive text and return models, without executing
commands or accessing the network. The ping parser is in `parsers/ping.py` and
the traceroute parser is in `parsers/traceroute.py`.

### Models

Responsible for representing structured diagnostic data as simple, immutable
data containers: `PingResult`, `HopResult` and `TracerouteResult` already exist.

### Analysis

Responsible for interpreting collected evidence and producing structured
interpretative findings. The layer currently provides analyses for ping
(`analyze_ping`) and traceroute (`analyze_traceroute`), producing findings as
`AnalysisFinding` values with a `Severity`. It interprets structured results
without executing commands or performing parsing, and it avoids unsupported
conclusions.

The diagnostic layer collects information.

The analysis layer interprets information.

These responsibilities should not be mixed unnecessarily.

The current data flow is:

```text
CLI (presentation/cli.py)
    ↓
application (diagnose_and_analyze_*)
    ↓
diagnostics (collects raw output)
    ↓
parsers (raw output → structured models)
    ↓
models (PingResult, HopResult, TracerouteResult)
    ↓
analysis (findings: AnalysisFinding with Severity)
    ↓
presentation (text.py formats the analysis for the terminal)
```

## Diagnostic Philosophy

The application must avoid making unsupported conclusions.

For example:

> Packet loss detected at an intermediate traceroute hop does not automatically mean that the router at that hop is defective.

Some network devices may limit or deprioritize ICMP responses while continuing to forward traffic normally. A router that does not answer a probe at one hop may still be forwarding the traffic of the following hops correctly.

Therefore, the application should compare multiple measurements and destinations before suggesting a possible problem. It must not interpret loss or latency at an intermediate hop in isolation as a failure of that router.

Example:

```text
Gateway
    ↓
ISP DNS
    ↓
1.1.1.1
    ↓
8.8.8.8
```

If the gateway responds normally while external destinations present packet loss or increased latency, the application may indicate that the degradation appears to occur beyond the local gateway.

The application should distinguish between:

* Observed evidence
* Possible interpretation
* Confirmed information

It should not present assumptions as confirmed causes.

## Development Principles

The project follows these principles:

* Keep the code simple and maintainable
* Prefer the Python standard library when appropriate
* Separate responsibilities between modules
* Use type hints
* Write automated tests
* Avoid unnecessary dependencies
* Validate external command results
* Handle command execution errors
* Keep diagnostic parsing isolated from diagnostic execution
* Avoid hard-coded assumptions about command output
* Document important technical decisions
* Make small and meaningful Git commits

## Testing Strategy

The project uses automated tests to validate:

* Command parsing
* Diagnostic result models
* Packet loss calculations
* Latency calculations
* Error handling
* Diagnostic analysis
* CLI dispatch and text formatting

Network commands should not be required for every unit test.

Real network execution should be treated separately from deterministic unit tests.

## Git Workflow

Development will be tracked using Git.

The `main` branch should contain stable code.

Features should preferably be developed in dedicated branches.

Example:

```text
main
│
├── feature/ping-diagnostic
├── feature/traceroute-diagnostic
├── feature/dns-diagnostic
└── feature/diagnostic-analyzer
```

Commits should describe a meaningful change.

Examples:

```text
chore: initialize project structure
feat: add ping result model
feat: implement ping diagnostic
test: add ping parser tests
feat: add traceroute diagnostic
```

## Roadmap

The ping and traceroute diagnostics, their parsers, the `analysis/` layer, the
`application/` layer, the CLI and the result presentation have been
implemented, tested and committed.

The following items are **not implemented yet** and are candidates for future
work (they are not currently available):

* Additional diagnostics: DNS, IP configuration, MTU, pathping
* Diagnostics based on `nslookup`, `ipconfig` and `arp`
* Any expansion of the analysis rules beyond the current ping and traceroute
  findings

No next diagnostic is committed at this point.

## Non-Goals for Version 1

The following will not be implemented during the initial version:

* Artificial intelligence
* Web dashboard
* Mobile application
* Docker infrastructure
* FastAPI backend
* React frontend
* Database
* SNMP monitoring
* IXC integration
* Radius integration
* Zabbix integration

These technologies may become relevant in future versions, but they are intentionally excluded from the first version so that the core diagnostic engine can be developed and validated first.

## Technologies

* Python
* Windows networking utilities
* Git
* GitHub
* Pytest

## Project Goal

The goal of this project is not simply to execute network commands.

The goal is to build a maintainable diagnostic system capable of collecting network evidence, organizing the results and assisting technical professionals in identifying possible network problems.

The project is also intended as a practical study of:

* Python
* Networking
* Software architecture
* Automated testing
* CLI applications
* Git/GitHub
* Technical troubleshooting
* Systems integration
