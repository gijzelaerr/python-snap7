"""
PROFINET DCP network discovery for finding Siemens PLCs.

Uses the pnio-dcp library for the underlying DCP protocol.
Install with: pip install python-snap7[discovery]
"""

from __future__ import annotations

import dataclasses
import logging

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Device:
    """A discovered PROFINET device on the network."""

    name: str
    ip: str
    mac: str
    netmask: str = ""
    gateway: str = ""
    family: str = ""

    def __str__(self) -> str:
        return f"{self.name} ({self.ip}) [{self.mac}]"


def discover(ip: str, timeout: float = 5.0) -> list[Device]:
    """Discover PROFINET devices on the network using DCP Identify All.

    Args:
        ip: IP address of the local network interface to use for discovery.
        timeout: How long to listen for responses in seconds (default 5.0).

    Returns:
        List of discovered devices.

    Raises:
        ImportError: If pnio-dcp is not installed.
        NotImplementedError: If the current platform is not supported by pnio-dcp.
    """
    try:
        from pnio_dcp import DCP
    except ImportError:
        raise ImportError("pnio-dcp is required for network discovery. Install it with: pip install python-snap7[discovery]")

    dcp = DCP(ip)
    dcp.identify_all_timeout = int(timeout) if timeout >= 1 else 1

    raw_devices = dcp.identify_all(timeout=int(timeout) if timeout >= 1 else 1)

    devices = []
    for raw in raw_devices:
        device = Device(
            name=raw.name_of_station,
            ip=raw.IP,
            mac=raw.MAC,
            netmask=getattr(raw, "netmask", ""),
            gateway=getattr(raw, "gateway", ""),
            family=getattr(raw, "family", ""),
        )
        devices.append(device)
        logger.debug(f"Discovered: {device}")

    logger.info(f"Discovery complete: found {len(devices)} device(s)")
    return devices


def identify(ip: str, mac: str) -> Device:
    """Identify a specific device by MAC address.

    Args:
        ip: IP address of the local network interface to use.
        mac: MAC address of the target device (colon-separated, e.g. "00:1b:1b:12:34:56").

    Returns:
        The identified device.

    Raises:
        ImportError: If pnio-dcp is not installed.
        TimeoutError: If the device does not respond.
    """
    try:
        from pnio_dcp import DCP, DcpTimeoutError
    except ImportError:
        raise ImportError("pnio-dcp is required for network discovery. Install it with: pip install python-snap7[discovery]")

    dcp = DCP(ip)
    try:
        raw = dcp.identify(mac)
    except DcpTimeoutError:
        raise TimeoutError(f"No response from device {mac}")

    return Device(
        name=raw.name_of_station,
        ip=raw.IP,
        mac=raw.MAC,
        netmask=getattr(raw, "netmask", ""),
        gateway=getattr(raw, "gateway", ""),
        family=getattr(raw, "family", ""),
    )


try:
    import click

    @click.command()
    @click.argument("ip")
    @click.option("--timeout", type=float, default=5.0, help="Discovery timeout in seconds.")
    def discover_command(ip: str, timeout: float) -> None:
        """Discover PROFINET devices on the network.

        IP is the address of the local network interface to use for discovery.
        """
        logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)
        try:
            devices = discover(ip, timeout)
        except ImportError as e:
            click.echo(str(e), err=True)
            raise SystemExit(1)
        except NotImplementedError as e:
            click.echo(f"Platform not supported: {e}", err=True)
            raise SystemExit(1)

        if not devices:
            click.echo("No devices found.")
            return

        click.echo(f"Found {len(devices)} device(s):\n")
        for device in devices:
            click.echo(f"  {device.name:<30s} {device.ip:<16s} {device.mac}")

except ImportError:
    pass


def main() -> None:
    """Standalone CLI entry point for discovery."""
    discover_command()


if __name__ == "__main__":
    main()
