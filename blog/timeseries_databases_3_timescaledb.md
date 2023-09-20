title: Timeseries Databases Part 3: Writing Data to TimescaleDB from .NET
date: 2019-02-10 14:20
tags: timeseries, influxdb, databases, dotnet, csharp
category: timeseries
slug: timeseries_databases_3_timescaledb
author: Philipp Wagner
summary: This part shows how to use TimescaleDB with .NET.

## What is TimescaleDB? ##

The [TimescaleDB] docs describe TimescaleDB as:

> [...] an open-source time-series database optimized for fast ingest and complex queries. It speaks "full SQL" and 
> is correspondingly easy to use like a traditional relational database, yet scales in ways previously reserved for NoSQL 
> databases.

In [Part 1] of the series I have shown how to parse the [DWD Open Data] dataset, which will be used in this article.

All code to reproduce the article can be found in my GitHub repository at:

* [https://codeberg.org/bytefish/GermanWeatherDataExample](https://codeberg.org/bytefish/GermanWeatherDataExample)

## The Dataset ##

The [DWD Open Data] portal of the [Deutscher Wetterdienst (DWD)] gives access to the historical weather data in Germany. I decided 
to use all available historical air temperature data for Germany given in a 10 minute resolution ([FTP Link]). 

If you want to recreate the example, you can find the list of CSV files in the GitHub repository at: [GermanWeatherDataExample/Resources/files.md].

The DWD dataset is given as CSV files and has a size of approximately 25.5 GB.

## Implementation ##

### TimescaleDB in Windows ###

TimescaleDB comes as a PostgreSQL Extension and can be installed for Windows using an official Installer at:

* [https://docs.timescale.com/v1.0/getting-started/installation/windows/installation-windows](https://docs.timescale.com/v1.0/getting-started/installation/windows/installation-windows)

After the installation you have to modify the ``postgresql.config`` and add the ``timescaledb`` extension:

```
shared_preload_libraries = 'timescaledb'		# (change requires restart)
```

### Preparing PostgreSQL ###

First of all create the user ``philipp`` for connecting to the databases:

```
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
```

Then we can create the test database and set the owner to ``philipp``:

```
postgres=# CREATE DATABASE sampledb WITH OWNER philipp; 
```

For creating the TimescaleDB hypertable the user needs the ``SUPERUSER`` role, so for creating the  database the user ``philipp`` is given the required permissions:

```
postgres=# ALTER USER philipp WITH SUPERUSER;
```


### Creating the Database ###

In the `TimescaleDB/Sql` folder you can find the following ``create_database.bat`` script, which is used to simplify creating the database:

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

The `create_database.sql` script is used to create the schema and tables for the database:

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

### The SQL Weather Data Model ###

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

### Connecting the Parts: The LINQ Import Pipeline ###


The import pipeline for TimescaleDB is parallelized, because PostgreSQL creates a worker per connection. So if we 
write 4 batches in parallel, then TimescaleDB will have 4 worker processes for the incoming data. The batch size is 
set to 80,000 entities, because I didn't see any speedup with smaller / larger batches.

```csharp
private static void ProcessLocalWeatherData(string[] csvFiles)
{
    var processor = new LocalWeatherDataBatchProcessor(ConnectionString);

    csvFiles
        .AsParallel()
        .WithDegreeOfParallelism(4)
        .ForAll(file =>
        {
            log.Info($"Processing File: {file}");

            // Access to the List of Parsers:
            var batches = Parsers
                // Use the LocalWeatherData Parser:
                .LocalWeatherDataParser
                // Read the File:
                .ReadFromFile(file, Encoding.UTF8, 1)
                // Get the Valid Results:
                .Where(x => x.IsValid)
                // And get the populated Entities:
                .Select(x => x.Result)
                // Convert into the Sql Data Model:
                .Select(x => LocalWeatherDataConverter.Convert(x))
                // Batch:
                .Batch(80000);

            foreach (var batch in batches)
            {
                processor.Write(batch);
            }
        });
}
```

### Configuration ###

When I initially tested TimescaleDB the import was very slow due to using the default ``postgresql.conf`` configuration. 

The first thing you should always do when using TimscaleDB is to let [timescaledb-tune] tune the PostgreSQL configuration for 
you. It didn't help much for my DWD dataset, so some extra tuning was required. I got in contact with [Mike Freedman] from the 
[TimescaleDB] team and he gave me great tips, that I want to share.

In the first version I used a single threaded pipeline, because I thought PostgreSQL automatically spans multiple worker processes 
under load, but having a single COPY command is also single-threaded on the Server-side:

> My read of the writeup is that you are inserting with a single client / single COPY command?  That's actually "single threaded" on the 
> server side, so it's very hard to maximize insert rate with that.  In fact, the whole reason we wrote a parallel COPY tool. This will 
> probably have the biggest impact: https://github.com/timescale/timescaledb-parallel-copy

The dataset has 25.5 GB. So due to compression it does fit into memory for some of the column stores I tested, like InfluxDB and SQL 
Server. This can skew results when running benchmarks. If you want reliable figures, make sure your data set is large enough so the main 
memory is exceeded for all platforms. 

[Mike] gave me the advices:

> I would test it out to a larger dataset. Because of the compression you are seeing in some of the column stores (influx & SQL server) 
> your dataset isn't big enough to exceed main memory on those platforms. We often test our datasets out to 1B or even 10B rows.

TimescaleDB partitions the data into chunks. You can read about chunking on the TimescaleDB page [How we scaled SQL](https://www.timescale.com/how-it-works). The 
very good TimescaleDB documentation has further details at: [https://docs.timescale.com/v1.2/faq#hypertable-chunks](https://docs.timescale.com/v1.2/faq#hypertable-chunks).

[Mike] wrote to me on the number of chunks for the DWD dataset I have used: 

> Maximizing insert rate does requiring a little bit of tuning for a proper chunk size. The default chunk are 1 week [...]
>
> So the timestamps over the 400M rows are across 27 years?  So it's internally creating ~1400 chunks, each of ~280K rows. Probably 
> a bit excessive, especially on the query side (adds a little query planning overhead).  To keep things simple, I'd just go with 1 chunk 
> per year. You can do that here:
>
> https://docs.timescale.com/v1.0/api#create_hypertable

The command to create a chunk per year is:

> ``SELECT create_hypertable('conditions', 'time', chunk_time_interval => interval '1 year');``

Finally in my initial write-up I wanted to maximize the insert rate of TimescaleDB. Long story short: The bottleneck wasn't TimescaleDB at all
, but my CSV Parsing. In a later installment of the series I will put the worker processes on different machines, so I can maximize the inserts 
to TimescaleDB.

However if you do an initial import of the data, that doesn't need to be queried while written, then you probably want to put off the 
default indexes:

> It looks like you didn't turn off our "default indexes" that we build. If you are looking to maximize insert rate, one approach is to 
> you bulk load without index, then create an index after you load.  Many users do indeed incrementally create the index during loading, 
> but just point out if we want to be apples-to-apples to some other options. 

The command to turn off the default indices is:

> ``SELECT create_hypertable('conditions', 'time', create_default_indexes  => FALSE);``

## Conclusion ##

I think [TimescaleDB] is a great technology, which enables me to continue using PostgreSQL and having Time series capabilities as 
a Postgres extension. I hope the [TimescaleDB] team succeeds in their efforts. The team was also a great help for my initial write-up 
and helped me better understand the [TimescaleDB] internals.

In the end TimescaleDB was just as fast as the Microsoft SQL Server 2017. But due to a bottleneck when parsing the CSV data I don't want 
all this to be a benchmark and removed the timing results.

In a later post we will look at the read behavior of TimescaleDB.

[Mike Freedman]: https://github.com/mfreed
[Mike]: https://github.com/mfreed
[Part 1]: /blog/timeseries_databases_1_dataset
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