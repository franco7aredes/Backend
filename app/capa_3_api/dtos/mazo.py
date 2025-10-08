from pydantic import BaseModel, ConfigDict


class ReponerSolicitud(BaseModel):
    jugador_id: int


class ReponerRespuesta(BaseModel):
    mensaje: str
    cartas: list[dict] | None = None
    model_config = ConfigDict(from_attributes=True)


class DescartarSolicitud(BaseModel):
    jugador_id: int


class DescartarRespuesta(BaseModel):
    mensaje: str


class ManoRespuesta(BaseModel):
    cantidad: int
