import datetime

from .s7_consts import S7Consts
from .s7_socket import S7Socket
from .s7_protocol import S7Protocol as S7
import time
import struct

from .. import WordLen
from ..type import S7CpInfo, S7CpuInfo, S7OrderCode, S7Protection, TS7BlockInfo,  Block


class S7SZLHeader:
    def __init__(self):
        self.LENTHDR = 0
        self.N_DR = 0


class S7SZL:
    def __init__(self, data_size=1024):
        self.Header: S7SZLHeader = S7SZLHeader()
        self.Data = bytearray(data_size)

class S7Size:
    def __init__(self, default_size=1024):
        self.size :int = default_size

class S7Client:
    @property
    def connected(self):
        return self.socket is not None and self.socket.connected

    def __init__(self):
        self._last_error : int = 0

        self._address_PLC : str = ""
        self._port_PLC : int = 102
        self._rack : int = 0
        self._slot : int = 0
        self.conn_type : int = S7.CONNTYPE_PG

        self._recv_timeout : int = 2000
        self._send_timeout : int = 2000
        self._conn_timeout : int = 2000

        self.local_TSAP_high : int = 0
        self.local_TSAP_low : int = 0
        self.remote_TSAP_high : int = 0
        self.remote_TSAP_low: int = 0

        self._length_PDU : int = 0
        self._size_requested_PDU : int = 480
        self._last_PDU_type : int = 0
        self.PDU : bytearray = bytearray(2048)

        self._time_ms : int = 0

        self.socket = S7Socket()
        self.socket.connect_timeout = self._conn_timeout
        self.socket.read_timeout = self._recv_timeout
        self.socket.write_timeout = self._send_timeout

    def set_connection_params(self,address, local_tsap, remote_tsap):
        self._address_PLC = address

        loc_tsap = local_tsap & 0x0000FFFF
        rem_tsap = remote_tsap & 0x0000FFFF

        self.local_TSAP_high = (loc_tsap >> 8)
        self.local_TSAP_low = loc_tsap & 0xFF
        self.remote_TSAP_high = (rem_tsap >> 8)
        self.remote_TSAP_low = rem_tsap & 0xFF

    def connect_to(self, host: str, rack: int = 0, slot: int = 3, tcp_port: int = 102) -> int:

        # Calculate the RemoteTSAP (Transport Service Access Point) PG
        # Connection Type
        #
        # Value PG : 0x01
        # Value OP : 0x02
        # Value S7 Basic : 0x03..0x10
        remote_tsap : int  = (S7.CONNTYPE_PG << 8) + (rack * 0x20) + slot
        # Set connection parameters with the calculated TSAP
        self.set_connection_params(host, 0x0100, remote_tsap)
        # Attempt to connect
        return self.connect()

    def connect(self) -> int:
        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)  # Elapsed time in milliseconds

        if not self.connected:
            self.tcp_connect()  # First stage: TCP Connection
            if self._last_error == 0:
                self.iso_connect()  # Second stage: ISOTCP (ISO 8073) Connection
                if self._last_error == 0:
                    self._last_error = self.negotiate_pdu_length()  # Third stage: S7 PDU negotiation

        if self._last_error != 0:
            self.disconnect()
        else:
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error


    def read_SZL(self, szl_id : int, szl_index : int, szl_buffer : S7SZL) -> int:
        offset = 0
        done = False
        first = True
        seq_in = 0x00
        seq_out = 0x0000

        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)
        szl_buffer.Header.LENTHDR = 0

        ## Send two requests to the PLC
        ## Continue reading until the last packet is received
        while not done and self._last_error == 0:
            if first:
                S7.set_word_at(S7.S7_SZL_FIRST, 11, seq_out + 1)
                S7.set_word_at(S7.S7_SZL_FIRST, 29, szl_id)
                S7.set_word_at(S7.S7_SZL_FIRST, 31, szl_index)
                self.send_packet(S7.S7_SZL_FIRST)
            else:
                S7.set_word_at(S7.S7_SZL_NEXT, 11, seq_out + 1)
                self.PDU[24] = seq_in
                self.send_packet(S7.S7_SZL_NEXT)

            if self._last_error != 0:
                return self._last_error

            length = self.recv_iso_packet()
            if self._last_error == 0:
                if first:
                    if length > 32:  # Minimum expected
                        if S7.get_word_at(self.PDU, 27) == 0 and self.PDU[29] == 0xFF:
                            data_szl = S7.get_word_at(self.PDU, 31) - 8  # Skip extra params
                            done = self.PDU[26] == 0x00
                            seq_in = self.PDU[24]  # Slice sequence
                            szl_buffer.Header.LENTHDR = S7.get_word_at(self.PDU, 37)
                            szl_buffer.Header.N_DR = S7.get_word_at(self.PDU, 39)
                            szl_buffer.Data[offset:offset + data_szl] = self.PDU[41:41 + data_szl]
                            offset += data_szl
                            szl_buffer.Header.LENTHDR += szl_buffer.Header.LENTHDR
                        else:
                            self._last_error = S7.errCliInvalidPlcAnswer
                    else:
                        self._last_error = S7.errIsoInvalidPDU
                else:
                    if length > 32:  # Minimum expected
                        if S7.get_word_at(self.PDU, 27) == 0 and self.PDU[29] == 0xFF:
                            data_szl = S7.get_word_at(self.PDU, 31)
                            done = self.PDU[26] == 0x00
                            seq_in = self.PDU[24]  # Slice sequence
                            szl_buffer.Data[offset:offset + data_szl] = self.PDU[37:37 + data_szl]
                            offset += data_szl
                            szl_buffer.Header.LENTHDR += szl_buffer.Header.LENTHDR
                        else:
                            self._last_error = S7.errCliInvalidPlcAnswer
                    else:
                        self._last_error = S7.errIsoInvalidPDU
            first = False

        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def get_cpu_info(self, info: S7CpuInfo) -> int:
        szl = S7SZL(1024)

        elapsed = int(time.time() * 1000)

        self._last_error = self.read_SZL(0x001C, 0x000, szl)

        if self._last_error == 0:
            info.ModuleTypeName = S7.get_chars_at(szl.Data, 172, 32)
            info.SerialNumber = S7.get_chars_at(szl.Data, 138, 24)
            info.ASName = S7.get_chars_at(szl.Data, 2, 24)
            info.Copyright = S7.get_chars_at(szl.Data, 104, 26)
            info.ModuleName = S7.get_chars_at(szl.Data, 36, 24)
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def get_cp_info(self, cp : S7CpInfo):
        szl = S7SZL(1024)

        elapsed = int(time.time() * 1000)

        self._last_error = self.read_SZL(0x0131, 0x0001, szl)
        if  self._last_error == 0:
            cp.MaxPduLength = S7.get_int_at(szl.Data, 2)
            # cp.MaxConnections = S7.get_int_at(szl.Data, 4)
            # cp.MaxMpiRate = S7.get_int_at(szl.Data, 6)
            # TODO : ??? Max Connections inverted with Max MPI Rate ???
            cp.MaxConnections = S7.get_int_at(szl.Data, 6)
            cp.MaxMpiRate = S7.get_int_at(szl.Data, 4)
            cp.MaxBusRate = S7.get_int_at(szl.Data, 10)
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def get_protection(self, protect : S7Protection):
        szl = S7SZL(1024)

        elapsed = int(time.time() * 1000)

        self._last_error = self.read_SZL(0x0232, 0x0004, szl)

        if self._last_error == 0:
            protect.sch_schal = S7.get_word_at(szl.Data, 2)
            protect.sch_par = S7.get_word_at(szl.Data, 4)
            protect.sch_rel = S7.get_word_at(szl.Data, 6)
            protect.bart_sch = S7.get_word_at(szl.Data, 8)
            protect.anl_sch = S7.get_word_at(szl.Data, 10)
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def get_order_code(self, order_code: S7OrderCode):
        szl = S7SZL(1024)

        elapsed = int(time.time() * 1000)

        self._last_error = self.read_SZL(0x0131, 0x000, szl)

        if self._last_error == 0:
            order_code.OrderCode = S7.get_chars_at(szl.Data, 2, 20)
            order_code.V1 = szl.Data[-3]
            order_code.V2 = szl.Data[-2]
            order_code.V3 = szl.Data[-1]
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def get_cpu_state(self,  status_ref: dict):
        self._last_error = 0
        elapsed = int(time.time() * 1000)

        self.send_packet(S7.S7_GET_STAT)
        if self._last_error != 0:
            return self._last_error

        length = self.recv_iso_packet()

        if length <= 30:
            self._last_error = S7.errIsoInvalidPDU
            return self._last_error

        result = S7.get_word_at(self.PDU, 27)
        if result == 0:
            state_value = self.PDU[44]
            status_ref["cpu_state"] = state_value
        else:
            self._last_error = S7.errCliInvalidPlcAnswer

        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def set_session_password(self, password: str) -> int:
        pwd = [0x20] * 8  # 8 spaces
        self._last_error = 0

        elapsed = int(time.time() * 1000)

        # SetCharsAt equivalent: copy up to 8 chars into pwd
        for i in range(min(len(password), 8)):
            pwd[i] = ord(password[i])

        pwd[0] = (pwd[0] ^ 0x55)
        pwd[1] = (pwd[1] ^ 0x55)

        for c in range(2, 8):
            pwd[c] ^= 0x55 ^ pwd[c - 2]

        # Copy pwd to S7_SET_PWD at offset 29
        s7_set_password = S7.S7_SET_PWD.copy()  # Copy to avoid modifying original
        for i in range(8):
            s7_set_password[29 + i] = pwd[i]

        # Send the telegram
        self.send_packet(s7_set_password)
        if self._last_error == 0:
            length = self.recv_iso_packet()
            if length > 32:
                result = S7.get_word_at(self.PDU,27)
                if result != 0:
                    self._last_error = S7.cpu_error(result)
            else:
                self._last_error = S7.errIsoInvalidPDU

        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed
        return self._last_error

    def clear_session_password(self) -> int:
        self._last_error = 0
        elapsed = int(time.time() * 1000)

        self.send_packet(S7.S7_CLR_PWD)
        if self._last_error == 0:
            length = self.recv_iso_packet()
            if length > 30:
                result = S7.get_word_at(self.PDU, 27)
                if result != 0:
                    self._last_error = S7.cpu_error(result)
            else:
                self._last_error = S7.errIsoInvalidPDU

        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed

        return self._last_error

    def get_exec_time(self):
        return self._time_ms

    def get_last_error(self):
        return self._last_error

    def recv_packet(self, buffer, start, size):
        if self.connected:
            self._last_error = self.socket.receive(buffer, start, size)
        else:
            self._last_error = S7.errTCPNotConnected

    def send_packet(self, buffer, length=None):
        if length is None:
            length = len(buffer)
        if not self.connected:
            self._last_error = S7.errTCPNotConnected
        else:
            self._last_error = self.socket.send(buffer, length)

    def recv_iso_packet(self):
        done = False
        size = 0
        while self._last_error == 0 and not done:
            self.recv_packet(self.PDU, 0, 4)
            if self._last_error == 0:
                size = struct.unpack(">H", self.PDU[2:4])[0]
                if size == 7:
                    self.recv_packet(self.PDU, 4, 3)
                else:
                    if size > self._size_requested_PDU + 7 or size < 16:
                        self._last_error = S7.errIsoInvalidPDU
                    else:
                        done = True

        if self._last_error == 0:
            self.recv_packet(self.PDU, 4, 3)
            self._last_PDU_type = self.PDU[5]
            self.recv_packet(self.PDU, 7, size - 7)
        return size if self._last_error == 0 else 0

    def iso_connect(self):
        iso_cr = S7.ISO_CR.copy()  # Copy to avoid modifying the original
        iso_cr[16] = self.local_TSAP_high
        iso_cr[17] = self.local_TSAP_low
        iso_cr[20] = self.remote_TSAP_high
        iso_cr[21] = self.remote_TSAP_low
        self.send_packet(iso_cr)
        if self._last_error == 0:
            size = self.recv_iso_packet()
            if self._last_error == 0:
                if size == 22:
                    if self._last_PDU_type != 0xD0:
                        self._last_error = S7.errIsoConnect
                else:
                    self._last_error = S7.errIsoInvalidPDU
        return self._last_error

    def negotiate_pdu_length(self):
        pn_message = S7.S7_PN.copy()  # Create a copy to avoid modifying the original
        S7.set_word_at(pn_message, 23, self._size_requested_PDU)
        self.send_packet(pn_message)
        if self._last_error == 0:
            length = self.recv_iso_packet()
            if self._last_error == 0:
                if length == 27 and self.PDU[17] == 0 and self.PDU[18] == 0:
                    plength = S7.get_word_at(self.PDU, 25)
                    if plength > 0:
                        self._length_PDU = plength  # Store the negotiated PDU length
                    else:
                        self._last_error = S7.errCliNegotiatingPDU
                else:
                    self._last_error = S7.errCliNegotiatingPDU
        return self._last_error

    def __del__(self):
        self.disconnect()

    def set_connection_type(self, connection_type):
        self.conn_type = connection_type
        return 0

    def disconnect(self) -> bool:
        self.socket.close()
        return True

    def get_param(self, param_number):
        return {
            S7.p_u16_RemotePort: self._port_PLC,
            S7.p_i32_PingTimeout: self._conn_timeout,
            S7.p_i32_SendTimeout: self._send_timeout,
            S7.p_i32_RecvTimeout: self._recv_timeout,
            S7.p_i32_PDURequest: self._size_requested_PDU,
        }.get(param_number, S7.errCliInvalidParamNumber)

    def set_param(self, param_number, value):
        if param_number == S7.p_u16_RemotePort:
            self._port_PLC = value
        elif param_number == S7.p_i32_PingTimeout:
            self._conn_timeout = value
        elif param_number == S7.p_i32_SendTimeout:
            self._send_timeout = value
        elif param_number == S7.p_i32_RecvTimeout:
            self._recv_timeout = value
        elif param_number == S7.p_i32_PDURequest:
            self._size_requested_PDU = value
        else:
            return S7.errCliInvalidParamNumber
        return 0

    def tcp_connect(self):
        if self._last_error == 0:
            try:
                # Assuming `self.Socket` is a socket object
                self.socket.connect(self._address_PLC, self._port_PLC)
            except Exception:
                self._last_error = S7.errTCPConnectionFailed
        return self._last_error

    def ab_read(self, start: int, size: int, buffer: bytearray) -> int:
        return self.read_area(S7.S7AreaPA, start, size, S7.S7WLByte, buffer)

    def db_read(self, db_number: int, start: int, size: int, buffer: bytearray) -> int:
        return self.read_area(S7.S7AreaDB, start, size, S7.S7WLByte, buffer, db_number)

    def mb_read(self, start: int, size: int, buffer: bytearray) -> int:
        return self.read_area(S7.S7AreaMK, start, size, S7.S7WLByte, buffer)

    def eb_read(self, start: int, size: int, buffer: bytearray) -> int:
        return self.read_area(S7.S7AreaPE, start, size, S7.S7WLByte, buffer)

    def read_area(self,
                  area: int,
                  start: int,
                  amount: int,
                  word_len: int,
                  buffer : bytearray,
                  db_number : int = 0):

        offset = 0
        self._last_error = 0
        self._time_ms = 0
        elapsed = time.time()

        if area == S7.S7AreaCT:
            word_len = S7.S7WLCounter
        if area == S7.S7AreaTM:
            word_len = S7.S7WLTimer

        word_size = WordLen(word_len).data_size_bytes
        if word_size == 0:
            return S7.errCliInvalidWordLen

        if word_len == S7.S7WLBit:
            amount = 1
        else:
            if word_len not in (S7.S7WLCounter, S7.S7WLTimer):
                amount *= word_size
                word_size = 1
                word_len = S7.S7WLByte

        max_elements = (self._length_PDU - 18) if self._length_PDU > 18 else (self._size_requested_PDU - 18)
        tot_elements = amount

        while tot_elements > 0 and self._last_error == 0:
            num_elements = min(tot_elements, max_elements)
            size_requested = num_elements * word_size
            self.PDU[: S7.size_RD] = S7.S7_RW[: S7.size_RD]
            self.PDU[27] = area

            if area == S7.S7AreaDB:
                S7.set_word_at(self.PDU, 25, db_number)

            if word_len in (S7.S7WLBit, S7.S7WLCounter, S7.S7WLTimer):
                address = start
                self.PDU[22] = word_len
            else:
                address = start << 3

            S7.set_word_at(self.PDU, 23, num_elements)
            self.PDU[30] = address & 0xFF
            address >>= 8
            self.PDU[29] = address & 0xFF
            address >>= 8
            self.PDU[28] = address & 0xFF

            self.send_packet(self.PDU, S7.size_RD)

            if self._last_error == 0:
                length = self.recv_iso_packet()
                if self._last_error == 0:
                    if length < 25:
                        self._last_error = S7.errIsoInvalidDataSize
                    else:
                        if self.PDU[21] != 0xFF:
                            self._last_error = S7.cpu_error(self.PDU[21])
                        else:
                            buffer[offset : offset + size_requested] = self.PDU[25 : 25 + size_requested]
                            offset += size_requested

            tot_elements -= num_elements
            start += num_elements * word_size

        if self._last_error == 0:
            bytes_read = offset
            self._time_ms = int((time.time() - elapsed) * 1000)
        else:
            bytes_read = 0

        return self._last_error

    # Convenience methods for reading different data types
    def read_bool(self, area: int, start: int, bit: int, db_number: int = 0) -> tuple[int, bool]:
        """Read a single boolean value"""
        buffer = bytearray(1)
        error = self.read_area(area, start, 1, S7.S7WLByte, buffer, db_number)
        if error == 0:
            return error, S7.GetBitAt(buffer, 0, bit)
        return error, False

    def read_int(self, area: int, start: int, db_number: int = 0) -> tuple[int, int]:
        """Read a 16-bit signed integer"""
        buffer = bytearray(2)
        error = self.read_area(area, start, 2, S7.S7WLByte, buffer, db_number)
        if error == 0:
            return error, S7.get_int_at(buffer, 0)
        return error, 0

    def read_word(self, area: int, start: int, db_number: int = 0) -> tuple[int, int]:
        """Read a 16-bit unsigned integer"""
        buffer = bytearray(2)
        error = self.read_area(area, start, 2, S7.S7WLByte, buffer, db_number)
        if error == 0:
            return error, S7.get_word_at(buffer, 0)
        return error, 0

    def read_dword(self, area: int, start: int, db_number: int = 0) -> tuple[int, int]:
        """Read a 32-bit unsigned integer"""
        buffer = bytearray(4)
        error = self.read_area(area, start, 4, S7.S7WLByte, buffer, db_number)
        if error == 0:
            return error, S7.GetDWordAt(buffer, 0)
        return error, 0

    def read_real(self, area: int, start: int, db_number: int = 0) -> tuple[int, float]:
        """Read a 32-bit real (float) value"""
        buffer = bytearray(4)
        error = self.read_area(area, start, 4, S7.S7WLByte, buffer, db_number)
        if error == 0:
            return error, S7.GetRealAt(buffer, 0)
        return error, 0.0

    def read_string(self, area: int, start: int, max_len: int, db_number: int = 0) -> tuple[int, str]:
        """Read a string value"""
        buffer = bytearray(max_len + 2)  # +2 for length bytes
        error = self.read_area(area, start, max_len + 2, S7.S7WLByte, buffer, db_number)
        if error == 0:
            return error, S7.GetStringAt(buffer, 0)
        return error, ""

    # Convenience methods for writing different data types
    def write_bool(self, area: int, start: int, bit: int, value: bool, db_number: int = 0) -> int:
        """Write a single boolean value"""
        buffer = bytearray(1)
        # First read the current byte
        read_error = self.read_area(area, start, 1, S7.S7WLByte, buffer, db_number)
        if read_error != 0:
            return read_error
        
        # Modify the specific bit
        S7.SetBitAt(buffer, 0, bit, value)
        
        # Write back the modified byte
        return self.write_area(area, start, 1, S7.S7WLByte, buffer, db_number)

    def write_int(self, area: int, start: int, value: int, db_number: int = 0) -> int:
        """Write a 16-bit signed integer"""
        buffer = bytearray(2)
        S7.SetIntAt(buffer, 0, value)
        return self.write_area(area, start, 2, S7.S7WLByte, buffer, db_number)

    def write_word(self, area: int, start: int, value: int, db_number: int = 0) -> int:
        """Write a 16-bit unsigned integer"""
        buffer = bytearray(2)
        S7.set_word_at(buffer, 0, value)
        return self.write_area(area, start, 2, S7.S7WLByte, buffer, db_number)

    def write_dword(self, area: int, start: int, value: int, db_number: int = 0) -> int:
        """Write a 32-bit unsigned integer"""
        buffer = bytearray(4)
        S7.SetDWordAt(buffer, 0, value)
        return self.write_area(area, start, 4, S7.S7WLByte, buffer, db_number)

    def write_real(self, area: int, start: int, value: float, db_number: int = 0) -> int:
        """Write a 32-bit real (float) value"""
        buffer = bytearray(4)
        S7.SetRealAt(buffer, 0, value)
        return self.write_area(area, start, 4, S7.S7WLByte, buffer, db_number)

    def write_string(self, area: int, start: int, value: str, max_len: int, db_number: int = 0) -> int:
        """Write a string value"""
        buffer = bytearray(max_len + 2)  # +2 for length bytes
        S7.SetStringAt(buffer, 0, max_len, value)
        return self.write_area(area, start, max_len + 2, S7.S7WLByte, buffer, db_number)


    def ab_write(self, start: int, size: int, buffer: bytearray) -> int:
        return self.write_area(S7.S7AreaPA, start, size, S7.S7WLByte, buffer)

    def db_write(self, db_number: int, start: int, size: int, buffer: bytearray) -> int:
        return self.write_area(S7.S7AreaDB, start, size, S7.S7WLByte, buffer, db_number)

    def mb_write(self, start: int, size: int, buffer: bytearray) -> int:
        return self.write_area(S7.S7AreaMK, start, size, S7.S7WLByte, buffer)

    def eb_write(self, start: int, size: int, buffer: bytearray) -> int:
        return self.write_area(S7.S7AreaPE, start, size, S7.S7WLByte, buffer)

    def write_area(self,
                   area : int,
                   start : int,
                   amount : int,
                   word_len : int,
                   buffer : bytearray,
                   db_number : int = 0):
        address = 0
        num_elements = 0
        max_elements = 0
        tot_elements = 0
        data_size = 0
        iso_size = 0
        length = 0
        offset = 0
        word_size = 1
        self._last_error = 0
        self._time_ms = 0
        elapsed = time.time()

        if area == S7.S7AreaCT:
            word_len = S7.S7WLCounter
        if area == S7.S7AreaTM:
            word_len = S7.S7WLTimer

        word_size = WordLen(word_len).data_size_bytes
        if word_size == 0:
            return S7.errCliInvalidWordLen

        if word_len == S7.S7WLBit:
            amount = 1
        else:
            if word_len not in (S7.S7WLCounter, S7.S7WLTimer):
                amount *= word_size
                word_size = 1
                word_len = S7.S7WLByte

        max_elements = (self._length_PDU - 35) // word_size if self._length_PDU > 35 else (self._size_requested_PDU - 35) // word_size
        tot_elements = amount

        while tot_elements > 0 and self._last_error == 0:
            num_elements = min(tot_elements, max_elements)
            data_size = num_elements * word_size
            iso_size = S7.size_WR + data_size
            self.PDU[: S7.size_WR] = S7.S7_RW[: S7.size_WR]
            S7.set_word_at(self.PDU, 2, iso_size)
            length = data_size + 4
            S7.set_word_at(self.PDU, 15, length)
            self.PDU[17] = 0x05
            self.PDU[27] = area

            if area == S7.S7AreaDB:
                S7.set_word_at(self.PDU, 25, db_number)

            if word_len in (S7.S7WLBit, S7.S7WLCounter, S7.S7WLTimer):
                address = start
                length = data_size
                self.PDU[22] = word_len
            else:
                address = start << 3
                length = data_size << 3

            S7.set_word_at(self.PDU, 23, num_elements)
            self.PDU[30] = address & 0xFF
            address >>= 8
            self.PDU[29] = address & 0xFF
            address >>= 8
            self.PDU[28] = address & 0xFF

            if word_len == S7.S7WLBit:
                self.PDU[32] = S7.TS_ResBit
            elif word_len in (S7.S7WLCounter, S7.S7WLTimer):
                self.PDU[32] = S7.TS_ResOctet
            else:
                self.PDU[32] = S7.TS_ResByte

            S7.set_word_at(self.PDU, 33, length)
            self.PDU[35 : 35 + data_size] = buffer[offset : offset + data_size]
            self.send_packet(self.PDU, iso_size)

            if self._last_error == 0:
                length = self.recv_iso_packet()
                if self._last_error == 0:
                    if length == 22:
                        if self.PDU[21] != 0xFF:
                            self._last_error = S7.cpu_error(self.PDU[21])
                    else:
                        self._last_error = S7.errIsoInvalidPDU

            offset += data_size
            tot_elements -= num_elements
            start += num_elements * word_size

        if self._last_error == 0:
            bytes_written = offset
            self._time_ms = int((time.time() - elapsed) * 1000)
        else:
            bytes_written = 0

        return self._last_error

    # Sharp7-compatible functions

    def get_ag_block_info(self, block_type: int, block_num: int, block_info: TS7BlockInfo) -> int:
        """
        Get information about a block (similar to Sharp7 GetAgBlockInfo)
        """
        # This is a simplified implementation - in a full implementation,
        # this would send the appropriate S7 protocol messages to get block info
        # For now, we'll implement a basic version that works with db_get and db_fill
        
        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)
        
        if not self.connected:
            self._last_error = S7.errTCPNotConnected
            return self._last_error
            
        # For DB blocks, we can estimate size by trying to read
        # This is a simplified approach - real implementation would use SZL queries
        if block_type == Block.DB:
            # Try reading progressively larger chunks to find the actual DB size
            # Start with a reasonable default
            test_sizes = [1, 10, 100, 1000, 8192]  # Common DB sizes
            
            block_info.BlkType = block_type
            block_info.BlkNumber = block_num
            block_info.BlkLang = 0  # Unknown
            block_info.BlkFlags = 0
            block_info.MC7Size = 0  # Will be determined
            block_info.LoadSize = 0
            block_info.LocalData = 0
            block_info.SBBLength = 0
            block_info.CheckSum = 0
            block_info.Version = 0
            
            # Try to determine actual size by testing reads
            max_size = 0
            test_buffer = bytearray(8192)
            
            for test_size in test_sizes:
                error = self.read_area(S7.S7AreaDB, 0, test_size, S7.S7WLByte, test_buffer, block_num)
                if error == 0:
                    max_size = test_size
                elif error == S7.errCliAddressOutOfRange:
                    break
                    
            # Binary search for exact size if we found a working size
            if max_size > 0:
                low = max_size
                high = max_size * 10
                
                # Find upper bound
                while high <= 65536:  # Max reasonable DB size
                    error = self.read_area(S7.S7AreaDB, 0, high, S7.S7WLByte, test_buffer, block_num)
                    if error == 0:
                        low = high
                        high *= 2
                    else:
                        break
                        
                # Binary search for exact size
                while low < high - 1:
                    mid = (low + high) // 2
                    error = self.read_area(S7.S7AreaDB, 0, mid, S7.S7WLByte, test_buffer, block_num)
                    if error == 0:
                        low = mid
                    else:
                        high = mid
                        
                block_info.MC7Size = low
            else:
                # Default size or error determining size
                block_info.MC7Size = 1024  # Default size
                
        else:
            self._last_error = S7.errCliInvalidBlockType
            
        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed
            
        return self._last_error

    def db_get(self, db_number: int, usr_data: bytearray) -> tuple[int, int]:
        """
        Get entire DB block (Sharp7 compatible)
        Returns tuple of (error_code, actual_size)
        """
        block_info = TS7BlockInfo()
        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)
        
        # Get block information first
        self._last_error = self.get_ag_block_info(Block.DB, db_number, block_info)
        
        if self._last_error == 0:
            db_size = block_info.MC7Size
            if db_size <= len(usr_data):
                # Read the entire DB
                self._last_error = self.db_read(db_number, 0, db_size, usr_data)
                if self._last_error == 0:
                    actual_size = db_size
                else:
                    actual_size = 0
            else:
                self._last_error = S7.errCliBufferTooSmall
                actual_size = 0
        else:
            actual_size = 0
            
        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed
            
        return self._last_error, actual_size

    def db_fill(self, db_number: int, fill_char: int) -> int:
        """
        Fill entire DB block with specified byte value (Sharp7 compatible)
        """
        block_info = TS7BlockInfo()
        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)
        
        # Get block information first
        self._last_error = self.get_ag_block_info(Block.DB, db_number, block_info)
        
        if self._last_error == 0:
            db_size = block_info.MC7Size
            # Create buffer filled with the specified character
            buffer = bytearray([fill_char & 0xFF] * db_size)
            self._last_error = self.db_write(db_number, 0, db_size, buffer)
            
        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed
            
        return self._last_error

    def write_multi_vars(self, items: list, items_count: int) -> int:
        """
        Write multiple variables in one operation (Sharp7 compatible)
        Items should be a list of S7DataItem structures or dictionaries with the same fields
        """
        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)
        
        # Check parameter limits
        if items_count > 20:  # MaxVars equivalent
            return S7.errCliTooManyItems
            
        if items_count == 0:
            return 0
            
        # For now, implement as sequential writes
        # A full implementation would use the multi-var protocol
        for i in range(items_count):
            item = items[i]
            
            # Handle both S7DataItem objects and dictionaries
            if hasattr(item, 'Area'):
                area = item.Area
                start = item.Start  
                db_number = item.DBNumber
                amount = item.Amount
                word_len = item.WordLen
                # Get data from pointer or data field
                if hasattr(item, 'pData') and item.pData:
                    # This would need proper pointer handling in a full implementation
                    data = bytearray(amount)  # Placeholder
                elif hasattr(item, 'data'):
                    data = item.data
                else:
                    data = bytearray(amount)
            else:
                # Dictionary format
                area = item.get('Area', 0)
                start = item.get('Start', 0)
                db_number = item.get('DBNumber', 0) 
                amount = item.get('Amount', 0)
                word_len = item.get('WordLen', S7.S7WLByte)
                data = item.get('data', bytearray(amount))
                
            # Write the data
            self._last_error = self.write_area(area, start, amount, word_len, data, db_number)
            
            # Set result for this item
            if hasattr(item, 'Result'):
                item.Result = self._last_error
            elif isinstance(item, dict):
                item['Result'] = self._last_error
                
            # Stop on first error
            if self._last_error != 0:
                break
                
        if self._last_error == 0:
            self._time_ms = int(time.time() * 1000) - elapsed
            
        return self._last_error

    # ========================================================================
    # Additional Sharp7 Compatible Methods
    # ========================================================================

    def tm_read(self, start: int, amount: int, buffer: list) -> int:
        """Read Timer values from PLC.
        
        Args:
            start: Start timer number
            amount: Number of timers to read
            buffer: List to store timer values (will be filled with ushort values)
            
        Returns:
            Error code (0 = success)
        """
        s_buffer = bytearray(amount * 2)
        result = self.read_area(S7.S7AreaTM, 0, start, amount, S7.S7WLTimer, s_buffer)
        if result == 0:
            buffer.clear()
            for c in range(amount):
                value = (s_buffer[c * 2 + 1] << 8) + s_buffer[c * 2]
                buffer.append(value)
        return result

    def tm_write(self, start: int, amount: int, buffer: list) -> int:
        """Write Timer values to PLC.
        
        Args:
            start: Start timer number
            amount: Number of timers to write
            buffer: List of timer values (ushort values)
            
        Returns:
            Error code (0 = success)
        """
        s_buffer = bytearray(amount * 2)
        for c in range(amount):
            value = buffer[c] & 0xFFFF
            s_buffer[c * 2] = value & 0xFF
            s_buffer[c * 2 + 1] = (value >> 8) & 0xFF
        return self.write_area(S7.S7AreaTM, start, amount, S7.S7WLTimer, s_buffer)

    def ct_read(self, start: int, amount: int, buffer: list) -> int:
        """Read Counter values from PLC.
        
        Args:
            start: Start counter number
            amount: Number of counters to read
            buffer: List to store counter values (will be filled with ushort values)
            
        Returns:
            Error code (0 = success)
        """
        s_buffer = bytearray(amount * 2)
        result = self.read_area(S7.S7AreaCT,  start, amount, S7.S7WLCounter, s_buffer)
        if result == 0:
            buffer.clear()
            for c in range(amount):
                value = (s_buffer[c * 2 + 1] << 8) + s_buffer[c * 2]
                buffer.append(value)
        return result

    def ct_write(self, start: int, amount: int, buffer: list) -> int:
        """Write Counter values to PLC.
        
        Args:
            start: Start counter number
            amount: Number of counters to write
            buffer: List of counter values (ushort values)
            
        Returns:
            Error code (0 = success)
        """
        s_buffer = bytearray(amount * 2)
        for c in range(amount):
            value = buffer[c] & 0xFFFF
            s_buffer[c * 2] = value & 0xFF
            s_buffer[c * 2 + 1] = (value >> 8) & 0xFF
        return self.write_area(S7.S7AreaCT,  start, amount, S7.S7WLCounter, s_buffer)

    def delete(self, block_type: int, block_num: int) -> int:
        # TODO: Implement block deletion if needed
        return S7.errCliFunctionNotImplemented

    def get_pg_block_info(self, info: dict, buffer: bytearray, size: int) -> int:
        # TODO: Implement block deletion if needed
        return S7.errCliFunctionNotImplemented

    def get_plc_date_time(self, dt_ref: list) -> int:
        # TODO: Implement reading PLC date/time if needed
        return S7.errCliFunctionNotImplemented


    def set_plc_date_time(self, dt) -> int:
        # TODO: Implement reading PLC date/time if needed
        return S7.errCliFunctionNotImplemented


    def plc_hot_start(self) -> int:
        # TODO: Implement this function if needed
        return S7.errCliFunctionNotImplemented

    def plc_cold_start(self) -> int:
        # TODO: Implement this function if needed
        return S7.errCliFunctionNotImplemented

    def plc_stop(self) -> int:
        # TODO: Implement this function if needed
        return S7.errCliFunctionNotImplemented

    def plc_compress(self, timeout: int) -> int:
        # TODO: Implement this function if needed
        return S7.errCliFunctionNotImplemented

    def plc_copy_ram_to_rom(self, timeout: int) -> int:
        # TODO: Implement this function if needed
        return S7.errCliFunctionNotImplemented

    def read_szl_list(self, szl_list_ref: list, items_count_ref: list) -> int:
        """
        Read the list of available SZL (System Zone List) from the PLC.

        Args:
            szl_list_ref: List to store tuples of (SZL ID, SZL Index)
            items_count_ref: List with one element to store the count of items read

        Returns:
            Error code (0 = success)
        """
        self._last_error = 0
        self._time_ms = 0
        elapsed = int(time.time() * 1000)
        if not self.connected:
            self._last_error = S7.errTCPNotConnected
            return self._last_error
        szl = S7SZL(1024)
        self._last_error = self.read_SZL(0x0000, 0x0000, szl)
        if self._last_error == 0:
            count = szl.Header.N_DR
            szl_list_ref.clear()
            for i in range(count):
                szl_id = S7.get_word_at(szl.Data, i * 4)
                szl_index = S7.get_word_at(szl.Data, i * 4 + 2)
                szl_list_ref.append((szl_id, szl_index))
            items_count_ref[0] = count
            self._time_ms = int(time.time() * 1000) - elapsed
        return self._last_error




    # Convenience properties for Sharp7 compatibility
    @property
    def last_error(self) -> int:
        """Get last error code."""
        return self._last_error

    @property 
    def exec_time(self) -> int:
        """Get execution time in milliseconds."""
        return self._time_ms

    @property
    def pdu_requested(self) -> int:
        """Get requested PDU length."""
        return self._size_requested_PDU

    @property
    def pdu_length(self) -> int:
        """Get negotiated PDU length."""
        return self._length_PDU

    def requested_pdu_length(self) -> int:
        """Get requested PDU length.
        
        Returns:
            Requested PDU length
        """
        return self._size_requested_PDU

    def negotiated_pdu_length(self) -> int:
        """Get negotiated PDU length.
        
        Returns:
            Negotiated PDU length
        """
        return self._length_PDU

    @property
    def plc_status(self) -> int:
        """Get PLC status."""
        # This would need actual implementation
        return 0

    def drv_connect_to(self, address: str, rack: int = 0, slot: int = 3) -> int:
        """Connect to PLC using Drive protocol.
        
        Args:
            address: PLC IP address
            rack: Rack number (default 0)
            slot: Slot number (default 3)
            
        Returns:
            Error code (0 = success)
        """
        remote_tsap = (self.conn_type << 8) + (rack * 0x20) + slot
        self.set_connection_params(address, 0x0100, remote_tsap)
        return self.connect()

    def nck_connect_to(self, address: str, rack: int = 0) -> int:
        """Connect to Sinumerik NCK.
        
        Args:
            address: PLC IP address  
            rack: Rack number (default 0)
            
        Returns:
            Error code (0 = success)
        """
        remote_tsap = (self.conn_type << 8) + (rack * 0x20) + 3
        self.set_connection_params(address, 0x0100, remote_tsap)
        return self.connect()


    def as_read_area(self, area: int, db_number: int, start: int, amount: int, word_len: int, buffer: bytearray) -> int:
        """Async read area from PLC.
        
        Args:
            area: Memory area to read from
            db_number: DB number (if area is DB)
            start: Start address
            amount: Amount to read
            word_len: Word length
            buffer: Buffer to store data
            
        Returns:
            Error code (0 = success)
        """
        return self.read_area(area, start, amount, word_len, buffer, db_number)

    def as_write_area(self, area: int, db_number: int, start: int, amount: int, word_len: int, buffer: bytearray) -> int:
        """Async write area to PLC.
        
        Args:
            area: Memory area to write to
            db_number: DB number (if area is DB)
            start: Start address
            amount: Amount to write
            word_len: Word length
            buffer: Buffer containing data
            
        Returns:
            Error code (0 = success)
        """
        return self.write_area(area, start, amount, word_len, buffer, db_number)

    def as_db_read(self, db_number: int, start: int, size: int, buffer: bytearray) -> int:
        """Async DB read from PLC.
        
        Args:
            db_number: DB number to read from
            start: Start address
            size: Size to read
            buffer: Buffer to store data
            
        Returns:
            Error code (0 = success)
        """
        return self.db_read(db_number, start, size, buffer)

    def as_db_write(self, db_number: int, start: int, size: int, buffer: bytearray) -> int:
        """Async DB write to PLC.
        
        Args:
            db_number: DB number to write to
            start: Start address
            size: Size to write
            buffer: Buffer containing data
            
        Returns:
            Error code (0 = success)
        """
        return self.db_write(db_number, start, size, buffer)

    def as_db_get(self, db_number: int, usr_data: bytearray, size_ref: list) -> int:
        """Async get entire DB from PLC.
        
        Args:
            db_number: DB number to read
            usr_data: Buffer to store data
            size_ref: Reference to size (list with one element)
            
        Returns:
            Error code (0 = success)
        """
        return self.db_get(db_number, usr_data, size_ref)

    def as_db_fill(self, db_number: int, fill_char: int) -> int:
        """Async fill DB with character.
        
        Args:
            db_number: DB number to fill
            fill_char: Character to fill with
            
        Returns:
            Error code (0 = success)
        """
        return self.db_fill(db_number, fill_char)

    def as_upload(self, block_type: int, block_num: int, usr_data: bytearray, size_ref: list) -> int:
        """Async upload block from PLC.
        
        Args:
            block_type: Type of block to upload
            block_num: Number of block to upload
            usr_data: Buffer to store uploaded data
            size_ref: Reference to size (list with one element)
            
        Returns:
            Error code (0 = success)
        """
        return self.upload(block_type, block_num, usr_data, size_ref)

    def as_full_upload(self, block_type: int, block_num: int, usr_data: bytearray, size_ref: list) -> int:
        """Async full upload block from PLC.
        
        Args:
            block_type: Type of block to upload
            block_num: Number of block to upload
            usr_data: Buffer to store uploaded data
            size_ref: Reference to size (list with one element)
            
        Returns:
            Error code (0 = success)
        """
        return self.full_upload(block_type, block_num, usr_data, size_ref)

    def as_list_blocks_of_type(self, block_type: int, block_list: list, items_count_ref: list) -> int:
        """Async list blocks of specific type.
        
        Args:
            block_type: Type of blocks to list
            block_list: List to store block numbers
            items_count_ref: Reference to items count (list with one element)
            
        Returns:
            Error code (0 = success)
        """
        return self.list_blocks_of_type(block_type, block_list, items_count_ref)

    def as_read_szl(self, id: int, index: int, szl_ref: list, size_ref: list) -> int:
        """Async read SZL from PLC.
        
        Args:
            id: SZL ID
            index: SZL index
            szl_ref: Reference to SZL (list with one element)
            size_ref: Reference to size (list with one element)
            
        Returns:
            Error code (0 = success)
        """
        return self.read_SZL(id, index, szl_ref[0], size_ref)

    def as_read_szl_list(self, szl_list_ref: list, items_count_ref: list) -> int:
        """Async read SZL list from PLC.
        
        Args:
            szl_list_ref: Reference to SZL list (list with one element)
            items_count_ref: Reference to items count (list with one element)
            
        Returns:
            Error code (0 = success)
        """
        return self.read_szl_list(szl_list_ref, items_count_ref)

    def as_tm_read(self, start: int, amount: int, buffer: list) -> int:
        """Async timer read from PLC.
        
        Args:
            start: Start timer number
            amount: Number of timers to read
            buffer: List to store timer values
            
        Returns:
            Error code (0 = success)
        """
        return self.tm_read(start, amount, buffer)

    def as_tm_write(self, start: int, amount: int, buffer: list) -> int:
        """Async timer write to PLC.
        
        Args:
            start: Start timer number
            amount: Number of timers to write
            buffer: List of timer values
            
        Returns:
            Error code (0 = success)
        """
        return self.tm_write(start, amount, buffer)

    def as_ct_read(self, start: int, amount: int, buffer: list) -> int:
        """Async counter read from PLC.
        
        Args:
            start: Start counter number
            amount: Number of counters to read
            buffer: List to store counter values
            
        Returns:
            Error code (0 = success)
        """
        return self.ct_read(start, amount, buffer)

    def as_ct_write(self, start: int, amount: int, buffer: list) -> int:
        """Async counter write to PLC.
        
        Args:
            start: Start counter number
            amount: Number of counters to write
            buffer: List of counter values
            
        Returns:
            Error code (0 = success)
        """
        return self.ct_write(start, amount, buffer)

    def as_plc_copy_ram_to_rom(self, timeout: int) -> int:
        """Async copy RAM to ROM in PLC.
        
        Args:
            timeout: Timeout in milliseconds
            
        Returns:
            Error code (0 = success)
        """
        return self.plc_copy_ram_to_rom(timeout)

    def as_plc_compress(self, timeout: int) -> int:
        """Async compress PLC memory.
        
        Args:
            timeout: Timeout in milliseconds
            
        Returns:
            Error code (0 = success)
        """
        return self.plc_compress(timeout)

    # ========================================================================
    # Async Support Methods
    # ========================================================================

    def check_as_completion(self, op_result_ref: list) -> int:
        """Check async operation completion.
        
        Args:
            op_result_ref: Reference to operation result (list with one element)
            
        Returns:
            Job status (0 = complete)
        """
        # In a real async implementation, this would check job status
        op_result_ref[0] = 0  # Assume completed successfully
        return 0

    def wait_as_completion(self, timeout: int) -> int:
        """Wait for async operation completion.
        
        Args:
            timeout: Timeout in milliseconds
            
        Returns:
            Error code (0 = success)
        """
        # In a real async implementation, this would wait for completion
        return 0

    def set_as_callback(self, callback, usr_ptr) -> int:
        """Set async completion callback.
        
        Args:
            callback: Callback function
            usr_ptr: User pointer for callback
            
        Returns:
            Error code (0 = success)
        """
        # This is a placeholder for async callback functionality
        return S7.errCliFunctionNotImplemented

    # ========================================================================
    # Sinumerik Drive/NCK Methods (Placeholders)
    # ========================================================================

    def read_drv_area(self, do_number: int, parameter_number: int, start: int, amount: int, word_len: int, buffer: bytearray, bytes_read_ref: list = None) -> int:
        """Read Drive area from Sinumerik.
        
        Args:
            do_number: Drive object number
            parameter_number: Parameter number
            start: Start address
            amount: Amount to read
            word_len: Word length
            buffer: Buffer to store data
            bytes_read_ref: Reference to bytes read (optional)
            
        Returns:
            Error code (0 = success)
        """
        return S7.errCliFunctionNotImplemented

    def write_drv_area(self, do_number: int, parameter_number: int, start: int, amount: int, word_len: int, buffer: bytearray, bytes_written_ref: list = None) -> int:
        """Write Drive area to Sinumerik.
        
        Args:
            do_number: Drive object number
            parameter_number: Parameter number
            start: Start address
            amount: Amount to write
            word_len: Word length
            buffer: Buffer containing data
            bytes_written_ref: Reference to bytes written (optional)
            
        Returns:
            Error code (0 = success)
        """
        return S7.errCliFunctionNotImplemented

    def read_nck_area(self, nck_area: int, nck_unit: int, nck_module: int, parameter_number: int, start: int, amount: int, word_len: int, buffer: bytearray, bytes_read_ref: list = None) -> int:
        """Read NCK area from Sinumerik.
        
        Args:
            nck_area: NCK area
            nck_unit: NCK unit
            nck_module: NCK module
            parameter_number: Parameter number
            start: Start address
            amount: Amount to read
            word_len: Word length
            buffer: Buffer to store data
            bytes_read_ref: Reference to bytes read (optional)
            
        Returns:
            Error code (0 = success)
        """
        return S7.errCliFunctionNotImplemented

    def write_nck_area(self, nck_area: int, nck_unit: int, nck_module: int, parameter_number: int, start: int, amount: int, word_len: int, buffer: bytearray, bytes_written_ref: list = None) -> int:
        """Write NCK area to Sinumerik.
        
        Args:
            nck_area: NCK area
            nck_unit: NCK unit
            nck_module: NCK module
            parameter_number: Parameter number
            start: Start address
            amount: Amount to write
            word_len: Word length
            buffer: Buffer containing data
            bytes_written_ref: Reference to bytes written (optional)
            
        Returns:
            Error code (0 = success)
        """
        return S7.errCliFunctionNotImplemented

    def read_multi_drv_vars(self, items: list, items_count: int) -> int:
        """Read multiple Drive variables from Sinumerik.
        
        Args:
            items: List of drive items to read
            items_count: Number of items
            
        Returns:
            Error code (0 = success)
        """
        return S7.errCliFunctionNotImplemented

    def write_multi_drv_vars(self, items: list, items_count: int) -> int:
        """Write multiple Drive variables to Sinumerik.
        
        Args:
            items: List of drive items to write
            items_count: Number of items
            
        Returns:
            Error code (0 = success)
        """
        return S7.errCliFunctionNotImplemented

    # ========================================================================
    # Block Constants (Sharp7 Compatible)
    # ========================================================================

    # Block types
    Block_OB = 0x38
    Block_DB = 0x41  
    Block_SDB = 0x42
    Block_FC = 0x43
    Block_SFC = 0x44
    Block_FB = 0x45
    Block_SFB = 0x46

    # Sub Block Type
    SubBlk_OB = 0x08
    SubBlk_DB = 0x0A
    SubBlk_SDB = 0x0B
    SubBlk_FC = 0x0C
    SubBlk_SFC = 0x0D
    SubBlk_FB = 0x0E
    SubBlk_SFB = 0x0F

    # Block languages
    BlockLangAWL = 0x01
    BlockLangKOP = 0x02
    BlockLangFUP = 0x03
    BlockLangSCL = 0x04
    BlockLangDB = 0x05
    BlockLangGRAPH = 0x06

    # Max vars for multi operations
    MaxVars = 20

    # Connection types
    CONNTYPE_PG = 0x01
    CONNTYPE_OP = 0x02
    CONNTYPE_BASIC = 0x03


