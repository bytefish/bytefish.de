title: Working with Elasticsearch in .NET
date: 2016-04-15 21:39
tags: csharp, elasticsearch
category: csharp
slug: elasticsearch_net
author: Philipp Wagner
summary: This article shows how to work with Elasticsearch from .NET.

I needed to visualize some data, so I wrote a sample .NET application to see how to work with [Elasticsearch] and [Kibana]. 

The [elastic] product page describes [Elasticsearch] as: 

> [...] a distributed, open source search and analytics engine, designed for horizontal 
> scalability, reliability, and easy management". 

Basically [Elasticsearch] is a NoSQL database, that makes it possible to index data in form of JSON documents. In constrast to a traditional relational database the data in [Elasticsearch] 
is not stored in separate tables, but stored in JSON documents containing all data neccessary for a query.

At the very core of [Elasticsearch] is [Apache Lucene], which is a text search engine library written entirely in Java. [Apache Lucene] is used to build a search index over the 
data, and makes it possible to efficiently query the large datasets. In order to make writing queries easier [Elasticsearch] provides a custom query language called the [Query DSL]. 

## Sources ##

You can find the full source code example in my git repository at:

* [https://github.com/bytefish/ElasticSearchExperiment](https://github.com/bytefish/ElasticSearchExperiment)

This post was based on Elasticsearch 2, but the example is available for:

* Elasticsearch 2
* Elasticsearch 6
* Elasticsearch 7

Please see the Releases at: 

* [https://github.com/bytefish/ElasticSearchExperiment/releases](https://github.com/bytefish/ElasticSearchExperiment/releases)

## What we are going to build ##

The idea is to store the hourly weather data of 1,600 U.S. locations in an [Elasticsearch] database and visualize it with [Kibana].

The final result will visualize the average temperature in March 2015 on a tile map:

<a href="/static/images/blog/elasticsearch_net/kibana.jpg">
	<img src="/static/images/blog/elasticsearch_net/thumbs/kibana_thumb.jpg" alt="Kibana Map Weather Visualization" />
</a>

## Prerequisites ##

### Elasticsearch ###

This example is based on:

* [Elasticsearch 2.3.1](https://www.elastic.co/downloads/elasticsearch)
* [Kibana 4.5.0](https://www.elastic.co/downloads/kibana)

Make sure your ``JAVA_HOME`` environment variable is set, before starting both. 

In Windows this can be done by running (set your JDK version accordingly):

```batch
SET "JAVA_HOME=C:\Program Files\Java\jre1.8.0_73\"
```

### Dataset ###

The data is the [Quality Controlled Local Climatological Data (QCLCD)]: 

> Quality Controlled Local Climatological Data (QCLCD) consist of hourly, daily, and monthly summaries for approximately 
> 1,600 U.S. locations. Daily Summary forms are not available for all stations. Data are available beginning January 1, 2005 
> and continue to the present. Please note, there may be a 48-hour lag in the availability of the most recent data.

The data is available as CSV files at:

* [http://www.ncdc.noaa.gov/orders/qclcd/](http://www.ncdc.noaa.gov/orders/qclcd/)

We are going to use the data from March 2015, which is located in the zipped file ``QCLCD201503.zip``.

## Parsing the CSV Dataset ###

The example is going to use [TinyCsvParser] to read in the CSV data.

You can install [TinyCsvParser] from NuGet with:

```
Install-Package TinyCsvParser
```

### Model ###

The first thing is to model the data we are interested in. The weather data is contained in the file ``201503hourly.txt`` and the list 
of available weather stations is given in the file ``201503station.txt``. The weather stations are identified by their ``WBAN`` number 
(*W*eather-*B*ureau-*A*rmy-*N*avy).

#### LocalWeatherData ####

The local weather data in ``201503hourly.txt`` has more than 30 columns, but we are only interested in the WBAN Identifier (Column 0), 
Time of measurement (Columns 1, 2), Sky Condition (Column 4), Air Temperature (Column 12), Wind Speed (Column 24) and Pressure (Column 30).

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace ElasticSearchExample.CSV.Model
{
    public class LocalWeatherData
    {
        public string WBAN { get; set; }

        public DateTime Date { get; set; }

        public TimeSpan Time { get; set; }

        public string SkyCondition { get; set; }

        public float DryBulbCelsius { get; set; }

        public float WindSpeed { get; set; }

        public float StationPressure { get; set; }
    }
}
```

#### Station ####

The Station data has only 14 properties, the model is going to contain all properties.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticSearchExample.CSV.Model
{
    public class Station
    {
        public string WBAN { get; set; }

        public string WMO { get; set; }

        public string CallSign { get; set; }

        public string ClimateDivisionCode { get; set; }

        public string ClimateDivisionStateCode { get; set; }

        public string ClimateDivisionStationCode { get; set; }

        public string Name { get; set; }

        public string State { get; set; }

        public string Location { get; set; }

        public float Latitude { get; set; }

        public float Longitude { get; set; }

        public string GroundHeight { get; set; }         

        public string StationHeight { get; set; }  

        public string Barometer { get; set; }  

        public string TimeZone { get; set; }            
    }
}
```

### Mapping ###

#### LocalWeatherDataMapper ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticSearchExample.CSV.Model;
using TinyCsvParser.Mapping;
using TinyCsvParser.TypeConverter;

namespace ElasticSearchExample.CSV.Mapper
{
    public class LocalWeatherDataMapper : CsvMapping<LocalWeatherData>
    {
        public LocalWeatherDataMapper()
        {
            MapProperty(0, x => x.WBAN);
            MapProperty(1, x => x.Date, new DateTimeConverter("yyyyMMdd"));
            MapProperty(2, x => x.Time, new TimeSpanConverter("hhmm"));
            MapProperty(4, x => x.SkyCondition);
            MapProperty(12, x => x.DryBulbCelsius);
            MapProperty(24, x => x.WindSpeed);
            MapProperty(30, x => x.StationPressure);
        }
    }
}
```

#### StationMapper ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticSearchExample.CSV.Model;
using TinyCsvParser.Mapping;

namespace ElasticSearchExample.CSV.Mapper
{
    public class StationMapper : CsvMapping<Station>
    {
        public StationMapper()
        {
            MapProperty(0, x => x.WBAN);
            MapProperty(1, x => x.WMO);
            MapProperty(2, x => x.CallSign);
            MapProperty(3, x => x.ClimateDivisionCode);
            MapProperty(4, x => x.ClimateDivisionStateCode);
            MapProperty(5, x => x.ClimateDivisionStationCode);
            MapProperty(6, x => x.Name);
            MapProperty(7, x => x.State);
            MapProperty(8, x => x.Location);
            MapProperty(9, x => x.Latitude);
            MapProperty(10, x => x.Longitude);
            MapProperty(11, x => x.GroundHeight);
            MapProperty(12, x => x.StationHeight);
            MapProperty(13, x => x.Barometer);
            MapProperty(14, x => x.TimeZone);
        }
    }
}
```

### Parsers ###

Finally the Parsers for the Weather Data and the Station list can be created. The CSV files are using different column delimiters for the 
data. The data in the Station list is delimited by a ``|`` and the data in the weather data is delimited by a ``,``. 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticSearchExample.CSV.Mapper;
using ElasticSearchExample.CSV.Model;
using TinyCsvParser;

namespace ElasticSearchExample.CSV.Parser
{
    public static class Parsers
    {
        public static CsvParser<Station> StationParser
        {
            get
            {
                CsvParserOptions csvParserOptions = new CsvParserOptions(true, new[] { '|' });

                return new CsvParser<Station>(csvParserOptions, new StationMapper());
            }
        }

        public static CsvParser<LocalWeatherData> LocalWeatherDataParser
        {
            get
            {
                CsvParserOptions csvParserOptions = new CsvParserOptions(true, new[] { ',' });

                return new CsvParser<LocalWeatherData>(csvParserOptions, new LocalWeatherDataMapper());
            }
        }
    }
}
```

## Elasticsearch ##

### Prerequisites ###

[Elasticsearch] can be queried with a RESTful API, which is described in the very good [Elasticsearch Reference]. In this example we are using [NEST], which is the official .NET client for Elasticsearch.

You can install [NEST] from NuGet:

```
Install-Package NEST
```

### Model and Mapping ###

If you are working with [Elasticsearch] the data needs to modeled different to a Relational Database. Instead of modelling relations between data in separate files, you need to store all data neccessary 
for a query in a document. The Elasticsearch documentation states on [Handling Relationships](https://www.elastic.co/guide/en/elasticsearch/guide/current/relations.html):

> Elasticsearch, like most NoSQL databases, treats the world as though it were flat. An index is a flat collection of independent documents. 
> A single document should contain all of the information that is required to decide whether it matches a search request.

So the Elasticsearch mindset is to denormalize the data as much as possible, because the inverted index is built over the documents and only this allows efficient queries.

I have decided to use the [NEST] attributes to create the initial index mapping, so the entities are the model and the mapping at the same time. The attributes help 
Elasticsearch to correctly map the data, when adding new entities to the search index. It's also necessary, because we want to create a visualization over the 
GPS locations of the stations and need to explictly map the values to an Elasticsearch [GeoPoint Type](https://www.elastic.co/guide/en/elasticsearch/reference/1.4/mapping-geo-point-type.html).

#### LocalWeatherData ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Nest;
using System;

namespace ElasticSearchExample.Elastic.Model
{
    public class LocalWeatherData
    {
        [Nested(IncludeInParent=true)]
        public Station Station { get; set; }

        [Date]
        public DateTime DateTime { get; set; }

        [Number]
        public float Temperature { get; set; }

        [Number]
        public float WindSpeed { get; set; }

        [Number]
        public float StationPressure { get; set; }

        [String]
        public string SkyCondition { get; set; }
    }
}
```

#### Station ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Nest;
using System;

namespace ElasticSearchExample.Elastic.Model
{
    public class Station
    {
        [String]
        public string WBAN { get; set; }

        [String]
        public string Name { get; set; }

        [String]
        public string State { get; set; }

        [String]
        public string Location { get; set; }

        [GeoPoint]
        public GeoLocation GeoLocation { get; set; }
    }
}
```

### Client ###

[NEST] is the high-level client to interface with an Elasticsearch instance. In the example I am using a wrapper around the [IElasticClient](https://www.elastic.co/guide/en/elasticsearch/client/net-api/1.x/nest-connecting.html), 
that makes it possible to create the search index and perform bulk inserts. In order to use the mapping attributes, we are doing an ``AutoMap``, when defining 
the entity mapping.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Elasticsearch.Net;
using ElasticSearchExample.Elastic.Client.Settings;
using log4net;
using Nest;
using System;
using System.Collections.Generic;
using System.Reflection;

namespace ElasticSearchExample.Elastic.Client
{
    public class ElasticSearchClient<TEntity>
        where TEntity : class
    {
        private static ILog log = LogManager.GetLogger(MethodBase.GetCurrentMethod().DeclaringType);

        public readonly string IndexName;

        protected readonly IElasticClient Client;

        public ElasticSearchClient(IElasticClient client, string indexName)
        {
            IndexName = indexName;
            Client = client;
        }

        public ElasticSearchClient(ConnectionString connectionString, string indexName)
            : this(CreateClient(connectionString), indexName)
        {
        }

        public ICreateIndexResponse CreateIndex()
        {
            var response = Client.IndexExists(IndexName);
            if (response.Exists)
            {
                return null;
            }
            return Client.CreateIndex(IndexName, index =>
                index.Mappings(ms =>
                    ms.Map<TEntity>(x => x.AutoMap())));
        }

        public IBulkResponse BulkInsert(IEnumerable<TEntity> entities)
        {
            var request = new BulkDescriptor();
            
            foreach (var entity in entities)
            {
                request
                    .Index<TEntity>(op => op
                        .Id(Guid.NewGuid().ToString())
                        .Index(IndexName)
                        .Document(entity));
            }

            return Client.Bulk(request);
        }

        private static IElasticClient CreateClient(ConnectionString connectionString)
        {
            var node = new UriBuilder(connectionString.Scheme, connectionString.Host, connectionString.Port);
            var connectionPool = new SingleNodeConnectionPool(node.Uri);
            var connectionSettings = new ConnectionSettings(connectionPool);

            return new ElasticClient(connectionSettings);
        }
    }
}
```

## Converting between the CSV and Elasticsearch model ##

What's left is converting between the CSV model and the flat Elasticsearch representation.

### LocalWeatherDataConverter ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Nest;

using CsvStationType = ElasticSearchExample.CSV.Model.Station;
using CsvLocalWeatherDataType = ElasticSearchExample.CSV.Model.LocalWeatherData;

using ElasticStationType = ElasticSearchExample.Elastic.Model.Station;
using ElasticLocalWeatherDataType = ElasticSearchExample.Elastic.Model.LocalWeatherData;


namespace ElasticSearchExample.Converter
{
    public static class LocalWeatherDataConverter
    {
        public static ElasticLocalWeatherDataType Convert(CsvStationType station, CsvLocalWeatherDataType localWeatherData)
        {
            return new ElasticLocalWeatherDataType
            {
                Station = new ElasticStationType 
                {
                    WBAN = station.WBAN,
                    Name = station.Name,
                    Location = station.Location,
                    State = station.State,
                    GeoLocation = new GeoLocation(station.Latitude, station.Longitude)
                },
                DateTime = localWeatherData.Date.Add(localWeatherData.Time),
                SkyCondition = localWeatherData.SkyCondition,
                StationPressure = localWeatherData.StationPressure,
                Temperature = localWeatherData.DryBulbCelsius,
                WindSpeed = localWeatherData.WindSpeed
            };
        }
    }
}
```

## Client ##

Now it's time to combine the pieces into an application. The simple command line application reads the CSV weather data and bulk inserts it into 
the Elasticsearch. You can see how to create the ``ElasticSearchClient``, create the search index and parse the CSV data. I think the program 
is very succinct to read, but please comment below if something is unclear.

### Program ###

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticSearchExample.CSV.Parser;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using TinyCsvParser;

using CsvStationType = ElasticSearchExample.CSV.Model.Station;
using CsvLocalWeatherDataType = ElasticSearchExample.CSV.Model.LocalWeatherData;

using ElasticLocalWeatherDataType = ElasticSearchExample.Elastic.Model.LocalWeatherData;

using ElasticSearchExample.Converter;
using ElasticSearchExample.Utils;
using ElasticSearchExample.Elastic.Client;
using ElasticSearchExample.Elastic.Client.Settings;

namespace ElasticSearchExample.Client
{
    class Program
    {
        public static void Main(string[] args)
        {
            var connectionString = new ConnectionString("http", "localhost", 9200);

            // Create a new Client, that writes the Weater Data and creates the Index weather_data:
            var client = new ElasticSearchClient<ElasticLocalWeatherDataType>(connectionString, "weather_data");

            // Creates the Index, if neccessary:
            client.CreateIndex();

            // Bulk Insert Data:
            foreach(var batch in GetData().Batch(100)) 
            {
                var response = client.BulkInsert(batch);
            }
        }

        private static IEnumerable<ElasticLocalWeatherDataType> GetData()
        {
            // Create Lookup Dictionary to map stations from:
            IDictionary<string, CsvStationType> stations =
                GetStations("C:\\Users\\philipp\\Downloads\\csv\\201503station.txt")
                .ToDictionary(station => station.WBAN, station => station);

            // Create the flattened Elasticsearch entry:
            return GetLocalWeatherData("C:\\Users\\philipp\\Downloads\\csv\\201503hourly.txt")
                .Where(x => stations.ContainsKey(x.WBAN))
                .Select(x =>
                {
                    var station = stations[x.WBAN];

                    return LocalWeatherDataConverter.Convert(station, x);
                });
        }

        private static IEnumerable<CsvStationType> GetStations(string fileName)
        {
            return Parsers.StationParser
                .ReadFromFile(fileName, Encoding.ASCII)
                .Where(x => x.IsValid)
                .Select(x => x.Result)
                .AsEnumerable();                
        }

        private static IEnumerable<CsvLocalWeatherDataType> GetLocalWeatherData(string fileName)
        {
            return Parsers.LocalWeatherDataParser
                .ReadFromFile(fileName, Encoding.ASCII)
                .Where(x => x.IsValid)
                .Select(x => x.Result)
                .AsEnumerable();
        }
    }
}
```

## Visualizing the Data with Kibana ##

[Kibana] is a front-end to visualize the indexed data stored in an [Elasticsearch] database. It's possible to create various graphs (line charts, pie charts, tilemaps, ...) and combine the 
created visualizations into custom dashboards. [Kibana] also updates the dashboard as soon as new data is indexed in Elasticsearch, which is a really cool feature to show your customers.

In the following example I want to show how to create a Tile Map, that shows the Average temperature of March 2015.

### Starting Kibana ###

After starting the [Kibana] you can access the front-end using a browser and visiting:

```
http://localhost:5601
```

### 1. Configure the Index Pattern ###

In the example application the created index was called ``weather_data``. To visualize this index with [Kibana], an index pattern must be configured.

You are going to the *Settings* tab and set the *Index name or pattern* to ``weather_data``:

<a href="/static/images/blog/elasticsearch_net/01_create_tilemap_configure_index_pattern.jpg">
	<img src="/static/images/blog/elasticsearch_net/01_create_tilemap_configure_index_pattern.jpg" alt="Creating the Initial Index Pattern" />
</a>

### 2. Inspecting the Index Pattern ###

<a href="/static/images/blog/elasticsearch_net/02_create_tilemap_weather_data_mapping.jpg">
	<img src="/static/images/blog/elasticsearch_net/02_create_tilemap_weather_data_mapping.jpg" alt="Inspecting the Weather Data Index Pattern" />
</a>

### 3. Create the Tile Map Visualization ###

<a href="/static/images/blog/elasticsearch_net/03_create_tilemap_create_tilemap_visualization.jpg">
	<img src="/static/images/blog/elasticsearch_net/03_create_tilemap_create_tilemap_visualization.jpg" alt="Create Tile Map Visualization Step 1" />
</a>

### 4. Create the Visualization from a New Search ###

We haven't stored any searches over the index yet, so the tile map needs to be created from a new search:

<a href="/static/images/blog/elasticsearch_net/04_create_tilemap_new_search.jpg">
	<img src="/static/images/blog/elasticsearch_net/04_create_tilemap_new_search.jpg" alt="Create New Search for the Tile Map" />
</a>

### 5. Choosing the Geocordinates for the Tile Map markers ###

The indexed data contains the GPS coordinates of each station. We are going to choose these GPS positions as *Geo Coordinates*:

<a href="/static/images/blog/elasticsearch_net/05_create_tilemap_geo_coordinates.jpg">
	<img src="/static/images/blog/elasticsearch_net/05_create_tilemap_geo_coordinates.jpg" alt="Choose Geo Coordinates from the Index" />
</a>

### 6. Inspecting the Geo Coordinates ###

There is only one *Geo Position* property in the index. Kibana should automatically choose this property, but you should inspect to 
see if the correct values has been determined:

<a href="/static/images/blog/elasticsearch_net/06_create_tilemap_geo_coordinates_set.jpg">
	<img src="/static/images/blog/elasticsearch_net/06_create_tilemap_geo_coordinates_set.jpg" alt="Inspecting the Geocordinates" />
</a>


### 7. Adding the Average Temperature Value ###

We want to visualize the Average Temperature, add a new value. *Aggregation* must be set to ``Average`` and *Field* must be set to ``temperature``:

<a href="/static/images/blog/elasticsearch_net/07_create_tilemap_adding_temperature_value.jpg">
	<img src="/static/images/blog/elasticsearch_net/07_create_tilemap_adding_temperature_value.jpg" alt="Adding Value: Average Temperature" />
</a>


### 8. Adjusting the Interval ###

You don't see values yet. This is because of the search interval [Kibana] defaults to. The indexed data is from March 2015, but Kibana visualize only 
the latest 15 Minutes by default. You need to set the interval to a larger time interval, by adjusting it in the upper right part of the Kibana front-end.

I have highlighted it with a red marker in the following screenshot:

<a href="/static/images/blog/elasticsearch_net/08_create_tilemap_adjust_interval.jpg">
	<img src="/static/images/blog/elasticsearch_net/08_create_tilemap_adjust_interval.jpg" alt="Inspecting the Weather Data Index Pattern" />
</a>


### Final Visualization ###

And now you can enjoy the final visualization of the Average temperature in March 2015:

<a href="/static/images/blog/elasticsearch_net/kibana.jpg">
	<img src="/static/images/blog/elasticsearch_net/thumbs/kibana_thumb.jpg" alt="Kibana Map Weather Visualization" />
</a>

## Conclusion ##

Getting started with [Elasticsearch] was very easy. [NEST] is a fine library and exceptionally well documented. [Kibana] is a great front-end and it was easy to 
create simple visualizations, such as a tile map.

[elastic]: https://www.elastic.co/
[NEST]: https://github.com/elastic/elasticsearch-net
[Elasticsearch Reference]: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
[MIT License]: https://opensource.org/licenses/MIT
[Apache Lucene]: https://lucene.apache.org/
[Elasticsearch]: https://www.elastic.co/products/elasticsearch
[Kibana]: https://www.elastic.co/products/kibana
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser/
[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd
[Query DSL]: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
[Introducing the Query Language]: https://www.elastic.co/guide/en/elasticsearch/reference/current/_introducing_the_query_language.html

