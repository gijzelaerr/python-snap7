from .msg_socket import MsgSocket
from .s7_consts import S7Consts
from .s7 import S7
import time
import struct


class S7Client:
    Block_OB = 0x38
    Block_DB = 0x41
    Block_SDB = 0x42
    Block_FC = 0x43
    Block_SFC = 0x44
    Block_FB = 0x45
    Block_SFB = 0x46
    SubBlk_OB = 0x08
    SubBlk_DB = 0x0A
    SubBlk_SDB = 0x0B
    SubBlk_FC = 0x0C
    SubBlk_SFC = 0x0D
    SubBlk_FB = 0x0E
    SubBlk_SFB = 0x0F
    BlockLangAWL = 0x01
    BlockLangKOP = 0x02
    BlockLangFUP = 0x03
    BlockLangSCL = 0x04
    BlockLangDB = 0x05
    BlockLangGRAPH = 0x06
    MaxVars = 20
    TS_ResBit = 0x03
    TS_ResByte = 0x04
    TS_ResInt = 0x05
    TS_ResReal = 0x07
    TS_ResOctet = 0x09
    Code7Ok = 0x0000
    Code7AddressOutOfRange = 0x0005
    Code7InvalidTransportSize = 0x0006
    Code7WriteDataSizeMismatch = 0x0007
    Code7ResItemNotAvailable = 0x000A
    Code7ResItemNotAvailable1 = 0xD209
    Code7InvalidValue = 0xDC01
    Code7NeedPassword = 0xD241
    Code7InvalidPassword = 0xD602
    Code7NoPasswordToClear = 0xD604
    Code7NoPasswordToSet = 0xD605
    Code7FunNotAvailable = 0x8104
    Code7DataOverPDU = 0x8500
    CONNTYPE_PG = 0x01
    CONNTYPE_OP = 0x02
    CONNTYPE_BASIC = 0x03

    def __init__(self):
        self._LastError = 0
        self._PDULength = 0
        self._PduSizeRequested = 480
        self._PLCPort = 102
        self._RecvTimeout = 2000
        self._SendTimeout = 2000
        self._ConnTimeout = 2000
        self.IPAddress = ""
        self.LocalTSAP_HI = 0
        self.LocalTSAP_LO = 0
        self.RemoteTSAP_HI = 0
        self.RemoteTSAP_LO = 0
        self.LastPDUType = 0
        self.ConnType = self.CONNTYPE_PG
        self.PDU = bytearray(2048)
        self.Socket = None
        self.Time_ms = 0
        self.cntword = 0
        self.connected = False

        self.ISO_CR = bytearray(
            [
                0x03,
                0x00,
                0x00,
                0x16,
                0x11,
                0xE0,
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0xC0,
                0x01,
                0x0A,
                0xC1,
                0x02,
                0x01,
                0x00,
                0xC2,
                0x02,
                0x01,
                0x02,
            ]
        )

        self.create_socket()

    def create_socket(self):
        self.Socket = MsgSocket()
        self.Socket.connect_timeout = self._ConnTimeout
        self.Socket.read_timeout = self._RecvTimeout
        self.Socket.write_timeout = self._SendTimeout

    def tcp_connect(self):
        if self._LastError == 0:
            try:
                self._LastError = self.Socket.connect(self.IPAddress, self._PLCPort)
            except:
                self._LastError = "errTCPConnectionFailed"
        return self._LastError

    def recv_packet(self, buffer, start, size):
        if self.connected:
            self._LastError = self.Socket.receive(buffer, start, size)
        else:
            self._LastError = "errTCPNotConnected"

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
                        self._LastError = "errIsoInvalidPDU"
                    else:
                        done = True
        if self._LastError == 0:
            self.recv_packet(self.PDU, 4, 3)
            self.LastPDUType = self.PDU[5]
            self.recv_packet(self.PDU, 7, size - 7)
        return size if self._LastError == 0 else 0

    def iso_connect(self):
        self.ISO_CR[16] = self.LocalTSAP_HI
        self.ISO_CR[17] = self.LocalTSAP_LO
        self.ISO_CR[20] = self.RemoteTSAP_HI
        self.ISO_CR[21] = self.RemoteTSAP_LO
        self.send_packet(self.ISO_CR)
        if self._LastError == 0:
            size = self.recv_iso_packet()
            if self._LastError == 0:
                if size == 22:
                    if self.LastPDUType != 0xD0:
                        self._LastError = "errIsoConnect"
                else:
                    self._LastError = "errIsoInvalidPDU"
        return self._LastError

    def negotiate_pdu_length(self):
        S7.set_word_at(self.S7_PN, 23, self._PduSizeRequested)
        self.send_packet(self.S7_PN)
        if self._LastError == 0:
            length = self.recv_iso_packet()
            if self._LastError == 0:
                if length == 27 and self.PDU[17] == 0 and self.PDU[18] == 0:
                    self._PDULength = S7.get_word_at(self.PDU, 25)
                    if self._PDULength <= 0:
                        self._LastError = S7Consts.errCliNegotiatingPDU
                else:
                    self._LastError = S7Consts.errCliNegotiatingPDU
        return self._LastError

    def cpu_error(self, error):
        return {
            0: 0,
            self.Code7AddressOutOfRange: S7Consts.errCliAddressOutOfRange,
            self.Code7InvalidTransportSize: S7Consts.errCliInvalidTransportSize,
            self.Code7WriteDataSizeMismatch: S7Consts.errCliWriteDataSizeMismatch,
            self.Code7ResItemNotAvailable: S7Consts.errCliItemNotAvailable,
            self.Code7ResItemNotAvailable1: S7Consts.errCliItemNotAvailable,
            self.Code7DataOverPDU: S7Consts.errCliSizeOverPDU,
            self.Code7InvalidValue: S7Consts.errCliInvalidValue,
            self.Code7FunNotAvailable: S7Consts.errCliFunNotAvailable,
            self.Code7NeedPassword: S7Consts.errCliNeedPassword,
            self.Code7InvalidPassword: S7Consts.errCliInvalidPassword,
            self.Code7NoPasswordToSet: S7Consts.errCliNoPasswordToSetOrClear,
            self.Code7NoPasswordToClear: S7Consts.errCliNoPasswordToSetOrClear,
        }.get(error, S7Consts.errCliFunctionRefused)

    def get_next_word(self):
        self.cntword += 1
        return self.cntword - 1

    def __del__(self):
        self.disconnect()

    def connect(self):
        self._LastError = 0
        self.Time_ms = 0
        elapsed = time.time()
        if not self.connected:
            self.tcp_connect()
            if self._LastError == 0:
                self.iso_connect()
                if self._LastError == 0:
                    self._LastError = self.negotiate_pdu_length()
        if self._LastError != 0:
            self.disconnect()
        else:
            self.Time_ms = int((time.time() - elapsed) * 1000)
        return self._LastError

    def connect_to(self, address, rack, slot, port=102):
        remote_tsap = (self.ConnType << 8) + (rack * 0x20) + slot
        self.set_connection_params(address, 0x0100, remote_tsap)
        self.set_param(S7Consts.p_u16_RemotePort, port)
        return self.connect()

    def set_connection_params(self, address, local_tsap, remote_tsap):
        self.IPAddress = address
        self.LocalTSAP_HI = (local_tsap >> 8) & 0xFF
        self.LocalTSAP_LO = local_tsap & 0xFF
        self.RemoteTSAP_HI = (remote_tsap >> 8) & 0xFF
        self.RemoteTSAP_LO = remote_tsap & 0xFF
        return 0

    def set_connection_type(self, connection_type):
        self.ConnType = connection_type
        return 0

    def disconnect(self):
        self.Socket.close()
        return 0

    def get_param(self, param_number):
        return {
            S7Consts.p_u16_RemotePort: self._PLCPort,
            S7Consts.p_i32_PingTimeout: self._ConnTimeout,
            S7Consts.p_i32_SendTimeout: self._SendTimeout,
            S7Consts.p_i32_RecvTimeout: self._RecvTimeout,
            S7Consts.p_i32_PDURequest: self._PduSizeRequested,
        }.get(param_number, S7Consts.errCliInvalidParamNumber)

    def set_param(self, param_number, value):
        if param_number == S7Consts.p_u16_RemotePort:
            self._PLCPort = value
        elif param_number == S7Consts.p_i32_PingTimeout:
            self._ConnTimeout = value
        elif param_number == S7Consts.p_i32_SendTimeout:
            self._SendTimeout = value
        elif param_number == S7Consts.p_i32_RecvTimeout:
            self._RecvTimeout = value
        elif param_number == S7Consts.p_i32_PDURequest:
            self._PduSizeRequested = value
        else:
            return S7Consts.errCliInvalidParamNumber
        return 0

    def set_as_callback(self, completion, usr_ptr):
        return S7Consts.errCliFunctionNotImplemented

    def read_area(self, area, db_number, start, amount, word_len, buffer, bytes_read=0):
        address = 0
        num_elements = 0
        max_elements = 0
        tot_elements = 0
        size_requested = 0
        length = 0
        offset = 0
        word_size = 1
        self._LastError = 0
        self.Time_ms = 0
        elapsed = time.time()

        if area == S7Consts.S7AreaCT:
            word_len = S7Consts.S7WLCounter
        if area == S7Consts.S7AreaTM:
            word_len = S7Consts.S7WLTimer

        word_size = S7.data_size_byte(word_len)
        if word_size == 0:
            return S7Consts.errCliInvalidWordLen

        if word_len == S7Consts.S7WLBit:
            amount = 1
        else:
            if word_len not in (S7Consts.S7WLCounter, S7Consts.S7WLTimer):
                amount *= word_size
                word_size = 1
                word_len = S7Consts.S7WLByte

        max_elements = (self._PDULength - 18) // word_size
        tot_elements = amount

        while tot_elements > 0 and self._LastError == 0:
            num_elements = min(tot_elements, max_elements)
            size_requested = num_elements * word_size
            self.PDU[: self.Size_RD] = self.S7_RW[: self.Size_RD]
            self.PDU[27] = area

            if area == S7Consts.S7AreaDB:
                S7.set_word_at(self.PDU, 25, db_number)

            if word_len in (S7Consts.S7WLBit, S7Consts.S7WLCounter, S7Consts.S7WLTimer):
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

            self.send_packet(self.PDU, self.Size_RD)

            if self._LastError == 0:
                length = self.recv_iso_packet()
                if self._LastError == 0:
                    if length < 25:
                        self._LastError = S7Consts.errIsoInvalidDataSize
                    else:
                        if self.PDU[21] != 0xFF:
                            self._LastError = self.cpu_error(self.PDU[21])
                        else:
                            buffer[offset : offset + size_requested] = self.PDU[25 : 25 + size_requested]
                            offset += size_requested

            tot_elements -= num_elements
            start += num_elements * word_size

        if self._LastError == 0:
            bytes_read = offset
            self.Time_ms = int((time.time() - elapsed) * 1000)
        else:
            bytes_read = 0

        return self._LastError

    def write_area(self, area, db_number, start, amount, word_len, buffer, bytes_written=0):
        address = 0
        num_elements = 0
        max_elements = 0
        tot_elements = 0
        data_size = 0
        iso_size = 0
        length = 0
        offset = 0
        word_size = 1
        self._LastError = 0
        self.Time_ms = 0
        elapsed = time.time()

        if area == S7Consts.S7AreaCT:
            word_len = S7Consts.S7WLCounter
        if area == S7Consts.S7AreaTM:
            word_len = S7Consts.S7WLTimer

        word_size = S7.data_size_byte(word_len)
        if word_size == 0:
            return S7Consts.errCliInvalidWordLen

        if word_len == S7Consts.S7WLBit:
            amount = 1
        else:
            if word_len not in (S7Consts.S7WLCounter, S7Consts.S7WLTimer):
                amount *= word_size
                word_size = 1
                word_len = S7Consts.S7WLByte

        max_elements = (self._PDULength - 35) // word_size
        tot_elements = amount

        while tot_elements > 0 and self._LastError == 0:
            num_elements = min(tot_elements, max_elements)
            data_size = num_elements * word_size
            iso_size = self.Size_WR + data_size
            self.PDU[: self.Size_WR] = self.S7_RW[: self.Size_WR]
            S7.set_word_at(self.PDU, 2, iso_size)
            length = data_size + 4
            S7.set_word_at(self.PDU, 15, length)
            self.PDU[17] = 0x05
            self.PDU[27] = area

            if area == S7Consts.S7AreaDB:
                S7.set_word_at(self.PDU, 25, db_number)

            if word_len in (S7Consts.S7WLBit, S7Consts.S7WLCounter, S7Consts.S7WLTimer):
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

            if word_len == S7Consts.S7WLBit:
                self.PDU[32] = self.TS_ResBit
            elif word_len in (S7Consts.S7WLCounter, S7Consts.S7WLTimer):
                self.PDU[32] = self.TS_ResOctet
            else:
                self.PDU[32] = self.TS_ResByte

            S7.set_word_at(self.PDU, 33, length)
            self.PDU[35 : 35 + data_size] = buffer[offset : offset + data_size]
            self.send_packet(self.PDU, iso_size)

            if self._LastError == 0:
                length = self.recv_iso_packet()
                if self._LastError == 0:
                    if length == 22:
                        if self.PDU[21] != 0xFF:
                            self._LastError = self.cpu_error(self.PDU[21])
                    else:
                        self._LastError = S7Consts.errIsoInvalidPDU

            offset += data_size
            tot_elements -= num_elements
            start += num_elements * word_size

        if self._LastError == 0:
            bytes_written = offset
            self.Time_ms = int((time.time() - elapsed) * 1000)
        else:
            bytes_written = 0

        return self._LastError


