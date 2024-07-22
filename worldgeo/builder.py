import json
import logging
import sys
import time
import requests
import os.path
from multiprocessing import Pool
from logging import getLogger, Logger, StreamHandler, Formatter
from typing import Optional, Dict, Any, Tuple, List
from queue import Queue
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from argparse import ArgumentParser
from worldgeo import Index, ShardedIndex
from worldgeo.collect import collect
from worldgeo.index import SourceLoadError, InvalidSource

DEFAULT_NUM_THREADS = 5
DEFAULT_GEOJSON_URL = "https://github.com/johan/world.geo.json/raw/master/countries.geo.json"

log: Logger


class Builder:

    src: str
    dest: str
    sharded: bool
    num_threads: int
    precision: int
    split_size: int
    mkdir: bool

    def __init__(self,
                 src: str,
                 dest: str,
                 precision: int,
                 *,
                 sharded: bool = False,
                 mkdir: bool = False,
                 num_threads: int = DEFAULT_NUM_THREADS,
                 split_size: int = 1):
        self.src = src
        self.dest = dest
        self.precision = precision
        self.sharded = sharded
        self.mkdir = mkdir
        self.num_threads = num_threads
        self.split_size = split_size

    def _load_source(self) -> Dict[str, Any]:
        use_http = self.src.startswith("http://") or self.src.startswith("https://")
        if use_http:
            log.debug(f"loading source from {self.src} via http")
            resp = requests.get(self.src)
            if resp.status_code == 404:
                raise SourceLoadError(f"source {self.src} not found")
            elif resp.status_code != 200:
                raise SourceLoadError(f"error loading index {self.src}: status code {resp.status_code}")
            return resp.json()
        else:
            if not os.path.isfile(self.src):
                raise SourceLoadError(f"index {self.src} not found")
            with open(self.src) as f:
                return json.load(f)

    def _collector(self, args: Tuple[str, BaseGeometry]) -> Tuple[str, List[str]]:
        code, boundaries = args
        ghs = list(collect(boundaries, max_precision=self.precision))
        return code, ghs

    def _build_index(self) -> ShardedIndex | Index:
        src = self._load_source()
        features = src.get("features")
        if features is None:
            raise InvalidSource("property \"features\" not found in source geojson")

        args = []
        count = 0
        failed_features = 0
        for feature in features:
            count += 1
            code = feature.get("id")
            if code is None:
                props = feature.get("properties")
                if props is None:
                    failed_features += 1
                    continue
                code = props.get("id")
                if code is None:
                    failed_features += 1
                    continue
            try:
                geom = shape(feature["geometry"])
            except:
                failed_features += 1
                continue
            args.append((code, geom))

        if failed_features > 0:
            if failed_features == count:
                raise InvalidSource("no valid features were found")
            else:
                log.warning("%d features have failed to process", failed_features)

        log.info("indexing %d features in %d threads", len(args), self.num_threads)

        with Pool(self.num_threads) as pool:
            results = pool.map(self._collector, args)

        if self.sharded:
            root = ShardedIndex(self.precision, shard_split=self.split_size)
        else:
            root = Index(self.precision)

        for res in results:
            code, ghs = res
            if ghs:
                log.debug("inserting %d geohashes for %s", len(ghs), code)
                for gh in ghs:
                    root.add(gh, code)

        return root

    def build(self) -> None:
        idx = self._build_index()
        idx.dump(self.dest, mkdir=self.mkdir)


def worker(wrk_id: int, in_queue: Queue, out_queue: Queue, max_precision: int):
    while True:
        item = in_queue.get()
        if item is None:
            break
        code, boundaries = item
        log.debug("[wrk %d] collecting geohash list for %s", wrk_id, code)
        t1 = time.time()
        for gh in collect(boundaries, max_precision=max_precision):
            out_queue.put((gh, code))
        t2 = time.time()
        log.debug("[wrk %d] collected geohash list for %s in %.3fs", wrk_id, code, t2-t1)
        in_queue.task_done()
    out_queue.put(None)
    log.debug("[wrk %d] finished", wrk_id)


def build_index(
    in_filename: Optional[str],
    out_filename: str,
    precision: int,
    *,
    sharded: bool,
    shard_split: int,
    country_filter: Optional[str] = None,
    num_threads: int = DEFAULT_NUM_THREADS,
):
    if sharded:
        root = ShardedIndex(precision, shard_split=shard_split)
    else:
        root = Index(precision)

    with open(in_filename) as f:
        data = json.load(f)

    in_queue = Queue()
    out_queue = Queue()

    if country_filter:
        country_filter = country_filter.lower()

    for item in data["features"]:
        country_name = item['properties']['name']
        country_code = item["id"]
        if country_filter and (
                country_name.lower() != country_filter and
                country_code.lower() != country_filter
        ):
            continue
        boundaries = shape(item["geometry"])
        in_queue.put((country_code, boundaries))

    for _ in range(num_threads):
        in_queue.put(None)

    wrk_alive = num_threads

    while True:
        item = out_queue.get()
        if item is None:
            wrk_alive -= 1
            if wrk_alive == 0:
                break
            continue
        gh, country = item
        root.add(gh, country)

    log.info("writing index to %s", out_filename)
    root.dump(out_filename)


def build():
    global log
    log = getLogger("indexer")
    log.setLevel(logging.DEBUG)
    for handler in log.handlers:
        log.removeHandler(handler)
    handler = StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    log.addHandler(handler)

    parser = ArgumentParser()
    parser.add_argument("-i", "--input", default=None, help="geojson input filename")
    parser.add_argument("-o", "--output", required=True, help="index output filename "
                                                              "(or prefix for sharded indexes)")
    parser.add_argument("-p", "--precision", type=int, default=6, help="index maximum precision")
    parser.add_argument("-t", "--threads", type=int, default=5, help="number of threads")
    parser.add_argument("-s", "--sharded", default=False, action="store_true",
                        help="build sharded index")
    parser.add_argument("--split-size", type=int, default=1,
                        help="number of symbols to shard (sharded index only)")
    parser.add_argument("-m", "--mkdir", action="store_true", default=False,
                        help="automatically create output folders")
    args = parser.parse_args()

    builder = Builder(
        args.input or DEFAULT_GEOJSON_URL,
        args.output,
        args.precision,
        num_threads=args.threads,
        sharded=args.sharded,
        split_size=args.split_size,
        mkdir=args.mkdir,
    )
    builder.build()


if __name__ == "__main__":
    build()
