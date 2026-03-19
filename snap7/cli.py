"""
Command-line interface for python-snap7.

Provides subcommands for interacting with Siemens S7 PLCs:
- server: Start an emulated S7 PLC server
- read: Read data from a PLC
- write: Write data to a PLC
- dump: Dump DB contents
- info: Get PLC information
"""

import logging
import sys
from typing import Optional

try:
    import click
except ImportError:
    print("CLI dependencies not installed. Try: pip install python-snap7[cli]")
    raise

from snap7 import __version__
from snap7.client import Client
from snap7.server import mainloop
from snap7.util import (
    get_bool,
    get_byte,
    get_dint,
    get_dword,
    get_int,
    get_real,
    get_string,
    get_uint,
    get_udint,
    get_word,
    get_lreal,
    set_bool,
    set_byte,
    set_dint,
    set_dword,
    set_int,
    set_real,
    set_string,
    set_uint,
    set_udint,
    set_word,
    set_lreal,
)

logger = logging.getLogger(__name__)

# Map type names to (getter, size_in_bytes) for reads
TYPE_READ_MAP: dict[str, tuple[str, int]] = {
    "bool": ("bool", 1),
    "byte": ("byte", 1),
    "int": ("int", 2),
    "uint": ("uint", 2),
    "word": ("word", 2),
    "dint": ("dint", 4),
    "udint": ("udint", 4),
    "dword": ("dword", 4),
    "real": ("real", 4),
    "lreal": ("lreal", 8),
    "string": ("string", 256),
}


def _connect(host: str, rack: int, slot: int, port: int) -> Client:
    """Create and connect a client."""
    client = Client()
    client.connect(host, rack, slot, port)
    return client


def _read_typed(client: Client, db: int, offset: int, type_name: str, bit: int = 0) -> str:
    """Read a typed value and return its string representation."""
    if type_name == "bool":
        data = client.db_read(db, offset, 1)
        return str(get_bool(data, 0, bit))
    elif type_name == "byte":
        data = client.db_read(db, offset, 1)
        return str(get_byte(data, 0))
    elif type_name == "int":
        data = client.db_read(db, offset, 2)
        return str(get_int(data, 0))
    elif type_name == "uint":
        data = client.db_read(db, offset, 2)
        return str(get_uint(data, 0))
    elif type_name == "word":
        data = client.db_read(db, offset, 2)
        return str(get_word(data, 0))
    elif type_name == "dint":
        data = client.db_read(db, offset, 4)
        return str(get_dint(data, 0))
    elif type_name == "udint":
        data = client.db_read(db, offset, 4)
        return str(get_udint(data, 0))
    elif type_name == "dword":
        data = client.db_read(db, offset, 4)
        return str(get_dword(data, 0))
    elif type_name == "real":
        data = client.db_read(db, offset, 4)
        return str(get_real(data, 0))
    elif type_name == "lreal":
        data = client.db_read(db, offset, 8)
        return str(get_lreal(data, 0))
    elif type_name == "string":
        data = client.db_read(db, offset, 256)
        return get_string(data, 0)
    else:
        raise click.BadParameter(f"Unknown type: {type_name}")


def _format_hex(data: bytearray) -> str:
    """Format bytearray as hex dump with offsets."""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:04X}  {hex_part:<48s}  {ascii_part}")
    return "\n".join(lines)


@click.group()
@click.version_option(__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug output.")
def main(verbose: bool) -> None:
    """python-snap7: CLI tools for Siemens S7 PLC communication."""
    if verbose:
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.DEBUG)
    else:
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)


@main.command()
@click.option("-p", "--port", default=1102, help="Port the server will listen on.")
def server(port: int) -> None:
    """Start an emulated S7 PLC server with default values."""
    mainloop(port, init_standard_values=True)


@main.command()
@click.argument("host")
@click.option("--db", required=True, type=int, help="DB number to read from.")
@click.option("--offset", required=True, type=int, help="Byte offset to start reading.")
@click.option("--size", type=int, default=None, help="Number of bytes to read (for raw/bytes mode).")
@click.option(
    "--type",
    "data_type",
    type=click.Choice(list(TYPE_READ_MAP.keys()) + ["bytes"], case_sensitive=False),
    default="bytes",
    help="Data type to read.",
)
@click.option("--bit", type=int, default=0, help="Bit offset (only for bool type).")
@click.option("--rack", type=int, default=0, help="PLC rack number.")
@click.option("--slot", type=int, default=1, help="PLC slot number.")
@click.option("--port", type=int, default=102, help="PLC TCP port.")
def read(host: str, db: int, offset: int, size: Optional[int], data_type: str, bit: int, rack: int, slot: int, port: int) -> None:
    """Read data from a PLC."""
    try:
        client = _connect(host, rack, slot, port)
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)

    try:
        if data_type == "bytes":
            if size is None:
                click.echo("--size is required when reading raw bytes.", err=True)
                sys.exit(1)
            data = client.db_read(db, offset, size)
            click.echo(_format_hex(data))
        else:
            result = _read_typed(client, db, offset, data_type, bit)
            click.echo(result)
    except Exception as e:
        click.echo(f"Read failed: {e}", err=True)
        sys.exit(1)
    finally:
        client.disconnect()


