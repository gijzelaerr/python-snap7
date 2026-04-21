CHANGES
=======

4.0.0 (unreleased)
-------------------

Major release: new `s7` package with S7CommPlus protocol support.

* New `s7` package as recommended entry point with protocol auto-detection
* S7CommPlus V1, V2 (TLS), and V3 support for S7-1200/1500
* S7CommPlus area read/write (M, I, Q, counters, timers)
* S7CommPlus PLC start/stop via INVOKE
* S7CommPlus object browsing via EXPLORE
* S7CommPlus live symbol browsing (`client.browse()`) and datablock listing (experimental)
* TIA Portal XML import for SymbolTable (`SymbolTable.from_tia_xml()`) (experimental)
* Partner BSend/BRecv with correct PBC format, async receive, PDU reference echo
* TCP_NODELAY and SO_KEEPALIVE on all sockets for lower latency
* Structured logging with PLC connection context (`snap7.log`)
* Command-line interface (`snap7-cli` / `s7`)
* Multi-variable read optimizer with parallel dispatch (experimental)
* S7 routing for multi-subnet PLC access (experimental)
* Symbolic addressing via SymbolTable (experimental)
* S7CommPlus CPU state reading and block transfer (upload/download)
* Array read/write helpers (`db_read_array`, `db_write_array`)
* Missing data type setters: `set_lint`, `set_ulint`, `set_ltime`, `set_ltod`, `set_ldt`
* **Unified Tag API**: `client.read_tag("DB1.DBD0:REAL")` with PLC4X /
  Siemens STEP7 syntax, replacing the homegrown SymbolTable class.
  Loaders: `load_csv`, `load_json`, `load_tia_xml` return `dict[str, Tag]`
* **Dual-dialect tag parsing**: `PLC4XTag` and `NodeS7Tag` subtypes of
  `Tag` with dialect-specific `parse()` and `__str__` (round-trip).
  `parse_tag(s, *, strict=True)` autodetects dialect from syntax markers
  (`,` → nodeS7, `:TYPE` → PLC4X); `strict=False` accepts bare short
  forms like `M7.1` or `IW22`. Enables pyS7 / Node-RED tag migration.
* **Symbolic (LID-based) access for optimized DBs** (experimental):
  `Tag.from_access_string("8A0E0001.A", "REAL")` creates a symbolic Tag;
  `client.read_tag(tag)` routes to S7CommPlus LID-based access via the
  PLC's symbol tree. Required for S7-1200/1500 DBs with
  "Optimized block access" enabled (the TIA Portal V13+ default).
* Optimizer excludes counter/timer areas from byte-range merging
* Fixed `get_cpu_info` field offsets for real S7-300/1500 (thanks @qzertywsx)
* Fixed `S7SZL.__str__` attribute name typo (thanks @qzertywsx)
* Dependabot auto-merge for dependency updates
* Documentation restructured: API Reference + Internals sections

### Thanks

