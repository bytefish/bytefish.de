title: Using SQL Server Table-valued Parameters (TVP) for Bulk Inserts
date: 2021-02-25 18:06
tags: sqlserver, java
category: java
slug: sql_server_tvp_bulk_inserts
author: Philipp Wagner
summary: Example for working with SQL Server Table-valued parameters in Java.

[JSqlServerBulkInsert]: https://github.com/JSqlServerBulkInsert/JSqlServerBulkInsert

Some years ago I have written [JSqlServerBulkInsert], which provides a small abstraction layer over the 
``SqlServerBulkCopy`` class of the Microsoft SQL Server JDBC Driver. The idea of the library is to write 
a small mapping for a POJO and fire data into SQL Server... without having to maintain Stored Procedures.

But in real life it's often not only about inserting data. You probably need to create additional relations 
between entities or you'll need to perform updates in the data. Simply put, [JSqlServerBulkInsert] and the 
underlying ``SqlServerBulkCopy`` can't do this.

So in recent years I have switched to using Stored Procedures and passing Table-valued parameters for most 
of the performance critical SQL Server work I am doing. It's not really obvious with the Microsoft SQL Server 
JDBC driver, so I made up an example here:

* [https://github.com/bytefish/SqlServerTvpExample](https://github.com/bytefish/SqlServerTvpExample)

## The Scenario: Handling Device Measurements ##

Imagine we are monitoring an array of machines, that send large amounts of measurements. At one point our 
single insert statements don't scale anymore, the connection pool exhausts and we are running into 
timeouts. Ouch. 

And how do we update measurements? Do we perform a ``SELECT`` lookup for every single measurement?

Instead of single inserts, we need to batch our data and let the database handle the rest of it. So how 
do we get the data into the SQL Server database efficiently? 

Table-valued Parameters!

### The Data Model ###

A measurement of a device probably has something like a Device Identifier, Parameter Identifier, a Timestamp 
the value was taken at and the measured Value. This probably leads to a Java class like this:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlservertvpexample.model;

import java.sql.Timestamp;

public class DeviceMeasurement {

    private String deviceId;

    private String parameterId;

    private Timestamp timestamp;

    private double value;

    public DeviceMeasurement() {
    }

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public String getParameterId() {
        return parameterId;
    }

    public void setParameterId(String parameterId) {
        this.parameterId = parameterId;
    }

    public Timestamp getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Timestamp timestamp) {
        this.timestamp = timestamp;
    }

    public double getValue() {
        return value;
    }

    public void setValue(double value) {
        this.value = value;
    }
}
```

### Simulating Data ###

There are no real devices here, so we need a way to fake some data for a given time range. We can define an 
iterator, that yields timestamps in a given interval between a start date and an end date: 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlservertvpexample.data;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Iterator;

public class DateTimeIterator implements Iterator<LocalDateTime> {

    private LocalDateTime endDate;
    private LocalDateTime currentDate;
    private Duration interval;

    public DateTimeIterator(LocalDateTime startDate, LocalDateTime endDate, Duration interval) {
        this.endDate = endDate;
        this.interval = interval;
        this.currentDate = startDate;
    }

    @Override
    public boolean hasNext() {
        return currentDate.isBefore(endDate);
    }

    @Override
    public LocalDateTime next() {
        final LocalDateTime result = currentDate;
        currentDate = currentDate.plus(interval);
        return result;
    }
}
```

Next we are writing a small class ``DataGenerator``, that generates random values between for a given time range:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlservertvpexample.data;

import de.bytefish.sqlservertvpexample.model.DeviceMeasurement;

import java.sql.Timestamp;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Random;
import java.util.Spliterator;
import java.util.Spliterators;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

public class DataGenerator {

    private static Random random = new Random();

    private LocalDateTime startDate;
    private LocalDateTime endDate;
    private Duration interval;

