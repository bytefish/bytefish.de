title: TinyDgraphClient: A Dgraph Client for .NET
date: 2019-09-29 13:20
tags: Dgraph, dotnet
category: Dgraph
slug: tinydgraphclient
author: Philipp Wagner
summary: This article introduces TinyDgraphClient, which is a library for working with Dgraph from .NET.

[MIT License]: https://opensource.org/licenses/MIT
[DGraph Dart Client]: https://github.com/marceloneppel/dgraph
[TinyDgraphClient]: https://github.com/bytefish/TinyDgraphClient
[Dgraph]: https://dgraph.io/
[Protobuf Schema provided by the Dgraph Team]: https://github.com/dgraph-io/dgo/blob/master/protos/api.proto

I am currently working on a project using [Dgraph]:

> [Dgraph] is a horizontally scalable and distributed graph database, providing ACID transactions, 
> consistent replication and linearizable reads. It's built from ground up to perform for a rich 
> set of queries. Being a native graph database, it tightly controls how the data is arranged on 
> disk to optimize for query performance and throughput, reducing disk seeks and network 
> calls in a cluster.

For the project I want to have a [Dgraph] .NET client implementation, that is as close as possible 
to the [Protobuf Schema provided by the Dgraph Team]. The idea is to learn more about Dgraph and 
more importantly have a client, that is easy to update on changes to the Protobuf API.

[TinyDgraphClient] is a thin wrapper for the Dgraph API. It is based on the great Dgraph Dart 
and JavaScript implementations:

* [https://github.com/dgraph-io/dgraph-js](https://github.com/dgraph-io/dgraph-js)
* [https://github.com/marceloneppel/dgraph](https://github.com/marceloneppel/dgraph)

You can find more information about [Dgraph] here:

* [https://dgraph.io/](https://dgraph.io/)

## Installing TinyDgraphClient ##

You can use [NuGet](https://www.nuget.org) to install [TinyDgraphClient]. Run the following command 
in the [Package Manager Console](http://docs.nuget.org/consume/package-manager-console).

```
PM> Install-Package TinyDgraphClient
```

## Using the DGraphClient ##

### Create the Schema ###

```csharp
public static async Task Main()
{
    var client = new DGraphClient("127.0.0.1", 9080, ChannelCredentials.Insecure);

    // Drop All Data for Tests:
    await client.AlterAsync(new Operation { DropAll = true }, CancellationToken.None);

    // Create the Schema:
    await client.AlterAsync(new Operation { Schema = Query.Schema }, CancellationToken.None);
            
    // Insert Data:
    ...
}
```

### Run a Mutation ###

Running a Mutation should be done in a Transaction. The following example shows how to get a new ``Transaction`` from 
the ``DGraphClient`` and use it to perform a ``Mutation`` in Dgraph:

```csharp
// Get a new Transaction:
var transaction = client.NewTxn();

// Create a Mutation:
var mutation = new Mutation();

// Create NQuads to add to the mutation:
var nquads = new List<NQuad>();

nquads.Add(new NQuad { Subject = "subject", Predicate = "predicate", ObjectValue = new Value { StrVal = "value" } });

// Set the NQuads for the Mutation:
mutation.Set.AddRange(nquads);

// Tell Dgraph to commit this Mutation instantly:
mutation.CommitNow = true;

// And mutate the data:
await transaction.MutateAsync(mutation, cancellationToken);
```

## License ##

The library is released under terms of the [MIT License]:

* [https://github.com/bytefish/TinyDgraphClient](https://github.com/bytefish/TinyDgraphClient)
