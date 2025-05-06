from ctypes import Structure, c_ubyte, c_ushort, sizeof, c_ulong
from snap7.low_level.s7_consts import S7Consts
import socket

# TPKT Header - ISO on TCP - RFC 1006 (4 bytes)
class TTPKT(Structure):
    _fields_ = [
        ("Version", c_ubyte),    # Always 3 for RFC 1006
        ("Reserved", c_ubyte),   # 0
        ("HI_Lenght", c_ubyte),  # High part of packet length (entire frame, payload and TPDU included)
        ("LO_Lenght", c_ubyte)   # Low part of packet length (entire frame, payload and TPDU included)
    ]

# TCOPT_Params structure
class TCOPT_Params(Structure):
    _fields_ = [
        ("PduSizeCode", c_ubyte),
        ("PduSizeLen", c_ubyte),
        ("PduSizeVal", c_ubyte),
        ("TSAP", c_ubyte * 245)  # We don't know in advance these fields....
    ]

# COTP Header for CONNECTION REQUEST/CONFIRM - DISCONNECT REQUEST/CONFIRM
class TCOTP_CO(Structure):
    _fields_ = [
        ("HLength", c_ubyte),     # Header length : initialized to 6 (length without params - 1)
        ("PDUType", c_ubyte),     # PDU Type
        ("DstRef", c_ushort),     # Destination reference : Always 0x0000
        ("SrcRef", c_ushort),     # Source reference : Always 0x0000
        ("CO_R", c_ubyte),        # Class + Option or Reason
        ("Params", TCOPT_Params)  # Parameter data
    ]

# COTP Header for DATA EXCHANGE
class TCOTP_DT(Structure):
    _fields_ = [
        ("HLength", c_ubyte),   # Header length : 3 for this header
        ("PDUType", c_ubyte),   # PDU Type
        ("EoT_Num", c_ubyte)    # EOT (bit 7) + PDU Number (bits 0..6)
    ]

# Info part of a PDU, only common parts
class TIsoHeaderInfo(Structure):
    _fields_ = [
        ("TPKT", TTPKT),       # TPKT Header
        ("HLength", c_ubyte),  # Header length
        ("PDUType", c_ubyte)   # PDU type
    ]

# PDU Type constants
pdu_type_CR = 0xE0  # Connection request
pdu_type_CC = 0xD0  # Connection confirm
pdu_type_DR = 0x80  # Disconnect request
pdu_type_DC = 0xC0  # Disconnect confirm
pdu_type_DT = 0xF0  # Data transfer

pdu_EoT = 0x80  # End of Transmission Packet (This packet is complete)

# DataHeaderSize and IsoFrameSize
DataHeaderSize = c_ulong(sizeof(TTPKT) + sizeof(TCOTP_DT))
IsoFrameSize = c_ulong( S7Consts.IsoPayload_Size + DataHeaderSize.value)

# TIsoControlPDU structure
class TIsoControlPDU(Structure):
    _fields_ = [
        ("TPKT", TTPKT),  # TPKT Header
        ("COTP", TCOTP_CO)  # COPT Header for CONNECTION stuffs
    ]

# TIsoPayload type
TIsoPayload = c_ubyte *  S7Consts.IsoPayload_Size

# TIsoDataPDU structure
class TIsoDataPDU(Structure):
    _fields_ = [
        ("TPKT", TTPKT),  # TPKT Header
        ("COTP", TCOTP_DT),  # COPT Header for DATA EXCHANGE
        ("Payload", TIsoPayload)  # Payload
    ]

# TPDUKind enum
class TPDUKind:
    pkConnectionRequest = 0
    pkDisconnectRequest = 1
    pkEmptyFragment = 2
    pkInvalidPDU = 3
    pkUnrecognizedType = 4
    pkValidData = 5

