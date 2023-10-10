title: PostgreSQL Bulk Inserts with Java
date: 2016-02-04 21:16
tags: java, pgbulkinsert
category: java
slug: pgbulkinsert
author: Philipp Wagner
summary: This article introduces PgBulkInsert, which is a library for efficient bulk inserts to PostgreSQL.

[MIT License]: https://opensource.org/licenses/MIT
[COPY command]: http://www.postgresql.org/docs/current/static/sql-copy.html
[Npgsql documentation]: http://www.npgsql.org/doc/copy.html
[PgBulkInsert]: https://github.com/bytefish/PgBulkInsert

[PgBulkInsert] is a small Java 1.8 library for bulk inserts with PostgreSQL.

It provides a wrapper around the PostgreSQL [Copy command]:

> The [COPY command] is a PostgreSQL specific feature, which allows efficient bulk import or export of 
> data to and from a table. This is a much faster way of getting data in and out of a table than using 
> INSERT and SELECT.

[PgBulkInsert] is released with under terms of the [MIT License]:

* [https://github.com/bytefish/PgBulkInsert](https://github.com/bytefish/PgBulkInsert)

## PgBulkInsert ##

You can add the following dependencies to your ``pom.xml`` to include [PgBulkInsert] in your project:

```xml
<dependency>
	<groupId>de.bytefish</groupId>
	<artifactId>pgbulkinsert</artifactId>
	<version>2.1</version>
</dependency>
```

## Basic Usage ##

Imagine we want to bulk insert a large amount of persons into a PostgreSQL database. Each ``Person`` has a first name, a last name and a birthdate.

### Database Table ###

The table in the PostgreSQL database might look like this:

```sql
 CREATE TABLE sample.unit_test
(
    first_name text,
    last_name text,
    birth_date date
);
```

### Domain Model ###

The domain model in the application might look like this:

```java
private class Person {

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

### Implementing the Mapping ###

Then you have to implement the ``AbstractMapping<Person>``, which defines the mapping between the table and the domain model.

```java
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

### Using the Bulk Inserter ###

And finally we can write a Unit Test to insert ``100000`` Persons into the database. You can find the entire Unit Test on GitHub: [IntegrationTest.java](https://github.com/bytefish/PgBulkInsert/blob/master/PgBulkInsert/src/test/de/bytefish/pgbulkinsert/de/bytefish/pgbulkinsert/IntegrationTest.java). 

```java
@Test
public void bulkInsertPersonDataTest() throws SQLException {
    // Create a large list of Persons:
    List<Person> persons = getPersonList(100000);
    
    // Create the BulkInserter:
    PgBulkInsert<Person> bulkInsert = new PgBulkInsert<Person>(new PersonMapping());
    
    // Now save all entities of a given stream:
    bulkInsert.saveAll(PostgreSqlUtils.getPGConnection(connection), persons.stream());
    
    // And assert all have been written to the database:
    Assert.assertEquals(100000, getRowCount());
}

private List<Person> getPersonList(int numPersons) {
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
```