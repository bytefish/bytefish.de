title: Using the Neo4j .NET 4.0 Driver
date: 2020-04-04 20:13
tags: dotnet, netcore
category: dotnet
slug: neo4j_dotnet_client
author: Philipp Wagner
summary: Using the Neo4j .NET Driver.

I am playing around with Neo4j for a small project and it's been a while since using Neo4j. The latest 
Neo4j 4.0 came with some changes to the .NET API and my previous approaches to writing data seemed overly 
complicated to me.

Starting with Neo4j in .NET is quite easy, the Neo4j .NET Driver README shares a Minimal Viable Snippet at:

* [https://github.com/neo4j/neo4j-dotnet-driver#minimum-viable-snippet](https://github.com/neo4j/neo4j-dotnet-driver#minimum-viable-snippet)

It looks like this:

```csharp
IDriver driver = GraphDatabase.Driver("neo4j://localhost:7687", AuthTokens.Basic("username", "pasSW0rd"));

IAsyncSession session = driver.AsyncSession(o => o.WithDatabase("neo4j"));

try
{
    IResultCursor cursor = await session.RunAsync("CREATE (n) RETURN n");
    await cursor.ConsumeAsync();
}
finally
{
    await session.CloseAsync();
}

await driver.CloseAsync();
```

In the code we can see, that the Session API slightly changed from 3.0 to 4.0. It is not sufficient to 
use ``RunAsync(...)`` to execute the Cypher statement, but we also need to use ``ConsumeAsync(...)`` 
to evaluate the statement.

It's somewhat tedious to always write these lines to execute and consume a result, so I first wrote 
a small extension method:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Neo4j.Driver;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace TinyQuestionnaire.Graph.Extensions
{
    public static class AsyncSessionExtensions
    {
        public static async Task<IResultSummary> RunAndConsumeAsync(this IAsyncSession session, string query, object parameters)
        {
            var cursor = await session
                .RunAsync(query, parameters)
                .ConfigureAwait(false);

            return await cursor
                .ConsumeAsync()
                .ConfigureAwait(false);
        }

        public static async Task<IResultSummary> RunAndConsumeAsync(this IAsyncSession session, string query, IDictionary<string, object> parameters)
        {
            var cursor = await session
                .RunAsync(query, parameters)
                .ConfigureAwait(false);

            return await cursor
                .ConsumeAsync()
                .ConfigureAwait(false);
        }
    }
}
```

So the next question is: How do we pass the parameters into the ``RunAndConsumeAsync`` method? Apparently I have overloaded a method 
for passing a ``IDictionary<string, object>`` and for an ``object``. It's because I want to either pass a ``dynamic`` as parameters or 
serialize an object into an ``IDictionary<string, object>``, where I can easily access parameters by name and even nest them.

In my previous uses of the Neo4j Driver I used Newtonsoft JSON to turn a complex object into an ``IDictionary<string, object>`` using 
a custom converter. But .NET Core 3.0 now comes with its own Json Serializer in the ``System.Text.Json`` namespace and my previous code 
isn't usable anymore.

And while porting the code I wondered... Why all this magic? 

All my projects follow a simple rule: 

> Get it working first and then improve upon.

## An Example ##

Imagine we want to create a *Person* Node in Neo4j, where each *Person* also has an *Address* Node. Instead of relying on 
a custom converter, I am just using adding a method ``AsDictionary`` in the model. You could also shift this code somewhere 
else.

All Properties also have a ``JsonPropertyName`` attribute, so we can later deserialize results to objects again.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TinyQuestionnaire.Graph.Model
{
    public class Person
    {
        [JsonPropertyName("id")]
        public string Id { get; set; }

        [JsonPropertyName("firstName")]
        public string FirstName { get; set; }

        [JsonPropertyName("lastName")]
        public string LastName { get; set; }

        [JsonPropertyName("gender")]
        public string Gender { get; set; }

        [JsonPropertyName("birthDate")]
        public DateTime BirthDate { get; set; }

        [JsonPropertyName("phone1")]
        public string Phone1 { get; set; }

        [JsonPropertyName("phone2")]
        public string Phone2 { get; set; }

        [JsonPropertyName("phone3")]
        public string Phone3 { get; set; }

        [JsonPropertyName("email")]
        public string Email { get; set; }

        [JsonPropertyName("address")]
        public Address Address { get; set; }

        public Dictionary<string, object> AsDictionary()
        {
            return new Dictionary<string, object>
            {
                { "id", Id },
                { "firstName", FirstName },
                { "lastName",  LastName },
                { "gender", Gender },
                { "birthDate", BirthDate },
                { "phone1", Phone1 },
                { "phone2", Phone2 },
                { "phone3", Phone3 },
                { "email", Email },
                { "address", Address?.AsDictionary() },
            };
        }
    }
}
```

And we can see, that the ``Address`` object also follows the same pattern.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace TinyQuestionnaire.Graph.Model
{
    public class Address
    {
        [JsonPropertyName("name1")]
        public string Name1 { get; set; }

        [JsonPropertyName("name2")]
        public string Name2 { get; set; }

        [JsonPropertyName("street")]
        public string Street { get; set; }

        [JsonPropertyName("zipCode")]
        public string ZipCode { get; set; }

        [JsonPropertyName("city")]
        public string City { get; set; }

        [JsonPropertyName("state")]
        public string State { get; set; }

        [JsonPropertyName("country")]
        public string Country { get; set; }

        public IDictionary<string, object> AsDictionary()
        {
            return new Dictionary<string, object>
            {
                { "name1", Name1 },
                { "name2", Name2 },
                { "street", Street },
                { "zipCode", ZipCode },
                { "city", City },
                { "state", State },
                { "country", Country },
            };
        }
    }
}
```

And now we connect all things by writing a small client that uses the Neo4j ``IDriver``. In the Cypher Query you 
can see, that I am addressing the values by using statements like ``$person.address.city``. This is possible, 
because we have created nested Dictionaries for the Objects:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Neo4j.Driver;
using System;
using System.Threading.Tasks;
using TinyQuestionnaire.Graph.Extensions;
using TinyQuestionnaire.Graph.Model;

namespace TinyQuestionnaire.Graph
{
    public class TinyQuestionnaireClient : IDisposable
    {
        public readonly IDriver Driver;

        private readonly string database;

        public TinyQuestionnaireClient(string url, string database, string username, string password)
        {
            this.database = database;
            this.Driver = GraphDatabase.Driver(url, AuthTokens.Basic(username, password));
        }

        public async Task CreatePersonAsync(Person person)
        {
            var session = CreateAsyncSession();

            try
            {
                var query = @"
                    MERGE (person:Person { email: $person.email })
                    SET person.firstName = $person.firstName,
                        person.lastname = $person.lastName,
                        person.email = $person.email,
                        person.phone1 = $person.phone1,
                        person.phone2 = $person.phone1,
                        person.phone3 = $person.phone1
                    MERGE (city:City { name: COALESCE($person.address.city, 'N/A'), country: COALESCE($person.address.country, 'N/A') })
                    SET city.zipCode = $person.address.zipCode
                    MERGE (state:State { name: COALESCE($person.address.state, 'N/A') })
                    MERGE (country:Country { name: COALESCE($person.address.country, 'N/A') })
                    MERGE (address:Address { street: COALESCE($person.address.street, 'N/A'), city: coalesce($person.address.city, 'N/A'), country:  coalesce($person.address.country, 'N/A') })
                    MERGE (person)-[:IN_CITY]->(city)
                    MERGE (person)-[:IN_STATE]->(state)
                    MERGE (person)-[:IN_COUNTRY]->(country)
                    MERGE (person)-[:HAS_ADDRESS]->(address)
                    MERGE (city)-[:IN_COUNTRY]->(country)";

                var parameters = new
                {
                    person = person.AsDictionary()
                };

                await session.RunAndConsumeAsync(query, parameters);
            }
            finally
            {
                await session.CloseAsync();
            }
        }

        public IAsyncSession CreateAsyncSession()
        {
            return Driver.AsyncSession(o => o.WithDatabase(database));
        }

        public void Dispose()
        {
            Driver?.Dispose();
        }
    }
}
```

## Conclusion ##

And that's it. Is this approach perfect? Oh it's not for sure:

* It's not really elegant to write the parameters names by hand.
* It's probably not the cleanest thing to hardcode Cypher queries in code.
* It's not easy to debug errors, when you mistyped a parameter name.
* It is a problem when parameters are null in ``MERGE`` statements.

But this approach will yield results quickly without any magic involved and you'll stick to the official Neo4j .NET driver.

I wasted so much of my lifetime with ORM libraries... I rather write queries in code, than fight leaky abstractions.
