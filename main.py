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
		self.apublkey = None
		self.serialthread = threading.Thread(target=self.run_serial, daemon=True)
		self.adthread = threading.Thread(target=self.admin, daemon=True)
		self.adthread.start()
		self.database.tick()
		self.shutdown()

	def admin(self):
		while True:
			inp = input("$> ")
			#inp = "insert 1234 2000 mboom 01-10-2005 69 420 0 123"
			#inp = "select 1234"
			if inp.lower() == "exit" or inp == "":
				self.database.running = False
				return

			split = inp.split()
			match split[0].upper():
				case "INSERT":
					match split[1].lower():
						case "campuscard":
							self.database.queue.append((self.database.insert_campuscard, split[2:]))
						case "readers":
							self.database.queue.append((self.database.insert_readers, split[2:]))
						case "clearances":
							self.database.queue.append((self.database.insert_clearances, split[2:]))
				case "SELECT":
					self.database.queue.append((self.database.select, split[1:]))


	def run_serial(self):
		with serial.Serial(sys.argv[0] if ["COM3", "COM4", "COM5"] in sys.argv else "COM5", 9600) as ser:
			def init():
				# initialize encrypted connection with Arduino
				# ser.write(self.database.publkey.e) # shouldn't be needed as e is always 65537
				ser.write(self.database.publkey.n)

				# TODO: See how many bytes actually need to be read
				# e = ser.read(512)
				n = ser.read(512)
				self.apublkey = rsa.PublicKey(n, 65537)

			def send_data(data: str):
				ser.write(rsa.encrypt(data.encode('utf-8'), self.apublkey))

			def check_clearance(rid):
				if self.database.has_sufficient_clearance(uid, rid):
					return '0'
				return '3'

			# initialize the (serial) connection
			init()

			# get uid
			while self.database.running:
				full_uid = ser.read(4)
				# reader_id = ser.read(4)
				# reader_id = randint(0, 0xffffffff)  # generate random reader id
				reader_id = randint(0, 2)  # generate random reader id
				uid = 0x00ffffff & full_uid  		# bit mask the actual uid
				counter = 0xff000000 & full_uid  	# bit mask the counter value
				print(f"{uid=}")

				# Check if card is valid
				if not (a := self.database.check_counter_val(uid, counter)) or (blocked := self.database.check_blocked(uid)):
					if a:
						print(f"Found copied card. {uid=}\t{counter=}")
						self.database.mark_blocked(uid)
						send_data('5')
					if blocked:
						print(f"Card is blocked. {uid=}\t{counter=}")
						ser.write('4')
					continue

				# self.database.get_bal_from_uid(uid)

				action_type = self.database.get_action_type_from_reader(reader_id)
				# 0 == success
				# 1 == failure
				# 2 == insufficient balance
				# 3 == insufficient clearance
				# 4 == blocked card
				# 5 == copied card
				# 6 == failed to create transaction
				auth_code = '0'

				match action_type:  # match case for faster support for more type
					case 0:  # payment
						amount = randint(0, 100_000) / 100
						if self.database.get_bal_from_uid(uid) > amount:
							# Create transaction
							t = self.database.create_transaction(uid, reader_id, -amount)
							if t is None:
								auth_code = '6'
							# Send auth code
							send_data(auth_code)
							if auth_code != '0':  # continue if we didn't create the transaction
								continue
							pid, timestamp = t

							# TODO: Check if reader agrees?

							# Queue transaction payment
							self.database.queue_transaction_payment(pid, timestamp, reader_id)
						else:
							auth_code = '2'
					case 1:  # door authorization
						auth_code = check_clearance(reader_id)
					case 2:  # top up balance
						amount = randint(0, 100_000) / 100
						if self.database.get_bal_from_uid(uid) > amount:
							# Create transaction
							t = self.database.create_transaction(uid, reader_id, amount)
							if t is None:
								auth_code = '6'
							# Send auth code
							send_data(auth_code)
							if auth_code != '0':  # continue if we didn't create the transaction
								continue
							pid, timestamp = t

							# TODO: Check if reader agrees?

							# Queue transaction payment
							self.database.queue_transaction_payment(pid, timestamp, reader_id)
						else:
							auth_code = '2'
				send_data(auth_code)

	def shutdown(self):
		del self.database


if __name__ == '__main__':
	main = Main()

