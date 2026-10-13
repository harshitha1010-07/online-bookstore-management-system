import mysql.connector
def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Harshi@1010",
        database="online_bookstore_management_system"
    )
    return connection