def read_multi_vars(self, items, items_count):
    offset = 0
    length = 0
    item_size = 0
    s7_item = bytearray(12)
    s7_item_read = bytearray(1024)
    self._LastError = 0
    self.Time_ms = 0
    elapsed = time.time()

    if items_count > self.MaxVars:
        return S7Consts.errCliTooManyItems

    self.PDU[: len(self.S7_MRD_HEADER)] = self.S7_MRD_HEADER
    S7.set_word_at(self.PDU, 13, items_count * len(s7_item) + 2)
    self.PDU[18] = items_count
    offset = 19

    for item in items:
        s7_item[:] = self.S7_MRD_ITEM
        s7_item[3] = item.WordLen
        S7.set_word_at(s7_item, 4, item.Amount)
        if item.Area == S7Consts.S7AreaDB:
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

    if offset > self._PDULength:
        return S7Consts.errCliSizeOverPDU

    S7.set_word_at(self.PDU, 2, offset)
    self.send_packet(self.PDU, offset)

    if self._LastError != 0:
        return self._LastError

    length = self.recv_iso_packet()

    if self._LastError != 0:
        return self._LastError

    if length < 22:
        self._LastError = S7Consts.errIsoInvalidPDU
        return self._LastError

    self._LastError = self.cpu_error(S7.get_word_at(self.PDU, 17))

    if self._LastError != 0:
        return self._LastError

    items_read = S7.get_byte_at(self.PDU, 20)

    if items_read != items_count or items_read > self.MaxVars:
        self._LastError = S7Consts.errCliInvalidPlcAnswer
        return self._LastError

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
    return self._LastError


