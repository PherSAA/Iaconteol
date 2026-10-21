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


## Genesis LIVE — 21 de octubre de 2026
El panel ahora agrega una zona «Red de información viva» con:
- USGS: eventos de magnitud ≥2.5 en las últimas 24 horas, con hora UTC, magnitud, profundidad y vínculo a USGS. La fuente actualiza sus feeds aproximadamente cada minuto.
- NASA/JPL: acercamientos de asteroides dentro de 10 distancias lunares previstos en los próximos 30 días, con fecha de acercamiento.
- Coinbase Exchange: cuatro pares (BTC-USD, ETH-USD, SOL-USD, XRP-USD), velas horarias históricas, último cierre, cambio relativo de 24 velas y SMA20. Los cierres de velas **no son un ticker de cotizaciones de segundo a segundo**.
- Bluesky: búsqueda manual de publicaciones públicas por palabra clave y fecha, si el proveedor permite consultas anónimas. Las publicaciones son opiniones no verificadas y no suponen análisis de todas las redes sociales.

El backend intenta actualizar USGS cada 75 segundos, cripto cada 120 segundos y NASA cada hora; consulta fuentes en serie con límites de tiempo y conserva el último estado en memoria. Puedes pulsar «Consultar ahora» para forzar la consulta. Si una API falla, el panel muestra un error, sin inventar resultados. El monitor funciona **solo mientras el proceso de Python permanezca activo**. El Codespace puede suspenderse o detenerse; no es un servidor público 24/7.

**En el móvil:** usa la terminal de Codespaces para escribir \`git pull origin main\`. Detén el servidor anterior pulsando **Ctrl+C en la terminal donde se ejecuta**; si el puerto 8765 está ocupado, localiza y detén esa terminal antes de iniciar otro servidor. Luego ejecuta \`SPLIT_HOST=0.0.0.0 python server.py\` y abre el puerto 8765 desde «Ports». No hagas público el puerto: el proyecto aún no tiene autenticación.

**Predicción sísmica:** la USGS indica que no existe técnica científica demostrada que prediga cuándo, dónde y de qué magnitud será un terremoto. Podremos estudiar peligrosidad de largo plazo y anomalías observadas, pero no publicar predicciones infundadas.

**Predicción cripto:** los datos permiten análisis descriptivo. Antes de cualquier pronóstico habrá que crear un conjunto histórico, hacer pruebas cronológicas fuera de muestra, comparar baselines, incluir costos/errores y mostrar intervalos de incertidumbre. No hay señales de compra/venta automática.

**Presupuesto:** para mantenernos dentro de USD 500, empezar sin hardware, con Codespaces de uso limitado y APIs públicas, revisar cuotas y costos antes de activar servicios de pago. La operación 24/7 requerirá hosting, tareas programadas, persistencia, control de gastos, seguridad y monitoreo continuo.