def read_multi_vars(self, items, items_count):
    offset = 0
    length = 0
    item_size = 0
    s7_item = bytearray(12)
    s7_item_read = bytearray(1024)
    self._last_error = 0
    self.Time_ms = 0
    elapsed = time.time()

    if items_count > self.MaxVars:
        return S7.errCliTooManyItems

    self.PDU[: len(self.S7_MRD_HEADER)] = self.S7_MRD_HEADER
    S7.set_word_at(self.PDU, 13, items_count * len(s7_item) + 2)
    self.PDU[18] = items_count
    offset = 19

    for item in items:
        s7_item[:] = self.S7_MRD_ITEM
        s7_item[3] = item.WordLen
        S7.set_word_at(s7_item, 4, item.Amount)
        if item.Area == S7.S7AreaDB:
            S7.set_word_at(s7_item, 6, item.DBNumber)
        s7_item[8] = item.Area
        address = item.Start
        s7_item[11] = address & 0xFF
        address >>= 8
        s7_item[10] = address & 0xFF
        address >>= 8
        s7_item[9] = address & 0xFF
        self.PDU[offset : offset + len(s7_item)] = s7_item
        offset += len(s7_item)

    if offset > self._PduLength:
        return S7.errCliSizeOverPDU

    S7.set_word_at(self.PDU, 2, offset)
    self.send_packet(self.PDU, offset)

    if self._last_error != 0:
        return self._last_error

    length = self.recv_iso_packet()

    if self._last_error != 0:
        return self._last_error

    if length < 22:
        self._last_error = S7.errIsoInvalidPDU
        return self._last_error

    self._last_error = self.cpu_error(S7.get_word_at(self.PDU, 17))

    if self._last_error != 0:
        return self._last_error

    items_read = S7.get_byte_at(self.PDU, 20)

    if items_read != items_count or items_read > self.MaxVars:
        self._last_error = S7.errCliInvalidPlcAnswer
        return self._last_error

    offset = 21

    for item in items:
        s7_item_read[: length - offset] = self.PDU[offset:length]
        if s7_item_read[0] == 0xFF:
            item_size = S7.get_word_at(s7_item_read, 2)
            if s7_item_read[1] not in (self.TS_ResOctet, self.TS_ResReal, self.TS_ResBit):
                item_size >>= 3
            item.pData[:item_size] = s7_item_read[4 : 4 + item_size]
            item.Result = 0
            if item_size % 2 != 0:
               item_size += 1
            offset += 4 + item_size
        else:
            item.Result = self.cpu_error(s7_item_read[0])
            offset += 4

    self.Time_ms = int((time.time() - elapsed) * 1000)
    return self._last_error


