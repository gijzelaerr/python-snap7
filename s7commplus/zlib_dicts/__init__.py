"""S7CommPlus zlib preset dictionaries for compressed blob decompression.

Extracted from thomas-v2/S7CommPlusDriver (LGPL-3.0):
  src/S7CommPlusDriver/Core/BlobDecompressor.cs

S7-1200/1500 PLCs compress various XML blobs (interface descriptions,
tag tables, line comments, debug info, etc.) using zlib with a preset
dictionary. Python's zlib.decompress() returns Z_NEED_DICT; we provide
the matching dictionary based on the Adler-32 checksum in the zlib header.

Each dictionary is stored as a readable ``.xml`` file in this package
directory, named ``{adler32}_{name}.xml``. They are loaded once at
import time and indexed by Adler-32 checksum.
"""

from pathlib import Path as _Path

_DIR = _Path(__file__).parent

ZLIB_DICT_NAMES: dict[int, str] = {}
ZLIB_DICTIONARIES: dict[int, bytes] = {}

for _f in sorted(_DIR.glob("*.xml")):
    _adler_hex, _rest = _f.stem.split("_", 1)
    _adler = int(_adler_hex, 16)
    _name = _rest.replace("_", " ")
    ZLIB_DICT_NAMES[_adler] = _name
    ZLIB_DICTIONARIES[_adler] = _f.read_bytes().rstrip(b"\n")
