title: PostgreSQL Bulk Insert with C#
date: 2015-10-24 10:38
tags: csharp, postgresql, bulk insert, sql
category: sql
slug: postgresql_bulk_insert
author: Philipp Wagner
summary: This article shows how to bulk insert data into PostgreSQL from .NET.

[Npgsql]: https://github.com/npgsql
[PostgreSQL]: http://www.postgresql.org
[COPY command]: http://www.postgresql.org/docs/current/static/sql-copy.html
[MIT License]: https://opensource.org/licenses/MIT
[PostgreSQLCopyHelper]: https://codeberg.org/bytefish/PostgreSQLCopyHelper
[Npgsql documentation]: http://www.npgsql.org/doc/copy.html

In my last post I have introduced [PostgreSQLCopyHelper], which is a small library to wrap the [Npgsql] 
implementation of the PostgreSQL [Copy command] behind a nice fluent API.

From the good [Npgsql documentation]:

> PostgreSQL has a feature allowing efficient bulk import or export of data to and from a table. This is 
> usually a much faster way of getting data in and out of a table than using INSERT and SELECT. See 
> documentation for the [COPY command] for more details.

[PostgreSQLCopyHelper] is released with under terms of the [MIT License]:

* [https://codeberg.org/bytefish/PostgreSQLCopyHelper](https://codeberg.org/bytefish/PostgreSQLCopyHelper)

It can be installed with [NuGet](https://www.nuget.org/) with the following command in the 
[Package Manager Console](http://docs.nuget.org/consume/package-manager-console):

```
PM> Install-Package PostgreSQLCopyHelper
```

## Basic Usage ##

Imagine we have the following table we want to copy data to:

```sql
CREATE TABLE sample.unit_test
(
    col_smallint smallint,
    col_integer integer,
    col_money money,
    col_bigint bigint,
    col_timestamp timestamp,
    col_real real,
    col_double double precision,
    col_bytea bytea,
    col_uuid uuid,
    col_numeric numeric,
    col_inet inet,
    col_macaddr macaddr,
    col_date date,
    col_interval interval
);
```

The corresponding domain model in our application could look like this:

```csharp
private class TestEntity
{
    public Int16? SmallInt { get; set; }
    public Int32? Integer { get; set; }
    public Int64? BigInt { get; set; }
    public Decimal? Money { get; set; }
    public DateTime? Timestamp { get; set; }
    public Decimal? Numeric { get; set; }
    public Single? Real { get; set; }
    public Double? DoublePrecision { get; set; }
    public byte[] ByteArray { get; set; }
    public Guid? UUID { get; set; }
    public IPAddress IpAddress { get; set; }
    public PhysicalAddress MacAddress { get; set; }
    public DateTime? Date { get; set; }
    public TimeSpan? TimeSpan { get; set; }
}
```

The [PostgreSQLCopyHelper] now defines the mapping between domain model and the database table:

```csharp
var copyHelper = new PostgreSQLCopyHelper<TestEntity>()
	.WithTableName("sample", "unit_test")
	.MapSmallInt("col_smallint", x => x.SmallInt)
	.MapInteger("col_integer", x => x.Integer)
	.MapMoney("col_money", x => x.Money)
	.MapBigInt("col_bigint", x => x.BigInt)
	.MapTimeStamp("col_timestamp", x => x.Timestamp)
	.MapReal("col_real", x => x.Real)
	.MapDouble("col_double", x => x.DoublePrecision)
	.MapByteArray("col_bytea", x => x.ByteArray)
	.MapUUID("col_uuid", x => x.UUID)
	.MapInetAddress("col_inet", x => x.IpAddress)
	.MapMacAddress("col_macaddr", x => x.MacAddress)
	.MapDate("col_date", x => x.Date)
	.MapInterval("col_interval", x => x.TimeSpan)
	.MapNumeric("col_numeric", x => x.Numeric);
```

And then we can use it to efficiently store the data:

```csharp
private void WriteToDatabase(PostgreSQLCopyHelper<TestEntity> copyHelper, IEnumerable<TestEntity> entities)
{
    using (var connection = new NpgsqlConnection("Server=127.0.0.1;Port=5432;Database=sampledb;User Id=philipp;Password=test_pwd;"))
    {
        connection.Open();

        copyHelper.SaveAll(connection, entities);
    }
}
```