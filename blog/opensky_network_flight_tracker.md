title: Building a Flight Tracker with the OpenSky Network API, ASP.NET Core and Angular
date: 2020-09-27 22:32
tags: osm, opensky, mapbox, dotnet
category: opensky
slug: opensky_network_flight_tracker
author: Philipp Wagner
summary: This article shows how to write a Flight Tracker using ASP.NET Core, Angular and OpenSky Network REST API.

It's weekend. The children are sleeping. Papa has some free time!

Some time ago I played with self-hosting vector tiles. But the maps have been rather boring, nothing 
happened on it. Recently I have read an article about the OpenSky Network, which provides Flight tracking 
data.

A flight tracker looks like a nice little application to implement and use the vector tiles for. So in this 
article I will show you how to query the OpenSky REST API, write a small Backend and a Frontend to display 
current flights with Angular. 

## What we are going to build ##

The final application queries the OpenSky Network REST API to get most recents Flight data and push it 
to an Angular application (using Server-Sent Events). The State Vectors returned by the OpenSky REST API 
are displayed with Mapbox GL JS. The Tiles are self-hosted using the .NET Tile Server:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/opensky_network_flight_tracker/final_app_screenshot.jpg">
        <img src="/static/images/blog/opensky_network_flight_tracker/final_app_screenshot.jpg">
    </a>
</div>

## Getting the Data ##

### What's the "OpenSky Network"? ###

According to Wikipedia the OpenSky Network ...

> [...] is a non-profit association based in Switzerland. It was set up as a research  project by several 
> universities and government entities with the goal to improve the security, reliability and efficiency 
> of the airspace. 
>
> Its main function is to collect, process and store air traffic control data and provide open access to this 
> data to the public. Similar to many existing flight trackers such as Flightradar24 and FlightAware, the OpenSky 
> Network consists of a multitude of sensors (currently around 1000, mostly concentrated in Europe and the US), 
> which are connected to the Internet by volunteers, industrial supporters, academic, and governmental 
> organizations.

The OpenSky Network provides a RESTful API to query the Sensor data and is thoroughly documented at:

