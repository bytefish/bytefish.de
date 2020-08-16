title: Adding Geocoding to the MapboxTileServer with Photon
date: 2020-08-16 10:09
tags: osm, dotnet, mapbox, tiles, photon
category: dotnet
slug: mapboxtileserver_geocoding
author: Philipp Wagner
summary: This article shows how to add Geocoding to the MapboxTileServer project.

In the last article I have shown how to display Vector and Raster tiles using [OpenMapTiles] and 
Mapbox GL JS. So you have been able to scroll through the map, click on it to get information about 
features, but one thing is missing: Searching for places.

Now there is an OpenStreetMap project called [Nomatim] for providing Geocoding on OSM data, but... 
setting up Nomatim requires quite some effort as far as I can see. It actually requires much more effort, than 
I am inclined to invest into small personal projects.

Enter Photon ...

[Nomatim]: https://nominatim.org/

## Photon ##

According to the documentation Photon is ...

> [...] an open source geocoder built for [OpenStreetMap] data. It is based on [elasticsearch] - an efficient, powerful and highly 
> scalable search platform.
>
> Photon was started by [komoot] and provides search-as-you-type and multilingual support. It's used in production with thousands 
> of requests per minute at [www.komoot.de]. Find our public API and demo on [photon.komoot.de].

You can find the GitHub repositories at:

* [https://github.com/komoot/photon]([https://github.com/komoot/photon)

[komoot]: http://www.komoot.de/
[photon.komoot.de]: http://photon.komoot.de/
[www.komoot.de]: http://www.komoot.de/
[OpenStreetMap]: http://www.osm.org/
[elasticsearch]: http://elasticsearch.org/

### Getting the Search Index Data for Photon ###

Photon requires an elasticsearch index. This index can be built by using the Photon CLI to import the data 
from [Nomatim], but there is a much simpler way.

The kind people of [GraphHopper] and [Ionvia] provide a download of the Photon elasticsearch index. The index 
is built each week, so it contains recent additions to the [OpenStreetMap] data. 

The archive ``photon-db-latest.tar.bz2`` always contains the latest build and can be downloaded from:

* [http://download1.graphhopper.com/public/](http://download1.graphhopper.com/public/)

If you are using a Unix system you can also run the following command to download and extract the latest search index:

```bash
wget -O - http://download1.graphhopper.com/public/photon-db-latest.tar.bz2 | bzip2 -cd | tar x
```

[GraphHopper]: https://www.graphhopper.com/
[Ionvia]: https://github.com/lonvia

### Getting Photon Up and Running ###

When you have downloaded an extracted the data, you start with getting the latest JAR file from the Photon 
releases. As of writing this is 0.3.3:

* [https://github.com/komoot/photon/releases/tag/0.3.3](https://github.com/komoot/photon/releases/tag/0.3.3)

What I do now is writing a simple Batch Script to set the Java executable, the JAR file and the Data Directory, which 
contains the Search index you have just downloaded and extracted:

```batch
@echo off

:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

set JAVA_EXE="G:\Applications\Oracle\jdk-14.0.1\bin\java.exe"
set PHOTON_JAR="G:\Applications\Photon\photon-0.3.3.jar"
set DATA_DIR="G:\Data\Photon\photon-db-de-200809"

%JAVA_EXE% -jar %PHOTON_JAR% -data-dir %DATA_DIR% -listen-ip 0.0.0.0 -listen-port 2322 -cors-any

pause
```

Now if you execute the Script, you should give elasticsearch some seconds to load the index and... that's it!

It was *unbelievably easy* to get started with Photon. The developers have done a great job!

## What we are going to build ##

Photon is already up and running. So what we are going to do now is to integrate it into the MapboxTileServer example 
we have written in our last article. We will add a simple Autocomplete Box to search for places and for selected places 
we will add a Marker.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/mapboxtileserver_geocoding/MapboxTileServerGeocodingExample.png">
        <img src="/static/images/blog/mapboxtileserver_geocoding/MapboxTileServerGeocodingExample.png">
    </a>
</div>

You can find all code in the MapboxTileServer GitHub repository at:

* [https://github.com/bytefish/MapboxTileServer](https://github.com/bytefish/MapboxTileServer)

## Backend: Integratin the Photon API ##

### Extending the ApplicationOptions ###

In the last article we have written a class ``ApplicationOptions`` to store all configurations for the 
application. For Photon we need to configure at least the API endpoint. I like to put these settings in 
a class ``PhotonSettings``, because there might be additional settings in the future:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace MapboxTileServer.Options
{
    public class PhotonSettings
    {
        public string ApiUrl { get; set; }
    }
}
```

Then we are adding the ``PhotonSettings`` to the ``ApplicationOptions``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;

namespace MapboxTileServer.Options
{
    public class ApplicationOptions
    {
        public PhotonSettings Photon { get; set; }

        public IDictionary<string, Tileset> Tilesets { get; set; }
    }
}
```

### Writing the Photon API Client ###

Once Photon has been started, it hosts a RESTful API to search for places or do a reverse search on coordinates. For my 
C\# projects I am always using some helper classes to build RESTful clients... so I am not taking more dependencies 
than required. 

You can find these helper classes here:

* [https://github.com/bytefish/MapboxTileServer/tree/master/MapboxTileServer/MapboxTileServer/Clients/Http](https://github.com/bytefish/MapboxTileServer/tree/master/MapboxTileServer/MapboxTileServer/Clients/Http)

Now for Photon there are only 2 endpoints for the Search and Reverse Search. The query parameters have been taken from 
the Photon documentation, but if there are missing parameters feel free to make a Pull Request to the repository.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.Clients.Http.Builder;
using MapboxTileServer.Options;
using Microsoft.Extensions.Options;
using System;
using System.Globalization;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace MapboxTileServer.Clients
{
    public class PhotonSearchClient
    {
        private readonly HttpClient httpClient;
        private readonly ApplicationOptions applicationOptions;

        public PhotonSearchClient(IOptions<ApplicationOptions> applicationOptions)
            : this(applicationOptions, new HttpClient())
        {
        }

        public PhotonSearchClient(IOptions<ApplicationOptions> applicationOptions, HttpClient httpClient)
        {
            this.httpClient = httpClient;
            this.applicationOptions = applicationOptions.Value;
        }

        public async Task<string> ReverseAsync(float lat, float lon, CancellationToken cancellationToken = default)
        {
            var url = $"{applicationOptions.Photon?.ApiUrl}/reverse";

            var httpRequestMessage = new HttpRequestMessageBuilder(url, HttpMethod.Get)
                .AddQueryString("lon", lon.ToString(CultureInfo.InvariantCulture))
                .AddQueryString("lat", lat.ToString(CultureInfo.InvariantCulture))
                .Build();

            var httpResponse = await httpClient
                .SendAsync(httpRequestMessage, cancellationToken)
                .ConfigureAwait(false);

            if (!httpResponse.IsSuccessStatusCode)
            {
                var statusCode = httpResponse.StatusCode;
                var reason = httpResponse.ReasonPhrase;

                throw new Exception($"API Request failed with Status Code {statusCode} and Reason {reason}. For additional information, see the HttpResponseMessage in this Exception.");
            }

            return await httpResponse.Content
                .ReadAsStringAsync()
                .ConfigureAwait(false);
        }

        public async Task<string> Search(string q, string lang = default, int? limit = default, float? lat = default, float? lon = default, int? location_bias_scale = default, string bbox = default, string[] osm_tags = default, CancellationToken cancellationToken = default)
        {
            var url = $"{applicationOptions.Photon?.ApiUrl}";

            var httpRequestMessageBuilder = new HttpRequestMessageBuilder(url, HttpMethod.Get);

            httpRequestMessageBuilder.AddQueryString("q", q);

            if(!string.IsNullOrWhiteSpace(lang))
            {
                httpRequestMessageBuilder.AddQueryString("lang", lang);
            }

            if(limit.HasValue)
            {
                httpRequestMessageBuilder.AddQueryString("limit", limit.Value.ToString(CultureInfo.InvariantCulture));
            }

            if(lat.HasValue)
            {
                httpRequestMessageBuilder.AddQueryString("lat", lat.Value.ToString(CultureInfo.InvariantCulture));
            }

            if(lon.HasValue)
            {
                httpRequestMessageBuilder.AddQueryString("lon", lon.Value.ToString(CultureInfo.InvariantCulture));
            }

            if (location_bias_scale.HasValue)
            {
                httpRequestMessageBuilder.AddQueryString("location_bias_scale", location_bias_scale.Value.ToString(CultureInfo.InvariantCulture));
            }

            if(!string.IsNullOrWhiteSpace(bbox))
            {
                httpRequestMessageBuilder.AddQueryString("bbox", bbox);
            }

            if(osm_tags != null)
            {
                foreach(var osm_tag in osm_tags)
                {
                    httpRequestMessageBuilder.AddQueryString("osm_tag", osm_tag);
                }
            }

            var httpRequestMessage = httpRequestMessageBuilder.Build();

            var httpResponse = await httpClient
                .SendAsync(httpRequestMessage)
                .ConfigureAwait(false);

            if (!httpResponse.IsSuccessStatusCode)
            {
                var statusCode = httpResponse.StatusCode;
                var reason = httpResponse.ReasonPhrase;

                throw new Exception($"API Request failed with Status Code {statusCode} and Reason {reason}. For additional information, see the HttpResponseMessage in this Exception.");
            }

            return await httpResponse.Content
                .ReadAsStringAsync()
                .ConfigureAwait(false);
        }
    }
}
```

The ``PhotonSearchClient`` then needs to be registered in the Dependency Injection container. For ASP.NET Core this is done 
in the ``Startup.cs`` file. In my example there is a method ``RegisterApplicationServices``:

```
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.Clients;
using MapboxTileServer.Options;
using MapboxTileServer.Services;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace MapboxTileServer
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        private void RegisterApplicationServices(IServiceCollection services)
        {
            services.AddSingleton<PhotonSearchClient>();
            // ...
        }
    }
}
```

### Handling Queries with a SearchController ###

What's left on the Backend-side is to define an endpoint for handling search queries. The controller offers a single 
endpoint ``/search``, that takes a query string. It then calls the ``PhotonSearchClient``, which has automatically 
been injected by the Dependency Injection framework.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using MapboxTileServer.Clients;
using MapboxTileServer.Options;
using MapboxTileServer.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using System.Threading;
using System.Threading.Tasks;

namespace MapboxTileServer.Controllers
{
    [ApiController]
    public class SearchController : ControllerBase
    {
        private readonly ILogger<TilesController> logger;
        private readonly ApplicationOptions applicationOptions;
        private readonly PhotonSearchClient photonSearchClient;

        public SearchController(ILogger<TilesController> logger, IOptions<ApplicationOptions> applicationOptions, PhotonSearchClient photonSearchClient)
        {
            this.logger = logger;
            this.applicationOptions = applicationOptions.Value;
            this.photonSearchClient = photonSearchClient;
        }

        [HttpGet]
        [Route("/search")]
        public async Task<ActionResult> Search([FromQuery(Name = "q")] string query, CancellationToken cancellationToken)
        {
            var result = await photonSearchClient.Search(query, cancellationToken: cancellationToken);

            if (logger.IsEnabled(LogLevel.Debug))
            {
                logger.LogDebug($"Results for '{query}': {result}");
            }

            return Ok(result);
        }
    }
}
```

## Frontend: Adding an Autocomplete and Markers ##

On the Frontend-side we are first adding an Autocomplete Box. You think there are million projects, but 
finding a Vanilla JS component, that my brain was able to digest... was really tough. 

I settled on the ``autocomplete`` component at:

* [https://github.com/kraaden/autocomplete](https://github.com/kraaden/autocomplete)

Once downloaded to ``wwwroot/static/js`` and ``wwwroot/static/css`` it can be easily added 
to the ``head`` using:

```html
<script src="/static/js/autocomplete.js"></script>
<link href="/static/css/autocomplete.css" rel="stylesheet" />
```

### Formatting the GeoJSON results ###

Photon returns GeoJSON features, which cannot be displayed in the ``autocomplete`` Textbox of course. So 
we need a function to turn a OSM feature into a text. Here is the simple ``formatOsmFeature`` function I 
came up with:

```javascript
// Formats an OSM feature from the Search results:
var formatOsmFeature = function (feature) {
    var components = [];

    components.push(feature.properties.name);

    if (feature.properties.city && feature.properties.city !== feature.properties.name) {
        components.push(feature.properties.city);
    }

    if (feature.properties.country) {
        components.push(feature.properties.country);
    }

    return components.join(', ');
};
```

### Adding Markers to Mapbox GL JS ###

Once a user has selected a search result, we want to add a marker and jump to it on the map. This is done using 
a small function ``setMapLocation`` written for the project:

```javascript
// Sets a Marker for specified coordinates and moves to it:
var setMapLocation = function (map, coordinates) {
    var marker = new mapboxgl.Marker()
        .setLngLat(coordinates)
        .addTo(map);

    map.jumpTo({ center: coordinates });
}
```

See I am not storing the markers anywhere. This is not a full-blown application, but only shows the basics.

### Implementing the Autocomplete ###

In the ``index.html`` we are adding an ``input`` element to the sidebar:

```html
<div id="heading">
    <h1>MapboxTileserver</h1>
    <p>
        The example project shows how to integrate Photon for searching the map.
    </p>
    <input id="autocomplete" type="text" placeholder="Search ...">
</div>
```

Once we are done, we can define the ``autocomplete`` using the ``/search`` endpoint, the ``formatOsmFeature`` function 
and in the ``onSelect`` handler, we are calling the ``setMapLocation`` function:

```javascript
// Add Autocomplete Functionality:
var input = document.getElementById("autocomplete");

autocomplete({
    input: input,
    fetch: async function (query, update) {
        const source = await fetch(`http://localhost:9000/search?q=${query}`);

        const data = await source.json();

        if (!data) {
            return;
        }

        if (!data.features) {
            return;
        }

        update(data.features);
    },
    render: function (item, value) {
        const itemElement = document.createElement("div");
        itemElement.textContent = formatOsmFeature(item);
        return itemElement;
        
    },
    onSelect: function (item) {
        input.value = formatOsmFeature(item);
        console.log(item.geometry.coordinates);
        setMapLocation(map, item.geometry.coordinates);
    }
});
```

## Conclusion ##

And that's it! You can now start Photon, the MapboxTileServer and enjoy Geocoding.

[maputnik]: http://maputnik.github.io/
[OpenMapTiles]: https://openmaptiles.org/