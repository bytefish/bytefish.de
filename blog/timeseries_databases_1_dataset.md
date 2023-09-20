title: Timeseries Databases Part 1: Parsing a Dataset with .NET
date: 2019-02-10 14:00
tags: timeseries, databases, dotnet, csharp
category: timeseries
slug: timeseries_databases_1_dataset
author: Philipp Wagner
summary: This article shows how to parse CSV data with .NET.

I often had to deal with large amounts time series data in my career and I have never been able 
to give qualified answers or recommendations for one database or another. So in a series of articles 
I want to learn more about [TimescaleDB] and [InfluxDB].

In this article I will start with parsing a CSV dataset using .NET. The Dataset is going to be used in the 
upcoming articles. 

All code to reproduce the article can be found in my GitHub repository at:

* [https://codeberg.org/bytefish/GermanWeatherDataExample](https://codeberg.org/bytefish/GermanWeatherDataExample)

## The Dataset ##

The [DWD Open Data] portal of the [Deutscher Wetterdienst (DWD)] gives access to the historical weather data in Germany. I decided 
to use all available historical air temperature data for Germany given in a 10 minute resolution ([FTP Link]). 

If you want to recreate the example, you can find the list of CSV files in the GitHub repository at: [GermanWeatherDataExample/Resources/files.md].

The DWD dataset is given as CSV files and has a size of approximately 25.5 GB.

## Parsing the Station Data ##

[FixedLengthTokenizer]: http://bytefish.github.io/TinyCsvParser/sections/userguide/tokenizer.html#fixedlengthtokenizer

Let's start by looking at the CSV data for the weather stations given in the file ``zehn_min_tu_Beschreibung_Stationen.txt``:

<a href="/static/images/blog/timeseries_databases/csv_stations.png">
	<img class="mediacenter" src="/static/images/blog/timeseries_databases/csv_stations.png" alt="CSV Stations Data Sample" />
</a>

We can see, that the file has two header rows and is fixed-width format. This format can be easily parsed with the [FixedLengthTokenizer] 
of [TinyCsvParser], which needs the indices of the data. 

### The Station Tokenizer ###

I start by defining a static class ``Tokenizers``, which defines the start and end column indices for each property:

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
                var columns = new[]
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

                return new FixedLengthTokenizer(columns, true);
            }
        }
    }
}
```

### The Station Model ###

Now we need the C# class, that maps to the properties of the Station. In the file the end date is optional, so 
we need to model it as a nullable ``DateTime``:

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

### The Station Mapper ###

A ``CsvMapping<Station>`` implementation is used to define the mapping between the column indices of the ``StationTokenizer`` and the 
C# class. All dates in the CSV file are given in a ``yyyyMMdd`` format, so we instantiate a custom TinyCsvParser ``DateTimeConverter`` and 
``NullableDateTimeConverter`` to correctly parse the data:

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

And that's it for the Station data already!

## Parsing the Weather Data ##

Let's start by looking at the CSV data for the weather data:

<a href="/static/images/blog/timeseries_databases/csv_weather_data.png">
	<img class="mediacenter" src="/static/images/blog/timeseries_databases/csv_weather_data.png" alt="CSV Stations Data Sample" />
</a>

The data uses a ``;`` as Column Delimiter, so we can use a simple [StringSplitTokenizer].

### Tokenizer ###

First of all we add the Tokenizer to the ``Tokenizers`` class:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using TinyCsvParser.Tokenizer;

namespace Experiments.Common.Csv.Tokenizer
{
    public static class Tokenizers
    {
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

### The Weather Data Model ###

I want to parse all data of the Dataset, so the C# model includes all properties of the CSV data:

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

### Custom Converters for the Dataset ###

Now there are some interesting properties to notice in the dataset:

1. The Station identifier has no left-padded zeros, like in the CSV station data.
2. Missing Values are defined with ``-999``.
3. All dates in the data are given as UTC.

We are going to write Custom Converters for each of the 

### 1. Converter: Left Padding the Station Identifier ###

First of all we need to make sure, that the station identifier has left padded zeros to match the Station identifier.

The converters in [TinyCsvParser] implement the ``ITypeConverter<TTargetType>`` interface, which requires to implement 
a ``TryConvert(string value, out TTargetType result)`` method. If the input string cannot be parsed into the target 
type, then you should return ``false``. If the converter is able to convert the data you should assign the result 
and return true.

The ``StringPadLeftConverter`` simply uses the ``string.PadLeft`` to implement the required funcationality.

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

### 2. Converter: Handling missing values in the data ###

The next converter is the ``IgnoreMissingValuesConverter``, which ignores values matching a given string:

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

#### 3. Converter: Handling UTC Timestamps ####

From the documentation of the dataset we know, that all dates are given as UTC. But if we would parse the given data 
it would leave us with an unspecified DateTime Kind, because a string with a format ``yyyyMMddmmhh``, for example 
``200001010000``, contains no timezone designation.

Instead we need to explicitly specify the kind of the DateTime by using the ``DateTime.SpecifyKind`` method.

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

### The Weather Data Mapper ###

With all custom Converters in place the mapping between the CSV data and the C# model can be defined as 
a ``CsvMapping<LocalWeatherData>``:

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

### Extension #1: Skipping multiple lines ###

Looking at the station data you will see there are 2 header lines, that cannot be parsed. Sadly skipping a single header line 
is something I hardcoded into the [TinyCsvParser]. I will make it more configurable for future releases, but I cannot promise 
a timeline.

As the author of the library, it is very easy for me to add a ``ReadFromFile`` method, that allows skipping multiple lines:

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


### Extension #2: Enumerable Batch Operator ###

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

### Building the Parsers: Connecting all the things ###

After all the preliminary work we can finally build the ``CsvParser`` for the data. I also define both in a 
static class, so I can easily access the Parsers. No magic involved:

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
                CsvParserOptions csvParserOptions = new CsvParserOptions(
                    skipHeader: false, 
                    commentCharacter: string.Empty, 
                    tokenizer: Tokenizers.StationsTokenizer,
                    degreeOfParallelism: 1,
                    keepOrder: false);

                return new CsvParser<Station>(csvParserOptions, new StationMapper());
            }
        }

        public static CsvParser<LocalWeatherData> LocalWeatherDataParser
        {
            get
            {
                CsvParserOptions csvParserOptions = new CsvParserOptions(
                    skipHeader: false, 
                    commentCharacter: string.Empty, 
                    tokenizer: Tokenizers.LocalWeatherDataTokenizer, 
                    degreeOfParallelism: 1, 
                    keepOrder: false);

                return new CsvParser<LocalWeatherData>(csvParserOptions, new LocalWeatherDataMapper());
            }
        }
    }
}
```

