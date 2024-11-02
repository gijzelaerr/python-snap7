from ctypes import (
    c_uint8,
    c_uint16,
    Structure,
    c_byte,
)

from .snap_msg_sock import TMsgSocket

word = c_uint16
byte = c_byte
u_char = c_uint8

isoTcpVersion = 3  # RFC 1006
iso_tcp_port = 102  # RFC 1006
isoInvalidHandle = 0
MaxTSAPLength = 16  # Max Lenght for Src and Dst TSAP
MaxIsoFragments = 64  # Max fragments
IsoPayload_Size = 4096  # Iso telegram Buffer size

noError = 0


class TTPKT(Structure):
    _fields_ = [
        ("Version", u_char),  # Always 3 for RFC 1006
        ("Reserved", u_char),  # 0
        ("HI_Lenght", u_char),  # High part of packet length (entire frame, payload and TPDU included)
        ("LO_Lenght", u_char),  # Low part of packet length (entire frame, payload and TPDU included)
    ]


class TCOTP_DT(Structure):
    _fields_ = [
        ("HLength", u_char),  # Header length : 3 for this header
        ("PDUType", u_char),  # 0xF0 for this header
        ("EoT_Num", u_char),  # EOT (bit 7) + PDU Number (bits 0..6)
        # EOT = 1 -> End of Trasmission Packet (This packet is complete)
        # PDU Number : Always 0
    ]


class TIsoDataPDU(Structure):
    _fields_ = [
        ("TPKT", TTPKT),  # TPKT Header
        ("COTP", TCOTP_DT),  # COPT Header for DATA EXCHANGE
    ]


class TIsoTcpSocket(TMsgSocket):
    def __init__(self):
        super().__init__()
        self.FControlPDU = None
        self.IsoMaxFragments = MaxIsoFragments
        self.PDU = TIsoDataPDU()
        self.LastIsoError = 0
        self.SrcTSap = 0
        self.DstTSap = 0
        self.SrcRef = 0
        self.DstRef = 0
        self.IsoPDUSize = 0

        self.recv_timeout = 3000  # Some old equipments are a bit slow to answer....
        self.remote_port = iso_tcp_port
        # These fields should be $0000 and in any case RFC says that they are not considered.
        # But some equipment...need a non zero value for the source reference.
        self.dst_ref = 0x0000
        self.src_ref = 0x0100
        # PDU size requested
        self.iso_pdu_size = 1024
        self.iso_max_fragments = MaxIsoFragments
        self.last_iso_error = 0

    def CheckPDU(self, pPDU, PduTypeExpected):
        pass

    def isoRecvFragment(self, From, Max, Size, EoT):
        pass

    def SetIsoError(self, Error):
        pass

    def BuildControlPDU(self):
        pass

    def PDUSize(self, pPDU):
        pass

    def IsoParsePDU(self, PDU):
        pass

    def IsoConfirmConnection(self, PDUType):
        pass

    def ClrIsoError(self):
        pass

    def FragmentSkipped(self, Size):
        pass

    def isoConnect(self):
        pass

    def isoDisconnect(self, OnlyTCP):
        if self.Connected:
            self.Purge()  # Flush pending
        self.last_iso_error = 0
        # OnlyTCP true -> Disconnect Request telegram is not required : only TCP disconnection
        if not OnlyTCP:
            # if we are connected -> we have a valid connection telegram
            if self.Connected:
                self.FControlPDU.COTP.PDUType = self.pdu_type_DR
            # Checks the format
            Result = self.CheckPDU(self.FControlPDU, self.pdu_type_DR)
            if Result != 0:
                return Result
            # Sends Disconnect request
            self.SendPacket(self.FControlPDU, self.PDUSize(self.FControlPDU))
            if self.LastTcpError != 0:
                Result = self.SetIsoError(self.errIsoSendPacket)
                return Result
        # TCP disconnect
        self.SckDisconnect()
        if self.LastTcpError != 0:
            Result = self.SetIsoError(self.errIsoDisconnect)
        else:
            Result = 0

        return Result

    def isoSendBuffer(self, Data, Size):
        pass

    def isoRecvBuffer(self, Data, Size):
        pass

    def isoExchangeBuffer(self, Data, Size):
        pass

    def IsoPDUReady(self):
        pass

    def isoSendPDU(self, Data):
        pass

    def isoRecvPDU(self, Data):
        pass

    def isoExchangePDU(self, Data):
        pass

    def IsoPeek(self, pPDU, PduKind):
        pass
