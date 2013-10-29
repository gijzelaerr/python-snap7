import re

asci = re.compile('[a-zA-Z0-9 ]')
import snap7

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
    print_row(data[:60])
    return data


def show_row(x):

    row_size = 126

    while True:
        get_db_row(1, 4 + x * row_size, row_size)
        break
        # do some write action..

        # do some check action..

#show_row(0)
#show_row(1)
show_row(2)

client.disconnect()
