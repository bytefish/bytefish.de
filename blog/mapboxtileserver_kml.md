title: Adding KML to the MapboxTileServer and Vue.js Client
date: 2020-08-28 10:32
tags: osm, dotnet, mapbox, tiles
category: dotnet
slug: mapboxtileserver_kml
author: Philipp Wagner
summary: This article shows how to add KML to the MapboxTileServer and Vue.js project.

Google knows what I search for. I have all my mails stored on Google Servers. And when I was 
in China my phone was cut off of all Google services and... it couldn't resolve any of my 
contacts stored in Google Mail.

That made me realize: I probably need a little bit of a backup plan.

Why does it matter here? Because I also track myself with Google Maps!

I want my [Pendlerpauschale]!

## What we are going to build ##

In the last post I have shown how to integrate the Mapbox GL JS client in a Vue.js application. So 
far we are able to display the tiles, markers and lines. Now that we have a solid base, let's add 
some features.

You are probably also tracking yourself using a Smartwatch, Google Maps or an app of your choice. And 
often enough you want to display where you have been. After all it should also be your data, because 
you have collected it.

Google Maps makes it possible to export a day as KML, which ...

> ... is a file format used to display geographic data in an Earth browser such as Google 
> Earth. KML uses a tag-based structure with nested elements and attributes and is based on 
> the XML standard. All tags are case-sensitive and must appear exactly as they are listed 
> in the KML Reference. The Reference indicates which tags are optional. Within a given element, 
> tags must appear in the order shown in the Reference. ([Source])


So let's add a way to plot KML data in our Vue.js application.

At the end of the tutorial we are able to overlay KML Polygons, Points and Lines in our Vue.js app, like 
this:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/mapboxtileserver_kml/MuensterDistrictsOutline.png">
        <img src="/static/images/blog/mapboxtileserver_kml/MuensterDistrictsOutline.png">
    </a>
</div>

[Pendlerpauschale]: https://de.wikipedia.org/wiki/Entfernungspauschale
[Source]: https://developers.google.com/kml/documentation/kml_tut


## Running the example ##

The .NET Tile Server can be found in its repository at:

* [https://github.com/bytefish/MapboxTileServer](https://github.com/bytefish/MapboxTileServer)

### Starting the Server ###

You can start it by running the ``docker-compose`` command in the folder [Docker folder]:

```
docker-compose up --detach --no-deps --build
```

[Docker folder]: https://github.com/bytefish/MapboxTileServer/tree/master/Docker

### Configuring the Server ###

The Backend is configured to load the OpenMapTiles from the file ``/Tiles/2017-07-03_europe_germany.mbtiles``, which 
you can configure to any other filename by changing the ``appsettings.json`` of the Server:

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
    "SchemaDirectory": "/static/schemas",
    "Photon": {
      "ApiUrl": "http://localhost:2322/api"
    },
    "Tilesets": {
      "openmaptiles": {
        "Filename": "/Tiles/2017-07-03_europe_germany.mbtiles",
        "ContentType": "application/vnd.mapbox-vector-tile"
      },
      "natural_earth_2_shaded_relief.raster": {
        "Filename": "/Tiles/natural_earth_2_shaded_relief.raster.mbtiles",
        "ContentType": "image/png"
      }
    }
  },
  "AllowedHosts": "*"
}
```

The ``/Tiles`` volume is mounted in the ``docker-compose.yaml``, you might configure it:

```yaml
version: '3.0'
services:
  mapbox_tileserver:
    container_name: mapbox_tileserver
    build: 
        context: ../MapboxTileServer
        dockerfile: ../Docker/mapbox_tileserver/Dockerfile
    environment:
      - ASPNETCORE_ENVIRONMENT=Linux
    volumes:
      - G:/Tiles:/Tiles
    ports:
      - 9000:9000
