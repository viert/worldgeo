import json
import shapely.geometry
from geohash import _base32
from collections import deque
from typing import Optional, Generator
from .misc import geohash_poly, split_geohash


def load_country(code: str) -> Optional[shapely.geometry.base.BaseGeometry]:
    with open("countries.geojson") as f:
        data = json.load(f)

    for item in data["features"]:
        if item["id"] == code or item["properties"]["name"] == code:
            return shapely.geometry.shape(item["geometry"])
    return None


def collect(shape: shapely.geometry.base.BaseGeometry, *, max_precision: int = 5) -> Generator[str, None, None]:
    queue = deque(list(_base32))

    while queue:
        gh = queue.pop()
        poly = geohash_poly(gh)
        if poly.intersects(shape):
            if shape.contains(poly):
                yield gh
            elif len(gh) < max_precision:
                for sub_gh in split_geohash(gh):
                    queue.append(sub_gh)
