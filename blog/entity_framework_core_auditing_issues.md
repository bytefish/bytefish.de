title: Using Microsoft SQL Server Temporal Tables and EntityFramework Core to Audit a Database
date: 2023-04-02 13:26
tags: aspnetcore, efcore, dotnet, csharp
category: csharp
slug: entity_framework_core_temporal_tables
author: Philipp Wagner
summary: This article discusses auditing with EntityFramework Core.

Audit trails are a very, very common requirement in software development. And if you are using 
SQL Server (or MariaDB) it's really easy to use a Temporal Table and track everything, that happens 
to your data. Just let your expensive database handle it!

Now a common example in EntityFramework Core articles is to add auditing by overriding the `DbContext.SaveChanges` method 
and add the audit information by inspecting the `ChangeTracker`. Some tutorials also use an `SaveChangesInterceptor` to add 
it as a cross-cutting concern.

The problem with this kind of approach to auditing is, that it doesn't work for the EF Core 7 `ExecuteUpdateAsync` 
methods, that basically bypass the `DbContext.SaveChangesAsync` method. So this example serves as a word of caution and 
also shows how to work with Temporal tables instead.
 
Please feel free to make a PR to the repository and fix this issue, because I don't know of a EntityFramework Core-based solution:

* [https://github.com/bytefish/EFCoreExperiments](https://github.com/bytefish/EFCoreExperiments)

## Table of contents ##

[TOC]

## The common EntityFramework Core Example ##

So let's first recreate the common example for writing audit trails, that's shown in many videos and tutorials.

We start by adding an abstract `AuditableEntity`, which all audited entities derive from:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace EfCoreAudit.Model
{
    /// <summary>
    /// Audit Information.
    /// </summary>
    public abstract class AuditableEntity
    {
        /// <summary>
        /// Gets or sets the created date.
        /// </summary>
        public DateTime? CreatedDateTime { get; set; }

        /// <summary>
        /// Gets or sets the modified date.
        /// </summary>
        public DateTime? ModifiedDateTime { get; set; }
    }
}
```

Next we add a `Person` entity, that extends an `AuditableEntity`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace EfCoreAudit.Model
{
    /// <summary>
    /// A Person in the application.
    /// </summary>
    internal class Person : IAuditableEntity
    {
        /// <summary>
        /// Gets or sets the Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Gets or sets the Name.
        /// </summary>
        public required string FullName { get; set; }
    }
}
```

We can then define the `ApplicationDbContext`, which will be used in the application and configure the `Person` using a `ModelBuilder`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Model;
using Microsoft.EntityFrameworkCore;

namespace EfCoreAudit.Context
{
    internal class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<Person> People { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.HasSequence<int>("sq_Person", schema: "Application")
                .StartsAt(1000)
                .IncrementsBy(1);

            modelBuilder.Entity<Person>(entity =>
            {
                entity.ToTable("Person", "Application");

                entity.HasKey(e => e.Id);

                entity.Property(x => x.Id)
                    .HasColumnType("INT")
                    .HasDefaultValueSql("NEXT VALUE FOR [Application].[sq_Person]")
                    .ValueGeneratedOnAdd();

                entity.Property(e => e.FullName)
                    .HasColumnType("NVARCHAR(255)")
                    .HasColumnName("FullName")
                    .IsRequired(true)
                    .HasMaxLength(255);

                entity.Property(e => e.CreatedDateTime)
                    .HasColumnType("DATETIME2(7)")
                    .HasColumnName("CreatedDateTime")
                    .IsRequired(false);

                entity.Property(e => e.ModifiedDateTime)
                    .HasColumnType("DATETIME2(7)")
                    .HasColumnName("ModifiedDateTime")
                    .IsRequired(false);
            });

            base.OnModelCreating(modelBuilder);
        }
    }
}
```

Then a `SaveChangesInterceptor` can be implemented, that overrides the `SavingChangesAsync` method. It then 
inspects, if entities of type `AuditableEntity` have been added or modified and then sets their `ModifiedDateTime` 
accordingly.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Model;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace EfCoreAudit.Database.Interceptors
{
    /// <summary>
    /// A <see cref="SaveChangesInterceptor"/> for adding auditing metadata.
    /// </summary>
    internal class AuditingInterceptor : SaveChangesInterceptor
    {
        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(DbContextEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default)
        {
            DbContext ctx = eventData.Context!;

            if (ctx == null)
            {
                return base.SavingChangesAsync(eventData, result, cancellationToken);
            }

            var auditableEntities = ctx.ChangeTracker.Entries<AuditableEntity>().ToList();

            foreach (var auditableEntity in auditableEntities)
            {

                if (auditableEntity.State == EntityState.Added)
                {
                    auditableEntity.Property(x => x.CreatedDateTime).CurrentValue = DateTime.UtcNow;
                }

                if (auditableEntity.State == EntityState.Modified)
                {
                    auditableEntity.Property(x => x.ModifiedDateTime).CurrentValue = DateTime.UtcNow;
                }
            }

            return base.SavingChangesAsync(eventData, result, cancellationToken);
        }
    }
}
```

