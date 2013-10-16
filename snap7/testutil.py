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
    print snap7.server.event_text(snap7.server.PSrvEvent(EvtRetCode=32652))
    while True:
        print server.get_status()
        time.sleep(1)

if __name__ == '__main__':
    test_server()
