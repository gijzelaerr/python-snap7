import logging

from snap7.logo import Logo

# for setup the Logo connection please follow this link
# https://snap7.sourceforge.net/logo.html


logging.basicConfig(level=logging.INFO)

# Siemens LOGO devices Logo 8 is the default
Logo_7 = True

logger = logging.getLogger(__name__)

plc = Logo()
plc.connect("192.168.0.41", 0x1000, 0x2000)

if plc.get_connected():
    logger.info("connected")

    # read I1 from logo
    vm_address = "V923.0" if Logo_7 else "V1024.0"
    print(f"I1: {str(plc.read(vm_address))}")

    # write some values in VM addresses between 0 and 100

    value_1 = 0b10110001
    value_2 = 480

    print("write 0b10110001 to V10")
    plc.write("V10", value_1)

    print(f"read V10.0 must be 1 - check: {str(plc.read('V10.0'))}")
    print(f"read V10.3 must be 0 - check: {str(plc.read('V10.3'))}")
    print(f"read V10.7 must be 1 - check: {str(plc.read('V10.7'))}")

    print("write 480 analog value to VW20")
    plc.write("VW20", value_2)

    print(f"read VW20 must be 480 - check: {str(plc.read('VW20'))}")

    print("trigger V10.2")
    plc.write("V10.2", 0)
    plc.write("V10.2", 1)
    plc.write("V10.2", 0)

else:
    logger.error("Conncetion failed")

plc.disconnect()
logger.info("Disconnected")
plc.destroy()
