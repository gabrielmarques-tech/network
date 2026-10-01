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

## Architecture

The project is organized into separate layers.

```text
network_diagnostic/
│
├── diagnostics/
│   ├── ping.py
│   ├── traceroute.py
│   ├── dns.py
│   ├── ipconfig.py
│   ├── mtu.py
│   └── pathping.py
│
├── analysis/
│   └── analyzer.py
│
└── models/
    └── results.py
```

### Diagnostics

Responsible for executing network diagnostic commands and collecting their results.

### Models

Responsible for representing structured diagnostic data.

### Analysis

Responsible for interpreting collected evidence and producing technical conclusions.

The diagnostic layer should collect information.

The analysis layer should interpret information.

These responsibilities should not be mixed unnecessarily.

## Diagnostic Philosophy

The application must avoid making unsupported conclusions.

For example:

> Packet loss detected at an intermediate traceroute hop does not automatically mean that the router at that hop is defective.

Some network devices may limit or deprioritize ICMP responses while continuing to forward traffic normally.

Therefore, the application should compare multiple measurements and destinations before suggesting a possible problem.

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

The project will use automated tests to validate:

* Command parsing
* Diagnostic result models
* Packet loss calculations
* Latency calculations
* Error handling
* Diagnostic analysis

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

## Current Development Stage

The project is currently focused on implementing the first diagnostic capability: **Ping**.

The immediate development sequence is:

1. Define the ping result model
2. Implement ping execution
3. Implement ping output parsing
4. Create automated tests
5. Validate real execution
6. Review the implementation
7. Commit the completed feature
8. Move to the next diagnostic

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
