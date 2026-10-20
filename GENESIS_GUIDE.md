# Split Run Genesis — Instrucciones

Esta rama del proyecto contiene el motor Python, SQLite y panel HTML ya existente. Se conserva la figura de La Llave original y E.

## Android sin instalar Python

1. Abre el repositorio en GitHub y selecciona **Code > Codespaces > Create codespace on main**.
2. En la terminal ejecuta `SPLIT_HOST=0.0.0.0 python server.py`.
3. Abre la pestaña **Ports**, el puerto **8765** y usa **Open in Browser**.
4. Mantén **Port visibility: Private**. No hay autenticación; no publiques el puerto.

## Comprobar

Ejecuta `python -m unittest discover -p 'test_*.py' -v`. También puedes abrir la pestaña **Actions** y consultar `Genesis tests`.

## Alcance

El motor procesa tareas reales con varios procesos en una máquina y guarda resultados en SQLite. Un supervisor relanza procesos terminados y reasigna tareas incompletas. SQLite sigue siendo un único punto de fallo. Los datos de NASA y USGS se consultan desde sus endpoints públicos al pulsar los botones de misiones; dependen de la red. El ejemplo NASA integrado es **ilustrativo**, no es una medición en vivo.

La E central y La Llave son elementos del panel; no producen energía física ni garantizan seguridad o tolerancia universal a fallos.
