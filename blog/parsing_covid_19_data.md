title: Parsing the COVID-19 Data with C#
date: 2020-02-15 09:31
tags: csv, dotnet, csharp, datamining
category: covid-19
slug: parsing_covid_19_data
author: Philipp Wagner
summary: Using C# to parse the COVID-19 data.

A new decease called [COVID-19] appeared in December 2019 and is headlining news all 
around the world. There is much we still have to learn about it, but fear travels fast 
these days... thanks to Twitter, Facebook and social media. 

So what can we do about it? Maybe get some official data first.

The [John Hopkins University] operates a dashboard for tracking the [COVID-19] spread and 
shares the data in a Github repository:

> This is the data repository for the 2019 Novel Coronavirus Visual Dashboard operated by 
> the Johns Hopkins University Center for Systems Science and Engineering (JHU CCSE). Also, 
> Supported by ESRI Living Atlas Team and the Johns Hopkins University Applied Physics Lab 
> (JHU APL).

The John Hopkins Github repository with the data is available at:

* [https://github.com/CSSEGISandData/COVID-19](https://github.com/CSSEGISandData/COVID-19)

I thought a first step is to show how to parse the data by the John Hopkins University and 
get it into a SQL database. From there we can process the data using tools like SQL, Microsoft 
Excel, R and so on.

All code in this article can be found at:

* [https://github.com/bytefish/ExampleDataAnalysis](https://github.com/bytefish/ExampleDataAnalysis)

So let's start!

## Parsing the CSV Data from Github ##

We start by defining the model ``Observation``, which holds the CSV data: 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace ExampleDataAnalysis.Github.Models
{
    public class Observation
    {
        public string Province { get; set; }

        public string Country { get; set; }

        public double Lat { get; set; }

        public double Lon { get; set; }

        public DateTime Timestamp { get; set; }

        public int Confirmed { get; set; }

        public int Deaths { get; set; }

        public int Recovered { get; set; }

    }
}
```

Next we write the parser to download and transform the CSV data into the ``Observation`` model. 

I used the ``RFC4180Tokenizer`` of [TinyCsvParser] to read the CSV, because a simple ``string.Split`` won't 
work with quoted data. I didn't use the rest of the parser library. Why? Because the CSV provided by the John 
Hopkins University has a variable number of columns and using a library would only complicate things.

The parser code isn't hard to understand. I first download the three files from Github, run some basic checks 
and extract the observation timestamps. For each of the CSV files I am creating a dictionary, that holds the 
Province / Country as the Key and the tokenized CSV data of the whole line.

I then iterate over the Province / Countries, and for each one I am zipping all three tokenized lines and create the 
``Observation`` based on it.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ExampleDataAnalysis.Github.Models;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using TinyCsvParser.Tokenizer.RFC4180;

namespace ExampleDataAnalysis.Github
{
    public class GithubObservationReader
    {
        private readonly HttpClient httpClient;

        public GithubObservationReader()
            : this(new HttpClient()) { }

        public GithubObservationReader(HttpClient httpClient)
        {
            this.httpClient = httpClient;
        }

        public IEnumerable<Observation> GetObservations()
        {
            var confirmed = GetConfirmedCasesFromGithubAsync().Result
                .Split(new[] { '\n' }, StringSplitOptions.None)
                .ToList();

            var deaths = GetDeathCasesFromGithubAsync().Result
                .Split(new[] { '\n' }, StringSplitOptions.None)
                .ToList();

            var recovered = GetRecoveredCasesFromGithubAsync().Result
                .Split(new[] { '\n' }, StringSplitOptions.None)
                .ToList();

            // Make sure all data has the same header, so the Timestamps match:
            if(!new[] { deaths[0], recovered[0] }.All(x => string.Equals(x, confirmed[0], StringComparison.InvariantCulture)))
            {
                throw new Exception($"Different Headers (Confirmed = {confirmed[0]}, Deaths = {deaths[0]}, Recovered = {recovered[0]}");
            }

            // Make sure all data has the same number of rows, or we can stop here:
            if(!new[] { deaths.Count, recovered.Count}.All(x => x == confirmed.Count))
            {
                throw new Exception($"Different Number of Rows (Confirmed = {confirmed.Count}, Deaths = {deaths.Count}, Recovered = {recovered.Count}");
            }

            var tokenizer = new RFC4180Tokenizer(new Options('"', '\\', ','));

            // Get Header Row:
            var header = tokenizer.Tokenize(confirmed[0])
                .ToArray();

            // Get the TimeStamps:
            var observationDateTimes = header
                .Skip(4)
                .Select(x => DateTime.Parse(x, CultureInfo.InvariantCulture))
                .ToList();

            // Now create a Lookup on the Raw Datas Province and Country:
            var confirmedLookup = confirmed.Skip(1)
                .Select(x => tokenizer.Tokenize(x))
                .Where(x => x.Length == header.Length)
                .ToDictionary(x => $"{x[0]},{x[1]}", x => x);

            var deathsLookup = deaths.Skip(1)
                .Select(x => tokenizer.Tokenize(x))
                .Where(x => x.Length == header.Length)
                .ToDictionary(x => $"{x[0]},{x[1]}", x => x);

            var recoveredLookup = recovered.Skip(1)
                .Select(x => tokenizer.Tokenize(x))
                .Where(x => x.Length == header.Length)
                .ToDictionary(x => $"{x[0]},{x[1]}", x => x);

            // Get all keys we want to iterate over:
            var keys = confirmedLookup.Keys.Concat(deathsLookup.Keys).Concat(recoveredLookup.Keys).Distinct().ToList();

            foreach(var key in keys)
            {
                // We now zip all 3 series, this will lead to an Exception if a key is missing for any Lookup dictionary:
                var observations = ZipThree(
                    first: confirmedLookup[key].Skip(4), 
                    second: deathsLookup[key].Skip(4), 
                    third: recoveredLookup[key].Skip(4), 
                    func: (first, second, third) => new { Confirmed = first, Death = second, Recovered = third })
                    // Now zip with the Observation Date Time in the Header:
                    .Zip(observationDateTimes, (value, dateTime) => new Observation
                     {
                         Province = confirmedLookup[key][0],
                         Country = confirmedLookup[key][1],
                         Lat = double.Parse(confirmedLookup[key][2].Trim(), CultureInfo.InvariantCulture),
                         Lon = double.Parse(confirmedLookup[key][3].Trim(), CultureInfo.InvariantCulture),
                         Timestamp = dateTime,
                         Confirmed = GetCountSafe(value.Confirmed),
                         Deaths = GetCountSafe(value.Death),
                         Recovered = GetCountSafe(value.Recovered)
                     });

                // And return the observations flat out:
                foreach(var observation in observations)
                {
                    yield return observation;
                }
            }
        }

        public static IEnumerable<TResult> ZipThree<T1, T2, T3, TResult>(IEnumerable<T1> first, IEnumerable<T2> second, IEnumerable<T3> third, Func<T1, T2, T3, TResult> func)
        {
            using (var e1 = first.GetEnumerator())
            {
                using (var e2 = second.GetEnumerator())
                {
                    using (var e3 = third.GetEnumerator())
                    {
                        {
                            while (e1.MoveNext() && e2.MoveNext() && e3.MoveNext())
                            {
                                yield return func(e1.Current, e2.Current, e3.Current);
                            }
                        }
                    }
                }
            }
        }

        private static int GetCountSafe(string value)
        {
            if(string.IsNullOrWhiteSpace(value))
            {
                return 0;
            }
            
            return (int) double.Parse(value, CultureInfo.InvariantCulture);
        }

        public async Task<string> GetConfirmedCasesFromGithubAsync()
        {
            return await httpClient
                .GetStringAsync("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Confirmed.csv")
                .ConfigureAwait(false);
        }

        public async Task<string> GetDeathCasesFromGithubAsync()
        {
            return await httpClient
                .GetStringAsync("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Deaths.csv")
                .ConfigureAwait(false);
        }

        public async Task<string> GetRecoveredCasesFromGithubAsync()
        {
            return await httpClient
                .GetStringAsync("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Recovered.csv")
                .ConfigureAwait(false);
        }
    }
}
```

## SQL Side ##

Now let's create the SQL database. I am using an SQL Server in this example.

### A Batch Script for creating the database ###

I am not a huge friend of using Entity Framework to automagically create a database or having 
migrations applied automatically. In my experience it only leads to chaos and tears.

For small projects I always have a simple Batch script, that you may have already seen on this 
page. The script sets some default values for the ``ServerName`` and ``DatabaseName`` and then 
executes an SQL script ``create_database.sql`` to create the given database.

```batch
@echo off

:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

set SQLCMD_EXECUTABLE="C:\Program Files\Microsoft SQL Server\110\Tools\Binn\SQLCMD.EXE"
set STDOUT=stdout.log
set STDERR=stderr.log
set LOGFILE=query_output.log

set ServerName=.\MSSQLSERVER2017
set DatabaseName=SampleDatabase

call :AskQuestionWithYdefault "Use Server (%ServerName%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y] (
	set /p ServerName="Enter Server: "
)

call :AskQuestionWithYdefault "Use Database (%DatabaseName%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y]  (
	set /p DatabaseName="Enter Database: "
)

1>%STDOUT% 2>%STDERR% (

	:: Database
	%SQLCMD_EXECUTABLE% -S %ServerName% -i "create_database.sql" -v dbname=%DatabaseName% -o %LOGFILE%
	
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

### SQL Script ###

And here is the SQL Script, which creates the database for storing observations.

```sql
--
-- DATABASE
--
IF DB_ID('$(dbname)') IS NULL
BEGIN
    CREATE DATABASE $(dbname)
END
GO

use $(dbname)
GO 

-- 
-- SCHEMAS
--
IF NOT EXISTS (SELECT name from sys.schemas WHERE name = 'sample')
BEGIN

	EXEC('CREATE SCHEMA sample')
    
END
GO

--
-- TABLES
--
IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[sample].[Observation]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [sample].[Observation](
        [ObservationID] INT PRIMARY KEY IDENTITY,
        [Province] [NVARCHAR](100),
        [Country] [NVARCHAR](100) NOT NULL,
        [Timestamp] [DATETIME2],
        [Confirmed] INT,
        [Deaths] INT,
        [Recovered] INT,
        [Lat] DOUBLE PRECISION,
        [Lon] DOUBLE PRECISION
    );

END
GO
```

Now what happens if we import the same data multiple times? We don't want to end up having hundred 
of duplicate observations for the same Province, Country and Timestamp. This could easily skew results, 
if we are not very careful.

Let's avoid this and set a unique index on the three columns ``Province``, ``Country`` and ``Timestamp``:

```sql
--
-- INDEXES
--
IF EXISTS (SELECT name FROM sys.indexes WHERE name = N'UX_Observation')
BEGIN
    DROP INDEX [UX_Observation] on [sample].[Observation];
END
GO

CREATE UNIQUE INDEX UX_Observation ON [sample].[Observation](Province, Country, Timestamp);   
GO
```

So the database will now scream, when we try to insert the duplicate data. Perfect!

What's left is how to insert or update the data. There are a probably a million ways to do it from 
the application-side. But I always tend to use the following simple way:

1. I define a Type ``ObservationType``, that more or less matches the table I want to update.
2. I create a ``MERGE`` procedure, that either inserts or updates the Observation.

In T-SQL this translates to:

```sql
--
-- STORED PROCEDURES
--
IF OBJECT_ID(N'[sample].[InsertOrUpdateObservation]', N'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [sample].[InsertOrUpdateObservation];
END
GO

IF EXISTS (SELECT * FROM sys.types WHERE is_table_type = 1 AND name = 'ObservationType')
BEGIN
    DROP TYPE [sample].[ObservationType];
END
GO

CREATE TYPE [sample].[ObservationType] AS TABLE (
    [Province] [NVARCHAR](255),
    [Country] [NVARCHAR](255),
    [Timestamp] [DATETIME2],
    [Confirmed] INT,
    [Deaths] INT,
    [Recovered] INT,
    [Lat] DOUBLE PRECISION,
    [Lon] DOUBLE PRECISION
);
GO

CREATE PROCEDURE [sample].[InsertOrUpdateObservation]
  @Entities [sample].[ObservationType] ReadOnly
AS
BEGIN
    
    SET NOCOUNT ON;
 
    MERGE [sample].[Observation] AS TARGET USING @Entities AS SOURCE ON (TARGET.Province = SOURCE.Province) AND (TARGET.Country = SOURCE.Country) AND (TARGET.Timestamp = SOURCE.Timestamp)
    WHEN MATCHED THEN
        UPDATE SET TARGET.Confirmed = SOURCE.Confirmed, TARGET.Deaths = SOURCE.Deaths, TARGET.Recovered = SOURCE.Recovered, TARGET.Lat = SOURCE.Lat, TARGET.Lon = SOURCE.Lon
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (Province, Country, Timestamp, Confirmed, Deaths, Recovered, Lat, Lon) 
        VALUES (SOURCE.Province, SOURCE.Country, SOURCE.Timestamp, SOURCE.Confirmed, SOURCE.Deaths, SOURCE.Recovered, SOURCE.Lat, SOURCE.Lon);

END
GO
```

### Application-side for the SQL Integration ###

We start by defining the ``Observation`` for SQL. I am using some Attributes, because I want to 
be able to easily query the database with Entity Framework. See how the attributes match the database 
columns:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.ComponentModel.DataAnnotations.Schema;

namespace ExampleDataAnalysis.SqlServer.Models
{
    [Table("Observation", Schema = "sample")]
    public class Observation
    {
        [Column("ObservationID")]
        public int ObservationId { get; set; }

        [Column("Province")]
        public string Province { get; set; }

        [Column("Country")]
        public string Country { get; set; }

        [Column("Timestamp")]
        public DateTime Timestamp { get; set; }

        [Column("Confirmed")]
        public int Confirmed { get; set; }

        [Column("Deaths")]
        public int Deaths { get; set; }

        [Column("Recovered")]
        public int Recovered { get; set; }

        [Column("Lat")]
        public double Lat { get; set; }

        [Column("Lon")]
        public double Lon { get; set; }
    }
}
```

The EntityFramework ``DbContext`` then looks like this:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ExampleDataAnalysis.SqlServer.Models;
using Microsoft.EntityFrameworkCore;

namespace ExampleDataAnalysis.SqlServer.Context
{
    public class ApplicationDbContext : DbContext
    {
        private readonly string connectionString;

        public DbSet<Observation> Observations { get; set; }

        public ApplicationDbContext(string connectionString)
        {
            this.connectionString = connectionString;
        }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlServer(connectionString);
        }
    }
}
```

#### Calling the MERGE Procedure ####

To call the ``InsertOrUpdateObservation`` Stored Procedure I am using classic ADO.NET. I am also 
grouping the observation before inserting, to avoid duplicates in batches. Basically each ``Observation`` 
is converted into an ``SqlDataRecord`` and then sent using a Table Valued Parameter (TVP).

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ExampleDataAnalysis.SqlServer.Models;
using Microsoft.SqlServer.Server;
using System.Collections.Generic;
using System.Data;
using System.Data.SqlClient;
using System.Linq;

namespace ExampleDataAnalysis.SqlServer.Processors
{
    public class SqlServerBulkProcessor
    {
        private readonly string connectionString;

        public SqlServerBulkProcessor(string connectionString)
        {
            this.connectionString = connectionString;
        }

        public void Write(IEnumerable<Observation> observations)
        {
            if (observations == null)
            {
                return;
            }

            // There may be duplicates, avoid duplicates in Batch:
            var groupedObservations = observations
                .GroupBy(x => new { x.Province, x.Country, x.Timestamp })
                .Select(x => x.First());

            using (var conn = new SqlConnection(connectionString))
            {
                // Open the Connection:
                conn.Open();

                // Execute the Batch Write Command:
                using (SqlCommand cmd = conn.CreateCommand())
                {
                    // Build the Stored Procedure Command:
                    cmd.CommandText = "[sample].[InsertOrUpdateObservation]";
                    cmd.CommandType = CommandType.StoredProcedure;

                    // Create the TVP:
                    SqlParameter parameter = new SqlParameter();

                    parameter.ParameterName = "@Entities";
                    parameter.SqlDbType = SqlDbType.Structured;
                    parameter.TypeName = "[sample].[ObservationType]";
                    parameter.Value = ToSqlDataRecords(groupedObservations);

                    // Add it as a Parameter:
                    cmd.Parameters.Add(parameter);

                    // And execute it:
                    cmd.ExecuteNonQuery();
                }
            }
        }

        private IEnumerable<SqlDataRecord> ToSqlDataRecords(IEnumerable<Observation> observations)
        {
            // Construct the Data Record with the MetaData:
            SqlDataRecord sdr = new SqlDataRecord(
                new SqlMetaData("Province", SqlDbType.NVarChar, 100),
                new SqlMetaData("Country", SqlDbType.NVarChar, 100),
                new SqlMetaData("Timestamp", SqlDbType.DateTime2),
                new SqlMetaData("Confirmed", SqlDbType.Int),
                new SqlMetaData("Deaths", SqlDbType.Int),
                new SqlMetaData("Recovered", SqlDbType.Int),
                new SqlMetaData("Lat", SqlDbType.Real),
                new SqlMetaData("Lon", SqlDbType.Real)
            );

            // Now yield the Measurements in the Data Record:
            foreach (var observation in observations)
            {
                sdr.SetString(0, observation.Province);
                sdr.SetString(1, observation.Country);
                sdr.SetDateTime(2, observation.Timestamp);
                sdr.SetInt32(3, observation.Confirmed);
                sdr.SetInt32(4, observation.Deaths);
                sdr.SetInt32(5, observation.Recovered);
                sdr.SetFloat(6, (float) observation.Lat);
                sdr.SetFloat(7, (float) observation.Lon);

                yield return sdr;
            }
        }
    }
}
```

## Connecting all the Things ##

What's left is connecting all the code above. We can now write a simple Console application to download the CSV 
data, parse it and insert it into an SQL Server database. From there we have a lot more ways to play around with 
the data.

In the example code I am also writing the data to Elasticsearch, just to show how to further work with the data.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Linq;
using ExampleDataAnalysis.Elasticsearch;
using ExampleDataAnalysis.SqlServer.Context;
using ExampleDataAnalysis.SqlServer.Processors;
using Microsoft.EntityFrameworkCore;

namespace ExampleDataAnalysis
{
    class Program
    {
        private static string SqlServerConnectionString = @"Server=.\MSSQLSERVER2017;Database=SampleDatabase;Integrated Security=True";

        static void Main(string[] args)
        {
            UpdateAllDatabases();

            Console.WriteLine("Press [Enter] to exit ...");
            Console.Read();
        }

        private static void UpdateAllDatabases()
        {
            Console.WriteLine("Getting latest Data from Github ...");

            var source = GetGithubData();

            Console.WriteLine("Writing to SQL Server ...");

            // Then update the data in SQL Server:
            WriteToSqlServer(source);

            // Indexes the Data to Elasticsearch for Dashboards:
            Console.WriteLine("Do you want to write the data to Elasticsearch? (Y/N)");
            
            if(string.Equals(Console.ReadLine(), "Y", StringComparison.InvariantCultureIgnoreCase))
            {
                UpdateElasticsearchIndex();
            }
        }

        private static IEnumerable<Github.Models.Observation> GetGithubData()
        {

            return new Github.GithubObservationReader()
                .GetObservations()
                .ToList();
        }

        private static void WriteToSqlServer(IEnumerable<Github.Models.Observation> source)
        {
            // Convert the data into the SQL representation:
            var target = GetSqlServerData(source);

            // This kicks off a Stored Procedure using a MERGE to either insert or 
            // update an existing entries in a bulk fashion: 
            var processor = new SqlServerBulkProcessor(SqlServerConnectionString);

            processor.Write(target);
        }

        private static IEnumerable<SqlServer.Models.Observation> GetSqlServerData(IEnumerable<Github.Models.Observation> observations)
        {
            foreach (var observation in observations)
            {
                yield return new SqlServer.Models.Observation
                {
                    Province = observation.Province,
                    Country = observation.Country,
                    Timestamp = observation.Timestamp,
                    Confirmed = observation.Confirmed,
                    Deaths = observation.Deaths,
                    Recovered = observation.Recovered,
                    Lat = observation.Lat,
                    Lon = observation.Lon
                };
            }
        }

        private static void UpdateElasticsearchIndex()
        {
            var client = new ElasticSearchObservationClient(new Uri("http://localhost:9200"), "observations");

            using (var context = new ApplicationDbContext(SqlServerConnectionString))
            {
                var documents = context.Observations
                    // Do not track the Entities in the DbContext:
                    .AsNoTracking()
                    // Turn all Entities into the Elasticsearch Representation:
                    .Select(x => new Elasticsearch.Models.Observation
                    {
                        ObservationId = x.ObservationId,
                        Confirmed = x.Confirmed,
                        Country = x.Country,
                        Deaths = x.Deaths,
                        Timestamp = x.Timestamp,
                        Location = new Nest.GeoLocation(x.Lat, x.Lon),
                        Province = x.Province,
                        Recovered = x.Recovered
                    })
                    .AsEnumerable();

                var response = client.BulkIndex(documents);
            }
        }
    }
}
```

## Conclusion ##

And that's it. We now have the dataset in a Relational Database and can use it to easily process it in other systems.  

[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[John Hopkins University]: [https://systems.jhu.edu/]
[COVID-19]: https://en.wikipedia.org/wiki/2019-nCoV_acute_respiratory_disease