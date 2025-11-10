import time
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import asyncio
from typing import Dict

from app.capa_3_api.nsf_tipos import VentanaNSFActiva, tiempo_en_ms
from app.capa_3_api.utilidades_nsf import *
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


@pytest.mark.asyncio
@patch('app.capa_3_api.utilidades_nsf.asyncio.create_task')
@patch('app.capa_3_api.utilidades_nsf.tiempo_en_ms', new_callable=AsyncMock)
@patch('app.capa_3_api.utilidades_nsf.uuid.uuid4')
async def test_activar_ventana_nsf_bonito(mock_uuid, mock_tiempo_en_ms, mock_create_task):
    
    mock_uuid.return_value.hex = "test-uuid-123"
    mock_tiempo_en_ms.return_value = 1234679
    mock_tarea = MagicMock(name="mock_tarea_creada")
    mock_create_task.return_value = mock_tarea

    ventanas_dict: Dict[int, VentanaNSFActiva] = {}
    partida_id = 10
    id_jugador = 5
    tipo_accion = "jugar_carta"
    payload = {"carta_id": 100}

    ventana_creada = await activar_ventana_nsf(
        tipo_accion=tipo_accion,
        id_jugador=id_jugador,
        partida_id=partida_id,
        ventanas_dict=ventanas_dict,
        payload=payload
    )

    
    mock_uuid.assert_called_once()
    mock_tiempo_en_ms.assert_called_once_with(5.0)
    
    # hay que ver si se crea una tarea
    mock_create_task.assert_called_once()
    args_tarea = mock_create_task.call_args[0]
    coro_tarea = args_tarea[0]
    assert coro_tarea.__name__ == 'gestionar_fin_ventana'
    
    # cierro la corutina
    coro_tarea.close()
    # vemos el dict
    assert 10 in ventanas_dict
    assert ventanas_dict[10] is ventana_creada

    assert ventana_creada.partida_id == 10
    assert ventana_creada.actor_id == 5
    assert ventana_creada.tipo_accion == "jugar_carta"
    assert ventana_creada.payload == {"carta_id": 100}
    assert ventana_creada.contador == 0
    assert ventana_creada.ventana_id == "test-uuid-123"
    assert ventana_creada.tiempo_ms == 1234679
    assert ventana_creada.tarea is mock_tarea


@pytest.mark.asyncio
@patch('app.capa_3_api.utilidades_nsf.asyncio.sleep', new_callable=AsyncMock)
@patch('app.capa_3_api.utilidades_nsf.asyncio.create_task')
@patch('app.capa_3_api.utilidades_nsf.tiempo_en_ms', new_callable=AsyncMock)
async def test_refrescar_ventana_nsf_cancela_tarea_anterior(
    mock_tiempo_en_ms, mock_create_task, mock_sleep
):
    
    mock_tiempo_en_ms.return_value = 55555
    mock_tarea_original = MagicMock(name="tarea_original")
    mock_tarea_original.done.return_value = False # La tarea está activa
    
    mock_tarea_nueva = MagicMock(name="tarea_nueva")
    mock_create_task.return_value = mock_tarea_nueva

    ventanas_dict: Dict[int, VentanaNSFActiva] = {}
    ventana = VentanaNSFActiva(
        partida_id=1,
        ventana_id="v1",
        actor_id=2,
        tipo_accion="test",
        payload={},
        contador=0,
        tiempo_ms=10000,
        tarea=mock_tarea_original
    )

    await refrescar_ventana_nsf(ventana, ventanas_dict)

    
    assert ventana.contador == 1
    assert ventana.tiempo_ms == 55555
    assert ventana.tarea is mock_tarea_nueva # Tarea fue reemplazada

    mock_tiempo_en_ms.assert_called_once_with(5.0)
    
    mock_tarea_original.done.assert_called_once()
    mock_tarea_original.cancel.assert_called_once() # Debe cancelarse
    mock_sleep.assert_called_once_with(0) # Se esperó para procesar cancelación

    # vemos si se creo una nueva tarea
    mock_create_task.assert_called_once()
    # Verificamos que la nueva tarea sea 'gestionar_fin_ventana'
    coro_tarea = mock_create_task.call_args[0][0]
    assert coro_tarea.__name__ == 'gestionar_fin_ventana'

    # cierro la corutina
    coro_tarea.close()

@pytest.mark.asyncio
@patch('app.capa_3_api.utilidades_nsf.asyncio.sleep', new_callable=AsyncMock)
@patch('app.capa_3_api.utilidades_nsf.asyncio.create_task')
@patch('app.capa_3_api.utilidades_nsf.tiempo_en_ms', new_callable=AsyncMock)
async def test_refrescar_ventana_nsf_tarea_anterior_ya_hecha(
    mock_tiempo_en_ms, mock_create_task, mock_sleep
):
    
    mock_tiempo_en_ms.return_value = 55555
    mock_tarea_original = MagicMock(name="tarea_original")
    mock_tarea_original.done.return_value = True # La tarea YA terminó
    
    mock_tarea_nueva = MagicMock(name="tarea_nueva")
    mock_create_task.return_value = mock_tarea_nueva

    ventanas_dict: Dict[int, VentanaNSFActiva] = {}
    ventana = VentanaNSFActiva(
        partida_id=1,
        ventana_id="v1",
        actor_id=2,
        tipo_accion="test",
        payload={},
        contador=0,
        tiempo_ms=10000,
        tarea=mock_tarea_original
    )

    await refrescar_ventana_nsf(ventana, ventanas_dict)

    
    assert ventana.contador == 1
    assert ventana.tiempo_ms == 55555
    assert ventana.tarea is mock_tarea_nueva

    mock_tiempo_en_ms.assert_called_once_with(5.0)
    
    mock_tarea_original.done.assert_called_once()
    mock_tarea_original.cancel.assert_not_called() # no se tiene que cancelar
    mock_sleep.assert_not_called() 

    mock_create_task.assert_called_once()
    coro_tarea = mock_create_task.call_args[0][0]
    assert coro_tarea.__name__ == 'gestionar_fin_ventana'
    # cierro la corutina
    coro_tarea.close()
