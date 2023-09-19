title: Analyzing Weather Data with .NET and SQL Server 2022+
date: 2023-08-07 12:53
tags: aspnetcore, csharp, blazor, odata
category: blazor
slug: blazor_fluentui_and_odata
author: Philipp Wagner
summary: This article shows how to use Fluent UI Blazor and OData to add Filtering to DataGrid. 

[Link DWD]: https://social.bund.de/@DeutscherWetterdienst/111051263708804194
[Link SZ]: https://www.sueddeutsche.de/panorama/wetter-essen-sieben-hitzetage-am-stueck-september-rekord-an-nrw-stationen-dpa.urn-newsml-dpa-com-20090101-230911-99-154458

I have been on Mastodon for quite a while and am following various official accounts, 
such as the Deutsche Wetterdienst (DWD), which is the Weather Service for Germany. They 
have recently shared an interesting quote, which reads:

> Kein Grund zum Jubeln in Zeiten der #Klimakrise: "Sieben Hitzetage am Stück: 
> September-Rekord an NRW-Stationen" bestätigt der DWD der Süddeutschen 
> Zeitung. ([[Link DWD]])

This literally means September was a record month in Germany, with 7 consecutive days 
of severe heat. In the referenced article at Süddeutsche Zeitung (SZ) we can find the 
criteria applied:

> Die vergangenen heißen Septembertage haben an einigen Orten in Nordrhein-Westfalen laut 
> dem Deutschen Wetterdienst für einen Hitzerekord in dem Monat gesorgt. An den Stationen 
> Bochum, Weilerswist-Lommersum und Tönisvorst sei mit dem Montag der siebte heiße Tag mit 
> mehr als 30 Grad hintereinander erreicht, sagte Thomas Kesseler-Lauterkorn, Meteorologe 
> beim Deutschen Wetterdienst (DWD). ([Link SZ])

The Deutsche Wetterdienst (DWD) shares the measured temperatures with a 10 minute accuracy, 
which we'll use to verify the results. You can find the historical data at:

* [https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/)

I am sharing it, because I think it applies to a lot of data you are going to work with, 
and it shows how to write an efficient import pipeline with a minimal set of .NET 
dependencies.

## What we are going to build ##

We are going to build an application for downloading and efficiently inserting the DWD weather data 
into an SQL Server database. This data is used to run queries and trying to find the September record 
streak.

All code can be found in the Git Repository at:

* []()

### On Efficiently Importing Data to SQL Server ###

[Microsoft Learn: BULK INSERT (Transact-SQL)]: https://learn.microsoft.com/de-de/sql/t-sql/statements/bulk-insert-transact-sql?view=sql-server-ver16
[SqlBulkCopy]: https://learn.microsoft.com/en-us/dotnet/framework/data/adonet/sql/bulk-copy-operations-in-sql-server

A golden rule when working with any kind of data is to *never trust the incoming data*. There's 
missing data, malformed data, duplicate measurements, ... to name a few issues. Let's summarize 
my personal experience.

The T-SQL `BULK INSERT` statement can directly import a CSV file, see [Microsoft Learn: BULK INSERT (Transact-SQL)] 
for more information. It sounds very, very appealing first, but what if incoming text data contains formats the SQL 
Server doesn't understand? It falls flat.

Spoiler alarm: The DWD data is no exception.

.NET also comes with the `SqlBulkCopy` class to write managed code solutions that provide bulk insert 
solutions. You basically point `SqlBulkCopy` at a SQL Server table in your database and then insert 
a ADO.NET `DataTable`, `DataRow[]` or an IDataReader, which it will then stream into SQL Server. 

Now `SqlBulkCopy` sounds like a good idea, right? But there's a catch. What happens, if there's duplicate 
data in your CSV data? An insert is going to trigger a key constraint exception, and there are no extension 
points in `SqlBulkCopy` to handle conflicts.

Spoiler alarm: The DWD data is no exception. 

What's most flexible, very efficient and easy to implement is to use a Stored Procedure, 
that takes a Table-Valued Parameter as its input variable. In the Stored Procedure we can use 
a `MERGE` statement to insert or update the data.

A SQL Server `MERGE` isn't atomic and we are multi-threaded, so we also add a `SERIALIZABLE` hint to it.

## Importing the DWD Measurements ##

### Understanding the Database Schema ##

We basically need only two tables to hold the Stations and the Measurements. 

We start by defining the `[dbo].[Station]` table, which is going to hold 
all information about the weather station, such as the station name, measurement 
period or its exact location.

```sql
IF NOT EXISTS (SELECT * FROM sys.objects 
    WHERE object_id = OBJECT_ID(N'[dbo].[Station]') AND type in (N'U'))
        
BEGIN

    CREATE TABLE [dbo].[Station](
        [StationID]         [nchar](5) NOT NULL,
        [DatumVon]          [datetime2](7) NULL,
        [DatumBis]          [datetime2](7) NULL,
        [Stationshoehe]     [real] NULL,
        [GeoBreite]         [real] NULL,
        [GeoLaenge]         [real] NULL,
        [Stationsname]      [nvarchar](255) NULL,
        [Bundesland]        [nvarchar](255) NULL,
        CONSTRAINT [PK_Station] PRIMARY KEY CLUSTERED 
        (
            [StationID] ASC
        )
    ) ON [PRIMARY]
   
END
```

