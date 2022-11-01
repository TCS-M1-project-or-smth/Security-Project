from pysqlitecipher import sqlitewrapper
# https://www.blog.letscodeofficial.com/@harshnative/encrypting-sqlite-database-in-python-using-pysqlitecipher-module-easy-and-secure-encryption-in-python-sqlite/


class Database:
	def __init__(self):
		self.__connection = sqlitewrapper.SqliteCipher(dataBasePath="system.db", checkSameThread=False, password="1234567689")
		coll_list = [["uid", "INT"], ["bal", "SMALLINT"], ["full_name", "TEXT"],
				["person_id", "INT"], ["clearance", "TINYINT"], ["counterval", "TINYINT"]]
		if not self.__connection.checkTableExist("cardholders"):
			self.__connection.createTable("cardholders", coll_list, makeSecure=True, commit=True)

	def get_bal_from_uid(self, uid):
		#self.cursor.execute("SELECT bal FROM cardholders WHERE uid=?", uid)
		data = self.__connection.getDataFromTable("cardholders")
		print(data)

	def insert_uid(self):
		self.__connection.insertIntoTable("cardholders", [0b00010000111100101100, 2000, "Melle Bosboom", 42069, 69, 420], commit=True)
