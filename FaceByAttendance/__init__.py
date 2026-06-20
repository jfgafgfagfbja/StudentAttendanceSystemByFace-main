
try:
	import pymysql

	pymysql.install_as_MySQLdb()
except Exception:
	# If PyMySQL isn't available (or another MySQL driver is used),
	# Django will fall back to its configured backend driver.
	pass
