# Notas de diseño — Gestor de colas de triaje

## 1. Elección de la estructura de datos

La cola interna es un **min-heap** (`heapq`) cuyas entradas son tuplas:

    (triage_level, secuencia, paciente)

- `triage_level` ordena por gravedad: el nivel 1 siempre sale antes que el 2, y el 2 antes que el 3.
- `secuencia` es un contador creciente (`itertools.count`) que desempata dentro del mismo nivel y garantiza el **orden de llegada (FIFO) estricto**.

### Por qué un contador y no el timestamp para desempatar

Dos pacientes pueden registrarse en el mismo instante y tener el mismo `arrived_at`. En ese caso el orden sería ambiguo y Python intentaría comparar dos objetos `Patient`, lo que lanza un error. El contador es único por paciente, así que el desempate es siempre determinista.

### Comparativa con las alternativas

| Estructura | Insertar | Siguiente paciente | Problema |
|---|---|---|---|
| Una sola `deque` | O(1) solo al final | O(1) | No respeta prioridades: un crítico que llega tarde obliga a recorrer o reordenar la cola, O(n). |
| Lista ordenada (`bisect.insort`) | O(n) | O(1) | Cada inserción desplaza elementos en memoria. Se degrada con colas largas. |
| Tres `deque` (una por nivel) | O(1) | O(1) | Válida para 3 niveles fijos, pero la lógica de prioridad queda repartida en condicionales y no escala si se añaden niveles. |
| **Heap (elegida)** | **O(log n)** | **O(log n) extraer, O(1) consultar** | Ninguno relevante: un paciente crítico se coloca en su sitio sin reordenar toda la cola. |

**Razón concreta de la elección:** el heap inserta un paciente crítico en su posición correcta en O(log n) sin reordenar la cola completa, mantiene la regla de prioridad en un único sitio (la tupla) y sirve igual para 3 niveles que para 10. Es el mismo patrón que usan los planificadores de jobs y los sistemas de colas de tickets.

`list_queue()` ordena una **copia** del heap (O(n log n)), así que mostrar la cola nunca altera el orden real de atención.

## 2. Escenario concurrente

**Escenario:** un worker A llama a `dequeue()` justo cuando un worker B hace `enqueue()` de un paciente crítico.

### Riesgos sin protección

- **Doble procesamiento:** si dos workers consultan quién es el siguiente y después lo extraen en dos pasos separados, ambos pueden quedarse con el mismo paciente.
- **Estado corrupto:** `heappush` y `heappop` reordenan la lista interna; si se intercalan, el heap puede quedar desordenado y romper la prioridad.

### Solución aplicada

`TriageQueue` usa un único `threading.Lock`. Cada operación es una **sección crítica completa**: la comprobación y la modificación ocurren dentro del mismo bloqueo.

**Orden de mutación en `dequeue()`:**

1. Adquirir el lock.
2. Comprobar que la cola no está vacía.
3. Extraer el paciente del heap: desde este momento ya no está en la cola y ningún otro worker puede obtenerlo.
4. Liberar el lock.
5. Solo entonces el worker atiende al paciente, fuera del lock, para no bloquear a los demás.

**Orden en `enqueue()`:** adquirir el lock → asignar el número de secuencia → insertar en el heap → liberar.

### Resultado

Como las dos operaciones no pueden intercalarse, solo hay dos desenlaces posibles y ambos son correctos:

- El crítico entra **antes** de la extracción: el worker A lo recibe a él.
- El crítico entra **después**: queda el primero de la cola para la siguiente llamada.

Ningún paciente se pierde ni se procesa dos veces. La regla clave es **reclamar extrayendo**: un paciente se asigna a un worker en el mismo paso en que sale de la cola, nunca con un `peek()` seguido de un `dequeue()` por separado.

### En un sistema distribuido

Con varios procesos o servidores, un lock en memoria no basta. Se aplicaría el mismo principio con operaciones atómicas del almacenamiento compartido, por ejemplo `SELECT ... FOR UPDATE SKIP LOCKED` en PostgreSQL o `ZPOPMIN` en Redis.