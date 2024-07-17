import os.path

import requests
from typing import Optional, Self
from io import StringIO
from geohash import encode
from .objects import Country


PREBUILT_BASE_URL = "https://github.com/viert/worldgeo/raw/main/world"


class Index:
    precision: int
    _src: Optional[str]
    _countries: dict[str, Country]
    _index: dict[str, str]

    def __init__(self, precision: int):
        self.precision = precision
        self._countries = {}
        self._index = {}
        self._src = None

    def add(self, gh: str, country: Country):
        if country.code not in self._countries:
            self._countries[country.code] = country
        self._index[gh] = country.code

    def find_by_hash(self, gh: str) -> Optional[Country]:
        for i in range(self.precision, 0, -1):
            key = gh[:i]
            if key in self._index:
                return self._countries[self._index[key]]
        return None

    def find_by_coord(self, lat: float, lon: float) -> Optional[Country]:
        gh = encode(lat, lon)
        return self.find_by_hash(gh)

    def dump(self, filename: str):
        with open(filename, "w") as f:
            f.write(f"P {self.precision}\n")
            for code, country in self._countries.items():
                f.write(f"C {code} {country.name}\n")
            for gh, code in self._index.items():
                f.write(f"G {gh} {code}\n")

    @classmethod
    def load_default(cls, precision: int) -> Self:
        path = os.path.join(PREBUILT_BASE_URL, f"world{precision}.idx")
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
            f = StringIO(resp.text)
        else:
            f = open(path)

        precision = None
        countries = {}
        index = {}

        for line in f:
            line = line.strip()
            tokens = line.split(" ", 2)

            match tokens[0]:
                case "P":
                    precision = int(tokens[1])
                case "C":
                    countries[tokens[1]] = Country(name=tokens[2], code=tokens[1])
                case "G":
                    index[tokens[1]] = tokens[2]
        f.close()

        if precision is None:
            raise RuntimeError("file is corrupted, precision cannot be found")

        inst = cls(precision)
        inst._src = path
        inst._index = index
        inst._countries = countries

        return inst

    def __repr__(self) -> str:
        source = f"\"{self._src}\"" if self._src else None
        return f"<Index source={source} precision={self.precision}>"
