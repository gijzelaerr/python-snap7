class S7Consts:
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


class S7Tag:
    def __init__(self, area, db_number, start, elements, word_len):
        self.area = area
        self.db_number = db_number
        self.start = start
        self.elements = elements
        self.word_len = word_len