```

## Starting with the Vue Components ##

### Adding a MapboxLayer component to Vue.js ###

The Mapbox GL JS library doesn't understand KML out-of-the box, but it has a great GeoJSON support. So the 
plan is to upload a KML file from the application, convert it to GeoJSON and display it using our Vue.js 
component. 

The properties for the component are:

* ``map``
    * The Mapbox GL JS reference we are layering the GeoJSON on.
* ``id``
    * A unique identifier for sources and layers in the component.
* ``geojson``
    * The GeoJSON object we are going to display.

The documentation has a lot of GeoJSON examples we can learn from, like ...

* [https://docs.mapbox.com/mapbox-gl-js/example/multiple-geometries/](https://docs.mapbox.com/mapbox-gl-js/example/multiple-geometries/)
* [https://docs.mapbox.com/mapbox-gl-js/example/data-driven-circle-colors/](https://docs.mapbox.com/mapbox-gl-js/example/data-driven-circle-colors/)

And in the Style Specification we can learn the properties for all layers available:

* [https://docs.mapbox.com/mapbox-gl-js/style-spec/layers/](https://docs.mapbox.com/mapbox-gl-js/style-spec/layers/)

So I came up with the following Vue.js component:

```javascript
<script>
export default {
  props: {
    map: {
      type: Object,
      required: true
    },
    id: {
      type: String,
      required: true
    },
    geojson: {
      type: Object,
      required: true
    }
  },
  mounted() {
    this.map.addSource(`geojson_${this.id}`, {
      type: 'geojson',
      data: this.geojson
    });

    this.map.addLayer({
      id: `geojson_polygons_${this.id}`,
      type: 'fill',
      source: `geojson_${this.id}`,
      paint: {
        'fill-outline-color': ['case', ['has', 'stroke'], ['get', 'stroke'], '#088'],
        'fill-color': ['case', ['has', 'fill'], ['get', 'fill'], '#088'],
        'fill-opacity': ['case', ['has', 'fill-opacity'], ['get', 'fill-opacity'], 0.8]
      },
      filter: ['==', '$type', 'Polygon']
    });

    this.map.addLayer({
      id: `geojson_polygons_lines_${this.id}`,
      type: 'line',
      source: `geojson_${this.id}`,
      paint: {
        'line-width': 1,
        'line-color': ['case', ['has', 'stroke'], ['get', 'stroke'], '#088']      },
      filter: ['==', '$type', 'Polygon']
    });

    this.map.addLayer({
      id: `geojson_points_${this.id}`,
      type: 'circle',
      source: `geojson_${this.id}`,
      paint: {
        'circle-radius': ['case', ['has', 'circle-radius'], ['get', 'circle-radius'], 6],
        'circle-color': ['case', ['has', 'circle-color'], ['get', 'circle-color'], '#088']
      },
      filter: ['==', '$type', 'Point']
    });

    this.map.addLayer({
      id: `geojson_lines_${this.id}`,
      type: 'line',
      source: `geojson_${this.id}`,
      paint: {
        'line-width': 3,
        'line-color': ['case', ['has', 'color'], ['get', 'color'], '#088']
      },
      filter: ['==', '$type', 'LineString']
    });
  },
  render() {}
};
</script>
```

In the ``index.js`` we are exporting it:

```javascript
// [...]
export { default as MapboxLayer } from '@/components/MapboxLayer.vue';
// [...]
```

And that's it!

### A Button for the File Upload ###

We now need a way to upload files. I thought a Floating Action Button (FAB) would be a nice addition, and there is 
a great tutorial how to create a Material Design Button here:

* [http://materialdesignblog.com/creating-a-simple-material-design-action-button-with-css/](http://materialdesignblog.com/creating-a-simple-material-design-action-button-with-css/)

This can be easily translated into a Vue.js component:

```javascript
<template>
  <div class="fab" @click="$emit('click')">+</div>
</template>

<script>
export default {
  name: 'FloatingActionButton',
  data() {
    return {};
  }
};
</script>

<style>
.fab {
  width: 48px;
  height: 48px;
  background-color: red;
  border-radius: 50%;
  box-shadow: 0 6px 10px 0 #666;
  transition: all 0.1s ease-in-out;

  font-size: 24px;
  color: white;
  text-align: center;
  line-height: 48px;

  position: fixed;
  right: 25px;
  bottom: 25px;
  cursor: pointer;
}

