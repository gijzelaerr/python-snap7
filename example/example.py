import time
import snap7
from snap7 import util
from db_layouts import rc_if_db_1_layout
from db_layouts import tank_rc_if_db_layout

print("""

THIS IS EXAMPLE CODE MEANTH TO BE READ.

It is used to manipulate a large DB object with over
450 'rows' which represent valves

You don't have a project and PLC like I have which I used
to create the test code with.

""")

client = snap7.client.Client()
client.connect('192.168.200.24', 0, 3)


def get_db1():
    """
    Here we read out DB1, all data we is put in the all_data
    variable and is a bytearray with the raw plc data
    """
    all_data = client.db_get(1)

    for i in range(400):                 # items in db
        row_size = 130                   # size of item
        index = i * row_size
        offset = index + row_size        # end of row in db
        util.print_row(all_data[index:offset])


def get_db_row(db, start, size):
    """
    Here you see and example of readying out a part of a DB

    Args:
        db (int): The db to use
        start (int): The index of where to start in db data
        size (int): The size of the db data to read
    """
    type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
    data = client.db_read(db, start, type_, size)
    # print_row(data[:60])
    return data


def set_db_row(db, start, size, _bytearray):
    """
    Here we replace a piece of data in a db block with new data

    Args:
       db (int): The db to use
       start(int): The start within the db
       size(int): The size of the data in bytes
       _butearray (enumerable): The data to put in the db
    """
    client.db_write(db, start, size, _bytearray)


def show_row(x):
    """
    print data in DB of row/object X in
    """

    row_size = 126

    while True:
        data = get_db_row(1, 4 + x * row_size, row_size)
        row = snap7.util.DB_Row(data, rc_if_db_1_layout,
                                layout_offset=4)
        print('name', row['RC_IF_NAME'])
        print(row['RC_IF_NAME'])
        break
        # do some write action..

        # do some check action..


def get_row(x):
    row_size = 126
    data = get_db_row(1, 4 + x * row_size, row_size)
    row = snap7.util.DB_Row(
        data, rc_if_db_1_layout,
        layout_offset=4)
    return row


def set_row(x, row):
    """
    We use db 1, use offset 4, we replace row x. To find the correct
    start_index we mulitpy by row_size by x and we put the
    byte array representation of row in the PLC
    """
    row_size = 126
    set_db_row(1, 4 + x * row_size, row_size, row._bytearray)


def open_row(row):
    """
    open a valve
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
    close a valve
    """
    # print row['RC_IF_NAME']
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
    db1 = make_item_db(1)
    all_data = db1._bytearray
    print(f'row objects: {len(db1.index)}')

    for x, (name, row) in enumerate(db1.index.items()):
        open_row(row)
        #set_part_db(4+x*126, 126, all_data)

    t = time.time()
    write_data_db(1, all_data, 4 + 126 * 450)
    print(f'opening all valves took: {time.time() - t}')

    print('sleep...')
    time.sleep(5)
    for x, (name, row) in enumerate(db1):
        close_row(row)
        #set_part_db(4+x*126, 126, all_data)

    print(time.time() - t)

    t = time.time()
    write_data_db(1, all_data, 4 + 126 * 450)
    print(f'closing all valves took: {time.time() - t}')


def read_tank_db():
    db73 = make_tank_db()
    print(len(db73))
    for x, (name, row) in enumerate(db73):
        print(row)


def make_item_db(db_number):
    t = time.time()
    all_data = client.db_upload(db_number)

    print(f'getting all data took: {time.time() - t}')

    db1 = snap7.util.DB(
        db_number,              # the db we use
        all_data,               # bytearray from the plc
        rc_if_db_1_layout,      # layout specification
        126,                    # size of the specification
        450,                    # number of row's / specifocations
        id_field='RC_IF_NAME',  # field we can use to make row
        layout_offset=4,        # sometimes specification does not start a 0
        db_offset=4             # At which point in all_data should we start
                                # parsing for data
    )

    return db1


def make_tank_db():
    tank_data = client.db_upload(73)
    db73 = snap7.util.DB(
        73, tank_data, tank_rc_if_db_layout,
        238, 2, id_field='RC_IF_NAME')
    return db73


def print_tag():
    db1 = make_item_db(1)
    print(db1['5V315'])


def print_open():
    db1 = make_item_db(1)
    for x, (name, row) in enumerate(db1):
        if row['BatchName']:
            print(row)


#read_tank_db()
#open_and_close()
#open_and_close_db1()
#time.sleep(1)
#show_row(2)
print_tag()
#print_open()

client.disconnect()
