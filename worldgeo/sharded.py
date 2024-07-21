import os.path
from multiprocessing import Pool
from typing import Dict, Optional, Tuple
from geohash import encode, _base32
from .index import Index, IndexNotFound, PREBUILT_BASE_URL, PrebuiltIndexName


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

    def add(self, gh: str, code: str):
        split, rest = self.split_geohash(gh)
        if split not in self._idx:
            self._idx[split] = Index(self.precision)
        self._idx[split].add(gh, code)

    def find_by_hash(self, gh: str) -> Optional[str]:
        split, rest = self.split_geohash(gh)
        if split not in self._idx:
            return None
        return self._idx[split].find_by_hash(gh)

    def find_by_coord(self, lat: float, lon: float) -> Optional[str]:
        gh = encode(lat, lon)
        return self.find_by_hash(gh)

    @staticmethod
    def filename(prefix: str, shard: str) -> str:
        return prefix + "_" + shard + ".idx"

    def dump(self, prefix: str):
        for shard, idx in self._idx.items():
            filename = self.filename(prefix, shard)
            idx.dump(filename)

    @staticmethod
    def _shard_loader(args: Tuple[str, str]) -> Optional[Tuple[str, Index]]:
        shard, filename = args
        try:
            idx = Index.load(filename)
            return shard, idx
        except IndexNotFound:
            return None

    @classmethod
    def load(cls, prefix: str, *, shard_split: int = 1, num_threads: int = 10):

        p = list(_base32)
        r = []

        # TODO optimize, implement as a generator
        for i in range(shard_split-1):
            for code in p:
                for suffix in _base32:
                    r.append(code+suffix)
            p = r

        args = [(shard, cls.filename(prefix, shard)) for shard in p]
        with Pool(num_threads) as pool:
            results = filter(lambda v: v, pool.map(cls._shard_loader, args))

        indexes: Dict[str, Index] = dict(results)
        first = list(indexes.values())[0]
        precision = first.precision
        inst = cls(precision, shard_split=shard_split)
        inst._idx = indexes

        return inst

    @classmethod
    def load_prebuilt(cls, index_name: PrebuiltIndexName, precision: int):
        path = os.path.join(PREBUILT_BASE_URL, index_name, "sharded", str(precision), f"{index_name}{precision}")
        return cls.load(path, shard_split=1)
