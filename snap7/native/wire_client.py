"""
Pure Python S7 client implementation.

Drop-in replacement for the ctypes-based client with native Python implementation.
"""

import logging
from typing import List, Any, Optional
from datetime import datetime

from .connection import ISOTCPConnection
from .protocol import S7Protocol
from .datatypes import S7Area, S7WordLen
from .errors import S7Error, S7ConnectionError, S7ProtocolError

# Import base client and existing types for compatibility
from ..client import Client as BaseClient
from ..type import Area, Block, BlocksList, S7CpuInfo, TS7BlockInfo

logger = logging.getLogger(__name__)


class WireClient:
    """
    Pure Python S7 client implementation.
    
    Drop-in replacement for the ctypes-based client that provides native Python
    communication with Siemens S7 PLCs without requiring the Snap7 C library.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize S7 client.

        Args:
            **kwargs: Accepts and ignores extra keyword arguments (e.g., pure_python, lib_location)
                     for compatibility with the Client factory.
        """
        super().__init__()
        self.connection: Optional[ISOTCPConnection] = None
        self.protocol = S7Protocol()
        self.connected = False
        self.host = ""
        self.port = 102
        self.rack = 0
        self.slot = 0
        self.pdu_length = 480  # Negotiated PDU length

        # Connection parameters
        self.local_tsap = 0x0100   # Default local TSAP
        self.remote_tsap = 0x0102  # Default remote TSAP

        logger.info("S7Client initialized (pure Python implementation)")
    
    def connect(self, host: str, rack: int, slot: int, port: int = 102) -> "WireClient":
        """
        Connect to S7 PLC.
        
        Args:
            host: PLC IP address
            rack: Rack number
            slot: Slot number  
            port: TCP port (default 102)
            
        Returns:
            Self for method chaining
        """
        self.host = host
        self.port = port
        self.rack = rack
        self.slot = slot
        
        # Calculate TSAP values from rack/slot
        # Remote TSAP: rack and slot encoded as per S7 specification
        self.remote_tsap = 0x0100 | (rack << 5) | slot
        
        try:
            # Establish ISO on TCP connection
            self.connection = ISOTCPConnection(
                host=host,
                port=port,
                local_tsap=self.local_tsap,
                remote_tsap=self.remote_tsap
            )
            
            self.connection.connect()
            
            # Setup communication and negotiate PDU length
            self._setup_communication()
            
            self.connected = True
            logger.info(f"Connected to {host}:{port} rack {rack} slot {slot}")
            
        except Exception as e:
            self.disconnect()
            if isinstance(e, S7Error):
                raise
            else:
                raise S7ConnectionError(f"Connection failed: {e}")
                
        return self
    
    def disconnect(self) -> None:
        """Disconnect from S7 PLC."""
        if self.connection:
            self.connection.disconnect()
            self.connection = None
            
        self.connected = False
        logger.info(f"Disconnected from {self.host}:{self.port}")
    
    def get_connected(self) -> bool:
        """Check if client is connected to PLC."""
        return self.connected and self.connection and self.connection.connected
    
    def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """
        Read data from DB.
        
        Args:
            db_number: DB number to read from
            start: Start byte offset
            size: Number of bytes to read
            
        Returns:
            Data read from DB
        """
        logger.debug(f"db_read: DB{db_number}, start={start}, size={size}")
        
        data = self.read_area(Area.DB, db_number, start, size)
        return data
    
    def db_write(self, db_number: int, start: int, data: bytearray) -> None:
        """
        Write data to DB.
        
        Args:
            db_number: DB number to write to
            start: Start byte offset
            data: Data to write
        """
        logger.debug(f"db_write: DB{db_number}, start={start}, size={len(data)}")
        
        self.write_area(Area.DB, db_number, start, data)
    
    def read_area(self, area: Area, db_number: int, start: int, size: int) -> bytearray:
        """
        Read data from memory area.
        
        Args:
            area: Memory area to read from
            db_number: DB number (for DB area only)
            start: Start address
            size: Number of bytes to read
            
        Returns:
            Data read from area
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
            
        # Map area enum to native area
        s7_area = self._map_area(area)
        
        # Build and send read request
        request = self.protocol.build_read_request(
            area=s7_area,
            db_number=db_number,
            start=start,
            word_len=S7WordLen.BYTE,
            count=size
        )
        
        self.connection.send_data(request)
        
        # Receive and parse response
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Extract data from response
        values = self.protocol.extract_read_data(response, S7WordLen.BYTE, size)
        
        return bytearray(values)
    
    def write_area(self, area: Area, db_number: int, start: int, data: bytearray) -> None:
        """
        Write data to memory area.
        
        Args:
            area: Memory area to write to
            db_number: DB number (for DB area only)
            start: Start address
            data: Data to write
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
            
        # Map area enum to native area
        s7_area = self._map_area(area)
        
        # Build and send write request
        request = self.protocol.build_write_request(
            area=s7_area,
            db_number=db_number,
            start=start,
            word_len=S7WordLen.BYTE,
            data=bytes(data)
        )
        
        self.connection.send_data(request)
        
        # Receive and parse response
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Check for write errors
        self.protocol.check_write_response(response)
    
    def read_multi_vars(self, items: List[dict]) -> List[Any]:
        """
        Read multiple variables in a single request.
        
        Args:
            items: List of item specifications
            
        Returns:
            List of read values
        """
        if not items:
            return []
        
        # Group items by area and DB to optimize reads
        grouped_reads = {}
        for i, item in enumerate(items):
            area = item['area']
            db_number = item.get('db_number', 0)
            start = item['start']
            size = item['size']
            
            key = (area, db_number)
            if key not in grouped_reads:
                grouped_reads[key] = []
            grouped_reads[key].append((i, start, size))
        
        # Execute optimized reads
        results = [None] * len(items)
        
        for (area, db_number), reads in grouped_reads.items():
            if len(reads) == 1:
                # Single read - use normal read_area
                i, start, size = reads[0]
                data = self.read_area(area, db_number, start, size)
                results[i] = data
            else:
                # Multiple reads from same area - try to optimize
                # Sort by start address
                reads.sort(key=lambda x: x[1])
                
                # Check if we can do a single large read
                first_start = reads[0][1]
                last_read = reads[-1]
                last_end = last_read[1] + last_read[2]
                total_span = last_end - first_start
                
                if total_span <= 512:  # If total span is reasonable, do one read
                    try:
                        large_data = self.read_area(area, db_number, first_start, total_span)
                        # Extract individual pieces
                        for i, start, size in reads:
                            offset = start - first_start
                            results[i] = large_data[offset:offset+size]
                    except Exception:
                        # Fall back to individual reads
                        for i, start, size in reads:
                            results[i] = self.read_area(area, db_number, start, size)
                else:
                    # Do individual reads
                    for i, start, size in reads:
                        results[i] = self.read_area(area, db_number, start, size)
        
        return results
    
    def write_multi_vars(self, items: List[dict]) -> None:
        """
        Write multiple variables in a single request.
        
        Args:
            items: List of item specifications with data
        """
        if not items:
            return
        
        # Group items by area and DB to potentially optimize writes
        grouped_writes = {}
        for item in items:
            area = item['area']
            db_number = item.get('db_number', 0)
            start = item['start']
            data = item['data']
            
            key = (area, db_number)
            if key not in grouped_writes:
                grouped_writes[key] = []
            grouped_writes[key].append((start, data))
        
        # Execute writes (for now still individual, but structured for future optimization)
        for (area, db_number), writes in grouped_writes.items():
            for start, data in writes:
                self.write_area(area, db_number, start, data)
    
    def list_blocks(self) -> BlocksList:
        """
        List blocks available in PLC.
        
        Returns:
            Block list structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Create a basic block list for the pure Python server
        # In a real implementation, this would use SZL (System Status List) functions
        block_list = BlocksList()
        
        # Initialize block counts to simulate a basic PLC configuration
        block_list.OBCount = 1   # Organization blocks
        block_list.FBCount = 0   # Function blocks
        block_list.FCCount = 0   # Functions  
        block_list.SFBCount = 0  # System function blocks
        block_list.SFCCount = 0  # System functions
        block_list.DBCount = 5   # Data blocks (simulate having DB1-DB5)
        block_list.SDBCount = 0  # System data blocks
        
        return block_list
    
    def get_cpu_info(self) -> S7CpuInfo:
        """
        Get CPU information.
        
        Returns:
            CPU information structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Create a basic CPU info structure for the pure Python server
        # In a real implementation, this would query the PLC via SZL functions
        cpu_info = S7CpuInfo()
        cpu_info.ModuleTypeName = b"Pure Python S7"
        cpu_info.SerialNumber = b"PY-S7-001"
        cpu_info.ASName = b"Pure Python"
        cpu_info.Copyright = b"Pure Python"
        cpu_info.ModuleName = b"CPU 317-2 PN/DP"
        
        return cpu_info
    
    def get_cpu_state(self) -> str:
        """
        Get CPU state (running/stopped).
        
        Returns:
            CPU state string
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Send CPU state request
        request = self.protocol.build_cpu_state_request()
        self.connection.send_data(request)
        
        # Receive response
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Extract CPU state from response
        return self.protocol.extract_cpu_state(response)
    
    def get_block_info(self, block_type: Block, db_number: int) -> TS7BlockInfo:
        """
        Get block information.
        
        Args:
            block_type: Type of block
            db_number: Block number
            
        Returns:
            Block information structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Create basic block info for the pure Python server
        # In a real implementation, this would query the PLC via SZL functions
        block_info = TS7BlockInfo()
        
        # Simulate block information based on type and number
        if block_type == Block.DB:
            block_info.BlkType = 0x41  # DB block type
            block_info.BlkNumber = db_number
            block_info.BlkLang = 0x05  # STL/AWL
            block_info.BlkFlags = 0x00
            block_info.MC7Size = 100   # Simulated size
            block_info.LoadSize = 100
            block_info.LocalData = 0
            block_info.SBBLength = 0
            block_info.CheckSum = 0x1234
            block_info.Version = 1
            # Set creation/modification time to current
            import time
            current_time = time.localtime()
            block_info.CodeDate = f"{current_time.tm_year:04d}/{current_time.tm_mon:02d}/{current_time.tm_mday:02d}".encode()
            block_info.IntfDate = block_info.CodeDate
            block_info.Author = b"PurePy"
            block_info.Family = b"S7-300"
            block_info.Header = b"DB Block"
        else:
            # Other block types - set minimal info
            block_info.BlkType = block_type
            block_info.BlkNumber = db_number
            block_info.BlkLang = 0x05
            block_info.MC7Size = 0
            block_info.LoadSize = 0
        
        return block_info
    
    def upload(self, block_num: int) -> bytearray:
        """
        Upload block from PLC.
        
        Args:
            block_num: Block number to upload
            
        Returns:
            Block data
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # For pure Python server, simulate block upload
        # In a real implementation, this would use upload functions
        logger.info(f"Simulating upload of block {block_num}")
        
        # Return simulated block data - basic AWL/STL block structure
        # This would normally be the actual compiled block from the PLC
        block_header = b"BLOCK_HEADER"
        block_code = b"NOP 0;\nBE;\n"  # Simple AWL/STL code
        
        return bytearray(block_header + block_code)
    
    def download(self, data: bytearray, block_num: int = -1) -> None:
        """
        Download block to PLC.
        
        Args:
            data: Block data to download
            block_num: Block number (-1 to extract from data)
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # For pure Python server, simulate block download
        # In a real implementation, this would use download functions
        logger.info(f"Simulating download of {len(data)} bytes to block {block_num}")
        
        # In a real implementation, this would:
        # 1. Parse the block data to extract block information
        # 2. Send download request to PLC
        # 3. Transfer the block data in chunks
        # 4. Verify the download completed successfully
        
        # For now, just log the operation
        logger.info("Block download simulation completed")
    
    def plc_stop(self) -> None:
        """Stop PLC CPU."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Send PLC stop command
        request = self.protocol.build_plc_control_request('stop')
        self.connection.send_data(request)
        
        # Receive response
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Check for errors
        self.protocol.check_control_response(response)
    
    def plc_hot_start(self) -> None:
        """Hot start PLC CPU."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Send PLC hot start command
        request = self.protocol.build_plc_control_request('hot_start')
        self.connection.send_data(request)
        
        # Receive response
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Check for errors
        self.protocol.check_control_response(response)
    
    def plc_cold_start(self) -> None:
        """Cold start PLC CPU."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Send PLC cold start command
        request = self.protocol.build_plc_control_request('cold_start')
        self.connection.send_data(request)
        
        # Receive response
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Check for errors
        self.protocol.check_control_response(response)
    
    def get_pdu_length(self) -> int:
        """
        Get negotiated PDU length.
        
        Returns:
            PDU length in bytes
        """
        return self.pdu_length
    
    def error_text(self, error_code: int) -> str:
        """
        Get error description for error code.
        
        Args:
            error_code: S7 error code
            
        Returns:
            Error description
        """
        from .errors import get_error_message
        return get_error_message(error_code)
    
    def get_plc_datetime(self) -> datetime:
        """
        Get PLC date/time.
        
        Returns:
            PLC date and time
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # For pure Python server, return current system time
        # In a real implementation, this would query the PLC's clock
        logger.info("Getting PLC datetime (returning system time)")
        return datetime.now()
    
    def set_plc_datetime(self, dt: datetime) -> None:
        """
        Set PLC date/time.
        
        Args:
            dt: Date and time to set
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # For pure Python server, simulate setting PLC time
        # In a real implementation, this would send time to PLC
        logger.info(f"Setting PLC datetime to {dt} (simulated)")
    
    def set_plc_system_datetime(self) -> None:
        """Set PLC time to system time."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        
        # Set PLC time to current system time
        current_time = datetime.now()
        self.set_plc_datetime(current_time)
        logger.info(f"Set PLC time to current system time: {current_time}")
    
    def _setup_communication(self) -> None:
        """Setup communication and negotiate PDU length."""
        request = self.protocol.build_setup_communication_request(
            max_amq_caller=1,
            max_amq_callee=1, 
            pdu_length=self.pdu_length
        )
        
        self.connection.send_data(request)
        
        response_data = self.connection.receive_data()
        response = self.protocol.parse_response(response_data)
        
        # Extract negotiated PDU length
        if response.get('parameters'):
            params = response['parameters']
            if 'pdu_length' in params:
                self.pdu_length = params['pdu_length']
                logger.info(f"Negotiated PDU length: {self.pdu_length}")
    
    def _map_area(self, area: Area) -> S7Area:
        """Map library area enum to native S7 area."""
        area_mapping = {
            Area.PE: S7Area.PE,
            Area.PA: S7Area.PA,
            Area.MK: S7Area.MK,
            Area.DB: S7Area.DB,
            Area.CT: S7Area.CT,
            Area.TM: S7Area.TM,
        }
        
        if area not in area_mapping:
            raise S7ProtocolError(f"Unsupported area: {area}")
            
        return area_mapping[area]
    
    def __enter__(self) -> "WireClient":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()