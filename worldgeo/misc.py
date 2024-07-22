from typing import Generator
from shapely import Polygon
from geohash import bbox, _base32


def geohash_poly(gh: str) -> Polygon:
    box = bbox(gh)
    coords = (
        (box["w"], box["n"]),
        (box["e"], box["n"]),
        (box["e"], box["s"]),
        (box["w"], box["s"]),
    )
    return Polygon(coords)


def split_geohash(gh: str) -> Generator[str, None, None]:
    for char in _base32:
        yield gh + char


def generate_possible_hashes(length: int) -> Generator[str, None, None]:
    max_value = len(_base32)
    digits = [0] * length
    while True:
        gh = "".join([_base32[i] for i in digits])
        yield gh
        upd = 0
        while upd < length:
            digits[upd] += 1
            if digits[upd] >= max_value:
                digits[upd] = 0
                upd += 1
            else:
                break
        if upd == length:
            return