* [https://opensky-network.org/apidoc/rest.html](https://opensky-network.org/apidoc/rest.html)

### A .NET Library to query the OpenSky Network REST API ###

Now implementing a RESTful API to me is like drawing patterns in a Zen Garden. 

That's why I have written a .NET library to query the OpenSky API here:

* [https://github.com/bytefish/OpenSkyRestClient](https://github.com/bytefish/OpenSkyRestClient)

You can install it from NuGet by running the following command from the Package Manager Console:

```
PM> Install-Package OpenSkyRestClient
```

## Backend ##

### Data Model ###

Let's start with the Domain model, which basically is the OpenSky Network data model. Why reinvent the wheel? 

The idea is, that an Angular Client (or any other Frontend) makes a request to a Backends API endpoint and 
gets the data pushed using Server Sent Events. All parameters to register for events are passed in the 
``StateVectorsRequestDto``. 

A ``StateVectorsRequestDto`` allows to define time, flight identifier and a Bounding Box. All parameters 
are optional, if none is *all* latest state vectors are returned:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;

namespace OpenSkyBackend.Contracts
{
    public class StateVectorsRequestDto
    {
        [FromQuery(Name = "time")]
        public int? Time { get; set; }

        [FromQuery(Name = "icao24")]
        public string Icao24 { get; set; }

        [FromQuery(Name = "lamin")]
        public float? LaMin { get; set; }

        [FromQuery(Name = "lomin")]
        public float? LoMin { get; set; }

        [FromQuery(Name = "lamax")]
        public float? LaMax { get; set; }

        [FromQuery(Name = "lomax")]
        public float? LoMax { get; set; }
    }
}
```

The Backend then pushes ``StateVectorResponseDto`` to the Client using Server Sent Events:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace OpenSkyBackend.Contracts
{
    public class StateVectorResponseDto
    {
        /// <summary>
        /// The time which the state vectors in this response are associated with. All vectors 
        /// represent the state of a vehicle with the interval [time−1, time].
        /// </summary>
        [JsonPropertyName("time")]
        public int Time { get; set; }

        /// <summary>
        /// The state vectors.
        /// </summary>
        [JsonPropertyName("states")]
        public StateVectorDto[] States { get; set; }
    }
}
```

And the ``StateVectorDto`` the contains all available sensor data about a flight:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace OpenSkyBackend.Contracts
{
    public class StateVectorDto
    {
        /// <summary>
        /// Unique ICAO 24-bit address of the transponder in hex string representation.
        /// </summary>
        [JsonPropertyName("icao24")]
        public string Icao24 { get; set; }

        /// <summary>
        /// Callsign of the vehicle (8 chars). Can be null if no callsign has been received.
        /// </summary>
        [JsonPropertyName("callsign")]
        public string CallSign { get; set; }

        /// <summary>
        /// Country name inferred from the ICAO 24-bit address.
        /// </summary>
        [JsonPropertyName("origin_country")]
        public string OriginCountry { get; set; }

        /// <summary>
        /// Unix timestamp (seconds) for the last position update. Can be null if no position 
        /// report was received by OpenSky within the past 15s.
        /// </summary>
        [JsonPropertyName("time_position")]
        public int? TimePosition { get; set; }

        /// <summary>
        /// Unix timestamp (seconds) for the last update in general. This field is updated for 
        /// any new, valid message received from the transponder.
        /// </summary>
        [JsonPropertyName("last_contact")]
        public int? LastContact { get; set; }

        /// <summary>
        /// WGS-84 longitude in decimal degrees. Can be null.
        /// </summary>
        [JsonPropertyName("longitude")]
        public float? Longitude { get; set; }

        /// <summary>
        /// WGS-84 latitude in decimal degrees. Can be null.
        /// </summary>
        [JsonPropertyName("latitude")]
        public float? Latitude { get; set; }

        /// <summary>
        /// Barometric altitude in meters. Can be null.
        /// </summary>
        [JsonPropertyName("baro_altitude")]
        public float? BarometricAltitude { get; set; }

        /// <summary>
        /// Boolean value which indicates if the position was retrieved from a surface position report.
        /// </summary>
        [JsonPropertyName("on_ground")]
        public bool OnGround { get; set; }

        /// <summary>
        /// Velocity over ground in m/s. Can be null.
        /// </summary>
        [JsonPropertyName("velocity")]
        public float? Velocity { get; set; }

        /// <summary>
        /// True track in decimal degrees clockwise from north (north=0°). Can be null.
        /// </summary>
        [JsonPropertyName("true_track")]
        public float? TrueTrack { get; set; }

        /// <summary>
        /// Vertical rate in m/s. A positive value indicates that the airplane is climbing, 
        /// a negative value indicates that it descends. Can be null.
        /// </summary>
        [JsonPropertyName("vertical_rate")]
        public float? VerticalRate { get; set; }

        /// <summary>
        /// IDs of the receivers which contributed to this state vector. Is null if no filtering for sensor was used in the request.
        /// </summary>
        [JsonPropertyName("sensors")]
        public int[] Sensors { get; set; }

        /// <summary>
        /// Geometric altitude in meters. Can be null.
        /// </summary>
        [JsonPropertyName("geo_altitude")]
        public float? GeometricAltitudeInMeters { get; set; }

        /// <summary>
        /// The transponder code aka Squawk. Can be null.
        /// </summary>
        [JsonPropertyName("squawk")]
        public string Squawk { get; set; }

        /// <summary>
        /// Whether flight status indicates special purpose indicator.
        /// </summary>
        [JsonPropertyName("spi")]
        public bool Spi { get; set; }

        /// <summary>
        /// Origin of this state’s position: 0 = ADS-B, 1 = ASTERIX, 2 = MLAT
        /// </summary>
        [JsonPropertyName("position_source")]
        [JsonConverter(typeof(JsonStringEnumConverter))]
        public PositionSourceEnumDto PositionSource { get; set; }
    }
}
```

And the origin of a state position is given in the ``PositionSourceEnum``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace OpenSkyBackend.Contracts
{
    public enum PositionSourceEnumDto
    {
        /// <summary>
        /// Unknown.
        /// </summary>
        Unknown = -1,

        /// <summary>
        /// ASBD.
        /// </summary>
        ASBD = 0,

        /// <summary>
        /// ASTERIX.
        /// </summary>
        ASTERIX = 1,

        /// <summary>
        /// MLAT.
        /// </summary>
        MLAT = 2
    }
}
```

### Configuring the Backend: ApplicationOptions ###

Now the OpenSky Network API is rate limited, so we first need a way to configure the refresh interval for 
polling the REST API, so we play fair. You can also register an OpenSky account and make authenticated requests 
and that means we also need a way to specify, where the Credentials are read from.

That's why we define a class ``ApplicationOptions``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace OpenSkyBackend.Options
{
    public class ApplicationOptions
    {
        public string CredentialsFile { get; set; }

        public int? RefreshInterval { get; set; }
    }
}
```

In the ``Startup`` class for the ASP.NET Core application, we then configure the options:

```csharp
public class Startup
{
    public Startup(IConfiguration configuration)
    {
        Configuration = configuration;
    }

    public IConfiguration Configuration { get; }

    // This method gets called by the runtime. Use this method to add services to the container.
    public void ConfigureServices(IServiceCollection services)
    {
        // ...

        services
            .AddOptions()
            .Configure<ApplicationOptions>(Configuration.GetSection("Application"));

        // ...
    }
}
```

And in the ``appsettings.json`` we can set the file and refresh interval (in seconds):

```json
{
  "ApplicationOptions": {
    "CredentialsFile": "D:\\credentials.json",
    "RefreshInterval": 10
  }
}
```

The Credentials file in ``D:\\credentials.json`` is expected to contain a username and password like this:

```json
{
  "username": "<USERNAME>",
  "password": "<PASSWORD>"
}
```

### Get and Push the Data: The StateVectorController ###

There is only 1 endpoint in the sample backend. It uses the ``OpenSkyClient`` to query the OpenSky REST API using 
(optional) filter criterias passed by the client. What then happens is basically:

1. Query the OpenSky REST API using the ``OpenSkyClient``
2. Convert the ``OpenSkyClient`` data model to the Webservice data model
3. Push the data to the client using Server Sent Events

This translates to:

```
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using OpenSkyBackend.Contracts;
using OpenSkyBackend.Options;
using OpenSkyRestClient;
using OpenSkyRestClient.Model;
using OpenSkyRestClient.Model.Response;
using OpenSkyRestClient.Options;
using IOFile = System.IO.File;

namespace OpenSkyBackend.Controllers
{
    [ApiController]
    public class StateVectorController : ControllerBase
    {
        private readonly ILogger<StateVectorController> logger;
        private readonly ApplicationOptions applicationOptions;
        private readonly OpenSkyClient client;

        public StateVectorController(ILogger<StateVectorController> logger, IOptions<ApplicationOptions> applicationOptions, OpenSkyClient client)
        {
            this.logger = logger;
            this.applicationOptions = applicationOptions.Value;
            this.client = client;
        }

        [HttpGet]
        [Route("/states/all")]
        public async Task<IActionResult> Get([FromQuery] StateVectorsRequestDto request, CancellationToken cancellationToken)
        {
            if (request == null)
            {
                return BadRequest("Invalid Request");
            }

            // Prepare some data for the OpenSkyClient request:
            Credentials credentials = GetCredentials();
            BoundingBox boundingBox = GetBoundingBoxFromRequest(request);
            TimeSpan refreshInterval = GetRefreshInterval();

            Response.Headers.Add("Content-Type", "text/event-stream");
            Response.Headers.Add("Cache-Control", "no-cache");

            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    // Get the data for the given Request:
                    var data = await GetDataAsync(request.Time, request.Icao24, boundingBox, credentials, cancellationToken);

                    if(data == null)
                    {
                        logger.LogInformation("No Data received. See Error Logs for details. Skipping Event ...");

                        continue;
                    }

                    // Serialize as a Json String:
                    var dataAsJson = JsonSerializer.Serialize(data);

                    // Send the data as JSON over the wire:
                    await Response.WriteAsync($"data: {dataAsJson}\r\r");

                    Response.Body.Flush();
                } 
                catch(Exception e)
                {
                    logger.LogError(e, "Requesting Data failed");
                }

                await Task.Delay(refreshInterval);
            }

            return Ok();
        }

        private BoundingBox GetBoundingBoxFromRequest(StateVectorsRequestDto request)
        {
            if (request == null)
            {
                return null;
            }

            if (request.LaMin.HasValue && request.LoMin.HasValue && request.LaMax.HasValue && request.LoMax.HasValue)
            {
                return new BoundingBox
                {
                    LaMin = request.LaMin.Value,
                    LoMin = request.LoMin.Value,
                    LaMax = request.LaMax.Value,
                    LoMax = request.LoMax.Value
                };
            }

            return null;
        }

        private Credentials GetCredentials()
        {
            if (applicationOptions == null)
            {
                return null;
            }

            var filename = applicationOptions.CredentialsFile;

            if (string.IsNullOrWhiteSpace(filename))
            {
                return null;
            }

            var content = IOFile.ReadAllText(applicationOptions.CredentialsFile);

            var document = JsonDocument.Parse(content);
            var element = document.RootElement;

            return new Credentials
            {
                Username = element.GetProperty("username").GetString(),
                Password = element.GetProperty("password").GetString()
            };
        }

        private TimeSpan GetRefreshInterval()
        {
            if (applicationOptions == null)
            {
                return TimeSpan.FromSeconds(10);
            }

            if (!applicationOptions.RefreshInterval.HasValue)
            {
                return TimeSpan.FromSeconds(10);
            }

            return TimeSpan.FromSeconds(applicationOptions.RefreshInterval.Value);
        }

        private async Task<StateVectorResponseDto> GetDataAsync(int? time, string icao24, BoundingBox boundingBox, Credentials credentials, CancellationToken cancellationToken)
        {
            try
            {
                var response = await client.GetAllStateVectorsAsync(time, icao24, boundingBox, credentials, cancellationToken);

                return ConvertStateVectorResponse(response);
            }
            catch (Exception e)
            {
                logger.LogError(e, $"Requesting Data failed (time = {time}, icao24 = {icao24}, bb({boundingBox?.LaMin},{boundingBox?.LoMin},{boundingBox?.LaMax},{boundingBox?.LoMax})");

                return null;
            }
        }

        private StateVectorResponseDto ConvertStateVectorResponse(StateVectorResponse response)
        {
            if(response == null)
            {
                return null;
            }

            return new StateVectorResponseDto
            {
                Time = response.Time,
                States = ConvertStates(response.States)
            };
        }

        private StateVectorDto[] ConvertStates(StateVector[] states)
        {
            if(states == null)
            {
                return null;
            }

            return states
                .Select(x => ConvertState(x))
                .ToArray();
        }

        private StateVectorDto ConvertState(StateVector state)
        {
            if(state == null)
            {
                return null;
            }

            return new StateVectorDto
            {
                BarometricAltitude = state.BarometricAltitude,
                CallSign = state.CallSign,
                GeometricAltitudeInMeters = state.GeometricAltitudeInMeters,
                Icao24 = state.Icao24,
                LastContact = state.LastContact,
                Latitude = state.Latitude,
                Longitude = state.Longitude,
                OnGround = state.OnGround,
                OriginCountry = state.OriginCountry,
                PositionSource = ConvertPositionSource(state.PositionSource),
                Sensors = state.Sensors,
                Spi = state.Spi,
                Squawk = state.Squawk,
                TimePosition = state.TimePosition,
                TrueTrack = state.TrueTrack,
                Velocity = state.Velocity,
                VerticalRate = state.VerticalRate
            };

            throw new NotImplementedException();
        }

        private PositionSourceEnumDto ConvertPositionSource(PositionSourceEnum? positionSource)
        {
            if(positionSource == null)
            {
                return PositionSourceEnumDto.Unknown;
            }

            switch(positionSource.Value)
            {
                case PositionSourceEnum.ASBD:
                    return PositionSourceEnumDto.ASBD;
                case PositionSourceEnum.ASTERIX:
                    return PositionSourceEnumDto.ASTERIX;
                case PositionSourceEnum.MLAT:
                    return PositionSourceEnumDto.MLAT;
                default:
                    return PositionSourceEnumDto.Unknown;
            }
        }
    }
}
```

### Wiring the things: The Startup class ###

An ASP.NET Core applications requires a ``Startup`` class (or any class attributed as ``[Startup]``) to wire up 
the Dependency Injection container and configure the Middleware. In the Startup class for the project we are also 
setting a CORS Policy and add it to all Controllers:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using OpenSkyBackend.Options;
using OpenSkyRestClient;
using System;

namespace OpenSkyBackend
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            services.AddCors(options =>
            {
                options.AddPolicy("CorsPolicy", policyBuilder => policyBuilder
                        .WithOrigins("http://localhost:4200", "http://localhost:8080", "http://localhost:9000")
                        .SetIsOriginAllowedToAllowWildcardSubdomains()
                        .AllowAnyMethod()
                        .AllowAnyHeader()
                        .AllowCredentials());
            });

            services
                .AddOptions()
                .Configure<ApplicationOptions>(Configuration.GetSection("Application"));

            ConfigureApplicationService(services);

            services.AddControllers();
        }

        private void ConfigureApplicationService(IServiceCollection services)
        {
            services.AddSingleton(new OpenSkyClient());
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }

            app.UseCors("CorsPolicy");
            
            app.UseRouting();
            app.UseAuthorization();

            app.UseEndpoints(endpoints =>
            {
                endpoints
                    .MapDefaultControllerRoute()
                    .RequireCors("CorsPolicy");
            });
        }
    }
}
```

