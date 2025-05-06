from .s7_socket import S7Socket
from .s7_protocol import S7Protocol as S7
import time
import struct

from ..type import S7CpInfo, S7CpuInfo


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
        return self.Socket is not None and self.Socket.connected

    def __init__(self):
        self._LastError = 0
        self._PduLength = 0
        self._PduSizeRequested = 480
        self._PLCPort = 102
        self._rack = 0
        self._slot = 0
        self._RecvTimeout = 2000
        self._SendTimeout = 2000
        self._ConnTimeout = 2000
        self.IPAddress = ""
        self.LocalTSAP_HI : int = 0
        self.LocalTSAP_LO : int = 0
        self.RemoteTSAP_HI : int = 0
        self.RemoteTSAP_LO = 0
        self.LastPDUType = 0
        self.ConnType = S7.CONNTYPE_PG
        self.PDU = bytearray(2048)
        self.Socket = None
        self.time_ms = 0
        self.cntword = 0

        self.Socket = S7Socket()
        self.Socket.connect_timeout = self._ConnTimeout
        self.Socket.read_timeout = self._RecvTimeout
        self.Socket.write_timeout = self._SendTimeout

    def set_connection_params(self,address, local_tsap, remote_tsap):
        self.IPAddress = address

        loc_tsap = local_tsap & 0x0000FFFF
        rem_tsap = remote_tsap & 0x0000FFFF

        self.LocalTSAP_HI = (loc_tsap >> 8)
        self.LocalTSAP_LO = loc_tsap & 0xFF
        self.RemoteTSAP_HI = (rem_tsap >> 8)
        self.RemoteTSAP_LO = rem_tsap & 0xFF

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
        self._LastError = 0
        self.time_ms = 0
        elapsed = int(time.time() * 1000)  # Elapsed time in milliseconds

        if not self.connected:
            self.tcp_connect()  # First stage: TCP Connection
            if self._LastError == 0:
                self.iso_connect()  # Second stage: ISOTCP (ISO 8073) Connection
                if self._LastError == 0:
                    self._LastError = self.negotiate_pdu_length()  # Third stage: S7 PDU negotiation

        if self._LastError != 0:
            self.disconnect()
        else:
            self.time_ms = int(time.time() * 1000) - elapsed

        return self._LastError


    def read_SZL(self, szl_id : int, szl_index : int, szl_buffer : S7SZL) -> int:
        offset = 0
        done = False
        first = True
        seq_in = 0x00
        seq_out = 0x0000

        self._LastError = 0
        self.time_ms = 0
        elapsed = int(time.time() * 1000)
        szl_buffer.Header.LENTHDR = 0

        ## Send two requests to the PLC
        ## Continue reading until the last packet is received
        while not done and self._LastError == 0:
            if first:
                S7.set_word_at(S7.S7_SZL_FIRST, 11, seq_out + 1)
                S7.set_word_at(S7.S7_SZL_FIRST, 29, szl_id)
                S7.set_word_at(S7.S7_SZL_FIRST, 31, szl_index)
                self.send_packet(S7.S7_SZL_FIRST)
            else:
                S7.set_word_at(S7.S7_SZL_NEXT, 11, seq_out + 1)
                self.PDU[24] = seq_in
                self.send_packet(S7.S7_SZL_NEXT)

            if self._LastError != 0:
                return self._LastError

            length = self.recv_iso_packet()
            if self._LastError == 0:
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
                            self._LastError = S7.errCliInvalidPlcAnswer
                    else:
                        self._LastError = S7.errIsoInvalidPDU
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
                            self._LastError = S7.errCliInvalidPlcAnswer
                    else:
                        self._LastError = S7.errIsoInvalidPDU
            first = False

        if self._LastError == 0:
            self.time_ms = int(time.time() * 1000) - elapsed

        return self._LastError

    def get_cpu_info(self, info: S7CpuInfo) -> int:
        szl = S7SZL(1024)

        elapsed = int(time.time() * 1000)

        self._LastError = self.read_SZL(0x001C, 0x000, szl)

        if self._LastError == 0:
            info.ModuleTypeName = S7.GetCharsAt(szl.Data, 172, 32)
            info.SerialNumber = S7.GetCharsAt(szl.Data, 138, 24)
            info.ASName = S7.GetCharsAt(szl.Data, 2, 24)
            info.Copyright = S7.GetCharsAt(szl.Data, 104, 26)
            info.ModuleName = S7.GetCharsAt(szl.Data, 36, 24)

        if self._LastError == 0:
            self.time_ms = int(time.time() * 1000) - elapsed

        return self._LastError

    def get_cp_info(self, cp : S7CpInfo):
        szl = S7SZL(1024)

        elapsed = int(time.time() * 1000)

        self._LastError = self.read_SZL(0x0131, 0x001, szl)
        if  self._LastError == 0:
            cp.MaxPduLength = S7.get_int_at(szl.Data, 2)
            # cp.MaxConnections = S7.get_int_at(szl.Data, 4)
            # cp.MaxMpiRate = S7.get_int_at(szl.Data, 6)
            # TODO : ??? Max Connections inverted with Max MPI Rate ???
            cp.MaxConnections = S7.get_int_at(szl.Data, 6)
            cp.MaxMpiRate = S7.get_int_at(szl.Data, 4)
            cp.MaxBusRate = S7.get_int_at(szl.Data, 10)

        if  self._LastError == 0:
            self.time_ms = int(time.time() * 1000) - elapsed

        return  self._LastError


    def recv_packet(self, buffer, start, size):
        if self.connected:
            self._LastError = self.Socket.receive(buffer, start, size)
        else:
            self._LastError = S7.errTCPNotConnected

    def send_packet(self, buffer, length=None):
        if length is None:
            length = len(buffer)
        self._LastError = self.Socket.send(buffer, length)

    def recv_iso_packet(self):
        done = False
        size = 0
        while self._LastError == 0 and not done:
            self.recv_packet(self.PDU, 0, 4)
            if self._LastError == 0:
                size = struct.unpack(">H", self.PDU[2:4])[0]
                if size == 7:
                    self.recv_packet(self.PDU, 4, 3)
                else:
                    if size > self._PduSizeRequested + 7 or size < 16:
                        self._LastError = S7.errIsoInvalidPDU
                    else:
                        done = True

        if self._LastError == 0:
            self.recv_packet(self.PDU, 4, 3)
            self.LastPDUType = self.PDU[5]
            self.recv_packet(self.PDU, 7, size - 7)
        return size if self._LastError == 0 else 0

    def iso_connect(self):
        iso_cr = S7.ISO_CR # Copy bytearray ?
        iso_cr[16] = self.LocalTSAP_HI
        iso_cr[17] = self.LocalTSAP_LO
        iso_cr[20] = self.RemoteTSAP_HI
        iso_cr[21] = self.RemoteTSAP_LO
        self.send_packet(iso_cr)
        if self._LastError == 0:
            size = self.recv_iso_packet()
            if self._LastError == 0:
                if size == 22:
                    if self.LastPDUType != 0xD0:
                        self._LastError = S7.errIsoConnect
                else:
                    self._LastError = S7.errIsoInvalidPDU
        return self._LastError

    def negotiate_pdu_length(self):
        pn_message = S7.S7_PN
        S7.set_word_at(pn_message, 23,  self._PduSizeRequested)
        self.send_packet(pn_message)
        if self._LastError == 0:
            length = self.recv_iso_packet()
            if self._LastError == 0:
                if length == 27 and self.PDU[17] == 0 and self.PDU[18] == 0:
                    self._PduLength = S7.get_word_at(self.PDU, 25)
                    if self._PduLength <= 0:
                        self._LastError = S7.errCliNegotiatingPDU
                else:
                    self._LastError = S7.errCliNegotiatingPDU
        return self._LastError

    def __del__(self):
        self.disconnect()

    def set_connection_type(self, connection_type):
        self.ConnType = connection_type
        return 0

    def disconnect(self) -> bool:
        self.Socket.close()
        return True

    def get_param(self, param_number):
        return {
            S7.p_u16_RemotePort: self._PLCPort,
            S7.p_i32_PingTimeout: self._ConnTimeout,
            S7.p_i32_SendTimeout: self._SendTimeout,
            S7.p_i32_RecvTimeout: self._RecvTimeout,
            S7.p_i32_PDURequest: self._PduSizeRequested,
        }.get(param_number, S7.errCliInvalidParamNumber)

    def set_param(self, param_number, value):
        if param_number == S7.p_u16_RemotePort:
            self._PLCPort = value
        elif param_number == S7.p_i32_PingTimeout:
            self._ConnTimeout = value
        elif param_number == S7.p_i32_SendTimeout:
            self._SendTimeout = value
        elif param_number == S7.p_i32_RecvTimeout:
            self._RecvTimeout = value
        elif param_number == S7.p_i32_PDURequest:
            self._PduSizeRequested = value
        else:
            return S7.errCliInvalidParamNumber
        return 0

    def tcp_connect(self):
        if self._LastError == 0:
            try:
                # Assuming `self.Socket` is a socket object
                self.Socket.connect(self.IPAddress, self._PLCPort)
            except Exception:
                self._LastError = S7.errTCPConnectionFailed
        return self._LastError


