title: Implementing a Spliterator for a JDBC ResultSet
date: 2016-02-15 18:41
tags: java, streams, spliterator
category: java
slug: resultset_spliterator
author: Philipp Wagner
summary: This article describes how to implement a spliterator for the Java ResultSet.

[MIT License]: https://opensource.org/licenses/MIT
[SqlMapper]: https://github.com/bytefish/SqlMapper
[Spliterator]: https://docs.oracle.com/javase/8/docs/api/java/util/Spliterator.html
[ResultSet]: https://docs.oracle.com/javase/8/docs/api/java/sql/ResultSet.html

Java 1.8 comes with the Streams API, which is a great feature for writing readable code. I recently needed to 
stream over a JDBC [ResultSet], which requires a custom [Spliterator].

According to the Java documentation a [Spliterator] is:

> An object for traversing and partitioning elements of a source. The source of elements covered by a Spliterator could be, 
> for example, an array, a Collection, an IO channel, or a generator function.

## ResultSetSpliterator ##

[AbstractSpliterator]: https://docs.oracle.com/javase/8/docs/api/java/util/Spliterators.AbstractSpliterator.html

The easiest way of implementing a custom [Spliterator] is to derive from an [AbstractSpliterator], which already implements 
most of the [Spliterator] interface. The intent of the ``ResultSetSpliterator<TEntity>`` iterator is to iterate over a given 
[ResultSet] and map the current result to an Entity with a [SqlMapper].

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.sqlmapper.iterator;

import de.bytefish.sqlmapper.SqlMapper;
import de.bytefish.sqlmapper.result.SqlMappingResult;

import java.sql.ResultSet;
import java.util.Spliterator;
import java.util.Spliterators;
import java.util.function.Consumer;

public class ResultSetSpliterator<TEntity> extends Spliterators.AbstractSpliterator<SqlMappingResult<TEntity>> {

    private final ResultSet resultSet;
    private final SqlMapper<TEntity> sqlMapper;

    public ResultSetSpliterator(final SqlMapper<TEntity> sqlMapper, final ResultSet resultSet) {
        super(Long.MAX_VALUE,Spliterator.ORDERED);

        this.sqlMapper = sqlMapper;
        this.resultSet = resultSet;
    }

    @Override
    public boolean tryAdvance(Consumer<? super SqlMappingResult<TEntity>> action) {
        if (next()) {
            action.accept(sqlMapper.toEntity(resultSet));
            return true;
        } else {
            return false;
        }
    }

    private boolean next() {
        try {
            return resultSet.next();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
```

## Using the ResultSetSpliterator ##

[StreamSupport]: https://docs.oracle.com/javase/8/docs/api/java/util/stream/StreamSupport.html

The [StreamSupport] class provides low-level utility methods for creating and manipulating streams. The ``StreamSupport.stream`` method makes it possible to create a new sequential or parallel Stream from a [Spliterator].

In the example I am also creating the [SqlMapper], which is not in the scope of this article, but it gives you a hint how to create the stream.

```csharp
@Test
public void testToEntityStream() throws Exception {
    // Number of persons to insert:
    int numPersons = 10000;
    // Insert the given number of persons:
    insert(numPersons);
    // Get all row of the Table:
    ResultSet resultSet = selectAll();
    // Create a SqlMapper, which maps between a ResultSet row and a Person entity:
    SqlMapper<Person> sqlMapper = new SqlMapper<>(() -> new Person(), new PersonMap());
    // Create the Stream using the StreamSupport class:
    Stream<SqlMappingResult<Person>> stream = StreamSupport.stream(new ResultSetSpliterator<>(sqlMapper, resultSet), false);
    // Collect the Results as a List:
    List<SqlMappingResult<Person>> result = stream.collect(Collectors.toList());
    // Assert the results:
    Assert.assertEquals(numPersons, result.size());
}
```