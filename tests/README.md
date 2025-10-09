Guía breve de tipos de tests

- Unit (unitarios)
	- Qué: prueban una unidad pequeña (función/método/clase) en aislamiento.
	- Cómo: mockeando dependencias externas (DB, red, reloj, random).
	- Objetivo: validar la lógica pura y contratos de esa unidad.
	- Carpeta: `tests/unit/`.

- Integration (integración)
	- Qué: prueban que varias piezas colaboren correctamente (slice de la app o con infraestructura real de pruebas).
	- Cómo: routers con servicio mockeado, o modelos/ORM con DB sqlite de test.
	- Objetivo: detectar errores de pegado entre capas, esquemas y wiring.
	- Carpeta: `tests/integration/`.

- E2E (extremo a extremo)
	- Qué: validan el sistema desde “afuera” (HTTP/WS) atravesando todas las capas.
	- Cómo: escenarios reales de negocio usando el cliente de pruebas.
	- Objetivo: máxima confianza de que el flujo completo funciona.
	- Carpeta: `tests/e2e/`.

¿Por qué separarlos?
- Velocidad y feedback: unit son muchos y rápidos; integration valida el pegado; e2e confirma el todo.
- Diagnóstico: los fallos unitarios son más fáciles de ubicar; e2e da confianza al usuario final.
- Mantenibilidad: cuanto más arriba en la pirámide, más costoso/ frágil; priorizamos unit e integration y usamos e2e con moderación.

Reglas prácticas
- Cambios de lógica pura → unit.
- Cambios en DTOs/mapeos/routers/ORM o wiring → integration.
- Cambios en contrato público o flujos completos → e2e.

Ejemplo de Uso de los Repos mocks:

from tests.mocks.repos_mocks import (
    crear_repo_partida_mock,
    crear_repo_jugador_mock,
    crear_repo_carta_mock,
    crear_partida_en_juego,
    crear_jugador,
)

repo_p = crear_repo_partida_mock()
repo_j = crear_repo_jugador_mock()

repo_p.obtener.return_value = crear_partida_en_juego(turno_actual=1)
repo_j.obtener.return_value = crear_jugador(id_jugador=10, orden_turno=1, id_partida=1)

# También podés simular errores
from app.capa_2_logica.errores import PartidaNoEncontrada
repo_p.obtener.side_effect = lambda *_: (_ for _ in ()).throw(PartidaNoEncontrada())