In the `TransactionalTestBase` class, we can see how the `AuditingInterceptor` is configured when 
creating an `ApplicationDbContext`. The `TransactionalTestBase` class can be used by all tests and 
basically executes everything in a `TransactionScope`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Context;
using EfCoreAudit.Database.Interceptors;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using NUnit.Framework;

namespace EfCoreAudit.Tests
{
    /// <summary>
    /// Will be used by all integration tests, that need an <see cref="ApplicationDbContext"/>.
    /// </summary>
    internal class TransactionalTestBase
    {
        // ...

        /// <summary>
        /// Builds an <see cref="ApplicationDbContext"/> based on a given Connection String 
        /// and enables sensitive data logging for eventual debugging. 
        /// </summary>
        /// <param name="connectionString">Connection String to the Test database</param>
        /// <returns>An initialized <see cref="ApplicationDbContext"/></returns>
        private ApplicationDbContext GetApplicationDbContext(string connectionString)
        {
            var dbContextOptionsBuilder = new DbContextOptionsBuilder<ApplicationDbContext>()
                .AddInterceptors(new AuditingInterceptor())
                .UseSqlServer(connectionString);

            return new ApplicationDbContext(dbContextOptionsBuilder.Options);
        }
    }
}
```

And finally we can write the integration test, that makes the problem obvious. While all 
modifications will be audited for calls to `DbContext#SaveChanges`, all Bulk Updates using 
the more recent `ExecuteUpdateAsync` will go unaudited.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Model;
using EfCoreAudit.Tests;
using Microsoft.EntityFrameworkCore;
using NUnit.Framework;

namespace EfCoreAudit
{
    [TestFixture]
    internal class AuditingEntitiesTests : TransactionalTestBase
    {
        public override async Task OnSetupBeforeTransaction()
        {
            await _applicationDbContext.Database.EnsureCreatedAsync();
        }

        [Test]
        public async Task AuditingEntites_SaveChanges_SetsCreatedDateTime()
        {
            // Prepare
            var person = new Person 
            {
                FullName = "Philipp Wagner"
            };

            // Act
            await _applicationDbContext.AddAsync(person);
            await _applicationDbContext.SaveChangesAsync();

            // Assert
            var people = await _applicationDbContext.People
                .AsNoTracking()
                .ToListAsync();

            Assert.AreEqual(1, people.Count);

            Assert.AreEqual("Philipp Wagner", people[0].FullName);

            Assert.IsNotNull(people[0].CreatedDateTime);
            Assert.IsNull(people[0].ModifiedDateTime);
        }

        [Test]
        public async Task AuditingEntites_SaveChanges_SetsModifiedDateTime()
        {
            // Prepare
            var person = new Person
            {
                FullName = "Philipp Wagner"
            };
            
            await _applicationDbContext.AddAsync(person);
            await _applicationDbContext.SaveChangesAsync();

            // Act
            person.FullName = "Edited Name";

            await _applicationDbContext.SaveChangesAsync();

            // Assert
            var people = await _applicationDbContext.People
                .AsNoTracking()
                .ToListAsync();

            Assert.AreEqual(1, people.Count);

            Assert.AreEqual("Edited Name", people[0].FullName);

            Assert.IsNotNull(people[0].CreatedDateTime);
            Assert.IsNotNull(people[0].ModifiedDateTime);
        }

