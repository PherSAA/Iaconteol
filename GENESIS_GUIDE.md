# Split Run Genesis — Misiones científicas y criptomonedas

Conservamos las coordenadas originales de **La Llave** y la célula **E**. Ocho procesos independientes ejecutan cálculos y procesan registros de datos abiertos en una sola máquina con SQLite. La recuperación de tareas se implementa mediante una cola persistente; no existe todavía comunicación directa entre células, ni red de varios ordenadores.

## Actualizar tu Codespace desde Android
En una terminal nueva, detén el servidor anterior con Ctrl+C si está activo. Luego:
```bash
git pull origin main
SPLIT_HOST=0.0.0.0 python server.py
```
Abre el puerto 8765 desde **Ports**, mantenlo **Private** y entra al panel.

## Misiones
- **NASA/JPL**: consulta acercamientos de asteroides de los próximos 30 días con filtro de distancia (≤10 distancias lunares), si la fuente está disponible.
- **USGS**: procesa eventos del feed de terremotos de magnitud 2.5+ del último día.
- **Crypto**: BTC-USD, ETH-USD, SOL-USD y XRP-USD. Usa velas históricas públicas de Coinbase (últimas 100 velas de una hora) y calcula precio último, cambio, media simple, desviación estándar de retornos logarítmicos, caída máxima entre cierres y volumen. No compra/vende ni predice rendimientos. Si Coinbase rechaza la solicitud o impone límites, se muestra un error explícito.

## Pruebas y benchmarks
```bash
python -m unittest -v test_genesis.py
python benchmark.py --tasks 1000
python benchmark.py --tasks 10000 --fail-worker
python benchmark.py --tasks 10000 --kind sha256_chain
```
El benchmark se ejecuta con base SQLite temporal e informa tiempos reales, tareas procesadas, errores, reintentos y reinicios. No asumas que los tiempos medidos en Codespaces representan rendimiento en otras máquinas.

## Resiliencia y límites
- En cada reinicio del motor, trabajos marcados como «running» se devuelven a «pending».
- La supervisión reinicia procesos terminados inesperadamente y vuelve a poner sus tareas en la cola.
- La clave primaria de tareas impide dos filas con el mismo ID. **No garantiza exactamente una ejecución** ni evita efectos externos duplicados.
- SQLite y la máquina son puntos únicos de fallo; la demo no está lista para producción.
- La latencia promedio incluye espera en cola y procesamiento; el throughput mide tareas completadas desde el último inicio.
- El indicador de resultados duplicados cuenta filas con ID repetido, no todos los posibles efectos duplicados de negocio.
- El servidor es experimental, sin autenticación: **nunca hagas público el puerto Codespaces**.

## Orden de investigación
1. Validar 1.000 y 10.000 tareas con y sin fallos.
2. Evaluar eventos NASA/USGS en vivo y registrar datos reales.
3. Analizar criptomonedas con datos históricos, sin trading.
4. Comparar estrategias de asignación, checkpoint y respaldo por desfase frente a baselines. La geometría de La Llave permanece intacta.
5. Solo después, integrar agentes de IA, comunicación entre dispositivos y autenticación.
