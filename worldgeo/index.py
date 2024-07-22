import os.path
import requests
from typing import Optional, Self, Literal
from io import StringIO
from geohash import encode
from collections import defaultdict

PREBUILT_BASE_URL = "https://github.com/viert/worldgeo/raw/main/prebuilt"
PrebuiltIndexName = Literal["world"]


class IndexLoadError(Exception):
    pass


class IndexNotFound(Exception):
    pass


class SourceLoadError(Exception):
    pass


class InvalidSource(Exception):
    pass


class Index:
    precision: int
    _src: Optional[str]
    _index: dict[str, str]

    def __init__(self, precision: int):
        self.precision = precision
        self._index = {}
        self._src = None

    def add(self, gh: str, code: str):
        self._index[gh] = code

    def find_by_hash(self, gh: str) -> Optional[str]:
        for i in range(self.precision, 0, -1):
            key = gh[:i]
            if key in self._index:
                return self._index[key]
        return None

    def find_by_coord(self, lat: float, lon: float) -> Optional[str]:
        gh = encode(lat, lon)
        return self.find_by_hash(gh)

    def dump(self, filename: str, *, mkdir: bool = False):
        dmp = defaultdict(list)

        for gh, code in self._index.items():
            dmp[code].append(gh)

        if mkdir:
            dirname = os.path.dirname(filename)
            os.makedirs(dirname, exist_ok=True)

        with open(filename, "w") as f:
            f.write(f"P {self.precision}\n")
            for code, ghs in dmp.items():
                hashes = ":".join(ghs)
                f.write(f"G {code} {hashes}\n")

    @classmethod
    def load_prebuilt(cls, index_name: PrebuiltIndexName, precision: int) -> Self:
        path = os.path.join(PREBUILT_BASE_URL, index_name, f"world{precision}.idx")
        return cls.load(path)

    @classmethod
    def load(cls, path: str) -> Self:
        """
        Loads index from a file or HTTP(S) URL
        :param path: filename or HTTP url
        :return:
        """
        use_http = path.startswith("http://") or path.startswith("https://")
        if use_http:
            resp = requests.get(path)
            if resp.status_code == 404:
                raise IndexNotFound(f"index {path} not found")
            elif resp.status_code != 200:
                raise IndexLoadError(f"error loading index {path}: status code {resp.status_code}")
            f = StringIO(resp.text)
        else:
            if not os.path.isfile(path):
                raise IndexNotFound(f"index {path} not found")
            try:
                f = open(path)
            except EnvironmentError as e:
                raise IndexLoadError(f"error loading index {path}: {e}")

        precision = None
        index = {}

        for line in f:
            line = line.strip()
            tokens = line.split(" ", 2)

            match tokens[0]:
                case "P":
                    precision = int(tokens[1])
                case "G":
                    code = tokens[1]
                    ghs = tokens[2].split(":")
                    for gh in ghs:
                        index[gh] = code
        f.close()

        if precision is None:
            raise IndexLoadError("file is corrupted, precision cannot be found")

        inst = cls(precision)
        inst._src = path
        inst._index = index

        return inst

    def __repr__(self) -> str:
        source = f"\"{self._src}\"" if self._src else None
        return f"<Index source={source} precision={self.precision}>"
