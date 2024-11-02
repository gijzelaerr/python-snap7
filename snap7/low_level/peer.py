from .iso_tcp_socket import IsoTcpSocket
from .type import PS7ReqHeader


class TSnap7Peer(IsoTcpSocket):
    def __init__(self):
        super().__init__()
        self.PDUH_out: PS7ReqHeader = PS7ReqHeader(self.PDU.Payload)
        self.PDURequest: int = 480  # Our request, FPDULength will contain the CPU answer
        self.last_error = 0
        self.cntword = 0
        self.destroying = False

    def __del__(self):
        self.destroying = True

    def set_error(self, error: int):
        if error == 0:
            self.clear_error()
        else:
            self.last_error = error | self.last_iso_error | self.last_tcp_error
        return error

    def clear_error(self):
        self.last_error = 0
        self.last_iso_error = 0
        self.last_tcp_error = 0

    def GetNextWord(self):
        if self.cntword == 0xFFFF:
            self.cntword = 0
        self.cntword += 1
        return self.cntword

    def peer_disconnect(self):
        self.clear_error()
        self.iso_disconnect(True)

    def peer_connect(self):
        self.clear_error()
        Result = self.iso_connect()
        if Result == 0:
            Result = self.negotiate_pdu_length()
            if Result != 0:
                self.peer_disconnect()
        return Result

    def negotiate_pdu_length(self):
        """
        Result, IsoSize = 0
        PReqFunNegotiateParams ReqNegotiate
        PResFunNegotiateParams ResNegotiate
        PS7ResHeader23 Answer
        self.clear_error()
        # Setup Pointers
        ReqNegotiate = PReqFunNegotiateParams(pbyte(PDUH_out) + sizeof(TS7ReqHeader))
        // Header
        PDUH_out->P        = 0x32;            // Always $32
        PDUH_out->PDUType  = PduType_request; // $01
        PDUH_out->AB_EX    = 0x0000;          // Always $0000
        PDUH_out->Sequence = GetNextWord();   // AutoInc
        PDUH_out->ParLen   = SwapWord(sizeof(TReqFunNegotiateParams)); // 8 bytes
        PDUH_out->DataLen  = 0x0000;
        // Params
        ReqNegotiate->FunNegotiate = pduNegotiate;
        ReqNegotiate->Unknown = 0x00;
        ReqNegotiate->ParallelJobs_1 = 0x0100;
        ReqNegotiate->ParallelJobs_2 = 0x0100;
        ReqNegotiate->PDULength = SwapWord(PDURequest);
        IsoSize = sizeof( TS7ReqHeader ) + sizeof( TReqFunNegotiateParams );
        Result = isoExchangeBuffer(NULL, IsoSize);
        if ((Result == 0) && (IsoSize == int(sizeof(TS7ResHeader23) + sizeof(TResFunNegotiateParams)))):
            #  Setup pointers
            Answer = PS7ResHeader23(&PDU.Payload);
            ResNegotiate = PResFunNegotiateParams(pbyte(Answer) + sizeof(TS7ResHeader23));
            if ( Answer->Error != 0 ):
                Result = SetError(errNegotiatingPDU);
            if ( Result == 0 ):
                PDULength = SwapWord(ResNegotiate->PDULength);

        return Result
        """
        ...
