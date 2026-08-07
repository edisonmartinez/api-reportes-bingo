import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno
load_dotenv()

# Leer variables con valores por defecto
DB_USER = os.getenv('DB_USER', 'amagno_api')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'Salvatore')

# Construir URL de conexión con el parámetro de codificación en la URL (forma correcta en SQLAlchemy 2.0)
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?client_encoding=UTF8"
)

print(f"--- CONECTANDO A BD: {DB_HOST}:{DB_PORT}/{DB_NAME} ---")

# Crear motor de base de datos (SIN los argumentos 'encoding' que causaban el error)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False
)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa
Base = declarative_base()

# Función para obtener sesión de BD
def get_db():
    db = SessionLocal()
    try:
        # Refuerzo: asegurar UTF-8 en cada conexión
        db.execute(text("SET client_encoding TO 'UTF8'"))
        yield db
    finally:
        db.close()