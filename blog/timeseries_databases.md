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

## The Setup ##

* Windows 10
* Intel® Core™ i5-3450 CPU
* 16 GB RAM
* Samsung SSD 860 EVO ([Specifications](https://www.samsung.com/semiconductor/minisite/ssd/product/consumer/860evo/))

### Software ###



## InfluxDB ##

[InfluxDB] is a database written specifically for handling time series data.

The [influxdata] website writes on [InfluxDB]:

> InfluxDB is a high-performance data store written specifically for time series data. It allows for high throughput 
> ingest, compression and real-time querying of that same data. InfluxDB is written entirely in Go and it compiles 
> into a single binary with no external dependencies.

### Configuration ###

InfluxDB 1.7.1 with the default configuration was unable to import the entire dataset.  It consumes too much memory under 
load and could not write the batches anymore. After reading through documentation I am quite confident, that the default 
shard duration and retention policy has to be adjusted, so that the shards do not stay in memory forever:

* https://www.influxdata.com/blog/tldr-influxdb-tech-tips-march-16-2017/
* https://docs.influxdata.com/influxdb/v1.7/guides/hardware_sizing/

The default configuration of InfluxDB is optimized for realtime data with a short [retention duration] and a short [shard duration]. 
This makes InfluxDB chewing up the entire RAM, just because for the historic data too many shards are created and the cached data 
is never written to disk.

So I am now creating the database using ``DURATION`` set to infinite (``inf``) to keep measurements forever. The ``SHARD DURATION`` 
is set to 4 weeks for limiting the number of shards being created during the import. This can be done by running the following 
``CREATE DATABASE`` statement:

```
CREATE DATABASE "weather_data" WITH DURATION inf REPLICATION 1 SHARD DURATION 4w NAME "weather_data_policy"
```

In the ``influxdb.conf`` I am setting the ``cache-snapshot-write-cold-duration`` to 5 seconds for flushing the caches more agressively:

```
cache-snapshot-write-cold-duration = "5s"
```

[retention duration]: https://docs.influxdata.com/influxdb/v1.7/concepts/glossary/#duration
[shard duration]: https://docs.influxdata.com/influxdb/v1.7/concepts/glossary/#shard-duration

### Results ###

[InfluxDB] was able to import the entire dataset. The final database has 398,704,931 measurements and has a file size 
of 7.91 GB. The difference between the number of measurements for InfluxDB and TimescaleDB will be part of further 
investigation.

The import took 147 minutes, so InfluxDB was able to write 45,112 records per second.

## TimescaleDB ##

The [TimescaleDB] docs describe TimescaleDB as:

> [...] an open-source time-series database optimized for fast ingest and complex queries. It speaks "full SQL" and 
> is correspondingly easy to use like a traditional relational database, yet scales in ways previously reserved for NoSQL 
> databases.

### Results #1 ###

With the default configuration [TimescaleDB] was able to import the entire dataset. The final database has 406,241,469 measurements 
and has a file size of 37 GB. Nothing had been changed in the TimescaleDB configuration.

The import took 690.5 minutes, so TimescaleDB was able to write 9,804 records per second.

### Results #2 ###

The import with the default configuration was much too slow. So the first thing I did was to use [timescaledb-tune] to tune 
the ``postgresql.config`` to values optimized for the hardware:

```
#------------------------------------------------------------------------------
# RESOURCE USAGE (except WAL)
#------------------------------------------------------------------------------

# - Memory -

shared_buffers = 512MB
work_mem = 67254kB
maintenance_work_mem = 2034MB
dynamic_shared_memory_type = windows

# - Kernel Resource Usage -

shared_preload_libraries = 'timescaledb'

# - Asynchronous Behavior -

max_worker_processes = 4		# (change requires restart)
max_parallel_workers_per_gather = 2	# taken from max_parallel_workers
max_parallel_workers = 4		# maximum number of max_worker_processes that

#------------------------------------------------------------------------------
# WRITE AHEAD LOG
#------------------------------------------------------------------------------

# - Settings -

wal_level = hot_standby
wal_buffers = 16MB

# - Checkpoints -

max_wal_size = 8GB
min_wal_size = 4GB
checkpoint_completion_target = 0.9	

#------------------------------------------------------------------------------
# QUERY TUNING
#------------------------------------------------------------------------------

# - Planner Cost Constants -

random_page_cost = 1.1
effective_cache_size = 12206MB
```

But this didn't yield significant improvements.

### Results #3 ###

[Disk-write settings]: https://docs.timescale.com/v1.0/getting-started/configuring#disk-write

The TimescaleDB docs write on [Disk-write settings]:

> Disk-write settings
>
> In order to increase write throughput, there are multiple settings to adjust the behaviour that PostgreSQL uses to write 
> data to disk. We find the performance to be good with the default (safest) settings. If you want a bit of additional 
> performance, you can set synchronous_commit = 'off'(PostgreSQL docs). Please note that when disabling ``sychronous_commit`` 
> in this way, an operating system or database crash might result in some recent allegedly-committed transactions being 
> lost. We actively discourage changing the ``fsync`` setting.

So I decided to turn the ``synchronous_commit`` off by uncommenting the following line in the ``postgresql.config``:

``synchronous_commit = off``

With synchronous commits disabled the import took 247 minutes, so TimescaleDB was able to write 27,560 records per second.

## SQL Server 2017 ##

The Microsoft documents describe the [SQL Server] as:

> [...] a central part of the Microsoft data platform. SQL Server is an industry leader in operational database management systems (ODBMS).

The SQL Server is not a database specialized for Time series data. It provides [Columnstore indexes] for storing data in a column-based layout 
and recently added a Graph Database engine to support more specialized data ([read my post here](https://bytefish.de/blog/sql_server_2017_graph_database/)).

### Results ###

The SQL Server 2017 was able to import the entire dataset. The final database has 406,242,465 measurements and a file 
size of 12.6 GB. Nothing has been changed in the SQL Server configuration. More queries and performance analysis to follow!

The import took 81.25 minutes, so the SQL Server was able to write 83,059 records per second.

## Elasticsearch ##


There is a great article written by [Felix Barnsteiner](https://www.elastic.co/blog/author/felix-barnsteiner) on using Elasticsearch as a :

* https://www.elastic.co/blog/elasticsearch-as-a-time-series-data-store

### Results ###

Elasticsearch was able to import the entire dataset. The final database has 406,548,765 documents and has a file size 
of 52.9 GB. The difference in documents between TimescaleDB and Elasticsearch can be explained due to an accidental restart 
during the first file import, this will be adjusted in a later post.

The import took 718.9 minutes, so Elasticsearch was able to write 9,425 records per second.

### Configuration ###

The default configuration of Elasticsearch 6.5.1 is not optimized for bulk loading large amounts of data into the 
database. To improve the import for the initial load, the first I did was to disable indexing and replication by 
creating the index with 0 Replicas (since it is all running local anyway) and disabling the Index Refresh Interval, 
so the index isn't built on inserts.

All the performance hints are taken from the Elasticsearch documentation at:

* https://www.elastic.co/guide/en/elasticsearch/reference/master/tune-for-indexing-speed.html

In Elasticsearch 6.5.1 these settings have to be configured as an index template apparently, instead of editing the 
``config/elasticsearch.yml``. Anyways it can be easily be achieved with the NEST, the official .NET Connector for 
Elasticsearch:

```csharp
// We are creating the Index with special indexing options for initial load, 
// as suggested in the Elasticsearch documentation at [1].
//
// We disable the performance-heavy indexing during the initial load and also 
// disable any replicas of the data. This comes at a price of not being able 
// to query the data in realtime, but it will enhance the import speed.
//
// After the initial load I will revert to the standard settings for the Index
// and set the default values for Shards and Refresh Interval.
//
// [1]: https://www.elastic.co/guide/en/elasticsearch/reference/master/tune-for-indexing-speed.html
//
client.CreateIndex(settings => settings
    .NumberOfReplicas(0)
    .RefreshInterval(-1));
```

Additionally I made sure I am running a 64-bit JVM, so the heap size can scale to more than 2 GB for fair comparisms 
with systems like InfluxDB, that aggressively take ownership of the RAM. You can configure the Elasticsearch JVM settings 
in the ``config/jvm.options`` file.

I have set the initial and maximum size of the total heap space to ``6 GB``, so Elasticsearch should be able to allocate 
enough RAM to play with:

```
# Xms represents the initial size of total heap space
# Xmx represents the maximum size of total heap space
-Xms6g
-Xmx6g
```

And finally I wanted to make sure, that the Elasticsearch process isn't swapped out. According to the Elasticsearch 
documentation this can be configured in the ``config/elasticsearch.yml`` by adding:

```
bootstrap.memory_lock: true
```

More information on Heap Sizing and Swapping can be found at:

* https://www.elastic.co/guide/en/elasticsearch/guide/current/heap-sizing.html (Guide to Heap Sizing)
* https://www.elastic.co/blog/a-heap-of-trouble (Detailed article on the maximum JVM Heap Size)

## Summary ##

<table>
  <thead>
    <tr>
      <th>Database</th>
      <th>Elapsed Time (Minutes)</th>
      <th># Records</th>
      <th>Throughput (records/s)</th>
      <th>Database Size (GB)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>InfluxDB 1.7.1</td>
      <td>147</td>
      <td>45,112</td>
      <td>7.91</td>
    </tr>
    <tr>
        <td>TimescaleDB 1.0</td>
        <td>247</td>
        <td>27,560</td>
        <td>37</td>
    </tr>
    <tr>
      <td>SQL Server 2017</td>
      <td>81.25</td>
      <td>406,242,465</td>
      <td>83,059</td>
      <td>12.6</td>
    </tr>
    <tr>
        <td>Elasticsearch 6.5.1</td>
        <td>718.9</td>
        <td>406,548,765</td>
        <td>9,425</td>
        <td>52.9</td>
  </tbody>
</table>

## Conclusion ##

It was interesting to see, that the SQL Server 2017 was the fastest database to write the data. Without any changes to its default configuration! This is 
probably a highly biased benchmark result, because I am using a Windows 10 machine in these tests. But I needed these figures to see, what I can recommend 
for Windows environments, that need a high throughput for Time series-based workloads.

But what's all the worlds data worth, if we cannot read it efficiently? In the next part of the series, I will investigate how efficient queries on the 
databases are and how to optimize it.

[Columnstore indexes]: https://docs.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview
[timescaledb-tune]: https://github.com/timescale/timescaledb-tune
[The world’s most valuable resource is no longer oil, but data]: https://www.economist.com/leaders/2017/05/06/the-worlds-most-valuable-resource-is-no-longer-oil-but-data
[FTP Link]: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/air_temperature/historical/
[TimescaleDB]: https://www.timescale.com/
[Elasticsearch]: https://www.elastic.co/
[SQL Server]: https://www.microsoft.com/de-de/sql-server/sql-server-2017
[InfluxData]: https://www.influxdata.com/
[InfluxDB]: https://www.influxdata.com/time-series-platform/influxdb/
[DWD Open Data]: https://opendata.dwd.de/
[Deutscher Wetterdienst (DWD)]: https://www.dwd.de
[GermanWeatherDataExample/Resources/files.md]: https://github.com/bytefish/GermanWeatherDataExample/blob/master/GermanWeatherData/Resources/files.md
