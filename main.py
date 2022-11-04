import sys
from random import randint  # for simulating different actions
import serial  # pip install pyserial
import rsa
import threading
from database import Database


class Main:
	def __init__(self):
		self.database = Database()
		self.publkey, self.privkey = rsa.newkeys(32)  # use 32 bits cuz of arduino, would rather use 512 bits
		self.apublkey = None
		self.serialthread = threading.Thread(target=self.run_serial, daemon=True)
		self.adthread = threading.Thread(target=self.admin, daemon=True)
		self.adthread.start()
		self.serialthread.start()
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
					self.database.queue.append((self.database.select_campuscard, split[1:]))

	def run_serial(self):
		with serial.Serial(sys.argv[0] if ["COM3", "COM4", "COM5"] in sys.argv else "COM5", 9600) as ser:
			def init():
				# initialize encrypted connection with Arduino
				code = ser.read(1)
				if code != b'0':
					self.database.running = False
					return
				print(f"{code=}")

				p = bytearray()
				self.publkey.n = 0xff_ff_ff_ff
				for j in range(4):  # little endian
					p.append((self.publkey.n & (0xff << 8 * j)) >> 8 * j)
				ser.write(p)

				# Usually we would read the Arduino's public key, but the Arduino does not have
				# enough computational power to quickly generate new key pairs so for demonstration
				# purposes we will send the RSA private key to the Arduino, which of course defeats
				# the purpose of RSA encryption
				# n = ser.read(512)
				# self.apublkey = rsa.PublicKey(n, 65537)
				self.apublkey, priv = rsa.newkeys(32)  # use 64 bits because of arduino
				p = bytearray()
				for j in range(4):  # little endian
					p.append((priv.d & (0xff << 8 * j)) >> 8 * j)
				ser.write(p)

				p = bytearray()
				for j in range(4):  # little endian
					p.append((priv.n & (0xff << 8 * j)) >> 8 * j)
				ser.write(p)

				status = ser.read(1)
				print(f"{status=}")

				privd = ser.read_until()
				privn = ser.read_until()
				pyn = ser.read_until()
				print(privd, privn, pyn)
				print(priv.d, priv.n, self.publkey.n)

			def send_data(data: str):
				ser.write(rsa.encrypt(data.encode('utf-8'), self.apublkey))

			def read_data(byte):
				#data = ser.read(byte)
				data = ser.read_until()
				print(data)
				return data[:-2]
				# return rsa.decrypt(data, self.privkey)

			def check_clearance(rid):
				if self.database.has_sufficient_clearance(uid, rid):
					return '0'
				return '3'

			# initialize the (serial) connection
			init()

			# get uid
			while self.database.running:
				print('yes')
				full_uid = int(read_data(32), 2)
				print(full_uid)
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
						send_data('4')
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
							continue
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
				if auth_code == '0':
					counter += 1
					tuid = (counter << 24) | uid
					# send_data_bytes(tuid)
					packet = bytearray()
					for i in range(4):
						packet.append((tuid & (0xff << 8 * i)) >> 8 * i)
					ser.write(packet)

	def shutdown(self):
		del self.database


if __name__ == '__main__':
	main = Main()

