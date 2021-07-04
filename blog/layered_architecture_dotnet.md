title: Software Architectures: Layered Architecture with .NET
date: 2021-07-04 18:06
tags: dotnet, architecture
category: dotnet
slug: layered_architecture_dotnet
author: Philipp Wagner
summary: Layered Architecture with .NET.

You start a new Backend and a question comes up real quick:

* What Software Architecture should we use?

There is no shortage of Software Architecture literature.

Do you want to build a Layered Architecture, Hexagonal Architcture, Event-driven Architecture, Service-oriented Architecture, 
Clean Architecture? Are you going to build a Monolith? Or do you go for Microservices? Are you going to use a Relational 
Database? Or better use a Document-Database? An Event-Bus to decouple all the things? What about Domain Driven Design? 
What's this Eventual Consistency? ...

There's a simple answer: 

> It depends!

So in this article I want to show you how to build a simple Layered Architecture with .NET.

The Checklist of things we'll look at is:

* ⬜ Data Access
* ⬜ Multi-Tenancy
* ⬜ Database Migrations
* ⬜ Audit Trails
* ⬜ Versioning
* ⬜ Optmistic Concurrency
* ⬜ Logging
* ⬜ Testing

As always all code can be found at:

* [https://github.com/bytefish/LayeredArchitectureDotNet](https://github.com/bytefish/LayeredArchitectureDotNet)

## Why am I writing this? ##

If you are working with .NET and want to use a Relational Database in your project, there is a good 
chance you are going to use Entity Framework. Entity Framework is a very fine technology and it's 
perfectly well suited for a lot of applications, so don't get me wrong.

Microsoft gives some implementation guidelines for an Entity Framework-based persistence layer over at:

* [Implement the infrastructure persistence layer with Entity Framework Core]

The Microsoft article shows how to use Entity Framework with Domain Driven Design (DDD). It talks about 
Aggregate Roots, Unit of Work, CQRS and using a Repository Pattern to abstract the Persistence Layer. It's 
a lot of topics to digest. At the same time, there are very few recommended .NET examples to learn 
from.

What's my problem with using a Domain-Driven Design approach right from the start? 

It is **very easy** to do it wrong.

[Implement the infrastructure persistence layer with Entity Framework Core]: https://docs.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/infrastructure-persistence-layer-implementation-entity-framework-core

### Is this against DDD? ###

No way! I discarded this article probably 12 times and started all over. It came off like a Anti-DDD 
rant. But I am not an expert on Domain Driven Development and I am not really qualified to write about 
it.

I am not saying "Don't use a DDD approach for your project!". Building up a common language between all people 
involved in a project surely is a honorable goal. I read about DDD stories of enlightment and success in 
blogs.

## Data Access ##

Let's build a Layered Architecture and start with the Data Access.

We go all in on a relational database. And I think, what people really want from an OR-Mapper is a simple and safe way of 
materializing query results into strongly-typed objects. So I have first taken a look at Dapper, which is often touted as 
best thing next to sliced bread.

But Dapper is really barebones and it would take quite some effort to abstract things like database mappings, loading 
related entities, interpolated SQL queries, Optimistic Concurrency, ... Basically I want everything Entity Framework Core 
already has, plus a way to provide a ``DbConnection`` and a ``DbTransaction`` all by myself.

### The Database Mappings ###

First of all we need a way to map between a C\# object and the relational Database. We want this to be 
configurable and inject those mappings into a ``DbContext``, so we need an abstraction first. Copying from a 
previous article on EntityFramework Core, we define an ``IEntityTypeMap``: 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;

namespace LayeredArchitecture.DataAccess.Mapping
{
    /// <summary>
    /// Implements Entity Framework Core Type Configurations using the 
    /// <see cref="ModelBuilder"/>. This class is used as an abstraction, 
    /// so we can pass the <see cref="IEntityTypeConfiguration{TEntity}"/> 
    /// into a <see cref="DbContext"/>.
    /// </summary>
    public interface IEntityTypeMap
    {
        /// <summary>
        /// Configures the <see cref="ModelBuilder"/> for an entity.
        /// </summary>
        /// <param name="builder"><see cref="ModelBuilder"/></param>
        void Map(ModelBuilder builder);
    }
}
```

To simplify working with the ``IEntityTypeMap``, we provide a ``EntityTypeMap<TEntityType>`` base class. This makes 
it simple to use the underlying ``EntityTypeBuilder<TEntityType>`` Fluent Interface of Entity Framework:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace LayeredArchitecture.DataAccess.Mapping
{
    /// <summary>
    /// A base class for providing simplified access to a <see cref="EntityTypeBuilder{TEntityType}"/> for a 
    /// given <see cref="TEntityType"/>. This is used to enable mappings for each type individually.
    /// </summary>
    /// <typeparam name="TEntityType"></typeparam>
    public abstract class EntityTypeMap<TEntityType> : IEntityTypeMap
            where TEntityType : class
    {
        /// <summary>
        /// Implements the <see cref="IEntityTypeMap"/>.
        /// </summary>
        /// <param name="builder"><see cref="ModelBuilder"/> passed from the <see cref="DbContext"/></param>
        public void Map(ModelBuilder builder)
        {
            InternalMap(builder.Entity<TEntityType>());
        }

        /// <summary>
        /// Implementy the Entity Type configuration for a <see cref="TEntityType"/>.
        /// </summary>
        /// <param name="builder">The <see cref="EntityTypeBuilder{TEntity}"/> to configure</param>
        protected abstract void InternalMap(EntityTypeBuilder<TEntityType> builder);
    }
}
```

And that's it for the mappings!

### Building a Base Class for the Data Access ###

Next we are defining an abstract ``SqlQueryContext``, which takes a ``DbConnection`` and our mappings:

* By explicitly passing a ``DbConnection`` we control the lifetime of the connection ourselves and not use Entity Framework. 
* By passing the Mappings into a ``DbContext`` and configuring the ``ModelBuilder``, we can query a ``DbSet`` without defining it explicitly.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Data.Common;

namespace LayeredArchitecture.DataAccess.Sql
{
    /// <summary>
    /// Implements a <see cref="DbContext"/> used for querying the database.
    /// </summary>
    public abstract class SqlQueryContext : DbContext
    {
        private readonly DbConnection connection;
        private readonly ILoggerFactory loggerFactory; 
        private readonly IEnumerable<IEntityTypeMap> mappings;

        /// <summary>
        /// Creates a new <see cref="DbContext"/> to query the database.
        /// </summary>
        /// <param name="loggerFactory">A Logger Factory to enable EF Core Logging facilities</param>
        /// <param name="connection">An opened <see cref="DbConnection"/> to enlist to</param>
        /// <param name="mappings">The <see cref="IEntityTypeMap"/> mappings for mapping query results</param>
        public SqlQueryContext(ILoggerFactory loggerFactory, DbConnection connection, IEnumerable<IEntityTypeMap> mappings)
        {
            this.connection = connection;
            this.mappings = mappings;
            this.loggerFactory = loggerFactory;
        }

        protected override void OnConfiguring(DbContextOptionsBuilder options)
        {
            OnConfiguring(options, connection, loggerFactory);
        }

        protected abstract void OnConfiguring(DbContextOptionsBuilder options, DbConnection connection, ILoggerFactory loggerFactory);

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            foreach (var mapping in mappings)
            {
                mapping.Map(modelBuilder);
            }
        }
    }
}
```

The implementation for the SQL Server then becomes very simple. We add some Logging for the ability to trace SQL queries, if needed:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Data.Common;

namespace LayeredArchitecture.DataAccess.Sql
{
    public class SqlServerQueryContext : SqlQueryContext
    {
        public SqlServerQueryContext(ILoggerFactory loggerFactory, DbConnection connection, IEnumerable<IEntityTypeMap> mappings)
            : base(loggerFactory, connection, mappings) { }

        protected override void OnConfiguring(DbContextOptionsBuilder options, DbConnection connection, ILoggerFactory loggerFactory)
        {
            options
                .UseLoggerFactory(loggerFactory)
                .EnableSensitiveDataLogging()
                .UseSqlServer(connection);
        }
    }
}
```

Now we want to be able to create this Context anywhere in code and not inject the DbContext directly, because ... 

1. Why should a DI container dictate where my business transaction starts and ends?
2. Why should all Service-level components become stateful by injecting a ``DbContext``?

So we are defining an abstract ``SqlQueryContextFactory`` base class. We force implementations to inject the Database 
mappings and an ``ILoggerFactory``, so implementations are able to use the .NET Core Logging abstractions:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Data.Common;

namespace LayeredArchitecture.DataAccess.Sql
{
    /// <summary>
    /// Generates a <see cref="SqlServerQueryContext"/> to query the database.
    /// </summary>
    public abstract class SqlQueryContextFactory
    {
        protected readonly ILoggerFactory loggerFactory;
        protected readonly IEnumerable<IEntityTypeMap> mappings;

        public SqlQueryContextFactory(ILoggerFactory loggerFactory, IEnumerable<IEntityTypeMap> mappings)
        {
            this.loggerFactory = loggerFactory;
            this.mappings = mappings;
        }

        public abstract SqlQueryContext Create(DbConnection connection);
    }
}
```

And now we can implement the SQL Server ``SqlServerQueryContextFactory``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Data.Common;

namespace LayeredArchitecture.DataAccess.Sql
{
    /// <summary>
    /// Generates a <see cref="SqlServerQueryContextFactory"/>.
    /// </summary>
    public class SqlServerQueryContextFactory : SqlQueryContextFactory
    {
        public SqlServerQueryContextFactory(ILoggerFactory loggerFactory, IEnumerable<IEntityTypeMap> mappings)
            : base(loggerFactory, mappings) { }

        public override SqlQueryContext Create(DbConnection connection)
        {
            return new SqlServerQueryContext(loggerFactory, connection, mappings);
        }
    }
}
```

And that's it for the Query Side!

### SQL Client ###

I want to keep all this as close as possible to the database. 

Because **no matter how hard you try to bridge the gap between your object model and a relational model, there will always be an impedance mismatch.** [^1] 

So for all my database interaction I want to have full control connection and transaction handling. 

