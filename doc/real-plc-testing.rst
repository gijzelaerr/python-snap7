Real-PLC acceptance testing
===========================

The versioned Gherkin specifications in ``tests/features/real_plc`` exercise the
same client APIs and canonical 37-byte fixture used by the diagnostic end-to-end
tests. ``pytest-bdd`` was selected because it keeps pytest as the runner, reuses
fixtures, maps tags to markers, and supports the existing JUnit workflow.

Safety model
------------

Use only a dedicated, non-production test PLC. The default runner selects
``@smoke`` and is read-only. It never enables writes or administrative actions.
Scratch writes require ``--allow-write``, a separate DB (DB2 by default), and are
wrapped in a guard that saves, restores, and reads back the original bytes from
fixture teardown even when a step fails or pytest handles an interruption.
Hard process termination or power loss cannot run cleanup, so inspect the scratch
DB before reuse after either event.

Administrative actions (CPU start/stop, clock changes, program transfers, or
protection changes) require ``--allow-admin`` and must never target an in-service
PLC. No administrative scenarios are included in the initial suite.

PLC preparation
---------------

Import ``tests/plc_setup/e2e_test_dbs.scl`` into TIA Portal, or recreate its exact
layout. It defines read-only DB1 and scratch DB2. On S7-1200/1500, disable
``Optimized block access`` for both fixture DBs. Enable PUT/GET only when the
chosen legacy protocol path and the PLC security policy require it. Defaults are
rack 0, slot 1, and TCP port 102. Apply the least privilege that permits the
selected scenarios; do not weaken a PLC that is in service.

Running and reporting
---------------------

Install the test extras, then run the safe profile. Values supplied to reportable
metadata must not contain addresses, credentials, certificate paths, plant names,
or other site identifiers::

  uv sync --extra test --extra s7commplus
  uv run python tools/run_real_plc_acceptance.py \
    --plc-ip YOUR_PRIVATE_ADDRESS \
    --protocol legacy_s7 \
    --tester @YOUR_HANDLE \
    --plc-family S7-1500 \
    --plc-model "CPU 1511-1 PN" \
    --plc-firmware V2.9 \
    --plc-security-mode "PUT/GET, non-optimized fixture DBs"

The runner prints a Gherkin-aware terminal summary and writes JUnit XML plus a
schema-versioned, sanitized JSON report beneath ``real-plc-results/``. The JSON
records exact source state, host environment, PLC metadata, scenario tags,
pass/fail/skip results, and bounded diagnostics. It deliberately never reads the
PLC address into the report. Review both artifacts before publishing them.

Add ``--allow-write`` only after confirming DB2 is disposable scratch space.
``--allow-admin`` remains separate so write permission never implies permission
for operational actions.

Result policy
-------------

File one ``Real PLC test result`` issue per tester, PLC configuration, source
revision, and run. Attach both generated artifacts and apply exactly one result
label and one protocol label:

* ``hardware-test``
* ``test-result: pass``, ``test-result: fail``, or ``test-result: partial``
* ``protocol: legacy-s7`` or ``protocol: s7commplus``

``pass`` means every selected applicable scenario passed. ``fail`` means at least
one selected scenario failed. ``partial`` means the run completed with capability
skips or an incomplete selection; unsupported capabilities are not failures.
Reruns get a new issue and link the earlier result. Close the earlier issue as
superseded only after the replacement artifacts exist. A result becomes stale
when the tested code, feature schema, relevant protocol implementation, PLC
firmware, or PLC configuration changes—not merely with age.

Useful searches:

* `Open hardware failures <https://github.com/gijzelaerr/python-snap7/issues?q=is%3Aissue+is%3Aopen+label%3Ahardware-test+label%3A%22test-result%3A+fail%22>`_
* `S7CommPlus hardware runs <https://github.com/gijzelaerr/python-snap7/issues?q=is%3Aissue+label%3Ahardware-test+label%3A%22protocol%3A+s7commplus%22>`_
* Search a release or commit by adding its version or SHA to ``is:issue label:hardware-test``.

For a release candidate, prioritize one supported legacy S7 PLC and one
S7CommPlus-capable S7-1200/1500 before expanding the host matrix; hosted CI already
covers supported Python versions and operating systems without hardware. Test
evidence stays in issues. Volunteer coordination may use Discussions, but is not
a substitute for an attached structured result.
