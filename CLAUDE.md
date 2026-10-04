# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-snap7 is a pure Python library for the classic Siemens S7 protocol (S7-300/400, and PUT/GET access on
S7-1200/1500). It supports Python 3.10–3.14 on Windows, Linux, and macOS without native dependencies.

S7CommPlus support (S7-1200/1500 without PUT/GET) lives in the separate
[`s7commplus`](https://github.com/gijzelaerr/s7commplus) repository. Do not add S7CommPlus code here.

## Layout

- **snap7/client.py**, **snap7/async_client.py**: synchronous and asyncio clients; shared logic in `client_base.py`
- **snap7/server/**: pure Python server used for PLC emulation and tests (`python -m snap7.server`)
- **snap7/connection.py**: TCP, TPKT (RFC 1006), and COTP (ISO 8073 Class 0) transport
- **snap7/s7protocol.py**: S7 PDU encoding and decoding
- **snap7/datatypes.py**: S7 data types and address encoding
- **snap7/ppi.py**: experimental S7-200 serial PPI client
- **snap7/logo.py**, **snap7/partner.py**: LOGO! and peer-to-peer connections
- **snap7/util/**: byte-level getters, setters, and DB row helpers
- **snap7/type.py**, **snap7/error.py**: enums, ctypes structures, and exceptions
- **snap7/optimizer.py**, **snap7/rate_limiter.py**, **snap7/tags.py**, **snap7/szl.py**: multi-read planning, request
  throttling, tag parsing, and SZL decoding
- **s7/**: alias package that re-exports `snap7`; `from s7 import Client` is recommended for new code

## Usage

```python
from s7 import Client

client = Client()
client.connect("192.168.1.10", 0, 1)
data = client.db_read(1, 0, 4)
client.db_write(1, 0, bytearray([1, 2, 3, 4]))
client.disconnect()
```

```python
from s7.server import Server
from s7.type import SrvArea

server = Server()
server.register_area(SrvArea.DB, 1, bytearray(100))
server.start(tcp_port=1102)
```

## Commands

```bash
pytest                                      # all tests; real-PLC tests are skipped by default
pytest -m "server or util or client"        # by marker (see pyproject.toml for the full list)
mypy snap7 s7 tests example                 # strict mode
ruff check snap7 s7 tests example
ruff format snap7 s7 tests example
uv run pre-commit run --all-files           # run before every push
tox                                         # mypy, lint, and py310–py314
```

The Makefile wraps the same commands (`make setup`, `make test`, `make mypy`, `make check`, `make format`).

## Conventions

- Use logging, not `print()`, except for CLI error messages.
- Ruff line length is 130; mypy runs in strict mode.
- Raise the custom exceptions from `snap7/error.py` for S7-specific failures.
- Keep sync and async clients at parity when changing client behaviour.

## Contribution Guidelines

- **Small, focused PRs only**: one bug fix, feature, refactor, or documentation change per PR.
- **Run the full test suite, mypy, and ruff before opening a PR.**
- **Always run `uv run pre-commit run --all-files` before every `git push`.** Individual `ruff check` /
  `ruff format --check` commands don't exercise every hook. Skipping pre-commit is the most common reason CI fails
  on the ruff-format hook. If the hook reformats, amend and re-push.
- **If using AI coding assistants**: review the generated code carefully. Large, unfocused, or unreviewed
  AI-generated PRs are likely to be rejected.
- **No AI attribution**: never add AI assistants as author or co-author, and never add `Co-Authored-By:` trailers,
  "Generated with ..." footers, or similar AI attribution to commit messages, PR descriptions, or issue comments.

## Release Branches and Changelog

- `master` contains the complete changelog, including releases made from maintenance branches.
- Maintain pending maintenance-release notes on the relevant release branch (for example, `v3.1`).
- After tagging a maintenance release, immediately forward-port its finalized `CHANGES.md` section to `master` in a
  changelog-only pull request. Do not merge the maintenance branch into `master`.
- Changes intended for both lines should normally land on `master` first and then be cherry-picked to the
  maintenance branch.
- A release is not complete until its finalized changelog section is present on `master`; the production publish
  workflow enforces this before uploading to PyPI.
