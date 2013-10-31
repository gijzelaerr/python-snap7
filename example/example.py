import time
import snap7
from snap7 import s7util
from db_layouts import rc_if_db_1_layout
#from db_layouts import tank_rc_if_db_layout

client = snap7.client.Client()
client.connect('192.168.200.24', 0, 3)



def get_db1():
    all_data = client.db_get(1)

    for i in range(400):                 # items in db
        row_size = 130                   # size of item
        index = i * row_size
        offset = index + row_size        # end of row in db
        s7util.print_row(all_data[index:offset])


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
        row = s7util.db.DB_Row(data, rc_if_db_1_layout,
                               layout_offset=4)
        print 'name', row['RC_IF_NAME']
        print row['RC_IF_NAME']
        break
        # do some write action..

        # do some check action..


def get_row(x):
    row_size = 126
    data = get_db_row(1, 4 + x * row_size, row_size)
    row = s7util.db.DB_Row(data, rc_if_db_1_layout,
                           layout_offset=4)
    return row


def set_row(x, row):
    row_size = 126
    set_db_row(1, 4 + x * row_size, row_size, row._bytearray)


def open_row(row):
    """
    """
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
    """
    """
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


def set_part_db(start, size, _bytearray):
    data = _bytearray[start:start+size]
    set_db_row(1, start, size, data)


def write_data_db(dbnumber, all_data, size):
    area = snap7.types.S7AreaDB
    dbnumber = 1
    client.write_area(area, dbnumber, 0, size, all_data)


def open_and_close_db1():
    t = time.time()
    all_data = client.db_upload(1)

    print 'getting all data took: ', time.time() - t
    db1 = s7util.db.DB(all_data, rc_if_db_1_layout,
                       126, 450, id_field='RC_IF_NAME',
                       layout_offset=4,
                       db_offset=4)

    print 'row objects: ', len(db1.index)

    for x, (name, row) in enumerate(db1.index.items()):
        open_row(row)
        #set_part_db(4+x*126, 126, all_data)

    t = time.time()
    write_data_db(1, all_data, 4 + 126 * 450)
    print 'opening all valves took: ', time.time() - t

    print 'sleep...'
    time.sleep(5)
    for x, (name, row) in enumerate(db1.index.items()):
        close_row(row)
        #set_part_db(4+x*126, 126, all_data)

    print time.time() - t

    t = time.time()
    write_data_db(1, all_data, 4 + 126 * 450)
    print 'closing all valves took: ', time.time() - t

#open_and_close()
open_and_close_db1()
#time.sleep(1)
#show_row(2)

client.disconnect()
