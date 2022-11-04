import sys
import os
from random import randint  # for simulating different actions
import serial  # pip install pyserial
import rsa
from getch import getch
from database import Database


class Main:
	def __init__(self):
		self.database = Database()
		self.publkey, self.privkey = rsa.newkeys(32)  # use 32 bits cuz of arduino, would rather use 512 bits
		self.apublkey = None

	def admin(self):
		while True:
			inp = input("$> ")
			# inp = "insert campuscards 1234 2000 mboom 01-10-2005 69 420 0 123"
			# inp = "select 1234"
			if inp.lower() == "exit" or inp == "":
				self.database.running = False
				return

			split = inp.split()
			match split[0].upper():
				case "INSERT":
					match split[1].lower():
						case "campuscards":
							self.database.queue.append((self.database.insert_campuscard, split[2:]))
						case "readers":
							self.database.queue.append((self.database.insert_readers, split[2:]))
						case "clearances":
							self.database.queue.append((self.database.insert_clearances, split[2:]))
				case "SELECT":
					self.database.queue.append((self.database.select_campuscard, split[1:]))
			self.database.tick_testing()

	def run_serial(self):
		ser = serial.Serial(sys.argv[0] if ["COM3", "COM4", "COM5"] in sys.argv else "COM5", 9600)

		def init():
			# initialize encrypted connection with Arduino
			code = ser.read(1)
			if code != b'0':
				self.database.running = False
				return
			print(f"{code=}")

			p = bytearray()
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

		def send_data(data: str):
			ser.write(data.encode('utf-8'))
			# ser.write(rsa.encrypt(data.encode('utf-8'), self.apublkey))

		def read_data(byte):
			# Would love to be able to read 32 bits instead of 32 bytes, but PySerial had other plans
			# It has to do with null bytes (0x00) forcing the read loop to exit
			# data = ser.read(byte)
			data = ser.read_until()
			return data[:-2]  # ignore the "\r\n"
			# We don't decrypt since the arduino isn't powerful to encrypt using a 32-bit RSA key (笑)
			# return rsa.decrypt(data, self.privkey)

		def check_clearance(rid):
			if self.database.has_sufficient_clearance(uid, rid):
				return '0'
			return '3'

		# initialize the (serial) connection
		init()

		# get uid
		while self.database.running:
			full_uid = int(read_data(32), 2)
			# reader_id = ser.read(4)					# get reader id from reader
			reader_id = randint(0, 2)  					# generate random reader id
			uid = 0x00ffffff & full_uid  				# bit mask the actual uid
			counter = (0xff000000 & full_uid) >> 24  	# bit mask the counter value
			print(f"{uid=}")

			# Check if card is valid
			blocked = False  # blocked might not be initialized if (not a) returns False
			if not (a := self.database.check_counter_val(uid, counter)) or (blocked := self.database.check_blocked(uid)):
				if not a:
					print(f"Found copied card. {uid=:024b}\t{counter=:008b}")
					self.database.mark_blocked(uid)
					send_data('5')
				if blocked:
					print(f"Card is blocked. {uid=}\t{counter=}")
					send_data('4')
				continue

			action_type = self.database.get_action_type_from_reader(reader_id)
			print(f"{reader_id=}\t{action_type=}")
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
		ser.close()

	def shutdown(self):
		del self.database


if __name__ == '__main__':
	main = Main()
	os.system("")
	print("Select:\n\t1.Admin Console (for database management)\n\t2.Serial connection (Arduino)")
	while True:
		inp = ord(getch())
		match inp:
			case 0x31:
				sys.stdout.write("\r\033[2K")
				sys.stdout.flush()
				main.admin()
			case 0x32:
				sys.stdout.write("\033[J")
				sys.stdout.flush()
				main.run_serial()
			case _:
				continue
		os.system('cls' if os.name == "nt" else "clear")
		print("\033[2JSelect:\n\t1.Admin Console (for database management)\n\t2.Serial connection (Arduino)")
	main.shutdown()