def write_multi_vars(self, items, items_count):
    offset = 0
    par_length = 0
    data_length = 0
    item_data_size = 0
    s7_par_item = bytearray(len(self.S7_MWR_PARAM))
    s7_data_item = bytearray(1024)
    self._LastError = 0
    self.Time_ms = 0
    elapsed = time.time()

    if items_count > self.MaxVars:
        return S7Consts.errCliTooManyItems

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
        if item.WordLen == S7Consts.S7WLBit:
            s7_data_item[1] = self.TS_ResBit
        elif item.WordLen in (S7Consts.S7WLCounter, S7Consts.S7WLTimer):
            s7_data_item[1] = self.TS_ResOctet
        else:
            s7_data_item[1] = self.TS_ResByte

        if item.WordLen in (S7Consts.S7WLCounter, S7Consts.S7WLTimer):
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

    if offset > self._PDULength:
        return S7Consts.errCliSizeOverPDU

    S7.set_word_at(self.PDU, 2, offset)
    S7.set_word_at(self.PDU, 15, data_length)
    self.send_packet(self.PDU, offset)
    self.recv_iso_packet()

    if self._LastError == 0:
        self._LastError = self.cpu_error(S7.get_word_at(self.PDU, 17))
        if self._LastError != 0:
            return self._LastError

        items_written = S7.get_byte_at(self.PDU, 20)

        if items_written != items_count or items_written > self.MaxVars:
            self._LastError = S7Consts.errCliInvalidPlcAnswer
            return self._LastError

        for i, item in enumerate(items):
            if self.PDU[i + 21] == 0xFF:
                item.Result = 0
            else:
                item.Result = self.cpu_error(self.PDU[i + 21])

        self.Time_ms = int((time.time() - elapsed) * 1000)

    return self._LastError
