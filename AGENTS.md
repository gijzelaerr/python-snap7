# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-snap7 is a pure Python S7 communication library for interfacing with Siemens S7 PLCs. The library supports Python 3.10+ and runs on Windows, Linux, and macOS without any native dependencies.

## Key Architecture

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

### Usage

```python
import snap7

# Create and connect client
client = snap7.Client()
client.connect("192.168.1.10", 0, 1)

# Read/write operations
data = client.db_read(1, 0, 4)
client.db_write(1, 0, bytearray([1, 2, 3, 4]))

# Memory area access
marker_data = client.mb_read(0, 4)
client.mb_write(0, 4, bytearray([1, 2, 3, 4]))

# Disconnect
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
mypy snap7 tests example

# Linting and formatting check
ruff check snap7 tests example
ruff format --diff snap7 tests example

# Auto-format code
ruff format snap7 tests example
ruff check --fix snap7 tests example
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

## Library Architecture Notes

### Key Design Patterns
- **Error wrapping**: Uses custom exception classes for S7-specific errors
- **Type safety**: Uses ctypes structures for data type compatibility
- **Modular design**: Clear separation between client, server, utilities, and protocol layers

### Common Development Tasks
- **Adding new PLC operations**: Extend client.py with proper error handling and logging
- **Utility functions**: Add to appropriate modules in snap7/util/ following existing patterns
- **Type definitions**: Update snap7/type.py for new enums or structures
