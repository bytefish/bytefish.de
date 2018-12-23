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

How well do databases work when we actually throw realistic data at them? 

What knobs have to be turned to make the databases scale? 

How far does **a single machine** take us?

## A Single Machine? ##

A *single machine*? Really? See. Scaling is hard.

As soon as you start distributing and sharding your database, you will probably learn everything about the 
[Fallacies of distributed computing] and experience some of the tough problems with Eventual Consistency as 
highlighted in some of [Jepsen Analyses].

In the past years I have accepted how much a single person can learn and how much a single person can do. And 
by now I think software systems need to be designed in a way, that a Junior Software Engineer can get up to 
speed quick. Without 8 months of training. Without falling into frustration and depression.

So what do big players like Google say about Eventual Consistency[ref]J. Corbett, J. Dean, M. Epstein, A. Fikes, C. Frost, JJ Furman, S. Ghemawat, A. Gubarev, C. Heiser, P. Hochschild, W. Hsieh, S. Kanthak, E. Kogan, H. Li, A. Lloyd, S. Melnik, D. Mwaura, D. Nagle, S. Quinlan, R. Rao, L. Rolig, Y. Saito, M. Szymaniak, C. Taylor, R. Wang, and D. Woodford. *Spanner: Google’s Globally-Distributed Database.* In Proceedings of OSDI '12: Tenth Symposium on Operating System Design and Implementation, Hollywood, CA, October, 2012[/ref]:

> We also have a lot of experience with eventual consistency systems at Google. In all such systems, we find developers 
> spend a significant fraction of their time building extremely complex and error-prone mechanisms to cope with eventual 
> consistency and handle data that may be out of date. We think this is an unacceptable burden to place on developers 
> and that consistency problems should be solved at the database level.

For me this means: Do yourself and others a favor and always start your projects with a RDBMS. A dead simple Layered 
Architecture. You have SQL queries, you have ER-Diagrams explaining the domain you work in (a little). ACID guarantees 
are gold: You have a little more safety, that your data is actually written when a database tells you so.

## One Size fits all? ##

Of course Relational Databases are not a silver bullet and not optimized for absolutely everything. These days we got 
[Graph Databases], [Document-oriented Databases], [Time series databases]... all highly specialized for different 
use-cases and they all have their place.




## The DWD Open Data Dataset ##

The [DWD Open Data] portal of the [Deutscher Wetterdienst (DWD)] gives access to the historical weather data in Germany. I decided 
to analyze the available historical Air Temperature data for Germany given in a 10 minute resolution ([FTP Link]). If you want to 
recreate the example, you can find the list of file in the GitHub repository at: [GermanWeatherDataExample/Resources/files.md].

The DWD dataset is given as CSV files and has a size of approximately 25.5 GB.

[works for Stackoverflow]: https://nickcraver.com/blog/2016/02/17/stack-overflow-the-architecture-2016-edition/
[The world’s most valuable resource is no longer oil, but data]: https://www.economist.com/leaders/2017/05/06/the-worlds-most-valuable-resource-is-no-longer-oil-but-data
[Time series Databases]: https://en.wikipedia.org/wiki/Time_series_database
[Document-oriented Databases]: https://en.wikipedia.org/wiki/Document-oriented_database
[Relational Databases]: https://en.wikipedia.org/wiki/Relational_database
[Graph Databases]: https://en.wikipedia.org/wiki/Graph_database
[FTP Link]: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/
[TimescaleDB]: https://www.timescale.com/
[Elasticsearch]: https://www.elastic.co/
[SQL Server]: https://www.microsoft.com/de-de/sql-server/sql-server-2017
[InfluxDB]: https://www.influxdata.com/
[DWD Open Data]: https://opendata.dwd.de/
[E-Government Act - EgovG]: http://www.gesetze-im-internet.de/englisch_egovg/index.html
[Deutscher Wetterdienst (DWD)]: https://www.dwd.de
[GermanWeatherDataExample/Resources/files.md]: https://github.com/bytefish/GermanWeatherDataExample/blob/master/GermanWeatherData/Resources/files.md
[Jepsen Analyses]: https://jepsen.io/
[Fallacies of distributed computing]: https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing


## Resources ##
