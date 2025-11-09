import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import asyncio

@dataclass
class VentanaNSFActiva:
    partida_id: int
    ventana_id: str
    actor_id: int
    tipo_accion: str
    payload: Dict[str, Any]
    contador: int = 0
    tiempo_ms: int = 0
    tarea: Optional[asyncio.Task] = field(default=None, compare=False)
   
async def tiempo_en_ms(segundos: float = 5.0) -> int:
    """ calcula el timestamp de tiempo_ms en milisegundos"""
    return int((time.time() + segundos) * 1000)
