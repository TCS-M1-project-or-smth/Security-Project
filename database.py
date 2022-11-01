import sqlite3


class Database:
	def __init__(self):
		self.__connection = sqlite3.connect("system.db")
		self.cursor = self.__connection.cursor()
		self.cursor.execute("""CREATE TABLE IF NOT EXISTS cardholders(
			uid INT,
			bal SMALLINT,
			full_name varchar,
			person_id int,
			clearance int,
			counterval tinyint
		)""")

	def __del__(self):
		self.__connection.close()

	def get_bal_from_uid(self, uid):
		self.cursor.execute("SELECT bal FROM cardholders WHERE uid=?", uid)