#     def read_area(self, area, db_number, start, amount, word_len, buffer, bytes_read=0):
#         address = 0
#         num_elements = 0
#         max_elements = 0
#         tot_elements = 0
#         size_requested = 0
#         length = 0
#         offset = 0
#         word_size = 1
#         self._LastError = 0
#         self.Time_ms = 0
#         elapsed = time.time()
#
#         if area == S7.S7AreaCT:
#             word_len = S7.S7WLCounter
#         if area == S7.S7AreaTM:
#             word_len = S7.S7WLTimer
#
#         word_size = S7.data_size_byte(word_len)
#         if word_size == 0:
#             return S7.errCliInvalidWordLen
#
#         if word_len == S7.S7WLBit:
#             amount = 1
#         else:
#             if word_len not in (S7.S7WLCounter, S7.S7WLTimer):
#                 amount *= word_size
#                 word_size = 1
#                 word_len = S7.S7WLByte
#
#         max_elements = (self._PduLength - 18) // word_size
#         tot_elements = amount
#
#         while tot_elements > 0 and self._LastError == 0:
#             num_elements = min(tot_elements, max_elements)
#             size_requested = num_elements * word_size
#             self.PDU[: self.Size_RD] = self.S7_RW[: self.Size_RD]
#             self.PDU[27] = area
#
#             if area == S7.S7AreaDB:
#                 S7.set_word_at(self.PDU, 25, db_number)
#
#             if word_len in (S7.S7WLBit, S7.S7WLCounter, S7.S7WLTimer):
#                 address = start
#                 self.PDU[22] = word_len
#             else:
#                 address = start << 3
#
#             S7.set_word_at(self.PDU, 23, num_elements)
#             self.PDU[30] = address & 0xFF
#             address >>= 8
#             self.PDU[29] = address & 0xFF
#             address >>= 8
#             self.PDU[28] = address & 0xFF
#
#             self.send_packet(self.PDU, self.Size_RD)
#
#             if self._LastError == 0:
#                 length = self.recv_iso_packet()
#                 if self._LastError == 0:
#                     if length < 25:
#                         self._LastError = S7.errIsoInvalidDataSize
#                     else:
#                         if self.PDU[21] != 0xFF:
#                             self._LastError = self.cpu_error(self.PDU[21])
#                         else:
#                             buffer[offset : offset + size_requested] = self.PDU[25 : 25 + size_requested]
#                             offset += size_requested
#
#             tot_elements -= num_elements
#             start += num_elements * word_size
#
#         if self._LastError == 0:
#             bytes_read = offset
#             self.Time_ms = int((time.time() - elapsed) * 1000)
#         else:
#             bytes_read = 0
#
#         return self._LastError
#
#     def write_area(self, area, db_number, start, amount, word_len, buffer, bytes_written=0):
#         address = 0
#         num_elements = 0
#         max_elements = 0
#         tot_elements = 0
#         data_size = 0
#         iso_size = 0
#         length = 0
#         offset = 0
#         word_size = 1
#         self._LastError = 0
#         self.Time_ms = 0
#         elapsed = time.time()
#
#         if area == S7.S7AreaCT:
#             word_len = S7.S7WLCounter
#         if area == S7.S7AreaTM:
#             word_len = S7.S7WLTimer
#
#         word_size = S7.data_size_byte(word_len)
#         if word_size == 0:
#             return S7.errCliInvalidWordLen
#
#         if word_len == S7.S7WLBit:
#             amount = 1
#         else:
#             if word_len not in (S7.S7WLCounter, S7.S7WLTimer):
#                 amount *= word_size
#                 word_size = 1
#                 word_len = S7.S7WLByte
#
#         max_elements = (self._PduLength - 35) // word_size
#         tot_elements = amount
#
#         while tot_elements > 0 and self._LastError == 0:
#             num_elements = min(tot_elements, max_elements)
#             data_size = num_elements * word_size
#             iso_size = self.Size_WR + data_size
#             self.PDU[: self.Size_WR] = self.S7_RW[: self.Size_WR]
#             S7.set_word_at(self.PDU, 2, iso_size)
#             length = data_size + 4
#             S7.set_word_at(self.PDU, 15, length)
#             self.PDU[17] = 0x05
#             self.PDU[27] = area
#
#             if area == S7.S7AreaDB:
#                 S7.set_word_at(self.PDU, 25, db_number)
#
#             if word_len in (S7.S7WLBit, S7.S7WLCounter, S7.S7WLTimer):
#                 address = start
#                 length = data_size
#                 self.PDU[22] = word_len
#             else:
#                 address = start << 3
#                 length = data_size << 3
#
#             S7.set_word_at(self.PDU, 23, num_elements)
#             self.PDU[30] = address & 0xFF
#             address >>= 8
#             self.PDU[29] = address & 0xFF
#             address >>= 8
#             self.PDU[28] = address & 0xFF
#
#             if word_len == S7.S7WLBit:
#                 self.PDU[32] = self.TS_ResBit
#             elif word_len in (S7.S7WLCounter, S7.S7WLTimer):
#                 self.PDU[32] = self.TS_ResOctet
#             else:
#                 self.PDU[32] = self.TS_ResByte
#
#             S7.set_word_at(self.PDU, 33, length)
#             self.PDU[35 : 35 + data_size] = buffer[offset : offset + data_size]
#             self.send_packet(self.PDU, iso_size)
#
#             if self._LastError == 0:
#                 length = self.recv_iso_packet()
#                 if self._LastError == 0:
#                     if length == 22:
#                         if self.PDU[21] != 0xFF:
#                             self._LastError = self.cpu_error(self.PDU[21])
#                     else:
#                         self._LastError = S7.errIsoInvalidPDU
#
#             offset += data_size
#             tot_elements -= num_elements
#             start += num_elements * word_size
#
#         if self._LastError == 0:
#             bytes_written = offset
#             self.Time_ms = int((time.time() - elapsed) * 1000)
#         else:
#             bytes_written = 0
#
#         return self._LastError
#
#
# def read_multi_vars(self, items, items_count):
#     offset = 0
#     length = 0
#     item_size = 0
#     s7_item = bytearray(12)
#     s7_item_read = bytearray(1024)
#     self._LastError = 0
#     self.Time_ms = 0
#     elapsed = time.time()
#
#     if items_count > self.MaxVars:
#         return S7.errCliTooManyItems
#
#     self.PDU[: len(self.S7_MRD_HEADER)] = self.S7_MRD_HEADER
#     S7.set_word_at(self.PDU, 13, items_count * len(s7_item) + 2)
#     self.PDU[18] = items_count
#     offset = 19
#
#     for item in items:
#         s7_item[:] = self.S7_MRD_ITEM
#         s7_item[3] = item.WordLen
#         S7.set_word_at(s7_item, 4, item.Amount)
#         if item.Area == S7.S7AreaDB:
#             S7.set_word_at(s7_item, 6, item.DBNumber)
#         s7_item[8] = item.Area
#         address = item.Start
#         s7_item[11] = address & 0xFF
#         address >>= 8
#         s7_item[10] = address & 0xFF
#         address >>= 8
#         s7_item[9] = address & 0xFF
#         self.PDU[offset : offset + len(s7_item)] = s7_item
#         offset += len(s7_item)
#
#     if offset > self._PduLength:
#         return S7.errCliSizeOverPDU
#
#     S7.set_word_at(self.PDU, 2, offset)
#     self.send_packet(self.PDU, offset)
#
#     if self._LastError != 0:
#         return self._LastError
#
#     length = self.recv_iso_packet()
#
#     if self._LastError != 0:
#         return self._LastError
#
#     if length < 22:
#         self._LastError = S7.errIsoInvalidPDU
#         return self._LastError
#
#     self._LastError = self.cpu_error(S7.get_word_at(self.PDU, 17))
#
#     if self._LastError != 0:
#         return self._LastError
#
#     items_read = S7.get_byte_at(self.PDU, 20)
#
#     if items_read != items_count or items_read > self.MaxVars:
#         self._LastError = S7.errCliInvalidPlcAnswer
#         return self._LastError
#
#     offset = 21
#
#     for item in items:
#         s7_item_read[: length - offset] = self.PDU[offset:length]
#         if s7_item_read[0] == 0xFF:
#             item_size = S7.get_word_at(s7_item_read, 2)
#             if s7_item_read[1] not in (self.TS_ResOctet, self.TS_ResReal, self.TS_ResBit):
#                 item_size >>= 3
#             item.pData[:item_size] = s7_item_read[4 : 4 + item_size]
#             item.Result = 0
#             if item_size % 2 != 0:
#                 item_size += 1
#             offset += 4 + item_size
#         else:
#             item.Result = self.cpu_error(s7_item_read[0])
#             offset += 4
#
#     self.Time_ms = int((time.time() - elapsed) * 1000)
#     return self._LastError
#
#
# def write_multi_vars(self, items, items_count):
#     offset = 0
#     par_length = 0
#     data_length = 0
#     item_data_size = 0
#     s7_par_item = bytearray(len(self.S7_MWR_PARAM))
#     s7_data_item = bytearray(1024)
#     self._LastError = 0
#     self.Time_ms = 0
#     elapsed = time.time()
#
#     if items_count > self.MaxVars:
#         return S7.errCliTooManyItems
#
#     self.PDU[: len(self.S7_MWR_HEADER)] = self.S7_MWR_HEADER
#     par_length = items_count * len(self.S7_MWR_PARAM) + 2
#     S7.set_word_at(self.PDU, 13, par_length)
#     self.PDU[18] = items_count
#     offset = len(self.S7_MWR_HEADER)
#
#     for item in items:
#         s7_par_item[:] = self.S7_MWR_PARAM
#         s7_par_item[3] = item.WordLen
#         s7_par_item[8] = item.Area
#         S7.set_word_at(s7_par_item, 4, item.Amount)
#         S7.set_word_at(s7_par_item, 6, item.DBNumber)
#         address = item.Start
#         s7_par_item[11] = address & 0xFF
#         address >>= 8
#         s7_par_item[10] = address & 0xFF
#         address >>= 8
#         s7_par_item[9] = address & 0xFF
#         self.PDU[offset : offset + len(s7_par_item)] = s7_par_item
#         offset += len(s7_par_item)
#
#     data_length = 0
#
#     for item in items:
#         s7_data_item[0] = 0x00
#         if item.WordLen == S7.S7WLBit:
#             s7_data_item[1] = self.TS_ResBit
#         elif item.WordLen in (S7.S7WLCounter, S7.S7WLTimer):
#             s7_data_item[1] = self.TS_ResOctet
#         else:
#             s7_data_item[1] = self.TS_ResByte
#
#         if item.WordLen in (S7.S7WLCounter, S7.S7WLTimer):
#             item_data_size = item.Amount * 2
#         else:
#             item_data_size = item.Amount
#
#         if s7_data_item[1] not in (self.TS_ResOctet, self.TS_ResBit):
#             S7.set_word_at(s7_data_item, 2, item_data_size * 8)
#         else:
#             S7.set_word_at(s7_data_item, 2, item_data_size)
#
#         s7_data_item[4 : 4 + item_data_size] = item.pData[:item_data_size]
#
#         if item_data_size % 2 != 0:
#             s7_data_item[item_data_size + 4] = 0x00
#             item_data_size += 1
#
#         self.PDU[offset : offset + item_data_size + 4] = s7_data_item[: item_data_size + 4]
#         offset += item_data_size + 4
#         data_length += item_data_size + 4
#
#     if offset > self._PduLength:
#         return S7.errCliSizeOverPDU
#
#     S7.set_word_at(self.PDU, 2, offset)
#     S7.set_word_at(self.PDU, 15, data_length)
#     self.send_packet(self.PDU, offset)
#     self.recv_iso_packet()
#
#     if self._LastError == 0:
#         self._LastError = self.cpu_error(S7.get_word_at(self.PDU, 17))
#         if self._LastError != 0:
#             return self._LastError
#
#         items_written = S7.get_byte_at(self.PDU, 20)
#
#         if items_written != items_count or items_written > self.MaxVars:
#             self._LastError = S7.errCliInvalidPlcAnswer
#             return self._LastError
#
#         for i, item in enumerate(items):
#             if self.PDU[i + 21] == 0xFF:
#                 item.Result = 0
#             else:
#                 item.Result = self.cpu_error(self.PDU[i + 21])
#
#         self.Time_ms = int((time.time() - elapsed) * 1000)
#
#     return self._LastError
