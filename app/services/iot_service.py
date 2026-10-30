#iot_service.py
from app.database import Database

class IoTService:
    def _ejecutar_sp(self, sp_name: str, params: tuple = (), fetch: str = "none"):
        """Ejecuta un Stored Procedure con una conexión PROPIA (segura entre hilos)."""
        db = Database()
        conn = db.get_connection()
        if not conn:
            raise Exception("Error de conexión a la base de datos")

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc(sp_name, params)

            resultado = None
            # Iterar SIEMPRE para vaciar el búfer de MySQL y evitar "Commands out of sync"
            for res in cursor.stored_results():
                if fetch == "all" and resultado is None:
                    resultado = res.fetchall()
                elif fetch == "one" and resultado is None:
                    resultado = res.fetchone()
                else:
                    res.fetchall()  # Lectura de limpieza

            if fetch == "none":
                resultado = {"status": "success", "mensaje": f"Procedimiento {sp_name} ejecutado."}

            conn.commit()
            return resultado
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            db.close()

    # --- VEHICULOS ---
    def crear_vehiculo(self, nombre: str, modelo: str, desc: str, micro: str):
        return self._ejecutar_sp('sp_crear_vehiculo', (nombre, modelo, desc, micro), fetch="one")

    def obtener_vehiculos(self):
        return self._ejecutar_sp('sp_obtener_vehiculos', fetch="all")

    def obtener_vehiculo(self, id_vehiculo: int):
        return self._ejecutar_sp('sp_obtener_vehiculo', (id_vehiculo,), fetch="one")

    def actualizar_vehiculo(self, id_vehiculo: int, nombre: str, modelo: str, desc: str, micro: str, activo: bool):
        return self._ejecutar_sp('sp_actualizar_vehiculo', (id_vehiculo, nombre, modelo, desc, micro, activo))

    def eliminar_vehiculo(self, id_vehiculo: int):
        return self._ejecutar_sp('sp_eliminar_vehiculo', (id_vehiculo,))

    # --- COMANDOS ---
    def crear_comando(self, id_vehiculo: int, nombre: str, codigo: int, desc: str):
        return self._ejecutar_sp('sp_crear_comando', (id_vehiculo, nombre, codigo, desc), fetch="one")

    def obtener_comandos_vehiculo(self, id_vehiculo: int):
        return self._ejecutar_sp('sp_obtener_comandos_vehiculo', (id_vehiculo,), fetch="all")

    def actualizar_comando(self, id_comando: int, nombre: str, codigo: int, desc: str, activo: bool):
        return self._ejecutar_sp('sp_actualizar_comando', (id_comando, nombre, codigo, desc, activo))

    def eliminar_comando(self, id_comando: int):
        return self._ejecutar_sp('sp_eliminar_comando', (id_comando,))

    # --- ESTADO E HISTORIAL ---
    def obtener_estado(self, id_vehiculo: int):
        return self._ejecutar_sp('sp_obtener_estado', (id_vehiculo,), fetch="one")

    def registrar_movimiento_individual(self, id_vehiculo: int, id_comando: int, conectado: bool, origen: str):
        """Guarda estado + historial. La validación del comando ya la hace la API (caché)."""
        db = Database()
        conn = db.get_connection()
        if not conn:
            raise Exception("Error de conexión a la base de datos")
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc('sp_actualizar_estado', (id_vehiculo, id_comando, conectado))
            cursor.callproc('sp_registrar_historial', (id_vehiculo, id_comando, origen))
            conn.commit()
            return {"status": "success", "mensaje": "Movimiento registrado y estado actualizado"}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            db.close()

    def actualizar_solo_estado(self, id_vehiculo: int, id_comando: int):
        return self._ejecutar_sp('sp_actualizar_estado', (id_vehiculo, id_comando, True))

    def obtener_historial_limitado(self, id_vehiculo: int):
        historial = self._ejecutar_sp('sp_obtener_historial', (id_vehiculo,), fetch="all")
        return historial[:10] if historial else []

    # --- DEMOS Y MOVIMIENTOS ---
    def crear_demo(self, id_vehiculo: int, nombre: str, desc: str):
        return self._ejecutar_sp('sp_crear_demo', (id_vehiculo, nombre, desc), fetch="one")

    def obtener_demos(self, id_vehiculo: int):
        return self._ejecutar_sp('sp_obtener_demos', (id_vehiculo,), fetch="all")

    def actualizar_demo(self, id_demo: int, nombre: str, desc: str, activo: bool):
        return self._ejecutar_sp('sp_actualizar_demo', (id_demo, nombre, desc, activo))

    def eliminar_demo(self, id_demo: int):
        return self._ejecutar_sp('sp_eliminar_demo', (id_demo,))

    def agregar_movimiento_demo(self, id_demo: int, id_comando: int, orden: int, duracion: int, pausa: int):
        return self._ejecutar_sp('sp_agregar_movimiento_demo', (id_demo, id_comando, orden, duracion, pausa))

    def obtener_movimientos_demo(self, id_demo: int):
        return self._ejecutar_sp('sp_obtener_movimientos_demo', (id_demo,), fetch="all")

    def actualizar_movimiento_demo(self, id_mov: int, id_comando: int, orden: int, duracion: int, pausa: int):
        return self._ejecutar_sp('sp_actualizar_movimiento_demo', (id_mov, id_comando, orden, duracion, pausa))

    def eliminar_movimiento_demo(self, id_mov: int):
        return self._ejecutar_sp('sp_eliminar_movimiento_demo', (id_mov,))