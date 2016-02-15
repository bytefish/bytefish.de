title: Building Import Pipelines with JTinyCsvParser and PgBulkInsert
date: 2016-02-04 21:16
tags: java, pgbulkinsert, jtinycsvparser
category: java
slug: jtinycsvparser_pgbulkinsert
author: Philipp Wagner
summary: This article shows how to build an import pipeline with JTinyCsvParser and PgBulkInsert.

[MIT License]: https://opensource.org/licenses/MIT
[COPY command]: http://www.postgresql.org/docs/current/static/sql-copy.html
[Npgsql documentation]: http://www.npgsql.org/doc/copy.html
[PgBulkInsert]: https://github.com/bytefish/PgBulkInsert
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser

In my professional life I have often seen large CSV files, which need to be imported as efficient as possible. 
That's why I have developed [JTinyCsvParser] and [PgBulkInsert] for Java 1.8. Both provide a Streaming API 
and are very easy to combine.

In this example I will show you how to combine both libraries and insert a large dataset.

## Dataset ##

In this post we are parsing and importing a real life dataset. It's the local weather data in March 2015 gathered 
by all weather stations in the USA. You can obtain the data  ``QCLCD201503.zip`` from:
 
* [http://www.ncdc.noaa.gov/orders/qclcd](http://www.ncdc.noaa.gov/orders/qclcd)

The File size is ``557 MB`` and it has ``4,496,262`` lines.

The CSV file has around ``40`` columns. We only want to use three columns of the file (``WBAN``, ``Sky Condition`` and ``Date``), 
which correspond to the indices 0 (``WBAN``), 1 (``SkyCondition``) and 4 (``Date``). It's not really necessary to know, what the 
meaning behind the columns is, I just needed a large dataset.

## Preparing the Database ##

Here is the SQL Script to create the table, where the data will be stored.

```sql
CREATE TABLE sample.unit_test
(
    wban text, 
    sky_condition text,
    date timestamp
);
```

## Domain Model ##

The corresponding domain model in the application might look like this.

```java
private class LocalWeatherData
{
    private String wban;

    private LocalDate date;

    private String skyCondition;

    public String getWban() {
        return wban;
    }

    public void setWban(String wban) {
        this.wban = wban;
    }

    public LocalDate getDate() {
        return date;
    }

    public void setDate(LocalDate date) {
        this.date = date;
    }

    public String getSkyCondition() {
        return skyCondition;
    }

    public void setSkyCondition(String skyCondition) {
        this.skyCondition = skyCondition;
    }
}
```

## TinyCsvParser ##

When using [JTinyCsvParser] you have to define a ``CsvMapping``, which defines how the domain model and the CSV file map to each other. You 
can see, that the column indices in the CSV file map to the setters of the domain model. 

The date in the CSV file has the format ``yyyyMMdd``, which is not the default date format of Java. That's why a ``LocalDateConverter`` 
with a custom format is passed into the property mapping.

```java
public class LocalWeatherDataMapper extends CsvMapping<LocalWeatherData>
{
    public LocalWeatherDataMapper(IObjectCreator creator)
    {
        super(creator);

        MapProperty(0, String.class, LocalWeatherData::setWban);
        MapProperty(1, LocalDate.class, LocalWeatherData::setDate, new LocalDateConverter(DateTimeFormatter.ofPattern("yyyyMMdd")));
        MapProperty(4, String.class, LocalWeatherData::setSkyCondition);
    }
}
```

## PgBulkInsert ##

For the bulk inserts to PostgreSQL the mapping between the database table and the domain model needs to be defined. This is done by implementing 
the abstract base class ``PgBulkInsert<TEntity>``. 

We can now implement it for the ``Person`` class, and again you can see how the getters of the domain model map to the column names of the 
database table.

```java
public class LocalWeatherDataBulkInserter extends PgBulkInsert<LocalWeatherData>
{
    public LocalWeatherDataBulkInserter() {
        super("sample", "unit_test");

        MapString("wban", LocalWeatherData::getWban);
        MapString("sky_condition", LocalWeatherData::getSkyCondition);
        MapDate("date", LocalWeatherData::getDate);
    }
}
```

## Import Pipeline ##

Finally we can write the import pipeline, which uses [JTinyCsvParser] and [PgBulkInsert] to import the CSV data into PostgreSQL. 

```java
@Test
public void bulkInsertWeatherDataTest() throws SQLException {
    // Do not process the CSV file in parallel (Java 1.8 bug!):
    CsvParserOptions options = new CsvParserOptions(true, ",", false);
    // The Mapping to employ:
    LocalWeatherDataMapper mapping = new LocalWeatherDataMapper(() -> new LocalWeatherData());
    // Construct the parser:
    CsvParser<LocalWeatherData> parser = new CsvParser<>(options, mapping);
    // Create the BulkInserter used for Bulk Inserts into the Database:
    LocalWeatherDataBulkInserter bulkInserter = new LocalWeatherDataBulkInserter();
    // Read the file. Make sure to wrap it in a try with resources block, so the file handle gets disposed properly:
    try(Stream<CsvMappingResult<LocalWeatherData>> stream = parser.readFromFile(FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503hourly.txt"), StandardCharsets.UTF_8)) {
        // Filter the Stream of Mapping results, so only valid entries are processed:
        Stream<LocalWeatherData> localWeatherDataStream =  stream.filter(e -> e.isValid()).map(e -> e.getResult());
        // Now bulk insert valid entries into the PostgreSQL database:
        bulkInserter.saveAll(PostgreSqlUtils.getPGConnection(connection), localWeatherDataStream);
    }
    // Check if we have the correct amount of rows in the DB:
    Assert.assertEquals(4496262, getRowCount());
}
```

### Explanation ###

A lot of things are going on here. First of all the ``CsvParser`` is constructed. This is done by using the ``CsvParserOptions`` and the ``CsvMapping`` 
for the entity to parse. Then a ``PgBulkInsert`` object is instantiated, which is the ``LocalWeatherDataBulkInserter`` defined above. 

Then the CSV file is parsed. You have to be careful and wrap the ``CsvParser<TEntity>.readFromFile`` method in a [try-with-resources statement](https://docs.oracle.com/javase/tutorial/essential/exceptions/tryResourceClose.html), 
so the File Handle gets disposed properly. The result of the parsing is a ``Stream<CsvMappingResult<LocalWeatherData>>``, which is then consumed by the ``LocalWeatherDataBulkInserter``. The 
``Stream<CsvMappingResult<LocalWeatherData>>`` result type might look scary, but it basically only contains the parsed object and a flag if it is valid or not. A CSV file might contain invalid 
entries (wrong formats), and you don't want to stop parsing because a single line is invalid.

We only want to import valid entities into the database, so the stream is further filtered for valid entries and then mapped to the result entities. This stream is then consumed by the 
``LocalWeatherDataBulkInserter``, which also takes a PGConnection. If you work with a ``java.sql.Connection``, then you can try to get the underlying ``PGConnection`` with the utility 
method in ``PostgreSqlUtils.getPGConnection``.

## Conclusion ##

The example shows how to build a very efficient import pipeline with [JTinyCsvParser] and [PgBulkInsert]. Both projects are available from the Central Maven Repository, so they can be easily 
integrated into existing projects. 

## Full Source Code ##

### TransactionalTestBase ###

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import org.junit.After;
import org.junit.Before;

import java.sql.Connection;
import java.sql.DriverManager;

public abstract class TransactionalTestBase {

    protected Connection connection;

    @Before
    public void setUp() throws Exception {
        connection = DriverManager.getConnection("jdbc:postgresql://127.0.0.1:5432/sampledb", "philipp", "test_pwd");

        onSetUpBeforeTransaction();
        connection.setAutoCommit(false); // Start the Transaction:
        onSetUpInTransaction();
    }

    @After
    public void tearDown() throws Exception {

        onTearDownInTransaction();
        connection.rollback();
        onTearDownAfterTransaction();

        connection.close();
    }

    protected void onSetUpInTransaction() throws Exception {}

    protected void onSetUpBeforeTransaction() throws Exception {}

    protected void onTearDownInTransaction() throws Exception {}

    protected void onTearDownAfterTransaction() throws Exception {}
}
```

### IntegrationTest ###

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import de.bytefish.jtinycsvparser.CsvParser;
import de.bytefish.jtinycsvparser.CsvParserOptions;
import de.bytefish.jtinycsvparser.builder.IObjectCreator;
import de.bytefish.jtinycsvparser.mapping.CsvMapping;
import de.bytefish.jtinycsvparser.mapping.CsvMappingResult;
import de.bytefish.jtinycsvparser.typeconverter.LocalDateConverter;
import de.bytefish.pgbulkinsert.de.bytefish.pgbulkinsert.PgBulkInsert;
import de.bytefish.pgbulkinsert.de.bytefish.pgbulkinsert.util.PostgreSqlUtils;
import org.junit.Assert;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystems;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.stream.Stream;

public class IntegrationTest extends TransactionalTestBase {

    @Override
    protected void onSetUpInTransaction() throws Exception {
        createTable();
    }

    private class LocalWeatherData
    {
        private String wban;

        private LocalDate date;

        private String skyCondition;

        public String getWban() {
            return wban;
        }

        public void setWban(String wban) {
            this.wban = wban;
        }

        public LocalDate getDate() {
            return date;
        }

        public void setDate(LocalDate date) {
            this.date = date;
        }

        public String getSkyCondition() {
            return skyCondition;
        }

        public void setSkyCondition(String skyCondition) {
            this.skyCondition = skyCondition;
        }
    }

    public class LocalWeatherDataBulkInserter extends PgBulkInsert<LocalWeatherData>
    {
        public LocalWeatherDataBulkInserter() {
            super("sample", "unit_test");

            MapString("wban", LocalWeatherData::getWban);
            MapString("sky_condition", LocalWeatherData::getSkyCondition);
            MapDate("date", LocalWeatherData::getDate);
        }
    }

    public class LocalWeatherDataMapper extends CsvMapping<LocalWeatherData>
    {
        public LocalWeatherDataMapper(IObjectCreator creator)
        {
            super(creator);

            MapProperty(0, String.class, LocalWeatherData::setWban);
            MapProperty(1, LocalDate.class, LocalWeatherData::setDate, new LocalDateConverter(DateTimeFormatter.ofPattern("yyyyMMdd")));
            MapProperty(4, String.class, LocalWeatherData::setSkyCondition);
        }
    }

    @Test
    public void bulkInsertWeatherDataTest() throws SQLException {
        // Do not process the CSV file in parallel (Java 1.8 bug!):
        CsvParserOptions options = new CsvParserOptions(true, ",", false);
        // The Mapping to employ:
        LocalWeatherDataMapper mapping = new LocalWeatherDataMapper(() -> new LocalWeatherData());
        // Construct the parser:
        CsvParser<LocalWeatherData> parser = new CsvParser<>(options, mapping);
        // Create the BulkInserter used for Bulk Inserts into the Database:
        LocalWeatherDataBulkInserter bulkInserter = new LocalWeatherDataBulkInserter();
        // Read the file. Make sure to wrap it in a try with resources block, so the file handle gets disposed properly:
        try(Stream<CsvMappingResult<LocalWeatherData>> stream = parser.readFromFile(FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503hourly.txt"), StandardCharsets.UTF_8)) {
            // Filter the Stream of Mapping results, so only valid entries are processed:
            Stream<LocalWeatherData> localWeatherDataStream =  stream.filter(e -> e.isValid()).map(e -> e.getResult());
            // Now bulk insert valid entries into the PostgreSQL database:
            bulkInserter.saveAll(PostgreSqlUtils.getPGConnection(connection), localWeatherDataStream);
        }
        // Check if we have the correct amount of rows in the DB:
        Assert.assertEquals(4496262, getRowCount());
    }

    private boolean createTable() throws SQLException {

        String sqlStatement = "CREATE TABLE sample.unit_test\n" +
                "            (\n" +
                "                wban text,\n" +
                "                sky_condition text,\n" +
                "                date timestamp\n" +
                "            );";

        Statement statement = connection.createStatement();

        return statement.execute(sqlStatement);
    }

    private int getRowCount() throws SQLException {

        Statement s = connection.createStatement();

        ResultSet r = s.executeQuery("SELECT COUNT(*) AS rowcount FROM sample.unit_test");
        r.next();
        int count = r.getInt("rowcount");
        r.close();

        return count;
    }
}
```