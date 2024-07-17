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
Out[3]: Country(name='Mexico', code='MEX')
```

or coordinates

```
In [4]: i.find_by_coord(49.2827, -123.1207) # Vancouver
Out[4]: Country(name='Canada', code='CAN')
```

#### Using a pre-built index

The indexes are based on https://github.com/johan/world.geo.json/blob/master/countries.geo.json
and this is the only GeoJSON source supported at the moment. Given that, you don't really
need to build indexes yourself, as there are ready to use files built by GitHub CI.