And that's it for the Backend!

## Displaying Flights on a Map: The Frontend ##

The Frontend starts with installing the Angular CLI:

```
> npm install -g @angular/cli
```

Next we are scaffolding the ``opensky-app`` project by running:

```
> ng new opensky-app
```

And then we are installing the Mapbox GL JS viewer and its types:

```
> npm install mapbox-gl
> npm install @types/mapbox-gl --save-dev
```

And now we start the implementation.

### Deserializing the JSON messages: The Client Data Model ###

In TypeScript we want to have a strongly typed data model, just like in C\#. So for the ``StateVectorResponse`` we 
are writing the contracts matching the Backend JSON property names:

```typescript
export enum PositionSourceEnum {
    // Unknown.
    Unknown = "Unknown",
    // ASBD.
    ASBD = "ASBD",
    //ASTERIX.
    ASTERIX = "ASTERIX",
    // MLAT.
    MLAT = "MLAT"
};

export interface StateVectorResponse {
    
    // The time which the state vectors in this response are associated with. All vectors 
    // represent the state of a vehicle with the interval [time−1, time].
    time: number;

    // The state vectors.    
    states: Array<StateVector>;
}

export interface StateVector {
        // Unique ICAO 24-bit address of the transponder in hex string representation.
        icao24: string;

        // Callsign of the vehicle (8 chars). Can be null if no callsign has been received.
        callsign: string;

        // Country name inferred from the ICAO 24-bit address.
        origin_country: string;
        
        // Unix timestamp (seconds) for the last position update. Can be null if no position 
        // report was received by OpenSky within the past 15s.
        time_position?:number;

        // Unix timestamp (seconds) for the last update in general. This field is updated for 
        // any new, valid message received from the transponder.
        last_contact?: number;

        // WGS-84 longitude in decimal degrees. Can be null.
        longitude?: number;

        // WGS-84 latitude in decimal degrees. Can be null.
        latitude?: number;

        // Barometric altitude in meters. Can be null.
        baro_altitude?: number;

        // Boolean value which indicates if the position was retrieved from a surface position report.
        on_ground: boolean;

        // Velocity over ground in m/s. Can be null.
        velocity?: number;

        // True track in decimal degrees clockwise from north (north=0°). Can be null.
        true_track?: number;

        // Vertical rate in m/s. A positive value indicates that the airplane is climbing, 
        // a negative value indicates that it descends. Can be null.
        vertical_rate?: number;

        // IDs of the receivers which contributed to this state vector. Is null if no filtering for sensor was used in the request.
        sensors?: Array<number>;

        // Geometric altitude in meters. Can be null.
        geo_altitude?: number;

        // The transponder code aka Squawk. Can be null.
        squawk: string;

        // Whether flight status indicates special purpose indicator.
        spi: boolean;

        // Origin of this state’s position: 0 = ADS-B, 1 = ASTERIX, 2 = MLAT
        position_source: PositionSourceEnum;
};
```

