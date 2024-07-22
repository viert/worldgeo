## worldgeo

### World geohash index

A simple, easy to use python package to get a country 
by a given geohash or raw coordinates.

### Getting started

#### Installation

```commandline
pip install worldgeo
```

#### Usage

Import the `Index` class and load an index file (we'll discuss
how to get one later on)

```python
from worldgeo import Index
i = Index.load("world5.idx")
```

Now you can resolve a geohash

```
In [3]: i.find_by_hash("9smk")
Out[3]: 'MEX'
```

or coordinates

```
In [4]: i.find_by_coord(49.2827, -123.1207) # Vancouver
Out[4]: 'CAN'
```

#### Using a pre-built index

There are pre-built indexes based on https://github.com/johan/world.geo.json/blob/master/countries.geo.json
. Given that, you don't really need to build indexes yourself, as there are ready to use files built by GitHub CI.

Pre-built indexes have various precision, check out the contents of `prebuilt` folder of this repo. 
Precision 6 means accuracy up to 1.2x1.2 km, which must be enough given the source might be even less accurate. 
Since more accurate index take much more disk and memory space, you might want to use precision 4 or 5 
(39km or 5km correspondingly) as these take only a few Mb. Higher precision (7 and above) gives an index that is
too large to fit in a default github repo, thus `ShardedIndex` was introduced. `ShardedIndex` splits the data into
multiple files and can load them in parallel using `multiprocessing`.

Pre-built indexes can be loaded with a short-cut method `load_prebuilt` that takes an index name and a precision value.
Available index names are `world` and `vatsim`. The `world` one resolves to a country alpha3 code and `vatsim` resolves
to a region ICAO.

```python
from worldgeo import Index

i = Index.load_prebuilt("vatsim", 5)
print(i.find_by_hash("ez656"))
```

The code above would resolve into `LPPC-E` which represents Lisboa FIR.

#### Building a new index

In case you still want to build a more (or less) precise index, you can do so by running

```
build-geoidx -o <output filename> -p <precision> [-t <num threads>] [-m] [-s]
```

and load the resulting file later on with `Index.load(filename)`
