from ctypes import cdll, sizeof, byref, CFUNCTYPE, POINTER, c_int, c_char

from ctypes.util import find_library
lib_location = find_library('snap7')
if not lib_location:
    msg = "cant find snap7 library. If installed, try running ldconfig"
    raise Exception(msg)
clib = cdll.LoadLibrary(lib_location)

# Server Area ID  (use with Register/unregister - Lock/unlock Area)
srvAreaPE = 0
srvAreaPA = 1
srvAreaMK = 2
srvAreaCT = 3
srvAreaTM = 4
srvAreaDB = 5

"""
typedef struct{
    time_t EvtTime; //Timestamp
    int EvtSender; // sender
    longword EvtCode; // event code
    word EvtRetCode; // event result
    word EvtParam1; // param1 (if availabe)
    word EvtParam2; // param2
    word EvtParam3; // param3
    word EvtParam4; // param4
}
"""


class Snap7Server(object):
    def __init__(self, pointer):
        self.pointer = pointer


def create():
    """Create a server.

    :returns: A Snap7Server object

    """
    pointer = clib.Srv_Create()
    return Snap7Server(pointer)


def register_area(server, area_code, index, userdata):
    """Shares a memory area with the server. That memory block will be visible
    by the clients.

    int Srv_RegisterArea(S7Object Server, int AreaCode, word Index,
    void *pUsrData, int Size)

    :returns: integer, 0 if the function was accomplished with no errors.
                       Other values : see the Errors Code List.
    """
    size = sizeof(userdata)
    return clib.Srv_RegisterArea(server.pointer, area_code, index,
                                 byref(userdata), size)


def set_events_callback(server, call_back):
    """Sets the user callback that the Server object has to call when an event
    is created.

    The expected callback is defined as:
    typedef void (S7API *pfn_SrvCallBack) (void * usrPtr, PSrvEvent PEvent,
    int Size);
    """
    def wrap_func(usrptr, pevent, size):
        call_back(pevent)

    wrap = CFUNCTYPE(c_int, c_int, POINTER(c_int), c_int)
    f = wrap(wrap_func)

    return clib.Srv_SetEventsCallback(server.pointer, f)


def start(server):
    return clib.Srv_Start(server.pointer)


def error_text(error):
    """Returns a textual explanation of a given error number
    """
    len_ = 1024
    text_type = c_char * len_
    text = text_type()
    clib.Srv_ErrorText(error, text, len_)
    return text


def stop(server):
    return clib.Srv_Stop(server.pointer)


def destroy(server):
    return clib.Srv_Destroy(server.pointer)
