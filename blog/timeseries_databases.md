title: Benchmarking Timeseries Databases
date: 2018-12-23 09:30
tags: timescaledb, sqlserver, elasticsearch, database, sql
category: databases
slug: timeseries_databases
author: Philipp Wagner
summary: This article evaluates Timeseries Databases on a realistic dataset.

These days it's all about Artificial Intelligence (AI), Big Data, Business Intelligence, Business Analytics, 
... "[The world’s most valuable resource is no longer oil, but data]" they say, so why not store everything 
first and make sense of it sometime later?

Well. I often had to deal with large amounts time series data in my career. And I have never been able to give 
qualified answers or recommendations for one database or another. Simply because I don't know how the available 
databases behave under realistic loads.

So how well do databases work when we actually throw realistic data at them? What knobs have to be turned to 
make the databases scale? How far does **a single machine** take us?

In this project I want to benchmark [TimescaleDB], [Elasticsearch], [SQL Server] and [InfluxDB] on the 10 Minute 
Weather Data for Germany. All code to recreate the results can be found at:

* [https://github.com/bytefish/GermanWeatherDataExample](https://github.com/bytefish/GermanWeatherDataExample)

This post is the first in a series I am planning and it focuses on the write throughput of databases.

## The Dataset ##

The [DWD Open Data] portal of the [Deutscher Wetterdienst (DWD)] gives access to the historical weather data in Germany. I decided 
to analyze the available historical Air Temperature data for Germany given in a 10 minute resolution ([FTP Link]). If you want to 
recreate the example, you can find the list of file in the GitHub repository at: [GermanWeatherDataExample/Resources/files.md].

The DWD dataset is given as CSV files and has a size of approximately 25.5 GB.


[The world’s most valuable resource is no longer oil, but data]: https://www.economist.com/leaders/2017/05/06/the-worlds-most-valuable-resource-is-no-longer-oil-but-data
[FTP Link]: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/
[TimescaleDB]: https://www.timescale.com/
[Elasticsearch]: https://www.elastic.co/
[SQL Server]: https://www.microsoft.com/de-de/sql-server/sql-server-2017
[InfluxDB]: https://www.influxdata.com/
[DWD Open Data]: https://opendata.dwd.de/
[Deutscher Wetterdienst (DWD)]: https://www.dwd.de
[GermanWeatherDataExample/Resources/files.md]: https://github.com/bytefish/GermanWeatherDataExample/blob/master/GermanWeatherData/Resources/files.md
