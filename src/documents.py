from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Document:
    """Контейнер для текстовых фрагментов, извлечённых с файловой системы."""

    path: Path
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Приводит метаданные к стандартному словарю."""
        # Ensure metadata is a plain dict to avoid surprises downstream.
        self.metadata = dict(self.metadata)

    def __repr__(self) -> str:
        """Возвращает удобочитаемое представление документа."""
        meta_keys = ", ".join(sorted(self.metadata))
        return f"<Document path={self.path} metadata=[{meta_keys}]>"
