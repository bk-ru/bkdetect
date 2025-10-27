from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from documents import Document


class TfidfIndexer:
    """Инкрементально строит TF-IDF-подобный индекс на базе hashing vectorizer."""

    def __init__(self, n_features: int = 2 ** 20) -> None:
        """Создаёт векторизатор и подготавливает хранилище документов."""
        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            analyzer="word",
            tokenizer=lambda text: text.split(),
            preprocessor=None,
            lowercase=False,
        )
        self.matrix: Optional[csr_matrix] = None
        self.doc_index: List[Document] = []

    def partial_fit(self, docs_chunk: Sequence[Document]) -> None:
        """Добавляет новую порцию документов в индекс."""
        token_texts = [" ".join(document.tokens) for document in docs_chunk if document.tokens]
        if not token_texts:
            return

        matrix = self.vectorizer.transform(token_texts)
        self.matrix = matrix if self.matrix is None else vstack([self.matrix, matrix])
        self.doc_index.extend(docs_chunk)

    def query(self, tokens: Sequence[str], top_k: Optional[int] = 5) -> List[Tuple[Document, float]]:
        """Возвращает список документов с оценкой схожести относительно запроса."""
        if self.matrix is None or not self.doc_index:
            return []

        query_text = " ".join(tokens)
        query_vector = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vector, self.matrix)[0]
        ranked = sorted(zip(self.doc_index, similarities), key=lambda item: item[1], reverse=True)

        if top_k is None or top_k >= len(ranked):
            return ranked
        return ranked[:top_k]