def write_multi_vars(self, items, items_count):
    offset = 0
    par_length = 0
    data_length = 0
    item_data_size = 0
    s7_par_item = bytearray(len(self.S7_MWR_PARAM))
    s7_data_item = bytearray(1024)
    self._last_error = 0
    self.Time_ms = 0
    elapsed = time.time()

    if items_count > self.MaxVars:
        return S7.errCliTooManyItems

    self.PDU[: len(self.S7_MWR_HEADER)] = self.S7_MWR_HEADER
    par_length = items_count * len(self.S7_MWR_PARAM) + 2
    S7.set_word_at(self.PDU, 13, par_length)
    self.PDU[18] = items_count
    offset = len(self.S7_MWR_HEADER)

    for item in items:
        s7_par_item[:] = self.S7_MWR_PARAM
        s7_par_item[3] = item.WordLen
        s7_par_item[8] = item.Area
        S7.set_word_at(s7_par_item, 4, item.Amount)
        S7.set_word_at(s7_par_item, 6, item.DBNumber)
        address = item.Start
        s7_par_item[11] = address & 0xFF
        address >>= 8
        s7_par_item[10] = address & 0xFF
        address >>= 8
        s7_par_item[9] = address & 0xFF
        self.PDU[offset : offset + len(s7_par_item)] = s7_par_item
        offset += len(s7_par_item)

    data_length = 0

    for item in items:
        s7_data_item[0] = 0x00
        if item.WordLen == S7.S7WLBit:
            s7_data_item[1] = self.TS_ResBit
        elif item.WordLen in (S7.S7WLCounter, S7.S7WLTimer):
            s7_data_item[1] = self.TS_ResOctet
        else:
            s7_data_item[1] = self.TS_ResByte

        if item.WordLen in (S7.S7WLCounter, S7.S7WLTimer):
            item_data_size = item.Amount * 2
        else:
            item_data_size = item.Amount

        if s7_data_item[1] not in (self.TS_ResOctet, self.TS_ResBit):
            S7.set_word_at(s7_data_item, 2, item_data_size * 8)
        else:
            S7.set_word_at(s7_data_item, 2, item_data_size)

        s7_data_item[4 : 4 + item_data_size] = item.pData[:item_data_size]

        if item_data_size % 2 != 0:
            s7_data_item[item_data_size + 4] = 0x00
            item_data_size += 1

        self.PDU[offset : offset + item_data_size + 4] = s7_data_item[: item_data_size + 4]
        offset += item_data_size + 4
        data_length += item_data_size + 4

    if offset > self._PduLength:
        return S7.errCliSizeOverPDU

    S7.set_word_at(self.PDU, 2, offset)
    S7.set_word_at(self.PDU, 15, data_length)
    self.send_packet(self.PDU, offset)
    self.recv_iso_packet()

    if self._last_error == 0:
        self._last_error = self.cpu_error(S7.get_word_at(self.PDU, 17))
        if self._last_error != 0:
            return self._last_error

        items_written = S7.get_byte_at(self.PDU, 20)

        if items_written != items_count or items_written > self.MaxVars:
            self._last_error = S7.errCliInvalidPlcAnswer
            return self._last_error

        for i, item in enumerate(items):
            if self.PDU[i + 21] == 0xFF:
                item.Result = 0
            else:
                item.Result = self.cpu_error(self.PDU[i + 21])

        self.Time_ms = int((time.time() - elapsed) * 1000)

    return self._last_error