    public DataGenerator(LocalDateTime startDate, LocalDateTime endDate, Duration interval) {
        this.startDate = startDate;
        this.endDate = endDate;
        this.interval = interval;
    }

    public Stream<DeviceMeasurement> generate(final String deviceId, final String parameterId, final double low, final double high) {

        // For Creating the Measurement TimeSteps:
        final DateTimeIterator iterator = new DateTimeIterator(startDate, endDate, interval);

        // Create the Stream:
        return StreamSupport
                .stream(Spliterators.spliteratorUnknownSize(iterator, Spliterator.ORDERED), false)
                .map(measurementTimeStamp -> createDeviceMeasurement(deviceId, parameterId, measurementTimeStamp, low, high));
    }

    private DeviceMeasurement createDeviceMeasurement(final String deviceId, final String parameterId, final LocalDateTime timestamp, final double low, final double high) {

        // Generate a Random Value for the Sensor:
        final double randomValue = low + (high - low) * random.nextDouble();

        // Create the Measurement:
        final DeviceMeasurement data = new DeviceMeasurement();

        data.setDeviceId(deviceId);
        data.setParameterId(parameterId);
        data.setTimestamp(Timestamp.valueOf(timestamp));
        data.setValue(randomValue);

        return data;
    }
}
```

We can now initialize a ``DataGenerator`` and use the ``DataGenerator#generate`` method to generate random values.

And that's it for the data!

## Creating the SQL Server Database ##

On the database side we start by creating the Database, a ``sample`` schema and the table ``[sample].[DeviceMeasurement]``, 
which holds the measurements and obviously maps to the Java data model:

```sql
--
-- DATABASE
--
IF DB_ID('$(dbname)') IS NULL
BEGIN
    CREATE DATABASE $(dbname)
END
GO

use $(dbname)
GO 

-- 
-- SCHEMAS
--
IF NOT EXISTS (SELECT name from sys.schemas WHERE name = 'sample')
BEGIN

	EXEC('CREATE SCHEMA sample')
    
END
GO

--
-- TABLES
--
IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[sample].[DeviceMeasurement]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [sample].[DeviceMeasurement](
        [DeviceID] [NVARCHAR](50) NOT NULL,
        [ParameterID] [NVARCHAR](50) NOT NULL,
        [Timestamp] [DATETIME2],
        [Value] [DECIMAL](18, 2)
    );

END
GO
```

We want to make sure, that there is only one measurement for a given device, parameter and timestamp. It 
also enables faster queries, so let's add a ``UNIQUE INDEX`` on the columns ``DeviceID``, ``ParameterID`` 
and ``Timestamp``:

```sql                                                                      

--
-- INDEXES
--
IF EXISTS (SELECT name FROM sys.indexes WHERE name = N'UX_DeviceMeasurement')
BEGIN
    DROP INDEX [UX_DeviceMeasurement] on [sample].[DeviceMeasurement];
END
GO

CREATE UNIQUE INDEX UX_DeviceMeasurement ON [sample].[DeviceMeasurement](DeviceID, ParameterID, Timestamp);
GO
```

The plan is to create a ``TYPE`` and pass the data as a ``TABLE`` into a Stored Procedure. The Stored Procedure can then 
perform a ``MERGE`` statement on the data batch. The Stored Procedures probably already references the TYPE, so in the DDL 
Script we are first dropping the Stored Procedure:

```sql
--
-- STORED PROCEDURES
--
IF OBJECT_ID(N'[sample].[InsertOrUpdateDeviceMeasurements]', N'P') IS NOT NULL
BEGIN
    DROP PROCEDURE [sample].[InsertOrUpdateDeviceMeasurements];
END
GO
```

Now we can define the TYPE ``[sample].[DeviceMeasurementType]`` as a TABLE. It is typically just a 1 to 1 copy of the 
destination table:

```sql
IF EXISTS (SELECT * FROM sys.types WHERE is_table_type = 1 AND name = 'DeviceMeasurementType')
BEGIN
    DROP TYPE [sample].[DeviceMeasurementType];
