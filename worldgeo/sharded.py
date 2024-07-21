import os.path
from typing import Dict, Optional, Tuple
from pycountry.db import Country
from geohash import encode, _base32
from .index import Index


class ShardedIndex:
    precision: int
    _split: int
    _idx: Dict[str, Index]

    def __init__(self, precision: int, *, shard_split: int = 1):
        self.precision = precision
        self._split = shard_split
        self._idx = {}

    def split_geohash(self, gh: str) -> Tuple[str, str]:
        return gh[:self._split], gh[self._split:]

    def add(self, gh: str, country: Country):
        split, rest = self.split_geohash(gh)
        if split not in self._idx:
            self._idx[split] = Index(self.precision)
        self._idx[split].add(gh, country)

    def find_by_hash(self, gh: str) -> Optional[Country]:
        split, rest = self.split_geohash(gh)
        if split not in self._idx:
            return None
        return self._idx[split].find_by_hash(gh)

    def find_by_coord(self, lat: float, lon: float) -> Optional[Country]:
        gh = encode(lat, lon)
        return self.find_by_hash(gh)

    @staticmethod
    def filename(prefix: str, shard: str) -> str:
        return prefix + "_" + shard + ".idx"

    def dump(self, prefix: str):
        for shard, idx in self._idx.items():
            filename = self.filename(prefix, shard)
            idx.dump(filename)

    @classmethod
    def load(cls, prefix: str, shard_split: int = 1):
        p = list(_base32)
        r = []
        for i in range(shard_split-1):
            for code in p:
                for suffix in _base32:
                    r.append(code+suffix)
            p = r

        indexes = {}
        for shard in p:
            filename = cls.filename(prefix, shard)
            if os.path.isfile(filename):
                indexes[shard] = Index.load(filename)
        first = list(indexes.values())[0]
        precision = first.precision
        inst = cls(precision, shard_split=shard_split)
        inst._idx = indexes
        return inst
