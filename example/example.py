import re
import time
asci = re.compile('[a-zA-Z0-9 ]')
import snap7
from snap7 import s7util
from db_layouts import rc_if_db_1_layout
#from db_layouts import tank_rc_if_db_layout

client = snap7.client.Client()
client.connect('192.168.200.24', 0, 3)


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
        # align white space
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
    # print_row(data[:60])
    return data


def set_db_row(db, start, size, _bytearray):
    client.db_write(db, start, size, _bytearray)


def show_row(x):

    row_size = 126

    while True:
        data = get_db_row(1, 4 + x * row_size, row_size)
        row = s7util.db.DB_Row(data, rc_if_db_1_layout)
        print 'name', row['RC_IF_NAME']
        print row['RC_IF_NAME']
        break
        # do some write action..

        # do some check action..


def get_row(x):
    row_size = 126
    data = get_db_row(1, 4 + x * row_size, row_size)
    row = s7util.db.DB_Row(data, rc_if_db_1_layout)
    return row


def set_row(x, row):
    row_size = 126
    set_db_row(1, 4 + x * row_size, row_size, row._bytearray)


def open_row(row):

    # row['AutAct'] = 1
    row['Occupied'] = 1
    row['BatchName'] = 'test'
    row['AutModLi'] = 1
    row['ManModLi'] = 0
    row['ModLiOp'] = 1

    row['CloseAut'] = 0
    row['OpenAut'] = 1

    # row['StartAut'] = True
    # row['StopAut'] = False
    # row['RstLi'] = True
    # row['StringValue'] = 'test'


def close_row(row):
    #print row['RC_IF_NAME']
    row['BatchName'] = ''
    row['Occupied'] = 0
    row['CloseAut'] = 1
    row['OpenAut'] = 0

#show_row(0)
#show_row(1)


def open_and_close():
    for x in range(450):
        row = get_row(x)
        open_row(row)
        set_row(x, row)

    time.sleep(3)

    for x in range(450):
        row = get_row(x)
        close_row(row)
        set_row(x, row)


def open_and_close_db1():
    all_data, size = client.db_full_upload(1)
    db1 = s7util.db.DB(all_data, rc_if_db_1_layout,
                       126, 450, id_field='RC_IF_NAME')

    #print_row(all_data[0:100])

    client.db_download(1, all_data, size)

    return

    old = bytearray(all_data)
    for name, row in db1.index.items()[:10]:
        open_row(row)
        print name, row['OpenAut']

    print 'opening..'
    client.db_download(1, all_data)

    assert(old != all_data)

    print 'sleep...'
    time.sleep(5)
    print 'closing..'

    for name, row in db1.index.items()[:10]:
        close_row(row)
        print name, row['OpenAut']

    client.db_download(1, db1._bytearray)

open_and_close()
#open_and_close_db1()
#time.sleep(1)
#show_row(2)

client.disconnect()
