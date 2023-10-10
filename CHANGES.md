CHANGES
=======

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
