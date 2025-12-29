# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-snap7 is a Python wrapper for the Snap7 library, providing Ethernet communication with Siemens S7 PLCs. The library supports Python 3.10+ and runs on Windows, Linux, and macOS.

## Key Architecture

- **snap7/client.py**: Main Client class for connecting to S7 PLCs
- **snap7/server.py**: Server implementation for PLC simulation
- **snap7/logo.py**: Logo PLC communication
- **snap7/partner.py**: Partner connection functionality
- **snap7/util/**: Utility functions for data conversion (getters.py, setters.py, db.py)
- **snap7/protocol.py**: Low-level protocol bindings to the native Snap7 library
- **snap7/type.py**: Type definitions and enums (Area, Block, WordLen, etc.)
- **snap7/common.py**: Common utilities including library loading
- **snap7/error.py**: Error handling and exceptions

The library uses ctypes to interface with the native Snap7 C library (libsnap7.so/snap7.dll/libsnap7.dylib).

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
- `common`: Common functionality tests

## Python Version Compatibility

**Fully tested and supported Python versions:**
- **Python 3.10** (EOL: October 2026) ✅
- **Python 3.11** (EOL: October 2027) ✅
- **Python 3.12** (EOL: October 2028) ✅
- **Python 3.13** (EOL: October 2029) ✅
- **Python 3.14** (EOL: October 2030) ✅

All versions pass the complete test suite and have been verified for type checking, linting, and functionality.

## Cross-Platform Development

This library supports **Windows, Linux, and macOS** through ctypes bindings:

- **Windows**: Uses `windll` from ctypes for library loading
- **Linux/macOS**: Uses `cdll` from ctypes for library loading
- **Library files**: Includes platform-specific Snap7 libraries (snap7.dll, libsnap7.so, libsnap7.dylib)

### Platform-Specific Notes
- The conditional import in `snap7/common.py` handles platform differences automatically
- No `# type: ignore` comments needed for platform-specific imports in modern mypy
- Cross-platform compatibility is maintained through the ctypes interface

## Code Quality Standards

### Expected Quality Tool Results
```bash
# MyPy should show clean results
mypy snap7 tests example
# Expected: "Success: no issues found in 27 source files"

# Ruff should pass all checks
ruff check snap7 tests example
# Expected: "All checks passed!"

# Tests should pass with high coverage
pytest tests/
# Expected: "188 passed, 4 skipped"
```

### Common Code Quality Issues and Fixes

1. **Print statements in production code**: Replace with `logger.info()` or appropriate log level
2. **Unused type ignore comments**: Remove if not needed, or make platform-specific
3. **Formatting inconsistencies**: Run `ruff format` to auto-fix
4. **Type annotation issues**: Use strict mypy checking to catch early

### Development Best Practices

- **Always use logging instead of print()** for debug output (except CLI error messages)
- **Test across Python versions** when making changes that might affect compatibility
- **Use existing patterns** for ctypes interactions and error handling
- **Follow the established project structure** when adding new functionality
- **Maintain cross-platform compatibility** - test platform-specific code paths

## Configuration Notes

- **pyproject.toml**: Main project configuration with build, dependencies, and tool settings
- **tox.ini**: Multi-environment testing configuration
- **.pre-commit-config.yaml**: Pre-commit hooks for code quality
- **Ruff**: Line length set to 130, targets Python 3.10+
- **MyPy**: Strict mode enabled with specific error code exceptions
- **Protocol exclusion**: snap7/protocol.py is excluded from some linting due to generated bindings

## Library Architecture Notes

### Key Design Patterns
- **Error wrapping**: Uses `@error_wrap` decorator for consistent error handling
- **Type safety**: Extensive use of ctypes with proper type annotations
- **Platform abstraction**: Single codebase works across Windows/Linux/macOS
- **Modular design**: Clear separation between client, server, utilities, and protocol layers

### Common Development Tasks
- **Adding new PLC operations**: Extend client.py with proper error handling and logging
- **Utility functions**: Add to appropriate modules in snap7/util/ following existing patterns
- **Type definitions**: Update snap7/type.py for new enums or structures
- **Cross-platform testing**: Use tox environments or manual virtual environment testing
