"""Unified S7 server combining legacy S7 and S7CommPlus protocols.

Provides a single server that can handle both legacy S7 and S7CommPlus
client connections simultaneously.

Usage::

    from s7 import Server

    server = Server()
    server.register_area(SrvArea.DB, 1, db_data)
    server.start(tcp_port=102)
"""

import logging
from typing import Any, Optional

from snap7.server import Server as LegacyServer
from snap7.s7commplus.server import S7CommPlusServer, DataBlock

logger = logging.getLogger(__name__)


class Server:
    """Unified S7 server combining legacy S7 and S7CommPlus.

    Wraps both a legacy S7 server and an S7CommPlus server, allowing
    them to run side by side. Legacy clients connect on the primary port,
    S7CommPlus clients on an optional secondary port.

    Methods not explicitly defined are delegated to the underlying
    legacy server via ``__getattr__``.

    Examples::

        from s7 import Server
        from snap7.type import SrvArea

        server = Server()

        # Register memory areas for legacy S7 clients
        db_data = bytearray(100)
        server.register_area(SrvArea.DB, 1, db_data)

        # Register data blocks for S7CommPlus clients
        server.register_db(1, {"temperature": ("Real", 0)})

        # Start both servers
        server.start(tcp_port=102, s7commplus_port=11020)

        # Stop both
        server.stop()
    """

    def __init__(self, log: bool = True) -> None:
        """Initialize unified server.

        Args:
            log: Enable event logging for the legacy server.
        """
        self._legacy: LegacyServer = LegacyServer(log=log)
        self._plus: S7CommPlusServer = S7CommPlusServer()
        self._plus_running: bool = False

    def start(
        self,
        tcp_port: int = 102,
        s7commplus_port: Optional[int] = None,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
    ) -> int:
        """Start the server(s).

        Args:
            tcp_port: Port for legacy S7 clients (default 102).
            s7commplus_port: Optional port for S7CommPlus clients.
                If None, only the legacy server is started.
            use_tls: Enable TLS for S7CommPlus server.
            tls_cert: Path to TLS certificate (PEM).
            tls_key: Path to TLS private key (PEM).

        Returns:
            0 on success.
        """
        result = self._legacy.start(tcp_port=tcp_port)

        if s7commplus_port is not None:
            self._plus.start(
                port=s7commplus_port,
                use_tls=use_tls,
                tls_cert=tls_cert,
                tls_key=tls_key,
            )
            self._plus_running = True
            logger.info(f"S7CommPlus server started on port {s7commplus_port}")

        return result

    def stop(self) -> int:
        """Stop both servers.

        Returns:
            0 on success.
        """
        if self._plus_running:
            try:
                self._plus.stop()
            except Exception:
                pass
            self._plus_running = False

        return self._legacy.stop()

    # -- S7CommPlus server methods --

    def register_db(
        self,
        db_number: int,
        variables: dict[str, tuple[str, int]],
        size: int = 1024,
    ) -> DataBlock:
        """Register a data block on the S7CommPlus server.

        Args:
            db_number: Data block number.
            variables: Dict of {name: (type_name, byte_offset)}.
            size: DB size in bytes (default 1024).

        Returns:
            The registered DataBlock.
        """
        return self._plus.register_db(db_number, variables, size)

    def register_raw_db(self, db_number: int, data: bytearray) -> DataBlock:
        """Register a raw data block on the S7CommPlus server.

        Args:
            db_number: Data block number.
            data: Raw DB data.

        Returns:
            The registered DataBlock.
        """
        return self._plus.register_raw_db(db_number, data)

    def get_db(self, db_number: int) -> Optional[DataBlock]:
        """Get a registered S7CommPlus data block.

        Args:
            db_number: Data block number.

        Returns:
            The DataBlock, or None if not registered.
        """
        return self._plus.get_db(db_number)

    @property
    def s7commplus_server(self) -> S7CommPlusServer:
        """Direct access to the underlying S7CommPlus server."""
        return self._plus

    @property
    def legacy_server(self) -> LegacyServer:
        """Direct access to the underlying legacy S7 server."""
        return self._legacy

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the legacy server."""
        if name.startswith("_"):
            raise AttributeError(name)
        legacy = self.__dict__.get("_legacy")
        if legacy is not None:
            return getattr(legacy, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __enter__(self) -> "Server":
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()