@main.command()
@click.argument("host")
@click.option("--db", required=True, type=int, help="DB number to write to.")
@click.option("--offset", required=True, type=int, help="Byte offset to start writing.")
@click.option(
    "--type",
    "data_type",
    required=True,
    type=click.Choice(list(TYPE_READ_MAP.keys()) + ["bytes"], case_sensitive=False),
    help="Data type to write.",
)
@click.option("--value", required=True, type=str, help="Value to write.")
@click.option("--bit", type=int, default=0, help="Bit offset (only for bool type).")
@click.option("--rack", type=int, default=0, help="PLC rack number.")
@click.option("--slot", type=int, default=1, help="PLC slot number.")
@click.option("--port", type=int, default=102, help="PLC TCP port.")
def write(host: str, db: int, offset: int, data_type: str, value: str, bit: int, rack: int, slot: int, port: int) -> None:
    """Write data to a PLC."""
    try:
        client = _connect(host, rack, slot, port)
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)

    try:
        if data_type == "bytes":
            raw = bytes.fromhex(value.replace(" ", ""))
            client.db_write(db, offset, bytearray(raw))
        elif data_type == "bool":
            data = client.db_read(db, offset, 1)
            set_bool(data, 0, bit, value.lower() in ("true", "1", "yes"))
            client.db_write(db, offset, data)
        elif data_type == "byte":
            data = bytearray(1)
            set_byte(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "int":
            data = bytearray(2)
            set_int(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "uint":
            data = bytearray(2)
            set_uint(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "word":
            data = bytearray(2)
            set_word(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "dint":
            data = bytearray(4)
            set_dint(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "udint":
            data = bytearray(4)
            set_udint(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "dword":
            data = bytearray(4)
            set_dword(data, 0, int(value))
            client.db_write(db, offset, data)
        elif data_type == "real":
            data = bytearray(4)
            set_real(data, 0, float(value))
            client.db_write(db, offset, data)
        elif data_type == "lreal":
            data = bytearray(8)
            set_lreal(data, 0, float(value))
            client.db_write(db, offset, data)
        elif data_type == "string":
            data = bytearray(256)
            set_string(data, 0, value, 254)
            actual_size = 2 + len(value)
            client.db_write(db, offset, data[:actual_size])
        else:
            click.echo(f"Unknown type: {data_type}", err=True)
            sys.exit(1)
        click.echo("OK")
    except Exception as e:
        click.echo(f"Write failed: {e}", err=True)
        sys.exit(1)
    finally:
        client.disconnect()


@main.command()
@click.argument("host")
@click.option("--db", required=True, type=int, help="DB number to dump.")
@click.option("--size", type=int, default=256, help="Number of bytes to dump.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["hex", "bytes"], case_sensitive=False),
    default="hex",
    help="Output format.",
)
@click.option("--rack", type=int, default=0, help="PLC rack number.")
@click.option("--slot", type=int, default=1, help="PLC slot number.")
@click.option("--port", type=int, default=102, help="PLC TCP port.")
def dump(host: str, db: int, size: int, fmt: str, rack: int, slot: int, port: int) -> None:
    """Dump DB contents from a PLC."""
    try:
        client = _connect(host, rack, slot, port)
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)

    try:
        data = client.db_read(db, 0, size)
        if fmt == "hex":
            click.echo(f"DB{db} ({len(data)} bytes):")
            click.echo(_format_hex(data))
        else:
            click.echo(data.hex())
    except Exception as e:
        click.echo(f"Dump failed: {e}", err=True)
        sys.exit(1)
    finally:
        client.disconnect()


@main.command()
@click.argument("host")
@click.option("--rack", type=int, default=0, help="PLC rack number.")
@click.option("--slot", type=int, default=1, help="PLC slot number.")
@click.option("--port", type=int, default=102, help="PLC TCP port.")
def info(host: str, rack: int, slot: int, port: int) -> None:
    """Get PLC information."""
    try:
        client = _connect(host, rack, slot, port)
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)

    try:
        # CPU Info
        try:
            cpu_info = client.get_cpu_info()
            click.echo("CPU Info:")
            click.echo(f"  Module Type: {cpu_info.ModuleTypeName}")
            click.echo(f"  Serial Number: {cpu_info.SerialNumber}")
            click.echo(f"  AS Name: {cpu_info.ASName}")
            click.echo(f"  Copyright: {cpu_info.Copyright}")
            click.echo(f"  Module Name: {cpu_info.ModuleName}")
        except Exception as e:
            click.echo(f"  CPU Info: unavailable ({e})")

        # CPU State
        try:
            state = client.get_cpu_state()
            click.echo(f"\nCPU State: {state}")
        except Exception as e:
            click.echo(f"\nCPU State: unavailable ({e})")

        # Order Code
        try:
            order_code = client.get_order_code()
            click.echo(f"\nOrder Code: {order_code.OrderCode}")
        except Exception as e:
            click.echo(f"\nOrder Code: unavailable ({e})")

        # Protection
        try:
            protection = client.get_protection()
            click.echo(f"\nProtection Level: {protection.sch_schal}")
        except Exception as e:
            click.echo(f"\nProtection: unavailable ({e})")

        # Block list
        try:
            blocks = client.list_blocks()
            click.echo("\nBlocks:")
            click.echo(f"  OB: {blocks.OBCount}")
            click.echo(f"  FB: {blocks.FBCount}")
            click.echo(f"  FC: {blocks.FCCount}")
            click.echo(f"  SFB: {blocks.SFBCount}")
            click.echo(f"  SFC: {blocks.SFCCount}")
            click.echo(f"  DB: {blocks.DBCount}")
            click.echo(f"  SDB: {blocks.SDBCount}")
        except Exception as e:
            click.echo(f"\nBlocks: unavailable ({e})")

    except Exception as e:
        click.echo(f"Info failed: {e}", err=True)
        sys.exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
