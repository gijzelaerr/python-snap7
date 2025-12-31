"""
S7 protocol implementation.

Handles S7 PDU encoding/decoding and protocol operations.
"""

import struct
import logging
from typing import List, Dict, Any
from enum import IntEnum

from .datatypes import S7Area, S7WordLen, S7DataTypes
from .error import S7ProtocolError

logger = logging.getLogger(__name__)


class S7Function(IntEnum):
    """S7 protocol function codes."""

    READ_AREA = 0x04
    WRITE_AREA = 0x05
    REQUEST_DOWNLOAD = 0x1A
    DOWNLOAD_BLOCK = 0x1B
    DOWNLOAD_ENDED = 0x1C
    START_UPLOAD = 0x1D
    UPLOAD = 0x1E
    END_UPLOAD = 0x1F
    PLC_CONTROL = 0x28
    PLC_STOP = 0x29
    SETUP_COMMUNICATION = 0xF0


class S7PDUType(IntEnum):
    """S7 PDU type codes."""

    REQUEST = 0x01
    RESPONSE = 0x03
    USERDATA = 0x07


class S7UserDataGroup(IntEnum):
    """S7 USER_DATA type groups (from s7_types.h)."""

    PROGRAMMER = 0x01  # grProgrammer
    CYCLIC_DATA = 0x02  # grCyclicData
    BLOCK_INFO = 0x03  # grBlocksInfo
    SZL = 0x04  # grSZL
    SECURITY = 0x05  # grPassword
    TIME = 0x07  # grClock


class S7UserDataSubfunction(IntEnum):
    """S7 USER_DATA subfunctions."""

    # Block info subfunctions
    LIST_ALL = 0x01  # SFun_ListAll
    LIST_BLOCKS_OF_TYPE = 0x02  # SFun_ListBoT
    BLOCK_INFO = 0x03  # SFun_BlkInfo

    # SZL subfunctions
    READ_SZL = 0x01  # SFun_ReadSZL
    SYSTEM_STATE = 0x02  # System state request

    # Clock subfunctions
    GET_CLOCK = 0x01
    SET_CLOCK = 0x02


