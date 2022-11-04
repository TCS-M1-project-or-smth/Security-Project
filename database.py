import sqlite3
import os
import rsa  # pip install rsa
from datetime import datetime


class Database:
	def __init__(self):
		self.__connection = sqlite3.connect("system.db")
		self.__connection.execute("PRAGMA foreign_keys = 1")
		self.queue: list[tuple[callable, list]] = []  # (method, *args)
		self.result = None
		self.running = True
		self.cursor = self.__connection.cursor()

		# Create tables
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS clearances(
					clearance_id INT PRIMARY KEY,
					description TEXT, -- usually department like Physics or Security or TCS M1 Coordinator
					category INT -- 4 bytes of flag, make sure to remove sign the int when checking flags
				)""")
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS campuscards(
					uid TEXT PRIMARY KEY,
					bal FLOAT,
					full_name TEXT,
					date_of_birth DATE,
					person_id TEXT,
					clearance_id INTEGER,
					blocked INTEGER DEFAULT 0, -- 0 is false, 1 is true
					counterval INTEGER,
					FOREIGN KEY (clearance_id) REFERENCES clearances(clearance_id)
				)""")
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS readers(
			reader_id INT PRIMARY KEY,
			clearance_id INTEGER,
			action_type INTEGER, -- 0 is payment, 1 is door authorization, 2 is top up balance
			FOREIGN KEY (clearance_id) REFERENCES clearances(clearance_id)
		)""")
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS transactions(
			person_id TEXT,
			time_stamp DATE,
			reader_id INTEGER,
			amount FLOAT, -- positive amount means reader to person, negative is person to reader
			status INTEGER DEFAULT 0, -- 0 is being processed, 1 is approved, 2 is declined
			PRIMARY KEY (person_id, reader_id, time_stamp),
			FOREIGN KEY (person_id) REFERENCES campuscards(person_id),
			FOREIGN KEY (reader_id) REFERENCES readers(reader_id)
		)""")
		self.__connection.commit()

		# self.publkey, self.privkey = rsa.newkeys(512)
		# with open("public.pem", "wb") as f:
		# 	f.write(self.publkey.save_pkcs1(format='PEM'))
		# with open("private.pem", "wb") as f:
		# 	f.write(self.privkey.save_pkcs1(format='PEM'))

		with open("public.pem", "rb") as f:
			data = f.read()
		self.publkey = rsa.PublicKey.load_pkcs1(data)
		#os.remove("public.pem")
		with open("private.pem", "rb") as f:
			data = f.read()
		self.privkey = rsa.PrivateKey.load_pkcs1(data)
		#os.remove("private.pem")

	def __del__(self):
		print("Shutting down database (writing public and private key to local files)")
		with open("public.pem", "wb") as f:
			f.write(self.publkey.save_pkcs1(format='PEM'))
		with open("private.pem", "wb") as f:
			f.write(self.privkey.save_pkcs1(format='PEM'))
		self.__connection.close()

	def tick(self):
		while self.running or len(self.queue) > 0:
			if len(self.queue) > 0:
				try:
					self.queue[0][0](*self.queue[0][1])
					self.result = self.cursor.fetchone()
				except sqlite3.Error as e:
					print(e)
				self.queue.pop(0)

	def cuid(self, uid):
		return rsa.sign(str(uid).encode("utf-8"), self.privkey, 'SHA-256')

	def encrypt(self, msg: str):
		return rsa.encrypt(msg.encode('utf-8'), self.publkey)

	def check_blocked(self, uid):
		self.queue.append((self.cursor.execute, ["SELECT blocked FROM campuscards WHERE uid=?", [self.cuid(uid)]]))
		fetch = self.result
		return fetch is not None and fetch[0]

	def check_counter_val(self, uid, counter):
		self.queue.append((self.cursor.execute, ["SELECT counter FROM campuscards WHERE uid=?", [self.cuid(uid)]]))
		fetch = self.result
		return fetch is not None and fetch[0] == counter

	def mark_blocked(self, uid):
		self.cursor.execute("UPDATE TABLE campuscards SET blocked = 1 WHERE uid=?", [self.cuid(uid)])

	def get_action_type_from_reader(self, rid):
		self.cursor.execute("SELECT action_type FROM readers WHERE reader_id=?", [rid])

	def get_bal_from_uid(self, uid):
		self.cursor.execute("SELECT bal FROM campuscards WHERE uid=?", [self.cuid(uid)])
		fetch = self.result
		return fetch[0] if fetch is not None else 0

	def insert_campuscard(self, *args):  # args: [uid, bal, full_name, dob, person_id, clearance_id, blocked, counterval]
		if len(args) != 8:
			print(f"INSERT campuscard expected 8 arguments, got {len(args)}")
			return

		try:
			self.cursor.execute("INSERT INTO campuscards VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
								[self.cuid(args[0]), int(args[1]), self.encrypt(args[2]),
								 datetime.strptime(args[3], "%d-%m-%Y"), self.encrypt(args[4]), int(args[5]),
								 args[6], int(args[7])])
			self.__connection.commit()
		except ValueError:
			print("Failed to convert to int")
		except sqlite3.Error as e:
			print("Failed to insert:")
			print(e)

	def insert_readers(self, *args):  # args: [rid, clearance_id, action_type]
		if len(args) != 3:
			print(f"INSERT readers expected 3 arguments, got {len(args)}")
			return

		try:
			self.cursor.execute("INSERT INTO readers VALUES (?, ?, ?)", args)
			self.__connection.commit()
		except sqlite3.Error as e:
			print("Failed to insert:")
			print(e)

	def insert_clearances(self, *args):  # args: [clearance_id, description, category]
		if len(args) != 3:
			print(f"INSERT clearances expected 3 arguments, got {len(args)}")
			return

		try:
			self.cursor.execute("INSERT INTO clearances VALUES (?, ?, ?)", args)
			self.__connection.commit()
		except sqlite3.Error as e:
			print("Failed to insert:")
			print(e)

	def select_campuscard(self, *args):
		cuid = rsa.sign(args[0].encode("utf-8"), self.privkey, 'SHA-256')
		self.cursor.execute("SELECT * FROM campuscards WHERE uid=?", [cuid])
		fetch = self.cursor.fetchone()
		print(args[0], fetch[1], rsa.decrypt(fetch[2], self.privkey),
				rsa.decrypt(fetch[3], self.privkey), fetch[4], fetch[5])

	def has_sufficient_clearance(self, uid, rid):
		self.queue.append((self.cursor.execute, ["SELECT clearance_id FROM campuscards WHERE uid=?", [self.cuid(uid)]]))
		fetch1 = self.cursor.fetchone()
		self.queue.append((self.cursor.execute, ["SELECT clearance_id FROM readers WHERE reader_id=?", [rid]]))
		fetch2 = self.cursor.fetchone()
		return fetch1 is not None and fetch2 is not None and fetch1[0] == fetch2[0]

	def complete_transaction(self, pid, timestamp, rid):
		self.cursor.execute("SELECT amount FROM transactions WHERE pid=? and time_stamp=? and reader_id=?", [pid, timestamp, rid])
		fetch = self.cursor.fetchone()
		if fetch is None:
			self.cursor.execute("UPDATE transactions SET status=2 WHERE pid=? and time_stamp=? and reader_id=?", [pid, timestamp, rid])
			self.__connection.commit()
			return
		self.cursor.execute("UPDATE campuscards SET bal=bal+?", fetch)
		self.cursor.execute("UPDATE transactions SET status=1 WHERE pid=? and time_stamp=? and reader_id=?", [pid, timestamp, rid])
		self.__connection.commit()

	def create_transaction(self, uid, rid, amount):
		self.cursor.execute("SELECT person_id FROM campuscards WHERE uid=?", [self.cuid(uid)])
		fetch = self.cursor.fetchone()
		if fetch is None:
			return None
		pid = fetch[0]  # pid is encrypted
		timestamp = datetime.now()
		try:
			self.cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?)", [pid, timestamp, rid, amount])
			self.__connection.commit()
		except sqlite3.Error as e:
			print(f"Failed to create transaction:")
			print(e)
			return None
		return pid, timestamp

	def queue_transaction_payment(self, pid, timestamp, rid):  # OOP moment
		self.queue.append((self.complete_transaction, [pid, timestamp, rid]))

