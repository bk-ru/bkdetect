from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Union

from docx import Document as DocxDocument

from documents import Document
from indexing import TfidfIndexer
from loaders import ChunkedDocumentLoader
from text_pipeline import TextPipeline


@dataclass(frozen=True)
class SourceMatch:
    """Описание найденного документа и его итогового балла схожести."""

    path: Path
    score: float


@dataclass(frozen=True)
class SourcePosition:
    """Данные о совпавшем фрагменте внутри документа-источника."""

    path: Path
    index: int
    snippet: str
    score: float
    label: str


class SourceFinder:
    """Фасад, объединяющий загрузчик, текстовый пайплайн и индексатор."""

    def __init__(self, loader: ChunkedDocumentLoader, pipeline: TextPipeline, indexer: TfidfIndexer) -> None:
        """Принимает готовые компоненты и объединяет их в сервис поиска."""
        self.loader = loader
        self.pipeline = pipeline
        self.indexer = indexer

    @classmethod
    def from_path(
        cls,
        input_path: Union[str, Path],
        *,
        language: str = "ru",
        use_stemming: bool = True,
        remove_stopwords: bool = True,
        chunk_size: int = 500,
    ) -> "SourceFinder":
        """Создаёт фасад, используя стандартные компоненты и настройки."""
        path = Path(input_path)
        loader = ChunkedDocumentLoader(path, chunk_size=chunk_size)
        pipeline = TextPipeline(language=language, use_stemming=use_stemming, remove_stopwords=remove_stopwords)
        indexer = TfidfIndexer()
        return cls(loader, pipeline, indexer)

    def build_index(self) -> None:
        """Проходит по всем документам и добавляет их в индекс."""
        for docs_chunk in self.loader.load():
            processed = [self._process_document(doc) for doc in docs_chunk]
            self.indexer.partial_fit(processed)

    def find_sources(self, query_text: str, top_k: int = 5) -> List[SourceMatch]:
        """Ищет наиболее похожие документы и возвращает их с баллами."""
        tokens = self.pipeline.transform(query_text)
        if not tokens:
            return []

        scored_documents = self.indexer.query(tokens, top_k=None)
        best_scores = self._aggregate_best_scores(scored_documents)
        ranked_paths = sorted(best_scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [SourceMatch(path=path, score=score) for path, score in ranked_paths]

    def find_sources_from_file(self, file_path: Union[str, Path], top_k: int = 5) -> List[SourceMatch]:
        """Считывает текст из файла и запускает поиск источников."""
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        return self.find_sources(text, top_k)

    def locate_source_positions(
        self,
        query_text: str,
        *,
        top_k: int = 5,
        max_positions_per_file: int = 2,
        snippet_len: int = 200,
    ) -> List[SourcePosition]:
        """Находит совпадающие фрагменты в документах-кандидатах."""
        matches = self.find_sources(query_text, top_k=top_k)
        if not matches:
            return []

        query_tokens = set(self.pipeline.transform(query_text))
        positions: List[SourcePosition] = []

        for match in matches:
            if match.path.suffix.lower() == ".docx":
                positions.extend(
                    self._scan_docx(
                        match,
                        query_tokens,
                        max_positions_per_file=max_positions_per_file,
                        snippet_len=snippet_len,
                    )
                )
            else:
                positions.extend(
                    self._scan_text(
                        match,
                        query_tokens,
                        max_positions_per_file=max_positions_per_file,
                        snippet_len=snippet_len,
                    )
                )

        return positions

    def _process_document(self, document: Document) -> Document:
        """Применяет пайплайн к документу и сохраняет полученные токены."""
        document.tokens = self.pipeline.transform(document.text)
        return document

    def _aggregate_best_scores(self, scored_documents: Sequence[tuple[Document, float]]) -> Dict[Path, float]:
        """Оставляет наилучший балл для каждого файла и отбрасывает нулевые значения."""
        best: Dict[Path, float] = {}
        for doc, score in scored_documents:
            if score <= 0.0:
                continue
            if score > best.get(doc.path, 0.0):
                best[doc.path] = score
        return best

    def _scan_docx(
        self,
        match: SourceMatch,
        query_tokens: Set[str],
        *,
        max_positions_per_file: int,
        snippet_len: int,
    ) -> List[SourcePosition]:
        """Просматривает DOCX-файл и находит параграфы, пересекающиеся с запросом."""
        positions: List[SourcePosition] = []
        doc = DocxDocument(match.path)
        for idx, paragraph in enumerate(doc.paragraphs, start=1):
            if len(positions) >= max_positions_per_file:
                break
            snippet = paragraph.text.strip()
            if not snippet:
                continue
            if self._matches_query(snippet, query_tokens):
                positions.append(
                    SourcePosition(
                        path=match.path,
                        index=idx,
                        snippet=self._truncate(snippet, snippet_len),
                        score=match.score,
                        label="paragraph",
                    )
                )
        return positions

    def _scan_text(
        self,
        match: SourceMatch,
        query_tokens: Set[str],
        *,
        max_positions_per_file: int,
        snippet_len: int,
    ) -> List[SourcePosition]:
        """Анализирует текстовый файл построчно и ищет пересечение с запросом."""
        positions: List[SourcePosition] = []
        content = match.path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(content.splitlines(), start=1):
            if len(positions) >= max_positions_per_file:
                break
            snippet = line.strip()
            if not snippet:
                continue
            if self._matches_query(snippet, query_tokens):
                positions.append(
                    SourcePosition(
                        path=match.path,
                        index=idx,
                        snippet=self._truncate(snippet, snippet_len),
                        score=match.score,
                        label="line",
                    )
                )
        return positions

    def _matches_query(self, text: str, query_tokens: Set[str]) -> bool:
        """Проверяет, делит ли фрагмент хотя бы один токен с запросом."""
        tokens = set(self.pipeline.transform(text))
        return bool(tokens & query_tokens)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        """Обрезает текст до заданной длины и добавляет многоточие при необходимости."""
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "..."
