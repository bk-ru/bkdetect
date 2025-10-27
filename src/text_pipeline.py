from __future__ import annotations

import re
from typing import Callable, Iterable, List

from bs4 import BeautifulSoup
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

from stemmers.porter_ru import russian_porter_stem


class TextPipeline:
    """Нормализует текст и приводит его к токенам, готовым для индексации."""

    _NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9а-яё']+", re.IGNORECASE)

    def __init__(self, language: str = "ru", use_stemming: bool = True, remove_stopwords: bool = True) -> None:
        """Настраивает параметры обработки текста и загружает необходимые ресурсы."""
        self.language = language
        self.use_stemming = use_stemming
        self.remove_stopwords = remove_stopwords

        self.stopword_set = self._load_stopwords(language) if remove_stopwords else frozenset()
        self._stemmer = self._resolve_stemmer(language) if use_stemming else None

    def transform(self, text: str) -> List[str]:
        """Полный цикл нормализации: от сырого текста до токенов."""
        normalized = self._normalize_text(text)
        tokens = self._tokenize(normalized)
        tokens = self._filter_stopwords(tokens)
        return self._stem_tokens(tokens)

    def _normalize_text(self, text: str) -> str:
        """Удаляет HTML, приводит текст к нижнему регистру и чистит символы."""
        stripped = BeautifulSoup(text, "html.parser").get_text(separator=" ")
        lowered = stripped.lower()
        return self._NON_ALPHANUMERIC_RE.sub(" ", lowered)

    def _tokenize(self, text: str) -> List[str]:
        """Разбивает строку на токены, исключая пустые элементы."""
        return [token for token in text.split() if token]

    def _filter_stopwords(self, tokens: Iterable[str]) -> List[str]:
        """Удаляет стоп-слова, если они были загружены."""
        if not self.stopword_set:
            return list(tokens)
        return [token for token in tokens if token not in self.stopword_set]

    def _stem_tokens(self, tokens: Iterable[str]) -> List[str]:
        """Применяет стеммер, если он включён, и возвращает токены."""
        if not self._stemmer:
            return list(tokens)
        return [self._stemmer(token) for token in tokens]

    def _load_stopwords(self, language: str) -> frozenset[str]:
        """Загружает список стоп-слов для выбранного языка через NLTK."""
        if language == "ru":
            corpus_name = "russian"
        elif language == "en":
            corpus_name = "english"
        else:
            return frozenset()

        try:
            words = stopwords.words(corpus_name)
        except LookupError:
            nltk.download("stopwords")
            nltk.download("punkt")
            words = stopwords.words(corpus_name)
        return frozenset(words)

    def _resolve_stemmer(self, language: str) -> Callable[[str], str]:
        """Возвращает функцию стемминга, подходящую для выбранного языка."""
        if language == "ru":
            return russian_porter_stem
        if language == "en":
            return PorterStemmer().stem
        return lambda token: token
