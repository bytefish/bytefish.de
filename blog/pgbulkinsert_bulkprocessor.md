title: Working with a BulkProcessor in PgBulkInsert 
date: 2016-06-19 12:43
tags: java, postgresql, pgbulkinsert
category: java
slug: pgbulkinsert_bulkprocessor
author: Philipp Wagner
summary: This article shows how to work with a BulkProcessor in PgBulkInsert.

[PgBulkInsert] is a Java library for Bulk Inserts to PostgreSQL. It implements the Binary COPY Protocol of PostgreSQL 
for providing highly efficient inserts to a table. 

> The [COPY command] is a PostgreSQL specific feature, which allows efficient bulk import or export of 
> data to and from a table. This is a much faster way of getting data in and out of a table than using 
> INSERT and SELECT.

Now actually integrating bulk inserts into existing applications can be tricky. I know this from my professional 
work, because you often don't want to deal with batching of entities or you can't obscure existing interfaces.

This is where the ``BulkProcessor`` of [PgBulkInsert] fits in.

The BulkProcessor provides a simple interface, which flushes bulk operations automatically based on the number 
of entities or after a given time period. 

## PgBulkInsert ##

[PgBulkInsert] is released under terms of the MIT License:

* [https://codeberg.org/bytefish/PgBulkInsert](https://codeberg.org/bytefish/PgBulkInsert)

You can add the following dependencies to your ``pom.xml`` to include [PgBulkInsert] in your project:

```xml
<dependency>
	<groupId>de.bytefish</groupId>
	<artifactId>pgbulkinsert</artifactId>
	<version>2.1</version>
</dependency>
```

## BulkProcessor ##

Imagine we want to bulk insert a large amount of persons into a PostgreSQL database using a ``BulkProcessor``. 

Each ``Person`` has a first name, a last name and a birthdate.

### Database Table ###

The table in the PostgreSQL database might look like this:

```sql
CREATE TABLE sample.person_example
(
    first_name text,
    last_name text,
    birth_date date
);
```

### Domain Model ###

The domain model in the application might look like this:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package model;

import java.time.LocalDate;

public class Person {

    private String firstName;

    private String lastName;

    private LocalDate birthDate;

    public Person() {}

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public LocalDate getBirthDate() {
        return birthDate;
    }

    public void setBirthDate(LocalDate birthDate) {
        this.birthDate = birthDate;
    }

}
```

### Bulk Inserter ###

Then the mapping between the database table and the domain model has to defined. This is done by implementing the abstract base class ``AbstractMapping<TEntity>``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package mapping;

import model.Person;

import de.bytefish.pgbulkinsert.mapping.AbstractMapping;

public class PersonMapping extends AbstractMapping<Person>
{
    public PersonMapping() {
        super("sample", "unit_test");

        mapString("first_name", Person::getFirstName);
        mapString("last_name", Person::getLastName);
        mapDate("birth_date", Person::getBirthDate);
    }
}

```

### Connection Pooling (with DBCP2) ###

The ``BulkProcessor`` needs a way to obtain a ``Connection`` for the database access. That's why the ``BulkProcessor`` takes a factory for creating connections. 

I don't like reinventing the wheel, so in my projects I simply use the great [DBCP2] project for handling database connections.

You can add the following dependencies to your ``pom.xml`` to include [DBCP2] in your project:

```xml
<dependency>
	<groupId>org.apache.commons</groupId>
	<artifactId>commons-dbcp2</artifactId>
	<version>2.0.1</version>
</dependency>
```

The Connection Factory for the ``BulkProcessor`` can now be implemented.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package connection;

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

### Application ###

And finally we can implement the sample application using the ``BulkProcessor``. The ``BulkProcessor`` takes a ``BulkWriteHandler``, which 
handles the writing of a list of batched entities. The ``BulkProcessor`` is thread-safe, so it can safely be used from multiple threads.

The example writes ``1000`` Person entities to the database, using a Bulk Size of ``100`` entities.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package app;

import connection.PooledConnectionFactory;
import de.bytefish.pgbulkinsert.PgBulkInsert;
import de.bytefish.pgbulkinsert.pgsql.processor.BulkProcessor;
import de.bytefish.pgbulkinsert.pgsql.processor.handler.BulkWriteHandler;
import mapping.PersonMapping;
import model.Person;

import java.net.URI;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public class BulkProcessorApp {

    public static void main(String[] args) throws Exception {
        // Create the Bulk Insert:
        PgBulkInsert<Person> bulkInsert = new PgBulkInsert<Person>(new PersonMapping());
        // Database to connect to:
        URI databaseUri = URI.create("postgres://philipp:test_pwd@127.0.0.1:5432/sampledb");
        // Bulk Actions after which the batched entities are written:
        final int bulkSize = 100;
        // Create a new BulkProcessor:
        try(BulkProcessor<Person> bulkProcessor = new BulkProcessor<>(new BulkWriteHandler<>(bulkInsert, new PooledConnectionFactory(databaseUri)), bulkSize)) {
            // Create some Test data:
            List<Person> thousandPersons = getPersonList(1000);
            // Now process them with the BulkProcessor:
            for (Person p : thousandPersons) {
                bulkProcessor.add(p);
            }
        }
    }

    private static List<Person> getPersonList(int numPersons) {
        List<Person> persons = new ArrayList<>();

        for (int pos = 0; pos < numPersons; pos++) {
            Person p = new Person();

            p.setFirstName("Philipp");
            p.setLastName("Wagner");
            p.setBirthDate(LocalDate.of(1986, 5, 12));

            persons.add(p);
        }

        return persons;
    }

}
```

[COPY command]: http://www.postgresql.org/docs/current/static/sql-copy.html
[DBCP2]: https://commons.apache.org/proper/commons-dbcp/
[PgBulkInsert]: https://codeberg.org/bytefish/PgBulkInsert
[JTinyCsvParser]: https://codeberg.org/bytefish/JTinyCsvParser