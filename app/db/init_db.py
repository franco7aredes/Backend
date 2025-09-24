from databases import engine, Base
from models.jugadores_models import Jugador
from models.partidas_models import Partida


Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Base de datos creada")