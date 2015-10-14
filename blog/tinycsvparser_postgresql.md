title: PostgreSQL and TinyCsvParser
date: 2015-09-25 10:54
tags: c#, csv, tinycsvparser, postgresql
category: c#
slug: tinycsvparser_postgresql
author: Philipp Wagner
summary: This article shows how to insert a large CSV dataset into PostgreSQL with TinyCsvParser and Npgsql.

[Npgsql]: https://github.com/npgsql
[PostgreSQL]: http://www.postgresql.org
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[MIT License]: https://opensource.org/licenses/MIT

In my last post you have seen how to use [TinyCsvParser] for reading a large dataset into memory, but actually there are 
only few use cases where reading an entire dataset into memory is really neccessary. 

In reality you often have to import the data into a database, so efficient queries can be made on the data. This post 
shows how to efficiently insert data into a PostgreSQL database with [TinyCsvParser] and [Npgsql].

## Dataset ##

In this post we are parsing a real life dataset. It's the local weather data in March 2015 gathered by all weather stations 
in the USA. You can obtain the data  ``QCLCD201503.zip`` from:
 
* [http://www.ncdc.noaa.gov/orders/qclcd](http://www.ncdc.noaa.gov/orders/qclcd)

The File size is ``557 MB`` and it has ``4,496,262`` lines.

## Preparing the Database ##

The data file has something around ``40`` columns. We only want to use three columns of the file (``WBAN``, ``Sky Condition`` and ``Date``).

Here is the SQL Script to create the table, where the data will be stored.

```sql
CREATE TABLE sample.local_weather
(
  local_weather_id serial NOT NULL,
  wban text,
  sky_condition text,
  date date  
)
```

## Domain Model ##

The domain model in this example simply holds the columns we are interested in.

```csharp
public class LocalWeatherData
{
    public string WBAN { get; set; }

    public DateTime Date { get; set; }

    public string SkyCondition { get; set; }
}
```

## Bulk Write with Npgsql ##

You can imagine, that inserting millions of lines one by one isn't really efficient. The application will wait for the synchronous 
database calls to finish and going asynchronous doesn't help either. The most efficient way to insert data into a PostgreSQL database 
is to use its COPY command, which can be used with [Npgsql] for a .NET application.

You can read everything about the COPY command in the [PostgreSQL Manual](http://www.postgresql.org/docs/9.4/static/sql-copy.html).

I am a *huge* fan of useful APIs, so I have written a small wrapper called ``PostgreSQLCopyHelper``, that wraps the [Npgsql] implementation 
behind a nice Fluent API. It doesn't implement every data type at the moment. It would be great if extensions are streamed back into the 
repository, which can be found at:

* [https://github.com/bytefish/PostgreSQLCopyHelper](https://github.com/bytefish/PostgreSQLCopyHelper)

The mapping between the domain model and database table can now be defined with the ``PostgreSQLCopyHelper``.

```csharp
private PostgeSQLCopyHelper<LocalWeatherData> CreateCopyHelper() {
    
    return new PostgeSQLCopyHelper<LocalWeatherData>()
        .WithTableName("sample", "local_weather")
        .AddColumn("wban", x => x.WBAN)
        .AddColumn("sky_condition", x => x.SkyCondition)
        .AddColumn("date", x => x.Date);
    
}
```

See how a Fluent API makes writing these mappings easy? 

That's it for the bulk writing part already!

## Benchmark ##

These benchmarks are carried out on a ``7200`` RPM hard drive and an Intel Core i5-3450 CPU. I am sure you'll see an even
greater speed-up when running these benchmarks on a Solid-state drive (SSD). All code is available at the end of this article.

### Results ###

The import pipeline is simple:

1. Create a ``TinyCsvParser.CsvParser`` for the ``LocalWeatherData``
2. Create a ``PostgreSQLCopyHelper`` for the ``LocalWeatherData``
3. Read the CSV File with the ``TinyCsvParser.CsvParser``
4. Write to the PostgreSQL database with the ``PostgreSQLCopyHelper``

In code this translates to:

```csharp
namespace PostgreSQLBulkCopyTest
{
    [TestFixture]
    public class BulkCopyTest
    {
        [Test]
        public void TinyCsvParserBenchmark()
        {
            CsvParser<LocalWeatherData> csvParser = CreateCsvParser();
            PostgreSQLCopyHelper<LocalWeatherData> copyHelper = CreateCopyHelper();

            BenchmarkUtilities.MeasureElapsedTime(string.Format("TinyCsvParser"),
                () =>
                {
                    var pipeline = csvParser
                        .ReadFromFile(@"C:\Users\philipp\Downloads\csv\201503hourly.txt", Encoding.ASCII)
                        .Where(x => x.IsValid)
                        .Select(x => x.Result)
                        .AsSequential();

                    WriteToDatabase(copyHelper, pipeline);
                });
        }

        private CsvParser<LocalWeatherData> CreateCsvParser()
        {
            var csvMapping = new LocalWeatherDataMapper();
            var csvParserOptions = CreateCsvParserOptions();

            return new CsvParser<LocalWeatherData>(csvParserOptions, csvMapping);
        }

        private CsvParserOptions CreateCsvParserOptions()
        {
            var skipHeader = true; // The dataset has a header.
            var fieldsSeparator = new[] { ',' }; // Separator is a , for the example.
            var orderedResults = false; // Not important for the import. Save some memory.
            var degreeOfParallelism = 4; // Use all cores!

            return new CsvParserOptions(skipHeader, fieldsSeparator, degreeOfParallelism, orderedResults);
        }

        private PostgreSQLCopyHelper<LocalWeatherData> CreateCopyHelper()
        {
            return new PostgreSQLCopyHelper<LocalWeatherData>()
                .WithTableName("sample", "local_weather")
                .AddColumn("wban", x => x.WBAN)
                .AddColumn("sky_condition", x => x.SkyCondition)
                .AddColumn("date", x => x.Date);
        }

        private void WriteToDatabase(PostgreSQLCopyHelper<LocalWeatherData> copyHelper, IEnumerable<LocalWeatherData> entities)
        {
            using (var connection = new NpgsqlConnection("Server=127.0.0.1;Port=5432;Database=sampledb;User Id=philipp;Password=test_pwd;"))
            {
                connection.Open();

                copyHelper.SaveAll(connection, entities);
            }
        }
    }
}
```

The whole import is done in under ``17`` seconds!

```
[TinyCsvParser] RunTime 00:00:16.89
```

And we can verify it in the database with SQL.

```sql
> SELECT count(*) FROM sample.local_weather;

4496262
```

## Conclusion ##

It was really easy to connect [Npgsql] and [TinyCsvParser]! By using the [PostgreSQL] COPY commands, we were able to 
import the entire CSV file in ``17`` seconds. The whole import pipeline is just a few lines of code and it was really 
fun to write.

Working with the binary import of [Npgsql] was amazingly simple and very uncomplicated to implement. [Npgsql] team you did a great job!

## Code ##

### BulkCopyTest.cs ###

```csharp
using Npgsql;
using NUnit.Framework;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using TinyCsvParser;
using TinyCsvParser.Mapping;
using TinyCsvParser.TypeConverter;

namespace PostgreSQLBulkCopyTest
{
    [TestFixture]
    public class BulkCopyTest
    {

        public class LocalWeatherData
        {
            public string WBAN { get; set; }

            public DateTime Date { get; set; }

            public string SkyCondition { get; set; }
        }

        public class LocalWeatherDataMapper : CsvMapping<LocalWeatherData>
        {
            public LocalWeatherDataMapper()
            {
                MapProperty(0, x => x.WBAN);
                MapProperty(1, x => x.Date).WithCustomConverter(new DateTimeConverter("yyyyMMdd"));
                MapProperty(4, x => x.SkyCondition);
            }
        }

        [Test]
        public void TinyCsvParserBenchmark()
        {
            CsvParser<LocalWeatherData> csvParser = CreateCsvParser();
            PostgreSQLCopyHelper<LocalWeatherData> copyHelper = CreateCopyHelper();

            BenchmarkUtilities.MeasureElapsedTime(string.Format("TinyCsvParser"),
                () =>
                {
                    var pipeline = csvParser
                        .ReadFromFile(@"C:\Users\philipp\Downloads\csv\201503hourly.txt", Encoding.ASCII)
                        .Where(x => x.IsValid)
                        .Select(x => x.Result)
                        .AsSequential();

                    WriteToDatabase(copyHelper, pipeline);
                });
        }

        private CsvParser<LocalWeatherData> CreateCsvParser()
        {
            var csvMapping = new LocalWeatherDataMapper();
            var csvParserOptions = CreateCsvParserOptions();

            return new CsvParser<LocalWeatherData>(csvParserOptions, csvMapping);
        }

        private CsvParserOptions CreateCsvParserOptions()
        {
            var skipHeader = true; // The dataset has a header.
            var fieldsSeparator = new[] { ',' }; // Separator is a , for the example.
            var orderedResults = false; // Not important for the import. Save some memory.
            var degreeOfParallelism = 4; // Use all cores!

            return new CsvParserOptions(skipHeader, fieldsSeparator, degreeOfParallelism, orderedResults);
        }

        private PostgreSQLCopyHelper<LocalWeatherData> CreateCopyHelper()
        {
            return new PostgreSQLCopyHelper<LocalWeatherData>()
                .WithTableName("sample", "local_weather")
                .AddColumn("wban", x => x.WBAN)
                .AddColumn("sky_condition", x => x.SkyCondition)
                .AddColumn("date", x => x.Date);
        }

        private void WriteToDatabase(PostgreSQLCopyHelper<LocalWeatherData> copyHelper, IEnumerable<LocalWeatherData> entities)
        {
            using (var connection = new NpgsqlConnection("Server=127.0.0.1;Port=5432;Database=sampledb;User Id=philipp;Password=test_pwd;"))
            {
                connection.Open();

                copyHelper.SaveAll(connection, entities);
            }
        }
    }
}
```

### BenchmarkUtilities.cs ###

```csharp
using System;
using System.Diagnostics;

namespace PostgreSQLBulkCopyTest
{
    public static class BenchmarkUtilities
    {
        public static void MeasureElapsedTime(string description, Action action)
        {
            // Get the elapsed time as a TimeSpan value.
            TimeSpan ts = MeasureElapsedTime(action);

            // Format and display the TimeSpan value.
            string elapsedTime = String.Format("{0:00}:{1:00}:{2:00}.{3:00}",
                ts.Hours, ts.Minutes, ts.Seconds,
                ts.Milliseconds / 10);

            Console.WriteLine("[{0}] RunTime {1}", description, elapsedTime);
        }

        public static TimeSpan MeasureElapsedTime(Action action)
        {
            Stopwatch stopWatch = new Stopwatch();

            stopWatch.Start();
            action();
            stopWatch.Stop();

            return stopWatch.Elapsed;
        }
    }
}
```

### PostgreSQLCopyHelper.cs ###

```csharp
using Npgsql;
using NpgsqlTypes;
using System;
using System.Linq;
using System.Collections.Generic;

namespace PostgreSQLCopyHelper
{
    public class PostgreSQLCopyHelper<TEntity>
    {
        private class TableDefinition
        {
            public string Schema { get; set; }

            public string TableName { get; set; }

            public string GetFullQualifiedTableName()
            {
                if (string.IsNullOrWhiteSpace(Schema))
                {
                    return TableName;
                }
                return string.Format("{0}.{1}", Schema, TableName);
            }

            public override string ToString()
            {
                return string.Format("TableDefinition (Schema = {0}, TableName = {1})", Schema, TableName);
            }
        }

        private class ColumnDefinition
        {
            public string ColumnName { get; set; }

            public Action<NpgsqlBinaryImporter, TEntity> Write { get; set; }

            public override string ToString()
            {
                return string.Format("ColumnDefinition (ColumnName = {0}, Serialize = {1})", ColumnName, Write);
            }
        }

        private TableDefinition Table { get; set; }

        private List<ColumnDefinition> Columns { get; set; }

        public PostgreSQLCopyHelper()
        {
            Columns = new List<ColumnDefinition>();
        }

        public PostgreSQLCopyHelper<TEntity> WithTableName(string schemaName, string tableName)
        {
            Table = new TableDefinition
            {
                Schema = schemaName,
                TableName = tableName
            };
            return this;
        }

        public PostgreSQLCopyHelper<TEntity> AddColumn(string columnName, Func<TEntity, string> propertyGetter)
        {
            AddColumn(columnName, (writer, entity) => writer.Write(propertyGetter(entity), NpgsqlDbType.Text));

            return this;
        }

        public PostgreSQLCopyHelper<TEntity> AddColumn(string columnName, Func<TEntity, System.DateTime> propertyGetter)
        {
            AddColumn(columnName, (writer, entity) => writer.Write(propertyGetter(entity), NpgsqlDbType.Date));

            return this;
        }

        public void SaveAll(NpgsqlConnection connection, IEnumerable<TEntity> entities)
        {
            using (var binaryCopyWriter = connection.BeginBinaryImport(GetCopyCommand()))
            {
                try
                {
                    WriteToStream(binaryCopyWriter, entities);
                }
                catch (Exception)
                {
                    binaryCopyWriter.Cancel();

                    throw;
                }
            }
        }

        private void WriteToStream(NpgsqlBinaryImporter writer, IEnumerable<TEntity> entities)
        {
            foreach (var entity in entities)
            {
                writer.StartRow();

                foreach (var columnDefinition in Columns)
                {
                    columnDefinition.Write(writer, entity);
                }
            }
        }

        private PostgreSQLCopyHelper<TEntity> AddColumn(string columnName, Action<NpgsqlBinaryImporter, TEntity> action)
        {
            Columns.Add(new ColumnDefinition
            {
                ColumnName = columnName,
                Write = action
            });

            return this;
        }

        private string GetCopyCommand()
        {
            var commaSeparatedColumns = string.Join(", ", Columns.Select(x => x.ColumnName));

            return string.Format("COPY {0}({1}) FROM STDIN BINARY;",
                Table.GetFullQualifiedTableName(),
                commaSeparatedColumns);
        }
    }
}
```
