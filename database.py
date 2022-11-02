import sqlite3
import os
import rsa  # pip install rsa


class Database:
	def __init__(self):
		self.__connection = sqlite3.connect("system.db")
		self.cursor = self.__connection.cursor()
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS cardholders(
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

	def get_bal_from_uid(self, uid):
		cuid = rsa.sign(str(uid).encode("utf-8"), self.privkey, 'SHA-256')
		self.cursor.execute("SELECT bal, full_name FROM cardholders WHERE uid=?", [cuid])
		fetch = self.cursor.fetchone()
		print(fetch[0], rsa.decrypt(fetch[1], self.privkey))

	def insert(self):
		cuid = rsa.sign(str(1234).encode("utf-8"), self.privkey, 'SHA-256')
		cname = rsa.encrypt("Melle Bosboom".encode('utf-8'), self.publkey)
		self.cursor.execute("""INSERT INTO cardholders VALUES (?, 2000, ?, 42069, 69, 420)
		""", [cuid, cname])