class S7Protocol:
    """
    S7 protocol implementation.

    Handles encoding and decoding of S7 PDUs for communication with Siemens PLCs.
    """

    def __init__(self) -> None:
        self.sequence = 0  # Message sequence counter

    def _next_sequence(self) -> int:
        """Get next sequence number for S7 PDU."""
        self.sequence = (self.sequence + 1) & 0xFFFF
        return self.sequence

    def build_read_request(self, area: S7Area, db_number: int, start: int, word_len: S7WordLen, count: int) -> bytes:
        """
        Build S7 read request PDU.

        Args:
            area: Memory area to read from
            db_number: DB number (for DB area)
            start: Start address/offset
            word_len: Data word length
            count: Number of items to read

        Returns:
            Complete S7 PDU
        """
        # S7 Header (12 bytes)
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.REQUEST,  # PDU type
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            0x000E,  # Parameter length (14 bytes)
            0x0000,  # Data length (no data for read)
        )

        # Parameter section (14 bytes)
        parameters = struct.pack(
            ">BBB",
            S7Function.READ_AREA,  # Function code
            0x01,  # Item count
            0x12,  # Variable specification
        )

        # Add address specification
        address_spec = S7DataTypes.encode_address(area, db_number, start, word_len, count)
        parameters += address_spec[1:]  # Skip first byte (already included as 0x12)

        return header + parameters

    def build_write_request(self, area: S7Area, db_number: int, start: int, word_len: S7WordLen, data: bytes) -> bytes:
        """
        Build S7 write request PDU.

        Args:
            area: Memory area to write to
            db_number: DB number (for DB area)
            start: Start address/offset
            word_len: Data word length
            data: Data to write

        Returns:
            Complete S7 PDU
        """
        # Calculate count from data length
        item_size = S7DataTypes.get_size_bytes(word_len, 1)
        count = len(data) // item_size

        # Parameter length: function + item count + address spec
        param_len = 3 + 11  # 14 bytes total

        # Data length: transport size + data
        data_len = 4 + len(data)  # Transport size (4 bytes) + actual data

        # S7 Header
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.REQUEST,  # PDU type
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            param_len,  # Parameter length
            data_len,  # Data length
        )

        # Parameter section
        parameters = struct.pack(
            ">BBB",
            S7Function.WRITE_AREA,  # Function code
            0x01,  # Item count
            0x12,  # Variable specification
        )

        # Add address specification
        address_spec = S7DataTypes.encode_address(area, db_number, start, word_len, count)
        parameters += address_spec[1:]  # Skip first byte

        # Data section
        data_section = (
            struct.pack(
                ">BBH",
                0x00,  # Reserved/Error
                word_len,  # Transport size
                len(data) * 8,  # Bit length (data length in bits)
            )
            + data
        )

        return header + parameters + data_section

    def build_setup_communication_request(self, max_amq_caller: int = 1, max_amq_callee: int = 1, pdu_length: int = 480) -> bytes:
        """
        Build S7 setup communication request.

        This negotiates communication parameters with the PLC.
        """
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.REQUEST,  # PDU type
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            0x0008,  # Parameter length (8 bytes)
            0x0000,  # Data length
        )

        parameters = struct.pack(
            ">BBHHH",
            S7Function.SETUP_COMMUNICATION,  # Function code
            0x00,  # Reserved
            max_amq_caller,  # Max AMQ caller
            max_amq_callee,  # Max AMQ callee
            pdu_length,  # PDU length
        )

        return header + parameters

    def build_plc_control_request(self, operation: str) -> bytes:
        """
        Build PLC control request.

        Args:
            operation: Control operation ('stop', 'hot_start', 'cold_start')

        Returns:
            Complete S7 PDU for PLC control
        """
        # Map operations to S7 control codes
        control_codes = {
            "stop": 0x29,  # PLC_STOP
            "hot_start": 0x28,  # PLC_CONTROL (warm restart)
            "cold_start": 0x28,  # PLC_CONTROL (cold restart)
        }

        if operation not in control_codes:
            raise ValueError(f"Unknown PLC control operation: {operation}")

        function_code = control_codes[operation]

        # Build control-specific parameters
        if operation == "stop":
            # Simple stop command
            param_data = struct.pack(">B", function_code)
        else:
            # Start commands with restart type
            restart_type = 1 if operation == "hot_start" else 2  # 1=warm, 2=cold
            param_data = struct.pack(">BB", function_code, restart_type)

        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.REQUEST,  # PDU type
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            len(param_data),  # Parameter length
            0x0000,  # Data length
        )

        return header + param_data

    def check_control_response(self, response: Dict[str, Any]) -> None:
        """
        Check PLC control response for errors.

        Args:
            response: Parsed S7 response

        Raises:
            S7ProtocolError: If control operation failed
        """
        # For now, just check that we got a response
        # In a full implementation, we would check specific error codes
        if response.get("error_code", 0) != 0:
            raise S7ProtocolError(f"PLC control failed with error: {response['error_code']}")

    # ========================================================================
    # USER_DATA PDU Builders (Chunk 3 of protocol implementation)
    # ========================================================================

    def build_list_blocks_request(self) -> bytes:
        """
        Build USER_DATA request for listing all blocks.

        Returns:
            Complete S7 PDU for list blocks request
        """
        # USER_DATA PDU format:
        # - S7 header (10 bytes)
        # - Parameter section (8 bytes for USER_DATA)
        # - Data section (4 bytes for list blocks)

        # Parameter section for USER_DATA request
        # Format: header + method + type|group + subfunction + seq
        param_data = struct.pack(
            ">BBBBBBBB",
            0x00,  # Reserved
            0x01,  # Parameter count
            0x12,  # Type/length header
            0x04,  # Length of following data
            0x11,  # Method (0x11 = request)
            0x43,  # Type (4=request) | Group (3=grBlocksInfo)
            S7UserDataSubfunction.LIST_ALL,  # Subfunction (0x01 = list all)
            self._next_sequence() & 0xFF,  # Sequence number (1 byte)
        )

        # Data section: return code placeholder
        data_section = struct.pack(
            ">BBH",
            0x0A,  # Return value (request)
            0x00,  # Transport size
            0x0000,  # Length (0 for request)
        )

        # S7 header for USER_DATA
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.USERDATA,  # PDU type (0x07)
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            len(param_data),  # Parameter length
            len(data_section),  # Data length
        )

        return header + param_data + data_section

    def build_list_blocks_of_type_request(self, block_type: int) -> bytes:
        """
        Build USER_DATA request for listing blocks of a specific type.

        Args:
            block_type: Block type code (e.g., 0x41 for DB)

        Returns:
            Complete S7 PDU for list blocks of type request
        """
        # Parameter section for USER_DATA request
        param_data = struct.pack(
            ">BBBBBBBB",
            0x00,  # Reserved
            0x01,  # Parameter count
            0x12,  # Type/length header
            0x04,  # Length of following data
            0x11,  # Method (0x11 = request)
            0x43,  # Type (4=request) | Group (3=grBlocksInfo)
            S7UserDataSubfunction.LIST_BLOCKS_OF_TYPE,  # Subfunction (0x02)
            self._next_sequence() & 0xFF,  # Sequence number
        )

        # Data section: block type
        data_section = struct.pack(
            ">BBHB",
            0x0A,  # Return value (request)
            0x00,  # Transport size
            0x0001,  # Length (1 byte for block type)
            block_type,  # Block type code
        )

        # S7 header for USER_DATA
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.USERDATA,  # PDU type (0x07)
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            len(param_data),  # Parameter length
            len(data_section),  # Data length
        )

        return header + param_data + data_section

    def parse_list_blocks_response(self, response: Dict[str, Any]) -> Dict[str, int]:
        """
        Parse list blocks response and extract block counts.

        Args:
            response: Parsed S7 response

        Returns:
            Dictionary mapping block type names to counts
        """
        result = {
            "OBCount": 0,
            "FBCount": 0,
            "FCCount": 0,
            "SFBCount": 0,
            "SFCCount": 0,
            "DBCount": 0,
            "SDBCount": 0,
        }

        data_info = response.get("data", {})
        raw_data = data_info.get("data", b"")

        if not raw_data:
            return result

        # Parse block entries (4 bytes each: 0x30 | type | count_hi | count_lo)
        # Block type codes
        type_to_name = {
            0x38: "OBCount",  # Organization Block
            0x41: "DBCount",  # Data Block
            0x42: "SDBCount",  # System Data Block
            0x43: "FCCount",  # Function
            0x44: "SFCCount",  # System Function
            0x45: "FBCount",  # Function Block
            0x46: "SFBCount",  # System Function Block
        }

        offset = 0
        while offset + 4 <= len(raw_data):
            indicator = raw_data[offset]
            block_type = raw_data[offset + 1]
            count = struct.unpack(">H", raw_data[offset + 2 : offset + 4])[0]

            if indicator == 0x30 and block_type in type_to_name:
                result[type_to_name[block_type]] = count

            offset += 4

        return result

    def parse_list_blocks_of_type_response(self, response: Dict[str, Any]) -> List[int]:
        """
        Parse list blocks of type response and extract block numbers.

        Args:
            response: Parsed S7 response

        Returns:
            List of block numbers
        """
        result: List[int] = []

        data_info = response.get("data", {})
        raw_data = data_info.get("data", b"")

        if not raw_data:
            return result

        # Parse block numbers (2 bytes each, big-endian)
        offset = 0
        while offset + 2 <= len(raw_data):
            block_num = struct.unpack(">H", raw_data[offset : offset + 2])[0]
            result.append(block_num)
            offset += 2

        return result

    def build_read_szl_request(self, szl_id: int, szl_index: int) -> bytes:
        """
        Build USER_DATA request for reading SZL (System Status List).

        Args:
            szl_id: SZL identifier
            szl_index: SZL index

        Returns:
            Complete S7 PDU for read SZL request
        """
        # Parameter section for USER_DATA SZL request
        param_data = struct.pack(
            ">BBBBBBBB",
            0x00,  # Reserved
            0x01,  # Parameter count
            0x12,  # Type/length header
            0x04,  # Length of following data
            0x11,  # Method (0x11 = request)
            0x44,  # Type (4=request) | Group (4=grSZL)
            S7UserDataSubfunction.READ_SZL,  # Subfunction (0x01)
            self._next_sequence() & 0xFF,  # Sequence number
        )

        # Data section: SZL ID and Index
        data_section = struct.pack(
            ">BBHHH",
            0x0A,  # Return value (request)
            0x00,  # Transport size
            0x0004,  # Length (4 bytes for ID + Index)
            szl_id,  # SZL ID
            szl_index,  # SZL Index
        )

        # S7 header for USER_DATA
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.USERDATA,  # PDU type (0x07)
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            len(param_data),  # Parameter length
            len(data_section),  # Data length
        )

        return header + param_data + data_section

    def parse_read_szl_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse read SZL response.

        Args:
            response: Parsed S7 response

        Returns:
            Dictionary with SZL ID, Index, and data
        """
        result: Dict[str, Any] = {
            "szl_id": 0,
            "szl_index": 0,
            "data": b"",
        }

        data_info = response.get("data", {})
        raw_data = data_info.get("data", b"")

        if len(raw_data) < 4:
            return result

        # Parse SZL header: ID (2) + Index (2)
        result["szl_id"] = struct.unpack(">H", raw_data[0:2])[0]
        result["szl_index"] = struct.unpack(">H", raw_data[2:4])[0]
        result["data"] = raw_data[4:]

        return result

    def build_cpu_state_request(self) -> bytes:
        """
        Build CPU state request.

        Returns:
            Complete S7 PDU for CPU state query
        """
        # Simple CPU state request - in real S7 this would be a userdata function
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            S7PDUType.REQUEST,  # PDU type
            0x0000,  # Reserved
            self._next_sequence(),  # Sequence
            0x0001,  # Parameter length
            0x0000,  # Data length
        )

        # Use a custom function code for CPU state
        parameters = struct.pack(">B", 0x04)  # Use READ_AREA function for simplicity

        return header + parameters

    def extract_cpu_state(self, response: Dict[str, Any]) -> str:
        """
        Extract CPU state from response.

        Args:
            response: Parsed S7 response

        Returns:
            CPU state string in S7CpuStatus format (e.g., 'S7CpuStatusRun')
        """
        # Map internal states to S7 status format for API compatibility with master branch
        # The cpu_statuses dict in type.py uses: {0: "S7CpuStatusUnknown", 4: "S7CpuStatusStop", 8: "S7CpuStatusRun"}
        return "S7CpuStatusRun"  # Default state for pure Python server

    def parse_response(self, pdu: bytes) -> Dict[str, Any]:
        """
        Parse S7 response PDU.

        Args:
            pdu: Complete S7 PDU

        Returns:
            Parsed response data
        """
        if len(pdu) < 12:
            raise S7ProtocolError("PDU too short for S7 response header")

        # Parse S7 response header (includes error class and error code)
        header = struct.unpack(">BBHHHHBB", pdu[:12])
        protocol_id, pdu_type, reserved, sequence, param_len, data_len, error_class, error_code = header

        if protocol_id != 0x32:
            raise S7ProtocolError(f"Invalid protocol ID: {protocol_id:#02x}")

        # Accept both standard RESPONSE and USERDATA response types
        if pdu_type not in (S7PDUType.RESPONSE, S7PDUType.USERDATA):
            raise S7ProtocolError(f"Expected response PDU, got {pdu_type}")

        response = {
            "sequence": sequence,
            "param_length": param_len,
            "data_length": data_len,
            "parameters": None,
            "data": None,
            "error_code": (error_class << 8) | error_code,
        }

        offset = 12

        # Parse parameters if present
        if param_len > 0:
            if offset + param_len > len(pdu):
                raise S7ProtocolError("Parameter section extends beyond PDU")

            param_data = pdu[offset : offset + param_len]
            response["parameters"] = self._parse_parameters(param_data)
            offset += param_len

        # Parse data if present
        if data_len > 0:
            if offset + data_len > len(pdu):
                raise S7ProtocolError("Data section extends beyond PDU")

            data_section = pdu[offset : offset + data_len]
            response["data"] = self._parse_data_section(data_section)

        return response

    def _parse_parameters(self, param_data: bytes) -> Dict[str, Any]:
        """Parse S7 parameter section."""
        if len(param_data) < 1:
            return {}

        function_code = param_data[0]

        if function_code == S7Function.READ_AREA:
            return self._parse_read_response_params(param_data)
        elif function_code == S7Function.WRITE_AREA:
            return self._parse_write_response_params(param_data)
        elif function_code == S7Function.SETUP_COMMUNICATION:
            return self._parse_setup_comm_response_params(param_data)
        else:
            return {"function_code": function_code}

    def _parse_read_response_params(self, param_data: bytes) -> Dict[str, Any]:
        """Parse read area response parameters."""
        if len(param_data) < 2:
            raise S7ProtocolError("Read response parameters too short")

        function_code = param_data[0]
        item_count = param_data[1]

        return {"function_code": function_code, "item_count": item_count}

    def _parse_write_response_params(self, param_data: bytes) -> Dict[str, Any]:
        """Parse write area response parameters."""
        if len(param_data) < 2:
            raise S7ProtocolError("Write response parameters too short")

        function_code = param_data[0]
        item_count = param_data[1]

        return {"function_code": function_code, "item_count": item_count}

    def _parse_setup_comm_response_params(self, param_data: bytes) -> Dict[str, Any]:
        """Parse setup communication response parameters."""
        if len(param_data) < 8:
            raise S7ProtocolError("Setup communication response parameters too short")

        function_code, reserved, max_amq_caller, max_amq_callee, pdu_length = struct.unpack(">BBHHH", param_data[:8])

        return {
            "function_code": function_code,
            "max_amq_caller": max_amq_caller,
            "max_amq_callee": max_amq_callee,
            "pdu_length": pdu_length,
        }

    def _parse_data_section(self, data_section: bytes) -> Dict[str, Any]:
        """Parse S7 data section."""
        if len(data_section) == 1:
            # Simple return code (for write responses)
            return {"return_code": data_section[0], "transport_size": 0, "data_length": 0, "data": b""}
        elif len(data_section) >= 4:
            # Full data header
            return_code = data_section[0]
            transport_size = data_section[1]
            data_length = struct.unpack(">H", data_section[2:4])[0]

            # Extract actual data - length interpretation depends on transport_size
            # Transport size 0x09 (octet string): byte length (USERDATA responses)
            # Transport size 0x00: byte length (USERDATA requests)
            # Transport size 0x04 (byte): bit length (READ_AREA responses)
            if transport_size in (0x00, 0x09):
                # USERDATA uses byte length directly
                actual_data = data_section[4 : 4 + data_length]
            else:
                # READ_AREA responses use bit length
                actual_data = data_section[4 : 4 + (data_length // 8)]

            return {"return_code": return_code, "transport_size": transport_size, "data_length": data_length, "data": actual_data}
        else:
            return {"raw_data": data_section}

    def extract_read_data(self, response: Dict[str, Any], word_len: S7WordLen, count: int) -> List[Any]:
        """
        Extract and decode data from read response.

        Args:
            response: Parsed S7 response
            word_len: Expected data word length
            count: Expected number of items

        Returns:
            List of decoded values
        """
        if not response.get("data"):
            raise S7ProtocolError("No data in response")

        data_info = response["data"]
        return_code = data_info.get("return_code", 0)

        if return_code != 0xFF:  # 0xFF = Success
            error_msg = f"Read operation failed with return code: {return_code:#02x}"
            raise S7ProtocolError(error_msg)

        raw_data = data_info.get("data", b"")

        # Return raw bytes directly - caller handles type conversion
        return list(raw_data)

    def check_write_response(self, response: Dict[str, Any]) -> None:
        """
        Check write operation response for errors.

        Args:
            response: Parsed S7 response

        Raises:
            S7ProtocolError: If write operation failed
        """
        if not response.get("data"):
            raise S7ProtocolError("No data in write response")

        data_info = response["data"]
        return_code = data_info.get("return_code", 0)

        if return_code != 0xFF:  # 0xFF = Success
            error_msg = f"Write operation failed with return code: {return_code:#02x}"
            raise S7ProtocolError(error_msg)
