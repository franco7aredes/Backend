from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base



# Si los tests parchean el engine y SessionLocal, usa esos
if not ("engine" in globals() and "SessionLocal" in globals()):
    SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()  # Esta clase es la base de todas las clases de modelo que definamos

# Función para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()