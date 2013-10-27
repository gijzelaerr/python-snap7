import re
import time

asci = re.compile('[a-zA-Z0-9 ]')
import snap7

client = snap7.client.Client()

client.connect('192.168.200.24', 0, 3)

# RC_IF layout / Route Control Interface DB block
"""
# Status fields.
NAME          IN     TYPE

EN            IN     BOOL
RC_IF_ID      IN     INT
RC_IF_NAME    IN     STRING[16]
LockAct       IN     BOOL
GrpErr        IN     BOOL
RdyToStart    IN     BOOL
RdyToReset    IN     BOOL
LocalAct      IN     BOOL
AutAct        IN     BOOL
ManAct        IN     BOOL
OoSAct        IN     BOOL
FbkOpenOut    IN     BOOL
FbkCloseOut   IN     BOOL
FbkRunOut     IN     BOOL
PV_Li         IN     STRUCT
PV_Li.Value   IN     REAL
PV_Li.ST      IN     BYTE
PV_LiUnit     IN     INT
ScaleOut      IN     STRUCT
ScaleOut.High IN     REAL
ScaleOut.Low  IN     REAL
PV_Out        IN     STRUCT
PV_Out.Value  IN     BOOL
PV_Out.ST     IN     BYTE
FlutAct       IN     STRUCT
FlutAct.Value IN     BOOL
FlutAct.ST    IN     BYTE
Bad           IN     STRUCT
Bad.Value     IN     BOOL
Bad.ST        IN     BYTE

# Controlfields. DB Fields we can change

ENO           OUT    BOOL
OpenAut       OUT    BOOL
CloseAut      OUT    BOOL
StartAut      OUT    BOOL
StopAut       OUT    BOOL
SP_Ext        OUT    REAL
ModLiOp       OUT    BOOL
AutModLi      OUT    BOOL
ManModLi      OUT    BOOL
RstLi         OUT    BOOL
BoolValue     OUT    BOOL
RealValue     OUT    REAL
IntValue      OUT    INT
StringValue   OUT    STRING[32]
BatchID       OUT    DWORD
BatchName     OUT    STRING[32]
StepNo        OUT    DWORD
Occupied      OUT    BOOL
RC_IF_ERR     OUT    BOOL
"""

# FIXME
row_status_setters = {
    'name': (0, 50),
    'value': (50, 51),
    'reservering': (60, 100),
}

# FIXME..
row_control_setters = {
    #
}


def print_row(data):
    """print a single db row in chr and str
    """
    index_line = ""
    pri_line1 = ""
    chr_line2 = ""

    for i, xi in enumerate(data):
        # index
        if not i % 5:
            diff = len(pri_line1) - len(index_line)
            i = str(i)
            index_line += diff * ' '
            index_line += i
            #i = i + (ws - len(i)) * ' ' + ','

        # byte array line
        str_v = str(xi)
        pri_line1 += str(xi) + ','
        # char line
        c = chr(xi)
        c = c if asci.match(c) else ' '
        # allign white space
        w = len(str_v)
        c = c + (w - 1) * ' ' + ','
        chr_line2 += c

    print index_line
    print pri_line1
    print chr_line2


def get_db1():
    all_data = client.db_get(1)

    for i in range(400):                 # items in db
        row_size = 130                   # size of item
        index = i * row_size
        offset = index + row_size        # end of row in db
        print_row(all_data[index:offset])


def get_db_row(db, start, size):
    type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
    data = client.db_read(db, start, type_, size)
    print_row(data)


def show_row(x):

    row_size = 126

    while True:
        get_db_row(1, 4 + x * row_size, row_size)
        break
        # do some write action..

        # do some check action..

show_row(0)
#show_row(1)
#show_row(2)

client.disconnect()
