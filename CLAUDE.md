# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-snap7 is a pure Python S7 communication library for interfacing with Siemens S7 PLCs. The library supports Python 3.10+ and runs on Windows, Linux, and macOS without any native dependencies.

## Key Architecture

### snap7/ — Legacy S7 protocol (S7-300/400, PUT/GET on S7-1200/1500)
- **snap7/client.py**: Main Client class for connecting to S7 PLCs
- **snap7/server.py**: Server implementation for PLC simulation
- **snap7/logo.py**: Logo PLC communication
- **snap7/partner.py**: Partner (peer-to-peer) connection functionality
- **snap7/connection.py**: ISO on TCP implementation (TPKT/COTP layers)
- **snap7/s7protocol.py**: S7 PDU encoding/decoding
- **snap7/datatypes.py**: S7 data types and address encoding
- **snap7/util/**: Utility functions for data conversion (getters.py, setters.py, db.py)
- **snap7/type.py**: Type definitions and enums (Area, Block, WordLen, etc.)
- **snap7/error.py**: Error handling and exceptions

### s7/ — Unified client with S7CommPlus + legacy fallback
- **s7/client.py**: Unified Client — tries S7CommPlus, falls back to snap7.Client
- **s7/async_client.py**: Unified AsyncClient — same pattern, async
- **s7/server.py**: Unified Server wrapping both legacy and S7CommPlus
- **s7/_protocol.py**: Protocol enum (AUTO/LEGACY/S7COMMPLUS)
- **s7/_s7commplus_client.py**: Pure S7CommPlus sync client (internal)
- **s7/_s7commplus_async_client.py**: Pure S7CommPlus async client (internal)
- **s7/_s7commplus_server.py**: S7CommPlus server emulator (internal)
- **s7/connection.py**: S7CommPlus low-level connection
- **s7/protocol.py**: S7CommPlus protocol constants/enums
- **s7/codec.py**: S7CommPlus encoding/decoding
- **s7/vlq.py**: Variable-Length Quantity encoding
- **s7/legitimation.py**: Authentication helpers

## Implementation Details

### Protocol Stack
The library implements the complete S7 protocol stack:
1. **TCP/IP**: Standard socket communication
2. **TPKT**: RFC 1006 framing layer
3. **COTP**: ISO 8073 Class 0 connection-oriented transport
4. **S7**: Siemens S7 protocol for PLC communication

### Features
- TCP connection management
- ISO on TCP (TPKT/COTP) transport layers
- S7 protocol PDU encoding/decoding
- Read/write operations for all memory areas (DB, M, I, Q, T, C)
- Error handling and connection management
- Data type conversions (BYTE, WORD, DWORD, INT, DINT, REAL)
- Multi-variable operations
- PLC control functions (start/stop/hot start/cold start)
- CPU information retrieval
- Block operations (list, info, upload, download)
- Date/time operations

### Usage (unified s7 package — recommended for S7-1200/1500)

```python
from s7 import Client

client = Client()
client.connect("192.168.1.10", 0, 1)  # auto-detects S7CommPlus vs legacy
data = client.db_read(1, 0, 4)
client.disconnect()
```

### Usage (legacy snap7 package — S7-300/400)

```python
import snap7

client = snap7.Client()
client.connect("192.168.1.10", 0, 1)

data = client.db_read(1, 0, 4)
client.db_write(1, 0, bytearray([1, 2, 3, 4]))

marker_data = client.mb_read(0, 4)
client.mb_write(0, 4, bytearray([1, 2, 3, 4]))

client.disconnect()
```

### Server Usage

```python
from snap7.server import Server, mainloop
from snap7.type import SrvArea
from ctypes import c_char

# Start a simple server
server = Server()
size = 100
db_data = bytearray(size)
db_array = (c_char * size).from_buffer(db_data)
server.register_area(SrvArea.DB, 1, db_array)
server.start(tcp_port=102)

# Or use the mainloop function
mainloop(tcp_port=102)
```

## Essential Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test categories using markers
pytest -m "server or util or client or mainloop"

# Run tests for specific component
pytest tests/test_client.py
```

### Code Quality
```bash
# Type checking
mypy snap7 s7 tests example

# Linting and formatting check
ruff check snap7 s7 tests example
ruff format --diff snap7 s7 tests example

# Auto-format code
ruff format snap7 s7 tests example
ruff check --fix snap7 s7 tests example
```

### Development with tox
```bash
# Run all tox environments (mypy, lint, py310-py314)
tox

# Run specific environments
tox -e mypy
tox -e lint-ruff
tox -e py310
```

### Using Makefile
```bash
# Setup development environment
make setup

# Run tests
make test

# Type checking
make mypy

# Linting
make check

# Format code
make format
```

### Building and Installation
```bash
# Install in development mode
pip install -e .

# Install with test dependencies
pip install -e ".[test]"

# Install with CLI tools
pip install -e ".[cli]"
```

## Test Markers

Tests are organized with pytest markers:
- `client`: Client functionality tests
- `server`: Server functionality tests
- `util`: Utility function tests
- `logo`: Logo PLC tests
- `partner`: Partner connection tests
- `mainloop`: Main loop tests

## Python Version Compatibility

**Fully tested and supported Python versions:**
- **Python 3.10** (EOL: October 2026)
- **Python 3.11** (EOL: October 2027)
- **Python 3.12** (EOL: October 2028)
- **Python 3.13** (EOL: October 2029)
- **Python 3.14** (EOL: October 2030)

## Code Quality Standards

### Expected Quality Tool Results
```bash
# MyPy should show clean results
mypy snap7 tests example

# Ruff should pass all checks
ruff check snap7 tests example

# Tests should pass
pytest tests/
```

### Development Best Practices

- **Always use logging instead of print()** for debug output (except CLI error messages)
- **Test across Python versions** when making changes that might affect compatibility
- **Follow the established project structure** when adding new functionality

## Configuration Notes

- **pyproject.toml**: Main project configuration with build, dependencies, and tool settings
- **tox.ini**: Multi-environment testing configuration
- **.pre-commit-config.yaml**: Pre-commit hooks for code quality
- **Ruff**: Line length set to 130, targets Python 3.10+
- **MyPy**: Strict mode enabled

## Contribution Guidelines

- **Small, focused PRs only**: Each pull request should address a single concern. Do not bundle unrelated changes together.
- **Each PR should have a single purpose**: Whether it is a bug fix, a new feature, a refactor, or a documentation update, keep it to one thing per PR.
- **Run the full test suite before submitting**: Run `make test` or `pytest` and ensure all tests pass.
- **Ensure mypy and ruff pass**: Run `mypy snap7 tests example` and `ruff check snap7 tests example` with no errors before opening a PR.
- **Always run `uv run pre-commit run --all-files` before every `git push`.** Individual `ruff check` / `ruff format --check` commands don't exercise every hook (`ruff format` is the one that actually reformats files, not the `--check` variant). Skipping pre-commit is the single most common reason CI fails on the ruff-format hook right after a push. If the hook reformats, amend and re-push — do not rely on "it passed locally" via other commands.
- **If using AI coding assistants**: Review the generated code carefully before submitting. AI-generated PRs that are large, unfocused, or not thoroughly reviewed are likely to be rejected.

## Library Architecture Notes

### Key Design Patterns
- **Error wrapping**: Uses custom exception classes for S7-specific errors
- **Type safety**: Uses ctypes structures for data type compatibility
- **Modular design**: Clear separation between client, server, utilities, and protocol layers

### Common Development Tasks
- **Adding new PLC operations**: Extend client.py with proper error handling and logging
- **Utility functions**: Add to appropriate modules in snap7/util/ following existing patterns
- **Type definitions**: Update snap7/type.py for new enums or structures
