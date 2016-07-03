title: Building Applications with Apache Flink (Part 4): Writing and Using a custom PostgreSQL SinkFunction
date: 2016-07-03 20:10
tags: java, flink, postgresql
category: java
slug: apache_flink_series_4
author: Philipp Wagner
summary: This article shows how to write a custom PostgreSQL SinkFunction for Apache Flink.

In this article I am going to show how to write a custom Apache Flink [SinkFunction], that bulk writes results of a [DataStream] into a PostgreSQL database.

## What we are going to build ##

Processed data often needs to be written into a relational database, simply because SQL makes it easy to work with data. Often 
enough you will also need to generate reports for customers or feed an existing application, which uses the relational database. 

A custom data sink for Apache Flink needs to implement the [SinkFunction] interface. If a resource needs to be opened and closed, then a 
[RichSinkFunction] needs to be implemented.

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://github.com/bytefish/FlinkExperiments](https://github.com/bytefish/FlinkExperiments)

## PostgreSQL SinkFunction ##

### BasePostgresSink ###

We start by implementing the abstract base class ``BasePostgresSink<TEntity>``. It implements the [RichSinkFunction], so it can create 
a new ``BulkProcessor`` when opening the Sink, and close the ``BulkProcessor`` when closing the Sink. 

You may wonder, why I don't pass the ``BulkProcessor`` as a dependency into the base class. It's simply because Apache Flink serializes and distributes 
the [RichSinkFunction] to each of its workers. That's why the ``BulkProcessor`` is created inside of the [RichSinkFunction], because all members of a 
[RichSinkFunction] need to be Serializable.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sinks.pgsql;

import de.bytefish.pgbulkinsert.IPgBulkInsert;
import de.bytefish.pgbulkinsert.pgsql.processor.BulkProcessor;
import de.bytefish.pgbulkinsert.pgsql.processor.handler.BulkWriteHandler;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import pgsql.connection.PooledConnectionFactory;

import java.net.URI;

public abstract class BasePostgresSink<TEntity> extends RichSinkFunction<TEntity> {

    private final URI databaseUri;
    private final int bulkSize;

    private BulkProcessor<TEntity> bulkProcessor;

    public BasePostgresSink(URI databaseUri, int bulkSize) {
        this.databaseUri = databaseUri;
        this.bulkSize = bulkSize;
    }

    @Override
    public void invoke(TEntity entity) throws Exception {
        bulkProcessor.add(entity);
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        this.bulkProcessor = new BulkProcessor<>(new BulkWriteHandler<>(getBulkInsert(), new PooledConnectionFactory(databaseUri)), bulkSize);
    }

    @Override
    public void close() throws Exception {
        bulkProcessor.close();
    }

    protected abstract IPgBulkInsert<TEntity> getBulkInsert();
}
```

#### PooledConnectionFactory ####

The ``BulkProcessor`` of [PgBulkInsert] needs a way to obtain a ``Connection`` for the database access. I don't like reinventing 
the wheel, so in my projects I simply use the great [DBCP2] project for handling database connections. 

You can add the following dependencies to your ``pom.xml`` to include [DBCP2] in your project:

```xml
<dependency>
	<groupId>org.apache.commons</groupId>
	<artifactId>commons-dbcp2</artifactId>
	<version>2.0.1</version>
</dependency>
```

The Connection Factory for the ``BulkProcessor`` can then be implemented like this.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package pgsql.connection;

import de.bytefish.pgbulkinsert.functional.Func1;
import org.apache.commons.dbcp2.BasicDataSource;

import java.net.URI;
import java.sql.Connection;

public class PooledConnectionFactory implements Func1<Connection> {

    private final BasicDataSource connectionPool;

    public PooledConnectionFactory(URI databaseUri) {
        this.connectionPool = new BasicDataSource();

        initializeConnectionPool(connectionPool, databaseUri);
    }

    private void initializeConnectionPool(BasicDataSource connectionPool, URI databaseUri) {
        final String dbUrl = "jdbc:postgresql://" + databaseUri.getHost() + databaseUri.getPath();

        if (databaseUri.getUserInfo() != null) {
            connectionPool.setUsername(databaseUri.getUserInfo().split(":")[0]);
            connectionPool.setPassword(databaseUri.getUserInfo().split(":")[1]);
        }
        connectionPool.setDriverClassName("org.postgresql.Driver");
        connectionPool.setUrl(dbUrl);
        connectionPool.setInitialSize(1);
    }

    @Override
    public Connection invoke() throws Exception {
        return connectionPool.getConnection();
    }
}
```

## Example ##

### Database Setup ###

First of all we are going to write the DDL scripts for creating the database schema and tables. 

#### Schema ####

I am using schemas to keep my database clean and so should you. A database schema logically groups the objects such as tables, views, 
stored procedures, ... and makes it possible to assign user permissions to the schema. In this example the ``sample`` schema is going 
to contain the tables for the station and measurement data.

