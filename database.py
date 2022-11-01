import sqlite3


class Database:
	def __init__(self):
		self.connection = sqlite3.connect("system.db")
		self.connection.execute("""CREATE TABLE IF NOT EXISTS cardholders(
			uid INT,
			bal SMALLINT,
			full_name varchar,
			person_id int,
			clearance int,
			counterval tinyint
		)""")