It's more or less a one-to-one copy and paste from the ASP.NET Core application.

### Displaying the Vector Tiles: The MapComponent ###

I am not including any additional libraries except the MapMapbox GL JS client. The ``MapComponent`` is responsible for 
displaying a map. We can see, that it basically only contains a ``<div>`` element, that the map will be rendered to. The 
actual setup of the map is done in the ``MapService`` injected into the ``MapComponent``:

```typescript
import { ElementRef, EventEmitter, Output, ViewChild } from '@angular/core';
import { AfterViewInit, ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { LngLatLike, Style } from 'mapbox-gl';
import { MapService } from '../services/map.service';

@Component({
    selector: 'mapbox-map',
    template: '<div #container></div>',
    styles: [
      `
        :host {
          display: block;
        }

        div {
          height: 100%;
          width: 100%;
        }
      `,
    ],
    changeDetection: ChangeDetectionStrategy.OnPush,
  })
  export class MapComponent implements AfterViewInit {
    
    @ViewChild('container', { static: true }) mapContainer: ElementRef;

    @Input() mapStyle: Style | string;
    @Input() center?: LngLatLike;
    @Input() zoom?: number;
    
    constructor(private mapService: MapService) {

    }

    ngAfterViewInit(): void {
        this.mapService.buildMap(this.mapContainer.nativeElement, this.mapStyle, this.center, this.zoom);
    }
  
    ngOnDestroy() {
        this.mapService.destroyMap();
      }
}
```