```
DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'sample') THEN

    CREATE SCHEMA sample;

END IF;

END;
$$;
```

#### Tables ####

```
DO $$
BEGIN

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'sample' 
	AND table_name = 'station'
) THEN

CREATE TABLE sample.station
(
	station_id SERIAL PRIMARY KEY,
	wban VARCHAR(255) NOT NULL,
	name VARCHAR(255) NOT NULL,
	state VARCHAR(255), 
	location VARCHAR(255),
	latitude REAL NOT NULL,
	longitude REAL NOT NULL,
	ground_height SMALLINT,
	station_height SMALLINT,
	TimeZone SMALLINT
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
	wban VARCHAR(255),
	dateTime TIMESTAMP,
	temperature REAL,
	windSpeed REAL,
	stationPressure REAL,
	skyCondition VARCHAR(255)	
);

END IF;

END;
$$;
```

#### Constraints ####

```
DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_station_wban') THEN
	ALTER TABLE sample.station
		ADD CONSTRAINT uk_station_wban
		UNIQUE (wban);
END IF;

END;
$$;
```

#### Security ####

```
DO $$
BEGIN

REVOKE ALL ON sample.station FROM public;
REVOKE ALL ON sample.weather_data FROM public;

END;
$$;
```

### Station Data ###

We are not going to persist the station data in the SQL database. That's why the Stations are initially populated with a simple insert script, which was generated 
from the original data. It contains all the informations, which is also set in the domain model.

```
DO $$
BEGIN

IF EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'sample' 
	AND table_name = 'station'
) THEN


INSERT INTO sample.station(wban, name, state, location, latitude, longitude, ground_height, station_height, timeZone)
SELECT '00100', 'ARKADELPHIA', 'AR', 'DEXTER B FLORENCE MEM FLD AP', 34.09972, -93.06583, 182, NULL, -6
WHERE NOT EXISTS (SELECT 1 FROM sample.station WHERE wban='00100');

-- ... station data


END IF;

END
$$;
```

#### Creating a Deployment Script ####

[Batch]: http://en.wikipedia.org/wiki/Batch_file

You could copy and paste the above scripts for this tutorial. This is totally OK for small applications, but it won't scale for any real project. 
Believe me, you need to automate the task of creating and migrating a database as early as possible in your project.

I am working in a Windows environment right now, so I have used a [Batch] file to automate the database setup. There is no magic going on, I am just 
setting the path to ``psql`` and use the ``PGPASSWORD`` environment variable to pass the password to the command line.

```batch
@echo off

:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

set PGSQL_EXECUTABLE="C:\Program Files\PostgreSQL\9.4\bin\psql.exe"
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

	:: Schemas
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 01_Schemas/schema_sample.sql -L %LOGFILE%
	
	:: Tables
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 02_Tables/tables_sample.sql -L %LOGFILE%
	
	:: Keys
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 03_Keys/keys_sample.sql -L %LOGFILE%
	
	:: Security
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 05_Security/security_sample.sql -L %LOGFILE%
	
	:: Data
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 06_Data/data_sample_stations.sql -L %LOGFILE%
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

### PostgreSQL Model ###

You have already seen, that we are building a separate model for each use case. This keeps the analysis model clean and so we do not leak any 
database related modelling into the analysis model (foreign keys, column names, ...). Note, that the measurement time should be stored as a 
PostgreSQL ``timestamp``, so it doesn't have any timezone information. The data in the station table already holds the relevant timezone offset. 

I have decided against using the Primary Key of a Station as a Foreign Key constraint, because such measurement data should be stored as fast as 
possible, without being eventually slowed down by Foreign Key constraints.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package pgsql.model;

import java.time.LocalDateTime;

public class LocalWeatherData {

    private String wban;

    private LocalDateTime dateTime;

    private Float temperature;

    private Float windSpeed;

    private Float stationPressure;

    private String skyCondition;

    public LocalWeatherData(String wban, LocalDateTime dateTime, Float temperature, Float windSpeed, Float stationPressure, String skyCondition) {
        this.wban = wban;
        this.dateTime = dateTime;
        this.temperature = temperature;
        this.windSpeed = windSpeed;
        this.stationPressure = stationPressure;
        this.skyCondition = skyCondition;
    }

    public String getWban() {
        return wban;
    }

    public LocalDateTime getDateTime() {
        return dateTime;
    }

    public Float getTemperature() {
        return temperature;
    }

    public Float getWindSpeed() {
        return windSpeed;
    }

    public Float getStationPressure() {
        return stationPressure;
    }

    public String getSkyCondition() {
        return skyCondition;
    }
}
```


### PgBulkInsert Database Mapping ###

The ``BasePostgresSink`` function has to implement a function, that returns a ``PgBulkInsert<TEntity>``. A ``PgBulkInsert<TEntity>`` in [PgBulkInsert] simply 
defines the mapping between a database table and the domain model.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package pgsql.mapping;

