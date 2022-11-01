import sys
import serial  # pip install pyserial
from database import Database


class Main:
    def __init__(self):
        self.database = Database()
        self.run_serial()

    def run_serial(self):
        with serial.Serial(sys.argv[0] if ["COM3", "COM4", "COM5"] in sys.argv else "COM5", 9600) as ser:
            uid = ser.read(4)
            print(f"{uid=}")


if __name__ == '__main__':
    main = Main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
