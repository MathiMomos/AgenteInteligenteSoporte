# src/utils/util_base_de_datos.py

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import os
from src.util import util_keyvault as key

USER = key.getkeyapi("PGUSER")
PASSWORD = key.getkeyapi("PGPASSWORD")
HOST = key.getkeyapi("PGHOST")
PORT = key.getkeyapi("PGPORT")
DB_NAME = key.getkeyapi("PGDATABASE")

DATABASE_URL = (
    f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/analyticsdb?sslmode=require"
)

if not DATABASE_URL:
    # Si no encuentra la URL, detiene la aplicación para evitar errores
    raise ValueError("No se encontró DATABASE_URL en las variables de entorno. Revisa tu archivo .env")

# Crea el "motor" de SQLAlchemy. Esta es la conexión central a tu base de datos.
# Se crea una sola vez cuando la aplicación se inicia.
engine = create_engine(DATABASE_URL)

# --- 2. MAPEO AUTOMÁTICO DEL ORM ---
# Aquí le decimos a SQLAlchemy que "aprenda" la estructura de la base de datos
# en lugar de definirla nosotros a mano.

# Preparamos las variables para que existan incluso si el mapeo falla
Base = None
Persona = Cliente = Servicio = ClienteDominio = Colaborador = Analista = External = ClienteServicio = Ticket = Conversacion = Escalado = None

try:
    # Creamos una base para el automapeo
    Base = automap_base()

    # Esta línea se conecta a la BD, lee las tablas y crea las clases de Python
    Base.prepare(autoload_with=engine)

    # Exponemos las clases generadas para poder importarlas en otros archivos
    Persona = Base.classes.persona
    Cliente = Base.classes.cliente
    Servicio = Base.classes.servicio
    ClienteDominio = Base.classes.cliente_dominio
    Colaborador = Base.classes.colaborador
    Analista = Base.classes.analista
    External = Base.classes.external
    ClienteServicio = Base.classes.cliente_servicio
    Ticket = Base.classes.ticket
    Conversacion = Base.classes.conversacion
    Escalado = Base.classes.escalado

    print("Conexión y mapeo a la base de datos exitosos.")

except Exception as e:
    print(f"Error al conectar o mapear la base de datos: {e}")


# --- 3. PROVEEDOR DE SESIONES ---
def obtener_bd():
    """
    Esta es la función clave que usarán nuestros endpoints.

    Cada vez que una petición llega a un endpoint que necesita la BD, FastAPI
    ejecutará esta función. Creará una nueva sesión (`db`), se la entregará
    al endpoint para que haga sus consultas, y al final, se asegurará de cerrarla.
    """
    if not engine:
        raise RuntimeError("El motor de la BD no fue inicializado por un error previo.")

    db = Session(engine)
    try:
        yield db
    finally:
        db.close()