import de.bytefish.pgbulkinsert.PgBulkInsert;

public class LocalWeatherDataBulkInsert extends PgBulkInsert<pgsql.model.LocalWeatherData> {

    public LocalWeatherDataBulkInsert(String schemaName, String tableName) {

        super(schemaName, tableName);

        mapString("wban", pgsql.model.LocalWeatherData::getWban);
        mapTimeStamp("dateTime", pgsql.model.LocalWeatherData::getDateTime);
        mapReal("temperature", pgsql.model.LocalWeatherData::getTemperature);
        mapReal("windSpeed", pgsql.model.LocalWeatherData::getWindSpeed);
        mapReal("stationPressure", pgsql.model.LocalWeatherData::getStationPressure);
        mapString("skyCondition", pgsql.model.LocalWeatherData::getSkyCondition);
    }

}
```

### LocalWeatherDataPostgresSink ###

With the PostgreSQL domain model defined, the ``BasePostgresSink`` and the ``PgBulkInsert`` mapping, the ``LocalWeatherDataPostgresSink`` for the example can easily be implemented.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sinks.pgsql;

import de.bytefish.pgbulkinsert.IPgBulkInsert;

import java.net.URI;

public class LocalWeatherDataPostgresSink extends BasePostgresSink<pgsql.model.LocalWeatherData> {

    public LocalWeatherDataPostgresSink(URI databaseUri, int bulkSize) {
        super(databaseUri, bulkSize);
    }

    @Override
    protected IPgBulkInsert<pgsql.model.LocalWeatherData> getBulkInsert() {
        return new pgsql.mapping.LocalWeatherDataBulkInsert("sample", "weather_data");
    }

}
```

### Plugging it into the DataStream ###

Once the [SinkFunction] is written, it can be plugged into the existing [DataStream] pipeline. In the example the general ``DataStream<model.LocalWeatherData>`` 
is first transformed into a DataStream<pgsql.model.LocalWeatherData>``. Then the custom PostgreSQL Sink is added to the DataStream, with a connection factory that 
 connects to a local database instance and a bulk size of 1000 entities.

```java
// Converts the general stream into the Postgres-specific representation:
DataStream<pgsql.model.LocalWeatherData> pgsqlDailyMaxTemperature = maxTemperaturePerDay
		.map(new MapFunction<model.LocalWeatherData, pgsql.model.LocalWeatherData>() {
			@Override
			public pgsql.model.LocalWeatherData map(model.LocalWeatherData localWeatherData) throws Exception {
				return pgsql.converter.LocalWeatherDataConverter.convert(localWeatherData);
			}
		});
	
// Add a new Postgres Sink with a Bulk Size of 1000 entities:
pgsqlDailyMaxTemperature.addSink(new LocalWeatherDataPostgresSink(URI.create("postgres://philipp:test_pwd@127.0.0.1:5432/sampledb"), 1000));
```

#### Converter ####

The ``LocalWeatherDataConverter`` simply takes a ``model.LocalWeatherData`` and converts it into a ``pgsql.model.LocalWeatherData``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package pgsql.converter;

import java.time.LocalDateTime;

public class LocalWeatherDataConverter {

    public static pgsql.model.LocalWeatherData convert(model.LocalWeatherData modelLocalWeatherData) {

        String wban = modelLocalWeatherData.getStation().getWban();
        LocalDateTime dateTime = modelLocalWeatherData.getDate().atTime(modelLocalWeatherData.getTime());
        Float temperature = modelLocalWeatherData.getTemperature();
        Float windSpeed = modelLocalWeatherData.getWindSpeed();
        Float stationPressure = modelLocalWeatherData.getStationPressure();
        String skyCondition = modelLocalWeatherData.getSkyCondition();

        return new pgsql.model.LocalWeatherData(wban, dateTime, temperature, windSpeed, stationPressure, skyCondition);
    }
}
```

## Conclusion ##

In this article you have seen how to write a custom [SinkFunction] for [Apache Flink]. In the next article you will see how to write a custom [SinkFunction] for 
writing into an [Elasticsearch] database and visualize the results with [Kibana], which is a Frontend to [Elasticsearch].

[Apache Flink]: https://flink.apache.org/
[Elasticsearch]: https://www.elastic.co
[Kibana]: https://www.elastic.co/products/kibana
[ElasticUtils]: https://github.com/bytefish/ElasticUtils
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser
[PgBulkInsert]: https://github.com/bytefish/PgBulkInsert
[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd
[DataStream]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/index.html
[KeyedStream]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/windows.html
[SourceFunction]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/#data-sources
[SinkFunction]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/#data-sinks
[RichSinkFunction]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/functions/sink/RichSinkFunction.html
[DBCP2]: https://commons.apache.org/proper/commons-dbcp/