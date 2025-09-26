
from typing import Union
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware




from .api import api_router
from .websockets.ApiWS import ws_router

from app.db.databases import Base, engine
# Importa ambos modelos para registrar las tablas en el metadata
from app.db.models import partidas_models, jugadores_models

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
origins = [
    "http://localhost:5173",  
    "http://localhost:5174",
    "http://127.0.0.1:8000",  
    "http://localhost:3000",  # Next.js frontend
]



# Aca se incluyen los routers
app.include_router(api_router)
app.include_router(ws_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)
