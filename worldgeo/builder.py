import json
import logging
import sys
import time
import requests
from logging import getLogger, Logger, StreamHandler, Formatter
from threading import Thread
from typing import Optional, Dict, Any
from queue import Queue
from shapely.geometry import shape
from argparse import ArgumentParser
from worldgeo import Index
from worldgeo.collect import collect
from worldgeo.objects import Country

DEFAULT_NUM_THREADS = 5
GEOJSON_URL = "https://github.com/johan/world.geo.json/raw/master/countries.geo.json"

log: Logger


def get_default_source() -> Dict[str, Any]:
    resp = requests.get(GEOJSON_URL)
    return resp.json()


def worker(wrk_id: int, in_queue: Queue, out_queue: Queue, max_precision: int):
    while True:
        item = in_queue.get()
        if item is None:
            break
        country, boundaries = item
        log.debug("[wrk %d] collecting geohash list for %s", wrk_id, country.name)
        t1 = time.time()
        for gh in collect(boundaries, max_precision=max_precision):
            out_queue.put((gh, country))
        t2 = time.time()
        log.debug("[wrk %d] collected geohash list for %s in %.3fs", wrk_id, country.name, t2-t1)
        in_queue.task_done()
    out_queue.put(None)
    log.debug("[wrk %d] finished", wrk_id)


def build_index(
    in_filename: Optional[str],
    out_filename: str,
    precision: int,
    *,
    country_filter: Optional[str] = None,
    num_threads: int = DEFAULT_NUM_THREADS
):

    root = Index(precision)

    if in_filename is None:
        data = get_default_source()
    else:
        with open(in_filename) as f:
            data = json.load(f)

    in_queue = Queue()
    out_queue = Queue()

    threads = []
    for i in range(num_threads):
        w_id = i + 1
        t = Thread(target=worker, name=f"wrk_{w_id}", args=(w_id, in_queue, out_queue, precision))
        t.start()
        threads.append(t)

    if country_filter:
        country_filter = country_filter.lower()

    for item in data["features"]:
        country = Country(name=item["properties"]["name"], code=item["id"])
        if country_filter and (country.code.lower() != country_filter and country.name.lower() != country_filter):
            continue
        boundaries = shape(item["geometry"])
        in_queue.put((country, boundaries))

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
    parser.add_argument("country", nargs="?", default=None, help="optional country filter")
    parser.add_argument("-i", "--input", default=None, help="geojson input filename")
    parser.add_argument("-o", "--output", required=True, help="index output filename")
    parser.add_argument("-p", "--precision", type=int, default=6, help="index maximum precision")
    parser.add_argument("-t", "--threads", type=int, default=5, help="number of threads")
    args = parser.parse_args()
    build_index(args.input, args.output, args.precision, country_filter=args.country, num_threads=args.threads)


if __name__ == "__main__":
    build()