END
GO

CREATE TYPE [sample].[DeviceMeasurementType] AS TABLE (
        [DeviceID] [NVARCHAR](50) NOT NULL,
        [ParameterID] [NVARCHAR](50) NOT NULL,
        [Timestamp] [DATETIME2],
        [Value] [DECIMAL](18, 2)
);
GO
```

And finally write the Stored Procedure ``[sample].[InsertOrUpdateDeviceMeasurements]``, which inserts or updates measurements in the database. You can 
see, that it takes the ``[sample].[DeviceMeasurementType]`` type as its only parameter:

```sql
CREATE PROCEDURE [sample].[InsertOrUpdateDeviceMeasurements]
  @TVP [sample].[DeviceMeasurementType] ReadOnly
AS
BEGIN
    
    SET NOCOUNT ON;
 
    MERGE [sample].[DeviceMeasurement] AS TARGET USING @TVP AS SOURCE ON (TARGET.DeviceID = SOURCE.DeviceID) AND (TARGET.ParameterID = SOURCE.ParameterID) AND (TARGET.Timestamp = SOURCE.Timestamp)
    WHEN MATCHED THEN
        UPDATE SET TARGET.Value = SOURCE.Value
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (DeviceID, ParameterID, Timestamp, Value)
        VALUES (SOURCE.DeviceID, SOURCE.ParameterID, SOURCE.Timestamp, SOURCE.Value);

END
GO
```

### Calling the Stored Procedure with Batched Data ###

What I usually add is a class I call "...BulkProcessor", which converts the ``DeviceMeasurement`` into the ``SQLServerDataTable`` 
and passes the data to the Stored Procedure. 

It's quite simple to do:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlservertvpexample.processor;

import com.microsoft.sqlserver.jdbc.SQLServerCallableStatement;
import com.microsoft.sqlserver.jdbc.SQLServerDataTable;
import com.microsoft.sqlserver.jdbc.SQLServerException;
import de.bytefish.sqlservertvpexample.model.DeviceMeasurement;
import de.bytefish.sqlservertvpexample.utils.Tuple3;

import java.sql.Connection;
import java.sql.Types;
import java.util.Collection;
import java.util.List;
import java.util.stream.Collectors;

import static java.util.stream.Collectors.groupingBy;

public class DeviceMeasurementBulkProcessor {

    private static final String SQL_COMMAND = "{call [sample].[InsertOrUpdateDeviceMeasurements] (?)}";

    public void saveAll(Connection connection, Collection<DeviceMeasurement> source) throws Exception {

        // In a Batch the Values have to be unique to satisfy the Unique Constraint in the Database,
        // so we group them by multiple keys and then take the first value from each of the batches:
        List<DeviceMeasurement> distinctDeviceMeasurements = source.stream()
                .collect(groupingBy(x -> new Tuple3<>(x.getDeviceId(), x.getParameterId(), x.getTimestamp())))
                .values().stream()
                .map(x -> x.get(0))
                .collect(Collectors.toList());

        // Build the SQLServerDataTable:
        SQLServerDataTable sqlServerDataTable = buildSqlServerDataTable(distinctDeviceMeasurements);

        // And insert it:
        try (SQLServerCallableStatement  callableStmt  = (SQLServerCallableStatement) connection.prepareCall(SQL_COMMAND)) {
            callableStmt.setStructured(1, "[sample].[DeviceMeasurementType]", sqlServerDataTable);
            callableStmt.execute();
        }
    }

    private SQLServerDataTable buildSqlServerDataTable(Collection<DeviceMeasurement> deviceMeasurements) throws SQLServerException {
        SQLServerDataTable tvp = new SQLServerDataTable();

        tvp.addColumnMetadata("DeviceID", Types.NVARCHAR);
        tvp.addColumnMetadata("ParameterID", Types.NVARCHAR);
        tvp.addColumnMetadata("Timestamp", Types.TIMESTAMP);
        tvp.addColumnMetadata("Value", Types.DECIMAL);

        for (DeviceMeasurement deviceMeasurement : deviceMeasurements) {
            tvp.addRow(
                    deviceMeasurement.getDeviceId(),
                    deviceMeasurement.getParameterId(),
                    deviceMeasurement.getTimestamp(),
                    deviceMeasurement.getValue()
            );
        }

        return tvp;
    }
}
```

