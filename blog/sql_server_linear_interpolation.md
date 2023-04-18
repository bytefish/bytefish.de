title: Linear Interpolation with Microsoft SQL Server 2022
date: 2023-04-17 13:50
tags: sql, sqlserver
category: sql
slug: sql_server_linear_interpolation
author: Philipp Wagner
summary: This article shows how to perform a Linear Interpolation with SQL Server 2022.

Microsoft SQL Server 2022 comes with new features to work with Timeseries data, such 
as `GENERATE_SERIES`, `FIRST_VALUE`, `LAST_VALUE` or `DATE_BUCKET`. So I thought I am 
giving it a try and see how to perform a Linear Interpolation of Time series data.

You can find everything about Microsoft SQL Server 2022 time series features here:

* [https://cloudblogs.microsoft.com/sqlserver/2023/01/12/working-with-time-series-data-in-sql-server-2022-and-azure-sql/](https://cloudblogs.microsoft.com/sqlserver/2023/01/12/working-with-time-series-data-in-sql-server-2022-and-azure-sql/)

## Table of contents ##

[TOC]

## What we are going to build ##

Imagine we are responsible for a Warehouse and need to continuously monitor its temperatures, so 
our precious food isn't spoiled. Sometimes the measurements are missing, and we need to interpolate 
it, so our consumers doesn't have gaps in their data.


## Linear Interpoation with T-SQL ##

We start by creating the `Warehouse` schema:

```sql
CREATE SCHEMA [Warehouse]
GO
```

And then we are going to create a table, that's going to hold the measurements:

```sql 
CREATE TABLE [Warehouse].[ColdRoomTemperatures] (
    [ColdRoomTemperatureID] BIGINT                                      IDENTITY (1, 1) NOT NULL,
    [ColdRoomSensorNumber]  INT                                         NOT NULL,
    [RecordedWhen]          DATETIME2 (7)                               NOT NULL,
    [Temperature]           DECIMAL (10, 2)                             NOT NULL
    CONSTRAINT [PK_Warehouse_ColdRoomTemperatures] PRIMARY KEY NONCLUSTERED ([ColdRoomTemperatureID] ASC),
    INDEX [IX_Warehouse_ColdRoomTemperatures_ColdRoomSensorNumber] NONCLUSTERED ([ColdRoomSensorNumber]),
)
GO
```

We then insert some temperatures for a sensor `1` and `2`, with gaps in the data:

```sql
DELETE FROM [Warehouse].[ColdRoomTemperatures];

INSERT INTO [Warehouse].[ColdRoomTemperatures]([ColdRoomSensorNumber], [RecordedWhen], [Temperature])
VALUES
	  (1, '2023-04-14 19:00', 3)
	, (1, '2023-04-14 19:01', 2)
	, (1, '2023-04-14 19:02', 1)
	, (1, '2023-04-14 19:04', 4)
	, (1, '2023-04-14 19:05', 5)
	, (1, '2023-04-14 19:06', 9)
	, (1, '2023-04-14 19:07', 8)
	, (1, '2023-04-14 19:09', 1)
	, (1, '2023-04-14 19:10', 3)
	, (1, '2023-04-14 19:12', 5)
	, (1, '2023-04-14 19:13', 1)
	, (2, '2023-04-14 19:00', 10)
	, (2, '2023-04-14 19:01', -3)
	, (2, '2023-04-14 19:02', -4)
	, (2, '2023-04-14 19:04', -5)
	, (2, '2023-04-14 19:05', 1)
	, (2, '2023-04-14 19:06', 2)
	, (2, '2023-04-14 19:07', 3)
	, (2, '2023-04-14 19:09', 4)
	, (2, '2023-04-14 19:10', 5)
	, (2, '2023-04-14 19:12', 6)
	, (2, '2023-04-14 19:13', 7);
GO
```

And then we can use `GENERATE_SERIES` to create the expected timestamps (`[Time]`) and by using the 
`DATE_BUCKET` function, we can assign each measurement into a time bucket (`[BoundedSeries]`). By 
using the `FIRST_VALUE` and `LAST_VALUE` functions, we can find the Previous and Next Timestamps 
and temperatures (`[InterpolationTable]`).

In the final `SELECT` we apply a Linear Interpolation for timestamps without a Temperature. 

```sql
WITH [Time] AS (
	SELECT 
		DATEADD(minute, [s].value, '2023-04-14 19:00') AS [RecordedWhen]
	FROM 
		GENERATE_SERIES(0, DATEDIFF(minute, '2023-04-14 19:00', '2023-04-14 19:15')) AS [s]
),
[ColdRoomSensorNumbers] AS (
	SELECT DISTINCT 
		[ColdRoomSensorNumber]
	FROM 
		[Warehouse].[ColdRoomTemperatures]
),
[DenseSeries] AS (
	SELECT DISTINCT 
		  [ColdRoomSensorNumbers].[ColdRoomSensorNumber]
		, [Time].[RecordedWhen]
	FROM [ColdRoomSensorNumbers]
		CROSS JOIN [Time]
),
[BoundedSeries] AS (
	SELECT 
		 [ColdRoomSensorNumber]
		, DATE_BUCKET(MINUTE, 1, [RecordedWhen]) AS [RecordedWhen]
		, AVG([Temperature]) AS [Temperature]
	FROM 
		[Warehouse].[ColdRoomTemperatures]
	GROUP BY 
		[ColdRoomSensorNumber], DATE_BUCKET(MINUTE, 1, [RecordedWhen])
),
[FilledSeries] AS (
	SELECT 
		[DenseSeries].[ColdRoomSensorNumber]
		, [DenseSeries].[RecordedWhen] AS [ExpectedRecordedWhen]
		, [BoundedSeries].[RecordedWhen] AS [ActualRecordedWhen]
		, [BoundedSeries].[Temperature]
		, CASE WHEN [BoundedSeries].[Temperature] IS NOT NULL THEN N'Measured' ELSE N'Interpolated' END AS [Type]
	FROM [DenseSeries]
		LEFT JOIN [BoundedSeries] ON ([DenseSeries].[ColdRoomSensorNumber] = [BoundedSeries].[ColdRoomSensorNumber] AND [DenseSeries].[RecordedWhen] = [BoundedSeries].[RecordedWhen])
),
[InterpolationTable] AS (
	SELECT 
		[ColdRoomSensorNumber]
		, [ExpectedRecordedWhen]
		, [ActualRecordedWhen]
		, [Temperature]	
		, LAST_VALUE([ActualRecordedWhen]) IGNORE NULLS OVER (PARTITION BY [ColdRoomSensorNumber] ORDER BY [ExpectedRecordedWhen]) AS [PreviousRecordedWhen]
		, LAST_VALUE([Temperature]) IGNORE NULLS OVER (PARTITION BY [ColdRoomSensorNumber] ORDER BY [ExpectedRecordedWhen]) AS [PreviousTemperature]
		, FIRST_VALUE([ActualRecordedWhen]) IGNORE NULLS OVER (PARTITION BY [ColdRoomSensorNumber] ORDER BY [ExpectedRecordedWhen] ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS [NextRecordedWhen]
		, FIRST_VALUE([Temperature]) IGNORE NULLS OVER (PARTITION BY [ColdRoomSensorNumber] ORDER BY [ExpectedRecordedWhen] ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) AS [NextTemperature]
		, [Type]
	FROM [FilledSeries]
)
SELECT 
	[ColdRoomSensorNumber]
	, [ExpectedRecordedWhen]
	, COALESCE([Temperature],
		CASE 
			WHEN [PreviousTemperature] IS NULL THEN [NextTemperature]
			WHEN [NextTemperature] IS NULL THEN [PreviousTemperature]
			ELSE
			([PreviousTemperature] + 
				([NextTemperature] - [PreviousTemperature]) / DATEDIFF(second, [PreviousRecordedWhen], [NextRecordedWhen]) * DATEDIFF(second, [PreviousRecordedWhen], [ExpectedRecordedWhen]))
		END)
	, [Type]
FROM [InterpolationTable]
order by [ColdRoomSensorNumber], [ExpectedRecordedWhen]
```

We can see, that it interpolates the values just fine:

| Sensor | ExpectedRecordedWhen    | Temperature | Type           |
|--------|-------------------------|-------------|----------------|
|1       | 2023-04-14 19:00	       | 3.000000	  | Measured      |
|1	     | 2023-04-14 19:01	       | 2.000000	  | Measured      |
|1	     | 2023-04-14 19:02	       | 1.000000	  | Measured      |
|1	     | 2023-04-14 19:03	       | 2.500000	  | Interpolated  |
|1	     | 2023-04-14 19:04	       | 4.000000	  | Measured      |
|1	     | 2023-04-14 19:05	       | 5.000000	  | Measured      |
|1	     | 2023-04-14 19:06	       | 9.000000	  | Measured      |
|1	     | 2023-04-14 19:07	       | 8.000000	  | Measured      |
|1	     | 2023-04-14 19:08	       | 4.500020	  | Interpolated  |
|1	     | 2023-04-14 19:09        | 1.000000	  | Measured      |
|1	     | 2023-04-14 19:10        | 3.000000	  | Measured      |
|1	     | 2023-04-14 19:11        | 3.999960	  | Interpolated  |
|1	     | 2023-04-14 19:12        | 5.000000	  | Measured      |
|1	     | 2023-04-14 19:13        | 1.000000	  | Measured      |
|1	     | 2023-04-14 19:14        | 1.000000	  | Interpolated  |
|1	     | 2023-04-14 19:15        | 1.000000	  | Interpolated  |
|2	     | 2023-04-14 19:00        | 10.000000	  | Measured      |
|2	     | ...	                   | ...         | ...            |

## Conclusion ##

And that's it! 

I think `GENERATE_SERIES`, `DATE_BUCKET`, `FIRST_VALUE` and `LAST_VALUE` are a great addition 
to Microsoft SQL Server, and it makes it much easier (and probably more efficient) to work with 
timeseries data.

This article didn't take a look at the Query Plans, and I am pretty sure there are much more 
concise ways for a Linear Interpolation in T-SQL. Feel free to comment and make a Pull Request 
to this article, so it can be improved!