from pydantic import BaseModel, ConfigDict


class ReponerRequest(BaseModel):
    jugador_id: int


class ReponerResponse(BaseModel):
    mensaje: str
    cartas: list[dict] | None = None
    model_config = ConfigDict(from_attributes=True)


class DescartarRequest(BaseModel):
    jugador_id: int


class DescartarResponse(BaseModel):
    mensaje: str


class ManoResponse(BaseModel):
    cantidad: int
