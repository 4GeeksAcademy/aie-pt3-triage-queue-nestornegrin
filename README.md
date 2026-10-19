# Gestor de colas de triaje

Gestor de colas de prioridad para la unidad de urgencias de un hospital, en Python y por terminal.

- Los pacientes se atienden por nivel de triaje: 1 = crítico, 2 = urgente, 3 = estándar.
- Dentro del mismo nivel, por estricto orden de llegada (FIFO).
- Solo usa la biblioteca estándar de Python (`heapq`, `datetime`, `threading`).

## Requisitos

Python 3.10 o superior.

## Cómo ejecutarlo

    python3 triage_queue.py

## Operaciones de `TriageQueue`

| Método | Descripción |
|---|---|
| `enqueue(patient)` | Añade un paciente respetando nivel y orden de llegada. |
| `dequeue()` | Extrae el siguiente paciente. Lanza `EmptyQueueError` si la cola está vacía. |
| `peek()` | Muestra el siguiente paciente sin extraerlo. |
| `list_queue()` | Devuelve la lista de pacientes en orden de atención. |
| `stats()` | Devuelve el número de pacientes en espera por nivel. |

## Estructura

    triage_queue.py   # Modelo (Patient), cola (TriageQueue), CLI y punto de entrada
    DESIGN.md         # Decisiones de diseño y escenario concurrente

Las decisiones técnicas están explicadas en [DESIGN.md](DESIGN.md).