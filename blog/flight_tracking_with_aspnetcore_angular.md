title: Flight Tracking with the OpenSky Network API, Angular and ASP.NET Core 
date: 2024-08-14 12:30
tags: angular, aspnetcore, docker, dotnet
category: dotnet
slug: flight_tracking_with_aspnetcore_angular
author: Philipp Wagner
summary: This article shows how to extract plain text from a docx file.

A few years ago, I have written a small Flight Tracking Software using ASP.NET Core, 
MapboxJS and the OpenSky API. But due to children and *life*, I've never managed to 
write about it.

I think it was a pretty cool project, and to leave it there for 4 years aches my 
heart. And a lot of people want to put things on web maps and see them moving 
around, right?

So let's look into it and bring it back to life. I'll update it to the most 
recent ASP.NET Core and Angular versions, MapboxJS will be replaced with 
MapLibreJS and while at it I'll also add Docker support.

The final result looks like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/flight_tracking_with_aspnetcore_angular/OpenSkyFlightTracker_Flights.jpg">
        <img src="/static/images/blog/flight_tracking_with_aspnetcore_angular/OpenSkyFlightTracker_Flights.jpg" alt="Final Result for the Flight Tracker">
    </a>
</div>

All code can be found in a Git repository at:

* [https://github.com/bytefish/OpenSkyFlightTracker](https://github.com/bytefish/OpenSkyFlightTracker)

## Table of contents ##

[TOC]

## Styles, Fonts, MBTiles, ... what's all that? ##

Before diving right into the migration plan and code, let's take a look at what's 
required to see beautiful web maps in our application. There are so called "Map Tiles", 
we need to download, there is a "Map Style" and "Fonts".

### Tilesets and MBTiles ###

[Bertil Chapuis]: https://github.com/bchapuis

An empty map is boring to look at, even if we see planes flying above a grey 
area. We need a world map, we need tiles! What's that, a "tile"? In web maps 
the world is divided into a regular grid of little square areas and these 
square areas are called "tiles".

Then there is the MBTiles specification, which stands for "Mapbox Tiles". A 
subtle hint, that Mapbox intially came up with them. It's basically a SQLite 
database with a specific database schema, that allows us to query for tiles.

Where do you get these tiles from?

For one you can of course generate these tiles all by yourself. Back then 
[Bertil Chapuis] just wrote baremaps, which allows you to create vector maps 
all by yourself. It uses my PgBulkInsert library, so I have a sweet spot 
there.

But for a non-commercial project, the simplest way is to register an OpenMapTiles 
account and download the MBTiles for the region we are interested in. In the example 
for the repository I have used the "Regierungsbezirk Münster, Germany":

* [https://data.maptiler.com/downloads/europe/germany/nordrhein-westfalen/muenster-regbez/](https://data.maptiler.com/downloads/europe/germany/nordrhein-westfalen/muenster-regbez/)

I have also downloaded the Natural Earth Relief tiles, so for anything we don't 
have the OpenMapTiles data for, we get a nice view of the earths relief at 
least. A kind soul is sharing it here:

* [https://klokantech.github.io/naturalearthtiles/](https://klokantech.github.io/naturalearthtiles/)

I am not allowed to redistribute these MBTiles, so you have to do some manual work. If 
someone however comes up with a redistributable "Starter Set" of MBTiles (let's say 
10MB), I'll be more than happy to add it.

#### Configuring the MBTiles Tilesets for the Application ####

If you want to change the MBTile, you can change it in the `appsettings.json` (or the Environment you want to change). My 
`appsettings.json` for local development looks like this:

```json
{
  "Application": {
    "Tilesets": {
      "openmaptiles": {
        "Filename": "C:/Users/philipp/data/osm-2020-02-10-v3.11_nordrhein-westfalen_muenster-regbez.mbtiles",
        "ContentType": "application/vnd.mapbox-vector-tile"
      },
      "natural_earth_2_shaded_relief.raster": {
        "Filename": "C:/Users/philipp/data/natural_earth_2_shaded_relief.raster.mbtiles",
        "ContentType": "image/png"
      }
    }
  }
}
```

### Style Specification ###

Mapbox initially came up with a specification for styling a map. I think we have 
to be thankful to the Mapbox team, that they didn't patent all their work. So we 
can enjoy beautiful web maps.

The "Style Specification" is a beast, you can find the documentation over at:

* [https://maplibre.org/maplibre-style-spec/](https://maplibre.org/maplibre-style-spec/)

What it basically does is defining the visual appereance of a map for basically 
everything on a map, and it links to the tiles, fonts and glyphs to use. Where 
do we start?

The maputnik repository comes with a set of pre-built styles and I think the OSM 
Liberty style looks great:

* [https://github.com/maputnik/osm-liberty](https://github.com/maputnik/osm-liberty)

I'll download it to the `src/OpenSkyFlightTracker.Web.Client` project into the `/assets` 
folder, where the Angular application resides. So when we publish the Angular application 
it will also be copied over.

### PBF Fonts ###

We'll need fonts converted to the PBF format, which we can download here:

* [https://github.com/korywka/fonts.pbf](https://github.com/korywka/fonts.pbf)

I have put a `fonts.tar.xz` (and a `fonts.zip`) into the `/data` folder of the project.

We need them in the `OpenSkyFlightTracker.Web.Server` web root folder, so switch to the 
folder `/src/OpenSkyFlightTracker.Web.Server/wwwroot` and run the following command:

```
> mkdir "assets\fonts"
> tar xf "..\..\..\data\fonts\fonts.zip" -C "assets/fonts"
```

The fonts are now unpacked to the `wwwroot` folder.

## The Migration Plan ##

### Migrating the Frontend to Angular 18 ###

The repository slept there for four years. Angular was at Angular 10 back in the days, 
so there have been 8 major releases in between. It's needless to say, there have been 
*some* breaking changes.

In the Jumanji-esque land of JavaScript it's impossible to simply run an `npm update` 
and call it a day. Take a two week old JavaScript project and you'll find yourself in 
a hopeless adventure. The Angular CLI supports migrations, but only between two 
consecutive major releases. 

So I am going to do the only sane thing. I'll create an Angular 18 sample project 
using the Angular CLI, copy the few parts of code over and fix the things breaking 
left and right.

### Migrating the Backend to .NET 8 ###

The Backend used .NET Core 3.1. .NET has a great backwards compability, so I could 
open the project, replace the `TargetFramework` in the Project file and it compiles 
happily. I think that's testament to the .NET ecosystem.

Except that... I am not happy with the "old way" of doing things! By now new best 
practices in ASP.NET Core emerged, and the "old code" looks nothing like current 
.NET developers would expect.

Plus the previous code relied on a "MapboxTileServer", that's nowhere to be 
found. It was a small ASP.NET Core API for serving vector map tiles in the 
MBTiles format.

Back then I've switched the MapboxTileServer repositories visibility to *Private*, 
because I feared infringing MapBox copyrights. And with a job, and two babies 
keeping me awake the nights? Some legal problems is nothing I want to deal with.

So while at it, we'll also rip the code for service map tiles off this mysterious 
MapboxTileServer repository and put it where it belongs, in the OpenSkyFlightTracker 
repository.

Sounds like a plan, right?

## To the Code! ##

### First: Creating a new Project Structure ###

In the previous implementation we had some kind of chaotic folder structure. The 
Backend API lived in a `Backend` folder, the Frontend lived in a `Frontend` folder, 
that had the Angular source included.

For the update I want everything to live together in a single Visual Studio 
Solution. The less context switches, the better. Visual Studio 2022 now comes 
with a new Project Type for JavaScript an TypeScript projects, called ESPROJ 
in the documentation:

* https://learn.microsoft.com/en-us/visualstudio/javascript/javascript-in-visual-studio?view=vs-2022

It's a good idea to use it. So I create three projects:

* `OpenSkyFlightTracker.Api` (ASP.NET Core)
    * This is the Backend API to communicate with the OpenSky API and serve tiles.
* `OpenSkyFlightTracker.Web.Client` (ESPROJ)
    * This is where the Angular application goes.
* `OpenSkyFlightTracker.Web.Server` (ASP.NET Core)
    * This is where the Angular application is hosted in.

### Angular 18: Environments are gone! ###

After creating the app from the Angular CLI templates, I've noticed, that there 
are no `environments` anymore. Say what? Yes, turns out managing configurations 
at build time was a bad idea, because every tiny configuration change needs a 
complete rebuild.

Wouldn't it be cool to have something like the `appsettings.json` in .NET? 

So let's do it.

We define an `AppSettings` interface, that holds some of our required configurations:

```typescript
export interface LngLat {
  lng: number;
  lat: number;
}

export interface MapOptions {
  mapStyleUrl: string;
  mapInitialPoint: LngLat;
  mapInitialZoom: number;
}

export interface AppSettings {
  apiUrl: string;
  mapOptions: MapOptions;
}
```

And then we define an `AppSettingsService` to read the whole thing:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpClient } from "@angular/common/http";
import { Injectable, NgZone } from "@angular/core";
import { Observable, lastValueFrom } from "rxjs";
import { AppSettings } from "../model/app-settings";

@Injectable({
  providedIn: "root"
})
export class AppSettingsService {

  private appSettings?: AppSettings;

  constructor(private http: HttpClient) { }

  async loadAppSettings() {
    const appSettings = await lastValueFrom(this.http.get<AppSettings>('/assets/appsettings.json'));

    this.appSettings = appSettings;
  }

  getAppSettings(): AppSettings {
    if (!this.appSettings) {
      throw new Error('appsetting.json has not been loaded');
    }
    return this.appSettings;
  }
}
```

In the `app.module.ts` we wire it up. We'll need to use the `APP_INITIALIZER` injection 
token, so we block until the `AppSettingsService` is initialized:

```
import { APP_INITIALIZER, NgModule } from '@angular/core';

// ...

export function initConfig(appConfig: AppSettingsService) {
  return () => appConfig.loadAppSettings();
}

@NgModule({
  // ...
  providers: [
    // ...
    provideHttpClient(),
    {
      provide: APP_INITIALIZER,
      useFactory: initConfig,
      deps: [AppSettingsService],
      multi: true,
    },
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

We can then use it in a component. Here is the `app.component.ts` for example:

```
export class AppComponent implements OnInit, OnDestroy {

  // ...
  
  constructor(private sseService: SseService, private appSettingsService: AppSettingsService, private mapService: MapService) {
    const appSettings = this.appSettingsService.getAppSettings();

    // Set the Style for the Map:
    this.mapStyle = appSettings.mapOptions.mapStyleUrl;

    // Set the Initial Map Center:
    this.mapCenter = new LngLat(
      appSettings.mapOptions.mapInitialPoint.lng,
      appSettings.mapOptions.mapInitialPoint.lat);

    // ...      
  }
  
  // ...
}
```

### Angular: Defining the Endpoints for Tiles, Sprites and Fonts ###

I've thought about making the style and fonts very configurable, but it's not worth 
the effort. MapLibre GL JS expects us to define the tiles to be used in the `"sources"` 
section of the Map style, so let's do it in the `osm_liberty.json` style.

You can find it in `assets/style/osm_liberty/osm_liberty.json`:

```json
{
  "sources": {
    "ne_2_hr_lc_sr": {
      "tiles": [
        "https://localhost:5000/tiles/natural_earth_2_shaded_relief.raster/{z}/{x}/{y}"
      ],
      "type": "raster",
      "tileSize": 256,
      "maxzoom": 6
    },
    "openmaptiles": {
      "type": "vector",
      "tiles": [
        "https://localhost:5000/tiles/openmaptiles/{z}/{x}/{y}"
      ],
      "minzoom": 0,
      "maxzoom": 14
    }
  },
  "sprite": "https://localhost:5001/assets/sprites/osm_liberty/osm-liberty",
  "glyphs": "https://localhost:5001/assets/fonts/{fontstack}/{range}.pbf",
}
```

Where ...

* `https://localhost:5000` is the `OpenSkyFlightTracker.Api`
* `https://localhost:5001` is the `OpenSkyFlightTracker.Web.Server`

### API: Serving MBTiles ###

I've promised to show how to serve MBTiles. 

We start by defining a `Tileset` class as:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace OpenSkyFlightTracker.Api.Options
{
    public class Tileset
    {
        /// <summary>
        /// Path to the MBTiles.
        /// </summary>
        public required string Filename { get; set; }

        /// <summary>
        /// The Content-Type to be served.
        /// </summary>
        public required string ContentType { get; set; }
    }
}

```

This will be used in the `ApplicationOptions` to populate a dictionary of Tilesets, 
that can be accessed by name:

```
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace OpenSkyFlightTracker.Api.Options
{
    public class ApplicationOptions
    {
        // ...
        
        /// <summary>
        /// Gets or sets the Tilesets available.
        /// </summary>
        public Dictionary<string, Tileset> Tilesets { get; set; } = new();
    }
}
```

The Tilesets for our Docker container look like this in the `appsettings.Docker.json`:

```json
{
  "Application": {
    "Tilesets": {
      "openmaptiles": {
        "Filename": "/opensky-tiles/osm-2020-02-10-v3.11_nordrhein-westfalen_muenster-regbez.mbtiles",
        "ContentType": "application/vnd.mapbox-vector-tile"
      },
      "natural_earth_2_shaded_relief.raster": {
        "Filename": "/opensky-tiles/natural_earth_2_shaded_relief.raster.mbtiles",
        "ContentType": "image/png"
      }
    }
  }
}
```

MBTiles are basically a SQLite database, so we then add a Package Reference to `Microsoft.Data.Sqlite`:

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">

    <!-- ... -->

    <ItemGroup>
        <PackageReference Include="Microsoft.Data.Sqlite" Version="8.0.8" />
        <!-- ... -->
    </ItemGroup>

</Project>
```

We'll then create a `MapboxTileService`, which is used to read the tile data for a given `x`, `y` and `z`, 
where `z` is the Zoom Level, `x` is the column number and `y` is the row.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Data.Sqlite;
using OpenSkyFlightTracker.Api.Options;

namespace OpenSkyFlightTracker.Api.Services
{
    public class MbTilesService
    {
        public byte[]? Read(Tileset tileset, int z, int x, int y)
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

And to serve the tiles we add a `MbTilesController`, that uses the `MbTilesService` to read from a requested Tileset.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using OpenSkyFlightTracker.Api.Options;
using OpenSkyFlightTracker.Api.Services;

namespace OpenSkyFlightTracker.Api.Controllers
{
    [ApiController]
    public class MbTilesController : ControllerBase
    {
        private readonly ILogger<MbTilesController> _logger;

        private readonly ApplicationOptions _applicationOptions;
        private readonly MbTilesService _mapboxTileService;

        public MbTilesController(ILogger<MbTilesController> logger, IOptions<ApplicationOptions> applicationOptions, MbTilesService mapboxTileService)
        {
            _logger = logger;
            _applicationOptions = applicationOptions.Value;
            _mapboxTileService = mapboxTileService;
        }

        [HttpGet]
        [Route("/tiles/{tileset}/{z}/{x}/{y}")]
        public ActionResult Get([FromRoute(Name = "tileset")] string tiles, [FromRoute(Name = "z")] int z, [FromRoute(Name = "x")] int x, [FromRoute(Name = "y")] int y)
        {
            _logger.LogDebug($"Requesting Tiles (tileset = {tiles}, z = {z}, x = {x}, y = {y})");

            if (!_applicationOptions.Tilesets.TryGetValue(tiles, out Tileset? tileset))
            {
                _logger.LogWarning($"No Tileset available for Tileset '{tiles}'");

                return BadRequest();
            }

            var data = _mapboxTileService.Read(tileset, z, x, y);

            if (data == null)
            {
                return Accepted();
            }

            // Mapbox Vector Tiles are already compressed, so we need to tell 
            // the client we are sending gzip Content:
            if (tileset.ContentType == Constants.MimeTypes.ApplicationMapboxVectorTile)
            {
                Response.Headers.TryAdd("Content-Encoding", "gzip");
            }

            return new FileContentResult(data, tileset.ContentType);
        }
    }
}
```

That's our Tile Server!

### Docker: OpenSkyFlightTracker.Api ###

The `Dockerfile` for the `OpenSkyFlightTracker.Api` is an easy one. We can merely 
copy and paste the example from the Microsoft documentation and off we go:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /source

COPY ../src/OpenSkyFlightTracker.Api/*.csproj ./OpenSkyFlightTracker.Api/

RUN dotnet restore "OpenSkyFlightTracker.Api/OpenSkyFlightTracker.Api.csproj"

COPY ../src/OpenSkyFlightTracker.Api/. ./src/OpenSkyFlightTracker.Api/

RUN dotnet publish ./src/OpenSkyFlightTracker.Api/OpenSkyFlightTracker.Api.csproj -c release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0

WORKDIR /app
COPY --from=build /app ./

ENTRYPOINT ["dotnet", "OpenSkyFlightTracker.Api.dll"]
```

### Docker: OpenSkyFlightTracker.Web.Server ###

I want to host the Angular app in an ASP.NET Core Web Application, so we have two projects:

* `OpenSkyFlightTracker.Web.Client`
* `OpenSkyFlightTracker.Web.Server`

My reasoning here is a simple one: I don't want to fiddle around with nginx, because I 
really don't want to learn yet another configuration language. If I can stay in the .NET 
ecosystem, I prefer to stay.

#### Output the Angular Build to the ASP.NET Application ####

So we need to first solve a small riddle: How does the build artifact of `ng build` go 
into the `wwwroot` folder of the `OpenSkyFlightTracker.Web.Server` project? Finding this 
out was quite an adventure.

Easy! In the `angular.json` we'll need to set the `outputPath` to the `wwwroot` folder 
of the ASP.NET Core Web project. So whenever we run an `ng build` or `npm run build`, the 
build artifacts will find their place:

```json
{
  "architect": {
    "build": {
      "options": {
        "outputPath": {
            "base": "../OpenSkyFlightTracker.Web.Server/wwwroot",
            "browser": ""
        },
        "index": "src/index.html"
      }
    }
  }
}
```

Just took me an hour to find this out.

#### How do we exclude files from Publishing? ####

Now there's another thing to take care of. If you look into the `wwwroot` folder of the `OpenSkyFlightTracker.Web.Server`  
project, you'll find a `README.txt` and a link to the `fonts.zip` file. As previously discussed, you need to manually 
extract the fonts to this folder, but we don't want to deploy them! 

So in the `OpenSkyFlightTracker.Web.Server.csproj` we'll add the following `ItemGroup` entries:

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  
  <!-- ... -->
  
  
  <ItemGroup>
      <Content Include="..\..\data\fonts\fonts.tar.xz" Link="wwwroot\fonts.tar.xz">
          <CopyToOutputDirectory>Never</CopyToOutputDirectory>
          <CopyToPublishDirectory>Never</CopyToPublishDirectory>
      </Content>
  </ItemGroup>
  
  <ItemGroup>
    <Content Update="wwwroot\README.txt">
      <CopyToOutputDirectory>Never</CopyToOutputDirectory>
      <CopyToPublishDirectory>Never</CopyToPublishDirectory>
    </Content>
  </ItemGroup>
  
  <!-- ... -->
  
</Project>
```

#### Finally the Dockerfile ####

Now we can finally write the `Dockerfile`. There's not a lot of things happening, except for installing 
`npm`, because we need it for building the Angular app. And there's a point, where we are weaseling in 
the fonts using Dockers `ADD` command.

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install nodejs -y

WORKDIR /data
COPY ../data/fonts/fonts.tar.xz ./fonts.tar.xz
 
WORKDIR /source

COPY ../src/OpenSkyFlightTracker.Web.Client/ ./OpenSkyFlightTracker.Web.Client/
COPY ../src/OpenSkyFlightTracker.Web.Server/ ./OpenSkyFlightTracker.Web.Server/

RUN dotnet restore "OpenSkyFlightTracker.Web.Server/OpenSkyFlightTracker.Web.Server.csproj"

WORKDIR /source/OpenSkyFlightTracker.Web.Client
RUN npm install

WORKDIR /source/OpenSkyFlightTracker.Web.Server

RUN dotnet publish -c release -o /app  /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0

WORKDIR /app

ADD ../data/fonts/fonts.tar.xz ./wwwroot/assets/fonts

COPY --from=build /app ./

ENTRYPOINT ["dotnet", "OpenSkyFlightTracker.Web.Server.dll"]
```

### Docker Compose ###

And now let's write the `docker-compose.yml` to start both services. We are using the 
Development Certificates to provide `https` for all services. At the same time we are 
adding the User Secrets, so they are also available within the application.

```yaml
networks:
  services:

services:
  opensky-api:
    container_name: opensky-api
    build:
      context: .
      dockerfile: ./docker/opensky-api/Dockerfile
    environment:
      - ASPNETCORE_ENVIRONMENT=Docker
      - ASPNETCORE_HTTPS_PORTS=5000
      - ASPNETCORE_Kestrel__Certificates__Default__Path=/https/aspnetapp.pfx
      - ASPNETCORE_Kestrel__Certificates__Default__Password=SuperStrongPassword
    profiles:  ["api", "dev"]
    env_file:
      - ./docker/.env
    ports:
      - "5000:5000"
    volumes:
      - ~/.aspnet/https:/https:ro
      - ${APPDATA}/Microsoft/UserSecrets:/root/.microsoft/usersecrets:ro
      - ./docker/opensky-tiles:/opensky-tiles
  opensky-web:
    container_name: opensky-web
    build:
      context: .
      dockerfile: ./docker/opensky-web/Dockerfile
    environment:
      - ASPNETCORE_ENVIRONMENT=Docker
      - ASPNETCORE_HTTPS_PORTS=5001
      - ASPNETCORE_Kestrel__Certificates__Default__Path=/https/aspnetapp.pfx
      - ASPNETCORE_Kestrel__Certificates__Default__Password=SuperStrongPassword
    profiles:  ["web", "dev"]
    env_file:
      - ./docker/.env
    ports:
      - "5001:5001"
    volumes:
      - ~/.aspnet/https:/https:ro      
      - ${APPDATA}/Microsoft/UserSecrets:/root/.microsoft/usersecrets:ro
```

We can now run:

```
docker compose --profile dev up
```

And you can visit `https://localhost:5001` and a map with the planes appears.

## Conclusion ##

So I think this repository gives you a pretty good idea, how to integrate web maps 
in your Angular application and how to feed it from an ASP.NET Core Backend.

If you need to host larger maps or, say, the entire world map, you'll need a 
beefy machine and a good amount of disk space. And also think about adding some 
caching to the tile server... or maybe use a battle-tested tile server?

However, it's a lean implementation, that I would use to display maps in "In-House" 
applications. It's so few .NET and TypeScript involved, and easy to adapt to your 
needs.