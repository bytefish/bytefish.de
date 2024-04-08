title: Implementing an Outbox Pattern with Postgres and .NET
date: 2024-04-06 12:26
tags: postgres, dotnet
category: dotnet
slug: outbox_events_postgres_dotnet
author: Philipp Wagner
summary: This article shows how to implement an Outbox pattern using Postgres and .NET.

[gitclub-dotnet]: https://github.com/bytefish/gitclub-dotnet

In my last article you have seen how to use PostgreSQL Logical Replication feature to implement a 
Change Data Capture (CDC) mechanism. It works great to subscribe to changes in our Postgres database 
and by using the Logical Replication feature we have an At-least-once delivery of messages.

We can now build upon this implementation to implement an Outbox Pattern:

> The application persists data to an outbox table in a database. Once the data has been persisted another 
> application or process can read from the outbox table and use that data to perform an operation which 
> it can retry upon failure until completion. The outbox pattern ensures that a message was sent 
> (e.g. to a queue) successfully at least once.

All code can be found in a Git Repository at:

* [https://github.com/bytefish/gitclub-dotnet](https://github.com/bytefish/gitclub-dotnet)

## Table of contents ##

[TOC]

## The Problem ##

I have been exploring Relationship-based Access Control in the past months, because I think it's a 
great way to provide Fine Grained Authorization (FGA) and is a key component to authorize data access 
with GraphQL or OData.

At the very beginning I thought I could easily implement a simplified version of the Google Zanzibar 
algorithms myself. Why? Because I don't need the global scalability of Google, and while I've learnt 
a lot by modeling the problem... I realized, that it's way out of my league.

So I've turned to OpenFGA, which is a Google Zanzibar implementation backed by Okta, described as ...

> [...] an open-source authorization solution that allows developers to build granular access control 
> using an easy-to-read modeling language and friendly APIs.

Now that we have decoupled Application and Authorization, we are distributed. It's 100% certain either 
of the services will be down. The approach of writing relation tuples to both the application database 
and OpenFGA database will fail. This can lead to inconsistencies, and these inconsistencies will be very, 
very painful to debug. 

I can feel the angry customer breathing down my neck. 

This problems is commonly known as a "Dual Write Problem". A "Dual Write" occurs, when you are changing 
data in (at least) two distinct systems, without having a shared transaction. In our case it occurs, when 
writing to both, our Applications database and the OpenFGA database.

The Outbox Pattern is an elegant way to reach Eventual Consistency between both systems, so let's take 
a look how we can implement it! This is an article, that goes all the way from Potgres Logical Replication 
to the "Outbox Pattern" implementation and using it in the sample [gitclub-dotnet] application.

## Configuring Postgres ##

### Enable Logical Replication in the postgres.conf ###

We add a file `postgres/postgres.conf` next to our `docker-compose.yaml`. In the configuration 
we are enabling a logical replication by setting the following properties:

```ini
#------------------------------------------------------------------------------
# WRITE-AHEAD LOG
#------------------------------------------------------------------------------

# - Settings -
wal_level = logical

#------------------------------------------------------------------------------
# REPLICATION
#------------------------------------------------------------------------------

max_wal_senders = 10
max_replication_slots = 10
```

### Setting the postgres.conf in Docker Compose ###

In the `docker-compose.yaml` we need to mount the `postgres/postgres.conf` in our container and start postgres with the mounted config file.

```yaml
version: '3.8'

networks:
  openfga:

services:
  postgres:
    image: postgres:16
    container_name: postgres
    networks:
      - openfga
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - "./postgres/postgres.conf:/usr/local/etc/postgres/postgres.conf"
    command: "postgres -c config_file=/usr/local/etc/postgres/postgres.conf"
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 5s
      timeout: 5s
      retries: 5
      
```

If you are now running a `docker-compose up` you should have a Postgres 16 instance with Logical Replication enabled.

## Subscribing to Postgres Logical Replication with .NET ##

The Postgres Logical Replication Protocol and the Data Message Flow is described at:

* [https://www.postgresql.org/docs/current/protocol-logical-replication.html](https://www.postgresql.org/docs/current/protocol-logical-replication.html)

It starts with ...

> The logical replication protocol sends individual transactions one by one. This means that all 
> messages between a pair of Begin and Commit messages belong to the same transaction. [...] Every 
> sent transaction contains zero or more DML messages (Insert, Update, Delete).

So we start by defining a `ReplicationTransaction`, which contains a list of `DataChangeEvent`, that occured inside the transaction:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace GitClub.Infrastructure.Postgres.Wal.Models
{
    /// <summary>
    /// A Transaction sent by Postgres with all related DataChange Events.
    /// </summary>
    public record ReplicationTransaction
    {
        public List<DataChangeEvent> ReplicationDataEvents { get; } = [];
    }
}
```

> Before the first DML message for a given relation OID, a Relation message will be sent, describing the schema of 
> that relation. [...] Subsequently, a new Relation message will be sent if the relation's definition has changed 
> since the last Relation message was sent for it. (The protocol assumes that the client is capable of remembering 
> this metadata for as many relations as needed.)

So we add a `Relation`, that holds the metadata for a given relation.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace GitClub.Infrastructure.Postgres.Wal.Models
{
    /// <summary>
    /// Postgres send a Relation Message during the Logical Replication.
    /// </summary>
    public record Relation
    {
        /// <summary>
        /// Gets or sets the Id of the Relation.
        /// </summary>
        public required uint RelationId { get; set; }

        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public required string? Namespace { get; set; }

        /// <summary>
        /// Gets or sets the Name of the Relation.
        /// </summary>
        public required string RelationName { get; set; }

        /// <summary>
        /// Gets or sets the Server Clock time.
        /// </summary>
        public required DateTime ServerClock { get; set; }

        /// <summary>
        /// Gets or sets the Column Names.
        /// </summary>
        public required string[] ColumnNames { get; set; }
    }
}
```

We can then define the Replication Events sent by the Logical Replication protocol.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace GitClub.Infrastructure.Postgres.Wal.Models
{
    /// <summary>
    /// Emitted, when a change to the Postgres tables occurs.
    /// </summary>
    [JsonPolymorphic(TypeDiscriminatorPropertyName = "$type")]
    [JsonDerivedType(typeof(InsertDataChangeEvent), typeDiscriminator: "insert")]
    [JsonDerivedType(typeof(DefaultUpdateDataChangeEvent), typeDiscriminator: "default_update")]
    [JsonDerivedType(typeof(FullUpdateDataChangeEvent), typeDiscriminator: "full_update")]
    [JsonDerivedType(typeof(KeyDeleteDataChangeEvent), typeDiscriminator: "key_delete")]
    [JsonDerivedType(typeof(FullDeleteDataChangeEvent), typeDiscriminator: "full_delete")]
    public abstract record DataChangeEvent
    {
        /// <summary>
        /// Gets or sets the Relation.
        /// </summary>
        public required Relation Relation { get; set; }
    }
    
    /// <summary>
    /// An insert event includes the new values.
    /// </summary>
    public record InsertDataChangeEvent : DataChangeEvent
    {
        /// <summary>
        /// Gets or sets the new column values.
        /// </summary>
        public required IDictionary<string, object?> NewValues { get; set; }
    }
    
    /// <summary>
    /// A default update event only contains the new values.
    /// </summary>
    public record DefaultUpdateDataChangeEvent : DataChangeEvent
    {
        public required IDictionary<string, object?> NewValues { get; set; }
    }
    
    /// <summary>
    /// A full update event contains the old and the new values.
    /// </summary>
    public record FullUpdateDataChangeEvent : DataChangeEvent
    {
        /// <summary>
        /// Gets or sets the new column values.
        /// </summary>
        public required IDictionary<string, object?> NewValues { get; set; }

        /// <summary>
        /// Gets or sets the old column values.
        /// </summary>
        public required IDictionary<string, object?> OldValues { get; set; }
    }
    
    /// <summary>
    /// A key delete event contains only the keys, that have been deleted.
    /// </summary>
    public record KeyDeleteDataChangeEvent : DataChangeEvent
    {
        /// <summary>
        /// Gets or sets the keys having been deleted.
        /// </summary>
        public required IDictionary<string, object?> Keys { get; set; }
    }
    
    /// <summary>
    /// A delete event contains the old column values.
    /// </summary>
    public record FullDeleteDataChangeEvent : DataChangeEvent
    {
        /// <summary>
        /// Gets or sets the old column values.
        /// </summary>
        public required IDictionary<string, object?> OldValues { get; set; }
    }    
}
```

### Streaming Transactions with their Data Change Events ###

As of now we'll need at least the database to connect to, and the names of the Publication and Replication Slot. For 
lack of a better name I put them into a `PostgresReplicationClientOptions` class.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GitClub.Hosted;

namespace GitClub.Infrastructure.Postgres.Wal
{
    /// <summary>
    /// Options to configure the <see cref="PostgresNotificationProcessor"/>.
    /// </summary>
    public class PostgresReplicationClientOptions
    {
        /// <summary>
        /// Gets or sets the ConnectionString for the Replication Stream.
        /// </summary>
        public required string ConnectionString { get; set; }

        /// <summary>
        /// Gets or sets the PublicationName the Service is listening to.
        /// </summary>
        public required string PublicationName { get; set; }

        /// <summary>
        /// Gets or sets the ReplicationSlot the Service is listening to.
        /// </summary>
        public required string ReplicationSlotName { get; set; }
    }
}
```

The `PostgresReplicationClient` now uses the Npgsql Logical Replication Protocol implementation to stream `ReplicationTransactions` to 
the consumer of the service. There are some things to be desired, but this is a good starting point I think.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GitClub.Infrastructure.Logging;
using GitClub.Infrastructure.Postgres.Wal.Models;
using Microsoft.Extensions.Options;
using Npgsql;
using Npgsql.Replication;
using Npgsql.Replication.PgOutput;
using Npgsql.Replication.PgOutput.Messages;
using System.Collections.Concurrent;
using System.Runtime.CompilerServices;

namespace GitClub.Infrastructure.Postgres.Wal
{
    /// <summary>
    /// This Client subscribes to Logical Replication messages sent by a Postgres database.
    /// </summary>
    public class PostgresReplicationClient
    {
        /// <summary>
        /// Logger.
        /// </summary>
        private readonly ILogger _logger;

        /// <summary>
        /// Options to configure the Wal Receiver.
        /// </summary>
        private readonly PostgresReplicationClientOptions _options;

        /// <summary>
        /// Creates a new <see cref="PostgresReplicationClient" />.
        /// </summary>
        /// <param name="logger">Logger to log messages</param>
        /// <param name="options">Options to configure the service</param>
        public PostgresReplicationClient(ILogger logger, IOptions<PostgresReplicationClientOptions> options)
        {
            _logger = logger;
            _options = options.Value;
        }

        /// <summary>
        /// Instructs the server to start the Logical Streaming Replication Protocol (pgoutput logical decoding 
        /// plugin), starting at WAL location walLocation or at the slot's consistent point if walLocation isn't 
        /// specified. The server can reply with an error, for example if the requested section of the WAL has 
        /// already been recycled.
        /// </summary>
        /// <param name="cancellationToken">Cancellation Token to stop the Logical Replication</param>
        /// <returns>Replication Transactions</returns>
        /// <exception cref="InvalidOperationException">Thrown when a replication message can't be handled</exception>
        public async IAsyncEnumerable<ReplicationTransaction> StartReplicationAsync([EnumeratorCancellation] CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            // Connection to subscribe to the logical replication slot. We are 
            // using NodaTime, but LogicalReplicationConnection has no TypeMappers, 
            // so we need to add them globally...
#pragma warning disable CS0618 // Type or member is obsolete
            NpgsqlConnection.GlobalTypeMapper.UseNodaTime();
#pragma warning restore CS0618 // Type or member is obsolete

            // This is the only way to create the Replication Connection, I have found no 
            // way to utilize the NpgsqlDataSource for it. There might be a way though.
            var replicationConnection = new LogicalReplicationConnection(_options.ConnectionString);

            // Open the Connection.
            await replicationConnection
                .Open(cancellationToken)
                .ConfigureAwait(false);

            // Reference to the Publication.
            var replicationPublication = new PgOutputReplicationOptions(_options.PublicationName, protocolVersion: 1, binary: true);

            // Reference to the Replication Slot.
            var replicationSlot = new PgOutputReplicationSlot(_options.ReplicationSlotName);

            // Postgres expects us to cache all relations.
            var relations = new ConcurrentDictionary<uint, Relation>();

            // The current transaction, which will be set, when we receive the first commit message.
            ReplicationTransaction transaction = null!;

            await foreach (var message in replicationConnection
                .StartReplication(replicationSlot, replicationPublication, cancellationToken)
                .ConfigureAwait(false))
            {
                _logger.LogDebug("Received Postgres WAL Message (Type = {WalMessageType}, ServerClock = {WalServerClock}, WalStart = {WalStart}, WalEnd = {WalEnd})",
                    message.GetType().Name, message.ServerClock, message.WalStart, message.WalEnd);

                if (message is BeginMessage beginMessage)
                {
                    transaction = new ReplicationTransaction();
                }
                else if (message is CommitMessage commitMessage)
                {
                    yield return transaction;
                }
                else if (message is RelationMessage relationMessage)
                {
                    relations[relationMessage.RelationId] = new Relation
                    {
                        RelationId = relationMessage.RelationId,
                        Namespace = relationMessage.Namespace,
                        RelationName = relationMessage.RelationName,
                        ServerClock = relationMessage.ServerClock,
                        ColumnNames = relationMessage.Columns
                            .Select(x => x.ColumnName)
                            .ToArray()
                    };
                }
                else if (message is InsertMessage insertMessage)
                {
                    var relation = relations[insertMessage.Relation.RelationId];

                    transaction.DataChangeEvents.Add(new InsertDataChangeEvent
                    {
                        Relation = relation,
                        NewValues = await ReadColumnValuesAsync(relation, insertMessage.NewRow, cancellationToken).ConfigureAwait(false)
                    });
                }
                else if (message is DefaultUpdateMessage defaultUpdateMessage)
                {
                    var relation = relations[defaultUpdateMessage.Relation.RelationId];

                    transaction.DataChangeEvents.Add(new DefaultUpdateDataChangeEvent
                    {
                        Relation = relation,
                        NewValues = await ReadColumnValuesAsync(relation, defaultUpdateMessage.NewRow, cancellationToken).ConfigureAwait(false),
                    });
                }
                else if (message is FullUpdateMessage fullUpdateMessage)
                {
                    var relation = relations[fullUpdateMessage.Relation.RelationId];

                    transaction.DataChangeEvents.Add(new FullUpdateDataChangeEvent
                    {
                        Relation = relation,
                        NewValues = await ReadColumnValuesAsync(relation, fullUpdateMessage.NewRow, cancellationToken).ConfigureAwait(false),
                        OldValues = await ReadColumnValuesAsync(relation, fullUpdateMessage.OldRow, cancellationToken).ConfigureAwait(false)
                    });
                }
                else if (message is KeyDeleteMessage keyDeleteMessage)
                {
                    var relation = relations[keyDeleteMessage.Relation.RelationId];

                    transaction.DataChangeEvents.Add(new KeyDeleteDataChangeEvent
                    {
                        Relation = relation,
                        Keys = await ReadColumnValuesAsync(relation, keyDeleteMessage.Key, cancellationToken).ConfigureAwait(false)
                    });
                }
                else if (message is FullDeleteMessage fullDeleteMessage)
                {
                    var relation = relations[fullDeleteMessage.Relation.RelationId];

                    transaction.DataChangeEvents.Add(new FullDeleteDataChangeEvent
                    {
                        Relation = relation,
                        OldValues = await ReadColumnValuesAsync(relation, fullDeleteMessage.OldRow, cancellationToken).ConfigureAwait(false)
                    });
                }
                else
                {
                    // We don't know what to do here and everything we could do... feels wrong. Throw 
                    // up to the consumer and let them handle the problem.
                    throw new InvalidOperationException($"Could not handle Message Type {message.GetType().Name}");
                }

                // Acknowledge the message. This should probably depend on wether a Transaction has finally been acknowledged
                // or not and is going to be something for future implementations.
                replicationConnection.SetReplicationStatus(message.WalEnd);
            }
        }

        private async ValueTask<IDictionary<string, object?>> ReadColumnValuesAsync(Relation relation, ReplicationTuple replicationTuple, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            // A normal dictionary could be sufficient, but I am not 
            // versed enough in asynchronous programming to know possible 
            // race conditions... so I'll just use the concurrent one.
            var results = new ConcurrentDictionary<string, object?>();

            // The ReplicationTuple does not contain a list of column names, but  
            // only a RelationId. So we need to provide the columns from the associated
            // Relation.
            // 
            // We then need to iterate each of the columns, because that's the idea 
            // behind a ReplicationTuple.
            int columnIdx = 0;

            // A "ReplicationTuple" implements an IAsyncEnumerable, so we need to iterate
            // it with a "await foreach", which yields the ReplicationValues with the
            // data.
            await foreach (var replicationValue in replicationTuple)
            {
                // These "ReplicationValues" do not carry the column name, so we resolve the column name
                // from the associated relation. This is going to throw, if we cannot find the column name, 
                // but in my opinion it should throw... because it is highly problematic.
                var column = relation.ColumnNames[columnIdx];

                // Get the column value and let Npgsql decide, how to map the value. You have seen, how the
                // NodaTime TypeConverters have been registered to a LogicalReplicationConnection, so you can
                // also automagically map unknown types.
                //
                // This is going to throw, if Npgsql fails to read the values. But again, it should throw.
                var value = await replicationValue
                    .Get(cancellationToken)
                    .ConfigureAwait(false);

                // While it looks like we could use the value directly, just don't... the value may include 
                // a DBNull for values, instead of a "null". This will pollute upper layers using the client,
                // so check them and turn it into a "null":
                var v = replicationValue.IsDBNull ? null : value;

                // It should never happen, that we fail to add a value. But what do I know? We guard against 
                // it and throw, if things go wrong. This is important, so upper layers don't need to operate 
                // on false assumptions.
                if (!results.TryAdd(column, v))
                {
                    throw new InvalidOperationException($"Failed to map ReplicationValue for Column '{column}'");
                }

                // Increase the column index, so we process the next column.
                columnIdx++;
            }

            return results;
        }
    }
}
```

## Implementing the Outbox Pattern ##

### Configuring the Postgres database ###

We start by adding a sequence `gitclub.outbox_event_seq` as a generator for the `outbox_event` primary key.

```plsql
CREATE SEQUENCE IF NOT EXISTS gitclub.outbox_event_seq
    start 38187
    increment 1
    NO MAXVALUE
    CACHE 1;
```

What's this "sequence" things and why do we use it? See sequences in relational databases turn out to be 
super useful, if you want to seed data with fixed IDs or if you want to use a HiLo-Pattern from our to-be-built 
.NET implementation.

We can then define the `outbox_event`, which is going to store the event data as JSON in a `JSONB` column. This 
simplifies the implementation... by a lot and makes it easier to debug the Outbox Events using PgAdmin or a 
database tool of your choice.

```plsql
CREATE TABLE IF NOT EXISTS gitclub.outbox_event (
    outbox_event_id integer default nextval('gitclub.outbox_event_seq'),
    correlation_id_1 varchar(2000) null,
    correlation_id_2 varchar(2000) null,
    correlation_id_3 varchar(2000) null,
    correlation_id_4 varchar(2000) null,
    event_time timestamptz not null,
    event_source varchar(2000) not null,
    event_type varchar(255) not null,
    payload JSONB not null,
    last_edited_by integer not null,
    sys_period tstzrange not null default tstzrange(current_timestamp, null),
    CONSTRAINT outbox_event_pkey
        PRIMARY KEY (outbox_event_id),
    CONSTRAINT outbox_event_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES gitclub.user(user_id)
);
```

You seldomly see so many Correlation IDs in an Outbox Event implementation, but my past experience for 
integrating systems is: The more Correlation IDs, the better. 

In a Database Script `gitclub.sql` we are now creating a PUBLICATION `outbox_pub`, that 
subscribes to the `gitclub.outbox_event` table only.

```plsql
DO $$

BEGIN

IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_publication WHERE pubname = 'outbox_pub') 
THEN
    CREATE PUBLICATION outbox_pub FOR TABLE 
        gitclub.outbox_event;
END IF;

END;
$$ LANGUAGE plpgsql;
```

We then instruct Postgres to keepi the Write Ahead Logs (WAL) by creating a Replication Slot.

```plsql
SELECT 'outbox_slot_init' FROM pg_create_logical_replication_slot('outbox_slot', 'pgoutput');
```

And that's it for Postgres!

### Streaming the OutboxEvents with .NET  ###

An `Entity` in our applications contains some properties all data needs to adhere to, so we can 
easily put Optimistic Concurrency and Auditing on top. It doesn't hurt and makes implementations 
a lot easier.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using NodaTime;

namespace GitClub.Database.Models
{
    public abstract class Entity
    {
        /// <summary>
        /// Gets or sets the Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Gets or sets the user the entity row version.
        /// </summary>
        public uint? RowVersion { get; set; }

        /// <summary>
        /// Gets or sets the user, that made the latest modifications.
        /// </summary>
        public required int LastEditedBy { get; set; }

        /// <summary>
        /// Gets or sets the SysPeriod.
        /// </summary>
        public Interval? SysPeriod { get; set; }
    }
}
```

The `OutboxEvent` now looks just like the table we have defined previously. Since we make the 
assumption, that out Event Data is always given in JSON format, we can use a `JsonDocument` 
directly.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json;

namespace GitClub.Database.Models
{
    /// <summary>
    /// Outbox Events.
    /// </summary>
    public class OutboxEvent : Entity
    {
        /// <summary>
        /// A Correlation ID.
        /// </summary>
        public string? CorrelationId1 { get; set; }

        /// <summary>
        /// A Correlation ID.
        /// </summary>
        public string? CorrelationId2 { get; set; }

        /// <summary>
        /// A Correlation ID.
        /// </summary>
        public string? CorrelationId3 { get; set; }

        /// <summary>
        /// A Correlation ID.
        /// </summary>
        public string? CorrelationId4 { get; set; }

        /// <summary> 
        /// The type of the event that occurred. 
        /// </summary>
        public required string EventType { get; set; }

        /// <summary> 
        /// The type of the event that occurred. 
        /// </summary>
        public string EventSource { get; set; } = "GitClub";

        /// <summary> 
        /// The time (in UTC) the event was generated. 
        /// </summary>
        public DateTimeOffset EventTime { get; set; } = DateTimeOffset.UtcNow;

        /// <summary>
        /// The Payload the Outbox event has.
        /// </summary>
        public required JsonDocument Payload { get; set; }
    }
}
```

And we are using EntityFramework Core for the .NET implementation, so what's left is mapping 
the whole thing in a `DbContext`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GitClub.Database.Models;
using Microsoft.EntityFrameworkCore;

namespace GitClub.Database
{
    /// <summary>
    /// A <see cref="DbContext"/> to query the database.
    /// </summary>
    public class ApplicationDbContext : DbContext
    {
        /// <summary>
        /// Constructor.
        /// </summary>
        /// <param name="options">Options to configure the base <see cref="DbContext"/></param>
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        // ...
        
        /// <summary>
        /// Gets or sets the TeamRepositoryRole.
        /// </summary>
        public DbSet<OutboxEvent> OutboxEvents { get; set; } = null!;

            protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            // Sequences
            modelBuilder.HasSequence<int>("outbox_event_seq", schema: "gitclub")
                .StartsAt(38187)
                .IncrementsBy(1);
                
            // ...

            // Tables
            modelBuilder.Entity<OutboxEvent>(entity =>
            {
                entity.ToTable("outbox_event", "gitclub");

                entity.HasKey(e => e.Id);

                entity.Property(e => e.Id)
                    .HasColumnType("INT")
                    .HasColumnName("outbox_event_id")
                    .UseHiLo("user_seq", "gitclub")
                    .ValueGeneratedOnAdd();

                entity.Property(e => e.CorrelationId1)
                    .HasColumnType("varchar(2000)")
                    .HasColumnName("correlation_id_1")
                    .HasMaxLength(2000)
                    .IsRequired(false);
                
                entity.Property(e => e.CorrelationId2)
                    .HasColumnType("varchar(2000)")
                    .HasColumnName("correlation_id_2")
                    .HasMaxLength(2000)
                    .IsRequired(false);
                
                entity.Property(e => e.CorrelationId3)
                    .HasColumnType("varchar(2000)")
                    .HasColumnName("correlation_id_3")
                    .HasMaxLength(2000)
                    .IsRequired(false);
                
                entity.Property(e => e.CorrelationId4)
                    .HasColumnType("varchar(2000)")
                    .HasColumnName("correlation_id_4")
                    .HasMaxLength(2000)
                    .IsRequired(false);
                
                entity.Property(e => e.EventTime)
                    .HasColumnType("timestamptz")
                    .HasColumnName("event_time")
                    .IsRequired(true);

                entity.Property(e => e.EventType)
                    .HasColumnType("varchar(2000)")
                    .HasColumnName("event_type")
                    .HasMaxLength(2000)
                    .IsRequired(true);
                
                entity.Property(e => e.EventSource)
                    .HasColumnType("varchar(2000)")
                    .HasColumnName("event_source")
                    .HasMaxLength(2000)
                    .IsRequired(true);

                entity.Property(e => e.Payload)
                    .HasColumnType("jsonb")
                    .HasColumnName("payload")
                    .HasMaxLength(2000)
                    .IsRequired(true);

                entity.Property(e => e.RowVersion)
                    .HasColumnType("xid")
                    .HasColumnName("xmin")
                    .IsRowVersion()
                    .IsConcurrencyToken()
                    .IsRequired(false)
                    .ValueGeneratedOnAddOrUpdate();

                entity.Property(e => e.LastEditedBy)
                    .HasColumnType("integer")
                    .HasColumnName("last_edited_by")
                    .IsRequired(true);

                entity.Property(e => e.SysPeriod)
                    .HasColumnType("tstzrange")
                    .HasColumnName("sys_period")
                    .IsRequired(false)
                    .ValueGeneratedOnAddOrUpdate();
            });
            
            // ...
        }
    }
}
```

It's repetitive to construct a new `OutboxEvent` by settings all properties, and we also want 
to have a simple method to cast the Payload to the `OutboxEvent` payload type. So we add a 
class `OutboxEventUtils` with some methods to help us.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace GitClub.Infrastructure.Outbox
{
    /// <summary>
    /// Static Methods to simplify working with a <see cref="OutboxEvent"/>.
    /// </summary>
    public static class OutboxEventUtils
    {
        /// <summary>
        /// Creates a new <see cref="OutboxEvent"/> from a given message Payload.
        /// </summary>
        /// <typeparam name="TMessageType">Type of the Message</typeparam>
        /// <param name="message">Message Payload</param>
        /// <param name="lastEditedBy">User that created the Outbox Event</param>
        /// <returns>An <see cref="OutboxEvent"/> that could be used</returns>
        public static OutboxEvent Create<TMessageType>(TMessageType message, int lastEditedBy)
        {
            var outboxEvent = new OutboxEvent
            {
                EventType = typeof(TMessageType).FullName!,
                Payload = JsonSerializer.SerializeToDocument(message),
                LastEditedBy = lastEditedBy
            };

            return outboxEvent;
        }

        /// <summary>
        /// Tries to get the deserialize the JSON Payload to the Type given in the 
        /// <see cref="OutboxEvent"/>. This returns an <see cref="object?"/>, so you 
        /// should do pattern matching on the consumer-side.
        /// </summary>
        /// <param name="outboxEvent">Outbox Event with typed Payload</param>
        /// <param name="result">The Payload deserialized to the Event Type</param>
        /// <returns><see cref="true"/>, if the payload can be deserialized; else <see cref="false"></returns>
        public static bool TryGetOutboxEventPayload(OutboxEvent outboxEvent, out object? result)
        {
            result = null;

            // Maybe throw here? We should probably log it at least...
            var type = Type.GetType(outboxEvent.EventType, throwOnError: false);

            if (type == null)
            {
                return false;
            }

            result = JsonSerializer.Deserialize(outboxEvent.Payload, type);

            return true;
        }
    }
}
```

The idea behind the implementation for the `OutboxEvent` stream is to wrap the `PostgresReplicationClient` for subscribing 
to the `outbox_slot`. This will stream all changes to the `outbox_event` table to our .NET application. We will then convert 
the untyped results into our `OutboxEvent` class.

So we first need all options for the `PostgresReplicationClient`, and additionally the Schema and Table name for the Outbox table.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace GitClub.Infrastructure.Outbox.Stream
{
    public class PostgresOutboxEventStreamOptions
    {
        /// <summary>
        /// Gets or sets the ConnectionString for the Replication Stream.
        /// </summary>
        public required string ConnectionString { get; set; }

        /// <summary>
        /// Gets or sets the PublicationName the Service is listening to.
        /// </summary>
        public required string PublicationName { get; set; }

        /// <summary>
        /// Gets or sets the ReplicationSlot the Service is listening to.
        /// </summary>
        public required string ReplicationSlotName { get; set; }

        /// <summary>
        /// Gets or sets the Table the Outbox Events are written to.
        /// </summary>
        public required string OutboxEventTableName { get; set; }

        /// <summary>
        /// Gets or sets the Schema the Outbox Events are written to.
        /// </summary>
        public required string OutboxEventSchemaName { get; set; }
    }

    // ...
}
```

Then before implementing the `PostgresOutboxEventStream` let's recap, that we get the values from the 
Replication Stream as a `IDictionary<string, object?>` for each of the columns. We will need to cast 
the values into their correct types. 

For this we first define a `DictionaryUtils` class, that does just that:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Diagnostics.CodeAnalysis;

namespace GitClub.Infrastructure.Outbox
{
    public static class DictionaryUtils
    {
        /// <summary>
        /// Tries to get a value from a <see cref="IDictionary{TKey, TValue}"> and tries 
        /// to cast it to the given type <typeparamref name="T"/>. If the given key doesn't 
        /// exist, we are returning a <paramref name="defaultValue"/>.
        /// </summary>
        /// <typeparam name="T">Target Type to try cast to</typeparam>
        /// <param name="values">Source Dictionary with values</param>
        /// <param name="key">The key to get</param>
        /// <param name="defaultValue">The default value returned, when <paramref name="key"/> does not exist</param>
        /// <returns>The value as <typeparamref name="T"/></returns>
        /// <exception cref="InvalidOperationException">Throws, if the cast isn't possible</exception>
        public static T? GetOptionalValue<T>(IDictionary<string, object?> values, string key, T? defaultValue = default)
        {
            if (!values.ContainsKey(key))
            {
                return defaultValue;
            }

            var untypedValue = values[key];

            if (untypedValue == null)
            {
                return defaultValue;
            }

            if (!TryCast<T>(untypedValue, out var typedValue))
            {
                throw new InvalidOperationException($"Failed to cast to '{typeof(T)}'");
            }

            return typedValue;
        }

        /// <summary>
        /// Gets a Value from a <see cref="IDictionary{TKey, TValue}"> and tries 
        /// to cast it to the given type <typeparamref name="T"/>.
        /// </summary>
        /// <typeparam name="T">Target Type to try cast to</typeparam>
        /// <param name="values">Source Dictionary with values</param>
        /// <param name="key">The key to get</param>
        /// <returns>The value as <typeparamref name="T"/></returns>
        /// <exception cref="InvalidOperationException">Throws, if the key doesn't exist or a cast isn't possible</exception>
        public static T GetRequiredValue<T>(IDictionary<string, object?> values, string key)
        {
            if (!values.ContainsKey(key))
            {
                throw new InvalidOperationException($"Value is required for key '{key}'");
            }

            var untypedValue = values[key];

            if (untypedValue == null)
            {
                throw new InvalidOperationException($"Value is required for key '{key}'");
            }

            if (!TryCast<T>(untypedValue, out var typedValue))
            {
                throw new InvalidOperationException($"Failed to cast to '{typeof(T)}'");
            }

            return typedValue;
        }

        /// <summary>
        /// Casts to a value of the given type if possible.
        /// If <paramref name="obj"/> is <see langword="null"/> and <typeparamref name="T"/>
        /// can be <see langword="null"/>, the cast succeeds just like the C# language feature.
        /// </summary>
        /// <param name="obj">The object to cast.</param>
        /// <param name="value">The value of the object, if the cast succeeded.</param>
        internal static bool TryCast<T>(object? obj, [NotNullWhen(true)] out T? value)
        {
            if (obj is T tObj)
            {
                value = tObj;
                return true;
            }

            value = default;
            return obj is null && default(T) is null;
        }
    }
}
```

And finally we can write the `PostgresOutboxEventStream`, that creates a new `PostgresReplicationClient` to 
subscribe to the Postgres replication slot. Then we'll convert the received data to an `OutboxEvent` and 
yield it.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace GitClub.Infrastructure.Outbox.Stream
{

    // ...

    /// <summary>
    /// Provides a Stream of <see cref="OutboxEvent"/>, that are published by a Postgres database.
    /// </summary>
    public class PostgresOutboxEventStream
    {
        private readonly ILogger _logger;

        private readonly PostgresOutboxEventStreamOptions _options;
        private readonly JsonSerializerOptions _jsonSerializerOptions;

        public PostgresOutboxEventStream(ILogger logger, IOptions<PostgresOutboxEventStreamOptions> options)
        {
            _logger = logger;
            _options = options.Value;
            _jsonSerializerOptions = new JsonSerializerOptions()
                .ConfigureForNodaTime(DateTimeZoneProviders.Tzdb);
        }

        public async IAsyncEnumerable<OutboxEvent> StartOutboxEventStream([EnumeratorCancellation] CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var replicationClientOptions = new PostgresReplicationClientOptions
            {
                ConnectionString = _options.ConnectionString,
                PublicationName = _options.PublicationName,
                ReplicationSlotName = _options.ReplicationSlotName
            };

            var _replicationService = new PostgresReplicationClient(_logger, Options.Create(replicationClientOptions));

            // This loop will emit whenever new Transactions are available:
            await foreach (var transaction in _replicationService
                .StartReplicationAsync(cancellationToken)
                .ConfigureAwait(false))
            {
                // We will now inspect the Data Change Events:
                foreach(var dataChangeEvent in transaction.DataChangeEvents)
                {
                    _logger.LogDebug($"Processing Data Change Event (Type = {dataChangeEvent.GetType().FullName}, Schema = {dataChangeEvent.Relation.Namespace}, Table = {dataChangeEvent.Relation.RelationName}");

                    // This is the wrong namespace ...
                    if(!string.Equals(dataChangeEvent.Relation.Namespace, _options.OutboxEventSchemaName, StringComparison.InvariantCultureIgnoreCase))
                    {
                        _logger.LogDebug($"Expected Namespace \"{_options.OutboxEventSchemaName}\", but was \"{dataChangeEvent.Relation.Namespace}\"");
                        
                        continue;
                    }

                    // This is the wrong Table ...
                    if (!string.Equals(dataChangeEvent.Relation.RelationName, _options.OutboxEventTableName, StringComparison.InvariantCultureIgnoreCase))
                    {
                        _logger.LogDebug($"Expected Namespace \"{_options.OutboxEventTableName}\", but was \"{dataChangeEvent.Relation.RelationName}\"");

                        continue;
                    }

                    if(dataChangeEvent is not InsertDataChangeEvent)
                    {
                        _logger.LogDebug($"Expected a \"{typeof(DataChangeEvent).Name}\", but was \"{dataChangeEvent.GetType().Name}\"");

                        continue;
                    }

                    // This is the correct message
                    if (dataChangeEvent is InsertDataChangeEvent insertDataChangeEvent)
                    {
                        var outboxEvent = await MapToOutboxEventAsync(insertDataChangeEvent.Relation, insertDataChangeEvent.NewValues, cancellationToken).ConfigureAwait(false);
                        
                        if(outboxEvent != null)
                        {
                            yield return outboxEvent;
                        }
                    }
                }
            }
        }

        private async ValueTask<OutboxEvent?> MapToOutboxEventAsync(Relation relation, IDictionary<string, object?> values, CancellationToken cancellationToken)
        {
            try
            {
                var result = await InternalMapToOutboxEventAsync(relation, values, cancellationToken).ConfigureAwait(false);

                return result;
            } 
            catch(Exception e)
            {
                _logger.LogError(e, "Failed to deserialize OutboxEvent due to an Exception");

                return null;
            }
        }


        private ValueTask<OutboxEvent?> InternalMapToOutboxEventAsync(Relation relation, IDictionary<string, object?> values, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var jsonDocument = GetAsJsonDocument(values, "payload");

            if(jsonDocument == null)
            {
                _logger.LogWarning("Failed to deserialize Event Payload as JsonDocument");

                return ValueTask.FromResult<OutboxEvent?>(null);
            }

            var outboxEvent = new OutboxEvent
            {
                Id = DictionaryUtils.GetRequiredValue<int>(values, "outbox_event_id"),
                EventSource = DictionaryUtils.GetRequiredValue<string>(values, "event_source"),
                EventType = DictionaryUtils.GetRequiredValue<string>(values, "event_type"),
                EventTime = DictionaryUtils.GetRequiredValue<Instant>(values, "event_time").ToDateTimeOffset(),
                Payload = jsonDocument,
                CorrelationId1 = DictionaryUtils.GetOptionalValue<string>(values, "correlation_id_1"),
                CorrelationId2 = DictionaryUtils.GetOptionalValue<string>(values, "correlation_id_2"),
                CorrelationId3 = DictionaryUtils.GetOptionalValue<string>(values, "correlation_id_3"),
                CorrelationId4 = DictionaryUtils.GetOptionalValue<string>(values, "correlation_id_4"),
                LastEditedBy = DictionaryUtils.GetRequiredValue<int>(values, "last_edited_by"),
                SysPeriod = DictionaryUtils.GetRequiredValue<Interval>(values, "sys_period")
            };

            return ValueTask.FromResult<OutboxEvent?>(outboxEvent);

            JsonDocument? GetAsJsonDocument(IDictionary<string, object?> values, string key)
            {
                var json = DictionaryUtils.GetRequiredValue<string>(values, key);

                return JsonSerializer.Deserialize<JsonDocument>(json, _jsonSerializerOptions);
            }
        }
    }
}
```

### Working through an Example ###

Let's round up this example by taking a look at the actual `GitClub` implementation.

If a user creates an `Organization`, we will raise an `OutboxEvent` using an `OrganizationCreatedMessage` as payload:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GitClub.Database.Models;
using System.Text.Json.Serialization;

namespace GitClub.Infrastructure.Outbox.Messages
{
    public class OrganizationCreatedMessage
    {
        /// <summary>
        /// Gets or sets the Organization ID.
        /// </summary>
        [JsonPropertyName("organizationId")]
        public required int OrganizationId { get; set; }

        /// <summary>
        /// Gets or sets the Base RepositoryRole for Users.
        /// </summary>
        [JsonPropertyName("baseRepositoryRole")]
        public required BaseRepositoryRoleEnum BaseRepositoryRole { get; set; }

        /// <summary>
        /// Gets or sets the Users assigned to the new Organization.
        /// </summary>
        [JsonPropertyName("userOrganizationRoles")]
        public List<AddedUserToOrganizationMessage> UserOrganizationRoles { get; set; } = [];
    }
}
```

In the `OrganizationService` class we have a method `CreateOrganizationAsync`, that now creates the 
`Organization`, default `User` assignments and the `OutboxEvent` in a single transaction. So whenever 
an `Organization` is created the `OutboxEvent` is also created within the same transaction.

If creating the `Organization` fails, for example due to constraint violations, then the `OutboxEvent` 
wouldn't be written either, since both write to the same database transaction.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GitClub.Database;
using GitClub.Database.Models;
using GitClub.Infrastructure.Authentication;
using GitClub.Infrastructure.Constants;
using GitClub.Infrastructure.Exceptions;
using GitClub.Infrastructure.Logging;
using GitClub.Infrastructure.OpenFga;
using GitClub.Infrastructure.Outbox;
using GitClub.Infrastructure.Outbox.Messages;
using Microsoft.EntityFrameworkCore;
using System.Data;

namespace GitClub.Services
{
    public class OrganizationService
    {
        private readonly ILogger<OrganizationService> _logger;

        private readonly IDbContextFactory<ApplicationDbContext> _dbContextFactory;
        private readonly AclService _aclService;

        public OrganizationService(ILogger<OrganizationService> logger, IDbContextFactory<ApplicationDbContext> dbContextFactory, AclService aclService)
        {
            _logger = logger;
            _dbContextFactory = dbContextFactory;
            _aclService = aclService;
        }

        public async Task<Organization> CreateOrganizationAsync(Organization organization, CurrentUser currentUser, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            bool isAuthorized = currentUser.IsInRole(Roles.Administrator);

            if(!isAuthorized)
            {
                throw new AuthorizationFailedException("Insufficient Permissions to create an Organization");
            }

            using var applicationDbContext = await _dbContextFactory
                .CreateDbContextAsync(cancellationToken)
                .ConfigureAwait(false);

            organization.LastEditedBy = currentUser.UserId;

            await applicationDbContext
                .AddAsync(organization, cancellationToken)
                .ConfigureAwait(false);

            // The User creating the Organization is automatically the Owner
            var userOrganizationRole = new UserOrganizationRole
            {
                OrganizationId = organization.Id,
                Role = OrganizationRoleEnum.Owner,
                UserId = currentUser.UserId,
                LastEditedBy = currentUser.UserId
            };

            await applicationDbContext
                .AddAsync(userOrganizationRole, cancellationToken)
                .ConfigureAwait(false);

            var outboxEvent = OutboxEventUtils.Create(new OrganizationCreatedMessage
            {
                OrganizationId = organization.Id,
                BaseRepositoryRole = organization.BaseRepositoryRole,
                UserOrganizationRoles = new[] { userOrganizationRole }
                    .Select(x => new AddedUserToOrganizationMessage
                    {
                        OrganizationId = userOrganizationRole.OrganizationId,
                        UserId = userOrganizationRole.UserId,
                        Role = userOrganizationRole.Role,
                    })
                    .ToList()
            }, lastEditedBy: currentUser.UserId);

            await applicationDbContext
                .AddAsync(outboxEvent, cancellationToken)
                .ConfigureAwait(false);

            await applicationDbContext
                .SaveChangesAsync(cancellationToken)
                .ConfigureAwait(false);

            return organization;
        }
        
        // ...
        
    }
}
```

What do we want to use the `OutboxEvent` for? We want to write a new Relation Tuple to OpenFGA, so 
we can authorize access to the Organization. We add an `OutboxEventConsumer`, that has a single 
method for handling the `OutboxEvent`.

```csharp
// ...

namespace GitClub.Infrastructure.Outbox.Consumer
{
    public class OutboxEventConsumer
    {
        private readonly ILogger<OutboxEventConsumer> _logger;

        private readonly AclService _aclService;

        public OutboxEventConsumer(ILogger<OutboxEventConsumer> logger, AclService aclService)
        {
            _logger = logger;
            _aclService = aclService;
        }

        public async Task HandleOutboxEventAsync(OutboxEvent outboxEvent, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();


            if(outboxEvent.Payload == null)
            {
                _logger.LogWarning("Event doesn't contain a JSON Payload");

                return;
            }

            var success = OutboxEventUtils.TryGetOutboxEventPayload(outboxEvent, out object? payload);

            // Maybe it's better to throw up, if we receive an event, we can't handle? But probably 
            // this wasn't meant for our Service at all? We don't know, so we log a Warning and go 
            // on with life ...
            if (!success)
            {
                _logger.LogWarning("Failed to get Data from OutboxEvent");

                return;
            }

            // Now handle the given payload ...
            switch (payload)
            {
                case OrganizationCreatedMessage organizationCreatedMessage:
                    await HandleOrganizationCreatedAsync(organizationCreatedMessage, cancellationToken).ConfigureAwait(false);
                    break;
                    
                // ...
            }
        }

        private async Task HandleOrganizationCreatedAsync(OrganizationCreatedMessage message, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            RelationTuple[] tuplesToWrite =
            [
                RelationTuples.Create<Organization, Organization>(message.OrganizationId, message.OrganizationId, message.BaseRepositoryRole, Relations.Member),
                ..message.UserOrganizationRoles
                    .Select(x => RelationTuples.Create<Organization, User>(x.OrganizationId, x.UserId, x.Role))
                    .ToArray()                
            ];

            await _aclService
                .AddRelationshipsAsync(tuplesToWrite, cancellationToken)
                .ConfigureAwait(false);

        }
        
        // ...
    }
}
```

We need to listen to the stream indefinitely, and this sounds like a `BackgroundService` is a good 
idea in ASP.NET Core. For lack of a better name I called it an `PostgresOutboxEventProcessor`, which 
gets the `OutboxEventConsumer` injected.

It then subscribes to the `PostgresOutboxEventStream`, and invokes the `outboxEventConsumer` for every 
`OutboxEvent` received. If the `ReplicationStream` fails, we need to reconnect. So we add a little error 
handling.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace GitClub.Hosted
{
    public class PostgresOutboxEventProcessorOptions
    {
        /// <summary>
        /// Gets or sets the ConnectionString for the Replication Stream.
        /// </summary>
        public required string ConnectionString { get; set; }

        /// <summary>
        /// Gets or sets the PublicationName the Service is listening to.
        /// </summary>
        public required string PublicationName { get; set; }

        /// <summary>
        /// Gets or sets the ReplicationSlot the Service is listening to.
        /// </summary>
        public required string ReplicationSlotName { get; set; }

        /// <summary>
        /// Gets or sets the Table the Outbox Events are written to.
        /// </summary>
        public required string OutboxEventTableName { get; set; }

        /// <summary>
        /// Gets or sets the Schema the Outbox Events are written to.
        /// </summary>
        public required string OutboxEventSchemaName { get; set; }
    }

    /// <summary>
    /// Processes Outbox Events.
    /// </summary>
    public class PostgresOutboxEventProcessor : BackgroundService
    {
        private readonly ILogger<PostgresOutboxEventProcessor> _logger;

        private readonly PostgresOutboxEventProcessorOptions _options;
        private readonly OutboxEventConsumer _outboxEventConsumer;

        public PostgresOutboxEventProcessor(ILogger<PostgresOutboxEventProcessor> logger, IOptions<PostgresOutboxEventProcessorOptions> options, OutboxEventConsumer outboxEventConsumer)
        {
            _logger = logger;
            _options = options.Value;
            _outboxEventConsumer = outboxEventConsumer;
        }

        protected override async Task ExecuteAsync(CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            // We could also inject the Stream, but I think it's better to do it 
            // this way, in case we have multiple consumers. I also played with 
            // putting it in a static method... feels wrong.
            var outboxEventStreamOptions = new PostgresOutboxEventStreamOptions
            {
                ConnectionString = _options.ConnectionString,
                PublicationName = _options.PublicationName,
                ReplicationSlotName = _options.ReplicationSlotName,
                OutboxEventSchemaName = _options.OutboxEventSchemaName,
                OutboxEventTableName = _options.OutboxEventTableName
            };

            var outboxEventStream = new PostgresOutboxEventStream(_logger, Options.Create(outboxEventStreamOptions));

            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {

                    // Listen to the Outbox Event Stream.
                    await foreach (var outboxEvent in outboxEventStream.StartOutboxEventStream(cancellationToken))
                    {
                        _logger.LogInformation("Processing OutboxEvent (Id = {OutboxEventId})", outboxEvent.Id);

                        try
                        {
                            await _outboxEventConsumer
                                .HandleOutboxEventAsync(outboxEvent, cancellationToken)
                                .ConfigureAwait(false);
                        }
                        catch (Exception e)
                        {
                            _logger.LogError(e, "Failed to handle the OutboxEvent due to an Exception (ID = {OutboxEventId})", outboxEvent.Id);
                        }
                    }
                }
                catch (Exception e)
                {
                    _logger.LogError(e, "Logical Replication failed with an Error. Restarting the Stream.");

                    await Task
                        .Delay(200)
                        .ConfigureAwait(false);
                }
            }
        }
    }
}
```

## Conclusion ##

And that's it!

Implementing the Outbox Pattern with Npgsql was quite easy, although it still takes some effort to make 
this production-ready. But it's a good starting point anyway and you don't have to go all-in on Debezium 
early in the project.

### Event Sourcing and Change Data Capture (CDC) ###

I want to close this article with a discussion on Change Data Capture, because Event Sourcing isn't my 
domain and it's interesting how others approach such problems. I initially thought about using the data 
captured by CDC as-is and make sense of it by inspecting a transaction.

But we are using an OLTP database, thus the data captured by CDC is heavily normalized (and rightly so!). Using 
the normalized data as-is will, first of all super-glue us to the database model, then leak all kinds of sensitive 
data and most probably it will be very complicated to process.

Yaroslav Tkachenko has written a great article on this very topic, that also describes challenges at Shopify:

* [Change Data Capture Is Still an Anti-pattern. And You Still Should Use It.](https://streamingdata.substack.com/p/change-data-capture-is-still-an-anti)

In [gitclub-dotnet] I have decided to use something similar to "Domain Events", but these events still look 
quite anemic to me. So I am still wondering, if I could have achieved something similar by just utilizing the 
CDC data as-is.

What's your experience here?

### Further Reading ###

* [The Wonders of Postgres Logical Decoding Messages (InfoQ, Gunnar Morling and Srini Penchikala)](https://www.infoq.com/articles/wonders-of-postgres-logical-decoding-messages/)
* [Avoiding dual writes in event-driven applications (Red Hat, Bernard Tison)](https://developers.redhat.com/articles/2021/07/30/avoiding-dual-writes-event-driven-applications#)
* [Change Data Capture Is Still an Anti-pattern. And You Still Should Use It. (Data Streaming Journey, Yaroslav Tkachenko)](https://streamingdata.substack.com/p/change-data-capture-is-still-an-anti)