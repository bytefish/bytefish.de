title: Building Applications with Apache Flink (Part 4): A custom PostgreSQL SinkFunction and Preparing the Database 
date: 2016-06-19 14:27
tags: java, flink, elasticsearch, postgresql
category: java
slug: apache_flink_example
author: Philipp Wagner
summary: This article shows how to write a custom PostgreSQL SinkFunction for Apache Flink.

## What we are going to build ##

You often need to write your data into a relational database, because relational databases offer amazing possibilities to work 
with data using SQL as a query language. Often enough reports need to be generated 

Single Inserts to a database are highly inefficient, that's why [PgBulkInsert] is used for Bulk Inserts to a PostgreSQL database. 

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://github.com/bytefish/FlinkExperiments](https://github.com/bytefish/FlinkExperiments)

## Database Setup ##

### Schema ###

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

### Tables ###

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

### Constraints ###

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

### Security ###

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

### Creating a Deployment Script ###

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

## PostgreSQL Model ##

The measurement time should be stored as PostgreSQL ``timestamp`` without timezone information, because the station data already holds the timezone offset.

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

## Converter ##

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


## SinkFunction ##

### BasePostgresSink ###

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

## LocalWeatherData ##


### Mapping ###

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

##

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



## PooledConnectionFactory ##

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

[Apache Flink]: https://flink.apache.org/
[Elasticsearch]: https://www.elastic.co
[ElasticUtils]: https://github.com/bytefish/ElasticUtils
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser
[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd