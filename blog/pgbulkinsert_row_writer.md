title: PgBulkInsert: Writing data using a SimpleRowWriter
date: 2020-02-15 14:02
tags: java, pgbulkinsert
category: java
slug: pgbulkinsert_row_writer
author: Philipp Wagner
summary: This article introduces PgBulkInsert, which is a library for efficient bulk inserts to PostgreSQL.

[MIT License]: https://opensource.org/licenses/MIT
[COPY command]: http://www.postgresql.org/docs/current/static/sql-copy.html
[Npgsql documentation]: http://www.npgsql.org/doc/copy.html
[PgBulkInsert]: https://github.com/bytefish/PgBulkInsert

[PgBulkInsert] is a small Java library for bulk inserts with PostgreSQL using the Binary COPY Protocol:

> The [COPY command] is a PostgreSQL specific feature, which allows efficient bulk import or export of 
> data to and from a table. This is a much faster way of getting data in and out of a table than using 
> INSERT and SELECT.

Until recently you had to use a Java class to insert the data to PostgreSQL. But it's not always possible 
to fit data into some kind of model and you may need to write the data directly to PostgreSQL without 
defining a class.

That's why the library now comes with a new class called ``SimpleRowWriter``. 

## Bulk Writing to PostgreSQL with a SimpleRowWriter ##

Using the ``SimpleRowWriter`` is really easy. 

It requires you to define the Table structure using a ``SimpleRowWriter.Table``, that has the schema name, table name and column names:

```java
// Schema of the Table:
String schemaName = "sample";

// Name of the Table:
String tableName = "row_writer_test";

// Define the Columns to be inserted:
String[] columnNames = new String[] {
        "value_int",
        "value_text"
};

// Create the Table Definition:
SimpleRowWriter.Table table = new SimpleRowWriter.Table(schemaName, tableName, columnNames);

// Create the Writer:
SimpleRowWriter writer = new SimpleRowWriter(table);
```

Once created you are required to open the ``SimpleRowWriter`` by yourself using a ``PGConnection``:

```java
// ... open it:
writer.open(pgConnection);
```

To write a row to PostgreSQL you call the ``startRow`` method. It expects you to pass a ``Consumer<SimpleRow>`` into it, 
which defines what data to write to the row. The call to ``startRow`` is synchronized, so it is safe to be called from 
multiple threads.

```java
// ... write your data rows:
for(int rowIdx = 0; rowIdx < 10000; rowIdx++) {

    // ... using startRow and work with the row, see how the order doesn't matter:
    writer.startRow((row) -> {
        row.setText("value_text", "Hi");
        row.setInteger("value_int", 1);
    });

}
```

And to finish the COPY operation, you need to close the ``SimpleRowWriter``:

```java
// ... and make sure to close it:
writer.close();
```

### The Complete Example ###

[here]: https://github.com/bytefish/PgBulkInsert/blob/master/PgBulkInsert/src/test/java/de/bytefish/pgbulkinsert/rows/SimpleRowWriterTest.java

The complete code can be found [here]:

```java
public class SimpleRowWriterTest extends TransactionalTestBase {

    // ...
    
    @Test
    public void rowBasedWriterTest() throws SQLException {

        // Get the underlying PGConnection:
        PGConnection pgConnection = PostgreSqlUtils.getPGConnection(connection);

        // Schema of the Table:
        String schemaName = "sample";
        
        // Name of the Table:
        String tableName = "row_writer_test";

        // Define the Columns to be inserted:
        String[] columnNames = new String[] {
                "value_int",
                "value_text"
        };

        // Create the Table Definition:
        SimpleRowWriter.Table table = new SimpleRowWriter.Table(schemaName, tableName, columnNames);

        // Create the Writer:
        SimpleRowWriter writer = new SimpleRowWriter(table);

        // ... open it:
        writer.open(pgConnection);

        // ... write your data rows:
        for(int rowIdx = 0; rowIdx < 10000; rowIdx++) {

            // ... using startRow and work with the row, see how the order doesn't matter:
            writer.startRow((row) -> {
                row.setText("value_text", "Hi");
                row.setInteger("value_int", 1);
            });

        }

        // ... and make sure to close it:
        writer.close();

        // Now assert, that we have written 10000 entities:

        Assert.assertEquals(10000, getRowCount());
    }
}
```

## Conclusion ##

[@skunkiferous]: https://github.com/skunkiferous
[raising the issue]: https://github.com/bytefish/PgBulkInsert/issues/46

I think the ``SimpleRowWriter`` is a great addition to [PgBulkInsert], and many thanks to [@skunkiferous] for [raising the issue].