import sys
from random import randint  # for simulating different actions
import serial  # pip install pyserial
from database import Database


class Main:
    def __init__(self):
        self.database = Database()
        self.database.insert_uid()
        self.database.get_bal_from_uid(1234)
        #self.run_serial()

    def run_serial(self):
        with serial.Serial(sys.argv[0] if ["COM3", "COM4", "COM5"] in sys.argv else "COM5", 9600) as ser:
            uid = ser.read(4)
            print(f"{uid=}")
            self.database.get_bal_from_uid(uid)


if __name__ == '__main__':
    main = Main()

