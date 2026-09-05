import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno (si el archivo .env existe y es válido)
load_dotenv()

# Leer variables con valores por defecto (por si el .env falla)
DB_USER = os.getenv('DB_USER', 'amagno_api')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
DB_HOST = os.getenv('DB_HOST', '192.168.100.17')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'Salvatore')

# Construir URL de conexión
#SQLALCHEMY_DATABASE_URL = #f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?client_encoding=UTF8&connect_timeout=10"
)

# Mensaje de depuración para saber a dónde se está conectando
print(f"--- CONECTANDO A BD: {DB_HOST}:{DB_PORT}/{DB_NAME} ---")

# Crear motor de base de datos
#engine = create_engine(SQLALCHEMY_DATABASE_URL)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    encoding='utf-8',
    client_encoding='utf-8',
    echo=False  # Cambia a True si quieres ver las consultas SQL en los logs
)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa
Base = declarative_base()

# Función para obtener sesión de BD
def get_db():
    db = SessionLocal()
    try:
        # Forzar UTF-8 en cada conexión
        db.execute(text("SET client_encoding TO 'UTF8'"))
        yield db
    finally:
        db.close()