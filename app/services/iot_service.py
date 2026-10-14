from app.database import Database

class IoTService:
    def __init__(self):
        self.db = Database()

    def registrar_movimiento_individual(self, id_vehiculo: int, id_comando: int, conectado: bool, origen: str):
        """Valida el comando y ejecuta la actualización de estado e historial en una sola transacción."""
        conn = self.db.get_connection()
        if not conn:
            raise Exception("Error de conexión a la base de datos")
        
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Validar que el comando pertenezca a este vehículo
            cursor.callproc('sp_obtener_comandos_vehiculo', (id_vehiculo,))
            comandos = []
            for result in cursor.stored_results():
                comandos = result.fetchall()
            
            comando_valido = any(c['id_comando'] == id_comando for c in comandos)
            if not comando_valido:
                raise ValueError(f"El comando {id_comando} no existe o no pertenece al vehículo {id_vehiculo}.")

            # 2. Ejecutar SPs (la transacción ya se inicia implícitamente por el conector)
            cursor.callproc('sp_actualizar_estado', (id_vehiculo, id_comando, conectado))
            cursor.callproc('sp_registrar_historial', (id_vehiculo, id_comando, origen))
            
            # 3. Confirmar cambios en RDS
            conn.commit()
            return {"status": "success", "mensaje": "Movimiento registrado y estado actualizado"}

        except Exception as e:
            conn.rollback() # Si falla, deshacemos
            raise e
        finally:
            cursor.close()
            self.db.close()

    def obtener_historial_limitado(self, id_vehiculo: int):
        """Obtiene el historial y devuelve únicamente los últimos 10 movimientos."""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc('sp_obtener_historial', (id_vehiculo,))
            historial = []
            for result in cursor.stored_results():
                historial = result.fetchall()
            
            # Regla de negocio: MÁXIMO 10 registros
            return historial[:10]
        except Exception as e:
            raise e
        finally:
            cursor.close()
            self.db.close()

    def obtener_ultimo_estado(self, id_vehiculo: int):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc('sp_obtener_estado', (id_vehiculo,))
            estado = None
            for result in cursor.stored_results():
                estado = result.fetchone()
            return estado
        finally:
            cursor.close()
            self.db.close()

    def obtener_movimientos_demo(self, id_demo: int):
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc('sp_obtener_movimientos_demo', (id_demo,))
            movimientos = []
            for result in cursor.stored_results():
                movimientos = result.fetchall()
            return movimientos
        finally:
            cursor.close()
            self.db.close()

    def actualizar_solo_estado(self, id_vehiculo: int, id_comando: int):
        """Regla de negocio: La DEMO actualiza el estado pero NO registra en el historial."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_actualizar_estado', (id_vehiculo, id_comando, True))
            conn.commit()
        except Exception as e:
            conn.rollback()
        finally:
            cursor.close()
            self.db.close()        