The weather measurements are going into the table `[dbo].[Messwert]` and holds 
all measurements given in the zipped CSV files:

```sql
IF NOT EXISTS (SELECT * FROM sys.objects 
    WHERE object_id = OBJECT_ID(N'[dbo].[Messwert]') AND type in (N'U'))

BEGIN

    CREATE TABLE [dbo].[Messwert](
        [StationID]     [nchar](5) NOT NULL,
        [MessDatum]     [datetime2](7) NOT NULL,
        [QN]            [int] NULL,
        [PP_10]         [real] NULL,
        [TT_10]         [real] NULL,
        [TM5_10]        [real] NULL,
        [RF_10]         [real] NULL,
        [TD_10]         [real] NULL
    ) ON [PRIMARY]

END
```

We then define the Table Types, that will be the input parameter for 
the Stored Procedures to come. The `[dbo].[udt_StationType]` is 
basically a one to one mapping to the `[dbo].[Station]` table.

```sql
IF NOT EXISTS (SELECT * FROM   [sys].[table_types]
    WHERE  user_type_id = Type_id(N'[dbo].[udt_StationType]'))
     
BEGIN

    CREATE TYPE [dbo].[udt_StationType] AS TABLE (
        [StationID]         [nchar](5),
        [DatumVon]          [datetime2](7),
        [DatumBis]          [datetime2](7),
        [Stationshoehe]     [real],
        [GeoBreite]         [real],
        [GeoLaenge]         [real],
        [Stationsname]      [nvarchar](255),
        [Bundesland]        [nvarchar](255)
    );

END
```

We'll define the `[dbo].[udt_MesswertType]` accordingly, which represents the 
weather measurements. Again it's a one to one mapping to the `[dbo].[Messwert]` 
table.

```sql
IF NOT EXISTS (SELECT * FROM   [sys].[table_types]
    WHERE  user_type_id = Type_id(N'[dbo].[udt_MesswertType]'))
         
BEGIN

    CREATE TYPE [dbo].[udt_MesswertType] AS TABLE (
        [StationID]     [nchar](5),
        [MessDatum]     [datetime2](7),
        [QN]            [int],
        [PP_10]         [real],
        [TT_10]         [real],
        [TM5_10]        [real],
        [RF_10]         [real],
        [TD_10]         [real]
    );

EN
```

What's left is to define the Stored Procedures for bulk importing the data. 

We'll start with the Stations and create a Stored Procedure named `[dbo].[usp_InsertOrUpdateStation]`. 

```sql
 CREATE OR ALTER PROCEDURE [dbo].[usp_InsertOrUpdateStation]
   @Entities [dbo].[udt_StationType] ReadOnly
 AS
 BEGIN
    
     SET NOCOUNT ON;

     MERGE [dbo].[Station] WITH (SERIALIZABLE) AS TARGET USING @Entities AS SOURCE ON (TARGET.StationID = SOURCE.StationID) 
     WHEN MATCHED THEN
         UPDATE SET TARGET.StationID = SOURCE.StationID
             , TARGET.DatumVon = SOURCE.DatumVon
             , TARGET.DatumBis = SOURCE.DatumBis
             , TARGET.Stationshoehe = SOURCE.Stationshoehe
             , TARGET.GeoBreite = SOURCE.GeoBreite
             , TARGET.GeoLaenge = SOURCE.GeoLaenge
             , TARGET.Stationsname = SOURCE.Stationsname
             , TARGET.Bundesland = SOURCE.Bundesland
     WHEN NOT MATCHED BY TARGET THEN
         INSERT (StationID, DatumVon, DatumBis, Stationshoehe, GeoBreite, GeoLaenge, Stationsname, Bundesland)
         VALUES (SOURCE.StationID, SOURCE.DatumVon, SOURCE.DatumBis, SOURCE.Stationshoehe, SOURCE.GeoBreite, SOURCE.GeoLaenge, SOURCE.Stationsname, SOURCE.Bundesland);

 END
```

It's a common misconception, that a `MERGE` is an atomic operation. It's not. So there's a 
chance, that you'll run into constraint violations when running `MERGE` statements 
concurrently. We fix it by adding a `SERIALIZABLE` hint to the target table.

Finally we define the Stored Procedure `[dbo].[usp_InsertOrUpdateMesswert]` to insert the 
weather data measurements using a `MERGE` statement.

