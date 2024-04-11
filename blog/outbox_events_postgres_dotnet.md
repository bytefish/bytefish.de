title: Implementing the Outbox Pattern with Postgres and .NET
date: 2024-04-08 13:42
tags: postgres, dotnet
category: dotnet
slug: outbox_events_postgres_dotnet
author: Philipp Wagner
summary: This article shows how to implement an Outbox pattern using Postgres and .NET.

[gitclub-dotnet]: https://github.com/bytefish/gitclub-dotnet

In my last article you have seen how to use PostgreSQL Logical Replication feature to implement a 
Change Data Capture (CDC) mechanism. It works great and allows you to subscribe to changes in a 
Postgres database. And by using the Logical Replication feature we have an At-least-once delivery 
of messages.

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

In the [gitclub-dotnet] application I am experimenting with, I experienced a "Dual Write Problem". A "Dual Write" 
occurs, when you are changing data in (at least) two distinct systems, without having a shared transaction. In my 
case it occurs, when writing to both, our applications database and the OpenFGA database.

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

### Creating the OutboxEvent Table ###

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
Creating the OutboxEvent Table('gitclub.outbox_event_seq'),
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

We then instruct Postgres to keep the Write Ahead Logs (WAL) by creating a Replication Slot.

```plsql
SELECT 'outbox_slot_init' FROM pg_create_logical_replication_slot('outbox_slot', 'pgoutput');
```

And that's it for Postgres!

## Receiving and Processing OutboxEvents in .NET ##

### The OutboxEvent Data Model ###

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
assumption, that our Event Data is always given in JSON format, we can use a `JsonDocument` 
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

### Configuring the EntityFramework DbContext ###

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

### Subscribing to Postgres Logical Replication Stream ###

To subscribe to the Logical Replication Stream of a Postgres Database, we'll need a few Options.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace GitClub.Infrastructure.Outbox.Postgres
{
    /// <summary>
    /// Options to configure the <see cref="PostgresNotificationProcessor"/>.
    /// </summary>
    public class PostgresOutboxSubscriberOptions
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
}
```

And in the `PostgresOutboxSubscriber` we can then leverage Npgsql great implementation to process all 
`OutboxEvents` inserted to the database. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GitClub.Infrastructure.Logging;
using Microsoft.Extensions.Options;
using Npgsql.Replication.PgOutput.Messages;
using Npgsql.Replication.PgOutput;
using Npgsql.Replication;
using Npgsql;
using System.Runtime.CompilerServices;
using GitClub.Database.Models;
using System.Text.Json;
using NodaTime;

namespace GitClub.Infrastructure.Outbox.Postgres
{
    public class PostgresOutboxSubscriber
    {
        /// <summary>
        /// Logger.
        /// </summary>
        private readonly ILogger _logger;

        /// <summary>
        /// Options to configure the Wal Receiver.
        /// </summary>
        private readonly PostgresOutboxSubscriberOptions _options;

        /// <summary>
        /// Creates a new <see cref="PostgresReplicationClient" />.
        /// </summary>
        /// <param name="logger">Logger to log messages</param>
        /// <param name="options">Options to configure the service</param>
        public PostgresOutboxSubscriber(ILogger logger, IOptions<PostgresOutboxSubscriberOptions> options)
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
        public async IAsyncEnumerable<OutboxEvent> StartOutboxEventStreamAsync([EnumeratorCancellation] CancellationToken cancellationToken)
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

            await foreach (var message in replicationConnection
                .StartReplication(replicationSlot, replicationPublication, cancellationToken)
                .ConfigureAwait(false))
            {
                _logger.LogDebug("Received Postgres WAL Message (Type = {WalMessageType}, ServerClock = {WalServerClock}, WalStart = {WalStart}, WalEnd = {WalEnd})",
                    message.GetType().Name, message.ServerClock, message.WalStart, message.WalEnd);

                if (message is InsertMessage insertMessage)
                {
                    if (IsOutboxTable(insertMessage))
                    {
                        var outboxEvent = await ConvertToOutboxEventAsync(insertMessage, cancellationToken).ConfigureAwait(false);

                        yield return outboxEvent;
                    }
                }

                // Acknowledge the message. This should probably depend on wether a Transaction has finally been acknowledged
                // or not and is going to be something for future implementations.
                replicationConnection.SetReplicationStatus(message.WalEnd);
            }
        }

        bool IsOutboxTable(InsertMessage message)
        {
            return string.Equals(_options.OutboxEventSchemaName, message.Relation.Namespace, StringComparison.InvariantCultureIgnoreCase)
                && string.Equals(_options.OutboxEventTableName, message.Relation.RelationName, StringComparison.InvariantCultureIgnoreCase);
        }

        async ValueTask<OutboxEvent> ConvertToOutboxEventAsync(InsertMessage insertMessage, CancellationToken cancellationToken)
        {
            var values = await ConvertToDictionaryAsync(insertMessage, cancellationToken).ConfigureAwait(false);

            return ConvertToOutboxEventAsync(values);
        }

        async ValueTask<Dictionary<string, object?>> ConvertToDictionaryAsync(InsertMessage insertMessage, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var result = new Dictionary<string, object?>();

            int columnIdx = 0;

            await foreach (var replicationValue in insertMessage.NewRow)
            {
                var columnName = insertMessage.Relation
                    .Columns[columnIdx++].ColumnName;
                result[columnName] = await GetValue(replicationValue, cancellationToken);
            }

            return result;
        }

        async Task<object?> GetValue(ReplicationValue replicationValue, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var value = await replicationValue
                .Get(cancellationToken)
                .ConfigureAwait(false);

            if (replicationValue.IsDBNull)
            {
                return null;
            }

            return value;
        }

        OutboxEvent ConvertToOutboxEventAsync(Dictionary<string, object?> values)
        {
            _logger.TraceMethodEntry();

            var payload = GetRequiredValue<string>(values, "payload");

            var outboxEvent = new OutboxEvent
            {
                Id = GetRequiredValue<int>(values, "outbox_event_id"),
                CorrelationId1 = GetOptionalValue<string>(values, "correlation_id_1"),
                CorrelationId2 = GetOptionalValue<string>(values, "correlation_id_2"),
                CorrelationId3 = GetOptionalValue<string>(values, "correlation_id_3"),
                CorrelationId4 = GetOptionalValue<string>(values, "correlation_id_4"),
                EventType = GetRequiredValue<string>(values, "event_type"),
                EventSource = GetRequiredValue<string>(values, "event_source"),
                EventTime = GetRequiredValue<Instant>(values, "event_time").ToDateTimeOffset(),
                Payload = JsonSerializer.Deserialize<JsonDocument>(payload)!,
                LastEditedBy = GetRequiredValue<int>(values, "last_edited_by")
            };

            return outboxEvent;
        }

        T GetRequiredValue<T>(Dictionary<string, object?> values, string key)
        {
            if (!values.ContainsKey(key))
            {
                throw new InvalidOperationException($"Value is required for key '{key}'");
            }

            if (values[key] is not T t)
            {
                throw new InvalidOperationException($"Value is not Type '{typeof(T).Name}'");
            }

            return t;
        }

        T? GetOptionalValue<T>(Dictionary<string, object?> values, string key, T? defaultValue = default)
        {
            if (!values.ContainsKey(key))
            {
                return defaultValue;
            }

            if (values[key] is T t)
            {
                return t;
            }

            return defaultValue;
        }
    }
}
```

