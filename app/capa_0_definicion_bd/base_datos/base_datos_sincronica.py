from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base

# Si tests u otros módulos ya definieron engine/SessionLocal, respetarlos
if not ("engine" in globals() and "SessionLocal" in globals()):
    SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
