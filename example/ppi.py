"""Read and write S7-200 V memory over a serial PPI cable."""

from s7 import PPIClient


def main() -> None:
    with PPIClient("/dev/ttyUSB0", station=2, baudrate=9600) as client:
        print(f"VB0..VB3: {client.v_read(0, 4).hex(' ')}")
        client.v_write(10, b"\x01\x02")


if __name__ == "__main__":
    main()
