import sys
from random import randint  # for simulating different actions
import serial  # pip install pyserial
import rsa
import threading
from database import Database


class Main:
	def __init__(self):
		self.database = Database()
		self.publkey, self.privkey = rsa.newkeys(512)
		# For testing
		#self.database.insert()
		#self.database.get_bal_from_uid(1234)
		self.apublkey = None
		self.serialthread = threading.Thread(target=self.run_serial, daemon=True)
		# self.dbthread = threading.Thread(target=self.database.tick, daemon=True)
		# self.dbthread.start()
		# self.serialthread.start()
		self.adthread = threading.Thread(target=self.admin, daemon=True)
		self.adthread.start()
		self.database.tick()
		self.shutdown()

	def admin(self):
		while True:
			inp = input("$> ")
			if inp.lower() == "exit" or inp == "":
				self.database.running = False
				return

			split = inp.split()
			match split[0].upper():
				case "INSERT":
					self.database.queue.append((self.database.insert, split[1:]))
				case "SELECT":
					self.database.queue.append((self.database.select, split[1:]))

	def run_serial(self):
		with serial.Serial(sys.argv[0] if ["COM3", "COM4", "COM5"] in sys.argv else "COM5", 9600) as ser:
			def init():

				# initialize encrypted connection with Arduino
				ser.write(self.database.publkey.e)
				ser.write(self.database.publkey.n)

				# TODO: See how many bytes actually need to be read
				e = ser.read(512)
				n = ser.read(512)
				self.apublkey = rsa.PublicKey(n, e)

			def send_data(data):
				ser.write(rsa.encrypt(data, self.apublkey))

			def read_data(byte):
				return ser.read(byte)

			init()

			# get uid
			uid = ser.read(4)
			print(f"{uid=}")
			self.database.get_bal_from_uid(uid)

			auth_code = 0  # 0 == success, 1 == failure, 2 == insufficient balance
			match randint(0, 11):
				case 0:  # buy coffee
					if self.database.get_bal_from_uid(uid) > 0.20:
						auth_code = 0
						self.database.update_bal_from_uid(uid)
					else:
						auth_code = 2

				case 1:
					pass
				case 2:
					pass
			auth_code = str(auth_code).encode('utf-8')
			send_data(auth_code)

	def shutdown(self):
		del self.database


if __name__ == '__main__':
	main = Main()

