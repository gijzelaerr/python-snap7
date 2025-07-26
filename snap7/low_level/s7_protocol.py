import struct
import datetime
from .s7_timer import S7Timer


class S7Protocol:

    size_RD : int = 31 # Header Size when Reading
    size_WR : int = 35 # Header Size when Writing

    bias = 621355968000000000  # "decimicros" between 0001-01-01 00:00:00 and 1970-01-01 00:00:00

    # Iso over TCP constants
    isoTcpVersion = 3  # RFC 1006
    isoTcpPort = 102  # RFC 1006
    isoInvalidHandle = 0
    MaxTSAPLength = 16  # Max Length for Src and Dst TSAP
    MaxIsoFragments = 64  # Max fragments
    IsoPayload_Size = 4096  # Iso telegram Buffer size
    noError = 0

    # Error codes
    errTCPSocketCreation = 0x00000001
    errTCPConnectionTimeout = 0x00000002
    errTCPConnectionFailed = 0x00000003
    errTCPReceiveTimeout = 0x00000004
    errTCPDataReceive = 0x00000005
    errTCPSendTimeout = 0x00000006
    errTCPDataSend = 0x00000007
    errTCPConnectionReset = 0x00000008
    errTCPNotConnected = 0x00000009
    errTCPUnreachableHost = 0x00002751

    errIsoConnect = 0x00010000
    errIsoInvalidPDU = 0x00030000
    errIsoInvalidDataSize = 0x00040000
    errIsoMask = 0x000F0000
    errIsoBase = 0x0000FFFF
    errIsoDisconnect = 0x00020000  # Disconnect error
    errIsoNullPointer = 0x00050000  # Null passed as pointer
    errIsoShortPacket = 0x00060000  # A short packet received
    errIsoTooManyFragments = 0x00070000  # Too many packets without EoT flag
    errIsoPduOverflow = 0x00080000  # The sum of fragments data exceeded maximum packet size
    errIsoSendPacket = 0x00090000  # An error occurred during send
    errIsoRecvPacket = 0x000A0000  # An error occurred during recv
    errIsoInvalidParams = 0x000B0000  # Invalid TSAP params
    errIsoResvd_1 = 0x000C0000  # Unassigned
    errIsoResvd_2 = 0x000D0000  # Unassigned
    errIsoResvd_3 = 0x000E0000  # Unassigned
    errIsoResvd_4 = 0x000F0000  # Unassigned

    ISO_OPT_TCP_NODELAY = 0x00000001  # Disable Nagle algorithm
    ISO_OPT_INSIDE_MTU = 0x00000002  # Max packet size < MTU ethernet card

    errCliNegotiatingPDU = 0x00100000
    errCliInvalidParams = 0x00200000
    errCliJobPending = 0x00300000
    errCliTooManyItems = 0x00400000
    errCliInvalidWordLen = 0x00500000
    errCliPartialDataWritten = 0x00600000
    errCliSizeOverPDU = 0x00700000
    errCliInvalidPlcAnswer = 0x00800000
    errCliAddressOutOfRange = 0x00900000
    errCliInvalidTransportSize = 0x00A00000
    errCliWriteDataSizeMismatch = 0x00B00000
    errCliItemNotAvailable = 0x00C00000
    errCliInvalidValue = 0x00D00000
    errCliCannotStartPLC = 0x00E00000
    errCliAlreadyRun = 0x00F00000
    errCliCannotStopPLC = 0x01000000
    errCliCannotCopyRamToRom = 0x01100000
    errCliCannotCompress = 0x01200000
    errCliAlreadyStop = 0x01300000
    errCliFunNotAvailable = 0x01400000
    errCliUploadSequenceFailed = 0x01500000
    errCliInvalidDataSizeRecvd = 0x01600000
    errCliInvalidBlockType = 0x01700000
    errCliInvalidBlockNumber = 0x01800000
    errCliInvalidBlockSize = 0x01900000
    errCliNeedPassword = 0x01D00000
    errCliInvalidPassword = 0x01E00000
    errCliNoPasswordToSetOrClear = 0x01F00000
    errCliJobTimeout = 0x02000000
    errCliPartialDataRead = 0x02100000
    errCliBufferTooSmall = 0x02200000
    errCliFunctionRefused = 0x02300000
    errCliDestroying = 0x02400000
    errCliInvalidParamNumber = 0x02500000
    errCliCannotChangeParam = 0x02600000
    errCliFunctionNotImplemented = 0x02700000

    p_u16_RemotePort = 2
    p_i32_PingTimeout = 3
    p_i32_SendTimeout = 4
    p_i32_RecvTimeout = 5
    p_i32_PDURequest = 10

    S7AreaPE = 0x81
    S7AreaPA = 0x82
    S7AreaMK = 0x83
    S7AreaDB = 0x84
    S7AreaCT = 0x1C
    S7AreaTM = 0x1D

    S7WLBit = 0x01
    S7WLByte = 0x02
    S7WLChar = 0x03
    S7WLWord = 0x04
    S7WLInt = 0x05
    S7WLDWord = 0x06
    S7WLDInt = 0x07
    S7WLReal = 0x08
    S7WLCounter = 0x1C
    S7WLTimer = 0x1D

    S7CpuStatusUnknown = 0x00
    S7CpuStatusRun = 0x08
    S7CpuStatusStop = 0x04

    CONNTYPE_PG = 0x01
    CONNTYPE_OP = 0x02
    CONNTYPE_BASIC = 0x03

    S7_PN = bytearray(
        [
            0x03, 0x00, 0x00, 0x19,
            0x02, 0xf0, 0x80,
            0x32, 0x01, 0x00, 0x00,
            0x04, 0x00, 0x00, 0x08,
            0x00, 0x00, 0xf0, 0x00,
            0x00, 0x01, 0x00, 0x01,
            0x01, 0xe0  # PDU Length Requested = HI-LO Here Default 480 bytes
        ]
    )

    S7_GET_STAT = bytearray(
        [
            0x03, 0x00, 0x00, 0x21,
            0x02, 0xf0, 0x80, 0x32,
            0x07, 0x00, 0x00, 0x2c,
            0x00, 0x00, 0x08, 0x00,
            0x08, 0x00, 0x01, 0x12,
            0x04, 0x11, 0x44, 0x01,
            0x00, 0xff, 0x09, 0x00,
            0x04, 0x04, 0x24, 0x00,
            0x00
        ]
    )

    # SZL First telegram request
    S7_SZL_FIRST = bytearray(
        [
            0x03, 0x00, 0x00, 0x21,
            0x02, 0xf0, 0x80, 0x32,
            0x07, 0x00, 0x00,
            0x05, 0x00,  # Sequence out
            0x00, 0x08, 0x00,
            0x08, 0x00, 0x01, 0x12,
            0x04, 0x11, 0x44, 0x01,
            0x00, 0xff, 0x09, 0x00,
            0x04,
            0x00, 0x00,  # ID(29)
            0x00, 0x00  # Index(31)
        ]
    )

    # SZL Next telegram request
    S7_SZL_NEXT = bytearray(
        [
            0x03, 0x00, 0x00, 0x21,
            0x02, 0xf0, 0x80, 0x32,
            0x07, 0x00, 0x00, 0x06,
            0x00, 0x00, 0x0c, 0x00,
            0x04, 0x00, 0x01, 0x12,
            0x08, 0x12, 0x44, 0x01,
            0x01, # Sequence
            0x00, 0x00, 0x00, 0x00,
            0x0a, 0x00, 0x00, 0x00
        ]
    )

    S7_RW = bytearray(
        [
        # 31 - 35 bytes
        0x03, 0x00,
        0x00, 0x1f, # Telegram Length(Data Size + 31 or 35)
        0x02, 0xf0, 0x80, # COTP(see above for info)
        0x32, # S7 Protocol ID
        0x01, # Job Type
        0x00, 0x00, # Redundancy identification
        0x05, 0x00, # PDU Reference
        0x00, 0x0e, # Parameters Length
        0x00, 0x00, # Data Length = Size(bytes) + 4
        0x04, # Function 4 Read Var, 5 Write Var
        0x01, # Items count
        0x12, # Var spec.
        0x0a, # Length of remaining bytes
        0x10, # Syntax ID
        0x02, # Transport Size idx=22
        0x00, 0x00, # Num Elements
        0x00, 0x00, # DB Number ( if any, else 0)
        0x84, # Area Type
        0x00, 0x00, 0x00, # Area Offset
        # WR area
        0x00, # Reserved
        0x04, # Transport size
        0x00, 0x00, # Data Length * 8 ( if not bit or timer or counter)
        ]
    )


    ISO_CR = bytearray(
        [
            # TPKT(RFC1006 Header)
            0x03,  # RFC 1006 ID (3)
            0x00,  # Reserved, always 0
            0x00,  # High part of packet lenght (entire frame, payload and TPDU included)
            0x16,  # Low part of packet lenght (entire frame, payload and TPDU included)
            # COTP(ISO 8073 Header)
            0x11,  # PDU Size Length
            0xE0,  # CR (Connection Request) ID
            0x00,  # Dst Reference HI
            0x00,  # Dst Reference LO
            0x00,  # Src Reference HI
            0x01,  # Src Reference LO
            0x00,  # Class + Options Flags
            0xC0,  # PDU Max Length ID
            0x01,  # PDU Max Length HI
            0x0A,  # PDU Max Length LO
            0xC1,  # Src TSAP Identifier
            0x02,  # Src TSAP Length
            0x01,  # Src TSAP HI (will be overwritten)
            0x00,  # Src TSAP LO (will be overwritten)
            0xC2,  # Dst TSAP Identifier
            0x02,  # Dst TSAP Length
            0x01,  # Dst TSAP HI (will be overwritten)
            0x02,  # Dst TSAP LO (will be overwritten)
        ]
    )

    # S7 Set Session Password
    S7_SET_PWD = bytearray(
        [
            0x03, 0x00, 0x00, 0x25,
            0x02, 0xf0, 0x80, 0x32,
            0x07, 0x00, 0x00, 0x27,
            0x00, 0x00, 0x08, 0x00,
            0x0c, 0x00, 0x01, 0x12,
            0x04, 0x11, 0x45, 0x01,
            0x00, 0xff, 0x09, 0x00,
            0x08, # 8 Char Encoded Password
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00
        ]
    )

    # S7 Clear Session Password

    S7_CLR_PWD = bytearray(
        [
            0x03, 0x00, 0x00, 0x1d,
            0x02, 0xf0, 0x80, 0x32,
            0x07, 0x00, 0x00, 0x29,
            0x00, 0x00, 0x08, 0x00,
            0x04, 0x00, 0x01, 0x12,
            0x04, 0x11, 0x45, 0x02,
            0x00, 0x0a, 0x00, 0x00,
            0x00
        ]
    )

    # Block_OB = 0x38
    # Block_DB = 0x41
    # Block_SDB = 0x42
    # Block_FC = 0x43
    # Block_SFC = 0x44
    # Block_FB = 0x45
    # Block_SFB = 0x46
    # SubBlk_OB = 0x08
    # SubBlk_DB = 0x0A
    # SubBlk_SDB = 0x0B
    # SubBlk_FC = 0x0C
    # SubBlk_SFC = 0x0D
    # SubBlk_FB = 0x0E
    # SubBlk_SFB = 0x0F
    #
    # BlockLangAWL = 0x01
    # BlockLangKOP = 0x02
    # BlockLangFUP = 0x03
    # BlockLangSCL = 0x04
    # BlockLangDB = 0x05
    # BlockLangGRAPH = 0x06
    #
    # MaxVars = 20
    #
    TS_ResBit = 0x03
    TS_ResByte = 0x04
    TS_ResInt = 0x05
    TS_ResReal = 0x07
    TS_ResOctet = 0x09
    #
    # Code7Ok = 0x0000
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



    @staticmethod
    def BCDtoByte(B):
        return ((B >> 4) * 10) + (B & 0x0F)

    @staticmethod
    def ByteToBCD(Value):
        return ((Value // 10) << 4) | (Value % 10)

    @staticmethod
    def CopyFrom(Buffer, Pos, Size):
        return Buffer[Pos : Pos + Size]

    @staticmethod
    def DataSizeByte(WordLength):
        if WordLength == S7Protocol.S7WLBit:
            return 1
        elif WordLength in [S7Protocol.S7WLByte, S7Protocol.S7WLChar]:
            return 1
        elif WordLength in [S7Protocol.S7WLWord, S7Protocol.S7WLCounter, S7Protocol.S7WLTimer, S7Protocol.S7WLInt]:
            return 2
        elif WordLength in [S7Protocol.S7WLDWord, S7Protocol.S7WLDInt, S7Protocol.S7WLReal]:
            return 4
        else:
            return 0

    @staticmethod
    def GetBitAt(Buffer, Pos, Bit):
        Mask = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]
        Bit = max(0, min(Bit, 7))
        return (Buffer[Pos] & Mask[Bit]) != 0

    @staticmethod
    def SetBitAt(Buffer, Pos, Bit, Value):
        Mask = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]
        Bit = max(0, min(Bit, 7))
        if Value:
            Buffer[Pos] |= Mask[Bit]
        else:
            Buffer[Pos] &= ~Mask[Bit]

    @staticmethod
    def GetSIntAt(Buffer, Pos):
        Value = Buffer[Pos]
        return Value if Value < 128 else Value - 256

    @staticmethod
    def SetSIntAt(Buffer, Pos, Value):
        Value = max(-128, min(Value, 127))
        Buffer[Pos] = Value

    @staticmethod
    def get_int_at(Buffer, Pos):
        return struct.unpack_from(">h", Buffer, Pos)[0]

    @staticmethod
    def SetIntAt(Buffer, Pos, Value):
        struct.pack_into(">h", Buffer, Pos, Value)

    @staticmethod
    def GetDIntAt(Buffer, Pos):
        return struct.unpack_from(">i", Buffer, Pos)[0]

    @staticmethod
    def SetDIntAt(Buffer, Pos, Value):
        struct.pack_into(">i", Buffer, Pos, Value)

    @staticmethod
    def GetLIntAt(Buffer, Pos):
        return struct.unpack_from(">q", Buffer, Pos)[0]

    @staticmethod
    def SetLIntAt(Buffer, Pos, Value):
        struct.pack_into(">q", Buffer, Pos, Value)

    @staticmethod
    def GetUSIntAt(Buffer, Pos):
        return Buffer[Pos]

    @staticmethod
    def SetUSIntAt(Buffer, Pos, Value):
        Buffer[Pos] = Value

    @staticmethod
    def get_uint_at(buffer, pos):
        return (buffer[pos] << 8) | buffer[pos + 1]

    @staticmethod
    def set_uint_at(buffer, pos, value):
        buffer[pos] = (value >> 8) & 0xFF
        buffer[pos + 1] = value & 0xFF

    @staticmethod
    def GetUDIntAt(Buffer, Pos):
        return struct.unpack_from(">I", Buffer, Pos)[0]

    @staticmethod
    def SetUDIntAt(Buffer, Pos, Value):
        struct.pack_into(">I", Buffer, Pos, Value)

    @staticmethod
    def GetULIntAt(Buffer, Pos):
        return struct.unpack_from(">Q", Buffer, Pos)[0]

    @staticmethod
    def SetULIntAt(Buffer, Pos, Value):
        struct.pack_into(">Q", Buffer, Pos, Value)

    @staticmethod
    def GetByteAt(Buffer, Pos):
        return Buffer[Pos]

    @staticmethod
    def SetByteAt(Buffer, Pos, Value):
        Buffer[Pos] = Value

    @staticmethod
    def get_word_at(Buffer, Pos):
        return S7Protocol.get_uint_at(Buffer, Pos)

    @staticmethod
    def set_word_at(Buffer, Pos, Value):
        S7Protocol.set_uint_at(Buffer, Pos, Value)

    @staticmethod
    def GetDWordAt(Buffer, Pos):
        return S7Protocol.GetUDIntAt(Buffer, Pos)

    @staticmethod
    def SetDWordAt(Buffer, Pos, Value):
        S7Protocol.SetUDIntAt(Buffer, Pos, Value)

    @staticmethod
    def GetLWordAt(Buffer, Pos):
        return S7Protocol.GetULIntAt(Buffer, Pos)

    @staticmethod
    def SetLWordAt(Buffer, Pos, Value):
        S7Protocol.SetULIntAt(Buffer, Pos, Value)

    @staticmethod
    def GetRealAt(Buffer, Pos):
        Value = S7Protocol.GetUDIntAt(Buffer, Pos)
        return struct.unpack(">f", struct.pack(">I", Value))[0]

    @staticmethod
    def SetRealAt(Buffer, Pos, Value):
        FloatArray = struct.pack(">f", Value)
        Buffer[Pos : Pos + 4] = FloatArray

    @staticmethod
    def GetLRealAt(Buffer, Pos):
        Value = S7Protocol.GetULIntAt(Buffer, Pos)
        return struct.unpack(">d", struct.pack(">Q", Value))[0]

    @staticmethod
    def SetLRealAt(Buffer, Pos, Value):
        FloatArray = struct.pack(">d", Value)
        Buffer[Pos : Pos + 8] = FloatArray

    @staticmethod
    def GetDateTimeAt(Buffer, Pos):
        Year = S7Protocol.BCDtoByte(Buffer[Pos])
        Year += 2000 if Year < 90 else 1900
        Month = S7Protocol.BCDtoByte(Buffer[Pos + 1])
        Day = S7Protocol.BCDtoByte(Buffer[Pos + 2])
        Hour = S7Protocol.BCDtoByte(Buffer[Pos + 3])
        Min = S7Protocol.BCDtoByte(Buffer[Pos + 4])
        Sec = S7Protocol.BCDtoByte(Buffer[Pos + 5])
        MSec = (S7Protocol.BCDtoByte(Buffer[Pos + 6]) * 10) + (S7Protocol.BCDtoByte(Buffer[Pos + 7]) // 10)
        try:
            return datetime.datetime(Year, Month, Day, Hour, Min, Sec, MSec * 1000)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetDateTimeAt(Buffer, Pos, Value):
        Year = Value.year - 2000 if Value.year > 1999 else Value.year
        Buffer[Pos] = S7Protocol.ByteToBCD(Year)
        Buffer[Pos + 1] = S7Protocol.ByteToBCD(Value.month)
        Buffer[Pos + 2] = S7Protocol.ByteToBCD(Value.day)
        Buffer[Pos + 3] = S7Protocol.ByteToBCD(Value.hour)
        Buffer[Pos + 4] = S7Protocol.ByteToBCD(Value.minute)
        Buffer[Pos + 5] = S7Protocol.ByteToBCD(Value.second)
        MsecH = Value.microsecond // 10000
        MsecL = (Value.microsecond // 1000) % 10
        Dow = Value.isoweekday()
        Buffer[Pos + 6] = S7Protocol.ByteToBCD(MsecH)
        Buffer[Pos + 7] = S7Protocol.ByteToBCD(MsecL * 10 + Dow)

    @staticmethod
    def GetDateAt(Buffer, Pos):
        try:
            return datetime.datetime(1990, 1, 1) + datetime.timedelta(days=S7Protocol.get_int_at(Buffer, Pos))
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetDateAt(Buffer, Pos, Value):
        S7Protocol.SetIntAt(Buffer, Pos, (Value - datetime.datetime(1990, 1, 1)).days)

    @staticmethod
    def GetTODAt(Buffer, Pos):
        try:
            return datetime.datetime(1, 1, 1) + datetime.timedelta(milliseconds=S7Protocol.GetDIntAt(Buffer, Pos))
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetTODAt(Buffer, Pos, Value):
        Time = Value.time()
        S7Protocol.SetDIntAt(Buffer, Pos, int(Time.hour * 3600000 + Time.minute * 60000 + Time.second * 1000 + Time.microsecond / 1000))

    @staticmethod
    def GetLTODAt(Buffer, Pos):
        try:
            return datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=S7Protocol.GetLIntAt(Buffer, Pos) // 100)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetLTODAt(Buffer, Pos, Value):
        Time = Value.time()
        S7Protocol.SetLIntAt(
            Buffer,
            Pos,
            int((Time.hour * 3600000000000 + Time.minute * 60000000000 + Time.second * 1000000000 + Time.microsecond * 1000)),
        )

    @staticmethod
    def GetLDTAt(Buffer, Pos):
        try:
            return datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=(S7Protocol.GetLIntAt(Buffer, Pos) // 100) + S7Protocol.bias)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetLDTAt(Buffer, Pos, Value):
        S7Protocol.SetLIntAt(Buffer, Pos, (Value - datetime.datetime(1, 1, 1)).total_seconds() * 1000000000 - S7Protocol.bias * 100)

    @staticmethod
    def GetDTLAt(Buffer, Pos):
        Year = Buffer[Pos] * 256 + Buffer[Pos + 1]
        Month = Buffer[Pos + 2]
        Day = Buffer[Pos + 3]
        Hour = Buffer[Pos + 5]
        Min = Buffer[Pos + 6]
        Sec = Buffer[Pos + 7]
        MSec = S7Protocol.GetUDIntAt(Buffer, Pos + 8) // 1000000
        try:
            return datetime.datetime(Year, Month, Day, Hour, Min, Sec, MSec)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetDTLAt(Buffer, Pos, Value):
        Year = Value.year
        Month = Value.month
        Day = Value.day
        Hour = Value.hour
        Min = Value.minute
        Sec = Value.second
        Dow = Value.isoweekday()
        NanoSecs = Value.microsecond * 1000000
        Buffer[Pos : Pos + 2] = struct.pack(">H", Year)
        Buffer[Pos + 2] = Month
        Buffer[Pos + 3] = Day
        Buffer[Pos + 4] = Dow
        Buffer[Pos + 5] = Hour
        Buffer[Pos + 6] = Min
        Buffer[Pos + 7] = Sec
        S7Protocol.SetDIntAt(Buffer, Pos + 8, NanoSecs)

    @staticmethod
    def GetStringAt(Buffer, Pos):
        size = Buffer[Pos + 1]
        return Buffer[Pos + 2 : Pos + 2 + size].decode("utf-8")

    @staticmethod
    def SetStringAt(Buffer, Pos, MaxLen, Value):
        size = len(Value)
        Buffer[Pos] = MaxLen
        Buffer[Pos + 1] = size
        Buffer[Pos + 2 : Pos + 2 + size] = Value.encode("utf-8")

    @staticmethod
    def GetWStringAt(Buffer, Pos):
        size = S7Protocol.get_int_at(Buffer, Pos + 2)
        return Buffer[Pos + 4 : Pos + 4 + size * 2].decode("utf-16-be")

    @staticmethod
    def SetWStringAt(Buffer, Pos, MaxCharNb, Value):
        size = len(Value)
        S7Protocol.SetIntAt(Buffer, Pos, MaxCharNb)
        S7Protocol.SetIntAt(Buffer, Pos + 2, size)
        Buffer[Pos + 4 : Pos + 4 + size * 2] = Value.encode("utf-16-be")

    @staticmethod
    def get_chars_at(buffer : bytearray, pos : int, size : int) -> str:
        if len(buffer) < pos + size or size < 0:
            return ""
        return buffer[pos: pos + size].decode("utf-8")

    @staticmethod
    def SetCharsAt(Buffer, Pos, Value):
        MaxLen = len(Buffer) - Pos
        MaxLen = min(MaxLen, len(Value))
        Buffer[Pos : Pos + MaxLen] = Value.encode("utf-8")

    @staticmethod
    def GetWCharsAt(Buffer, Pos, SizeInCharNb):
        return Buffer[Pos : Pos + SizeInCharNb * 2].decode("utf-16-be")

    @staticmethod
    def SetWCharsAt(Buffer, Pos, Value):
        MaxLen = (len(Buffer) - Pos) // 2
        MaxLen = min(MaxLen, len(Value))
        Buffer[Pos : Pos + MaxLen * 2] = Value.encode("utf-16-be")

    @staticmethod
    def GetCounter(Value):
        return S7Protocol.BCDtoByte(Value & 0xFF) * 100 + S7Protocol.BCDtoByte(Value >> 8)

    @staticmethod
    def GetCounterAt(Buffer, Index):
        return S7Protocol.GetCounter(Buffer[Index])

    @staticmethod
    def ToCounter(Value):
        return (S7Protocol.ByteToBCD(Value // 100) << 8) | S7Protocol.ByteToBCD(Value % 100)

    @staticmethod
    def SetCounterAt(Buffer, Pos, Value):
        Buffer[Pos] = S7Protocol.ToCounter(Value)

    @staticmethod
    def GetS7TimerAt(Buffer, Pos):
        return S7Timer(Buffer[Pos : Pos + 12])

    @staticmethod
    def SetS7TimespanAt(Buffer, Pos, Value):
        S7Protocol.SetDIntAt(Buffer, Pos, int(Value.total_seconds() * 1000))

    @staticmethod
    def GetS7TimespanAt(Buffer, Pos):
        if len(Buffer) < Pos + 4:
            return datetime.timedelta()
        a = struct.unpack_from(">i", Buffer, Pos)[0]
        return datetime.timedelta(milliseconds=a)

    @staticmethod
    def GetLTimeAt(Buffer, Pos):
        if len(Buffer) < Pos + 8:
            return datetime.timedelta()
        try:
            return datetime.timedelta(microseconds=S7Protocol.GetLIntAt(Buffer, Pos) // 100)
        except ValueError:
            return datetime.timedelta()

    @staticmethod
    def SetLTimeAt(Buffer, Pos, Value):
        S7Protocol.SetLIntAt(Buffer, Pos, int(Value.total_seconds() * 1000000000))

    @classmethod
    def cpu_error(cls, error_code):
        if error_code == 0:
            return 0
        elif cls.Code7AddressOutOfRange == error_code:
            return cls.errCliAddressOutOfRange
        elif cls.Code7InvalidTransportSize == error_code:
            return cls.errCliInvalidTransportSize
        elif cls.Code7WriteDataSizeMismatch == error_code:
            return cls.errCliWriteDataSizeMismatch
        elif cls.Code7ResItemNotAvailable == error_code or cls.Code7ResItemNotAvailable1 == error_code:
            return cls.errCliItemNotAvailable
        elif cls.Code7DataOverPDU == error_code:
            return cls.errCliSizeOverPDU
        elif cls.Code7InvalidValue == error_code:
            return cls.errCliInvalidValue
        elif cls.Code7FunNotAvailable == error_code:
            return cls.errCliFunNotAvailable
        elif cls.Code7NeedPassword == error_code:
            return cls.errCliNeedPassword
        elif cls.Code7InvalidPassword == error_code:
            return cls.errCliInvalidPassword
        elif cls.Code7NoPasswordToClear == error_code or cls.Code7NoPasswordToSet == error_code:
            return cls.errCliNoPasswordToSetOrClear

        return cls.errCliFunctionRefused