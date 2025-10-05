from app.db.databases import engine
from app.layer_0_db_definition.database_sqlalchemy import Base
from app.db.models.jugadores_models import Jugador
from app.db.models.partidas_models import Partida


Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Base de datos creada")