title: Timeseries Databases Part 2: Writing Data to InfluxDB from .NET
date: 2019-02-10 14:04
tags: timeseries, influxdb, databases, dotnet, csharp
category: timeseries
slug: timeseries_databases_2_influxdb
author: Philipp Wagner
summary: This part shows how to use InfluxDB with .NET.

## What is InfluxDB? ##

[InfluxDB] is a database written specifically for handling time series data.

The [influxdata] website writes on [InfluxDB]:

> InfluxDB is a high-performance data store written specifically for time series data. It allows for high throughput 
> ingest, compression and real-time querying of that same data. InfluxDB is written entirely in Go and it compiles 
> into a single binary with no external dependencies.

In [Part 1] of the series I have shown how to parse the [DWD Open Data] dataset, which will be used in this article.

All code to reproduce the article can be found in my GitHub repository at:

* [https://github.com/bytefish/GermanWeatherDataExample](https://github.com/bytefish/GermanWeatherDataExample)

## The Dataset ##

The [DWD Open Data] portal of the [Deutscher Wetterdienst (DWD)] gives access to the historical weather data in Germany. I decided 
to use all available historical air temperature data for Germany given in a 10 minute resolution ([FTP Link]). If you want to recreate 
the example, you can find the list of CSV files in the GitHub repository at: [GermanWeatherDataExample/Resources/files.md].

The DWD dataset is given as CSV files and has a size of approximately 25.5 GB.

## Implementation ##

### The InfluxDB Line Protocol ###

[Line Protocol]: https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_reference/

The data points are written using the InfluxDB [Line Protocol], which has the following syntax:

```
<measurement>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]
```

The protocol has already been implemented for C\# by the very good [influxdb-csharp] library:

* https://github.com/influxdata/influxdb-csharp

[influxdb-csharp]: https://github.com/influxdata/influxdb-csharp

### Writing to InfluxDB: The LocalWeatherDataBatchProcessor ###

The ``LocalWeatherDataBatchProcessor`` is just a wrapper around the [influxdb-csharp] ``LineProtocolClient``, which opens up a 
new connection to the database for each batch to write:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Threading;
using System.Threading.Tasks;
using InfluxDB.LineProtocol.Client;
using InfluxDB.LineProtocol.Payload;

namespace InfluxExperiment.Influx.Client
{
    public class LocalWeatherDataBatchProcessor
    {
        private readonly string database;
        private readonly string connectionString;

        public LocalWeatherDataBatchProcessor(string connectionString, string database)
        {
            this.database = database;
            this.connectionString = connectionString;
        }

        public Task<LineProtocolWriteResult> WriteAsync(LineProtocolPayload source, CancellationToken cancellationToken = default(CancellationToken))
        {
            if(source == null)
            {
                return Task.FromResult(new LineProtocolWriteResult(true, string.Empty));
            }

            var client = new LineProtocolClient(new Uri(connectionString), database);

            return client.WriteAsync(source, cancellationToken);
        }
    }
}
```

### Converting to LineProtocolPayload: The LocalWeatherDataConverter ###

What's left is converting from a list of ``LocalWeatherData`` items to the ``LineProtocolPayload``. This is done by first 
converting each ``LocalWeatherData`` item to a ``LineProtocolPoint`` and then adding them to the ``LineProtocolPayload``: 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Threading.Tasks;
using InfluxDB.LineProtocol.Payload;
using Experiments.Common.Csv.Model;
using CsvLocalWeatherDataType = Experiments.Common.Csv.Model.LocalWeatherData;

namespace InfluxExperiment.Converters
{
    public static class LocalWeatherDataConverter
    {
        public static LineProtocolPayload Convert(IEnumerable<CsvLocalWeatherDataType> source)
        {
            if (source == null)
            {
                return null;
            }

            LineProtocolPayload payload = new LineProtocolPayload();

            foreach (var item in source)
            {
                var point = Convert(item);

                if (point != null)
                {
                    payload.Add(point);
                }
            }

            return payload;
        }

        public static LineProtocolPoint Convert(LocalWeatherData source)
        {
            if (source == null)
            {
                return null;
            }

            var fields = new Dictionary<string, object>();

            fields.AddFieldValue("air_temperature_at_2m", source.AirTemperatureAt2m);
            fields.AddFieldValue("air_temperature_at_5cm", source.AirTemperatureAt5cm);
            fields.AddFieldValue("dew_point_temperature_at_2m", source.DewPointTemperatureAt2m);
            fields.AddFieldValue("relative_humidity", source.RelativeHumidity);

            // No Measurements to be inserted:
            if (fields.Count == 0)
            {
                return null;
            }

            var tags = new Dictionary<string, string>
                {
                    {"station_identifier", source.StationIdentifier},
                    {"quality_code", source.QualityCode.ToString(CultureInfo.InvariantCulture)}
                };

            return new LineProtocolPoint("weather_measurement", new ReadOnlyDictionary<string, object>(fields), tags, source.TimeStamp);
        }

        private static void AddFieldValue(this IDictionary<string, object> dictionary, string key, object value)
        {
            if (value == null)
            {
                return;
            }

            dictionary.Add(key, value);
        }
    }

}
```

### Connecting the Parts: The LINQ Import Pipeline ###

That's it already. The Import Pipeline now simply reads the CSV data, batches the valid records, converts each batch 
into a ``LineProtocolPayload`` and then writes the payload to InfluxDB using the ``LocalWeatherDataBatchProcessor``:

```csharp
private static void ProcessLocalWeatherData(string csvFilePath)
{
    if (log.IsInfoEnabled)
    {
        log.Info($"Processing File: {csvFilePath}");
    }

    // Construct the Batch Processor:
    var processor = new LocalWeatherDataBatchProcessor(ConnectionString, Database);

    // Access to the List of Parsers:
    var batches = Parsers
        // Use the LocalWeatherData Parser:
        .LocalWeatherDataParser
        // Read the File:
        .ReadFromFile(csvFilePath, Encoding.UTF8, 1)
        // Get the Valid Results:
        .Where(x => x.IsValid)
        // And get the populated Entities:
        .Select(x => x.Result)
        // Let's stay safe! Stop parallelism here:
        .AsEnumerable()
        // Evaluate:
        .Batch(10000)
        // Convert each Batch into a LineProtocolPayload:
        .Select(measurements => LocalWeatherDataConverter.Convert(measurements));

    foreach (var batch in batches)
    {
        try
        {
            var result = processor.WriteAsync(batch).GetAwaiter().GetResult();

            // Log all unsuccessful writes, but do not quit execution:
            if (!result.Success)
            {
                if (log.IsErrorEnabled)
                {
                    log.Error(result.ErrorMessage);
                }
            }
        }
        catch (Exception e)
        {
            // Some Pokemon Exception Handling here. I am seeing TaskCanceledExceptions with the 
            // InfluxDB .NET Client. At the same time I do not want to quit execution, because 
            // some batches fail:
            if (log.IsErrorEnabled)
            {
                log.Error(e, "Error occured writing InfluxDB Payload");
            }
        }
    }
}
```

I caught all exceptions here and simply log them, instead of rethrowing. I saw some non-reproducible ``TaskCanceledExceptions`` for the 
[influxdb-csharp] client, which may be due to my implementation. And I didn't want to quit the whole import because there is a problem 
writing one batch out of 400 million recods. In a real setup this should be handeled with greater care instead of just dropping the data!

I chose a batch size of 10,000, because the [InfluxDB Documentation states](https://docs.influxdata.com/influxdb/v1.7/tools/api#request-body-1):

> We recommend writing points in batches of 5,000 to 10,000 points. Smaller batches, and more HTTP requests, will result in sub-optimal performance.

### Turning the Knobs: InfluxDB Configuration ###

InfluxDB 1.7.1 with the default configuration was unable to import the entire dataset. It consumes too much memory under 
load and could not write the batches anymore. After reading through documentation I am quite confident, that the default 
shard duration and retention policy has to be adjusted, so that the shards do not stay in memory forever:

* [https://www.influxdata.com/blog/tldr-influxdb-tech-tips-march-16-2017/](https://www.influxdata.com/blog/tldr-influxdb-tech-tips-march-16-2017/)
* [https://docs.influxdata.com/influxdb/v1.7/guides/hardware_sizing/](https://docs.influxdata.com/influxdb/v1.7/guides/hardware_sizing/)

The default configuration of InfluxDB is optimized for realtime data with a short [retention duration] and a short [shard duration]. 
This makes InfluxDB chewing up the entire RAM, just because for the historic data too many shards are created and the cached data 
is never written to disk.

So I am now creating the database using ``DURATION`` set to infinite (``inf``) to keep measurements forever. The ``SHARD DURATION`` 
is set to 4 weeks for limiting the number of shards being created during the import. This can be done by running the following 
``CREATE DATABASE`` statement:

```
CREATE DATABASE "weather_data" WITH DURATION inf REPLICATION 1 SHARD DURATION 4w NAME "weather_data_policy"
```

In the ``influxdb.conf`` I am setting the ``cache-snapshot-write-cold-duration`` to 5 seconds for flushing the caches more agressively:

```
cache-snapshot-write-cold-duration = "5s"
```

[retention duration]: https://docs.influxdata.com/influxdb/v1.7/concepts/glossary/#duration
[shard duration]: https://docs.influxdata.com/influxdb/v1.7/concepts/glossary/#shard-duration

### Results ###

[InfluxDB] was able to import the entire dataset. The final database has 398,704,931 measurements and has a file size 
of 7.91 GB. I was very impressed, that InfluxDB was able to compress the data from 25.5 GB raw CSV data to 7.91 GB! 

In a later post we will look at the read behavior of InfluxDB.


[Part 1]: /blog/timeseries_databases_1_dataset
[StringSplitTokenizer]: http://bytefish.github.io/TinyCsvParser/sections/userguide/tokenizer.html#stringsplittokenizer
[Deep Learning]: https://en.wikipedia.org/wiki/Deep_learning
[PostgreSQLCopyHelper]: https://github.com/bytefish/PostgreSQLCopyHelper
[Npgsql]: https://github.com/npgsql/npgsql
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[Columnstore indexes]: https://docs.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview
[timescaledb-tune]: https://github.com/timescale/timescaledb-tune
[The world's most valuable resource is no longer oil, but data]: https://www.economist.com/leaders/2017/05/06/the-worlds-most-valuable-resource-is-no-longer-oil-but-data
[FTP Link]: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/
[TimescaleDB]: https://www.timescale.com/
[Elasticsearch]: https://www.elastic.co/
[SQL Server]: https://www.microsoft.com/de-de/sql-server/sql-server-2017
[InfluxData]: https://www.influxdata.com/
[InfluxDB]: https://www.influxdata.com/time-series-platform/influxdb/
[DWD Open Data]: https://opendata.dwd.de/
[Deutscher Wetterdienst (DWD)]: https://www.dwd.de
[GermanWeatherDataExample/Resources/files.md]: https://github.com/bytefish/GermanWeatherDataExample/blob/master/GermanWeatherData/Resources/files.md