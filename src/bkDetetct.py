from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Sequence

from source_finder import SourceFinder


class LocalizedArgumentParser(argparse.ArgumentParser):
    """Парсер аргументов, выводящий сообщения об ошибках на русском языке."""

    def format_usage(self) -> str:  # type: ignore[override]
        usage = super().format_usage()
        return usage.replace("usage:", "Использование:", 1)

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        translated = self._translate_error(message)
        self.exit(2, f"{self.prog}: ошибка: {translated}\n")

    @staticmethod
    def _translate_error(message: str) -> str:
        if message.startswith("the following arguments are required: "):
            missing = message.split(": ", 1)[1]
            return f"требуется указать аргументы: {missing}"
        return message


def parse_args(args: Sequence[str]) -> argparse.Namespace:
    """Создаёт парсер аргументов командной строки и разбирает входные параметры."""
    parser = LocalizedArgumentParser(
        prog="bkDetetct",
        description="Поиск документов-источников и их совпадающих фрагментов.",
        usage="bkDetetct [опции] <путь_к_документам> <файл_с_запросом>",
    )
    parser.add_argument("documents", type=Path, help="Путь к каталогу или отдельному документу для индексации.")
    parser.add_argument("query", type=Path, help="Файл с текстом запроса.")
    parser.add_argument("--language", choices=["ru", "en"], default="ru", help="Язык текста для нормализации.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Размер порции документов при обработке.")
    parser.add_argument("--top-k", type=int, default=5, help="Количество документов, выводимых в списке лидеров.")
    parser.add_argument(
        "--max-positions",
        type=int,
        default=2,
        help="Максимум найденных фрагментов на один файл.",
    )
    parser.add_argument("--snippet-len", type=int, default=200, help="Максимальная длина выводимого фрагмента.")
    parser.add_argument("--no-stemming", action="store_true", help="Отключить стемминг при обработке текста.")
    parser.add_argument("--keep-stopwords", action="store_true", help="Не удалять стоп-слова.")
    return parser.parse_args(args)


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа CLI: строит индекс, ищет совпадения и выводит отчёт на русском языке."""
    args = parse_args(sys.argv[1:] if argv is None else argv)

    total_start = time.time()

    finder = SourceFinder.from_path(
        args.documents,
        language=args.language,
        use_stemming=not args.no_stemming,
        remove_stopwords=not args.keep_stopwords,
        chunk_size=args.chunk_size,
    )

    print("Строим индекс...")
    build_start = time.time()
    finder.build_index()
    build_time = time.time() - build_start
    print(f"Индекс построен за {build_time:.2f} с\n")

    query_text = args.query.read_text(encoding="utf-8", errors="ignore")

    search_start = time.time()
    matches = finder.find_sources(query_text, top_k=args.top_k)
    search_time = time.time() - search_start
    if not matches:
        print(f"Похожие источники не найдены (поиск занял {search_time:.2f} с).")
        total_time = time.time() - total_start
        print(f"Общее время работы: {total_time:.2f} с")
        return 0

    print("Лучшие совпадения:")
    for match in matches:
        print(f"{match.path.name} - оценка: {match.score:.4f}")
    print(f"Поиск источников занял {search_time:.2f} с\n")

    positions_start = time.time()
    positions = finder.locate_source_positions(
        query_text,
        top_k=args.top_k,
        max_positions_per_file=args.max_positions,
        snippet_len=args.snippet_len,
    )
    positions_time = time.time() - positions_start
    if not positions:
        print(f"Совпадающих фрагментов не обнаружено (анализ занял {positions_time:.2f} с).")
        total_time = time.time() - total_start
        print(f"Общее время работы: {total_time:.2f} с")
        return 0

    print("Совпадающие фрагменты:")
    for position in positions:
        print(
            f"{position.path.name} - {position.label} {position.index}: "
            f"{position.snippet} [оценка: {position.score:.4f}]"
        )
    print(f"Анализ фрагментов занял {positions_time:.2f} с\n")

    total_time = time.time() - total_start
    print(f"Общее время работы: {total_time:.2f} с")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