### Creating the Map, Registering Events and Displaying Markers: The MapService ###

The ``MapService`` is responsible for actually creating the Mapbox GL JS map, send an event as soon as the 
map has been fully loaded, display markers and handle clicks on the markers.

I don't want to overthink small projects anymore, so I am not working with libraries like ngrx. The ``MapService`` 
simply contains some rxjs ``Subjects``, that could be subscribed on for events. Interested parties should directly 
inject the ``MapService`` singleton, because I don't want to deal with ``@Output`` events.

Is it tightly coupled? For sure! Is it simple? You bet!

```typescript
import { Injectable, NgZone } from "@angular/core";
import * as mapboxgl from 'mapbox-gl';
import { LngLatLike, MapboxOptions, GeoJSONSource, Style, MapLayerMouseEvent, MapboxGeoJSONFeature } from 'mapbox-gl';
import { BehaviorSubject, Observable, of, ReplaySubject } from "rxjs";
import { first } from 'rxjs/operators';
import { StateVector } from '../model/state-vector';
import { LoggerService } from './logger.service';

@Injectable({
    providedIn: 'root',
})
export class MapService {

    public mapInstance: mapboxgl.Map;

    private mapCreated$: BehaviorSubject<boolean>;
    private mapLoaded$: BehaviorSubject<boolean>;
    private markerClick$: ReplaySubject<MapboxGeoJSONFeature[]>;
    private markers: GeoJSON.FeatureCollection<GeoJSON.Geometry>;

    constructor(private ngZone: NgZone, private loggerService: LoggerService) {
        this.mapCreated$ = new BehaviorSubject<boolean>(false);
        this.mapLoaded$ = new BehaviorSubject<boolean>(false);
        this.markerClick$ = new ReplaySubject();

        this.markers = {
            type: 'FeatureCollection',
            features: [],
        };
    }

    buildMap(mapContainer: string | HTMLElement, style?: Style | string, center?: LngLatLike, zoom?: number) {
        this.ngZone.onStable.pipe(first()).subscribe(() => {
            this.createMap(mapContainer, style, center, zoom);
            this.registerEvents();
        });
    }

    private createMap(mapContainer: string | HTMLElement, style?: Style | string, center?: LngLatLike, zoom?: number): void {
        const mapboxOptions: MapboxOptions = {
            container: mapContainer,
            style: style,
            center: center,
            zoom: zoom
        };

        this.mapInstance = new mapboxgl.Map(mapboxOptions);
    }

    private registerEvents(): void {
        this.mapInstance.on('load', () => {
            this.ngZone.run(() => {
                this.mapLoaded$.next(true);
            });
        });

        this.mapInstance.on('style.load', () => {
            // We cannot reference the mapInstance in the callback, so store
            // it temporarily here:
            const map = this.mapInstance;
            const markers = this.markers;
            // We want a custom icon for the GeoJSON Points, so we need to load 
            // an image like described here: https://docs.mapbox.com/mapbox-gl-js/example/add-image/
            map.loadImage('http://localhost:4200/assets/plane.png', function (error, image) {

                if (error) {
                    throw error;
                }

                map.addImage("icon_plane", image);

                map.addSource('markers', {
                    "type": "geojson",
                    "data": markers
                });

                map.addLayer({
                    "id": "markers",
                    "source": "markers",
                    "type": "symbol",
                    "layout": {
                        "icon-image": "icon_plane",
                        "icon-allow-overlap": true,
                        "icon-rotate": {
                            "property": "icon_rotate",
                            "type": "identity"
                        }
                    }
                });
            });
        });

        this.mapInstance.on('click', 'markers', (e: MapLayerMouseEvent) => {
            this.ngZone.run(() => {
                this.markerClick$.next(e.features);
            });
        });


        this.mapInstance.on('mousemove', 'markers', (e) => {
            this.mapInstance.getCanvas().style.cursor = 'pointer';
        });

        this.mapInstance.on("mouseleave", "markers", () => {
            this.mapInstance.getCanvas().style.cursor = '';
        });
    }

    onMapLoaded(): Observable<boolean> {
        return this.mapLoaded$.asObservable();
    }

    onMapCreated(): Observable<boolean> {
        return this.mapCreated$.asObservable();
    }

    onMarkerClicked(): Observable<MapboxGeoJSONFeature[]> {
        return this.markerClick$.asObservable();
    }

    displayStateVectors(states: Array<StateVector>): void {
        if (this.mapInstance) {

            this.markers.features = states
                .filter(state => state.longitude && state.latitude)
                .map(state => this.convertStateVectorToGeoJson(state));

            const source: GeoJSONSource = <GeoJSONSource>this.mapInstance.getSource('markers');

            source.setData(this.markers);
        }

    }

    private convertStateVectorToGeoJson(stateVector: StateVector): GeoJSON.Feature<GeoJSON.Point> {

        const feature: GeoJSON.Feature<GeoJSON.Point> = {
            type: 'Feature',
            properties: {
                'flight.icao24': stateVector.icao24,
                'flight.last_contact': stateVector.last_contact,
                'flight.longitude': stateVector.longitude,
                'flight.latitude': stateVector.latitude,
                'flight.origin_country': stateVector.origin_country
            },
            geometry: {
                type: 'Point',
                coordinates: [stateVector.longitude, stateVector.latitude]
            }
        };

        if (stateVector.true_track) {
            feature.properties['icon_rotate'] = stateVector.true_track * -1;
        }

        return feature;
    }

    destroyMap() {
        this.loggerService.log("Destroying Map ...");

        if (this.mapInstance) {
            this.mapInstance.remove();
        }
    }
}
```

