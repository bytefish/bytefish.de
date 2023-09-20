title: Simplified Java Database Access with SqlMapper
date: 2016-02-15 20:41
tags: java, sql
category: sql
slug: database_access_using_sqlmapper
author: Philipp Wagner
summary: This article introduces SqlMapper, which is Java 1.8 library to map between a JDBC ResultSet and Java Beans.

[MIT License]: https://opensource.org/licenses/MIT
[SqlMapper]: https://codeberg.org/bytefish/SqlMapper
[ResultSet]: https://docs.oracle.com/javase/8/docs/api/java/sql/ResultSet.html
[NPoco]: https://github.com/schotime/NPoco/
[Dapper]: https://github.com/StackExchange/dapper-dot-net
[OrmLite]: https://github.com/ServiceStack/ServiceStack.OrmLite

.NET has a large amount of Micro ORMs ([Dapper], [NPoco], [OrmLite], ...) to access databases in a very 
simple way, while Java is lacking small libraries. [SqlMapper] is a wrapper over the JDBC [ResultSet], 
and makes it very easy to map between Java Beans and a database table:

* [https://codeberg.org/bytefish/SqlMapper](https://codeberg.org/bytefish/SqlMapper)

## Basic Usage ##

Imagine we want to read a list of Persons from a database, where each Person has a first name, last name and a 
birthdate.

### Database Table ###

The table in the database could look like this (PostgreSQL):

```
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

### Define the Mapping ###

All you have implement is the mapping between both, which is done with a ``ResultSetMapping``:

```java
public class PersonMap extends ResultSetMapping<Person>
{
    public PersonMap() {
        map("first_name", String.class, Person::setFirstName);
        map("last_name", String.class, Person::setLastName);
        map("birth_date", LocalDate.class, Person::setBirthDate);
    }
}
```

### Map ResultSet to an Entity ###

An ``SqlMapper`` is used to perform the actual mapping between a [ResultSet] and the Entities. It takes 
an ``IObjectCreator`` and an ResultSetMapping``. The ``IObjectCreator`` is a functional interface, that is 
used to instantiate a target object.

The ``SqlMapper.toEntity`` method returns a ``SqlMappingResult<TEntity>``. The ``SqlMappingResult<TEntity>`` 
holds either the populated target object or an error, which can be checked with the ``SqlMappingResult<TEntity>.isValid()`` 
method.

If the mapping was successful, the populated entity can be obtained by calling ``SqlMappingResult<TEntity>.getEntity()``.

```java
@Test
public void testToEntity() throws Exception {
    SqlMapper<Person> sqlMapper = new SqlMapper<>(() -> new Person(), new PersonMap());

    Person person0 = new Person();

    person0.firstName = "Philipp";
    person0.lastName = "Wagner";
    person0.birthDate = LocalDate.of(1986, 5, 12);

    insert(person0);

    ResultSet resultSet = selectAll();
    
    while (resultSet.next() ) {

        SqlMappingResult<Person> person = sqlMapper.toEntity(resultSet);

        Assert.assertEquals(true, person.isValid());

        Assert.assertEquals("Philipp", person.getEntity().get().getFirstName());
        Assert.assertEquals("Wagner", person.getEntity().get().getLastName());
        Assert.assertEquals(LocalDate.of(1986, 5, 12), person.getEntity().get().getBirthDate());
    }
}
```