```sql
CREATE OR ALTER PROCEDURE [dbo].[usp_InsertOrUpdateMesswert]
  @Entities [dbo].[udt_MesswertType] ReadOnly
AS
BEGIN
    
    SET NOCOUNT ON;

    MERGE [dbo].[Messwert] WITH (SERIALIZABLE) AS TARGET USING @Entities AS SOURCE ON (TARGET.StationID = SOURCE.StationID AND TARGET.MessDatum = SOURCE.MessDatum) 
    WHEN MATCHED THEN
        UPDATE SET TARGET.StationID = SOURCE.StationID
            , TARGET.MessDatum = SOURCE.MessDatum
            , TARGET.QN = SOURCE.QN
            , TARGET.PP_10 = SOURCE.PP_10
            , TARGET.TT_10 = SOURCE.TT_10
            , TARGET.TM5_10 = SOURCE.TM5_10
            , TARGET.RF_10 = SOURCE.RF_10
            , TARGET.TD_10 = SOURCE.TD_10
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (StationID, MessDatum, QN, PP_10, TT_10, TM5_10, RF_10, TD_10)
        VALUES (SOURCE.StationID, SOURCE.MessDatum, SOURCE.QN, SOURCE.PP_10, SOURCE.TT_10, SOURCE.TM5_10, SOURCE.RF_10, SOURCE.TD_10);

END
```

It's useful to create some indexes on the `[dbo].[Messwert]` table for more efficient queries and 
compress the data. We start by defining a Clustered Column Store Index `CCI_Messwert_StationID_MessDatum` 
on `[dbo].[Messwert](StationID, MessDatum)`.

```sql
IF EXISTS (SELECT name FROM sys.indexes 
    WHERE name = N'CCI_Messwert_StationID_MessDatum' AND object_id = OBJECT_ID(N'dbo.Messwert'))  
BEGIN
    DROP INDEX CCI_Messwert_StationID_MessDatum ON [dbo].[Messwert];  
END

CREATE CLUSTERED COLUMNSTORE INDEX [CCI_Messwert_StationID_MessDatum] ON [dbo].[Messwert](StationID, MessDatum) WITH (DROP_EXISTING = OFF)
```

Maybe it's also useful to have a unique index on `[dbo].[Messwert]([StationID], [MessDatum])` to be on 
the safe side for inserts and it shouldn't hurt either.

```sql
IF EXISTS (SELECT name FROM sys.indexes 
    WHERE name = N'UX_Messwert_StationID_MessDatum' AND object_id = OBJECT_ID(N'dbo.Messwert'))  
BEGIN
    DROP INDEX [UX_Messwert_StationID_MessDatum] ON [dbo].[Messwert];  
END

CREATE UNIQUE INDEX [UX_Messwert_StationID_MessDatum] ON [dbo].[Messwert]([StationID], [MessDatum])
```

And that's it for the database.

### Understanding the File Formats ###

Before we begin the implementation, we'll take a look at the files for stations and measurements. 

The stations are given in a file `zehn_min_tu_Beschreibung_Stationen.txt` in the data folder, the first few lines look like this:

```
Stations_id von_datum bis_datum Stationshoehe geoBreite geoLaenge Stationsname Bundesland
----------- --------- --------- ------------- --------- --------- ----------------------------------------- ----------
00003 19930429 20110331            202     50.7827    6.0941 Aachen                                   Nordrhein-Westfalen
00044 20070209 20230918             44     52.9336    8.2370 Großenkneten                             Niedersachsen
...
```

The first two lines are just information and need to be skipped, when reading the data. We can see, that the 
properties are given in a fixed-width format. So how could we extract these fields? Regular Expressions with 
named captures seems like a nice way for me.

After counting the width for each column, I came up with this simple Regular Expression:

```
(?<stations_id>.{5})\\s(?<von_datum>.{8})\\s(?<bis_datum>.{8})\\s(?<stationshoehe>.{14})\\s(?<geo_breite>.{11})\\s(?<geo_laenge>.{9})\\s(?<stationsname>.{40})\\s(?<bundesland>.+)$
```

Cool!

The measurements are given in ZIP files. These ZIP files contain a single `txt` file with the 
measurements. The first few lines in the `txt` files look like this:

```
STATIONS_ID;MESS_DATUM;  QN;PP_10;TT_10;TM5_10;RF_10;TD_10;eor
          3;199912312300;    1;  997.3;   4.1;   3.6;  87.0;   2.1;eor
          3;199912312310;    1;  997.3;   4.1;   3.6;  86.0;   2.0;eor
          3;199912312320;    1;  997.3;   4.2;   3.7;  87.0;   2.2;eor
```

So there are a few things to note: 

* The field delimiter character is a semi-colon (`;`)
* `STATIONS_ID` lacks the left-padded zeros.
* `MESS_DATUM` has the date format `yyyyMMddHHmm`.
* `PP_10`, `TT_10`, TM5_10`, `RF_10`, `TD_10` are given in an invariant culture.
* `PP_10`, `TT_10`, TM5_10`, `RF_10`, `TD_10` represent missing values with `-999`.

And we can see in the files, that a simple `string.Split` will do. We don't need to take dependencies on CSV parsers.

### Understanding the .NET dependencies ###

`System.Data.SqlClient` 

First of all we need to download all historical data from the DWD FTP Server. .NET Framework 
came with an `FtpWebRequest` for working with an FTP Server, but these classes have been 
deprecated in .NET 6 and shouldn't be used anymore:

* []()

There are great community projects, such as `FluentFTP`, which is used in the application.

