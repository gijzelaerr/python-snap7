
import snap7

c = snap7.client.Client()

c.connect('192.168.200.24', 0, 3)


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

all_data = c.db_get(1)

for i in range(400):            # items in db
    row_size = 124              # size of item
    index = i * row_size
    offset = index + row_size    # lenght of row in db
    print all_data[index:offset]


c.disconnect()