        [Test]
        public async Task AuditingEntites_ExecuteUpdate_SetsModifiedDateTime()
        {
            // Prepare
            var person = new Person
            {
                FullName = "Philipp Wagner"
            };

            await _applicationDbContext.AddAsync(person);
            await _applicationDbContext.SaveChangesAsync();

            // Act
            await _applicationDbContext.People.ExecuteUpdateAsync(s => 
                s.SetProperty(p => p.FullName, p => "Edited Name"));

            // Assert
            var people = await _applicationDbContext.People
                .AsNoTracking()
                .ToListAsync();

            Assert.AreEqual(1, people.Count);

            Assert.AreEqual("Edited Name", people[0].FullName);

            Assert.IsNotNull(people[0].CreatedDateTime);
            Assert.IsNotNull(people[0].ModifiedDateTime);
        }
    }
}
```

And boom, you will see that the last test fails. And there is no simple way to fix it, because the 
interceptor doesn't know about `ExecuteUpdate`. And it also bypasses the `ChangeTracker`, so there 
is no simple way to inspect it.

So you are basically left with an implementation, that only covers only a few use cases. 

I guess the easiest fix would be to override the `DbContext#ExecuteUpdateAsync` method and set the 
`ModifiedDateTime`, but you need somewhat advanced skills to rewrite the `Expression` used by 
EntityFramework Core (I don't have them).

Amazing!

## Temporal Tables to Rescue ##

There is no one-size-fits-all solution, but I think you shouldn't do auditing using a `DbContext` in 
your application layer. What if you need to modify data using a Stored Procedure? What if you need to 
run migrations or fix data inconsistencies?

A much safer (and sane) way is to use Temporal Tables, if you are working with a Microsoft SQL Server.

### Database Schema ###

We start by creating the Database Schema:

```sql
CREATE SCHEMA [Application];
```

Then we create a Sequence for the `PersonID` Primary Key:

```sql
CREATE SEQUENCE [Application].[sq_Person]
    AS INT
    START WITH 38187
    INCREMENT BY 1;
```

And then we can create the `[Application].[Person]` table with SYSTEM VERSIONING enabled:

```sql
CREATE TABLE [Application].[Person](
    [PersonID]              INT                                         CONSTRAINT [DF_Application_Person_PersonID] DEFAULT (NEXT VALUE FOR [Application].[sq_Person]) NOT NULL,
    [FullName]              NVARCHAR(255)                               NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_Person] PRIMARY KEY ([PersonID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[PersonHistory]));
```

For our tests, we need to clean the History Table between the tests. But once you have System Versioning 
enabled on a table, there is no way for EntityFramework Core to delete the historic data. That makes 
sense, and rightly so! 

So we define a Stored Procedure `[Application].[usp_Database_ResetForTests]`, that resets all data for us by 
first deactivating System Versioning, then deleting all data, and then reactivating System versioning:

```sql 
CREATE PROCEDURE [Application].[usp_Database_ResetForTests]
AS BEGIN
    EXECUTE [Application].[usp_TemporalTables_DeactivateTemporalTables];

    EXEC(N'DELETE FROM [Application].[Person]');
    EXEC(N'DELETE FROM [Application].[PersonHistory]');

    EXECUTE [Application].[usp_TemporalTables_ReactivateTemporalTables];
END
```

In `[Application].[usp_TemporalTables_DeactivateTemporalTables]` we disable System Versioning:

```sql
CREATE PROCEDURE [Application].[usp_TemporalTables_DeactivateTemporalTables]
AS BEGIN
    IF OBJECTPROPERTY(OBJECT_ID('[Application].[Person]'), 'TableTemporalType') = 2
    BEGIN
	    PRINT 'Deactivate Temporal Table for [Application].[Person]'

	    ALTER TABLE [Application].[Person] SET (SYSTEM_VERSIONING = OFF);
	    ALTER TABLE [Application].[Person] DROP PERIOD FOR SYSTEM_TIME;
    END
END
```

In `[Application].[usp_TemporalTables_ReactivateTemporalTables]` we reactivate System Versioning:

```sql
CREATE PROCEDURE [Application].[usp_TemporalTables_ReactivateTemporalTables]
AS BEGIN
    IF OBJECTPROPERTY(OBJECT_ID('[Application].[Person]'), 'TableTemporalType') = 0
    BEGIN
	    PRINT 'Reactivate Temporal Table for [Application].[Person]'

	    ALTER TABLE [Application].[Person] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
	    ALTER TABLE [Application].[Person] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[PersonHistory], DATA_CONSISTENCY_CHECK = ON));
    END
END
```

That's it!

### Integration Tests ###

The `AuditableEntity` base class is gone. All our entities are System Versioned, so we just add a 
`ValidFrom` and `ValidTo` timestamp. If you want to know, when the entity was created, you would 
find the first entity in the history table.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace EfCoreAudit.Temporal.Model
{
    /// <summary>
    /// A Person in the application.
    /// </summary>
    public class Person
    {
        /// <summary>
        /// Gets or sets the Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Gets or sets the Name.
        /// </summary>
        public required string FullName { get; set; }

        /// <summary>
        /// Gets or sets the ValidFrom.
        /// </summary>
        public DateTime? ValidFrom { get; set; }

        /// <summary>
        /// Gets or sets the ValidTo
        /// </summary>
        public DateTime? ValidTo { get; set; }
    }
}
```

The `ApplicationDbContext` now has the properties `ValidFrom` and `ValidTo` to be mapped:

```
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Temporal.Model;
using Microsoft.EntityFrameworkCore;

namespace EfCoreAudit.Temporal.Database
{
    internal class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<Person> People { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.HasSequence<int>("sq_Person", schema: "Application")
                .StartsAt(1000)
                .IncrementsBy(1);

            modelBuilder.Entity<Person>(entity =>
            {
                entity.ToTable("Person", "Application");

                entity.HasKey(e => e.Id);

                entity.Property(x => x.Id)
                    .HasColumnType("INT")
                    .HasColumnName("PersonID")
                    .HasDefaultValueSql("NEXT VALUE FOR [Application].[sq_Person]")
                    .ValueGeneratedOnAdd();

                entity.Property(e => e.FullName)
                    .HasColumnType("NVARCHAR(255)")
                    .HasColumnName("FullName")
                    .IsRequired(true)
                    .HasMaxLength(255);

                entity.Property(e => e.ValidFrom)
                    .HasColumnType("DATETIME2(7)")
                    .HasColumnName("ValidFrom")
                    .IsRequired(false)
                    .ValueGeneratedOnAddOrUpdate();

                entity.Property(e => e.ValidTo)
                    .HasColumnType("DATETIME2(7)")
                    .HasColumnName("ValidTo")
                    .IsRequired(false)
                    .ValueGeneratedOnAddOrUpdate();
            });

            base.OnModelCreating(modelBuilder);
        }
    }
}
```

The `TransactionalTestBase` is also out the door and now `TestBase`. The reason? A `PersonHistory` 
entry will only be written, when a Transaction is commited (again, makes a lot of sense). So we 
cannot keep the Transaction open for the entire time.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Temporal.Database;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;

namespace EfCoreAudit.Temporal.Tests
{
    /// <summary>
    /// Will be used by all integration tests, that need an <see cref="ApplicationDbContext"/>.
    /// </summary>
    internal class TestBase
    {
        /// <summary>
        /// We can assume the Configuration has been initialized, when the Tests 
        /// are run. So we inform the compiler, that this field is intentionally 
        /// left uninitialized.
        /// </summary>
        protected IConfiguration _configuration = null!;

        public TestBase()
        {
            _configuration = ReadConfiguration();
        }

        /// <summary>
        /// Read the appsettings.json for the Test.
        /// </summary>
        /// <returns></returns>
        private IConfiguration ReadConfiguration()
        {
            return new ConfigurationBuilder()
                .AddJsonFile("appsettings.json")
                .Build();
        }

        /// <summary>
        /// Builds an <see cref="ApplicationDbContext"/> based on a given Configuration. We 
        /// expect the Configuration to have a Connection String "ApplicationDatabase" to 
        /// be defined.
        /// </summary>
        /// <param name="configuration">A configuration provided by the appsettings.json</param>
        /// <returns>An initialized <see cref="ApplicationDbContext"/></returns>
        /// <exception cref="InvalidOperationException">Thrown when no Connection String "ApplicationDatabase" was found</exception>
        protected ApplicationDbContext CreateDbContext()
        {
            var connectionString = _configuration.GetConnectionString("ApplicationDatabase");

            if (connectionString == null)
            {
                throw new InvalidOperationException($"No Connection String named 'ApplicationDatabase' found in appsettings.json");
            }

            var dbContextOptionsBuilder = new DbContextOptionsBuilder<ApplicationDbContext>()
                .UseSqlServer(connectionString);

            return new ApplicationDbContext(dbContextOptionsBuilder.Options);
        }
    }
}
```

