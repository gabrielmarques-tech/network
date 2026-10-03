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

The first version will use native Windows utilities such as:

* `ping`
* `tracert`
* `nslookup`
* `ipconfig`
* `arp`
* `pathping`

Additional diagnostic capabilities may be added in future versions.

## Project Scope

### Version 1

The initial version will focus on:

1. Ping diagnostics
2. Traceroute diagnostics
3. DNS diagnostics
4. Local IP configuration
5. MTU diagnostics
6. Basic diagnostic analysis
7. Structured diagnostic results
8. Automated tests

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
* Ping execution
* Ping parsing
* Traceroute execution
* Traceroute parsing
* Traceroute orchestration
* Automated tests for the above (68 tests passing)

**Not implemented yet:**

* CLI / command-line entry point
* Result presentation to the user
* Automatic analysis of structured results
* DNS diagnostics
* IP configuration diagnostics
* MTU diagnostics
* Pathping diagnostics

The `analysis/` layer is still under development and currently contains no code.

## Architecture

The project is organized into separate layers. The structure below reflects
the files and directories that currently exist on disk.

```text
network_diagnostic/
│
├── diagnostics/       ← executes and orchestrates diagnostics
│   ├── ping.py
│   └── traceroute.py
│
├── parsers/           ← transforms raw command output into structured data
│   └── traceroute.py
│
├── models/            ← represents structured results
│   └── results.py
│
└── analysis/          ← interprets structured results (not implemented yet)
```

Note: the ping parser currently lives inside `diagnostics/ping.py`. This is
the current state and is documented as such; it is not stated as a required
refactoring task.

### Diagnostics

Responsible for executing network diagnostic commands and orchestrating their
collection (running commands, collecting raw output and coordinating the call
to the parser).

### Parsers

Responsible for transforming raw command output into structured data. Parsers
are pure functions: they receive text and return models, without executing
commands or accessing the network.

### Models

Responsible for representing structured diagnostic data as simple, immutable
data containers: `PingResult`, `HopResult` and `TracerouteResult` already exist.

### Analysis

Responsible for interpreting collected evidence and producing technical
conclusions. This layer is still under development and currently contains no
code. It will interpret structured results without executing commands or
performing parsing.

The diagnostic layer collects information.

The analysis layer interprets information.

These responsibilities should not be mixed unnecessarily.

The current data flow is:

```text
user input (not implemented)
    ↓
command execution (implemented: ping, traceroute)
    ↓
parsing (implemented: ping, traceroute)
    ↓
structured models (implemented: PingResult, HopResult, TracerouteResult)
    ↓
analysis (not implemented: analysis/ contains no code yet)
    ↓
presentation (not implemented)
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
* Diagnostic analysis (future)

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

The ping and traceroute diagnostics have been implemented, tested and
committed. The remaining work, in the recommended order, is:

1. Implement the `analysis/` layer to interpret structured results
2. Add a CLI entry point and result presentation
3. Implement remaining diagnostics: DNS, IP configuration, MTU, pathping

The immediate next development step is to build the `analysis/` layer, which
will interpret structured results without executing commands or performing
parsing.

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