The values in a batch need to be unique, so to group by Device, Parameter and Timestamp with Javas ``groupingBy`` I 
defined a class ``Tuple3<T1, T2, T3>`` and have overriden the ``Object#equals`` method:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlservertvpexample.utils;

import java.util.Objects;

public class Tuple3<T1, T2, T3> {
    private final T1 t1;
    private final T2 t2;
    private final T3 t3;

    public Tuple3(T1 t1, T2 t2, T3 t3) {
        this.t1 = t1;
        this.t2 = t2;
        this.t3 = t3;
    }

    public T1 getT1() {
        return t1;
    }

    public T2 getT2() {
        return t2;
    }

    public T3 getT3() {
        return t3;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Tuple3<?, ?, ?> tuple3 = (Tuple3<?, ?, ?>) o;
        return Objects.equals(t1, tuple3.t1) && Objects.equals(t2, tuple3.t2) && Objects.equals(t3, tuple3.t3);
    }

    @Override
    public int hashCode() {
        return Objects.hash(t1, t2, t3);
    }
}
```

### Wiring All The Things ###

And finally it's time to wire things up. There are probably a million way to create batches from a stream of data, but 
in this example I opted to use RxJava, which already has a ``buffer`` operator to create data batches:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlservertvpexample;

import de.bytefish.sqlservertvpexample.data.DataGenerator;
import de.bytefish.sqlservertvpexample.model.DeviceMeasurement;
import de.bytefish.sqlservertvpexample.processor.DeviceMeasurementBulkProcessor;
import io.reactivex.rxjava3.core.Observable;
import io.reactivex.rxjava3.disposables.Disposable;

import java.sql.Connection;
import java.sql.DriverManager;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Stream;

public class Program {

	private static final String connectionUrl = "jdbc:sqlserver://localhost;instanceName=SQLEXPRESS;databaseName=SampleDatabase;user=philipp;password=test_pwd";

	public static void main(String[] args) {

		LocalDateTime startDate = LocalDateTime.of(2020, 1, 1, 0, 0, 0);
		LocalDateTime endDate = LocalDateTime.of(2020, 12, 31, 0, 0, 0);

		// Create the Batch Processor:
		DeviceMeasurementBulkProcessor processor = new DeviceMeasurementBulkProcessor();

		// Generate a Stream of data using a fake device sending each 15s for a year. This should
		// generate something around 2 Million measurements:
		Stream<DeviceMeasurement> measurementStream = new DataGenerator(startDate, endDate, Duration.ofSeconds(15))
				.generate("device1", "parameter1", 10, 19);

		// Write Data in 80000 Value Batches:
		Disposable disposable = Observable
				.fromStream(measurementStream)
				.buffer(80_000)
				.forEach(values -> writeBatch(processor, values));

		// Being a good citizen by cleaning up RxJava stuff:
		disposable.dispose();
	}

	private static void writeBatch(DeviceMeasurementBulkProcessor processor, List<DeviceMeasurement> values) throws Exception {
		try {
			internalWriteBatch(processor, values);
		} catch(Exception e) {
			throw new RuntimeException(e);
		}
	}

	private static void internalWriteBatch(DeviceMeasurementBulkProcessor processor, List<DeviceMeasurement> values) throws Exception {
		try (Connection connection = DriverManager.getConnection(connectionUrl)) {
			processor.saveAll(connection, values);
		}
	}
}
```

And that's it for now.