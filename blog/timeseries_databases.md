title: Timeseries Databases
date: 2018-12-23 09:30
tags: timescaledb, sqlserver, elasticsearch, database, sql
category: databases
slug: timeseries_databases
author: Philipp Wagner
summary: This article evaluates Timeseries Databases on a realistic dataset.

These days it's all about Artificial Intelligence (AI), Big Data, Business Intelligence, Business Analytics, 
... "[The world’s most valuable resource is no longer oil, but data]" they say, so why not store everything 
first and make sense of it sometime later?

Well. 

I often had to deal with large amounts time series data in my career. And I have never been able to give 
qualified answers or recommendations for one database or another. Simply because I don't know how the available 
databases behave under realistic loads.

So how well do databases work when we actually throw realistic data at them? What knobs have to be turned to 
make the databases scale? How far does **a single machine** take us?

In this project I want to benchmark [TimescaleDB], [Elasticsearch], [SQL Server] and [InfluxDB] on the 10 Minute 
Weather Data for Germany. 

All code to recreate the results can be found at:

* [https://github.com/bytefish/GermanWeatherDataExample](https://github.com/bytefish/GermanWeatherDataExample)

This post is the first in a series I am planning and it focuses on the write throughput of databases.

## The Dataset ##

The [DWD Open Data] portal of the [Deutscher Wetterdienst (DWD)] gives access to the historical weather data in Germany. I decided 
to analyze the available historical Air Temperature data for Germany given in a 10 minute resolution ([FTP Link]). If you want to 
recreate the example, you can find the list of CSV files in the GitHub repository at: [GermanWeatherDataExample/Resources/files.md].

The DWD dataset is given as CSV files and has a size of approximately 25.5 GB.

## The Setup ##

### Hardware ###

* Intel® Core™ i5-3450 CPU
* 16 GB RAM
* Samsung SSD 860 EVO ([Specifications](https://www.samsung.com/semiconductor/minisite/ssd/product/consumer/860evo/))

### Software ###

I am using Microsoft Windows 10 as Operating System.

C\# is used for the experiments and all libraries support efficient Bulk Inserts to the databases:

* [TinyCsvParser] is used for parsing the CSV data
* [influxdb-csharp] is used for writing data to [InfluxDB]
* [Nest] is used for writing data to Elasticsearch
* [PostgreSQLCopyHelper] is used to write data to PostgreSQL

## Parsing the CSV Data ##

### Parsing the CSV Station Data ###

[FixedLengthTokenizer]: http://bytefish.github.io/TinyCsvParser/sections/userguide/tokenizer.html#fixedlengthtokenizer

Let's start by looking at the CSV data for the Weather stations:

<a href="/static/images/blog/timeseries_databases/csv_stations.png">
	<img class="mediacenter" src="/static/images/blog/timeseries_databases/csv_stations.png" alt="CSV Stations Data Sample" />
</a>

#### Domain Model ####

The data can be easily translated into the following C\# class ``Station``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace Experiments.Common.Csv.Model
{
    public class Station
    {
        public string Identifier { get; set; }

        public string Name { get; set; }

        public DateTime StartDate { get; set; }

        public DateTime? EndDate { get; set; }

        public short StationHeight { get; set; }

        public string State { get; set; }

        public float Latitude { get; set; }

        public float Longitude { get; set; }
    }
}
```

#### Split the Line: Writing a Tokenizer ####

In the CSV we can see, that it is a fixed-width file and we could use the [FixedLengthTokenizer] to read the data. There should 
be no leading and trailing whitespaces for the column data, which is something [TinyCsvParser] doesn't apply by default. But it 
can be easily added by wrapping the ``FixedLengthTokenizer``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Linq;
using TinyCsvParser.Tokenizer;
using ColumnDefinition = TinyCsvParser.Tokenizer.FixedLengthTokenizer.ColumnDefinition;

namespace Experiments.Common.Csv.Tokenizer
{
    public class CustomFixedLengthTokenizer : ITokenizer
    {
        private readonly bool trim;
        private readonly ITokenizer tokenizer;

        public CustomFixedLengthTokenizer(ColumnDefinition[] columns, bool trim = true)
        {
            this.tokenizer = new FixedLengthTokenizer(columns);
            this.trim = trim;
        }

        public string[] Tokenize(string input)
        {
            var tokens = tokenizer.Tokenize(input);

            if (trim)
            {
                return tokens
                    .Select(x => x.Trim())
                    .ToArray();
            }

            return tokens;
        }
    }
}
```

To build a ``CustomFixedLengthTokenizer`` instance we need to pass the list of ``ColumnDefinition``, that define the 
start and end index of each column in the record. I always do this in a class ``Tokenizers``, which returns the 
Tokenizers:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using TinyCsvParser.Tokenizer;

namespace Experiments.Common.Csv.Tokenizer
{
    public static class Tokenizers
    {
        public static ITokenizer StationsTokenizer
        {
            get
            {
                var columnDefinitions = new[]
                {
                    new FixedLengthTokenizer.ColumnDefinition(0, 6),
                    new FixedLengthTokenizer.ColumnDefinition(6, 14),
                    new FixedLengthTokenizer.ColumnDefinition(15, 23),
                    new FixedLengthTokenizer.ColumnDefinition(32, 39),
                    new FixedLengthTokenizer.ColumnDefinition(43, 51),
                    new FixedLengthTokenizer.ColumnDefinition(52, 61),
                    new FixedLengthTokenizer.ColumnDefinition(61, 102),
                    new FixedLengthTokenizer.ColumnDefinition(102, 125),
                };

                return new CustomFixedLengthTokenizer(columnDefinitions, true);
            }
        }
        
        // More Tokenizers ...
    }
}
```

#### Mapping the Data: StationMapper ####

The ``StationMapper`` defines how to map between the columns in the CSV data and the C\# ``Station`` class. In the CSV data dates are 
given in a ``yyyyMMdd`` format, so we can apply the ``DateTimeConverter`` for the date:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Experiments.Common.Csv.Model;
using TinyCsvParser.Mapping;
using TinyCsvParser.TypeConverter;

namespace Experiments.Common.Csv.Mapper
{
    public class StationMapper : CsvMapping<Station>
    {
        public StationMapper()
        {
            MapProperty(0, x => x.Identifier);
            MapProperty(1, x => x.StartDate, new DateTimeConverter("yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture));
            MapProperty(2, x => x.EndDate, new NullableDateTimeConverter("yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture));
            MapProperty(3, x => x.StationHeight);
            MapProperty(4, x => x.Latitude);
            MapProperty(5, x => x.Longitude);
            MapProperty(6, x => x.Name);
            MapProperty(7, x => x.State);
        }
    }
}
```

#### Connecting the Parts: Building a CsvParser ####

And what's left for reading the weather stations is constructing the ``CsvParser<Station>``, which connects all the parts:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Experiments.Common.Csv.Mapper;
using Experiments.Common.Csv.Model;
using Experiments.Common.Csv.Tokenizer;
using TinyCsvParser;

namespace Experiments.Common.Csv.Parser
{
    public static class Parsers
    {
        public static CsvParser<Station> StationParser
        {
            get
            {
                CsvParserOptions csvParserOptions = new CsvParserOptions(false, string.Empty, Tokenizers.StationsTokenizer, 1, false);

                return new CsvParser<Station>(csvParserOptions, new StationMapper());
            }
        }
        
        // More Parsers here ...
    }
}
```

### Parsing the CSV Weather Data ###

Next on the list is parsing the weather data. Let's start again by looking at the CSV Data:

<a href="/static/images/blog/timeseries_databases/csv_weather_data.png">
	<img class="mediacenter" src="/static/images/blog/timeseries_databases/csv_weather_data.png" alt="CSV Stations Data Sample" />
</a>

#### Domain Model ####

The ``LocalWeatherData`` C\# class contains all available informations about a weather measurement:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace Experiments.Common.Csv.Model
{
    public class LocalWeatherData
    {
        public string StationIdentifier { get; set; }

        public DateTime TimeStamp { get; set; }

        public byte QualityCode { get; set; }

        public float? StationPressure { get; set; }

        public float? AirTemperatureAt2m { get; set; }

        public float? AirTemperatureAt5cm { get; set; }

        public float? RelativeHumidity { get; set; }

        public float? DewPointTemperatureAt2m { get; set; }
    }
}
```

#### Additional DateTime Converter ####

According the CSV documentation all dates are measured on a UTC timescale. When I wrote the experiments I noticed, that the existing [TinyCsvParser] 
don't have a functionality to specify the ``DateTime`` kind. That's why I added a ``CustomDateTimeConverter``, that specifies the kind of a 
``DateTime`` after parsing it:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Globalization;
using TinyCsvParser.TypeConverter;

namespace Experiments.Common.Csv.Converter
{
    public class CustomDateTimeConverter : ITypeConverter<DateTime>
    {
        private readonly DateTimeKind dateTimeKind;

        private readonly DateTimeConverter dateTimeConverter;

        public CustomDateTimeConverter(DateTimeKind dateTimeKind)
            : this(string.Empty, dateTimeKind)
        {
        }

        public CustomDateTimeConverter(string dateTimeFormat, DateTimeKind dateTimeKind)
            : this(dateTimeFormat, CultureInfo.InvariantCulture, dateTimeKind)
        {
        }

        public CustomDateTimeConverter(string dateTimeFormat, IFormatProvider formatProvider, DateTimeKind dateTimeKind)
            : this(dateTimeFormat, formatProvider, DateTimeStyles.None, dateTimeKind)
        {
        }

        public CustomDateTimeConverter(string dateTimeFormat, IFormatProvider formatProvider, DateTimeStyles dateTimeStyles, DateTimeKind dateTimeKind)
        {
            this.dateTimeConverter = new DateTimeConverter(dateTimeFormat, formatProvider, dateTimeStyles);
            this.dateTimeKind = dateTimeKind;
        }

        public bool TryConvert(string value, out DateTime result)
        {
            if (dateTimeConverter.TryConvert(value, out result))
            {
                result = DateTime.SpecifyKind(result, dateTimeKind);

                return true;
            }

            return false;
        }

        public Type TargetType
        {
            get { return typeof(DateTime); }
        }
    }
}
```

#### Ignoring Missing Values ####

In the CSV weather data missing values are denoted by the value ``-999``. So I reused the ``IgnoreMissingValuesConverter``, that I wrote 
for a previous project. We can pass the ``-999`` as missing value representation into the class and it will return null for matching 
values:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Globalization;
using TinyCsvParser.TypeConverter;

namespace Experiments.Common.Csv.Converter
{
    public class IgnoreMissingValuesConverter : ITypeConverter<Single?>
    {
        private readonly string missingValueRepresentation;

        private readonly NullableSingleConverter nullableSingleConverter;
        
        public IgnoreMissingValuesConverter(string missingValueRepresentation)
        {
            this.missingValueRepresentation = missingValueRepresentation;
            this.nullableSingleConverter = new NullableSingleConverter();
        }

        public IgnoreMissingValuesConverter(string missingValueRepresentation, IFormatProvider formatProvider)
        {
            this.missingValueRepresentation = missingValueRepresentation;
            this.nullableSingleConverter = new NullableSingleConverter(formatProvider);
        }

        public IgnoreMissingValuesConverter(string missingValueRepresentation, IFormatProvider formatProvider, NumberStyles numberStyles)
        {
            this.missingValueRepresentation = missingValueRepresentation;
            this.nullableSingleConverter = new NullableSingleConverter(formatProvider, numberStyles);
        }


        public bool TryConvert(string value, out float? result)
        {
            if(string.Equals(missingValueRepresentation, value.Trim(), StringComparison.InvariantCultureIgnoreCase))
            {
                result = default(float?);

                return true;
            }

            return nullableSingleConverter.TryConvert(value, out result);
        }

        public Type TargetType
        {
            get { return typeof(Single?); }
        }
    }
}
```

#### Padding Station Identifiers ####

In the Station data the Stations are always 5 characters long and are left-padded with zeros. In the weather data the leading 
zeros are trimmed, which can lead to problems when we try to match the data. That's why I added a ``StringPadLeftConverter`` that 
can be configured to left pad a string value:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using TinyCsvParser.TypeConverter;

namespace Experiments.Common.Csv.Converter
{
    public class StringPadLeftConverter : ITypeConverter<string>
    {
        private readonly int totalWidth;
        private readonly char paddingChar;

        public StringPadLeftConverter(int totalWidth, char paddingChar)
        {
            this.totalWidth = totalWidth;
            this.paddingChar = paddingChar;
        }

        public bool TryConvert(string value, out string result)
        {
            result = null;

            if (value == null)
            {
                return true;
            }

            result = value.PadLeft(totalWidth, paddingChar);

            return true;
        }

        public Type TargetType
        {
            get { return typeof(string); }
        }
    }
}
```

#### Mapping the Data: LocalWeatherDataMapper ####

The custom converters can now be used to define the mapping between the mapping between the CSV column data 
and the C\# domain model. You can see how the ``StringPadLeftConverter``, the ``CustomDateTimeConverter`` and 
``IgnoreMissingValuesConverter`` are used to preprocess the column fields:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using Experiments.Common.Csv.Converter;
using Experiments.Common.Csv.Model;
using TinyCsvParser.Mapping;

namespace Experiments.Common.Csv.Mapper
{
    public class LocalWeatherDataMapper : CsvMapping<LocalWeatherData>
    {
        public LocalWeatherDataMapper()
        {
            MapProperty(0, x => x.StationIdentifier, new StringPadLeftConverter(5, '0'));
            MapProperty(1, x => x.TimeStamp, new CustomDateTimeConverter("yyyyMMddHHmm", DateTimeKind.Utc));
            MapProperty(2, x => x.QualityCode);
            MapProperty(3, x => x.StationPressure, new IgnoreMissingValuesConverter("-999"));
            MapProperty(4, x => x.AirTemperatureAt2m, new IgnoreMissingValuesConverter("-999"));
            MapProperty(5, x => x.AirTemperatureAt5cm, new IgnoreMissingValuesConverter("-999"));
            MapProperty(6, x => x.RelativeHumidity, new IgnoreMissingValuesConverter("-999"));
            MapProperty(7, x => x.DewPointTemperatureAt2m, new IgnoreMissingValuesConverter("-999"));
        }
    }
}
```

#### Split the Line: Using a SplitStringTokenizer ####

[StringSplitTokenizer]: http://bytefish.github.io/TinyCsvParser/sections/userguide/tokenizer.html#stringsplittokenizer

The CSV data does not contain quoted data and uses a ``;`` as column delimiter. So we can use the [StringSplitTokenizer] to 
split each row into column data. I am again defining a static property it in the ``Tokenizers`` class:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using TinyCsvParser.Tokenizer;

namespace Experiments.Common.Csv.Tokenizer
{
    public static class Tokenizers
    {
    
        // Additional Tokenizers here ...

        public static ITokenizer LocalWeatherDataTokenizer
        {
            get
            {
                return new StringSplitTokenizer(new [] {';' }, true);
            }
        }
    }
}
```

#### Connecting the Parts: Building a CsvParser ####

And the last step is to define the ``CsvParser<LocalWeatherData>`` for the Weather data:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Experiments.Common.Csv.Mapper;
using Experiments.Common.Csv.Model;
using Experiments.Common.Csv.Tokenizer;
using TinyCsvParser;

namespace Experiments.Common.Csv.Parser
{
    public static class Parsers
    {
        
        // Additional Parsers here ...
        
        public static CsvParser<LocalWeatherData> LocalWeatherDataParser
        {
            get
            {
                CsvParserOptions csvParserOptions = new CsvParserOptions(false, string.Empty, Tokenizers.LocalWeatherDataTokenizer, 1, false);

                return new CsvParser<LocalWeatherData>(csvParserOptions, new LocalWeatherDataMapper());
            }
        }
    }
}
```

### Adding a CsvParser Extension: Skipping Lines ###

If you look closely into the CSV data you will notice, that the Station CSV data has two lines for the header. I didn't take this into account 
when writing [TinyCsvParser], but the library is very flexible... so as the library developer I can add an additional ``ReadFromFile<TEntity>`` 
method, that skips a given amount of lines when parsing the data:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.IO;
using System.Linq;
using System.Text;
using TinyCsvParser;
using TinyCsvParser.Mapping;
using TinyCsvParser.Model;

namespace Experiments.Common.Csv.Extensions
{
    public static class CsvParserExtensions
    {
        public static ParallelQuery<CsvMappingResult<TEntity>> ReadFromFile<TEntity>(this CsvParser<TEntity> csvParser, string fileName, Encoding encoding, int skip)
            where TEntity : class, new()
        {
            if (fileName == null)
            {
                throw new ArgumentNullException("fileName");
            }

            var lines = File
                .ReadLines(fileName, encoding)
                .Select((line, index) => new Row(index, line))
                .Skip(skip);

            return csvParser.Parse(lines);
        }
    }
}
``` 

### Batching Data: LINQ Extension ###

Batching data often improves the performance of writes to a database. I want my import pipeline to be simple and 
expressed with LINQ, so I am adding an extension method ``Batch<T>`` on an ``IEnumerable<T>``. It also allows to 
modify the batch size:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace Experiments.Common.Extensions
{
    public static class EnumerableExtensions
    {
        public static IEnumerable<IEnumerable<T>> Batch<T>(this IEnumerable<T> source, int size)
        {
            T[] bucket = null;
            var count = 0;

            foreach (var item in source)
            {
                if (bucket == null)
                {
                    bucket = new T[size];
                }

                bucket[count++] = item;

                if (count != size)
                {
                    continue;
                }

                yield return bucket.Select(x => x);

                bucket = null;
                count = 0;
            }

            if (bucket != null && count > 0)
            {
                yield return bucket.Take(count);
            }
        }
    }
}
```

And that's it! Now everything is prepared to parse the CSV data and write it to the databases.

## InfluxDB ##

[InfluxDB] is a database written specifically for handling time series data.

The [influxdata] website writes on [InfluxDB]:

> InfluxDB is a high-performance data store written specifically for time series data. It allows for high throughput 
> ingest, compression and real-time querying of that same data. InfluxDB is written entirely in Go and it compiles 
> into a single binary with no external dependencies.

### C\# Implementation ###

[Line Protocol]: https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_reference/

The data points are written using the InfluxDB [Line Protocol], which has the following syntax:

```
<measurement>[,<tag_key>=<tag_value>[,<tag_key>=<tag_value>]] <field_key>=<field_value>[,<field_key>=<field_value>] [<timestamp>]
```

The protocol has already been implemented for C\# by the very good [influxdb-csharp] library:

* https://github.com/influxdata/influxdb-csharp

[influxdb-csharp]: https://github.com/influxdata/influxdb-csharp

#### LocalWeatherDataBatchProcessor ####

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

#### LocalWeatherDataConverter ####

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

#### Import Pipeline ####

The Import Pipeline now simply reads the CSV data, batches the valid records, converts each batch into a ``LineProtocolPayload`` and 
then writes the payload to InfluxDB using the ``LocalWeatherDataBatchProcessor``.

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

### Configuration ###

InfluxDB 1.7.1 with the default configuration was unable to import the entire dataset.  It consumes too much memory under 
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
of 7.91 GB. The difference between the number of measurements for InfluxDB and TimescaleDB will be part of further 
investigation.

The import took 147 minutes, so InfluxDB was able to write 45,112 records per second.

## TimescaleDB ##

The [TimescaleDB] docs describe TimescaleDB as:

> [...] an open-source time-series database optimized for fast ingest and complex queries. It speaks "full SQL" and 
> is correspondingly easy to use like a traditional relational database, yet scales in ways previously reserved for NoSQL 
> databases.

TimescaleDB comes as a PostgreSQL Extension and can be installed for Windows using an official Installer at:

* [https://docs.timescale.com/v1.0/getting-started/installation/windows/installation-windows](https://docs.timescale.com/v1.0/getting-started/installation/windows/installation-windows)

After the installation you have to modify the ``postgresql.config`` and add the ``timescaledb`` extension:

```
shared_preload_libraries = 'timescaledb'		# (change requires restart)
```

### Implementation SQL-side ###

First of all create the user ``philipp`` for connecting to the databases:

```
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
```

Then we can create the two tenant databases and set the owner to ``philipp``:

```
postgres=# CREATE DATABASE sampledb WITH OWNER philipp; 
```

For creating the TimescaleDB Hypertable the user needs ``SUPERUSER`` permissions, so for creating the 
database the user ``philipp`` is given the permissions:

```
postgres=# ALTER USER philipp WITH SUPERUSER;
```

#### SQL Scripts ####

In the [TimescaleDB/Sql] folder you can find the following ``create_database.bat`` script, which is used to 
simplify creating the database:

```bat
@echo off

:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

set PGSQL_EXECUTABLE="psql.exe"
set STDOUT=stdout.log
set STDERR=stderr.log
set LOGFILE=query_output.log

set HostName=localhost
set PortNumber=5432
set DatabaseName=sampledb
set UserName=philipp
set Password=

call :AskQuestionWithYdefault "Use Host (%HostName%) Port (%PortNumber%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y] (
	set /p HostName="Enter HostName: "
	set /p PortNumber="Enter Port: "
)

call :AskQuestionWithYdefault "Use Database (%DatabaseName%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y]  (
	set /p ServerName="Enter Database: "
)

call :AskQuestionWithYdefault "Use User (%UserName%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y]  (
	set /p UserName="Enter User: "
)

set /p PGPASSWORD="Password: "

1>%STDOUT% 2>%STDERR% (

    %PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < create_database.sql -L %LOGFILE%
    %PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < create_hypertable.sql -L %LOGFILE%
)

goto :end

:: The question as a subroutine
:AskQuestionWithYdefault
    setlocal enableextensions
    :_asktheyquestionagain
    set return_=
    set ask_=
    set /p ask_="%~1"
    if "%ask_%"=="" set return_=y
    if /i "%ask_%"=="Y" set return_=y
    if /i "%ask_%"=="n" set return_=n
    if not defined return_ goto _asktheyquestionagain
    endlocal & set "%2=%return_%" & goto :EOF
    
:end
pause
```

[TimescaleDB/Sql]: https://github.com/bytefish/GermanWeatherDataExample/tree/master/GermanWeatherData/TimescaleDB/Sql

The ``create_database.sql`` script is used to create the schema and tables for the database:

```sql
DO $$
--
-- Schema
--
BEGIN


IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'sample') THEN

    CREATE SCHEMA sample;

END IF;

--
-- Tables
--
IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'sample' 
	AND table_name = 'station'
) THEN

CREATE TABLE sample.station
(
    identifier VARCHAR(5) NOT NULL,
    name VARCHAR(255) NOT NULL,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    station_height SMALLINT,
    state VARCHAR(255),
    latitude REAL,
    longitude REAL

);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'sample' 
	AND table_name = 'weather_data'
) THEN

CREATE TABLE sample.weather_data
(
    station_identifier VARCHAR(5) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    quality_code SMALLINT,
    station_pressure REAL NULL,
    air_temperature_at_2m REAL NULL,
    air_temperature_at_5cm REAL NULL,
    relative_humidity REAL NULL,
    dew_point_temperature_at_2m REAL NULL        
);

END IF;


END;
$$
```

And the second script ``create_hypertable.sql`` is used to create the TimescaleDB Hypertable on the ``timestamp`` column of the ``sample.weather_data`` table:

```sql
DO $$

BEGIN

--
-- The user needs to be SUPERUSER to create extensions. So before executing the Script run 
-- something along the lines:
--
--      postgres=# ALTER USER philipp WITH SUPERUSER;
-- 
-- And after executing, you can revoke the SUPERUSER Role again:
--
--      postgres=# ALTER USER philipp WITH NOSUPERUSER;
--
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

--
-- Make sure to create the timescaledb Extension in the Schema:
--
PERFORM create_hypertable('sample.weather_data', 'timestamp');

END

$$
```

#### Implementation C\#-side ####

TimescaleDB is a Postgres extension, so the Binary COPY protocol of Postgres can be used to bulk import the data. I have used 
[PostgreSQLCopyHelper] for it, which is a library I wrote. It's basically a wrapper around the the great [Npgsql] library.

We start by defining the SQL model for the Weather Data:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace TimescaleExperiment.Sql.Model
{
    public class LocalWeatherData
    {
        public string StationIdentifier { get; set; }

        public DateTime TimeStamp { get; set; }

        public byte QualityCode { get; set; }

        public float? StationPressure { get; set; }

        public float? AirTemperatureAt2m { get; set; }

        public float? AirTemperatureAt5cm { get; set; }

        public float? RelativeHumidity { get; set; }

        public float? DewPointTemperatureAt2m { get; set; }
    }
}
```

Next up is the Converter for converting between the CSV and SQL model:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using CsvLocalWeatherDataType = Experiments.Common.Csv.Model.LocalWeatherData;
using SqlLocalWeatherDataType = TimescaleExperiment.Sql.Model.LocalWeatherData;

using CsvStationDataType = Experiments.Common.Csv.Model.Station;
using SqlStationDataType = TimescaleExperiment.Sql.Model.Station;

namespace TimescaleExperiment.Converters
{
    public static class Converters
    {
        public static SqlLocalWeatherDataType Convert(CsvLocalWeatherDataType source)
        {
            return new SqlLocalWeatherDataType
            {
                StationIdentifier = source.StationIdentifier,
                AirTemperatureAt2m = source.AirTemperatureAt2m,
                StationPressure = source.StationPressure,
                TimeStamp = source.TimeStamp,
                RelativeHumidity = source.RelativeHumidity,
                DewPointTemperatureAt2m = source.DewPointTemperatureAt2m,
                AirTemperatureAt5cm = source.AirTemperatureAt5cm,
                QualityCode = source.QualityCode
            };
        }
    }
}
```

The ``LocalWeatherDataBatchProcessor`` defines the mapping between the C\# class and the SQL table, using 
the fluent mapping of [PostgreSQLCopyHelper] and provides a function to write a batch of measurements: 

```csharp
/ Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using NLog;
using Npgsql;
using NpgsqlTypes;
using PostgreSQLCopyHelper;
using TimescaleExperiment.Sql.Model;

namespace TimescaleExperiment.Sql.Client
{
    public class LocalWeatherDataBatchProcessor : IBatchProcessor<LocalWeatherData>
    {
        private static readonly ILogger log = LogManager.GetCurrentClassLogger();

        private class LocalWeatherCopyHelper : PostgreSQLCopyHelper<LocalWeatherData>
        {
            public LocalWeatherCopyHelper()
                : base("sample", "weather_data")
            {
                Map("station_identifier", x => x.StationIdentifier, NpgsqlDbType.Varchar);
                Map("timestamp", x => x.TimeStamp, NpgsqlDbType.TimestampTz);
                Map("quality_code", x => x.QualityCode, NpgsqlDbType.Smallint);
                MapNullable("station_pressure", x => x.StationPressure, NpgsqlDbType.Real);
                MapNullable("air_temperature_at_2m", x => x.AirTemperatureAt2m, NpgsqlDbType.Real);
                MapNullable("air_temperature_at_5cm", x => x.AirTemperatureAt5cm, NpgsqlDbType.Real);
                MapNullable("relative_humidity", x => x.RelativeHumidity, NpgsqlDbType.Real);
                MapNullable("dew_point_temperature_at_2m", x => x.RelativeHumidity, NpgsqlDbType.Real);
            }
        }

        private readonly string connectionString;

        private readonly IPostgreSQLCopyHelper<LocalWeatherData> processor;

        public LocalWeatherDataBatchProcessor(string connectionString)
            : this(connectionString, new LocalWeatherCopyHelper())
        {
        }

        public LocalWeatherDataBatchProcessor(string connectionString, IPostgreSQLCopyHelper<LocalWeatherData> processor)
        {
            this.processor = processor;
            this.connectionString = connectionString;
        }

        public void Write(IEnumerable<LocalWeatherData> measurements)
        {
            try
            {
                InternalWrite(measurements);
            }
            catch (Exception e)
            {
                if (log.IsErrorEnabled)
                {
                    log.Error(e, "An Error occured while writing measurements");
                }
            }
        }

        private void InternalWrite(IEnumerable<LocalWeatherData> measurements)
        {
            if(measurements == null)
            {
                return;
            }
            
            using (var connection = new NpgsqlConnection(connectionString))
            {
                // Open the Connection:
                connection.Open();

                processor.SaveAll(connection, measurements);
            }
        }
    }
}
```

The import pipeline now reads the CSV Data and converts it into the SQL model, then it is batched to 80,000 entities per 
batch and written to PostgreSQL using the ``LocalWeatherDataBatchProcessor``:

```
private static void ProcessLocalWeatherData(string csvFilePath)
{
    log.Info($"Processing File: {csvFilePath}");

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
        // Convert into the Sql Data Model:
        .Select(x => Converters.Converters.Convert(x))
        // Sequential:
        .AsEnumerable()
        // Batch:
        .Batch(80000);
    
    // Construct the Batch Processor:
    var processor = new LocalWeatherDataBatchProcessor(ConnectionString);

    foreach (var batch in batches)
    {
        // Finally write them with the Batch Writer:
        processor.Write(batch);
    }
}
```

### Results #1 ###

With the default configuration [TimescaleDB] was able to import the entire dataset. The final database has 406,241,469 measurements 
and has a file size of 37 GB. Nothing had been changed in the TimescaleDB configuration.

The import took 690.5 minutes, so TimescaleDB was able to write 9,804 records per second.

### Results #2 ###

The import with the default configuration was much too slow. So the first thing I did was to use [timescaledb-tune] to tune 
the ``postgresql.config`` to values optimized for the hardware:

```
#------------------------------------------------------------------------------
# RESOURCE USAGE (except WAL)
#------------------------------------------------------------------------------

# - Memory -

shared_buffers = 512MB
work_mem = 67254kB
maintenance_work_mem = 2034MB
dynamic_shared_memory_type = windows

# - Kernel Resource Usage -

shared_preload_libraries = 'timescaledb'

# - Asynchronous Behavior -

max_worker_processes = 4		# (change requires restart)
max_parallel_workers_per_gather = 2	# taken from max_parallel_workers
max_parallel_workers = 4		# maximum number of max_worker_processes that

#------------------------------------------------------------------------------
# WRITE AHEAD LOG
#------------------------------------------------------------------------------

# - Settings -

wal_level = hot_standby
wal_buffers = 16MB

# - Checkpoints -

max_wal_size = 8GB
min_wal_size = 4GB
checkpoint_completion_target = 0.9	

#------------------------------------------------------------------------------
# QUERY TUNING
#------------------------------------------------------------------------------

# - Planner Cost Constants -

random_page_cost = 1.1
effective_cache_size = 12206MB
```

But this didn't yield significant improvements.

### Results #3 ###

[Disk-write settings]: https://docs.timescale.com/v1.0/getting-started/configuring#disk-write

The TimescaleDB docs write on [Disk-write settings]:

> Disk-write settings
>
> In order to increase write throughput, there are multiple settings to adjust the behaviour that PostgreSQL uses to write 
> data to disk. We find the performance to be good with the default (safest) settings. If you want a bit of additional 
> performance, you can set synchronous_commit = 'off'(PostgreSQL docs). Please note that when disabling ``sychronous_commit`` 
> in this way, an operating system or database crash might result in some recent allegedly-committed transactions being 
> lost. We actively discourage changing the ``fsync`` setting.

So I decided to turn the ``synchronous_commit`` off by uncommenting the following line in the ``postgresql.config``:

``synchronous_commit = off``

With synchronous commits disabled the import took 247 minutes, so TimescaleDB was able to write 27,560 records per second.

## SQL Server 2017 ##

The Microsoft documents describe the [SQL Server] as:

> [...] a central part of the Microsoft data platform. SQL Server is an industry leader in operational database management systems (ODBMS).

The SQL Server is not a database specialized for Time series data. It provides [Columnstore indexes] for storing data in a column-based layout 
and recently added a Graph Database engine to support more specialized data ([read my post here](https://bytefish.de/blog/sql_server_2017_graph_database/)).

### Results ###

The SQL Server 2017 was able to import the entire dataset. The final database has 406,242,465 measurements and a file 
size of 12.6 GB. Nothing has been changed in the SQL Server configuration. More queries and performance analysis to follow!

The import took 81.25 minutes, so the SQL Server was able to write 83,059 records per second.

## Elasticsearch ##

[elastic]: https://www.elastic.co
[Document-oriented database]: https://en.wikipedia.org/wiki/Document-oriented_database

The [elastic] product page describes Elasticsearch as:

> [...] a distributed, RESTful search and analytics engine capable of solving a growing number of use 
> cases. As the heart of the Elastic Stack, it centrally stores your data so you can discover the expected and 
> uncover the unexpected.

Why did I include Elasticsearch? At its heart Elasticsearch is a [Document-oriented database], that's not obviously suited 
for storing time series data. But as a NoSQL database it's quite easy to scale and with [Kibana] it's simple to quickly 
generate visualizations for the data.

There is a great article written by [Felix Barnsteiner](https://www.elastic.co/blog/author/felix-barnsteiner) on using 
Elasticsearch as a Time series database:

* https://www.elastic.co/blog/elasticsearch-as-a-time-series-data-store

### Implementation ###

[Nest]: https://github.com/elastic/elasticsearch-net

The Elasticsearch implementation uses [Nest] for interfacing with Elasticsearch. The Elasticsearch Mapping can be easily expressed 
in [Nest] using Attributes. These Attributes will be used by [Nest] to generate and create the Elasticsearch mapping:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using Nest;

namespace ElasticExperiment.Elastic.Model
{
    public class LocalWeatherData
    {
        [Text]
        public string Station { get; set; }

        [Date]
        public DateTime TimeStamp { get; set; }

        [Number(NumberType.Byte)]
        public byte QualityCode { get; set; }

        [Number(NumberType.Float)]
        public float? StationPressure { get; set; }

        [Number(NumberType.Float)]
        public float? AirTemperatureAt2m { get; set; }

        [Number(NumberType.Float)]
        public float? AirTemperatureAt5cm { get; set; }

        [Number(NumberType.Float)]
        public float? RelativeHumidity { get; set; }

        [Number(NumberType.Float)]
        public float? DewPointTemperatureAt2m { get; set; }
    }
}
```

The ``LocalWeatherDataConverter`` is used to convert between the CSV and Elasticsearch representation:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Nest;
using CsvStationType = Experiments.Common.Csv.Model.Station;
using CsvLocalWeatherDataType = Experiments.Common.Csv.Model.LocalWeatherData;

using ElasticStationType = ElasticExperiment.Elastic.Model.Station;
using ElasticLocalWeatherDataType = ElasticExperiment.Elastic.Model.LocalWeatherData;

namespace ElasticExperiment.Converters
{

    public static class LocalWeatherDataConverter
    {
         public static ElasticLocalWeatherDataType Convert(CsvLocalWeatherDataType source)
        {
            if (source == null)
            {
                return null;
            }

            return new ElasticLocalWeatherDataType
            {
                Station = source.StationIdentifier,
                AirTemperatureAt2m = source.AirTemperatureAt2m,
                AirTemperatureAt5cm = source.AirTemperatureAt5cm,
                DewPointTemperatureAt2m = source.DewPointTemperatureAt2m,
                QualityCode = source.QualityCode,
                RelativeHumidity = source.RelativeHumidity,
                StationPressure = source.StationPressure,
                TimeStamp = source.TimeStamp
            };
        }
    }
}
```

[Nest] supports the Elasticsearch Bulk API, but I decided to simplify it by wrapping the [Nest] ``IElasicClient`` in the 
``ElasticSearchClient<TEntity>`` class, which nicely abstracts the [Nest] implementation details away and can be reused 
for all entities:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using Elasticsearch.Net;
using Nest;

namespace ElasticExperiment.Elastic.Client
{
    public class ElasticSearchClient<TEntity>
        where TEntity : class
    {
        public readonly string IndexName;

        protected readonly IElasticClient Client;

        public ElasticSearchClient(IElasticClient client, string indexName)
        {
            IndexName = indexName;
            Client = client;
        }

        public ElasticSearchClient(Uri connectionString, string indexName)
            : this(CreateClient(connectionString), indexName)
        {
        }

        public ICreateIndexResponse CreateIndex(Func<IndexSettingsDescriptor, IPromise<IndexSettings>> indexSettings)
        {
            var response = Client.IndexExists(IndexName);

            if (response.Exists)
            {
                return null;

            }

            return Client
                .CreateIndex(IndexName, index => index
                    .Settings(settings => indexSettings(settings))
                    .Mappings(mappings => mappings.Map<TEntity>(x => x.AutoMap())));
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

        private static IElasticClient CreateClient(Uri connectionString)
        {
            var connectionPool = new SingleNodeConnectionPool(connectionString);
            var connectionSettings = new ConnectionSettings(connectionPool);

            return new ElasticClient(connectionSettings);
        }
    }
}
```

The import pipeline first creates the Index with custom settings, please read below for the details why I am disabling 
the Refresh Interval and set the Number Of Replicas to 0. The import pipeline then reads the CSV data, converts the 
entities and batches it into 30,000 entities. Each batch is then written using the ``ElasticSearchClient``, which handles 
the bulk indexing:

```csharp
private static void ProcessLocalWeatherData(string csvFilePath)
{
    if (log.IsInfoEnabled)
    {
        log.Info($"Processing File: {csvFilePath}");
    }

    // Construct the Batch Processor:
    var client = new ElasticSearchClient<Elastic.Model.LocalWeatherData>(ConnectionString, "weather_data");

    // We are creating the Index with special indexing options for initial load, 
    // as suggested in the Elasticsearch documentation at [1].
    //
    // We disable the performance-heavy indexing during the initial load and also 
    // disable any replicas of the data. This comes at a price of not being able 
    // to query the data in realtime, but it will enhance the import speed.
    //
    // After the initial load I will revert to the standard settings for the Index
    // and set the default values for Shards and Refresh Interval.
    //
    // [1]: https://www.elastic.co/guide/en/elasticsearch/reference/master/tune-for-indexing-speed.html
    //
    client.CreateIndex(settings => settings
        .NumberOfReplicas(0)
        .RefreshInterval(-1));
    
    // Access to the List of Parsers:
    var batches = Parsers
        // Use the LocalWeatherData Parser:
        .LocalWeatherDataParser
        // Read the File, Skip first row:
        .ReadFromFile(csvFilePath, Encoding.UTF8, 1)
        // Get the Valid Results:
        .Where(x => x.IsValid)
        // And get the populated Entities:
        .Select(x => x.Result)
        // Convert to ElasticSearch Entity:
        .Select(x => LocalWeatherDataConverter.Convert(x))
        // Batch Entities:
        .Batch(30000);


    foreach (var batch in batches)
    {
        client.BulkInsert(batch);
    }
}
```

### Results ###

Elasticsearch was able to import the entire dataset. The final database has 406,548,765 documents and has a file size 
of 52.9 GB. The difference in documents between TimescaleDB and Elasticsearch can be explained due to an accidental restart 
during the first file import, this will be adjusted in a later post.

The import took 718.9 minutes, so Elasticsearch was able to write 9,425 records per second.

### Configuration ###

The default configuration of Elasticsearch 6.5.1 is not optimized for bulk loading large amounts of data into the 
database. To improve the import for the initial load, the first I did was to disable indexing and replication by 
creating the index with 0 Replicas (since it is all running local anyway) and disabling the Index Refresh Interval, 
so the index isn't built on inserts.

All the performance hints are taken from the Elasticsearch documentation at:

* https://www.elastic.co/guide/en/elasticsearch/reference/master/tune-for-indexing-speed.html

In Elasticsearch 6.5.1 these settings have to be configured as an index template apparently, instead of editing the 
``config/elasticsearch.yml``. Anyways it can be easily be achieved with the NEST, the official .NET Connector for 
Elasticsearch:

```csharp
// We are creating the Index with special indexing options for initial load, 
// as suggested in the Elasticsearch documentation at [1].
//
// We disable the performance-heavy indexing during the initial load and also 
// disable any replicas of the data. This comes at a price of not being able 
// to query the data in realtime, but it will enhance the import speed.
//
// After the initial load I will revert to the standard settings for the Index
// and set the default values for Shards and Refresh Interval.
//
// [1]: https://www.elastic.co/guide/en/elasticsearch/reference/master/tune-for-indexing-speed.html
//
client.CreateIndex(settings => settings
    .NumberOfReplicas(0)
    .RefreshInterval(-1));
```

Additionally I made sure I am running a 64-bit JVM, so the heap size can scale to more than 2 GB for fair comparisms 
with systems like InfluxDB, that aggressively take ownership of the RAM. You can configure the Elasticsearch JVM settings 
in the ``config/jvm.options`` file.

I have set the initial and maximum size of the total heap space to ``6 GB``, so Elasticsearch should be able to allocate 
enough RAM to play with:

```
# Xms represents the initial size of total heap space
# Xmx represents the maximum size of total heap space
-Xms6g
-Xmx6g
```

And finally I wanted to make sure, that the Elasticsearch process isn't swapped out. According to the Elasticsearch 
documentation this can be configured in the ``config/elasticsearch.yml`` by adding:

```
bootstrap.memory_lock: true
```

More information on Heap Sizing and Swapping can be found at:

* [https://www.elastic.co/guide/en/elasticsearch/guide/current/heap-sizing.html (Guide to Heap Sizing)](https://www.elastic.co/guide/en/elasticsearch/guide/current/heap-sizing.html)
* [https://www.elastic.co/blog/a-heap-of-trouble (Detailed article on the maximum JVM Heap Size)](https://www.elastic.co/blog/a-heap-of-trouble)

## Summary ##

<table>
  <thead>
    <tr>
      <th>Database</th>
      <th>Elapsed Time (Minutes)</th>
      <th># Records</th>
      <th>Throughput (records/s)</th>
      <th>Database Size (GB)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>InfluxDB 1.7.1</td>
      <td>147</td>
      <td>398,704,931</td>
      <td>45,112</td>
      <td class="bg-light-green"><b>7.91</b></td>
    </tr>
    <tr>
      <td>TimescaleDB 1.0</td>
      <td>247</td>
      <td>406,241,469</td>
      <td>27,560</td>
      <td>37</td>
    </tr>
    <tr>
      <td>SQL Server 2017</td>
      <td class="bg-light-green"><b>81.25</b></td>
      <td>406,242,465</td>
      <td class="bg-light-green"><b>83,059</b></td>
      <td>12.6</td>
    </tr>
    <tr>
      <td>Elasticsearch 6.5.1</td>
      <td class="bg-light-red">718.9</td>
      <td>406,548,765</td>
      <td class="bg-light-red">9,425</td>
      <td class="bg-light-red">52.9</td>
  </tbody>
</table>

## Conclusion ##

It was interesting to see, that the SQL Server 2017 was the fastest database to write the historic time series data. Without any changes to its default 
configuration! This is probably a highly biased benchmark result, because I am using a Windows 10 machine in these tests. But I needed these figures to 
see what database I can recommend for Windows Servers, that need to digest a high influx of Time series data.

But what's all the worlds data worth, if we cannot read it efficiently? 

In the next part of the series I will investigate how efficient queries on the databases are and how to optimize it.

[PostgreSQLCopyHelper]: https://github.com/bytefish/PostgreSQLCopyHelper
[Npgsql]: https://github.com/npgsql/npgsql
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[Columnstore indexes]: https://docs.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview
[timescaledb-tune]: https://github.com/timescale/timescaledb-tune
[The world’s most valuable resource is no longer oil, but data]: https://www.economist.com/leaders/2017/05/06/the-worlds-most-valuable-resource-is-no-longer-oil-but-data
[FTP Link]: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/
[TimescaleDB]: https://www.timescale.com/
[Elasticsearch]: https://www.elastic.co/
[SQL Server]: https://www.microsoft.com/de-de/sql-server/sql-server-2017
[InfluxData]: https://www.influxdata.com/
[InfluxDB]: https://www.influxdata.com/time-series-platform/influxdb/
[DWD Open Data]: https://opendata.dwd.de/
[Deutscher Wetterdienst (DWD)]: https://www.dwd.de
[GermanWeatherDataExample/Resources/files.md]: https://github.com/bytefish/GermanWeatherDataExample/blob/master/GermanWeatherData/Resources/files.md
