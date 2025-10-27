# Взято с https://gist.github.com/Kein1945/9111512
# -*- coding: utf-8 -*-
# Портирован с Java по мотивам http://www.algorithmist.ru/2010/12/porter-stemmer-russian.html
from __future__ import annotations

import re
from functools import lru_cache

__all__ = ["russian_porter_stem"]


class _PorterRU:
    _PERFECTIVEGROUND = re.compile(
        r"((ив|ивши|ившись|ыв|ывши|ывшись)|((?<=[ая])(в|вши|вшись)))$"
    )
    _REFLEXIVE = re.compile(r"(с[яь])$")
    _ADJECTIVE = re.compile(
        r"(ее|ие|ые|ое|ими|ыми|ей|ий|ый|ой|ем|им|ым|ом|его|ого|ему|ому|их|ых|ую|юю|ая|яя|ою|ею)$"
    )
    _PARTICIPLE = re.compile(r"((ивш|ывш|ующ)|((?<=[ая])(ем|нн|вш|ющ|щ)))$")
    _VERB = re.compile(
        r"((ила|ыла|ена|ейте|уйте|ите|или|ыли|ей|уй|ил|ыл|им|ым|ен|ило|ыло|ено|ят|ует|уют|ит|ыт|ены|ить|ыть|ишь|ую|ю)|((?<=[ая])(ла|на|ете|йте|ли|й|л|ем|н|ло|но|ет|ют|ны|ть|ешь|нно)))$"
    )
    _NOUN = re.compile(
        r"(а|ев|ов|ие|ье|е|иями|ями|ами|еи|ии|и|ией|ей|ой|ий|й|иям|ям|ием|ем|ам|ом|о|у|ах|иях|ях|ы|ь|ию|ью|ю|ия|ья|я)$"
    )
    _RVRE = re.compile(r"^(.*?[аеиоуыэюя])(.*)$")
    _DERIVATIONAL = re.compile(r".*[^аеиоуыэюя]+[аеиоуыэюя].*ость?$")
    _DER = re.compile(r"ость?$")
    _SUPERLATIVE = re.compile(r"(ейше|ейш)$")
    _I = re.compile(r"и$")
    _P = re.compile(r"ь$")
    _NN = re.compile(r"нн$")

    def __init__(self) -> None:
        pass  # Ничего инициализировать не нужно

    @lru_cache(maxsize=50_000)
    def stem(self, word: str) -> str:
        word = word.casefold().replace("ё", "е")
        m = self._RVRE.match(word)
        if not m:
            return word

        pre, rv = m.groups()

        temp = self._PERFECTIVEGROUND.sub("", rv, 1)
        if temp == rv:
            rv = self._REFLEXIVE.sub("", rv, 1)
            temp = self._ADJECTIVE.sub("", rv, 1)
            if temp != rv:
                rv = temp
                rv = self._PARTICIPLE.sub("", rv, 1)
            else:
                temp = self._VERB.sub("", rv, 1)
                if temp == rv:
                    rv = self._NOUN.sub("", rv, 1)
                else:
                    rv = temp
        else:
            rv = temp

        rv = self._I.sub("", rv, 1)

        if self._DERIVATIONAL.match(rv):
            rv = self._DER.sub("", rv, 1)

        temp = self._P.sub("", rv, 1)
        if temp == rv:
            rv = self._SUPERLATIVE.sub("", rv, 1)
            rv = self._NN.sub("н", rv, 1)
        else:
            rv = temp

        return pre + rv


# Экземпляр стеммера (для повторного использования)
_STEMMER = _PorterRU()


def russian_porter_stem(token: str) -> str:
    """Функция-обёртка с кэшем на 50_000 слов."""
    return _STEMMER.stem(token)
