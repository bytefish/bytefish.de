title: Extract Plain text from a Word Document 
date: 2024-08-12 13:15
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

So let's look into it and bring it back to life. I'll uppdate it to the most 
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

## Styles, Fonts, MBTiles, ... what's all that? ##

Before diving into the code, let's take a look at what's required to see beautiful 
web maps in your application. There are so called "Map Tiles", we need to download, 
there is a "Map Style" and "Fonts".

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

#### Changing the MBTiles File ####

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

## To the Code! ##

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
  
  constructor(private sseService: SseService, private appSettings: AppSettingsService, private mapService: MapService) {
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

Job done! Cool!

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

#### How does the Angular Build go into the ASP.NET Application? ####

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

## Conclusion ##

We can now run:

```
docker compose --profile dev up
```

And all services start up.

You can now visit `https://localhost:5001` and a map with the planes appears.