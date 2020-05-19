CHANGES
=======

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
