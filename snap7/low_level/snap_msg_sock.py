from .snap_base import TSnapBase


class TMsgSocket(TSnapBase):
    def __init__(self):
        super().__init__()
        self.Pinger = None
        self.FSocket = None
        self.LocalSin = None
        self.RemoteSin = None
        self.ClientHandle = 0
        self.LocalBind = 0
        self.LocalAddress = ""
        self.RemoteAddress = ""
        self.LocalPort = 0
        self.RemotePort = 0
        self.WorkInterval = 0
        self.PingTimeout = 750
        self.RecvTimeout = 0
        self.SendTimeout = 0
        self.LastTcpError = 0
        self.Connected = False

    def GetLastSocketError(self):
        pass

    def SockCheck(self, SockResult):
        pass

    def DestroySocket(self):
        pass

    def SetSocketOptions(self):
        pass

    def CanWrite(self, Timeout):
        pass

    def GetLocal(self):
        pass

    def GetRemote(self):
        pass

    def SetSin(self, sin, Address, Port):
        pass

    def GetSin(self, sin, Address, Port):
        pass

    def CreateSocket(self):
        pass

    def GotSocket(self):
        pass

    def WaitingData(self):
        pass

    def WaitForData(self, Size, Timeout):
        pass

    def Purge(self):
        pass

    def CanRead(self, Timeout):
        pass

    def SckConnect(self):
        pass

    def SckDisconnect(self):
        pass

    def ForceClose(self):
        pass

    def SckBind(self):
        pass

    def SckListen(self):
        pass

    def SetSocket(self, s):
        pass

    def SckAccept(self):
        pass

    def Ping(self, Host):
        pass

    def SendPacket(self, Data, Size):
        pass

    def PacketReady(self, Size):
        pass

    def Receive(self, Data, BufSize):
        pass

    def RecvPacket(self, Data, Size):
        pass

    def PeekPacket(self, Data, Size):
        pass

    def Execute(self):
        pass
