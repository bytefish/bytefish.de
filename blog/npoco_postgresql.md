title: NPoco with PostgreSQL
date: 2015-05-24 21:55
tags: csharp, sql
category: csharp
slug: npoco_postgresql
author: Philipp Wagner

[NPoco]: https://github.com/schotime/NPoco

[NPoco] is a great micro-ORM, that makes it really easy to work with a database in .NET. I needed to use 
it with PostgreSQL, so here is the initial test I wrote. Nothing spectacular, I just thought another tutorial 
doesn't hurt and it might get you started quicker.

## Preparing the Database  ##

First of all we need to create a user and database for this tutorial. 

The user in this tutorial is called ``philipp`` and the database is called ``sampledb``, you'll need 
these values for the connection string in C#.

```
PS C:\Users\philipp> psql -U postgres
psql (9.4.1)
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
postgres=# CREATE DATABASE sampledb
postgres-#   WITH OWNER philipp;
CREATE DATABASE
```

Next we'll create the Schema.

```
CREATE SCHEMA sample;
```

And then the Tables.

```
CREATE TABLE sample.address (
	address_id SERIAL PRIMARY KEY,
	street TEXT NOT NULL,
	house_no TEXT NOT NULL,
	city TEXT NOT NULL	
);

CREATE TABLE sample.person (
	person_id SERIAL PRIMARY KEY,
	firstname TEXT NOT NULL,
	lastname TEXT NOT NULL,
	age INTEGER NOT NULL,
	address_id INTEGER REFERENCES sample.address (address_id)
);
```

## NPoco ##

Now the C# side! 

We create a new library project and install the required libraries with [NuGet](https://www.nuget.org):

```
Install-Package NUnit
Install-Package Npgsql
Install-Package NPoco
```

Then we'll add a new ``App.config`` to the project, which registers Npgsql as a DbProvider and defines a connection string.

```xml
<?xml version="1.0" encoding="utf-8" ?>
<configuration>
  
  <system.data>
    <DbProviderFactories>
      <add name="Npgsql Data Provider" invariant="Npgsql" support="FF" description=".Net Framework Data Provider for Postgresql Server" type="Npgsql.NpgsqlFactory, Npgsql" />
    </DbProviderFactories>
  </system.data>

  <connectionStrings>
    <add name="ApplicationConnectionString" connectionString="Server=127.0.0.1;Port=5432;Database=sampledb;User Id=philipp;Password=test_pwd;" providerName="Npgsql" />
  </connectionStrings>
  
</configuration>
```

And then we can write a Unit Test to work with NPoco. The test shows how to define the POCOs, their Mappers with the ``NPoco.FluentMappings`` and register them with the ``DatabaseFactory``.

```csharp
using NPoco;
using NPoco.FluentMappings;
using NUnit.Framework;

namespace NPoco.Postgresql.Test
{
    [TestFixture]
    public class PostgresqlNPocoTest
    {
        public class Person
        {
            public int PersonId { get; set; }
            public int AddressId { get; set; }
            public string FirstName { get; set; }
            public string LastName { get; set; }
            public int Age { get; set; }

            public override string ToString()
            {
                return string.Format("Person, PersonId: {0}, FirstName: {1}, LastName: {2}, Age: {3}",
                    PersonId, FirstName, LastName, Age);
            }
        }

        public class Address
        {
            public int AddressId { get; set; }
            public string Street { get; set; }
            public string HouseNo { get; set; }
            public string City { get; set; }

            public override string ToString()
            {
                return string.Format("Address, AddressId: {0}, Street: {1}, HouseNo: {2}, City: {3}",
                    AddressId, Street, HouseNo, City);
            }
        }

        public class PersonMap : Map<Person>
        {
            public PersonMap()
            {
                PrimaryKey(p => p.PersonId, autoIncrement: true)
                .TableName("sample.person")
                .Columns(x =>
                {
                    x.Column(p => p.PersonId).WithName("person_id");
                    x.Column(p => p.AddressId).WithName("address_id");
                    x.Column(p => p.FirstName).WithName("firstname");
                    x.Column(p => p.LastName).WithName("lastname");
                    x.Column(p => p.Age).WithName("age");
                });
            }
        }

        public class AddressMap : Map<Address>
        {
            public AddressMap()
            {
                PrimaryKey(a => a.AddressId, autoIncrement: true)
                .TableName("sample.address")
                .Columns(x =>
                {
                    x.Column(a => a.AddressId).WithName("address_id");
                    x.Column(a => a.Street).WithName("street");
                    x.Column(a => a.HouseNo).WithName("house_no");
                    x.Column(a => a.City).WithName("city");
                });
            }
        }

        private DatabaseFactory databaseFactory;

        [SetUp]
        public void SetUp()
        {
            DatabaseFactoryConfigOptions options = new DatabaseFactoryConfigOptions();

            options.Database = () => new Database("ApplicationConnectionString");
            options.PocoDataFactory = FluentMappingConfiguration.Configure(new PersonMap(), new AddressMap());

            databaseFactory = new DatabaseFactory(options);
        }

        [Test]
        public void InsertAndQueryPersonTest()
        {
            using (var db = databaseFactory.GetDatabase())
            {
                using (var tran = db.GetTransaction())
                {
                    // Clean existing items:
                    db.Execute("delete from sample.address");
                    db.Execute("delete from sample.person");

                    // Insert data:
                    var address = new Address()
                    {
                        Street = "Fakestreet",
                        HouseNo = "123",
                        City = "Faketown"
                    };
                    db.Insert(address);

                    var person = new Person()
                    {
                        FirstName = "Philipp",
                        LastName = "Wagner",
                        Age = 10,
                        AddressId = address.AddressId
                    };
                    db.Insert(person);
                    
                    // Query data:
                    Person resultPerson = db.SingleById<Person>(person.PersonId);
                    Address resultAddress = db.SingleById<Address>(address.AddressId);

                    // Check data:
                    Assert.AreEqual(person.FirstName, resultPerson.FirstName);
                    Assert.AreEqual(person.LastName, resultPerson.LastName);
                    Assert.AreEqual(person.Age, resultPerson.Age);
                    Assert.AreEqual(address.AddressId, resultPerson.AddressId);

                    Assert.AreEqual(address.Street, resultAddress.Street);
                    Assert.AreEqual(address.HouseNo, resultAddress.HouseNo);
                    Assert.AreEqual(address.City, resultAddress.City);
                }
            }
        }
    }
}
```

And that's it! [NPoco] provides a lot more functionality of course, for more examples see the [NPoco wiki](https://github.com/schotime/NPoco/wiki). 