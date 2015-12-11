title: TinySqlMapper
date: 2015-12-11 09:42
tags: c#, sql
category: c#, sql
slug: tinysqlmapper
author: Philipp Wagner
summary: This article introduces TinySqlMapper, which makes querying a database with .NET easy.

[PostgreSQL]: http://www.postgresql.org
[MIT License]: https://opensource.org/licenses/MIT
[TinySqlMapper]: https://github.com/bytefish/TinySqlMapper

It may be a surprise to read .NET articles on my site. A lot of articles in the past have 
dealt with Computer Vision and Linux, which are my passions. But I have worked in enterprise software 
development with .NET and C++ for the last years, and these posts are meant to fix some pain points.

[TinySqlMapper] was born out of frustration with overly complex frameworks to do simple mappings 
between the results of an SQL query and C# objects (POCO). The result is a high-performance, simple 
to use and simple to extend library.

I have the opinion, that a library should do only one thing and it should do it well.

## Obtaining TinySqlMapper ##

I have released [TinySqlMapper] under terms of the [MIT License]:

* [https://github.com/bytefish/TinySqlMapper](https://github.com/bytefish/TinySqlMapper)

You can also use the [NuGet](https://www.nuget.org) package. To install [TinySqlMapper], run the 
following command in the [Package Manager Console](http://docs.nuget.org/consume/package-manager-console).

```
PM> Install-Package TinySqlMapper
```

## Usage ##

The library provides a simple way to map the results of a SQL query to a Plain Old CLR Object (POCO), 
which simply is a C# object. The only class an application has to implement is a ``SqlQueryMapping``, 
which maps between the columns of your table and the domain objects.

So imagine we have a table with Users (this is PostgreSQL):

```sql
CREATE TABLE sample.unit_test
(
    user_id integer,
    name text
);
```

And populate the ``sample.unit_test`` table:

```sql
insert into sample.unit_test values (1, 'philipp');
insert into sample.unit_test values (2, 'wagner');
```

The domain model in the code probably looks like this:

```csharp
// Entity we want to map to:
private class User
{
    public int UserId { get; set; }

    public string Name { get; set; }
}
```

Now to map the query results, you simply create create a new ``SqlQueryMapping``:

```csharp
public class UserMapping : SqlQueryMapping<User>
{
    public UserMapping()
        : base()
    {
        MapColumn(x => x.UserId, "user_id");
        MapColumn(x => x.Name, "name");
    }
}
```

That's all. And now we can already read the entities with ``ReadAll`` method of the ``SqlQueryMapping``:

```csharp
[Test]
public void SqlQueryHelperBasicTest()
{
    var sqlQueryMapping = new UserMapping();

    using (var command = Connection.CreateCommand())
    {
        command.CommandText = "select * from sample.unit_test";

        using (var reader = command.ExecuteReader())
        {
            var users = sqlQueryMapping.ReadAll(reader).ToList();

            Assert.AreEqual(2, users.Count);

            Assert.IsNotNull(users.FirstOrDefault(x => x.UserId == 1 && x.Name == "philipp"));
            Assert.IsNotNull(users.FirstOrDefault(x => x.UserId == 2 && x.Name == "wagner"));
        }
    }
}
```