### Example: Processing OutboxEvents in GitClub ###

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
    public class OutboxEventConsumer : IOutboxEventConsumer
    {
        private readonly ILogger<OutboxEventConsumer> _logger;

        private readonly AclService _aclService;

        public OutboxEventConsumer(ILogger<OutboxEventConsumer> logger, AclService aclService)
        {
            _logger = logger;
            _aclService = aclService;
        }

        public async Task ConsumeOutboxEventAsync(OutboxEvent outboxEvent, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();


            if (outboxEvent.Payload == null)
            {
                _logger.LogWarning("Event doesn't contain a JSON Payload");

                return;
            }

            var success = outboxEvent.TryGetOutboxEventPayload(out object? payload);

            // Maybe it's better to throw up, if we receive an event, we can't handle? But probably 
            // this wasn't meant for our Service at all? We don't know, so we log a Warning and go 
            // on with life ...
            if (!success)
            {
                _logger.LogWarning("Failed to get Data from OutboxEvent (Id = {OutboxEventId}, EventType = {OutboxEventType})", outboxEvent.Id, outboxEvent.EventType);

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
            var outboxSubscriberOptions = new PostgresOutboxSubscriberOptions
            {
                ConnectionString = _options.ConnectionString,
                PublicationName = _options.PublicationName,
                ReplicationSlotName = _options.ReplicationSlotName,
                OutboxEventSchemaName = _options.OutboxEventSchemaName,
                OutboxEventTableName = _options.OutboxEventTableName
            };

            var outboxEventStream = new PostgresOutboxSubscriber(_logger, Options.Create(outboxSubscriberOptions));

            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    await foreach (var outboxEvent in outboxEventStream.StartOutboxEventStreamAsync(cancellationToken))
                    {
                        _logger.LogInformation("Processing OutboxEvent (Id = {OutboxEventId})", outboxEvent.Id);

                        try
                        {
                            await _outboxEventConsumer
                                .ConsumeOutboxEventAsync(outboxEvent, cancellationToken)
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

                    // Probably add some better Retry options ...
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

Implementing the Outbox Pattern with Npgsql was quite easy, it clocks in at less than 200 lines of code. It still 
takes some effort to make this production-ready, but I think it's a good starting point and you don't have to go 
all-in on Debezium early in a project.

### Further Reading ###

* [The Wonders of Postgres Logical Decoding Messages (InfoQ, Gunnar Morling and Srini Penchikala)](https://www.infoq.com/articles/wonders-of-postgres-logical-decoding-messages/)
* [Avoiding dual writes in event-driven applications (Red Hat, Bernard Tison)](https://developers.redhat.com/articles/2021/07/30/avoiding-dual-writes-event-driven-applications#)
* [Change Data Capture Is Still an Anti-pattern. And You Still Should Use It. (Data Streaming Journey, Yaroslav Tkachenko)](https://streamingdata.substack.com/p/change-data-capture-is-still-an-anti)