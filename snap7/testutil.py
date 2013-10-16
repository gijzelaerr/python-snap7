import time
import logging
import snap7

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def test_server():
    def event_callback(event):
        logger.info(event)

    server = snap7.server.Server()
    server.set_events_callback(event_callback)
    server.start()
    while True:
        print "server: %s cpu: %s users: %s" % server.get_status()
        time.sleep(1)

if __name__ == '__main__':
    test_server()