All this is handled by the ``SqlClient`` abstraction, which prepares the ``DbContext`` accordingly:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Identity;
using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Data.Common;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace LayeredArchitecture.DataAccess.Sql
{
    /// <summary>
    /// Provides simplified Access to the <see cref="DbContext"/> for CRUD Operations and raw SQL Queries.
    /// </summary>
    public class SqlClient
    {
        /// <summary>
        /// A factory to generate a fresh DbContext for database queries.
        /// </summary>
        private readonly SqlQueryContextFactory sqlQueryContextFactory;

        /// <summary>
        /// Creates an <see cref="EntityFrameworkSqlClient"/> based on the given <see cref="IEntityTypeMap"/> mappings.
        /// </summary>
        /// <param name="sqlQueryContextFactory">A Factory to create a Query DbContext</param>
        public SqlClient(SqlQueryContextFactory sqlQueryContextFactory)
        {
            this.sqlQueryContextFactory = sqlQueryContextFactory;
        }

        /// <summary>
        /// SQL Query on the Database for an Entity Type.
        /// </summary>
        /// <typeparam name="TEntityType">Entity Type to Query for</typeparam>
        /// <param name="connection"><see cref="DbConnection"/> used to query</param>
        /// <param name="sql">SQL Command as <see cref="FormattableString"/> to prevent SQL Injection Attacks</param>
        /// <param name="config">Additional Configuration for Querying the data, such as including related data</param>
        /// <param name="cancellationToken">Optional <see cref="CancellationToken"/> to cancel the Operation</param>
        /// <returns>SQL Query results</returns>
        public async Task<List<TEntityType>> SqlQuery<TEntityType>(DbConnection connection, DbTransaction transaction, FormattableString sql, Func<IQueryable<TEntityType>, IQueryable<TEntityType>> config = null, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                var queryable = context.Set<TEntityType>()
                    .FromSqlInterpolated(sql)
                    .AsNoTracking();

                if (config != null)
                {
                    queryable = config(queryable);
                }

                return await queryable
                    .ToListAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Runs a LINQ Query for a given entity.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="query">The LINQ Query</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task<List<TEntityType>> QueryAsync<TEntityType>(DbConnection connection, DbTransaction transaction, Func<IQueryable<TEntityType>, IQueryable<TEntityType>> query, CancellationToken cancellationToken)
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                var entityQueryable = context
                    .Set<TEntityType>()
                    .AsQueryable();

                if (query != null)
                {
                    entityQueryable = query(entityQueryable);
                }

                return await entityQueryable
                    .AsNoTracking()
                    .ToListAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Executes Raw SQL Commands.
        /// </summary>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="sql">Formattable SQL Command</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task<int> ExecuteRawSql(DbConnection connection, DbTransaction transaction, FormattableString sql, CancellationToken cancellationToken)
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                return await context.Database
                    .ExecuteSqlInterpolatedAsync(sql, cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Inserts a given Entity into the Database.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="entity">Entity to insert</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task InsertAsync<TEntityType>(DbConnection connection, DbTransaction transaction, TEntityType entity, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                context.Entry(entity).State = EntityState.Added;

                await context
                    .SaveChangesAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Inserts a Range of Entities to the Database.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="entities">Entities to insert</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task InsertRangeAsync<TEntityType>(DbConnection connection, DbTransaction transaction, IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                foreach(var entity in entities)
                {
                    context.Entry(entity).State = EntityState.Added;
                }
                
                context
                    .Set<TEntityType>()
                    .AddRange(entities);

                await context
                    .SaveChangesAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Finds an entity with the given primary key values. If no entity is found, a null value is returned.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="keyValues">Primary Key Values</param>
        /// <returns>Entity or Null</returns>
        public async ValueTask<TEntityType> FindAsync<TEntityType>(DbConnection connection, DbTransaction transaction, object[] keyValues, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                return await context.Set<TEntityType>()
                    .FindAsync(keyValues, cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Finds an entity with the given primary key values. If no entity is found, a null value is returned.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="keyValues">Primary Key Values</param>
        /// <returns>Entity or Null</returns>
        public async ValueTask<TEntityType> FindAsync<TEntityType>(DbConnection connection, DbTransaction transaction, params object[] keyValues)
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                // TODO: Add CancellationToken
                await PrepareDbContextAsync(context, transaction, default(CancellationToken));

                return await context.Set<TEntityType>()
                    .FindAsync(keyValues)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Deletes an entity from the Database.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="entity">Entity to delete</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task DeleteAsync<TEntityType>(DbConnection connection, DbTransaction transaction, TEntityType entity, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                context.Entry(entity).State = EntityState.Deleted;

                await context
                    .SaveChangesAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Deletes a Range of Entities from the Database.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="entities">Entities to delete</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task DeleteRangeAsync<TEntityType>(DbConnection connection, DbTransaction transaction, IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                foreach (var entity in entities)
                {
                    context.Entry(entity).State = EntityState.Deleted;
                }

                await context
                    .SaveChangesAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Updates an entity in the Database.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="entity">Entity to delete</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task UpdateAsync<TEntityType>(DbConnection connection, DbTransaction transaction, TEntityType entity, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                context.Entry(entity).State = EntityState.Modified;

                await context
                    .SaveChangesAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        /// <summary>
        /// Updates a Range of Entities in the Database.
        /// </summary>
        /// <typeparam name="TEntityType">Type of the Entity</typeparam>
        /// <param name="connection">Current Connection</param>
        /// <param name="transaction">Current Transaction</param>
        /// <param name="entities">Entities to update</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        public async Task UpdateRangeAsync<TEntityType>(DbConnection connection, DbTransaction transaction, IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default(CancellationToken))
            where TEntityType : class
        {
            
            using (var context = sqlQueryContextFactory.Create(connection))
            {
                await PrepareDbContextAsync(context, transaction, cancellationToken);

                foreach (var entity in entities)
                {
                    context.Entry(entity).State = EntityState.Modified;
                }

                await context
                    .SaveChangesAsync(cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        #region Context Setup

        /// <summary>
        /// Prepares the underlying <see cref="DbContext"/>, so Automatic Transactions are disabled on SaveChanges 
        /// and the current Transaction for the Connection is supplied. So we enlist in the local transaction.
        /// </summary>
        /// <param name="context">The <see cref="DbContext"/></param>
        /// <param name="transaction">The <see cref="DbTransaction"/> of the current <see cref="DbConnectionScope"/></param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A Task</returns>
        private async Task PrepareDbContextAsync(SqlQueryContext context, DbTransaction transaction, CancellationToken cancellationToken)
        {
            if (transaction != null)
            {
                context.Database.AutoTransactionsEnabled = false;

                await context.Database
                    .UseTransactionAsync(transaction, cancellationToken)
                    .ConfigureAwait(false);
            }
        }

        #endregion
    }
}
```

### Data Access Objects ###

What's left for the Data Access Layer is having a Data Access Object implementation for not having to use the ``SqlClient`` directly. 

We start by writing an interface ``IDao``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace LayeredArchitecture.DataAccess.Dao
{
    /// <summary>
    /// The Data Access Object.
    /// </summary>
    /// <typeparam name="TEntityType">The Type of Entity for this DAO</typeparam>
    public interface IDao<TEntityType>
         where TEntityType : class
    {
        /// <summary>
        /// Inserts a <see cref="TEntityType"/>.
        /// </summary>
        /// <param name="entity">Entity</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        Task InsertAsync(TEntityType entity, CancellationToken cancellationToken = default);

        /// <summary>
        /// Inserts a range of <see cref="TEntityType"/>.
        /// </summary>
        /// <param name="entities">Entities to insert</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        Task InsertRangeAsync(IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default);

        /// <summary>
        /// Finds a <see cref="TEntityType"/> by its Primary Key.
        /// </summary>
        /// <param name="keyValues">Primary Key</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        ValueTask<TEntityType> FindAsync(object[] keyValues, CancellationToken cancellationToken = default);

        /// <summary>
        /// Finds a <see cref="TEntityType"/> by its Primary Key.
        /// </summary>
        /// <param name="keyValues">Primary Key</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        ValueTask<TEntityType> FindAsync(params object[] keyValues);

        /// <summary>
        /// Deletes a <see cref="TEntityType"/> from the database.
        /// </summary>
        /// <param name="entity">Entity</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        Task DeleteAsync(TEntityType entity, CancellationToken cancellationToken = default);

        /// <summary>
        /// Deletes a range of <see cref="TEntityType"/> from the database.
        /// </summary>
        /// <param name="entities">Entities</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        Task DeleteRangeAsync(IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default);

        /// <summary>
        /// Updates a <see cref="TEntityType"/>.
        /// </summary>
        /// <param name="entity">Entity</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        Task UpdateAsync(TEntityType entity, CancellationToken cancellationToken = default);

        /// <summary>
        /// Updates a range of <see cref="TEntityType"/>.
        /// </summary>
        /// <param name="entities">Entities</param>
        /// <param name="cancellationToken">CancellationToken</param>
        /// <returns>Task</returns>
        Task UpdateRangeAsync(IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default);

        /// <summary>
        /// Queries the Database asynchronously for a List of <see cref="TEntityType"/> based on an <see cref="IQueryable{TEntityType}"/> 
        /// passed to the method.
        /// </summary>
        /// <param name="query">Query to execute</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Results</returns>
        Task<List<TEntityType>> QueryAsync(Func<IQueryable<TEntityType>, IQueryable<TEntityType>> query = null, CancellationToken cancellationToken = default);

        /// <summary>
        /// Queries the Database asynchronously for a List of <see cref="TEntityType"/> based on a raw SQL Query. The result can be further 
        /// filtered or extended using the <paramref name="config"/> parameter.
        /// </summary>
        /// <param name="sql">SQL Query</param>
        /// <param name="config">Additional Query</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Results</returns>
        Task<List<TEntityType>> SqlQueryAsync(FormattableString sql, Func<IQueryable<TEntityType>, IQueryable<TEntityType>> config = null, CancellationToken cancellationToken = default);

        /// <summary>
        /// Executes raw SQL and returns the number of rows affected.
        /// </summary>
        /// <param name="sql">SQL Query</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Results</returns>
        Task<int> ExecuteRawSqlAsync(FormattableString sql, CancellationToken cancellationToken = default);
    }
}
```

Now the ``DaoBase<T>`` implementation uses the ``SqlClient`` to query the database and a ``DbConnectionScope`` to get hold of 
the current ``DbConnection`` and ``DbTransaction``, which we will look at in the next section.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Auditing;
using LayeredArchitecture.Base.Auditing.Exceptions;
using LayeredArchitecture.Base.Exensions;
using LayeredArchitecture.Base.Identity;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.DataAccess.Sql;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace LayeredArchitecture.DataAccess.Dao
{
    public abstract class DaoBase<TEntityType> : IDao<TEntityType>
        where TEntityType : class
    {
        private readonly SqlClient sqlClient;
        private readonly IUserAccessor userAccessor;
        private readonly IDbConnectionScopeResolver dbConnectionScopeResolver;

        public DaoBase(IDbConnectionScopeResolver dbConnectionScopeResolver, IUserAccessor userAccessor, SqlClient sqlClient) 
        {
            this.dbConnectionScopeResolver = dbConnectionScopeResolver;
            this.userAccessor = userAccessor;
            this.sqlClient = sqlClient;
        }

        public async Task<List<TEntityType>> QueryAsync(Func<IQueryable<TEntityType>, IQueryable<TEntityType>> query, CancellationToken cancellationToken = default)
        {
            var result = DbConnectionScope.GetConnection();

            return await sqlClient.QueryAsync(result.Connection, result.Transaction, query, cancellationToken);
        }

        public async Task<List<TEntityType>> SqlQueryAsync(FormattableString sql, Func<IQueryable<TEntityType>, IQueryable<TEntityType>> config = null, CancellationToken cancellationToken = default)
        {
            var result = DbConnectionScope.GetConnection();

            return await sqlClient.SqlQuery(result.Connection, result.Transaction, sql, config, cancellationToken);
        }

        public async Task<int> ExecuteRawSqlAsync(FormattableString sql, CancellationToken cancellationToken)
        {
            var result = DbConnectionScope.GetConnection();

            return await sqlClient.ExecuteRawSql(result.Connection, result.Transaction, sql, cancellationToken);
        }

        public async Task InsertAsync(TEntityType entity, CancellationToken cancellationToken = default)
        {
            HandleAuditedEntity(entity);
            
            var result = DbConnectionScope.GetConnection();

            await sqlClient.InsertAsync(result.Connection, result.Transaction, entity, cancellationToken);
        }

        public async Task InsertRangeAsync(IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default)
        {
            HandleAuditedEntities(entities);

            var result = DbConnectionScope.GetConnection();

            await sqlClient.InsertRangeAsync(result.Connection, result.Transaction, entities, cancellationToken);
        }

        public async ValueTask<TEntityType> FindAsync(object[] keyValues, CancellationToken cancellationToken = default)
        {
            var result = DbConnectionScope.GetConnection();

            return await sqlClient.FindAsync<TEntityType>(result.Connection, result.Transaction, keyValues, cancellationToken);
        }

        public async ValueTask<TEntityType> FindAsync(params object[] keyValues)
        {
            var result = DbConnectionScope.GetConnection();

            return await sqlClient.FindAsync<TEntityType>(result.Connection, result.Transaction, keyValues);
        }

        public async Task DeleteAsync(TEntityType entity, CancellationToken cancellationToken = default)
        {
            HandleAuditedEntity(entity);

            var result = DbConnectionScope.GetConnection();

            await sqlClient.DeleteAsync(result.Connection, result.Transaction, entity, cancellationToken);
        }

        public async Task DeleteRangeAsync(IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default)
        {
            HandleAuditedEntities(entities);

            var result = DbConnectionScope.GetConnection();

            await sqlClient.DeleteRangeAsync(result.Connection, result.Transaction, entities, cancellationToken);
        }

        public async Task UpdateAsync(TEntityType entity, CancellationToken cancellationToken = default)
        {
            HandleAuditedEntity(entity);

            var result = DbConnectionScope.GetConnection();

            await sqlClient.UpdateAsync(result.Connection, result.Transaction, entity, cancellationToken);
        }

        public async Task UpdateRangeAsync(IEnumerable<TEntityType> entities, CancellationToken cancellationToken = default)
        {
            HandleAuditedEntities(entities);

            var result = DbConnectionScope.GetConnection();

            await sqlClient.UpdateRangeAsync(result.Connection, result.Transaction, entities, cancellationToken);
        }

        protected DbConnectionScope DbConnectionScope => dbConnectionScopeResolver.Resolve();

        #region Audit Information

        private void HandleAuditedEntity(TEntityType entity)
        {
            HandleAuditedEntities(new[] { entity });
        }

        private void HandleAuditedEntities(IEnumerable<TEntityType> entities)
        {
            var isAuditedEntityType = typeof(IAuditedEntity).IsAssignableFrom(typeof(TEntityType));

            if (!isAuditedEntityType)
            {
                return;
            }

            var userId = GetUserId();

            foreach (var entity in entities)
            {
                ((IAuditedEntity)entity).UserId = userId;
            }
        }

        private string GetUserId()
        {
            if (userAccessor.User == null)
            {
                throw new MissingUserIdException();
            }

            var userId = userAccessor.User.GetUserId();

            if (userId == null)
            {
                throw new MissingUserIdException();
            }

            return userId;
        }

        #endregion
    }
}
```

So what is a ``DbConnectionScope`` and where are the connections created?

### Creating Connections ###

Let's do the simple part first and define a ``IDbConnectionFactory``, that will be used to create and open a Database Connection:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Data.Common;

namespace LayeredArchitecture.DataAccess.Base
{
    public interface IDbConnectionFactory
    {
        DbConnection Create();
    }
}
```

A simple default implementation for the SQL Server can look like this:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Data.SqlClient;
using System.Data.Common;

namespace LayeredArchitecture.DataAccess.Base
{
    public class SqlServerDbConnectionFactory : IDbConnectionFactory
    {
        private readonly string connectionString;

        public SqlServerDbConnectionFactory(string connectionString)
        {
            this.connectionString = connectionString;
        }

        public DbConnection Create()
        {
            return new SqlConnection(connectionString);
        }
    }
}
```

But bear with me. Let's add Multi-Tenancy from the start, because this requirement will **always** come in a project. 

Now as you know from my articles on Multi-Tenancy with Spring Boot, you know the simplest way to achieve Multi-Tenancy 
is to use isolated databases for each Tenant.

So we start by adding a class ``Tenant``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace LayeredArchitecture.Base.Tenancy.Model
{
    public class Tenant
    {
        /// <summary>
        /// ID.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Name.
        /// </summary>
        public string Name { get; set; }

        /// <summary>
        /// Description.
        /// </summary>
        public string Description { get; set; }
    }
}
```

Each Tenant has a ``TenantConfiguration``, that refers to the ``Tenant``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace LayeredArchitecture.Base.Tenancy.Model
{
    /// <summary>
    /// Settings for the <see cref="Tenant"/>, focus on Database here.
    /// </summary>
    public class TenantConfiguration
    {
        /// <summary>
        /// ID.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Unique Name of the Tenant.
        /// </summary>
        public string Name { get; set; }

        /// <summary>
        /// Connection String for Tenants database.
        /// </summary>
        public string ConnectionString { get; set; }

        /// <summary>
        /// Reference to the Tenant.
        /// </summary>
        public int TenantId { get; set; }
    }
}
```

And how do we get the current ``Tenant`` in the Application? By adding a way to resolve it with a ``ITenantResolver``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Tenancy.Model;

namespace LayeredArchitecture.Base.Tenancy
{
    /// <summary>
    /// An Interface to get the current Tenant.
    /// </summary>
    public interface ITenantResolver
    {
        Tenant Tenant { get; }
    }
}
```

And we can now rewrite the ``SqlServerDbConnectionFactory`` to use the ``ITenantResolver`` and a list of ``TenantConfiguration``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Tenancy;
using LayeredArchitecture.Base.Tenancy.Exceptions;
using LayeredArchitecture.Base.Tenancy.Model;
using Microsoft.Data.SqlClient;
using System;
using System.Collections.Generic;
using System.Data.Common;
using System.Linq;

namespace LayeredArchitecture.DataAccess.Base
{
    /// <summary>
    /// A default SQL Server-based factory to build <see cref="DbConnection"/> for a Tenant.
    /// </summary>
    public class SqlServerDbConnectionFactory : DbConnectionFactory
    {
        private readonly IDictionary<string, TenantConfiguration> tenants;

        public SqlServerDbConnectionFactory(ITenantResolver tenantResolver, IEnumerable<TenantConfiguration> tenants) 
            : base(tenantResolver)
        {
            this.tenants = tenants.ToDictionary(x => x.Name, x => x);
        }

        public override DbConnection Create(Tenant tenant)
        {
            if(tenant == null)
            {
                throw new ArgumentNullException(nameof(tenant));
            }

            if(!tenants.ContainsKey(tenant.Name))
            {
                throw new MissingTenantConfigurationException($"No TenantConfiguration registered for Tenant '{tenant.Name}'");
            }

            var connectionString = tenants[tenant.Name].ConnectionString;

            if(string.IsNullOrWhiteSpace(connectionString))
            {
                throw new InvalidTenantConfigurationException($"No Connection String registered for Tenant '{tenant.Name}'");
            }

            return new SqlConnection(connectionString);
        }
    }
}
```

Job done!

### DbConnectionScope ###

Next we need a way to provide a ``DbConnection`` and ``DbTransaction`` to the Data Access Object. The implementation I used is 
a mishmash of the great ``Dapper.AmbientContext`` library mixed with a little bit of ``TransactionScope``, which is available at:

* [https://github.com/sakopov/Dapper.AmbientContext](https://github.com/sakopov/Dapper.AmbientContext)

The basic idea is the following. We have an ``AsyncLocal``, which holds a ``ContextKey``. This ``ContextKey`` is used to lookup 
an immutable stack of ``DbConnectionScope`` instances. In theory an ``AsyncLocal`` passes the value with the flow as a shallow 
copy, which is well explained by Stephen Cleary here:

* [https://blog.stephencleary.com/2013/04/implicit-async-context-asynclocal.html](https://blog.stephencleary.com/2013/04/implicit-async-context-asynclocal.html)
 
So we pass the current ``DbConnectionScope`` in an ``ImmutableStack``. If we are the initiator of the async flow, we are creating a 
new connection using the ``IDbConnectionFactory`` and start a new transaction. Only the outer-most scope then will be allowed commit 
the transaction:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Immutable;
using System.Data;
using System.Data.Common;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

namespace LayeredArchitecture.DataAccess.Base
{
    internal sealed class ContextKey
    {
    }

    internal static class AsyncLocalStorage
    {
        private static readonly AsyncLocal<ContextKey> CurrentContextKey = new AsyncLocal<ContextKey>();

        private static readonly ConditionalWeakTable<ContextKey, ImmutableStack<DbConnectionScope>> DbConnectionScopes = new ConditionalWeakTable<ContextKey, ImmutableStack<DbConnectionScope>>();

        public static void SaveStack(ImmutableStack<DbConnectionScope> stack)
        {
            var contextKey = CurrentContextKey.Value;

            if (contextKey == null)
            {
                throw new Exception("No Key found for Scope.");
            }

            if (DbConnectionScopes.TryGetValue(contextKey, out _))
            {
                DbConnectionScopes.Remove(contextKey);
            }

            DbConnectionScopes.Add(contextKey, stack);
        }

        public static ImmutableStack<DbConnectionScope> GetStack()
        {
            var contextKey = CurrentContextKey.Value;

            if (contextKey == null)
            {
                contextKey = new ContextKey();

                CurrentContextKey.Value = contextKey;
                DbConnectionScopes.Add(contextKey, ImmutableStack.Create<DbConnectionScope>());
            }

            bool keyFound = DbConnectionScopes.TryGetValue(contextKey, out var dbConnectionScopes);

            if (!keyFound)
            {
                throw new Exception("Stack not found for this DbConnectionScope");
            }

            return dbConnectionScopes;
        }
    }

    public class DbConnectionScope : IDisposable
    {
        protected DbConnectionScope Parent;
        protected DbConnection Connection;
        protected DbTransaction Transaction;
        protected IsolationLevel IsolationLevel;
        protected bool Suppress;

        public DbConnectionScope(DbConnection connection, bool join, bool suppress, IsolationLevel isolationLevel)
        {
            var currentStack = AsyncLocalStorage.GetStack();

            IsolationLevel = isolationLevel;
            Suppress = suppress;
            Connection = connection;

            if (join)
            {
                if (!currentStack.IsEmpty)
                {
                    var parent = currentStack.Peek();

                    Parent = parent;
                    Connection = parent.Connection;
                    Transaction = parent.Transaction;
                    Suppress = parent.Suppress;
                    IsolationLevel = parent.IsolationLevel;
                }
            }

            currentStack = currentStack.Push(this);

            AsyncLocalStorage.SaveStack(currentStack);
        }

        public async Task<Tuple<DbConnection, DbTransaction>> GetConnectionAsync(CancellationToken cancellationToken)
        {
            if (Parent == null && Connection.State != ConnectionState.Open)
            {
                await Connection.OpenAsync(cancellationToken).ConfigureAwait(false);

                if (!Suppress)
                {
                    Transaction = Connection.BeginTransaction(IsolationLevel);
                }
            }

            // Has a parent but their connection was never opened
            if (Parent != null && Parent.Connection.State == ConnectionState.Closed)
            {
                await Parent.Connection.OpenAsync(cancellationToken).ConfigureAwait(false);

                if (!Parent.Suppress)
                {
                    Parent.Transaction = Parent.Connection.BeginTransaction(Parent.IsolationLevel);
                }
            }

            // Opened the parent transaction, now inherit their transaction
            if (Parent != null && Parent.Connection.State == ConnectionState.Open)
            {
                if (Parent.Transaction != null && Transaction == null)
                {
                    Transaction = Parent.Transaction;
                }
            }

            return Tuple.Create(Connection, Transaction);
        }

        public void Commit()
        {
            if (Parent != null)
            {
                return;
            }

            try
            {
                if (Transaction != null)
                {
                    Transaction.Commit();
                    Transaction.Dispose();
                    Transaction = null;
                }
            }
            catch (Exception)
            {
                Rollback();

                throw;
            }
        }

        public void Rollback()
        {
            if (Parent != null)
            {
                return;
            }

            try
            {
                if (Transaction != null)
                {
                    Transaction.Rollback();
                    Transaction.Dispose();
                    Transaction = null;
                }
            }
            catch (Exception)
            {
                if (Transaction != null && Transaction.Connection != null)
                {
                    Transaction.Dispose();
                    Transaction = null;
                }

                throw;
            }
        }

        public void Dispose()
        {
            var currentStack = AsyncLocalStorage.GetStack();

            if (currentStack.IsEmpty)
            {
                throw new Exception("Could not dispose scope because it does not exist in storage.");
            }

            var topItem = currentStack.Peek();

            if (this != topItem)
            {
                throw new InvalidOperationException("Could not dispose scope because it is not the active scope. This could occur because scope is being disposed out of order.");
            }

            currentStack = currentStack.Pop();

            AsyncLocalStorage.SaveStack(currentStack);

            if (Parent == null)
            {
                if (Transaction != null)
                {
                    Commit();
                }

                if (Connection != null)
                {
                    if (Connection.State == ConnectionState.Open)
                    {
                        Connection.Close();
                    }

                    Connection.Dispose();
                    Connection = null;
                }
            }

            GC.SuppressFinalize(this);
            GC.WaitForPendingFinalizers();
        }
    }
}
```

What's left is a way to create a new ``DbConnectionScope``, when we need it. 

So we define a ``DbConnectionScopeFactory`` and take a dependency on a ``IDbConnectionFactory``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Data;

namespace LayeredArchitecture.DataAccess.Base
{
    public class DbConnectionScopeFactory
    {
        private readonly IDbConnectionFactory dbConnectionFactory;

        public DbConnectionScopeFactory(IDbConnectionFactory dbConnectionFactory)
        {
            this.dbConnectionFactory = dbConnectionFactory;
        }

        public DbConnectionScope Create(bool join = true, bool suppress = false, IsolationLevel isolationLevel = IsolationLevel.ReadCommitted)
        {
            var connection = dbConnectionFactory.Create();

            if (connection.State != ConnectionState.Closed)
            {
                throw new Exception("The database connection factory returned a database connection in a non-closed state. This behavior is not allowed as the ambient database scope will maintain database connection state as required.");
            }

            return new DbConnectionScope(connection, join, suppress, isolationLevel);
        }
    }
}
```

And in the Data Access Layer we need a way to resolve the current ``DbConnectionScope``, which is done using a ``DbConnectionScopeProvider``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace LayeredArchitecture.DataAccess.Base
{
    public class DbConnectionScopeProvider : IDbConnectionScopeProvider
    {
        public DbConnectionScope Resolve()
        {
            var immutableStack = AsyncLocalStorage.GetStack();

            if(immutableStack.IsEmpty)
            {
                throw new Exception("There is no active DbConnectionScope");
            }

            return immutableStack.Peek();
        }
    }
}
```

### Creating and Applying Migrations ###

Next thing on our list: Database Migrations. The ``SqlQueryContext`` expects us to pass a ``DbConnection`` to it's constructor. This 
doesn't play nice with the .NET Core Tooling (of course). So for the migrations we will define a separate ``DbContext``, that is used 
for Migrations exclusively:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.EntityFrameworkCore;
using System.Collections.Generic;

namespace LayeredArchitecture.DataAccess.Sql
{
    public class SqlMigrationsContext : DbContext
    {
        private readonly IEnumerable<IEntityTypeMap> mappings;

        public SqlMigrationsContext(DbContextOptions<SqlMigrationsContext> options, IEnumerable<IEntityTypeMap> mappings)
            : base(options)
        {
            this.mappings = mappings;
        }


        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            foreach (var mapping in mappings)
            {
                mapping.Map(modelBuilder);
            }
        }
    }
}
```

And for the .NET CLI tooling we derive from an ``IDesignTimeDbContextFactory<TDbContext>``. In it a ``SqlMigrationsContext`` will be 
created. We also add two abstract methods to configure the ``SqlMigrationsContext`` and provide the dependencies for it:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.DependencyInjection;

namespace LayeredArchitecture.DataAccess.Sql
{
    public abstract class SqlMigrationsContextFactory : IDesignTimeDbContextFactory<SqlMigrationsContext>
    {
        public SqlMigrationsContext CreateDbContext(string[] args)
        {
            // Register all Dependencies:
            var services = new ServiceCollection();

            RegisterDependencies(services);

            // Build the ServiceProvider:
            var serviceProvider = services.BuildServiceProvider();

            // Get the Entity Mappings:
            var entityTypeMappings = serviceProvider.GetServices<IEntityTypeMap>();

            // Builder the Options:
            var builder = new DbContextOptionsBuilder<SqlMigrationsContext>();

            ConfigureDbContextOptions(builder);

            // Build the Context:
            return new SqlMigrationsContext(builder.Options, entityTypeMappings);
        }

        /// <summary>
        /// Configures the DbContext, for example the Database to use.
        /// </summary>
        /// <param name="builder"></param>
        protected abstract void ConfigureDbContextOptions(DbContextOptionsBuilder<SqlMigrationsContext> builder);

        /// <summary>
        /// Registers the Dependencies needed to bootstrap the MigrationsContext.
        /// </summary>
        /// <param name="services"></param>
        protected abstract void RegisterDependencies(ServiceCollection services);
    }
}
```

In a real project an implementation of the Migration Context may look like this:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Sql;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace LayeredArchitecture.Tests.DataAccess.Migrations
{
    public class CustomMigrationsContext : SqlMigrationsContextFactory
    {
        protected override void ConfigureDbContextOptions(DbContextOptionsBuilder<SqlMigrationsContext> builder)
        {
            builder
                .UseSqlServer(@"Data Source=localhost\SQLEXPRESS;Initial Catalog=SampleDb;Integrated Security=SSPI;", 
                    b => b.MigrationsAssembly("LayeredArchitecture.Tests"));
        }

        protected override void RegisterDependencies(ServiceCollection services)
        {
            Bootstrapper.RegisterDependencies(services);
        }
    }
}
```

We can then use the Package Manager Console or the dotnet CLI to add the Migrations like this:

```
PM> Add-Migration InitialCreate -o "Sample/DataAccess/Migrations/History"
```

And the Package Manager Console can be used to create the Database:

```
PM> Update-Database
```

### Conclustion ###

And that's it for the Data Access, we can now cross a lot of points off of our list:

* ✅ Data Access
* ✅ Multi-Tenancy
* ✅ Database Migrations
* ⬜ Audit Trails
* ⬜ Versioning
* ⬜ Optmistic Concurrency
* ⬜ Logging
* ⬜ Testing

## Auditing and Versioning ##

If you have been in this industry long enough, there's one requirement that **always** comes late in a project: Auditing and Versioning.

But no one really knows a simple approach Auditing and Versioning with SQL, .NET and Entity Framework. And that left me wondering: How would 
I approach data auditing in a way, that 1. puts minimal work on me, 2. contains a minimum amount of magic and 3. is understandable for a future 
developer?

When it comes to Auditing and Versioning in a system there are a lot of question coming to my mind instantly:

* What about Stored Procedures writing to your database?
* What about Bulk Inserts? Are those tracked as well?
* What about Database Migrations? How will those be audited?
* What about someone directly running updates on the database?
* What about adding and removing columns?
* What about querying historic data at a specific point in time?
* What if we need to recover data at a specific time?
* ...

Are all those use-cases supported as well? We know *all of this* happens in real life.

The general advice to me has always been "Just add ``CreatedBy``, ``CreatedAt``, ``ModifiedBy`` and ``ModifiedAt`` columns! Why overthink 
this?", "Maybe override the Entity Framework ``DbContext#SaveAll`` method and extend it a bit?". Well, where are examples? Stackoverflow is 
also very vague on it. 

Do I want to develop my own (badly implemented) Entity Framework Auditing library? Not really. Do I have time for that at all? Not really. Or 
should I use yet another NuGet package, where the maintainer may lose interest? Dangerous. Do I want to develop my own trigger-based solution? 
Not really. 

> The less code, the less errors, the less maintenance, the less fingerpointing, the better. 

Let's just use the most straightforward way for the database system at hand and abstract just a tiny bit. 

### Temporal Tables ###

The ANSI SQL 2011 Standard added Temporal Tables to the SQL Feature Set.

[According to Microsoft](https://docs.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables) a Temporal Table 
is ...

> [...] a type of user table designed to keep a full history of data changes  to allow easy point in time 
> analysis. This type of temporal table is referred to as a system-versioned temporal table because the period 
> of validity for each row is managed by the system (i.e. database engine).
>
> Every temporal table has two explicitly defined columns, each with a datetime2 data type. These columns are 
> referred to as period columns. These period columns are used exclusively by the system to record period of 
> validity for each row whenever a row is modified.
>
> In addition to these period columns, a temporal table also contains a reference to another table with a mirrored 
> schema. The system uses this table to automatically store the previous version of the row each time a row in the 
> temporal table gets updated or deleted. This additional table is referred to as the history table, while the main 
> table that stores current (actual) row versions is referred to as the current table or simply as the temporal 
> table. During temporal table creation users can specify existing history table (must be schema compliant) or let 
> system create default history table.

And in the Section "Why temporal" it specifically refers to Auditing as ...

> Real data sources are dynamic and more often than not business decisions rely on insights that analysts can get 
> from data evolution. Use cases for temporal tables include:
>
> * Auditing all data changes and performing data forensics when necessary
> * ...

So it seems we are on the right track here. Great!

### How to define a Temporal Table ###

In the following SQL snippet I am using SQL Server to create a table ``[dbo].[Address]``, which holds the current data and a table 
``[history].[AddressHistory]`` to keep historic data. Each table contains the columns ``SysStartTime`` and ``SysEndTime``, which 
indicate the validity of the row relative to the system time.

```sql
IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[history].[AddressHistory]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [history].[AddressHistory](
        [AddressID] INT NOT NULL
        , [Name1] [NVARCHAR](255)
        , [Name2] [NVARCHAR](255)
        , [Street] [NVARCHAR](2000)
        , [ZipCode] [NVARCHAR](255)
        , [City] [NVARCHAR](255)
        , [Country] [NVARCHAR](255)
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT]
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 NOT NULL
        , [SysEndTime] DATETIME2 NOT NULL
    );

END
GO

IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[dbo].[Address]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [dbo].[Address](
        [AddressID] INT NOT NULL IDENTITY PRIMARY KEY
        , [Name1] [NVARCHAR](255)
        , [Name2] [NVARCHAR](255)
        , [Street] [NVARCHAR](2000)
        , [ZipCode] [NVARCHAR](255)
        , [City] [NVARCHAR](255)
        , [Country] [NVARCHAR](255)
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT]
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL
        , [SysEndTime] DATETIME2 GENERATED ALWAYS AS ROW END NOT NULL
        , PERIOD FOR SYSTEM_TIME (SysStartTime, SysEndTime)
        , CONSTRAINT CHK_Address_AuditOperation CHECK (AuditOperation in (1, 2, 3))
    ) 
    WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [history].[AddressHistory]));

END
GO
```

### Where to get the Audit User from? ###

Most important question for an Audit: Who changed the data? 

In the example you can already see, that each table contains a ``AuditUser`` column with a ``NOT NULL`` 
constraint. So we are required to pass the username on every insert and update. But where does it come 
from?

It depends. In a WPF Application it is most probably the current Windows User. In an ASP.NET Core application, 
it is most probably resolved from the ``HttpContext``. 

So in the application code we start by defining an interface ``IUserAccessor``, which will return the 
``ClaimsPrincipal`` for the current context (whatever that means):

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Security.Claims;

namespace LayeredArchitecture.Base.Identity
{
    /// <summary>
    /// Accesses the <see cref="ClaimsPrincipal"/> for the current context, for example through 
    /// a <see cref="IHttpContextAccessor"/> or other implementations.
    /// </summary>
    public interface IUserAccessor
    {
        /// <summary>
        /// Access the <see cref="ClaimsPrincipal"/> for this context.
        /// </summary>
        ClaimsPrincipal User { get; }
    }
}
```

For testing purposes we can define a very simple mock version of the ``IUserAccessor``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Security.Claims;

namespace LayeredArchitecture.Base.Identity
{
    /// <summary>
    /// A Mock for Testing Purposes.
    /// </summary>
    public class MockUserAccessor : IUserAccessor
    {
        public ClaimsPrincipal User => BuildMockClientPrincipal();

        private ClaimsPrincipal BuildMockClientPrincipal()
        {
            var mockClaimIdentity = new ClaimsIdentity();

            mockClaimIdentity.AddClaim(new Claim(ClaimTypes.NameIdentifier, "MOCK_USER"));

            return new ClaimsPrincipal(mockClaimIdentity);
        }
    }
}
```

Next question for an Audit is: What Data Change Operation has been performed? An ``UPDATE``, ``INSERT`` or ``DELETE``?.

We model it as ``DataChangeOperation`` enumeration:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace LayeredArchitecture.Base.Auditing
{
    /// <summary>
    /// The Operation executed on the Audited Entity.
    /// </summary>
    public enum DataChangeOperationEnum
    {
        /// <summary>
        /// Insert.
        /// </summary>
        Insert = 1,

        /// <summary>
        /// Update.
        /// </summary>
        Update = 2,

        /// <summary>
        /// Delete.
        /// </summary>
        Delete = 3
    }
}
```

Each entity that should be audited then implements the ``IAuditedEntity`` interface:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace LayeredArchitecture.Base.Auditing
{
    /// <summary>
    /// A class implementing this interface supplies a User ID and may supply a Entity Version or 
    /// receive it from a database generated value (e.g. AFTER INSERT / UPDATE Triggers).
    /// </summary>
    public interface IAuditedEntity
    {
        /// <summary>
        /// A UserId.
        /// </summary>
        string AuditUser { get; set; }

        /// <summary>
        /// Audit Operation (Insert, Update, Delete)
        /// </summary>
        DataChangeOperationEnum AuditOperation { get; set; }

        /// <summary>
        /// Version.
        /// </summary>
        long EntityVersion { get; set; }
    }
}
```

And now the final step to pass the data to the SQL Server for ``INSERT``, ``UPDATE`` and ``DELETE`` operations. 

I initially experimented with a ``SESSION_CONTEXT``, used ``INSTEAD OF`` and ``AFTER`` triggers. but honestly? It all turned out way too brittle.

We are supplying the additional audit data only on application-level and  add a ``HandleAuditedEntities`` method to the Data Access Object:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Auditing;
using LayeredArchitecture.Base.Auditing.Exceptions;
using LayeredArchitecture.Base.Exensions;
using LayeredArchitecture.Base.Identity;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.DataAccess.Sql;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace LayeredArchitecture.DataAccess.Dao
{
    public abstract class DaoBase<TEntityType> : IDao<TEntityType>
        where TEntityType : class
    {
    
        // ...
        
        #region Append Audit Information

        private async Task HandleAuditedEntity(ConnectionTransactionHolder connectionTransactionHolder, TEntityType entity, AuditOperationEnum operation, CancellationToken cancellationToken)
        {
            await HandleAuditedEntities(connectionTransactionHolder, new[] { entity }, operation, cancellationToken);
        }

        private async Task HandleAuditedEntities(ConnectionTransactionHolder connectionTransactionHolder, IEnumerable<TEntityType> entities, AuditOperationEnum operation, CancellationToken cancellationToken)
        {
            var isAuditedEntityType = typeof(IAuditedEntity).IsAssignableFrom(typeof(TEntityType));

            if (!isAuditedEntityType)
            {
                return;
            }

            var userId = GetUserId();

            foreach (var entity in entities)
            {
                ((IAuditedEntity)entity).AuditUser = userId;
                ((IAuditedEntity)entity).AuditOperation = operation;
                ((IAuditedEntity)entity).EntityVersion = ((IAuditedEntity)entity).EntityVersion + 1;
            }

            // This isn't probably the best way. When we have an audited entity we need to update the deleted entities first, so the deleted operation
            // is reflected in the Temporal Table when actually deleting the entity. This is done to keep us from maintaining yet another Audit-table,
            // when we could keep this information simply in the audited record itself.
            //
            // The Entity Version won't increase for the Operation.
            if (operation == AuditOperationEnum.Delete)
            {
                await sqlClient.UpdateRangeAsync(connectionTransactionHolder.Connection, connectionTransactionHolder.Transaction, entities, cancellationToken);
            }
        }

        private string GetUserId()
        {
            if (userAccessor.User == null)
            {
                throw new MissingUserIdException();
            }

            var userId = userAccessor.User.GetUserId();

            if (userId == null)
            {
                throw new MissingUserIdException();
            }

            return userId;
        }

        #endregion
    }
}
```

The only thing, that's not nice in the implementation is the additional update before running a ``DELETE``. This is done, so that the DELETE Operation also goes into the 
temporal table. Other Databasess like DB2 have an ``ON DELETE ADD EXTRA ROW`` statement to add extra rows into the temporal table on delete, and they provide a way to add 
the Data Change Operation by themselves.

Anyway... 

Implementing this Audit Trail:

* Took no time.
* Is going to work just fine for a SQL Server. 
* Has no additional implementation costs.
* May satisfy your Stakeholders?

### Conclusion ###

Providing Auditing and Versioning was simpler, than expected. Let's update the list:

* ✅ Data Access
* ✅ Multi-Tenancy
* ✅ Database Migrations
* ✅ Audit Trails
* ✅ Versioning
* ⬜ Optmistic Concurrency
* ⬜ Logging
* ⬜ Testing


## Optimistic Concurrency ##

There is something I suggest: Add a ``ROWVERSION`` column to all your tables. It doesn't cost you a thing database-side. 

We can then use this column as the row version to handle optimistic locking, which is ...

> [...] a strategy where you read a record, take note of a version number (other methods to do this involve dates, 
> timestamps or checksums/hashes) and check that the version hasn't changed before you write the record back. When you write the 
> record back you filter the update on the version to make sure it's atomic. (i.e. hasn't been updated between when you check the 
> version and write the record to the disk) and update the version in one hit.
>
> If the record is dirty (i.e. different version to yours) you abort the transaction and the user can re-start it.

Imagine we define a class ``Person``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Auditing;
using LayeredArchitecture.DataAccess.Base;
using System;

namespace LayeredArchitecture.Example.Domain
{
    /// <summary>
    /// Person.
    /// </summary>
    public class Person : IAuditedEntity, IStatefulEntity
    {
        // ...
        
        /// <summary>
        /// RowVersion Concurrency Token.
        /// </summary>
        public byte[] RowVersion { get; set; }

        // ...
    }
}
```

And then implement an ``EntityTypeMap<Person>`` to define the ``RowVersion`` column as a concurrency token:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using LayeredArchitecture.Example.Domain;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace LayeredArchitecture.Example.DataAccess.Mappings
{
    public class PersonTypeMap : EntityTypeMap<Person>
    {
        protected override void InternalMap(EntityTypeBuilder<Person> builder)
        {
            builder
                .ToTable("Person", "dbo");

            builder
                .HasKey(x => x.Id);

            // ...
            
            builder
                .Property(x => x.RowVersion)
                .HasColumnName("RowVersion")
                .IsRowVersion();
        }
    }
}
```

### Conclusion ###

By using Entity Framework Core it was a no brainer to add Optimistic Concurrency:

* ✅ Data Access
* ✅ Multi-Tenancy
* ✅ Database Migrations
* ✅ Audit Trails
* ✅ Versioning
* ✅ Optmistic Concurrency
* ⬜ Logging
* ⬜ Testing

## Logging ##

What's the most important thing in an application? Logging, Logging, Logging and... Logging! 

You want to know:

* What method has been executed? 
* What's the SQL, that has been generated?
* How long did the invocation take?
* Which Thread has the method been executed on?
* Which continuation does this call belong to, if .NET awaits the continuation on another thread?
* Which Tenant is the call related to?
* Which User initiated the call?
* Which ``X-Correlation-ID`` header was passed to the Webserver?
* Oh and which Machine are we running on?
* What is the Process ID and Process Name?
* ...

And once you are done, you probably want to evaluate your logs? Structured Logging to rescue! 

I will show how to use *Serilog* to answer most of the questions above:

* [https://serilog.net/](https://serilog.net/)

### Log Method Arguments, Entry and Exit ###

AOP provides a good way for handling Cross Cutting Concerns, such as debugging and instrumentation, which may 
come in handy for tracing really hard production-level bugs. Those bugs where you cannot simply attach a Debugger 
and everything you can get is a Log file.

So before using an AOP library I experimented with a .NET Core [DispatchProxy] or frameworks like [Scrutor], but it didn't 
really work well. And it's much more on the implementation-side (read maintenance-side!), than I am willing to accept. The 
instrumentation code should be no more than 20 lines of code. And I don't want to overcomplicate the DI configuration.

There is a great project called [MrAdvice], which provides a simple way to defined Aspects for intercepting asynchronous 
calls. And with it we can easily write a ``LogAspectAttribute``, that can be used to attribute methods or classes and 
logs method invocations plus their arguments:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ArxOne.MrAdvice.Advice;
using Serilog;
using Serilog.Events;
using System;
using System.Threading.Tasks;

namespace LayeredArchitecture.Base.Aspects
{
    /// <summary>
    /// Advises a method for Trace Logging using the MrAdvice Framework. It excludes any Logging for Constructor Invocations. 
    /// 
    /// This enables to get a verbose trace, if you for example need to trace errors in a Remote System.
    /// </summary>
    [Serializable]
    [AttributeUsage(AttributeTargets.All, AllowMultiple = true)]
    public class LogAspectAttribute : Attribute, IMethodAsyncAdvice
    {
        public async Task Advise(MethodAsyncAdviceContext context)
        {
            if (!context.TargetMethod.IsConstructor)
            {
                if (Log.IsEnabled(LogEventLevel.Verbose))
                {
                    Log.Logger.Verbose("Entering Method {DeclaringType}.{Method} (Arguments {@Arguments})", context.TargetMethod.DeclaringType.FullName, context.TargetMethod.Name, context.Arguments);
                }
            }

            await context.ProceedAsync();

            if (!context.TargetMethod.IsConstructor)
            {
                if (Log.IsEnabled(LogEventLevel.Verbose))
                {
                    Log.Logger.Verbose("Exiting Method {DeclaringType}.{Method}", context.TargetMethod.Name, context.Arguments);
                }
            }
        }
    }
}
```

And if you now want to Log all method calls in a class, you just add the ``LogAspect`` Attribute and call it a day:

```csharp
// ...

namespace LayeredArchitecture.Example.Business
{
    [LogAspect] // <----
    public class PersonService : IPersonService
    {
        // ...
    }
    
    // ...
}
```

The Verbose output in the log is then is going to look like this:

```
2021-07-02 08:10:53.405 +02:00 [VRB] Entering Method LayeredArchitecture.Example.Business.PersonService.AssignAddressAsync (Arguments [7, 7, "2021-07-02T08:10:53.4044371+02:00", {"IsCancellationRequested": false}]) {ProcessId=19388, ProcessName="LayeredArchitecture.Example", ThreadId=1, ThreadCorrelationId=5ef1d07c-043b-436c-8ae0-d3c31d9f0731, MachineName="DESKTOP-C4ORD8V", TenantId=1, UserId="MOCK_USER"}
...
2021-07-02 08:10:53.075 +02:00 [VRB] Exiting Method AddOrUpdatePersonAsync.["LayeredArchitecture.Example.Domain.Person","System.Threading.CancellationToken"] { ProcessId: 19388, ProcessName: "LayeredArchitecture.Example", ThreadId: 1, ThreadCorrelationId: 5ef1d07c-043b-436c-8ae0-d3c31d9f0731, MachineName: "DESKTOP-C4ORD8V", TenantId: 1, UserId: "MOCK_USER" }
```

There is surely a lot to improve of course: 

* Is it worth to pollute the log file with serialized arguments like a ``CancellationToken``? 
* What if you want to log Constructor invocations?
* ...

But let's make it complicated. [MrAdvice] *just works* and is simple to use.

[Scrutor]: https://andrewlock.net/adding-decorated-classes-to-the-asp.net-core-di-container-using-scrutor/
[DispatchProxy]: https://devblogs.microsoft.com/dotnet/migrating-realproxy-usage-to-dispatchproxy/
[MrAdvice]: https://github.com/ArxOne/MrAdvice/

### Serilog Enrichers and Extensions ###

Serilog provides a simple way to add additional properties to the Logger by implementing an ``ILogEventEnricher``. We need this, 
so we can add data to correlate log entries and answer some of the questions raised above. Serilog also provides a NuGet package
``Serilog.Extensions.Hosting``, that makes it possible to use Dependency Injection by hooking into the ``HostBuilder`` pipeline.

#### MachineIdEnricher ####

We start by adding an Enricher, that provides the MachineName of the Environment we are running in. The MachineName is very 
unlikely to change, so we can cache it and don't need to recreate the Property on each Logger invocation:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Serilog.Core;
using Serilog.Events;
using System;

namespace LayeredArchitecture.Base.Serilog
{
    /// <summary>
    /// Adds the <see cref="Environment.MachineName"/> to a Log Entry.
    /// </summary>
    public class MachineNameEnricher : ILogEventEnricher
    {
        private LogEventProperty cachedLogEvent;

        public const string MachineNameEnricherPropertyName = "MachineName";

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            cachedLogEvent = cachedLogEvent ?? propertyFactory.CreateProperty(MachineNameEnricherPropertyName, Environment.MachineName);

            logEvent.AddPropertyIfAbsent(cachedLogEvent);
        }
    }
}
```

#### ProcessIdEnricher ###

From the ``System.Diagnostics.Process`` we can get the current Process Id and Process Name.

The ProcessIdEnricher

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Serilog;
using Serilog.Configuration;
using Serilog.Core;
using Serilog.Events;
using System;

namespace LayeredArchitecture.Base.Serilog
{
    /// <summary>
    /// Adds a the current Id of the <see cref="System.Diagnostics.Process"/> to the Log entry.
    /// </summary>
    public class ProcessIdEnricher : ILogEventEnricher
    {
        LogEventProperty cachedLogEvent;

        public const string ProcessIdPropertyName = "ProcessId";

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var currentProcessId = System.Diagnostics.Process.GetCurrentProcess().Id;

            cachedLogEvent = cachedLogEvent ?? propertyFactory.CreateProperty(ProcessIdPropertyName, currentProcessId);

            logEvent.AddPropertyIfAbsent(cachedLogEvent);
        }
    }

    /// <summary>
    /// Adds a the current Name of the <see cref="System.Diagnostics.Process"/> to the Log entry.
    /// </summary>
    public class ProcessNameEnricher : ILogEventEnricher
    {
        LogEventProperty cachedLogEvent;

        public const string ProcessNamePropertyName = "ProcessName";

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var currentProcessName = System.Diagnostics.Process.GetCurrentProcess().ProcessName;

            cachedLogEvent = cachedLogEvent ?? propertyFactory.CreateProperty(ProcessNamePropertyName, currentProcessName);

            logEvent.AddPropertyIfAbsent(cachedLogEvent);
        }
    }
}
```

#### ThreadIdEnricher ###

If you are writing parallel and asynchronous code, it might be useful to know which Thread a call was executed on. We can write 
a ``ThreadIdEnricher`` to get (and cache) the ThreadId. We are again caching it, so we don't have to create the Property for 
each Log entry.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Serilog;
using Serilog.Configuration;
using Serilog.Core;
using Serilog.Events;
using System;

namespace LayeredArchitecture.Base.Serilog
{
    /// <summary>
    /// Adds the Thread ID of the <see cref="Environment"/> to the Log entry.
    /// </summary>
    public class ThreadIdEnricher : ILogEventEnricher
    {
        public const string ThreadIdPropertyName = "ThreadId";

        private int cachedThreadId;
        private LogEventProperty cachedLogEvent;

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var currentThreadId = Environment.CurrentManagedThreadId;
            
            if (cachedLogEvent == null || cachedThreadId != currentThreadId)
            {
                cachedThreadId = currentThreadId;
                cachedLogEvent = cachedLogEvent ?? propertyFactory.CreateProperty(ThreadIdPropertyName, currentThreadId);
            }

            logEvent.AddPropertyIfAbsent(cachedLogEvent);
        }
    }
}
```

#### ThreadCorrelationId ###

There is no guarantee in C\#, that a continuation always awaits on the same thread. That's why a Threads ID might not be sufficient to 
correlate asynchronous calls. Instead we are going to use an ``AsyncLocal`` with a Guid, which will be magically passed down the call 
stack, just like ``CallContext`` used to work in the old days.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Serilog;
using Serilog.Configuration;
using Serilog.Core;
using Serilog.Events;
using System;
using System.Threading;

namespace LayeredArchitecture.Base.Serilog
{
    /// <summary>
    /// Adds a random Correlation ID to the Log entries, so we can correlate async flows, where the 
    /// Continuation may be executed on different threads.
    /// </summary>
    public class ThreadCorrelationIdEnricher : ILogEventEnricher
    {
        private static readonly AsyncLocal<Guid> CorrelationIdContext = new AsyncLocal<Guid>();

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            if (CorrelationIdContext.Value == Guid.Empty)
            {
                CorrelationIdContext.Value = Guid.NewGuid();
            }

            logEvent.AddOrUpdateProperty(new LogEventProperty("ThreadCorrelationId", new ScalarValue(CorrelationIdContext.Value)));
        }
    }
}
```

#### UserIdEnricher ####

Which user initiated an action? We have already defined an ``IUserAccessor``, which provides a way to access a ``ClaimsPrincipal`` representing 
the current user (whatever current means). By using Dependency Injection, we inject the ``IUserAccessor`` into ``UserIdEnricher``.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Exensions;
using LayeredArchitecture.Base.Identity;
using Serilog.Core;
using Serilog.Events;
using System;

namespace LayeredArchitecture.Base.Serilog
{
    /// <summary>
    /// Adds the Thread ID of the <see cref="Environment"/> to the Log entry.
    /// </summary>
    public class UserIdEnricher : ILogEventEnricher
    {
        public const string UserIdPropertyName = "UserId";

        private readonly IUserAccessor userAccessor;


        private string cachedUserId;
        private LogEventProperty cachedLogEvent;

        public UserIdEnricher(IUserAccessor userAccessor)
        {
            this.userAccessor = userAccessor;
        }

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var currentUserId = userAccessor.User.GetUserId();

            if (cachedLogEvent == null || !string.Equals(cachedUserId, currentUserId, StringComparison.InvariantCulture))
            {
                cachedUserId = currentUserId;
                cachedLogEvent = cachedLogEvent ?? propertyFactory.CreateProperty(UserIdPropertyName, currentUserId);
            }

            var logEventProperty = propertyFactory.CreateProperty(UserIdPropertyName, cachedLogEvent);

            logEvent.AddPropertyIfAbsent(logEventProperty);
        }
    }
}
```

#### TenantIdEnricher ####

Which Tenant is the call related to? In a Multi-Tenant scenario we need this to know, which Tenant code executes for and for 
example to filter the Logs only for a given Tenant. By using the ``ITenantResolver``, we can get the Tenant ID for current 
call context.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Tenancy;
using Serilog.Core;
using Serilog.Events;
using System;

namespace LayeredArchitecture.Base.Serilog
{
    /// <summary>
    /// Adds the Tenant ID to a Log entry.
    /// </summary>
    public class TenantIdEnricher : ILogEventEnricher
    {
        public const string TenantIdPropertyName = "TenantId";

        private readonly ITenantResolver tenantResolver;

        public TenantIdEnricher(ITenantResolver tenantResolver)
        {
            this.tenantResolver = tenantResolver;
        }

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var logEventProperty = propertyFactory.CreateProperty(TenantIdPropertyName, tenantResolver.Tenant?.Id);

            logEvent.AddPropertyIfAbsent(logEventProperty);
        }
    }

    /// <summary>
    /// Adds the Tenant Name to a Log entry.
    /// </summary>
    public class TenantNameEnricher : ILogEventEnricher
    {
        public const string TenantNamePropertyName = "TenantName";

        private readonly ITenantResolver tenantResolver;

        public TenantNameEnricher(ITenantResolver tenantResolver)
        {
            this.tenantResolver = tenantResolver;
        }

        public void Enrich(LogEvent logEvent, ILogEventPropertyFactory propertyFactory)
        {
            var logEventProperty = propertyFactory.CreateProperty(TenantNamePropertyName, tenantResolver.Tenant?.Name);

            logEvent.AddPropertyIfAbsent(logEventProperty);
        }
    }
}
```
### LoggingConfiguration ###

What's left is to configure the Logger on Startup. We can use the ``UseSerilog`` Extension for the ``HostBuilder`` here, which 
gives us access to the ``IServiceCollection`` and makes it possible to access the Services by calling 
``IServiceCollection#GetRequiredService<T>``.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

//...

namespace LayeredArchitecture.Example
{
    class Program
    {
        public static IHostBuilder CreateHostBuilder(string[] args)
        {
            // Create the Host and Register Dependencies:
            var hostBuilder = Host
                .CreateDefaultBuilder(args)
                .ConfigureServices(RegisterServices)
                .ConfigureLogging(RegisterLogging)
                .UseSerilog((hostingContext, services, LoggerConfiguration) =>
                {
                    LoggerConfiguration
                                    .MinimumLevel.Verbose()
                                    // Override Minimum Levels:
                                    .MinimumLevel.Override("Microsoft", LogEventLevel.Verbose)
                                    .MinimumLevel.Override("System", LogEventLevel.Verbose)
                                    // Enrich the Logs:
                                    .Enrich.With(
                                        new ProcessIdEnricher(),
                                        new ProcessNameEnricher(),
                                        new ThreadIdEnricher(),
                                        new ThreadCorrelationIdEnricher(),
                                        new MachineNameEnricher(),
                                        new TenantIdEnricher(services.GetRequiredService<ITenantResolver>()),
                                        new TenantNameEnricher(services.GetRequiredService<ITenantResolver>()),
                                        new UserIdEnricher(services.GetRequiredService<IUserAccessor>()))
                                    // Add Log Appenders:
                                    .WriteTo.Console(outputTemplate: outputTemplate)
                                    .WriteTo.File("log.txt",
                                        rollingInterval: RollingInterval.Day,
                                        rollOnFileSizeLimit: true,
                                        outputTemplate: outputTemplate);
                });

            return hostBuilder;
        }
        
        // ...
    }
}
```

### Conclusion ###

It was pretty easy to get Serilog going with .NET Core. It integrates well into the ASP.NET Core Pipeline and provides a 
simple way for building custom Log Enrichers.

Let's cross logging off our list:

* ✅ Data Access
* ✅ Multi-Tenancy
* ✅ Database Migrations
* ✅ Audit Trails
* ✅ Versioning
* ✅ Optmistic Concurrency
* ✅ Logging
* ⬜ Testing

## Testing ##

Next on our list is testing. It sounds heretic, but if you work closely to the database:

* Never use in-memory databases!
* Always use the real database you are going to work with!

Some problems with In-Memory Databases is:

* What about using SQL directly in your Persistence Layer? Will an In-Memory Database work with it? 
* What about an N+1 Query, that's superfast in an In-Memory Database and stalls with a real database?
* ...

The Entity Framework Core docs have some recommendations for Unit Testing:

* [https://docs.microsoft.com/en-us/ef/core/testing/](https://docs.microsoft.com/en-us/ef/core/testing/)

It basically suggests to instantiate your DbContext with a ``new`` as your Fixture, so you can explicitly 
set the connection and set the Transaction using ``dbContext.Connection.BeginTransaction()`` to run code 
in a Transaction.

This sounds very similar to what we have done in the ``SqlClient``? 

What we will do is define a simple base class ``TransactionalTestBase``. Each Test will open a new Database 
Connection and a Transaction. Inside the test everyone will be automatically enlisted in the local 
transaction. At the end of the test we will simply do a Rollback and leave a clean state behind:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Base;
using Microsoft.Extensions.DependencyInjection;
using NUnit.Framework;

namespace LayeredArchitecture.DataAccess.Tests
{
    public abstract class TransactionalTestBase
    {
        protected ServiceProvider services;
        protected DbConnectionScope dbConnectionScope;

        [OneTimeSetUp]
        public void OneTimeSetUp()
        {
            var serviceCollection = new ServiceCollection();

            RegisterDependencies(serviceCollection);

            services = serviceCollection.BuildServiceProvider();
        }

        [SetUp]
        public void Setup()
        {
            OnSetupBeforeTransaction();
            
            this.dbConnectionScope = services
                .GetRequiredService<DbConnectionScopeFactory>()
                .Create();

            OnSetupInTransaction();
        }

        protected virtual void OnSetupBeforeTransaction() { }

        protected virtual void OnSetupInTransaction() { }

        [TearDown]
        public void Teardown()
        {
            OnTeardownInTransaction();

            dbConnectionScope.Rollback();
            
            OnTeardownAfterTransaction();
        }

        protected virtual void OnTeardownInTransaction() { }

        protected virtual void OnTeardownAfterTransaction() { }

        protected abstract void RegisterDependencies(ServiceCollection services);
    }
}
```

A simple test case for a DAO object will then look like this:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Tests;
using LayeredArchitecture.Tests.DataAccess;
using LayeredArchitecture.Tests.Domain;
using Microsoft.Extensions.DependencyInjection;
using NUnit.Framework;
using System;
using System.Threading.Tasks;

namespace LayeredArchitecture.Tests
{
    [TestFixture]
    public class DaoTests : TransactionalTestBase
    {
        private IPersonDao personDao;

        // Initialize Members by using the Service Locator...
        protected override void OnSetupBeforeTransaction()
        {
            personDao = services.GetRequiredService<IPersonDao>();
        }

        [Test]
        public async Task TestInsertAsync()
        {
            var p = new Person
            {
                FirstName = "Philipp",
                LastName = "Wagner",
                BirthDate = new DateTime(2020, 1, 3)
            };

            await personDao.InsertAsync(p);

            Assert.NotNull(p.Id);

            var persons = await personDao.QueryAsync();

            Assert.IsNotNull(persons);
            Assert.AreEqual(1, persons.Count);
        }

        protected override void RegisterDependencies(ServiceCollection services)
        {
            Bootstrapper.RegisterDependencies(services);
        }
    }
}
```

### Conclusion ###

And we can finally check the last TODO item:

* ✅ Data Access
* ✅ Multi-Tenancy
* ✅ Database Migrations
* ✅ Audit Trails
* ✅ Versioning
* ✅ Optmistic Concurrency
* ✅ Logging
* ✅ Testing

## Example ##

Let's make up a very simple example. It's only meant to showcase how to get started with the above code. Basically I create 
a Console Application for managing ``Person`` and ``Address`` entities, plus their assignments in an junction table. We will 
see how the various layers in an application will be implemented.

### Database ###

For me it starts with the database. The three tables ``[dbo].[Address]``, ``[dbo].[Person]`` and ``[dbo].[PersonAddress]`` 
store the most recent data. The ``[history]`` schema contains the temporal tables ``[history].[AddressHistory]``, ``[history].[PersonHistory]`` 
and ``[history].[PersonAddressHistory]`` for saving the history of the data:
 
```sql
--
-- DATABASE
--
IF DB_ID('$(dbname)') IS NULL
BEGIN
    CREATE DATABASE $(dbname)
END
GO

USE $(dbname)
GO 

-- Create History Schema:
IF NOT EXISTS ( SELECT  *
                FROM    sys.schemas
                WHERE   name = N'history' )
    EXEC('CREATE SCHEMA [history]');
GO

--
-- TABLES
--

IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[history].[AddressHistory]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [history].[AddressHistory](
        [AddressID] INT NOT NULL
        , [Name1] [NVARCHAR](255)
        , [Name2] [NVARCHAR](255)
        , [Street] [NVARCHAR](2000)
        , [ZipCode] [NVARCHAR](255)
        , [City] [NVARCHAR](255)
        , [Country] [NVARCHAR](255)
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT]
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 NOT NULL
        , [SysEndTime] DATETIME2 NOT NULL
    );

END
GO

IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[dbo].[Address]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [dbo].[Address](
        [AddressID] INT NOT NULL IDENTITY PRIMARY KEY
        , [Name1] [NVARCHAR](255)
        , [Name2] [NVARCHAR](255)
        , [Street] [NVARCHAR](2000)
        , [ZipCode] [NVARCHAR](255)
        , [City] [NVARCHAR](255)
        , [Country] [NVARCHAR](255)
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT]
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL
        , [SysEndTime] DATETIME2 GENERATED ALWAYS AS ROW END NOT NULL
        , PERIOD FOR SYSTEM_TIME (SysStartTime, SysEndTime)
        , CONSTRAINT CHK_Address_AuditOperation CHECK (AuditOperation in (1, 2, 3))
    ) 
    WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [history].[AddressHistory]));

END
GO

IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[history].[PersonHistory]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [history].[PersonHistory](
        [PersonID] INT NOT NULL
        , [FirstName] [NVARCHAR](255)
        , [LastName] [NVARCHAR](255)
        , [BirthDate] [DATETIME2](7)        
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT]
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 NOT NULL
        , [SysEndTime] DATETIME2 NOT NULL
    );

END
GO


IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[dbo].[Person]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [dbo].[Person](
        [PersonID] INT NOT NULL IDENTITY PRIMARY KEY
        , [FirstName] [NVARCHAR](255)
        , [LastName] [NVARCHAR](255)
        , [BirthDate] [DATETIME2](7)        
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT] DEFAULT 0
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL
        , [SysEndTime] DATETIME2 GENERATED ALWAYS AS ROW END NOT NULL
        , PERIOD FOR SYSTEM_TIME (SysStartTime, SysEndTime)
        , CONSTRAINT CHK_Person_AuditOperation CHECK (AuditOperation in (1, 2, 3))
    ) 
    WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [history].[PersonHistory]));

END
GO

IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[history].[PersonAddressHistory]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [history].[PersonAddressHistory](
        [PersonAddressID] INT NOT NULL
        , [PersonID] INT NOT NULL
        , [AddressID] INT NOT NULL
        , [ValidFrom] [DATETIME2](7)
        , [ValidUntil] [DATETIME2](7)     
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT]
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 NOT NULL
        , [SysEndTime] DATETIME2 NOT NULL
    );

END
GO

IF  NOT EXISTS 
	(SELECT * FROM sys.objects 
	 WHERE object_id = OBJECT_ID(N'[dbo].[PersonAddress]') AND type in (N'U'))
	 
BEGIN

	CREATE TABLE [dbo].[PersonAddress](
        [PersonAddressID] INT NOT NULL IDENTITY PRIMARY KEY  
        , [PersonID] INT NOT NULL
        , [AddressID] INT NOT NULL
        , [ValidFrom] [DATETIME2](7)
        , [ValidUntil] [DATETIME2](7)
        , [AuditUser] [NVARCHAR](255) NOT NULL
        , [AuditOperation] [TINYINT] NOT NULL
        , [EntityVersion] [BIGINT] DEFAULT 0
        , [RowVersion] [ROWVERSION]
        , [SysStartTime] DATETIME2 GENERATED ALWAYS AS ROW START NOT NULL
        , [SysEndTime] DATETIME2 GENERATED ALWAYS AS ROW END NOT NULL
        , PERIOD FOR SYSTEM_TIME (SysStartTime, SysEndTime)
        , CONSTRAINT FK_PersonAddress_Address FOREIGN KEY (AddressID)
          REFERENCES dbo.Address (AddressID)
        , CONSTRAINT FK_PersonAddress_Person FOREIGN KEY (PersonID)
          REFERENCES dbo.Person (PersonID)
        , CONSTRAINT CHK_PersonAddress_AuditOperation CHECK (AuditOperation in (1, 2, 3))
    ) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [history].[PersonAddressHistory]))

END
GO
```

### Domain Objects ###

In our application, we start with defining the ``Address`` entity:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Auditing;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.DataAccess.Base.Model;

namespace LayeredArchitecture.Example.Domain
{
    /// <summary>
    /// Address.
    /// </summary>
    public class Address : IAuditedEntity, IStatefulEntity
    {
        /// <summary>
        /// Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Name1.
        /// </summary>
        public string Name1 { get; set; }

        /// <summary>
        /// Name2.
        /// </summary>
        public string Name2 { get; set; }

        /// <summary>
        /// Street with HouseNo.
        /// </summary>
        public string Street { get; set; }

        /// <summary>
        /// Zip Code.
        /// </summary>
        public string ZipCode { get; set; }

        /// <summary>
        /// City.
        /// </summary>
        public string City { get; set; }

        /// <summary>
        /// Country.
        /// </summary>
        public string Country { get; set; }

        /// <summary>
        /// Audit User.
        /// </summary>
        public string AuditUser { get; set; }

        /// <summary>
        /// Audit Operation.
        /// </summary>
        public DataChangeOperationEnum AuditOperation { get; set; }

        /// <summary>
        /// The Version of the Entity.
        /// </summary>
        public long EntityVersion { get; set; }

        /// <summary>
        /// RowVersion Concurrency Token.
        /// </summary>
        public byte[] RowVersion { get; set; }

        /// <summary>
        /// State.
        /// </summary>
        public EntityStateEnum EntityState { get; set; }
    }
}
```

Then define the ``Person`` Entity:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Auditing;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.DataAccess.Base.Model;
using System;

namespace LayeredArchitecture.Example.Domain
{
    /// <summary>
    /// Person.
    /// </summary>
    public class Person : IAuditedEntity, IStatefulEntity
    {
        /// <summary>
        /// The Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// First Name.
        /// </summary>
        public string FirstName { get; set; }

        /// <summary>
        /// Last Name.
        /// </summary>
        public string LastName { get; set; }

        /// <summary>
        /// Birth Date.
        /// </summary>
        public DateTime BirthDate { get; set; }

        /// <summary>
        /// Audit User.
        /// </summary>
        public string AuditUser { get; set; }

        /// <summary>
        /// Audit Operation.
        /// </summary>
        public DataChangeOperationEnum AuditOperation { get; set; }

        /// <summary>
        /// The Version of the Entity.
        /// </summary>
        public long EntityVersion { get; set; }

        /// <summary>
        /// RowVersion Concurrency Token.
        /// </summary>
        public byte[] RowVersion { get; set; }

        /// <summary>
        /// State.
        /// </summary>
        public EntityStateEnum EntityState { get; set; }
    }
}
```

And finally define the ``PersonAddress`` entity:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Auditing;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.DataAccess.Base.Model;
using System;

namespace LayeredArchitecture.Example.Domain
{
    /// <summary>
    /// Person to Address Assignment.
    /// </summary>
    public class PersonAddress : IAuditedEntity, IStatefulEntity
    {
        /// <summary>
        /// Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Person ID.
        /// </summary>
        public int PersonId { get; set; }

        /// <summary>
        /// Address ID.
        /// </summary>
        public int AddressId { get; set; }

        /// <summary>
        /// Valid From.
        /// </summary>
        public DateTime ValidFrom { get; set; }

        /// <summary>
        /// Valid Until.
        /// </summary>
        public DateTime? ValidUntil { get; set; }

        /// <summary>
        /// Navigation Property for Person.
        /// </summary>
        public Person Person { get; set; }

        /// <summary>
        /// Navigation Property for Address.
        /// </summary>
        public Address Address { get; set; }

        /// <summary>
        /// Audit User.
        /// </summary>
        public string AuditUser { get; set; }

        /// <summary>
        /// Audit Operation.
        /// </summary>
        public DataChangeOperationEnum AuditOperation { get; set; }

        /// <summary>
        /// The Version of the Entity.
        /// </summary>
        public long EntityVersion { get; set; }

        /// <summary>
        /// RowVersion Concurrency Token.
        /// </summary>
        public byte[] RowVersion { get; set; }

        /// <summary>
        /// State.
        /// </summary>
        public EntityStateEnum EntityState { get; set; }
    }
}
```

### Data Access Layer ###

In the Data Access Layer has to implement:

1. The Data Access Objects implementing the ``IDao<T>`` interface.
2. The ``EntityTypeMap<T>`` database mappings.

In a real application the interfaces would contain more methods, of course.

#### Data Access Objects ####

The ``IAddressDao`` for ``Address`` entities:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Dao;
using LayeredArchitecture.Example.Domain;

namespace LayeredArchitecture.Example.DataAccess
{
    public interface IAddressDao 
        : IDao<Address>
    {
    }

    [LogAspect]
    public class AddressDao : DaoBase<Address>, IAddressDao
    {
        public AddressDao(IDbConnectionScopeResolver dbConnectionScopeResolver, IUserAccessor userAccessor, SqlClient sqlClient) 
            : base(dbConnectionScopeResolver, userAccessor, sqlClient) { }
    }
}
```

The ``IPersonDao`` for ``Person`` entities:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Dao;
using LayeredArchitecture.Example.Domain;

namespace LayeredArchitecture.Example.DataAccess
{
    public interface IPersonDao 
        : IDao<Person>
    {
    }
    
    [LogAspect]
    public class PersonDao : DaoBase<Person>, IPersonDao
    {
        public PersonDao(IDbConnectionScopeResolver dbConnectionScopeResolver, IUserAccessor userAccessor, SqlClient sqlClient) 
            : base(dbConnectionScopeResolver, userAccessor, sqlClient)
        {
        }
    }
}
```

The ``IPersonAddressDao`` for ``PersonAdress`` entities:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Dao;
using LayeredArchitecture.Example.Domain;

namespace LayeredArchitecture.Example.DataAccess
{
    public interface IPersonAddressDao 
        : IDao<PersonAddress>
    {
    }
    
    [LogAspect]
    public class PersonAddressDao : StatefulDaoBase<PersonAddress>, IPersonAddressDao
    {
        public PersonAddressDao(IDbConnectionScopeResolver dbConnectionScopeResolver, IUserAccessor userAccessor, SqlClient sqlClient) 
            : base(dbConnectionScopeResolver, userAccessor, sqlClient)
        {
        }
    }
}
```

#### Mappings ####

The ``AdressTypeMap`` maps to the ``[dbo].[Address]`` table in the database:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using LayeredArchitecture.Example.Domain;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace LayeredArchitecture.Example.DataAccess.Mappings
{
    public class AddressTypeMap : EntityTypeMap<Address>
    {
        protected override void InternalMap(EntityTypeBuilder<Address> builder)
        {
            builder
                .ToTable("Address", "dbo");

            builder
                .HasKey(x => x.Id);

            builder
                .Property(x => x.Id)
                .HasColumnName("AddressID")
                .ValueGeneratedOnAdd();

            builder
                .Property(x => x.Name1)
                .HasColumnName("Name1");

            builder
                .Property(x => x.Name2)
                .HasColumnName("Name2");

            builder
                .Property(x => x.Street)
                .HasColumnName("Street");

            builder
                .Property(x => x.ZipCode)
                .HasColumnName("ZipCode");

            builder
                .Property(x => x.City)
                .HasColumnName("City");

            builder
                .Property(x => x.Country)
                .HasColumnName("Country");

            builder
                .Property(x => x.RowVersion)
                .HasColumnName("RowVersion")
                .IsRowVersion();

            builder
                .Property(x => x.AuditUser)
                .HasColumnName("AuditUser")
                .IsRequired();

            builder
                .Property(x => x.AuditOperation)
                .HasColumnName("AuditOperation")
                .HasConversion<int>()
                .IsRequired();

            builder
                .Property(x => x.EntityVersion)
                .HasColumnName("EntityVersion")
                .HasDefaultValue(0);

            builder
                .Ignore(x => x.EntityState);
        }
    }
}
```

The ``PersonTypeMap`` maps to the ``[dbo].[Person]`` table in the database:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using LayeredArchitecture.Example.Domain;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace LayeredArchitecture.Example.DataAccess.Mappings
{
    public class PersonTypeMap : EntityTypeMap<Person>
    {
        protected override void InternalMap(EntityTypeBuilder<Person> builder)
        {
            builder
                .ToTable("Person", "dbo");

            builder
                .HasKey(x => x.Id);

            builder
                .Property(x => x.Id)
                .HasColumnName("PersonID")
                .ValueGeneratedOnAdd();

            builder
                .Property(x => x.FirstName)
                .HasColumnName("FirstName");

            builder
                .Property(x => x.LastName)
                .HasColumnName("LastName");

            builder
                .Property(x => x.BirthDate)
                .HasColumnName("BirthDate");

            builder
                .Property(x => x.RowVersion)
                .HasColumnName("RowVersion")
                .IsRowVersion();

            builder
                .Property(x => x.AuditUser)
                .HasColumnName("AuditUser")
                .IsRequired();

            builder
                .Property(x => x.AuditOperation)
                .HasColumnName("AuditOperation")
                .HasConversion<int>()
                .IsRequired();

            builder
                .Property(x => x.EntityVersion)
                .HasColumnName("EntityVersion")
                .HasDefaultValue(0);

            builder
                .Ignore(x => x.EntityState);
        }
    }
}
```

And for the ``PersonAddress`` mapping we can also use Navigation properties. It maps to the ``[dbo].[PersonAddress]`` table:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Mapping;
using LayeredArchitecture.Example.Domain;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace LayeredArchitecture.Example.DataAccess.Mappings
{
    public class PersonAddressTypeMap : EntityTypeMap<PersonAddress>
    {
        protected override void InternalMap(EntityTypeBuilder<PersonAddress> builder)
        {
            builder
                .ToTable("PersonAddress", "dbo");

            builder
                .HasKey(x => x.Id);

            builder
                .Property(x => x.Id)
                .HasColumnName("PersonAddressID")
                .ValueGeneratedOnAdd();

            builder
                .Property(x => x.AddressId)
                .HasColumnName("AddressID");

            builder
                .Property(x => x.PersonId)
                .HasColumnName("PersonID");

            builder
                .Property(x => x.ValidFrom)
                .HasColumnName("ValidFrom");

            builder
                .Property(x => x.ValidUntil)
                .HasColumnName("ValidUntil");

            builder
                .HasOne(x => x.Address)
                .WithMany()
                .HasForeignKey(x => x.AddressId);

            builder
                .HasOne(x => x.Person)
                .WithMany()
                .HasForeignKey(x => x.PersonId);

            builder
                .Property(x => x.AuditUser)
                .HasColumnName("AuditUser")
                .IsRequired();

            builder
                .Property(x => x.AuditOperation)
                .HasColumnName("AuditOperation")
                .HasConversion<int>()
                .IsRequired();

            builder
                .Property(x => x.EntityVersion)
                .HasColumnName("EntityVersion")
                .HasDefaultValue(0);

            builder
                .Property(x => x.RowVersion)
                .HasColumnName("RowVersion")
                .IsRowVersion();

            builder
                .Ignore(x => x.EntityState);

        }
    }
}
```

### Business Logic ###

Finally we are up to the Business Logic Layer, where something like a ``IPersonService`` could reside:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Example.Domain;
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace LayeredArchitecture.Example.Business
{
    /// <summary>
    /// Service for managing Person entities in the System.
    /// </summary>
    public interface IPersonService
    {
        /// <summary>
        /// Adds or updates a Person.
        /// </summary>
        /// <param name="person">Person</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Task result</returns>
        Task AddOrUpdatePersonAsync(Person person, CancellationToken cancellationToken = default);

        /// <summary>
        /// Deletes a Person.
        /// </summary>
        /// <param name="person">Person</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Task result</returns>
        Task DeletePersonAsync(Person person, CancellationToken cancellationToken = default);

        /// <summary>
        /// Adds or updates an Address.
        /// </summary>
        /// <param name="address">Address</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Task result</returns>
        Task AddOrUpdateAddressAsync(Address address, CancellationToken cancellationToken = default);

        /// <summary>
        /// Assigns an Address to a Person and gives it a Start Date for the Assignment.
        /// </summary>
        /// <param name="personId">Person Database ID</param>
        /// <param name="addressId">Address Database ID</param>
        /// <param name="validFrom">Start of the Assignment</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>Task result</returns>
        Task AssignAddressAsync(int personId, int addressId, DateTime validFrom, CancellationToken cancellationToken = default);

        /// <summary>
        /// Returns all PersonAddress assignments in the database.
        /// </summary>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>All PersonAddress assignments in the database</returns>
        Task<List<PersonAddress>> GetPersonAddressAllAsync(CancellationToken cancellationToken = default);
    }
}
```

And the implementation now uses the DAO interfaces and the ``DbConnectionScopeFactory`` for creating a ``DbConnectionScope``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.Example.DataAccess;
using LayeredArchitecture.Example.Domain;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using LayeredArchitecture.Base.Aspects;

namespace LayeredArchitecture.Example.Business
{
    /// <summary>
    /// Service for managing Person entities in the System.
    /// </summary>
    [LogAspect]
    public class PersonService : IPersonService
    {
        private readonly DbConnectionScopeFactory dbConnectionScopeFactory;
        private readonly IPersonDao personDao;
        private readonly IAddressDao addressDao;
        private readonly IPersonAddressDao personAddressDao;

        public PersonService(IServiceProvider services)
        {
            this.dbConnectionScopeFactory = services.GetService<DbConnectionScopeFactory>();

            // Poor Man Property Injection here:
            this.personDao = services.GetRequiredService<IPersonDao>();
            this.addressDao = services.GetRequiredService<IAddressDao>();
            this.personAddressDao = services.GetRequiredService<IPersonAddressDao>();
        }

        public async Task AddOrUpdateAddressAsync(Address address, CancellationToken cancellationToken = default)
        {
            using (var scope = dbConnectionScopeFactory.Create())
            {
                if(address.Id == 0)
                {
                    await addressDao.InsertAsync(address, cancellationToken);
                } 
                else
                {
                    await addressDao.UpdateAsync(address, cancellationToken);
                }
                
                scope.Commit();
            }
        }

        public async Task DeletePersonAsync(Person person, CancellationToken cancellationToken = default)
        {
            using (var scope = dbConnectionScopeFactory.Create())
            {
                await personDao.DeleteAsync(person, cancellationToken);

                scope.Commit();
            }
        }

        public async Task AddOrUpdatePersonAsync(Person person, CancellationToken cancellationToken = default)
        {
            using(var scope = dbConnectionScopeFactory.Create())
            {
                if(person.Id == 0)
                {
                    await personDao.InsertAsync(person, cancellationToken);
                } 
                else
                {
                    await personDao.UpdateAsync(person, cancellationToken);
                }
                
                scope.Commit();
            }
        }

        public async Task AssignAddressAsync(int personId, int addressId, DateTime validFrom, CancellationToken cancellationToken = default)
        {
            var personAddress = new PersonAddress
            {
                AddressId = addressId,
                PersonId = personId,
            };

            using (var scope = dbConnectionScopeFactory.Create())
            {
                await personAddressDao.InsertAsync(personAddress, cancellationToken);

                scope.Commit();
            }
        }

        public async Task<List<PersonAddress>> GetPersonAddressAllAsync(CancellationToken cancellationToken = default)
        {
            using (var scope = dbConnectionScopeFactory.Create())
            {
                return await personAddressDao
                    .QueryAsync(x => x
                        .Include(pa => pa.Person)
                        .Include(pa => pa.Address));
            }
        }

        public Task<List<Person>> GetAll(CancellationToken cancellationToken = default)
        {
            using (var scope = dbConnectionScopeFactory.Create())
            {
                return personDao.QueryAsync(cancellationToken: cancellationToken);
            }
        }
    }
}
```

### The Application ###

Because the underlying ``IDbConnectionFactory`` expects us to resolve a Tenant, we are implementing a simple ``ITenantResolver``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Tenancy;
using LayeredArchitecture.Base.Tenancy.Model;

namespace LayeredArchitecture.Example.App.Implementation
{
    /// <summary>
    /// A "useless" Tenant resolver, which always resolves to a single Tenant.
    /// </summary>
    public class TenantResolver : ITenantResolver
    {
        private Tenant tenant;

        public TenantResolver(Tenant tenant)
        {
            this.tenant = tenant;
        }

        public Tenant Tenant => tenant;
    }
}
```

What's left is the Application itself. In this application we are injecting a ``DbConnectionScopeFactory`` and a ``IPersonService``, which 
will be used to create an Address, a Person and the Assignmen in a single transaction:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Aspects;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.Example.Business;
using LayeredArchitecture.Example.Domain;
using System;
using System.Threading.Tasks;

namespace LayeredArchitecture.Example.App
{
    [LogAspect]
    public class Application
    {
        private readonly IPersonService personService;
        private readonly DbConnectionScopeFactory dbConnectionScopeFactory;

        public Application(DbConnectionScopeFactory dbConnectionScopeFactory, IPersonService personManager)
        {
            this.dbConnectionScopeFactory = dbConnectionScopeFactory;
            this.personService = personManager;
        }

        public async Task RunAsync()
        {
            // Let's do all this in a single Transaction:
            using (var dbConnectionScope = dbConnectionScopeFactory.Create())
            {
                var person0 = new Person
                {
                    FirstName = "Philipp",
                    LastName = "Wagner",
                    BirthDate = new DateTime(1912, 1, 1)
                };

                var person1 = new Person
                {
                    FirstName = "Max",
                    LastName = "Mustermann",
                    BirthDate = new DateTime(1911, 1, 1)
                };


                var address = new Address
                {
                    Name1 = "My Address"
                };

                // We're running in a ConnectionScope, so all this will be done in a single Transaction:
                await personService.AddOrUpdatePersonAsync(person0);
                await personService.AddOrUpdateAddressAsync(address);
                await personService.AssignAddressAsync(person0.Id, address.Id, DateTime.Now);

                await personService.AddOrUpdatePersonAsync(person1);
                await personService.DeletePersonAsync(person1);

                // For demonstration we could also Rollback here:
                dbConnectionScope.Commit();
            }
        }
    }
}
```

### Dependency Injection Configuration ###

For the Dependency Injection we are defining a static class ``Bootstrapper``, which configures the ``IServiceCollection`` for the application:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Identity;
using LayeredArchitecture.Base.Tenancy;
using LayeredArchitecture.Base.Tenancy.Model;
using LayeredArchitecture.DataAccess.Base;
using LayeredArchitecture.DataAccess.Mapping;
using LayeredArchitecture.DataAccess.Sql;
using LayeredArchitecture.Example.App;
using LayeredArchitecture.Example.App.Implementation;
using LayeredArchitecture.Example.Business;
using LayeredArchitecture.Example.DataAccess;
using LayeredArchitecture.Example.DataAccess.Mappings;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace LayeredArchitecture.Example
{
    /// <summary>
    /// Configures the Dependency Injection Container.
    /// </summary>
    public static class Bootstrapper
    {
        public static void RegisterServices(HostBuilderContext context, IServiceCollection services)
        {
            // Add Logging Infrastructure:
            services.AddLogging();

            // Entity Type Mappings:
            services.AddSingleton<IEntityTypeMap, AddressTypeMap>();
            services.AddSingleton<IEntityTypeMap, PersonTypeMap>();
            services.AddSingleton<IEntityTypeMap, PersonAddressTypeMap>();

            // Ambient Database:
            ConfigureDbConnectionFactory(services);

            services.AddSingleton<IDbConnectionScopeResolver, DbConnectionScopeProvider>();
            services.AddSingleton<DbConnectionScopeFactory>();
            services.AddSingleton<IUserAccessor, MockUserAccessor>();

            // SQL Client Abstraction:
            services.AddSingleton<SqlClient>();
            services.AddSingleton<SqlQueryContextFactory, SqlServerQueryContextFactory>();

            // Data Access:
            services.AddSingleton<IAddressDao, AddressDao>();
            services.AddSingleton<IPersonDao, PersonDao>();
            services.AddSingleton<IPersonAddressDao, PersonAddressDao>();

            // Services:
            services.AddSingleton<IPersonService, PersonService>();

            // Application:
            services.AddSingleton<Application>();
        }

        private static void ConfigureDbConnectionFactory(IServiceCollection services)
        {
            // A Tenant for our Console Application:
            var tenant = new Tenant
            {
                Id = 1,
                Name = "2DDC0BD3-9C9E-4189-B5B6-B03DF5FA9E87",
                Description = "Console Application"
            };

            // The configuration with the Connection String to a Database:
            var configuration = new TenantConfiguration
            {
                Id = 1,
                TenantId = 1,
                Name = tenant.Name,
                ConnectionString = @"Data Source=localhost\SQLEXPRESS;Initial Catalog=SampleDb;Integrated Security=SSPI;"
            };

            // Always resolves to the App Tenant:
            var resolver = new TenantResolver(tenant);
            var connectionFactory = new SqlServerDbConnectionFactory(resolver, new[] { configuration });

            // Register both:
            services.AddSingleton<ITenantResolver>(resolver);
            services.AddSingleton<IDbConnectionFactory>(connectionFactory);
        }
    }
}
```

### The Console Runner ###

And finally we can implement the Entrypoint for the Console Application. We are using the .NET Core ``HostBuilder`` to configure the Dependency Injection and Logging:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using LayeredArchitecture.Base.Identity;
using LayeredArchitecture.Base.Serilog;
using LayeredArchitecture.Base.Tenancy;
using LayeredArchitecture.Example.App;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Serilog;
using Serilog.Events;
using System.Threading.Tasks;

namespace LayeredArchitecture.Example
{
    class Program
    {
        private static string outputTemplate = "{Timestamp:yyyy-MM-dd HH:mm:ss.fff zzz} [{Level:u3}] {Message:lj} {Properties}{NewLine}{Exception}";

        static async Task Main(string[] args)
        {
            // Now Create the Host:
            using IHost host = CreateHostBuilder(args).Build();

            await host.Services
                .GetRequiredService<Application>()
                .RunAsync();
         
            await host.RunAsync();
        }

        public static IHostBuilder CreateHostBuilder(string[] args)
        {
            // Create the Host and Register Dependencies:
            var hostBuilder = Host
                .CreateDefaultBuilder(args)
                .ConfigureServices(RegisterServices)
                .ConfigureLogging(RegisterLogging)
                .UseSerilog((hostingContext, services, loggerConfiguration) =>
                {
                    loggerConfiguration
                                    .MinimumLevel.Verbose()
                                    // Override Minimum Levels:
                                    .MinimumLevel.Override("Microsoft", LogEventLevel.Verbose)
                                    .MinimumLevel.Override("System", LogEventLevel.Verbose)
                                    // Enrich the Logs:
                                    .Enrich.With(
                                        new ProcessIdEnricher(),
                                        new ProcessNameEnricher(),
                                        new ThreadIdEnricher(),
                                        new ThreadCorrelationIdEnricher(),
                                        new MachineNameEnricher(),
                                        new TenantIdEnricher(services.GetRequiredService<ITenantResolver>()),
                                        new TenantNameEnricher(services.GetRequiredService<ITenantResolver>()),
                                        new UserIdEnricher(services.GetRequiredService<IUserAccessor>()))
                                    // Add Log Appenders:
                                    .WriteTo.Console(outputTemplate: outputTemplate)
                                    .WriteTo.File("log.txt",
                                        rollingInterval: RollingInterval.Day,
                                        rollOnFileSizeLimit: true,
                                        outputTemplate: outputTemplate);
                });

            return hostBuilder;
        }

        private static void RegisterLogging(HostBuilderContext context, ILoggingBuilder loggingBuilder)
        {
            loggingBuilder.ClearProviders();
            loggingBuilder.AddSerilog(); 
        }

        public static void RegisterServices(HostBuilderContext context, IServiceCollection services)
        {
            Bootstrapper.RegisterServices(context, services);
        }
    }
}
```

And that's it!

## Final Thoughts ##

I hear you:

* Doesn't such an architecture lead to *God Objects*, *Feature Envy* and an *Anemic Domain model*?
* Isn't it dangerous to keep a transaction open for so long and risk deadlock victims?
* It doesn't scale!

Yes, yes and yes!

But I've seen, that such a Software Architecture can take you a long way, because:

* It contains a minimal amount of magic and everyone in a team understands it.
* Everyone knows where to put files.
* Works fine for Web applications, Console Applications, Windows Services or Rich Desktop applications.
* Data Access Objects and Services can be defined with a Singleton lifetime, which reduces the complexity of a DI Configuration.

And that's it for now.

[Domain Driven Design (DDD)]: https://en.wikipedia.org/wiki/Domain-driven_design

## Footnotes ##

[^1]: [Wikipedia, "Object Relational Impedance Mistmatch"](https://en.wikipedia.org/wiki/Object%E2%80%93relational_impedance_mismatch)
[^2]: [Vaughn Vernon, "Implementing Domain-Driven Design: Aggregates"](https://www.informit.com/articles/article.aspx?p=2020371&seqNum=5)
[^3]: Eric Evans, "Domain-Driven Design"
[^4]: J. Corbett, J. Dean, M. Epstein, A. Fikes, C. Frost, JJ Furman, S. Ghemawat, A. Gubarev, C. Heiser, P. Hochschild, W. Hsieh, S. Kanthak, E. Kogan, H. Li, A. Lloyd, S. Melnik, D. Mwaura, D. Nagle, S. Quinlan, R. Rao, L. Rolig, Y. Saito, M. Szymaniak, C. Taylor, R. Wang, and D. Woodford. "Spanner: Google’s Globally-Distributed Database." Proceedings of OSDI ‘12: Tenth Symposium on Operating System Design and Implementation, Hollywood, CA, October, 2012 