And in the `AuditingEntitiesTests` we can now see, that all changes commited to the database are tracked 
in the `PersonHistory` table. We didn't need to add a single line of code to do so, but let the database 
handle it.

The great thing is, that this also applies to data modifications bypassing our application layer, such 
as Stored Procedures or ETL jobs, that need to run on the database.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Temporal.Model;
using EfCoreAudit.Temporal.Tests;
using Microsoft.EntityFrameworkCore;
using NUnit.Framework;

namespace EfCoreAudit.Temporal
{
    [TestFixture]
    internal class AuditingEntitiesTests : TestBase
    {
        [SetUp]
        public void SetUp()
        {
            using (var context = CreateDbContext())
            {
                context.Database.ExecuteSqlRaw("EXEC [Application].[usp_Database_ResetForTests]");
            }
        }

        [Test]
        public async Task AuditingEntites_SaveChanges_SetsCreatedDateTime()
        {
            // Prepare
            using var context = CreateDbContext();

            var person = new Person
            {
                FullName = "Philipp Wagner"
            };

            // Act
            await context.AddAsync(person);
            await context.SaveChangesAsync();

            // Assert
            var people = await context.People
                .AsNoTracking()
                .ToListAsync();

            var peopleHistory = await context.People.TemporalAll()
                .AsNoTracking()
                .ToListAsync();

            Assert.AreEqual(1, people.Count);

            Assert.AreEqual("Philipp Wagner", people[0].FullName);

            Assert.That(people[0].ValidFrom, Is.EqualTo(DateTime.UtcNow).Within(1).Seconds);
            Assert.That(people[0].ValidTo, Is.EqualTo(new DateTime(9999, 12, 31, 23, 59, 59)).Within(1).Seconds);

            Assert.AreEqual(1, peopleHistory.Count);

            Assert.That(peopleHistory[0].ValidFrom, Is.EqualTo(DateTime.UtcNow).Within(1).Seconds);
            Assert.That(peopleHistory[0].ValidTo, Is.EqualTo(new DateTime(9999, 12, 31, 23, 59, 59)).Within(1).Seconds);
        }