* [@hs2bws-hash](https://github.com/hs2bws-hash) — extensive real PLC testing of Partner BSend/BRecv (#668)
* [@QuakeString](https://github.com/QuakeString) — read optimizer inspiration via python-snap7-optimized fork

3.0.0
-----

Major release: python-snap7 is now a pure Python S7 communication library.
This version completely breaks with the previous approach of wrapping the C snap7
shared library. The entire S7 protocol stack is now implemented in pure Python,
greatly improving portability and making it easier to install and extend.

* **Breaking**: The C snap7 library is no longer required or used
* Complete rewrite of the S7 protocol stack in pure Python
* Native Python implementation of TPKT (RFC 1006) and COTP (ISO 8073) layers
* Native S7 protocol PDU encoding/decoding
* Pure Python server implementation for testing and simulation
* No platform-specific binary dependencies — works on any platform that runs Python
* Improved error handling and connection management
* Full type annotations with mypy strict mode
* CLI interface for running an S7 server emulator (`pip install "python-snap7[cli]"`)

If you experience issues with 3.0, please report them on the
[issue tracker](https://github.com/gijzelaerr/python-snap7/issues) with a clear
description and the version you are using. As a workaround, pin to the last
pre-3.0 release:

    $ pip install "python-snap7<3"

### Thanks

Special thanks to the following people for testing, reporting issues, and providing
feedback during the 3.0 development:

* [@lupaulus](https://github.com/lupaulus) — extensive testing and bug reports
* [@spreeker](https://github.com/spreeker) — testing and feedback
* [@nikteliy](https://github.com/nikteliy) — review and feedback on the rewrite
* [@amorelettronico](https://github.com/amorelettronico) — testing
* [@razour08](https://github.com/razour08) — testing
* [@core-engineering](https://github.com/core-engineering) — bug reports (#553)
* [@AndreasScharf](https://github.com/AndreasScharf) — bug reports (#572)
* [@Robatronic](https://github.com/Robatronic) — bug reports (#574)
* [@hirotasoshu](https://github.com/hirotasoshu) — feedback (#545)
* [@PoitrasJ](https://github.com/PoitrasJ) — bug reports (#479)

1.2
---

* fix wheel tag for linux x86_64 by @nikteliy in https://github.com/gijzelaerr/python-snap7/pull/297
* Fixed typo area doesn't exist areas does by @Ofloo in https://github.com/gijzelaerr/python-snap7/pull/306
* add get_time and set_time in util by @Yingliangzhe in https://github.com/gijzelaerr/python-snap7/pull/308
* modification of TIME data type by @Yingliangzhe in https://github.com/gijzelaerr/python-snap7/pull/311
* added DATE_AND_TIME Value as Datetime object by @zsisamci in https://github.com/gijzelaerr/python-snap7/pull/312
* #273 by @nikteliy in https://github.com/gijzelaerr/python-snap7/pull/321
* Add byte type parsing to DB_Row API + set parsing case insensitive by @LoicGRENON in https://github.com/gijzelaerr/python-snap7/pull/315
* added missing types in  WordLen by @zsisamci in https://github.com/gijzelaerr/python-snap7/pull/326
* Add support for read/write unsigned value from bytearray by @LoicGRENON in https://github.com/gijzelaerr/python-snap7/pull/316
* fixing ip string paramters to c function by @zsisamci in https://github.com/gijzelaerr/python-snap7/pull/329
* Add py.typed marker file by @mthuurne in https://github.com/gijzelaerr/python-snap7/pull/342
* require correct package name, fixes issue #344 by @gijzelaerr in https://github.com/gijzelaerr/python-snap7/pull/345
* Fix warnings by @nikteliy in https://github.com/gijzelaerr/python-snap7/pull/350
* Update license identifier by @Shortfinga in https://github.com/gijzelaerr/python-snap7/pull/349
* Update client db_write docs by @pwablito in https://github.com/gijzelaerr/python-snap7/pull/352
* Fix db_offset calculation error by @lubbbert in https://github.com/gijzelaerr/python-snap7/pull/351
* fix #355 by @swamper123 in https://github.com/gijzelaerr/python-snap7/pull/359
* fix #272 by @swamper123 in https://github.com/gijzelaerr/python-snap7/pull/360
* fix get_time for small values by @swamper123 in https://github.com/gijzelaerr/python-snap7/pull/358
* add more getter methods for utils by @swamper123 in https://github.com/gijzelaerr/python-snap7/pull/357
* Prepare for 1.2 by @gijzelaerr in https://github.com/gijzelaerr/python-snap7/pull/364

### New Contributors

* @Ofloo made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/306
* @zsisamci made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/312
* @LoicGRENON made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/315
* @mthuurne made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/342
* @Shortfinga made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/349
* @pwablito made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/352
* @lubbbert made their first contribution in https://github.com/gijzelaerr/python-snap7/pull/351

**Full Changelog**: https://github.com/gijzelaerr/python-snap7/compare/1.1...1.2

1.1
---

* Make a binary wheel for all platforms (#232)
* Improve doc strings of all functions (#242)

Special thanks for this release to
 * Fabian Beitler
 * Nikteliy
 * Lautaro Nahuel Dapino

1.0
---

 *  Drop python 2 support  (#214)
 *  Feature request: ReadSZL()  (#196)
 *  Keep argument format across the functions  (#193)
 *  Drop Python2 Tests  (#167)
 *  Support for S5TIME  (#163)
 *  Add type annotations  (#157)
 *  client.full_upload() return bytearray size 65536  (#127)
 *  Some client tests segfault on Linux  (#26)
 *  Not all functions are implemented yet  (#25)

special thanks to [Fabian Beitler](https://github.com/swamper123) and
[Nikteliy](https://github.com/nikteliy>) for their contributions to the 1.0 release!




0.11
----

 * Update read_multi.py (#132)
 * Added fixes to snap7/client.py read_area function to allow for Counter and Timer Reads  (#121)
 * Post to a public docker repository? (#119)
 * Implementation of Cli_SetDateTime, Cli_GetDateTime enhancement (#114)


0.10
----

 * Fix OSX travis build #99
 * util.get_int() broken #101
 * Compatibility issue with Python3 #109
 * Logo 8 improvements bug #105


0.7
---

* util.get_int() broken (#65, #71)
* fix Add files via upload bug (#59)

Special thanks to Pelle van der Heide for solving issues


0.6
---

* Add __del__ to client, server and partner (#69)
* Add files via upload (#59)

Special thanks to xybsoft for solving issues

0.5
---

* adding some missing functions
* fixing Python3 support (issue #43)
* improving the documentation

0.4
---

More functions added:

* client.plc_stop
* client.plc_cold_start
* client.plc_hot_start
* client.read_multi_vars

0.2.1
-----

Small fix, README.rst was not included in sdist


0.2
---

- Add support for Windows
- Add functions added in Snap7 1.1.0
- Add missing client functions
- fix some partner functions
- simplified API

0.1
---

- Initial release.