## Conclusion ##

We are done with parsing the data. There was quite some non-intuitive work to be done, like defining custom converters 
on the CSV data. But we got all data processing parts nicely separated and have created reusable classes. 

With LINQ we can write very elegant processing pipelines for the data:

```csharp
private static void ParseStationsExample()
{
    var numberOfStations = Parsers.StationParser
        .ReadFromFile(@"G:\Datasets\CDC\zehn_min_tu_Beschreibung_Stationen.txt", Encoding.UTF8, 2)
        .Where(x => x.IsValid)
        .Select(x => x.Result)
        .Count();

    Console.WriteLine($"Found {numberOfStations} Stations!");
}
```

And it outputs:

```
Found 505 Stations!
```

We are now ready to throw the data at the time series databases.

[StringSplitTokenizer]: http://bytefish.github.io/TinyCsvParser/sections/userguide/tokenizer.html#stringsplittokenizer
[Deep Learning]: https://en.wikipedia.org/wiki/Deep_learning
[PostgreSQLCopyHelper]: https://codeberg.org/bytefish/PostgreSQLCopyHelper
[Npgsql]: https://github.com/npgsql/npgsql
[TinyCsvParser]: https://codeberg.org/bytefish/TinyCsvParser
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
[GermanWeatherDataExample/Resources/files.md]: https://codeberg.org/bytefish/GermanWeatherDataExample/blob/master/GermanWeatherData/Resources/files.md