import time
from unittest.mock import patch, AsyncMock
import pytest
import asyncio
from typing import Dict

from app.capa_3_api.nsf_tipos import VentanaNSFActiva, tiempo_en_ms
from app.capa_3_api.utilidades_nsf import gestionar_fin_ventana
import app.capa_3_api.websockets.ApiWS as wsmod

@pytest.mark.asyncio
@patch('time.time')
async def test_tiempo_en_ms_correcto(mock_time):

    mock_time.return_value = 1000.0

    resultado = await tiempo_en_ms(segundos=5.0)

    assert resultado == 1005000
    mock_time.assert_called_once()


@pytest.mark.asyncio
@patch('app.capa_3_api.utilidades_nsf.asyncio.sleep', new_callable=AsyncMock)
async def test_gestionar_fin_ventana_correcto(mock_sleep, monkeypatch):

    ventana = VentanaNSFActiva(
        partida_id=1,
        ventana_id="ventana",
        actor_id=2,
        tipo_accion="jugar_set",
        payload={"carta":1},
        contador=0,
        tiempo_ms=14768,
        tarea=None
    )

    ventanas_dict: Dict[int, VentanaNSFActiva] = {1: ventana}

    mock_difundir = AsyncMock()
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", mock_difundir)

    await gestionar_fin_ventana(ventana, ventanas_dict)

    mock_sleep.assert_called_once()

    mock_difundir.assert_called_once_with(
        1,
        {
            "evento": "nsf_resolved",
            "partida_id": 1,
            "window_id": "ventana",
            "outcome": "execute",
            "tipo_accion": "jugar_set",
            "actor_id": 2,
            "payload": {"carta": 1}
        }
    )

    assert 1 not in ventanas_dict

@pytest.mark.asyncio
@patch('app.capa_3_api.utilidades_nsf.asyncio.sleep', new_callable=AsyncMock)
async def test_gestionar_fin_ventana_ventana_ya_no_valida(mock_sleep, monkeypatch):

    antigua = VentanaNSFActiva(
        partida_id=1,
        ventana_id="ventana-a",
        actor_id=2,
        tipo_accion="jugar_set",
        payload={"carta":1},
        contador=0,
        tiempo_ms=14768,
        tarea=None
    )


    nueva = VentanaNSFActiva(
        partida_id=1,
        ventana_id="ventana-x",
        actor_id=2,
        tipo_accion="jugar_set",
        payload={"carta":1},
        contador=2,
        tiempo_ms=54738,
        tarea=None
    )

    ventanas_dict: Dict[int, VentanaNSFActiva] = {1: nueva}

    await gestionar_fin_ventana(antigua, ventanas_dict)
    
    mock_sleep.assert_called_once()

    mock_difundir = AsyncMock()
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", mock_difundir)
    # no se tiene que haber mandado el mensaje, ni haber sacado la ventana actual
    mock_difundir.assert_not_called()

    assert 1 in ventanas_dict
    assert ventanas_dict[1].ventana_id == "ventana-x"
