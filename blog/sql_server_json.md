title: Generating JSON in Microsoft SQL Server 2012+
date: 2023-03-27 11:34
tags: csharp, sqlserver, dotnet, sql
category: csharp, sql, sqlserver
slug: sql_server_json
author: Philipp Wagner
summary: In this article we will learn how to return JSON data from a SQL Server 2012+ database.

EntityFramework Core is an amazing technical achievement and it's the recommended tool for data access 
with .NET. But there are alternative ways to query your data, that don't require you to go all-in 
on EntityFramework Core.

In this article we will learn how to return JSON data from a SQL Server 2012+ database using 
the `FOR JSON PATH` expression and learn how to query it in a C# application using the 
`SqlQuery` library.

All code can be found in a GitHub repository at:

* [https://codeberg.org/bytefish/SqlQueryMapper](https://codeberg.org/bytefish/SqlQueryMapper)

## Table of contents ##

[TOC]

## What we are going to build ##

Imagine we are building a subset of a larger application and we are managing the address 
of people. A `[Person]` has an `[Address]`, an `[Address]` is linked to a `[Person]` using 
the `[PersonAddress]`. An address can have many types like `Billing`, `Delivery` and so 
on, which is given in the `[AddressType]` table.

So we need to return a list of people with their current address details included. We can 
get all data required for the use case by joining the 4 tables. This would leave us with 
a flat result set and we would need additional mappings or a query materializer to put 
the result set into a nice object model.

But what if we could just return JSON like this from the SQL Server database?

This is what our query response is going to look like:

```json
{
  "@odata.context": "http://localhost/odata/Person",
  "value": [
    {
      "FullName": "Philipp Wagner",
      "PreferredName": "Philipp",
      "Addresses": [
        {
          "AddressLine1": "Billing Address Street 123",
          "AddressType": "Billing"
        },
        {
          "AddressLine1": "Home Address Street 456",
          "AddressType": "Home"
        }
      ]
    }
  ]
}
```

## Generating JSON with SQL Server: FOR JSON PATH  ##

We can easily generate the JSON response using a `FOR JSON PATH` expression, like this:

```sql
SELECT person.FullName, person.PreferredName,
    (SELECT address.AddressLine1, AddressLine2, AddressLine3, AddressLine4, address_type.Name AS [AddressType]
        FROM [Application].[PersonAddress] person_address
            INNER JOIN [Application].[Address] address ON person_address.AddressID = address.AddressID
            INNER JOIN [Application].[AddressType] address_type ON person_address.AddressTypeID = address_type.AddressTypeID
        WHERE 
            person_address.PersonID = person.PersonID
        FOR JSON PATH
    ) AS [Addresses]
FROM [Application].[Person] person
FOR JSON PATH
```

## Using SqlQueryMapper to Query for JSON  ##

We can then model the Response we want to return to the Client application:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AdoNetBasics.Tests.Queries
{
    /// <summary>
    /// Examples for JSON queries.
    /// </summary>
    public class JsonQueryTests : TransactionalTestBase
    {
        #region Sample Model

        /// <summary>
        /// OData Response model.
        /// </summary>
        /// <typeparam name="T">Returned Entity</typeparam>
        private class ODataResponse<T>
        {
            [JsonPropertyName("@odata.context")]
            public string? Type { get; set; }

            [JsonPropertyName("value")]
            public List<T> Value { get; set; } = new();
        }


        /// <summary>
        /// Models the Address.
        /// </summary>
        private class AddressDto
        {
            [JsonPropertyName("AddressLine1")]
            public string AddressLine1 { get; set; } = null!;

            [JsonPropertyName("AddressLine2")]
            public string? AddressLine2 { get; set; }

            [JsonPropertyName("AddressLine3")]
            public string? AddressLine3 { get; set; }

            [JsonPropertyName("AddressLine4")]
            public string? AddressLine4 { get; set; }

            [JsonPropertyName("AddressType")]
            public string AddressType { get; set; } = null!;
        }

        /// <summary>
        /// Models the Person.
        /// </summary>
        private class PersonDto
        {
            [JsonPropertyName("FullName")]
            public string FullName { get; set; } = null!;

            [JsonPropertyName("PreferredName")]
            public string PreferredName { get; set; } = null!;

            [JsonPropertyName("Addresses")]
            public List<AddressDto> Addresses { get; set; } = new();
        }

        #endregion Sample Model
    
    // ...
    
}
```

The idea is to get the JSON from the SQL Server and use `System.Text.Json.JsonSerializer` to deserialize the JSON result:

```csharp
ODataResponse<PersonDto> result = System.Text.Json.JsonSerializer.Deserialize<ODataResponse<PersonDto>>(jsonResult)!;
```

Let's create some test data, so we actually return something from the query:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AdoNetBasics.Tests.Queries
{
    /// <summary>
    /// Examples for JSON queries.
    /// </summary>
    public class JsonQueryTests : TransactionalTestBase
    {
        #region Sample Model

        // ...

        #endregion Sample Model

        #region Test Data

        private async Task InitializeSampleData(ISqlConnectionFactory connectionFactory)
        {
            var personService = new PersonService(connectionFactory);

            var user = new User
            {
                FullName = "Philipp Wagner",
                PreferredName = "Philipp",
                IsPermittedToLogon = true,
                LogonName = "philipp@test.localhost",
                HashedPassword = PasswordHasher.HashPassword("ThisIsASuperSecretPasswordUserForTests"),
            };

            await personService.CreateUserAsync(user, 1, default);

            var person = new Person
            {
                FullName = "Philipp Wagner",
                PreferredName = "Philipp",
                UserId = user.Id,
                LastEditedBy = 1
            };

            await personService.CreatePersonAsync(person, 1, default);

            // Create a Billing Address
            {
                var address = new Address
                {
                    AddressLine1 = "Billing Address Street 123",
                    City = "Billing Town",
                    Country = "Billing Country",
                };

                await personService.CreateAddressAsync(address, 1, default);

                var personAddress = new PersonAddress
                {
                    PersonId = person.Id,
                    AddressId = address.Id,
                    AddressTypeId = (int)AddressTypeEnum.Billing
                };

                await personService.CreatePersonAddressAsync(personAddress, 1, default);
            }
            
            // Create a Home Address
            {
                var address = new Address
                {
                    AddressLine1 = "Home Address Street 456",
                    City = "Home Town",
                    Country = "Home Country",
                };

                await personService.CreateAddressAsync(address, 1, default);

                var personAddress = new PersonAddress
                {
                    PersonId = person.Id,
                    AddressId = address.Id,
                    AddressTypeId = (int)AddressTypeEnum.Home
                };

                await personService.CreatePersonAddressAsync(personAddress, 1, default);
            }
        }

        #endregion Test Data
    }   
}
```

And we can now put it all together. You can see the SQL Query, that we came up with and the `SqlQuery#StreamAsync` method 
to get JSON result back. The Test also inspects the deserialized JSON to see, if everything has been read correctly:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AdoNetBasics.Connections;
using AdoNetBasics.Query;
using AdoNetBasics.Tests.Sample.Authentication;
using AdoNetBasics.Tests.Sample.Models;
using AdoNetBasics.Tests.Sample.Services;
using Microsoft.Extensions.Configuration;
using NUnit.Framework;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace AdoNetBasics.Tests.Queries
{
    /// <summary>
    /// Examples for JSON queries.
    /// </summary>
    public class JsonQueryTests : TransactionalTestBase
    {
        #region Sample Model

        // ...

        #endregion Sample Model

        #region Test Data

        // ...

        #endregion Test Data

        #region Tests

        [Test]
        public async Task JsonQuery_QueryForJson_Success()
        {
            // An ISqlConnectionFactory to create an opened SqlConnection.
            var connectionFactory = GetSqlServerConnectionFactory();

            await InitializeSampleData(connectionFactory);

            // A JSON Query using "FOR JSON PATH" to return the data exactely the way we need it:
            var sql = @"SELECT person.FullName, person.PreferredName,
                    (SELECT address.AddressLine1, AddressLine2, AddressLine3, AddressLine4, address_type.Name AS [AddressType]
                        FROM [Application].[PersonAddress] person_address
                            INNER JOIN [Application].[Address] address ON person_address.AddressID = address.AddressID
							INNER JOIN [Application].[AddressType] address_type ON person_address.AddressTypeID = address_type.AddressTypeID
                        WHERE 
                            person_address.PersonID = person.PersonID
                        FOR JSON PATH
                    ) AS [Addresses]
                FROM [Application].[Person] person
                FOR JSON PATH";

            // The JSON should be an OData Response, so we wrap it into an 
            // OData JSON response according to the OData specification:
            var options = new SqlQueryStreamOptions
            {
                Encoding = Encoding.UTF8,
                DefaultOutput = "[]",
                Prefix = @"{""@odata.context"":""http://localhost/odata/Person"",""value"":",
                Suffix = @"}"
            };

            // Now read the JSON Response from the SQL Server:
            string jsonResult = string.Empty;

            using (var connection = await connectionFactory.GetDbConnectionAsync(default).ConfigureAwait(false))
            {
                using (var textWriter = new StringWriter())
                {
                    // Fire off the SQL query to get the JSON response:
                    await new SqlQuery(connection).Sql(sql)
                        .StreamAsync(textWriter, options, default)
                        .ConfigureAwait(false);

                    jsonResult = textWriter.ToString();
                }
            }

            // Deserialize the Response into an ODataResponse<T> model:
            ODataResponse<PersonDto> result = System.Text.Json.JsonSerializer.Deserialize<ODataResponse<PersonDto>>(jsonResult)!;

            // And run some sanity tests:
            Assert.IsNotNull(result);

            Assert.AreEqual("http://localhost/odata/Person", result.Type);
            
            // Check ODataResponse value:
            {
                var value = result.Value;

                Assert.AreEqual(1, value.Count);

                // Check Person:
                {
                    var person = value[0];

                    Assert.AreEqual("Philipp Wagner", person.FullName);
                    Assert.AreEqual("Philipp", person.PreferredName);

                    // Check Addresses:
                    {
                        var addresses = person.Addresses
                            .OrderBy(x => x.AddressType)
                            .ToList();

                        Assert.AreEqual(2, result.Value[0].Addresses.Count);

                        Assert.AreEqual("Billing Address Street 123", result.Value[0].Addresses[0].AddressLine1);
                        Assert.AreEqual("Home Address Street 456", result.Value[0].Addresses[1].AddressLine1);
                    }
                }
            }
        }

        #endregion Tests

        #region Infrastructure 

        /// <summary>
        /// Builds an <see cref="SqlServerConnectionFactory"/>.
        /// </summary>
        /// <returns>An initialized <see cref="SqlServerConnectionFactory"/></returns>
        /// <exception cref="InvalidOperationException">Thrown when no Connection String "ApplicationDatabase" was found</exception>
        private SqlServerConnectionFactory GetSqlServerConnectionFactory()
        {
            var connectionString = _configuration.GetConnectionString("ApplicationDatabase");

            if (connectionString == null)
            {
                throw new InvalidOperationException($"No Connection String named 'ApplicationDatabase' found in appsettings.json");
            }

            return new SqlServerConnectionFactory(connectionString);
        }

        #endregion Infrastructure  
    }
}
```

And boom... all tests pass!

You can also use `SqlQuery#MapSingleAsync` with the `DbDataReader` callback like this:

```csharp
var jsonResult = await new SqlQuery(connection).Sql(sql)
        .MapSingleAsync(callback: (reader) => reader.GetString(0), default)
        .ConfigureAwait(false);
```

## Conclusion ##

And that's it for now!

In this article we have seen how to query a Microsoft SQL Server database for JSON data in just a few lines 
of code. By using the `FOR JSON PATH` expression, we can easily return data tailored to our specific use 
cases.
