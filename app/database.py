import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.port = os.getenv("DB_PORT", 3306)
        self.connection = None

    def connect(self):
        """Establece la conexión a Amazon RDS."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )
            if self.connection.is_connected():
                print("¡Conexión exitosa a Amazon RDS!")
                return self.connection
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            return None

    def get_connection(self):
        """Devuelve la conexión activa, si no existe, la crea."""
        if self.connection is None or not self.connection.is_connected():
            self.connect()
        return self.connection

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Conexión cerrada.")

# Bloque de prueba: solo se ejecuta si corres este archivo directamente
if __name__ == "__main__":
    db = Database()
    db.connect()
    db.close()