.fab:hover {
  box-shadow: 0 6px 14px 0 #666;
  transform: scale(1.05);
}
</style>
```

Again in the ``index.js`` we are exporting the Button:

```javascript
// [...]
export { default as FloatingActionButton } from '@/components/FloatingActionButton.vue';
// [...]
```

## Converting from KML to GeoJSON in the Backend ##


### The /kml/toGeoJson Endpoint ###

It starts by creating a new endpoint for ``/kml/toGeoJson`` for converting from KML to GeoJSON. Maybe a different resource 
would be more RESTful, but I don't overthink it. In the Controller, we are injecting the ``IKmlConverterService``, which 
handles the conversion.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.Extensions;
using MapboxTileServer.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using System.Threading;
using System.Threading.Tasks;

namespace MapboxTileServer.Controllers
{
    [ApiController]
    public class KmlController : ControllerBase
    {
        private readonly ILogger<KmlController> logger;
        private readonly IKmlConverterService kmlConverterService;

        public KmlController(ILogger<KmlController> logger, IKmlConverterService kmlConverterService)
        {
            this.logger = logger;
            this.kmlConverterService = kmlConverterService;
        }

        [HttpPost]
        [Route("/kml/toGeoJson")]
        public async Task<IActionResult> KmlToGeoJson([FromForm(Name = "file")] IFormFile file, CancellationToken cancellationToken)
        {
            logger.LogDebug($"Uploaded a KML File ...");

            if (file == null)
            {
                return BadRequest();
            }

            var xml = await file.ReadAsStringAsync(); ;

            if (!kmlConverterService.ToGeoJson(xml, out string json))
            {
                return BadRequest();
            }

            return Content(json, "application/json");
        }

    }
}
```

### The Actual Conversion ###

The ``IKmlConverterService`` has a single method ``IKmlConverterService#ToGeoJson`` for now. This method calls the 
``GeoJsonConverter``, which we have to implemented for getting the JSON data from the XML file.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.GeoJson;
using Microsoft.Extensions.Logging;
using System;

namespace MapboxTileServer.Services
{
    public interface IKmlConverterService
    {
        bool ToGeoJson(string xml, out string json);
    }

    public class KmlConverterService : IKmlConverterService
    {
        private readonly ILogger<KmlConverterService> logger;

        public KmlConverterService(ILogger<KmlConverterService> logger)
        {
            this.logger = logger;
        }

        public bool ToGeoJson(string xml, out string json)
        {
            json = null;

            try
            {
                json = GeoJsonConverter.FromKml(xml);

                return true;
            } 
            catch(Exception e)
            {
                logger.LogError(e, "Failed to convert Kml to GeoJson");

                return false;
            }
        }
    }
}
```

For the KML <-> GeoJSON conversion I started by looking at existing .NET projects. You probably think a lot of projects exist for such 
a task, but most of the projects I found have been abandoned or aren't compatible to .NET Core. Some took additional dependencies on 
Newtonsoft.JSON, which would be OK in a real project... but for this I don't want to add more and more dependencies. 

After all it's also a good learning experience. So I downloaded the KML Schema and had a look, if I can generate the Contracts and have 
a simple way to iterate through the document and build the GeoJSON from it. Long story short: Frustrated I gave up after some hours...

Then I found a JavaScript library called ``toGeoJson``, which has originally been developed by Mapbox Employees and is now maintained 
by [Tom MacWright (@tmcw)]:

* [https://github.com/tmcw/togeojson](https://github.com/tmcw/togeojson)

I have then translated the JavaScript implementation to C\# using the ``XDocument`` and ``XElement`` abstractions. It would be a lie 
to say this was straightforward... Anyway! The C\# version of ``toGeoJson`` can be found in the ``GeoJsonConverter`` class:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Xml.Linq;
using System.Xml.XPath;
using MapboxTileServer.GeoJson.Model;

namespace MapboxTileServer.GeoJson
{
    /// <summary>
    /// This is a shameless copy from: https://github.com/tmcw/togeojson/blob/master/lib/kml.js, so there is 
    /// no need for taking additional dependencies on third-party libraries. Updates to kml.js should be 
    /// reflected here.
    /// 
    /// The Object Model is intentionally ugly (no abstract classes, no interfaces), because this would make 
    /// Deserialization with .NET Core System.Text.Json complicated or impossible, see the Open Issue at:
    /// https://github.com/dotnet/runtime/issues/30083.
    /// </summary>
    public partial class GeoJsonConverter
    {
        private static readonly XNamespace Kml = XNamespace.Get("http://www.opengis.net/kml/2.2");
        private static readonly XNamespace Ext = XNamespace.Get("http://www.google.com/kml/ext/2.2");

        private static readonly XName[] Geotypes = new[] 
        {
            XName.Get("Polygon", Kml.NamespaceName),
            XName.Get("LineString", Kml.NamespaceName),
            XName.Get("Point", Kml.NamespaceName),
            XName.Get("Track", Kml.NamespaceName),
            XName.Get("Track", Ext.NamespaceName)
        };


        public static string FromKml(string xml)
        {
            var root = XDocument.Parse(xml);

            return FromKml(root);
        }
    }
}
```

At the end we hook the Service in the ``Startup``:

```csharp
private void RegisterApplicationServices(IServiceCollection services)
{
    // ...
    services.AddSingleton<IKmlConverterService, KmlConverterService>();
}
```

And that's it for the Backend!

## Extending the Home.vue ##

So we start by adding the ``FloatingActionButton`` and ``MapboxLayer`` to the ``Home.vue`` view:

```html
<template>
  <div id="home">
    <Search id="search" :items="searchResults" @input="search" @selected="onItemSelected" />
    <FloatingActionButton id="fab" @click="onFloatingActionButtonClicked" />
    <MapboxLoader id="map" v-bind="mapOptions">
      <template slot-scope="{ map }">
        <MapboxMarker v-for="marker in markers" :key="marker.id" :marker="marker" :map="map" />
        <MapboxLine v-for="line in lines" :id="line.id" :key="line.id" :map="map" :color.sync="line.color" :path.sync="line.path" />
        <MapboxLayer v-for="layer in layers" :id="layer.id" :key="layer.id" :map="map" :geojson="layer.geojson" />
      </template>
    </MapboxLoader>
    <input ref="file" type="file" style="display: none;" @change="handleFileUpload" />
  </div>
</template>
```

For the KML file upload a hidden ``<input>`` has been added, which calls a ``handleFileUpload`` on change. In the 
script, we are first importing the new components, implement the method handling the Floating Action Button click 
and the callback ``handleFileUpload``.

```

export default {
  name: 'Home',
  components: {
    // ...
    FloatingActionButton,
    MapboxLayer
  },
  data: function () {
    return {
      // ...
      layers: [],
    };
  },
  mounted: function () {
    this.addLine(LINE_WALK_THROUGH_MUENSTER);
    this.addMarker(MARKER_MUENSTER_CITY_CENTER);
  },
  methods: {
    onFloatingActionButtonClicked() {
      this.$refs.file.click();
    },
    async handleFileUpload(event) {
      var result = await kmlToGeoJsonAsync('http://localhost:9000/kml/toGeoJson', event.target.files[0]);

      this.addLayer({
        geojson: result
      });
    },
  },
  /...
}
```

The ``kmlToGeoJsonAsync`` method just posts the first file selected by the ``<input>`` to the Backend:

```
export async function kmlToGeoJsonAsync(url, file) {
  var formData = new FormData();

  formData.append('file', file);

  var response = await fetch(url, {
    method: 'POST',
    body: formData
  });

  return await response.json();
}
```

Every ``id`` needs to be unique for both Vue.js and Mapbox, so layers and markers don't share the same id's for example. That's 
why we are also assigning a unique identifier for each layer, when adding it to the array of ``layers`` to be displayed by our 
component:

```
export default {
  name: 'Home',
  // ...
  methods: {
    addLayer(layer) {
      var layer_id = this.getLastLayerId() + 1;

      this.layers.push({
        layer_id: layer_id,
        id: `Layer_${layer_id}`,
        ...layer
      });
    },
    getLastLayerId: function () {
      if (isNullOrUndefined(this.layers)) {
        return 0;
      }

      if (this.layers.length == 0) {
        return 0;
      }

      return this.layers
        .map((x) => x.layer_id)
        .reduce((a, b) => {
          return Math.max(a, b);
        });
    }
  }
}
```

And that's it for the Frontend!

## Testing it! ##

I start by opening the Google Timeline page. There you can export a day to KML 
by clicking the Gear Icon here:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/mapboxtileserver_kml/MuensterWorkPath.png">
        <img src="/static/images/blog/mapboxtileserver_kml/MuensterWorkPath.png">
    </a>
</div>

It's my way to work, I zoom into a part, so **you** cannot track me. I now click 
the floating action button, upload the KML data and the KML data gets overlayed 
in the Vue.js application:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/mapboxtileserver_kml/MuensterMapboxTileServer.png">
        <img src="/static/images/blog/mapboxtileserver_kml/MuensterMapboxTileServer.png">
    </a>
</div>

It works! Keep in mind, this is what the KML to GeoJSON converter is tested with right now.

## Conclusion ##

And that's it! In the end I have to admit... I could have saved a lot of time implementing all this, 
if I had simply used the great ``toGeoJson`` library on client-side or if I had spun up a process for 
calling rock-solid libraries like [GDAL]. 😅

[Tom MacWright (@tmcw)]: https://github.com/tmcw
[Vetur]: https://github.com/vuejs/vetur
[MapboxTileServer]: https://github.com/bytefish/MapboxTileServer/
[GDAL]: https://gdal.org/