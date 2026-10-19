"""
Gestor de colas de triaje para urgencias hospitalarias.

Orden de atención:
  1. Por nivel de triaje (1 = crítico, 2 = urgente, 3 = estándar).
  2. Dentro del mismo nivel, por orden de llegada (FIFO estricto).

Solo usa la biblioteca estándar de Python.
"""

from __future__ import annotations

import heapq
import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


# ---------------------------------------------------------------------------
# Dominio
# ---------------------------------------------------------------------------

class TriageLevel(IntEnum):
    """Niveles de triaje válidos. Un valor menor implica mayor prioridad."""
    CRITICAL = 1
    URGENT = 2
    STANDARD = 3


class EmptyQueueError(Exception):
    """Se lanza al intentar desencolar o consultar una cola vacía."""


@dataclass(frozen=True)
class Patient:
    """Paciente registrado en urgencias. Inmutable una vez creado."""

    name: str
    triage_level: int
    arrived_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        clean_name = self.name.strip() if isinstance(self.name, str) else ""
        if not clean_name:
            raise ValueError("El nombre del paciente no puede estar vacío.")

        # bool es subclase de int en Python: lo excluimos explícitamente.
        valid_levels = {level.value for level in TriageLevel}
        if isinstance(self.triage_level, bool) or self.triage_level not in valid_levels:
            raise ValueError("El nivel de triaje debe ser 1, 2 o 3.")

        # La dataclass es frozen, así que normalizamos el nombre así.
        object.__setattr__(self, "name", clean_name)

    def __str__(self) -> str:
        level = TriageLevel(self.triage_level).name
        return f"{self.name} [nivel {self.triage_level} - {level}] llegada {self.arrived_at:%H:%M:%S}"


# ---------------------------------------------------------------------------
# Cola de prioridad
# ---------------------------------------------------------------------------

class TriageQueue:
    """
    Cola de prioridad basada en un min-heap (heapq).

    Cada entrada es (triage_level, sequence, patient):
      - triage_level ordena por gravedad.
      - sequence es un contador monotónico que desempata en orden de llegada
        y evita que Python tenga que comparar objetos Patient.

    Todas las operaciones se protegen con un Lock para que la consulta y la
    mutación de la cola sean atómicas si varios workers la usan a la vez.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, Patient]] = []
        self._sequence = itertools.count()
        self._lock = threading.Lock()

    def enqueue(self, patient: Patient) -> None:
        """Añade un paciente en O(log n) respetando nivel y orden de llegada."""
        with self._lock:
            entry = (patient.triage_level, next(self._sequence), patient)
            heapq.heappush(self._heap, entry)

    def dequeue(self) -> Patient:
        """Extrae y devuelve el siguiente paciente a atender, en O(log n)."""
        with self._lock:
            if not self._heap:
                raise EmptyQueueError("No hay pacientes en espera.")
            return heapq.heappop(self._heap)[2]

    def peek(self) -> Patient:
        """Devuelve el siguiente paciente sin extraerlo, en O(1)."""
        with self._lock:
            if not self._heap:
                raise EmptyQueueError("No hay pacientes en espera.")
            return self._heap[0][2]

    def list_queue(self) -> list[Patient]:
        """
        Devuelve los pacientes en orden de atención, en O(n log n).
        Ordena una copia: no modifica el heap interno.
        """
        with self._lock:
            return [patient for _, _, patient in sorted(self._heap)]

    def stats(self) -> dict[int, int]:
        """Devuelve el número de pacientes en espera por nivel de triaje."""
        with self._lock:
            counts = {level.value: 0 for level in TriageLevel}
            for level, _, _ in self._heap:
                counts[level] += 1
            return counts

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    def is_empty(self) -> bool:
        return len(self) == 0