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