To display a custom icon for the Marker I am loading an image (``plane.png``) from the ``/assets`` folder as described 
in the documentation:

* [https://docs.mapbox.com/mapbox-gl-js/example/add-image/](https://docs.mapbox.com/mapbox-gl-js/example/add-image/)

As for the markers... You might be tempted to use the ``mapbox.Marker`` for displaying the planes (at least I was), but 
doing so is brutally slow for the 5000 planes we are going to display (I confirm). Instead I create a GeoJSON layer like 
described here:

* [https://docs.mapbox.com/help/tutorials/custom-markers-gl-js/](https://docs.mapbox.com/help/tutorials/custom-markers-gl-js/)

And I am updating the Markers using the ``setData`` method on the Source Layer to write the Markers in 
one batch and use the GPU. At the same time we are also rotating the icon to the ``true_track`` received from 
the API, so we know where the plane is heading to.

### Getting the Push Messages: SseService ###

The Backend pushes the data using Server Sent Events. HTML5 comes with an ``EventSource`` to handle streams of 
``MessageEvent``. This ``EventSource`` will now be wrapped in a small Angular Service, that returns an Observable 
from the Messages:

```typescript
import {Injectable, NgZone} from "@angular/core";
import {Observable} from "rxjs";

@Injectable({
    providedIn: "root"
})
export class SseService {
    constructor(private ngZone: NgZone) {}

    asObservable(url: string): Observable<MessageEvent<any>> {
        return new Observable<MessageEvent<any>>(observer => {
            const eventSource = new EventSource(url);

            eventSource.onmessage = (event) => {
                this.ngZone.run(() => observer.next(event));
            };

            eventSource.onerror = (error) => {
                this.ngZone.run(() => observer.error(error));
            }
        });
    }
}
```
### Wiring the pieces: The AppComponent ###

In the ``app.component.html`` we are using the ``<mapbox-map>`` defined in the ``MapComponent``. When a plane is clicked, 
we want to display some flight information, which will be shown in a sidebar.

```html
<div id="heading">
  <h1>Flight Tracker</h1>
  <p>
      Click on a plane to get its associated state vector.
  </p>
  <pre id="features">{{features}}</pre>
</div>

<div class="main-container">
  <mapbox-map [mapStyle]="mapStyle" [center]="mapCenter" [zoom]="mapZoom"></mapbox-map>
</div>
```

In the ``app.component.scss`` a little styling is added:

```css
body {
    margin: 0;
  }

mapbox-map {
    height: 100%;
    width: 100%;
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
    width: 300px;
    overflow: auto;
    z-index: 9;
}

.main-container {
    position: absolute;
    top: 0;
    bottom: 0;
    height: 100%;
    width: 100%;
}
```

And the ``app.component.ts`` now makes use of the ``MapService`` and ``SseService`` to show the planes. Using the 
``MapService`` we can register on click events and get notified when a map has been loaded. The ``SseService`` is 
used to receive events from a URL and transform them into a ``StateVectorResponse``:

```
import { Component, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { LngLat, LngLatLike, MapLayerMouseEvent, Style } from 'mapbox-gl';
import { Observable, Subject, Subscription } from 'rxjs';
import { filter, map, takeUntil } from 'rxjs/operators'
import { environment } from 'src/environments/environment';
import { StateVectorResponse } from './model/state-vector';
import { LoggerService } from './services/logger.service';
import { MapService } from './services/map.service';
import { SseService } from './services/sse.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {

  private readonly destroy$ = new Subject();

  mapZoom: number;
  mapStyle: string;
  mapCenter: LngLatLike;
  isMapLoaded: boolean;
  features: string;

  constructor(private ngZone: NgZone, private loggerService: LoggerService, private sseService: SseService, private mapService: MapService) {
    this.mapStyle = "http://localhost:9000/static/style/osm_liberty/osm_liberty.json";
    this.mapCenter = new LngLat(7.628202, 51.961563);
    this.mapZoom = 10;
    this.features = "Select a plane on the map\n to display its data.";
  }

  ngOnInit(): void {

    this.mapService.onMapLoaded()
      .pipe(takeUntil(this.destroy$))
      .subscribe((value) => {
        this.isMapLoaded = value;
      });

    this.mapService.onMarkerClicked()
      .pipe(takeUntil(this.destroy$))
      .subscribe((value: mapboxgl.MapboxGeoJSONFeature[]) => {
        this.handleMarkerClick(value);
      });

    this.sseService
      .asObservable(environment.apiUrl)
      .pipe(
        takeUntil(this.destroy$),
        map(x => <StateVectorResponse>JSON.parse(x.data)))
      .subscribe(x => this.updateStateVectors(x));

  }

  updateStateVectors(stateVectorResponse: StateVectorResponse): void {
    if (this.isMapLoaded && stateVectorResponse?.states) {
      this.mapService.displayStateVectors(stateVectorResponse.states);
    }
  }

  handleMarkerClick(features: mapboxgl.MapboxGeoJSONFeature[]): void {
    if (features && features.length > 0) {
      this.features = JSON.stringify(features[0].properties, null, 2);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

And that's it!

## Conclusion ##

You now have a flight tracker, that will be updated using a Server-side push. It has been really simple 
to implement a Frontend with Angular and honestly: It's easy, when someone provides you almost all type 
definitions. 

