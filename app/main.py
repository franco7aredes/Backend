from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

"""
app = FastAPI()
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
origins = [
    "http://localhost:5173",  # Reemplaza esto con la URL de tu frontend
    "http://localhost:5174",
    "http://127.0.0.1:8000",  # Asegúrate de incluir esta también si es diferente
]
"""
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