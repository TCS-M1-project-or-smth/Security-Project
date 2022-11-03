import sqlite3
import os
import rsa  # pip install rsa


class Database:
	def __init__(self):
		self.__connection = sqlite3.connect("system.db")
		self.queue: list[tuple[callable, list]] = []  # (method, *args)
		self.running = True
		self.cursor = self.__connection.cursor()
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS campuscard(
			uid BLOB PRIMARY KEY,
			bal SMALLINT,
			full_name TEXT,
			person_id TEXT,
			clearance int,
			counterval tinyint
		)""")

		self.publkey, self.privkey = rsa.newkeys(512)
		with open("public.pem", "wb") as f:
			f.write(self.publkey.save_pkcs1(format='PEM'))
		with open("private.pem", "wb") as f:
			f.write(self.privkey.save_pkcs1(format='PEM'))

		with open("public.pem", "rb") as f:
			data = f.read()
		self.publkey = rsa.PublicKey.load_pkcs1(data)
		os.remove("public.pem")
		with open("private.pem", "rb") as f:
			data = f.read()
		self.privkey = rsa.PrivateKey.load_pkcs1(data)
		os.remove("private.pem")

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
				self.queue[0][0](*self.queue[0][1])
				self.queue.pop(0)

	def get_bal_from_uid(self, uid):
		cuid = rsa.sign(str(uid).encode("utf-8"), self.privkey, 'SHA-256')
		self.cursor.execute("SELECT bal, full_name FROM campuscard WHERE uid=?", [cuid])
		fetch = self.cursor.fetchone()
		print(fetch[0], rsa.decrypt(fetch[1], self.privkey))

	def insert(self, *args):  # args: [uid, bal, full_name, person_id, clearance, counterval]
		if len(args) != 6:
			return
		cuid = rsa.sign(args[0].encode("utf-8"), self.privkey, 'SHA-256')
		cname = rsa.encrypt(args[3].encode('utf-8'), self.publkey)
		cpid = rsa.encrypt(str(args[3]).encode("utf-8"), self.publkey)
		try:
			self.cursor.execute("INSERT INTO campuscard VALUES (?, ?, ?, ?, ?, ?)",
							[cuid, int(args[1]), cname, cpid, int(args[4]), int(args[5])])
			print(self.get_bal_from_uid(args[0]))
		except ValueError:
			print("Failed to convert to int")

	def select(self, *args):  # TODO: temporary maybe
		cuid = rsa.sign(args[0].encode("utf-8"), self.privkey, 'SHA-256')
		self.cursor.execute("SELECT * FROM campuscard WHERE uid=?", [cuid])
		fetch = self.cursor.fetchone()
		print(args[0], fetch[1], rsa.decrypt(fetch[2], self.privkey),
				rsa.decrypt(fetch[3], self.privkey), fetch[4], fetch[5])

	def update_bal_from_uid(self, uid, bal):
		cuid = rsa.sign(str(uid).encode("utf-8"), self.privkey, 'SHA-256')
		self.cursor.execute("UPDATE campuscard SET bal = bal + ? WHERE uid = ? ", [bal, cuid])
