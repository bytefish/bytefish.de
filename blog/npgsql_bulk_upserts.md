title: Bulk Updates and Inserts with PostgreSQL using Composite Types
date: 2021-11-07 15:23
tags: dotnet, npgsql, postgres
category: postgres
slug: bulk_updates_postgres
author: Philipp Wagner
summary: On Bulk Updates with PostgreSQL and Npgsql.

Something, that often comes up in the [PostgreSQLCopyHelper] and [PgBulkInsert] issue trackers is how to do bulk 
updates with the libraries. Simple answer is: You can't. The underlying Postgres ``COPY`` protocol only supports 
inserts.

In SQL Server I've always used Table-valued Parameters (TVP) to send a batch of data over the wire and perform a 
``MERGE`` statement on the bulk data. So let's see how to do something similar in Postgres using composite types 
and Npgsql.

All code can also be found in a Gist at:

* [https://gist.github.com/bytefish/dbd2da81267990e9326044661be1c480](https://gist.github.com/bytefish/dbd2da81267990e9326044661be1c480)

[PostgreSQLCopyHelper]: https://github.com/PostgreSQLCopyHelper/PostgreSQLCopyHelper
[PgBulkInsert]: https://github.com/PgBulkInsert/PgBulkInsert

## Implementation ##

Imagine we want to bulk insert or update measurements of a device. 

We probably come up with a table like this:

```sql
CREATE TABLE sample.measurements
(
  device_id int,
  parameter_id int,
  timestamp timestamp with time zone,
  value double precision
);
```

We expect only a single value for a device and parameter at a given timestamp. 

So let's add an index to the ``sample.measurements`` table:

```sql
DROP INDEX IF EXISTS sample.unique_measurement;

CREATE UNIQUE INDEX unique_measurement ON sample.measurements(device_id, parameter_id, timestamp);
```

Now we can create a Composite Type, that matches the ``measurements`` table structure:


```sql
DROP TYPE IF EXISTS "sample"."measurement_type";

CREATE TYPE "sample"."measurement_type" AS (
  device_id int,
  parameter_id int,
  timestamp timestamp with time zone,
  value double precision
);
```

And finally we can write a Stored Procedure, that takes a ``measurement_type[]`` as a parameter, which is the 
data we want to insert. We are using the ``UNNEST`` operator to expand the array to a set of rows, and then 
use the ``INSERT ... ON CONFLICT ... DO UPDATE ...`` syntax for atomic updates:

```sql
CREATE OR REPLACE PROCEDURE sample.insert_or_update_measurements(p_measurements sample.measurement_type[])
LANGUAGE SQL
AS $$

	INSERT INTO sample.measurements(device_id, parameter_id, timestamp, value)
	SELECT * FROM UNNEST(p_measurements)
	ON CONFLICT (device_id, parameter_id, timestamp)
	DO UPDATE SET value = EXCLUDED.value;

$$;
```

We are done on the Postgres side! 

What's left is using Npsql for mapping the composite type and calling the Stored Procedure:

```csharp
using Npgsql;
using NUnit.Framework;
using System;
using System.Linq;
using System.Threading.Tasks;

namespace NpgsqlTypeMappings.Example
{
    /// <summary>
    /// Maps to the Postgres "measurement_type" type.
    /// </summary>
    public class Measurement
    {
        public int DeviceId { get; set; }

        public int ParameterId { get; set; }

        public DateTime Timestamp { get; set; }

        public double Value { get; set; }
    }

    public class Tests
    {
        private static readonly string ConnectionString = @"Host=localhost;Port=5432;Database=sampledb;Pooling=false;User Id=philipp;Password=test_pwd;";

        [Test]
        public async Task BulkInsertMeasurements()
        {
            var startDate = new DateTime(2013, 1, 1, 0, 0, 0, DateTimeKind.Utc);

            var measurements = Enumerable.Range(0, 1_000_000) // We start with 1_000,000 Measurements ...
                // ... transform them into fake measurements ...
                .Select(idx => new Measurement
                {
                    DeviceId = 1,
                    ParameterId = 1,
                    Timestamp = startDate.AddSeconds(idx),
                    Value = idx
                })
                // ... and finally evaluate them:
                .ToArray();

            // Create the Parameter:
            var p_measurements = new NpgsqlParameter
            {
                ParameterName = "p_measurements",
                DataTypeName = "sample.measurement_type[]",
                Value = measurements
            };

            // Configure the Mappings:
            NpgsqlConnection.GlobalTypeMapper.MapComposite<Measurement>("sample.measurement_type");

            using (var connection = new NpgsqlConnection(ConnectionString))
            {
                await connection.OpenAsync();

                // Execute the Insert or Update Function:
                using(var cmd = new NpgsqlCommand("CALL sample.insert_or_update_measurements(@p_measurements)", connection))
                {
                    cmd.Parameters.Add(p_measurements);

                    await cmd.ExecuteNonQueryAsync();
                }
            }
        }
    }
}
```

## Conclusion ##

So how well does it perform? 

Bulk inserting and updating  ``1,000,000`` measurements takes something around ``20`` seconds on my machine. It's well within the range of what I 
expected. According to [this article] (that's all research I did) one million inserts in a single transaction takes something around 81 seconds... so 
I think this method does fairly well.

Do you know a better way to do bulk updates with PostgreSQL, that doesn't include staging tables?

Let's discuss it in the GitHub Gist over at:

* [https://gist.github.com/bytefish/dbd2da81267990e9326044661be1c480](https://gist.github.com/bytefish/dbd2da81267990e9326044661be1c480)

[this article]: https://www.cybertec-postgresql.com/en/postgresql-bulk-loading-huge-amounts-of-data/