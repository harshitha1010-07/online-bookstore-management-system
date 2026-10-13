from database import get_connection
try:
    connection = get_connection()

    print("Successfully connected to MySQL!")

    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")

    print("\nTables in the database:")

    for table in cursor.fetchall():
        print(table[0])

    cursor.close()
    connection.close()

except Exception as error:
    print("Connection failed!")
    print(error)