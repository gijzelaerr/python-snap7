import struct
import datetime
from .s7_consts import S7Consts
from .s7_timer import S7Timer


class S7Protocol:
    bias = 621355968000000000  # "decimicros" between 0001-01-01 00:00:00 and 1970-01-01 00:00:00

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
        if WordLength == S7Consts.S7WLBit:
            return 1
        elif WordLength in [S7Consts.S7WLByte, S7Consts.S7WLChar]:
            return 1
        elif WordLength in [S7Consts.S7WLWord, S7Consts.S7WLCounter, S7Consts.S7WLTimer, S7Consts.S7WLInt]:
            return 2
        elif WordLength in [S7Consts.S7WLDWord, S7Consts.S7WLDInt, S7Consts.S7WLReal]:
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
    def GetIntAt(Buffer, Pos):
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
    def GetUIntAt(Buffer, Pos):
        return struct.unpack_from(">H", Buffer, Pos)[0]

    @staticmethod
    def SetUIntAt(Buffer, Pos, Value):
        struct.pack_into(">H", Buffer, Pos, Value)

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
    def GetWordAt(Buffer, Pos):
        return S7.GetUIntAt(Buffer, Pos)

    @staticmethod
    def SetWordAt(Buffer, Pos, Value):
        S7.SetUIntAt(Buffer, Pos, Value)

    @staticmethod
    def GetDWordAt(Buffer, Pos):
        return S7.GetUDIntAt(Buffer, Pos)

    @staticmethod
    def SetDWordAt(Buffer, Pos, Value):
        S7.SetUDIntAt(Buffer, Pos, Value)

    @staticmethod
    def GetLWordAt(Buffer, Pos):
        return S7.GetULIntAt(Buffer, Pos)

    @staticmethod
    def SetLWordAt(Buffer, Pos, Value):
        S7.SetULIntAt(Buffer, Pos, Value)

    @staticmethod
    def GetRealAt(Buffer, Pos):
        Value = S7.GetUDIntAt(Buffer, Pos)
        return struct.unpack(">f", struct.pack(">I", Value))[0]

    @staticmethod
    def SetRealAt(Buffer, Pos, Value):
        FloatArray = struct.pack(">f", Value)
        Buffer[Pos : Pos + 4] = FloatArray

    @staticmethod
    def GetLRealAt(Buffer, Pos):
        Value = S7.GetULIntAt(Buffer, Pos)
        return struct.unpack(">d", struct.pack(">Q", Value))[0]

    @staticmethod
    def SetLRealAt(Buffer, Pos, Value):
        FloatArray = struct.pack(">d", Value)
        Buffer[Pos : Pos + 8] = FloatArray

    @staticmethod
    def GetDateTimeAt(Buffer, Pos):
        Year = S7.BCDtoByte(Buffer[Pos])
        Year += 2000 if Year < 90 else 1900
        Month = S7.BCDtoByte(Buffer[Pos + 1])
        Day = S7.BCDtoByte(Buffer[Pos + 2])
        Hour = S7.BCDtoByte(Buffer[Pos + 3])
        Min = S7.BCDtoByte(Buffer[Pos + 4])
        Sec = S7.BCDtoByte(Buffer[Pos + 5])
        MSec = (S7.BCDtoByte(Buffer[Pos + 6]) * 10) + (S7.BCDtoByte(Buffer[Pos + 7]) // 10)
        try:
            return datetime.datetime(Year, Month, Day, Hour, Min, Sec, MSec * 1000)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetDateTimeAt(Buffer, Pos, Value):
        Year = Value.year - 2000 if Value.year > 1999 else Value.year
        Buffer[Pos] = S7.ByteToBCD(Year)
        Buffer[Pos + 1] = S7.ByteToBCD(Value.month)
        Buffer[Pos + 2] = S7.ByteToBCD(Value.day)
        Buffer[Pos + 3] = S7.ByteToBCD(Value.hour)
        Buffer[Pos + 4] = S7.ByteToBCD(Value.minute)
        Buffer[Pos + 5] = S7.ByteToBCD(Value.second)
        MsecH = Value.microsecond // 10000
        MsecL = (Value.microsecond // 1000) % 10
        Dow = Value.isoweekday()
        Buffer[Pos + 6] = S7.ByteToBCD(MsecH)
        Buffer[Pos + 7] = S7.ByteToBCD(MsecL * 10 + Dow)

    @staticmethod
    def GetDateAt(Buffer, Pos):
        try:
            return datetime.datetime(1990, 1, 1) + datetime.timedelta(days=S7.GetIntAt(Buffer, Pos))
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetDateAt(Buffer, Pos, Value):
        S7.SetIntAt(Buffer, Pos, (Value - datetime.datetime(1990, 1, 1)).days)

    @staticmethod
    def GetTODAt(Buffer, Pos):
        try:
            return datetime.datetime(1, 1, 1) + datetime.timedelta(milliseconds=S7.GetDIntAt(Buffer, Pos))
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetTODAt(Buffer, Pos, Value):
        Time = Value.time()
        S7.SetDIntAt(Buffer, Pos, int(Time.hour * 3600000 + Time.minute * 60000 + Time.second * 1000 + Time.microsecond / 1000))

    @staticmethod
    def GetLTODAt(Buffer, Pos):
        try:
            return datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=S7.GetLIntAt(Buffer, Pos) // 100)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetLTODAt(Buffer, Pos, Value):
        Time = Value.time()
        S7.SetLIntAt(
            Buffer,
            Pos,
            int((Time.hour * 3600000000000 + Time.minute * 60000000000 + Time.second * 1000000000 + Time.microsecond * 1000)),
        )

    @staticmethod
    def GetLDTAt(Buffer, Pos):
        try:
            return datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=(S7.GetLIntAt(Buffer, Pos) // 100) + S7.bias)
        except ValueError:
            return datetime.datetime(1, 1, 1)

    @staticmethod
    def SetLDTAt(Buffer, Pos, Value):
        S7.SetLIntAt(Buffer, Pos, (Value - datetime.datetime(1, 1, 1)).total_seconds() * 1000000000 - S7.bias * 100)

    @staticmethod
    def GetDTLAt(Buffer, Pos):
        Year = Buffer[Pos] * 256 + Buffer[Pos + 1]
        Month = Buffer[Pos + 2]
        Day = Buffer[Pos + 3]
        Hour = Buffer[Pos + 5]
        Min = Buffer[Pos + 6]
        Sec = Buffer[Pos + 7]
        MSec = S7.GetUDIntAt(Buffer, Pos + 8) // 1000000
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
        S7.SetDIntAt(Buffer, Pos + 8, NanoSecs)

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
        size = S7.GetIntAt(Buffer, Pos + 2)
        return Buffer[Pos + 4 : Pos + 4 + size * 2].decode("utf-16-be")

    @staticmethod
    def SetWStringAt(Buffer, Pos, MaxCharNb, Value):
        size = len(Value)
        S7.SetIntAt(Buffer, Pos, MaxCharNb)
        S7.SetIntAt(Buffer, Pos + 2, size)
        Buffer[Pos + 4 : Pos + 4 + size * 2] = Value.encode("utf-16-be")

    @staticmethod
    def GetCharsAt(Buffer, Pos, Size):
        return Buffer[Pos : Pos + Size].decode("utf-8")

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
        return S7.BCDtoByte(Value & 0xFF) * 100 + S7.BCDtoByte(Value >> 8)

    @staticmethod
    def GetCounterAt(Buffer, Index):
        return S7.GetCounter(Buffer[Index])

    @staticmethod
    def ToCounter(Value):
        return (S7.ByteToBCD(Value // 100) << 8) | S7.ByteToBCD(Value % 100)

    @staticmethod
    def SetCounterAt(Buffer, Pos, Value):
        Buffer[Pos] = S7.ToCounter(Value)

    @staticmethod
    def GetS7TimerAt(Buffer, Pos):
        return S7Timer(Buffer[Pos : Pos + 12])

    @staticmethod
    def SetS7TimespanAt(Buffer, Pos, Value):
        S7.SetDIntAt(Buffer, Pos, int(Value.total_seconds() * 1000))

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
            return datetime.timedelta(microseconds=S7.GetLIntAt(Buffer, Pos) // 100)
        except ValueError:
            return datetime.timedelta()

    @staticmethod
    def SetLTimeAt(Buffer, Pos, Value):
        S7.SetLIntAt(Buffer, Pos, int(Value.total_seconds() * 1000000000))
