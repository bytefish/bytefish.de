title: How to host Mapbox Vector Tiles and write a .NET Tile Server
date: 2020-08-15 10:12
tags: osm, dotnet, mapbox, tiles
category: dotnet
slug: mapboxtileserver_csharp
author: Philipp Wagner
summary: This article shows how to write a Tile Server and host Vector Tiles.

Every project grows to a point it needs to support maps. With the current COVID-19 pandemic you 
are seeing maps basically everywhere. So how could we host maps ourselves without hitting Google 
Maps servers?

Some time ago I played with [baremaps] to generate Vector tiles and it gave me *a lot of ideas* for 
OpenStreetMap data and mapping in general. It is a great project and I wish [Bertil] success for his 
project.

Playing with [baremaps] has also taught me how complicated it is to design styles and how to preprocess 
OSM data for your needs. At some point I gave up, but instead of throwing away the code I wrote I adapted 
it to use the pre-built [OpenMapTiles]:

* [https://github.com/bytefish/MapboxTileServer](https://github.com/bytefish/MapboxTileServer)

[Bertil]: https://www.bertil.ch/
[baremaps]: https://github.com/baremaps/baremaps

## What we are going to build ##

In this project you will see how to acquire the data to serve tiles locally using a simple 
tile server we are going to write. The end result will display the tiles from [OpenMapTiles] 
on a website:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/mapboxtileserver_csharp/MapboxTileServer.png">
        <img src="/static/images/blog/mapboxtileserver_csharp/MapboxTileServer.png">
    </a>
</div>

## Getting the Data ##

I want to be able to host maps without using external services, but host everything locally. This means 
we'll need to get the necessary data for vector tiles, fonts and sprites first.

### Vector Tilesets ###

There is a great project called [OpenMapTiles], which has a huge range of prebuilt tilesets 
and is used by large enterprises like Siemens, Bosch or IBM. And on the upside, most of the 
available map styles expect data in the OpenMapTiles schema:

* [https://openmaptiles.com/](https://openmaptiles.com/)

I want to show a map of Germany, so I am going to download the data for Germany here:

* [https://openmaptiles.com/downloads/dataset/osm/europe/germany/#4.8/51.376/10.458](https://openmaptiles.com/downloads/dataset/osm/europe/germany/#4.8/51.376/10.458)

And that's it for the tileset.

### Fonts ###

We'll need to display all kinds of names for roads, lakes or points of interests. In the Mapbox styles all 
fonts are given in the ``text-font`` attribute. The Mapbox GL viewer expects the fonts to be served as PBF 
files. 

I have absolutely no idea how to this, but the required fonts have already been pre-built by the 
[OpenMapTiles] team at:

* [https://github.com/openmaptiles/fonts/releases/download/v1.0/v1.0.zip](https://github.com/openmaptiles/fonts/releases/download/v1.0/v1.0.zip)

I only need a small subset, so I have added the PBF fonts to the GitHub repository.

### Sprites ###

Sprites are needed for displaying icons and other kinds of images on the map. We are going to use the OSM 
Liberty style from the [maputnik] editor. You can download these Sprites from the [maputnik] repositories 
at:

* [https://github.com/maputnik/osm-liberty](https://github.com/maputnik/osm-liberty)

### Natural Earth Tiles ###

Most of the examples you find for Mapbox Vector Tiles are using a layer for the Natural Earth dataset:

> Natural Earth is a public domain map dataset available at 1:10m, 1:50m, and 1:110 million scales. Featuring tightly 
> integrated vector and raster data, with Natural Earth you can make a variety of visually pleasing, well-crafted maps 
> with cartography or GIS software.

So how can we add it to our project? There are prebuilt Tilesets kindly provided [Lukas Martinelli](https://lukasmartinelli.ch), 
and the project page states:

> Natural Earth is one of the best public domain data sets and now you can instantly use it for 
> your mapping projects by using the prerendered vector or raster tiles.

The Tiles can be downloaded from:

* [http://naturalearthtiles.lukasmartinelli.ch/](http://naturalearthtiles.lukasmartinelli.ch/)

In the example I am going to use "Natural Earth II with Shaded Relief" Raster tiles.

## Writing a Tileserver ##

### ApplicationOptions ###

We probably need to serve multiple tilesets with different MIME Types, think of Vector and Raster tiles. That's 
why we are first creating a class ``Tileset``, that's going to hold the information:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace MapboxTileServer.Options
{
    public class Tileset
    {
        /// <summary>
        /// Path to the Dataset.
        /// </summary>
        public string Filename { get; set; }

        /// <summary>
        /// The Content-Type to be served.
        /// </summary>
        public string ContentType { get; set; }
    }
}
```

Every Tileset is going to be accessed by a name, which will be passed from the Frontend to the Backend. So 
we are going to store the Tilesets in an ``IDictionary<string, Tileset>`` to provide fast lookups:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;

namespace MapboxTileServer.Options
{

    public class ApplicationOptions
    {
        public IDictionary<string, Tileset> Tilesets { get; set; }
    }
}
```

This enables us to define the ``openmaptiles`` and ``natural_earth`` layer from the previous section. We are 
adding a section ``Application``, which will be bound to the ``ApplicationOptions`` using the [Options Pattern] 
of .NET Core.

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  },
  "Application": {
    "Tilesets": {
      "openmaptiles": {
        "Filename": "G:\\Tiles\\2017-07-03_europe_germany.mbtiles",
        "ContentType": "application/vnd.mapbox-vector-tile"
      },
      "natural_earth_2_shaded_relief.raster": {
        "Filename": "G:\\Tiles\\natural_earth_2_shaded_relief.raster.mbtiles",
        "ContentType": "image/png"
      }
    }
  },
  "AllowedHosts": "*"
}
```

[Options Pattern]: https://docs.microsoft.com/en-us/aspnet/core/fundamentals/configuration/options?view=aspnetcore-3.1

### MapboxTileService: Reading the Tiles ###

The tiles are stored in the [Vector tile specification] format suggested by Mapbox. One of the most common implementations is 
the MBTiles format. According to the OpenStreetMap Wiki MBTiles ... 

> [...] is a file format for storing map tiles in a single file. It is, technically, a SQLite database.

So we are going to add the ``Microsoft.Data.Sqlite`` packages for accessing SQLite Databases and write a small ``MapboxTileService`` 
to read the data off of it. Please look into the [MBTiles Specification] for further information on how to access data.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.Options;
using Microsoft.Data.Sqlite;
using System;
using System.IO;

namespace MapboxTileServer.Services
{
    public interface IMapboxTileService
    {
        byte[] Read(Tileset tileset, int z, int x, int y);
    }

    public class MapboxTileService : IMapboxTileService
    {
        public byte[] Read(Tileset tileset, int z, int x, int y)
        {
            using (var connection = new SqliteConnection($"Data Source={tileset.Filename}"))
            {
                connection.Open();

                var command = connection.CreateCommand();

                command.CommandText = "SELECT tile_data FROM tiles WHERE zoom_level = $level AND tile_column = $column AND tile_row = $row";

                command.Parameters.AddWithValue("$level", z);
                command.Parameters.AddWithValue("$column", x);
                command.Parameters.AddWithValue("$row", ReverseY(y, z));

                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        return GetBytes(reader);
                    }
                }
            }

            return null;
        }

        private static int ReverseY(int y, int z)
        {
            return (int)(Math.Pow(2.0d, z) - 1 - y);
        }

        private static byte[] GetBytes(SqliteDataReader reader)
        {
            byte[] buffer = new byte[2048];
            
            using (MemoryStream stream = new MemoryStream())
            {
                long bytesRead = 0;
                long fieldOffset = 0;
                
                while ((bytesRead = reader.GetBytes(0, fieldOffset, buffer, 0, buffer.Length)) > 0)
                {
                    stream.Write(buffer, 0, (int)bytesRead);
                    fieldOffset += bytesRead;
                }

                return stream.ToArray();
            }
        }
    }
}
```

[MBTiles Specification]: https://github.com/mapbox/mbtiles-spec
[Vector tile specification]: https://docs.mapbox.com/vector-tiles/specification/

### TilesController: Serving the Tiles ###

What's left is serving the Tiles. We are writing a ``TilesController``, which gets the ``ApplicationOptions`` and ``MapboxTileService`` 
injected. There is a single ``HttpGet`` Endpoint, which resolves all required parameters from the the requested Route. For Mapbox 
Vector Tiles (MIME Type ``application/vnd.mapbox-vector-tile``) we need to add the ``Content-Type: gzip`` header, because this data 
has already been gzipped in the database.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.Options;
using MapboxTileServer.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace MapboxTileServer.Controllers
{
    [ApiController]
    public class TilesController : ControllerBase
    {
        private readonly ILogger<TilesController> logger;
        private readonly ApplicationOptions applicationOptions;
        private readonly IMapboxTileService mapboxTileService;

        public TilesController(ILogger<TilesController> logger, IOptions<ApplicationOptions> applicationOptions, IMapboxTileService mapboxTileService)
        {
            this.logger = logger;
            this.applicationOptions = applicationOptions.Value;
            this.mapboxTileService = mapboxTileService;
        }

        [HttpGet]
        [Route("/tiles/{tileset}/{z}/{x}/{y}")]
        public ActionResult Get([FromRoute(Name = "tileset")] string tiles, [FromRoute(Name = "z")] int z, [FromRoute(Name = "x")] int x, [FromRoute(Name = "y")] int y)
        {
            logger.LogDebug($"Requesting Tiles (tileset = {tiles}, z = {z}, x = {x}, y = {y})");
 
            if(!applicationOptions.Tilesets.TryGetValue(tiles, out Tileset tileset))
            {
                logger.LogWarning($"No Tileset available for Tileset '{tiles}'");

                return BadRequest();
            }

            var data = mapboxTileService.Read(tileset, z, x, y);
            
            if(data == null)
            {
                return Accepted();
            }

            // Mapbox Vector Tiles are already compressed, so we need to tell 
            // the client we are sending gzip Content:
            if (tileset.ContentType == Constants.MimeTypes.ApplicationMapboxVectorTile)
            {
                Response.Headers.Add("Content-Encoding", "gzip");
            }

            return new FileContentResult(data, tileset.ContentType);
        }
    }
}
```

### Getting the Style right: Setting the Tiles ###

If you are downloading the Styles from [maputnik], you are going to access remote endpoints for tiles, 
sprites and fonts. In order to load the resources from our local server, we are setting the properties 
for ``sources``, ``sprite`` and ``glyphs`` in the ``osm_liberty.json`` file:

```json
{
  "version": 8,
  "name": "OSM Liberty",
  "metadata": {
    "maputnik:license": "https://github.com/maputnik/osm-liberty/blob/gh-pages/LICENSE.md",
    "maputnik:renderer": "mbgljs",
    "openmaptiles:version": "3.x"
  },
  "sources": {
    "ne_2_hr_lc_sr": {
      "tiles": [
        "http://localhost:9000/tiles/natural_earth_2_shaded_relief.raster/{z}/{x}/{y}"
      ],
      "type": "raster",
      "tileSize": 256,
      "maxzoom": 6
    },
    "openmaptiles": {
      "type": "vector",
      "tiles": [
        "http://localhost:9000/tiles/openmaptiles/{z}/{x}/{y}"
      ],
      "minzoom": 0,
      "maxzoom": 14
    }
  },
  "sprite": "http://localhost:9000/static/sprites/osm_liberty/osm-liberty",
  "glyphs": "http://localhost:9000/static/fonts/{fontstack}/{range}.pbf",
  "layers": [
    {
      "id": "background",
      "type": "background",
      "filter": [ "all" ],
      "paint": { "background-color": "rgb(239,239,239)" }
    },
    {
      "id": "ne_2_hr_lc_sr",
      "type": "raster",
      "source": "ne_2_hr_lc_sr",
      "interactive": true,
      "layout": {
        "visibility": "visible"
      },
      "paint": {
        "raster-opacity": {
          "base": 0.5,
          "stops": [
            [
              0,
              0.6
            ],
            [
              4,
              1
            ],
            [
              8,
              0.3
            ]
          ]
        },
        "raster-contrast": 0
      },
      
      ... Original OSM Liberty Style from here ...
      
    }
  ]
}
```

### Mapbox GL JS: A minimal Frontend to display the Map ###

So how can we render the Maps served by our MapboxTileServer? We are going to use Mapbox GL JS, which is a ...

> [...] JavaScript library that uses WebGL to render interactive maps from vector tiles and Mapbox 
> styles. It is part of the Mapbox GL ecosystem, which includes Mapbox Mobile, a compatible renderer written in 
> C++ with bindings for desktop and mobile platforms.

We can include it as a ``script`` in a simple HTML file. This is heavily based on a HTML file from the [baremaps] 
repository, so I don't take much of a credit in it. It displays the Mapbox GL JS client for the full view width 
and view height of your browser, and it overlays a side bar to display features of a tile.

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Mapbox GL</title>
    <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
    <script src="https://api.mapbox.com/mapbox-gl-js/v1.12.0/mapbox-gl.js"></script>
    <link href="https://api.mapbox.com/mapbox-gl-js/v1.12.0/mapbox-gl.css" rel="stylesheet" />
    <style>
        #map {
            height: 100vh;
        }

            #map canvas {
                cursor: crosshair;
            }

        #heading {
            font-family: 'Montserrat', sans-serif;
            color: rgb(255, 255, 255);
            background: rgb(40, 40, 40);
            position: fixed;
            top: 0px;
            left: 0px;
            bottom: 0px;
            padding: 30px;
            width: 450px;
            overflow: auto;
            z-index: 9;
        }

        h1 {
            font-family: 'Roboto', sans-serif;
            margin: 0;
            padding: 0;
        }

        pre {
            font-family: 'Roboto Mono', monospace;
        }

        a, a:hover, a:visited {
            color: rgb(229, 235, 247);
        }
    </style>
</head>
<body style="margin: 0">
    <div id="map"></div>
    <div id="heading">
        <h1>MapboxTileserver</h1>
        <p>
           Click on the map to get the metadata associated with a Mapbox Vector Tile. You can learn about the Vector Tile Specification <a href="https://docs.mapbox.com/vector-tiles/specification/">here</a>.
        </p>
        <pre id='features'>
Select a feature on the map
to display its metadata.
  </pre>
    </div>
    <script>
        // Initialize the map
        var map = new mapboxgl.Map({
            container: 'map',
            style: 'http://localhost:9000/static/style/osm_liberty/osm_liberty.json',
            center: [7.628202, 51.961563],
            zoom: 14
        });

        // Recenter the map according to the location saved in the url
        if (location.hash) {
            let arr = location.hash.substr(1).split("/");
            let zoom = parseFloat(arr[0]);
            let lng = parseFloat(arr[1]);
            let lat = parseFloat(arr[2]);
            let bearing = parseFloat(arr[3]);
            let pitch = parseFloat(arr[4]);
            map.setZoom(zoom);
            map.setCenter([lng, lat]);
            map.setBearing(bearing);
            map.setPitch(pitch);
        }

        // Changes the hash of the url when the location changes
        map.on('moveend', ev => {
            location.hash = "#" + map.getZoom() + "/" + map.getCenter().lng + "/" + map.getCenter().lat + "/" + map.getBearing() + "/" + map.getPitch();
        });

        map.on('click', function (e) {
            var features = map.queryRenderedFeatures(e.point);

            document.getElementById('features').innerHTML = JSON.stringify(features.map(f => f.properties), null, 2);
        });

    </script>
</body>
</html>
```

#### What's this Overzooming? ####

Now if you look the Vector tiles generated by OpenMapTiles, they are generated down to Zoom Level 14. Often 
enough you want to zoom in even more, that's why the OpenMapTiles documentation states:

> The tiles are generated on zoom levels 1 to 14, but can be overzoomed to level 18+. Vector tiles contain 
> selection of OpenStreetMap data - following the OpenMapTiles schema, compatible with the open styles.

So how can we overzoom the tiles? Now this was a not really obvious. You first need to adjust the style and 
set the ``minzoom`` and ``maxzoom`` zoom levels for the ``openmaptiles`` tileset:

```json
{
  "sources": {
    "openmaptiles": {
      "type": "vector",
      "tiles": [
        "http://localhost:9000/tiles/openmaptiles/{z}/{x}/{y}"
      ],
      "minzoom": 0,
      "maxzoom": 14
    }
  }
}
```

And when you initialize the Mapbox GL JS client do not set any minimum or maximum zoom-level:

```javascript
var map = new mapboxgl.Map({
    container: 'map',
    style: 'http://localhost:9000/static/style/osm_liberty/osm_liberty.json',
    center: [7.628202, 51.961563],
    zoom: 14
});
```

This allows the client to overzoom the tiles and go down to ground level.

## Conclusion ##

And that's it! You now have a solid starting point to integrate [OpenMapTiles] in your projects or 
write a tile server yourself. Of course a lot of things are still missing, like Geocoding to reverse 
search for adresses. Maybe I will research it in a follow-up article.

[maputnik]: http://maputnik.github.io/
[OpenMapTiles]: https://openmaptiles.org/