class S7IsoTcpSocket:


    def __init__(self, sock, src_tsap, dst_tsap):
        self.RecvTimeout = 3000
        self.RemotePort = S7Consts.isoTcpPort
        self.DstRef = 0x0000
        self.SrcRef = 0x0100
        self.IsoPDUSize = 1024
        self.IsoMaxFragments = S7Consts.MaxIsoFragments
        self.LastIsoError = 0




    #
    # def checkPDU(self, pPDU, PduTypeExpected):
    #     self.ClrIsoError()
    #     if pPDU is not None:
    #         Info = PIsoHeaderInfo(pPDU)
    #         Size = self.PDUSize(pPDU)
    #         if (Size < 7 or Size > S7Consts.IsoPayload_Size or
    #             Info.HLength < sizeof(TCOTP_DT) - 1 or
    #             Info.PDUType != PduTypeExpected):
    #             return self.SetIsoError(S7Consts.errIsoInvalidPDU)
    #         else:
    #             return S7Consts.noError
    #     else:
    #         return self.SetIsoError(S7Consts.errIsoNullPointer)
    #
    # def SetIsoError(self, Error):
    #     self.LastIsoError = Error | self.LastTcpError
    #     return self.LastIsoError
    #
    # def ClrIsoError(self):
    #     self.LastIsoError = 0
    #     self.LastTcpError = 0
    #
    # def BuildControlPDU(self):
    #     self.ClrIsoError()
    #     self.FControlPDU.COTP.Params.PduSizeCode = 0xC0
    #     self.FControlPDU.COTP.Params.PduSizeLen = 0x01
    #     pdu_size_map = {
    #         128: 0x07,
    #         256: 0x08,
    #         512: 0x09,
    #         1024: 0x0A,
    #         2048: 0x0B,
    #         4096: 0x0C,
    #         8192: 0x0D
    #     }
    #     self.FControlPDU.COTP.Params.PduSizeVal = pdu_size_map.get(self.IsoPDUSize, 0x0B)
    #     self.FControlPDU.COTP.Params.TSAP = [
    #         0xC1, 2, (self.SrcTSap >> 8) & 0xFF, self.SrcTSap & 0xFF,
    #         0xC2, 2, (self.DstTSap >> 8) & 0xFF, self.DstTSap & 0xFF
    #     ]
    #     ParLen = 11
    #     IsoLen = sizeof(TTPKT) + 7 + ParLen
    #     self.FControlPDU.TPKT.Version = S7Consts.isoTcpVersion
    #     self.FControlPDU.TPKT.Reserved = 0
    #     self.FControlPDU.TPKT.HI_Lenght = 0
    #     self.FControlPDU.TPKT.LO_Lenght = IsoLen
    #     self.FControlPDU.COTP.HLength = ParLen + 6
    #     self.FControlPDU.COTP.PDUType = pdu_type_CR
    #     self.FControlPDU.COTP.DstRef = self.DstRef
    #     self.FControlPDU.COTP.SrcRef = self.SrcRef
    #     self.FControlPDU.COTP.CO_R = 0x00
    #     return S7Consts.noError
    #
    # def PDUSize(self, pPDU):
    #     return PIsoHeaderInfo(pPDU).TPKT.HI_Lenght * 256 + PIsoHeaderInfo(pPDU).TPKT.LO_Lenght
    #
    # def IsoParsePDU(self, pdu):
    #     pass
    #
    # def IsoConfirmConnection(self, PDUType):
    #     CPDU = PIsoControlPDU(self.PDU)
    #     self.ClrIsoError()
    #     self.PDU.COTP.PDUType = PDUType
    #     TempRef = CPDU.COTP.DstRef
    #     CPDU.COTP.DstRef = CPDU.COTP.SrcRef
    #     CPDU.COTP.SrcRef = 0x0100
    #     return self.SendPacket(self.PDU, self.PDUSize(self.PDU))
    #
    # def FragmentSkipped(self, Size):
    #     pass
    #
    # def isoConnect(self):
    #     self.BuildControlPDU()
    #     ControlPDU = self.FControlPDU
    #     Result = self.checkPDU(ControlPDU, pdu_type_CR)
    #     if Result != 0:
    #         return Result
    #     Result = self.SckConnect()
    #     if Result == S7Consts.noError:
    #         Length = self.PDUSize(ControlPDU)
    #         self.SendPacket(ControlPDU, Length)
    #         if self.LastTcpError == 0:
    #             TmpControlPDU = ControlPDU
    #             self.RecvPacket(TmpControlPDU, sizeof(TTPKT))
    #             if self.LastTcpError == 0:
    #                 Length = self.PDUSize(TmpControlPDU)
    #                 if Length <= sizeof(TIsoControlPDU) and Length > sizeof(TTPKT):
    #                     TmpControlPDU += sizeof(TTPKT)
    #                     Length -= sizeof(TTPKT)
    #                     self.RecvPacket(TmpControlPDU, Length)
    #                     if self.LastTcpError == 0:
    #                         Result = self.checkPDU(ControlPDU, pdu_type_CC)
    #                         if Result != 0:
    #                             self.LastIsoError = Result
    #                     else:
    #                         Result = self.SetIsoError(S7Consts.errIsoRecvPacket)
    #                 else:
    #                     Result = self.SetIsoError(S7Consts.errIsoInvalidPDU)
    #             else:
    #                 Result = self.SetIsoError(S7Consts.errIsoRecvPacket)
    #             if Result != 0:
    #                 self.Purge()
    #         else:
    #             Result = self.SetIsoError(S7Consts.errIsoSendPacket)
    #         if Result != 0:
    #             self.SckDisconnect()
    #     return Result
    #
    # def isoSendBuffer(self, Data, Size):
    #     self.ClrIsoError()
    #     IsoSize = Size + DataHeaderSize
    #     if 0 < IsoSize <= IsoFrameSize:
    #         self.PDU.TPKT.Version = S7Consts.isoTcpVersion
    #         self.PDU.TPKT.Reserved = 0
    #         self.PDU.TPKT.HI_Lenght = (IsoSize >> 8) & 0xFF
    #         self.PDU.TPKT.LO_Lenght = IsoSize & 0xFF
    #         self.PDU.COTP.HLength = sizeof(TCOTP_DT) - 1
    #         self.PDU.COTP.PDUType = pdu_type_DT
    #         self.PDU.COTP.EoT_Num = pdu_EoT
    #         if Data is not None:
    #             self.PDU.Payload = Data[:Size]
    #         self.SendPacket(self.PDU, IsoSize)
    #         if self.LastTcpError != 0:
    #             return self.SetIsoError(S7Consts.errIsoSendPacket)
    #     else:
    #         return self.SetIsoError(S7Consts.errIsoInvalidDataSize)
    #     return S7Consts.noError
    #
    # def isoRecvBuffer(self, Data, Size):
    #     self.ClrIsoError()
    #     Size = 0
    #     Result = self.isoRecvPDU(self.PDU)
    #     if Result == 0:
    #         Size = self.PDUSize(self.PDU) - DataHeaderSize
    #         if Data is not None:
    #             Data[:] = self.PDU.Payload[:Size]
    #     return Result
    #
    # def isoExchangeBuffer(self, Data, Size):
    #     self.ClrIsoError()
    #     Result = self.isoSendBuffer(Data, Size)
    #     if Result == 0:
    #         Result = self.isoRecvBuffer(Data, Size)
    #     return Result
    #
    # def IsoPDUReady(self):
    #     self.ClrIsoError()
    #     return self.PacketReady(sizeof(TCOTP_DT))
    #
    # def isoDisconnect(self, OnlyTCP):
    #     self.ClrIsoError()
    #     if self.Connected:
    #         self.Purge()
    #     self.LastIsoError = 0
    #     if not OnlyTCP:
    #         if self.Connected:
    #             self.FControlPDU.COTP.PDUType = pdu_type_DR
    #         Result = self.checkPDU(self.FControlPDU, pdu_type_DR)
    #         if Result != 0:
    #             return Result
    #         self.SendPacket(self.FControlPDU, self.PDUSize(self.FControlPDU))
    #         if self.LastTcpError != 0:
    #             return self.SetIsoError(S7Consts.errIsoSendPacket)
    #     self.SckDisconnect()
    #     if self.LastTcpError != 0:
    #         return self.SetIsoError(S7Consts.errIsoDisconnect)
    #     return 0
    #
    # def isoSendPDU(self, Data):
    #     self.ClrIsoError()
    #     Result = self.checkPDU(Data, pdu_type_DT)
    #     if Result == 0:
    #         self.SendPacket(Data, self.PDUSize(Data))
    #         if self.LastTcpError != 0:
    #             return self.SetIsoError(S7Consts.errIsoSendPacket)
    #     return Result
    #
    # def isoRecvFragment(self, From, Max, Size, EoT):
    #     self.ClrIsoError()
    #     Size = 0
    #     EoT = False
    #     self.RecvPacket(self.PDU, DataHeaderSize)
    #     if self.LastTcpError == 0:
    #         PDUType = self.PDU.COTP.PDUType
    #         if PDUType in [pdu_type_CR, pdu_type_DR]:
    #             EoT = True
    #         elif PDUType == pdu_type_DT:
    #             EoT = (self.PDU.COTP.EoT_Num & 0x80) == 0x80
    #         else:
    #             return self.SetIsoError(S7Consts.errIsoInvalidPDU)
    #         DataLength = self.PDUSize(self.PDU) - DataHeaderSize
    #         if self.checkPDU(self.PDU, PDUType) != 0:
    #             return self.LastIsoError
    #         if DataLength > 0:
    #             if DataLength <= Max:
    #                 self.RecvPacket(From, DataLength)
    #                 if self.LastTcpError != 0:
    #                     return self.SetIsoError(S7Consts.errIsoRecvPacket)
    #                 else:
    #                     Size = DataLength
    #             else:
    #                 return self.SetIsoError(S7Consts.errIsoPduOverflow)
    #     else:
    #         return self.SetIsoError(S7Consts.errIsoRecvPacket)
    #     return self.LastIsoError
    #
    # def isoRecvPDU(self, Data):
    #     self.ClrIsoError()
    #     NumParts = 1
    #     Offset = 0
    #     Complete = False
    #     pData = self.PDU.Payload
    #     while not Complete and self.LastIsoError == 0:
    #         pData = pData[Offset:]
    #         max_size = S7Consts.IsoPayload_Size - Offset
    #         if max_size > 0:
    #             Result = self.isoRecvFragment(pData, max_size, Received, Complete)
    #             if Result == 0 and not Complete:
    #                 NumParts += 1
    #                 Offset += Received
    #                 if NumParts > self.IsoMaxFragments:
    #                     Result = self.SetIsoError(S7Consts.errIsoTooManyFragments)
    #         else:
    #             Result = self.SetIsoError(S7Consts.errIsoTooManyFragments)
    #     if Result == 0:
    #         Size = Offset + Received + DataHeaderSize
    #         self.PDU.TPKT.HI_Lenght = (Size >> 8) & 0xFF
    #         self.PDU.TPKT.LO_Lenght = Size & 0xFF
    #         if Data is not self.PDU:
    #             Data[:] = self.PDU[:Size]
    #     else:
    #         if self.LastTcpError != WSAECONNRESET:
    #             self.Purge()
    #     return Result
    #
    # def isoExchangePDU(self, Data):
    #     self.ClrIsoError()
    #     Result = self.isoSendPDU(Data)
    #     if Result == 0:
    #         Result = self.isoRecvPDU(Data)
    #     return Result
    #
    # def IsoPeek(self, pPDU, PduKind):
    #     Info = PIsoHeaderInfo(pPDU)
    #     IsoLen = self.PDUSize(Info)
    #     if IsoLen == DataHeaderSize:
    #         PduKind = pkEmptyFragment
    #         return
    #     if IsoLen < DataHeaderSize:
    #         PduKind = pkInvalidPDU
    #         return
    #     if IsoLen > DataHeaderSize:
    #         if Info.PDUType == pdu_type_CR:
    #             PduKind = pkConnectionRequest
    #         elif Info.PDUType == pdu_type_DR:
    #             PduKind = pkDisconnectRequest
    #         elif Info.PDUType == pdu_type_DT:
    #             PduKind = pkValidData
    #         else:
    #             PduKind = pkUnrecognizedType