        [Test]
        public async Task AuditingEntites_SaveChanges_SetsModifiedDateTime()
        {

            // Prepare
            using var context = CreateDbContext();
            
            var person = new Person
            {
                FullName = "Philipp Wagner"
            };

            await context.AddAsync(person);
            await context.SaveChangesAsync();

            // Act
            person.FullName = "Edited Name";

            await context.SaveChangesAsync();

            // Assert
            var people = await context.People
                .AsNoTracking()
                .ToListAsync();

            var peopleHistory = await context.People.TemporalAll()
                .OrderByDescending(x => x.ValidFrom)
                .AsNoTracking()
                .ToListAsync();

            // Check Current Entity
            Assert.AreEqual(1, people.Count);

            Assert.AreEqual("Edited Name", people[0].FullName);

            Assert.IsNotNull(people[0].ValidFrom);
            Assert.IsNotNull(people[0].ValidTo);

            // Check Person History
            Assert.AreEqual(2, peopleHistory.Count);

            Assert.AreEqual("Edited Name", peopleHistory[0].FullName);
            Assert.That(peopleHistory[0].ValidTo, Is.EqualTo(new DateTime(9999, 12, 31, 23, 59, 59)).Within(1).Seconds);

            Assert.AreEqual("Philipp Wagner", peopleHistory[1].FullName);
            Assert.That(peopleHistory[1].ValidTo, Is.LessThan(new DateTime(9999, 12, 31, 23, 59, 59)));
        }

        [Test]
        public async Task AuditingEntites_ExecuteUpdate_SetsModifiedDateTime()
        {
            // Prepare
            using var context = CreateDbContext();

            var person = new Person
            {
                FullName = "Philipp Wagner"
            };

            await context.AddAsync(person);
            await context.SaveChangesAsync();

            // Act
            await context.People.ExecuteUpdateAsync(s =>
                s.SetProperty(p => p.FullName, p => "Edited Name"));

            // Assert
            var people = await context.People
                .AsNoTracking()
                .ToListAsync();

            var peopleHistory = await context.People.TemporalAll()
                .OrderByDescending(x => x.ValidFrom)
                .AsNoTracking()
                .ToListAsync();

            // Check Current Entity
            Assert.AreEqual(1, people.Count);

            Assert.AreEqual("Edited Name", people[0].FullName);

            Assert.IsNotNull(people[0].ValidFrom);
            Assert.IsNotNull(people[0].ValidTo);

            // Check Person History
            Assert.AreEqual(2, peopleHistory.Count);

            Assert.AreEqual("Edited Name", peopleHistory[0].FullName);
            Assert.That(peopleHistory[0].ValidTo, Is.EqualTo(new DateTime(9999, 12, 31, 23, 59, 59)).Within(1).Seconds);


            Assert.AreEqual("Philipp Wagner", peopleHistory[1].FullName);
            Assert.That(peopleHistory[1].ValidTo, Is.LessThan(new DateTime(9999, 12, 31, 23, 59, 59)));
        }
    }
}
```

## Conclusion ##

I think using a Temporal Table is a good way to audit changes to your database. There is no need 
to fiddle around with Change Tracking and relying on EntityFramework Core to write the Audit 
trails.

The situation is different, if you are using PostgreSQL, which doesn't have Temporal Tables. But even 
with PostgreSQL, I think using the [temporal_tables](https://github.com/nearform/temporal_tables) extensions 
might be a much more foolproof option.