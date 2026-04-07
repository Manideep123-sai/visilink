import pymysql

def create_database():
    try:
        # Connect to MySQL server (without specifying a database)
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='Password@1234',
            port=3306
        )
        
        with connection.cursor() as cursor:
            # Create the database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS visilink;")
            print("Successfully created or verified the 'visilink' database.")
            
        connection.commit()
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == "__main__":
    create_database()
