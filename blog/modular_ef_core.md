title: Building Modular Applications with Entity Framework Core 2.1
date: 2018-08-19 11:23
tags: csharp, efcore, entityframework
category: entityframework
slug: modular_ef_core
author: Philipp Wagner
summary: This article shows how to build modular applications with EF Core 2.1.

In this post I want to show you how to build modular applications with Entity Framework 2.1. 

It's something I have been playing around for quite some time and it would be a waste to leave it unnoticed in a private GitHub repository. 

So I thought I share it over at:

* [https://github.com/bytefish/ModularEfCore](https://github.com/bytefish/ModularEfCore)

## What is this whole post about? ##

### How I design Software ###

[it's all the same]: http://blog.ploeh.dk/2013/12/03/layers-onions-ports-adapters-its-all-the-same/

See, I spent countless hours of my life in endless meetings on software architecture. 

To me the whole aspect of software architecture and designing a systems based on uncertain requirements 
(Hello Agile Development!) is a source of very emotional and useless discussions.

And to be honest: Every sufficiently large project turns into hell anyway. No matter what architecture you 
are going to use. The only difference is, if your company is giving you time to fix the most hellish 
parts or not.

A Layered Architecture, Onion Architecture, Hexagonal Architecture, Ports and Adapters... 
to me [it's all the same]. I noticed, that if you understand the domain you work in and you 
keep your concerns separated, then everything is going to work out anyway.

By now I always start my projects with a dead simple Layered Architecture. Business Objects, Data Abstraction Layer, 
Data Transfer Objects. The whole thing. 

Often enough the Database model directly is my Applications Domain model. These 
days I am not even building Data Abstraction Layers, the Entity Framework ``DbContext`` **is the repository**. 

I extensively use OR-Mappers in the design process, because every other abstraction you try to "invent" leads to an 
OR-Mapper anyway. And believe me: You really, really don't want to maintain your own OR-Mapper. Just give yourself in!

I want to enjoy writing software. I want to be productive.

### The Goal ###

All Entity Framework projects I have been in implement a huge ``DbContext``, which holds at least 40 ``DbSet`` properties. 

For most projects this works good enough and I am also not a friend of over-designing stuff (anymore). But for my personal Entity Framework Core projects I want to build more modular applications. 

Basically I want to be able to define mappings in their own assemblies, while still making use of all query, migration and seeding capabilities of Entity Framework Core 2.1.

## From the Idea to the Implementation ##

[https://docs.microsoft.com/en-us/ef/ef6/modeling/code-first/fluent/relationships]: https://docs.microsoft.com/en-us/ef/ef6/modeling/code-first/fluent/relationships

### Extracting the Entity Mappings ###

I like to keep my Domain model clean from any EntityFramework-related attributes and use the Fluent-mapping API to define the Mapping between the Database and the Domain model:

* [https://docs.microsoft.com/en-us/ef/ef6/modeling/code-first/fluent/relationships]

In the Entity Framework Documents, this is often done by overriding the ``OnModelCreating`` method and using the 
``ModelBuilder``:

```csharp
public class ApplicationDbContext : DbContext
{
    protected override void OnModelCreating(ModelBuilder builder)
    {
        // Define your mappings here
        modelBuilder.Entity<Customer>()
            .HasKey(x => x.Id);
    }
}
``` 

In order to extract the mappings I define an interface first, which has a single method ``Map(ModelBuilder builder)``. This way we can inject a list of ``IEntityMap`` into to ``DbContext`` and have each of those configuring the ``ModelBuilder``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;

namespace ModularEfCore.Map
{
    public interface IEntityTypeMap
    {
        void Map(ModelBuilder builder);
    }
}
```

It's tedious to write ``builder.Entity<T>`` for each class you want to map. So I am also defining a ``BaseEntityMap<TEntityType>`` class, that does this job for us:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace ModularEfCore.Map
{
    public abstract class BaseEntityMap<TEntityType> : IEntityTypeMap
        where TEntityType : class
    {
        public void Map(ModelBuilder builder)
        {
            InternalMap(builder.Entity<TEntityType>());
        }

        protected abstract void InternalMap(EntityTypeBuilder<TEntityType> builder);
    }
}
```

### Seeding Data ###

Entity Framework Core 2.1 comes with a nice mechanism to seed data:

* [https://docs.microsoft.com/en-us/ef/core/modeling/data-seeding](https://docs.microsoft.com/en-us/ef/core/modeling/data-seeding)

The Microsoft Entity Framework Core Documentation writes:

> Data seeding allows to provide initial data to populate a database. Unlike in EF6, in EF Core, seeding data is associated with an entity type
> as part of the model configuration. Then EF Core migrations can automatically compute what insert, update or delete operations need to be
> applied when upgrading the database to a new version of the model.
>
> As an example, you can use this to configure seed data for a Blog in OnModelCreating:
>
> ``modelBuilder.Entity<Blog>().HasData(new Blog {BlogId = 1, Url = "http://sample.com"});``

Again the ``ModelBuilder`` is used to define the Seed Data. Do you see where this leads to? We define an interface ``IDbContextSeed`` again, which takes an ``ModelBuilder``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;

namespace ModularEfCore.Seed
{
    public interface IDbContextSeed
    {
        void Seed(ModelBuilder modelBuilder);
    }
}
```

This allows us to later inject the Seeding strategy into the DbContext.

### Implementing the DbContext ###

Now what's left is creating the actual ``DbContext`` and have our abstractions injected to it. 

I have defined a class ``ApplicationDbContextOptions``, that takes the DbContextOptions (Connection Strings, Migration Configuration, ...), the ``IDbContextSeed`` and the Mappings. In the ``OnModelCreating`` override of the ``DbContext`` all those dependencies are used to configure the ``ModelBuilder``. 

There is also a ``ApplicationDbContextExtensions`` class, which adds an Extension method to dynamically access a ``DbSet<TEntityType>`` without having it to define in the ``DbContext`` class.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using Microsoft.EntityFrameworkCore;
using ModularEfCore.Map;
using ModularEfCore.Seed;

namespace ModularEfCore.Context
{
    public class ApplicationDbContextOptions
    {
        public readonly DbContextOptions<ApplicationDbContext> Options;
        public readonly IDbContextSeed DbContextSeed;
        public readonly IEnumerable<IEntityTypeMap> Mappings;

        public ApplicationDbContextOptions(DbContextOptions<ApplicationDbContext> options, IDbContextSeed dbContextSeed, IEnumerable<IEntityTypeMap> mappings)
        {
            DbContextSeed = dbContextSeed;
            Options = options;
            Mappings = mappings;
        }
    }

    public class ApplicationDbContext : DbContext
    {
        private readonly ApplicationDbContextOptions options;
        
        public ApplicationDbContext(ApplicationDbContextOptions options)
            : base(options.Options)
        {
            this.options = options;
        }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            foreach (var mapping in options.Mappings)
            {
                mapping.Map(builder);
            }

            options.DbContextSeed.Seed(builder);
        }
    }

    public static class ApplicationDbContextExtensions
    {
        public static DbSet<TEntityType> DbSet<TEntityType>(this ApplicationDbContext context)
            where TEntityType : class
        {
            return context.Set<TEntityType>();
        }
    }
}
```

### DbContextFactory ###

And how do you instantiate this ``ApplicationDbContext`` from your Business Logic? 

You cannot write ``new ApplicationDbContext()`` anymore! But have no fear: 

> In Software Architecture, every problem can be solved with yet another layer of indirection. 

So we use a factory method instead, that creates an ``ApplicationDbContext`` for us:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ModularEfCore.Context;

namespace ModularEfCore.Factory
{
    public interface IApplicationDbContextFactory
    {
        ApplicationDbContext Create();
    }
}
```

And its implementation is really simple:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ModularEfCore.Context;

namespace ModularEfCore.Factory
{
    public class ApplicationDbContextFactory : IApplicationDbContextFactory
    {
        private readonly ApplicationDbContextOptions options;

        public ApplicationDbContextFactory(ApplicationDbContextOptions options)
        {
            this.options = options;
        }

        public ApplicationDbContext Create()
        {
            return new ApplicationDbContext(options);
        }
    }
}
```

That's it!

## A Sample Module: Customers ##

Imagine I want to add a new module to manager Customers to the application. The idea is, that all we need to do is to reference the ``ModularEfCore`` package to participate in the EF Core 2.1 Mapping, Seeding and Querying.

Let's take a look at the project structure first:

<a href="/static/images/blog/modular_ef_core/Example_Application_Module.jpg">
    <img src="/static/images/blog/modular_ef_core/Example_Application_Module.jpg" alt="Example App Structure" class="mediacenter" />
</a>

And here is what the classes do:

* Database
    * Map
        * Defines the Mapping between C# and the Database.
    * Model
        * Defines the Domain Model.
* Web
    * Controllers
        * REST Interface.
    * Converters
        * Converter between Domain Model and DTO
    * DTO
        * Data Transfer Objects (DTO) for the Web Layer.

### Domain Model ###

A customer in the application simply consists of a First Name and Last Name:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ModularEfCore.Example.Database.Model
{
    public class Customer
    {
        public int Id { get; set; }

        public string FirstName { get; set; }

        public string LastName { get; set; }
    }
}
```

### Database Mapping ###

Now we define the Mapping between the Customer Domain Model and the Database. This is done by deriving from the ``BaseEntityMap<T>`` we defined and using the usual EF Core Fluent Mapping API:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ModularEfCore.Example.Database.Model;
using ModularEfCore.Map;

namespace ModularEfCore.Example.Database.Map
{
    public class CustomerMap : BaseEntityMap<Customer>
    {
        protected override void InternalMap(EntityTypeBuilder<Customer> builder)
        {
            builder
                .ToTable("Sample", "Customer");

            builder
                .HasKey(x => x.Id)
                .HasName("PK_Customer");

            builder.Property(x => x.Id)
                .HasColumnName("Id")
                .ValueGeneratedOnAdd();

            builder
                .Property(x => x.FirstName)
                .HasColumnName("FirstName");

            builder
                .Property(x => x.LastName)
                .HasColumnName("LastName");
        }
    }
}
```

### Webservice ###

#### Data Transfer Object ####

I always keep the concerns in applications separated, and that's why I am always using Data Transfer Objects (DTO) for Web Services. 

Even though it sometimes looks like the Domain Model and the Data Transfer Object are the same thing, in a sufficiently complex application they are totally different beasts.

See how the ``CustomerDto`` is using the JSON.NET attributes for the JSON Serialization. I really don't want to have this leaking into my domain model:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Newtonsoft.Json;

namespace ModularEfCore.Example.Web.DTO
{
    public class CustomerDto
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("firstname")]
        public string FirstName { get; set; }

        [JsonProperty("lastname")]
        public string LastName { get; set; }
    }
}
```

And how do we convert between the two representations? 

A lot of .NET folks use the AutoMapper library to do it, but to me **explicit is better, than implicit**. So I always write a simple ``Converter`` class, that does the mapping. 

If there is a bug, I don't have to debug into ``AutoMapper`` Reflection Voodoo and I can do a simple *Find Usages* to see where properties have been used:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using System.Linq;
using ModularEfCore.Example.Database.Model;
using ModularEfCore.Example.Web.DTO;

namespace ModularEfCore.Example.Web.Converters
{
    public static class Converter
    {
        public static CustomerDto Convert(Customer source)
        {
            if (source == null)
            {
                return null;
            }

            return new CustomerDto
            {
                Id = source.Id,
                FirstName = source.FirstName,
                LastName = source.LastName
            };
        }

        public static IEnumerable<CustomerDto> Convert(IEnumerable<Customer> source)
        {
            if (source == null)
            {
                return null;
            }

            return source
                .Select(x => Convert(x));
        }
    }
}
```

#### Controller ####

Now the REST Service simply gets the ``ApplicationDbContextFactory`` injected to get a hold of the ``ApplicationDbContext``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ModularEfCore.Context;
using ModularEfCore.Example.Database.Model;
using ModularEfCore.Example.Web.Converters;
using ModularEfCore.Factory;

namespace ModularEfCore.Example.Web.Controllers
{
    public class CustomerController : Controller
    {
        private readonly IApplicationDbContextFactory dbContextFactory;

        public CustomerController(IApplicationDbContextFactory dbContextFactory)
        {
            this.dbContextFactory = dbContextFactory;
        }

        [HttpGet("customer/{id}")]
        public async Task<IActionResult> GetCustomer([FromRoute] int id, CancellationToken cancellationToken)
        {
            using (var context = dbContextFactory.Create())
            {
                var customer = await context.DbSet<Customer>()
                    .FirstOrDefaultAsync(x => x.Id == id, cancellationToken);

                if (customer == null)
                {
                    return NotFound();
                }

                var dtoCustomer = Converter.Convert(customer);

                return Ok(dtoCustomer);
            }
        }

        [HttpGet("customers")]
        public async Task<IActionResult> GetAllCustomers(CancellationToken cancellationToken)
        {
            using (var context = dbContextFactory.Create())
            {
                var customers = await context.DbSet<Customer>()
                    .ToListAsync(cancellationToken);

                var dtoCustomers = Converter.Convert(customers);

                return Ok(dtoCustomers);
            }
        }
    }
}
```

### Plugging it together ###

#### Initializing Data ####

When the Database is created, some sample data should be migrated. We defined the ``IDbContextSeed`` interface for it, which 
will be implemented by the application root. Entity Framework Core will use this to create the Migrations, when we update the database.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using ModularEfCore.Example.Database.Model;
using ModularEfCore.Seed;

namespace ModularEfCore.Example.Web.Database
{
    public class DbContextSeed : IDbContextSeed
    {
        private readonly IConfiguration configuration;

        public DbContextSeed(IConfiguration configuration)
        {
            this.configuration = configuration;
        }

        public void Seed(ModelBuilder modelBuilder)
        {
            // Add Customers:
            var customer1 = new Customer {Id = 1, FirstName = "Philipp", LastName = "Wagner"};
            var customer2 = new Customer {Id = 2, FirstName = "Max", LastName = "Mustermann"};
            

            modelBuilder.Entity<Customer>()
                .HasData(customer1, customer2);
        }
    }
}
```

#### Application Settings ####

The Application expects a Connection String named ``DefaultConnection``. You need to define it in the ``appsettings.json`` of the project:

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=.\\MSSQLSERVER2017;Database=SampleDB;Trusted_Connection=True;"
  }
}
```

#### Startup ####

And in the Startup Class the Dependency Injection Container is populated with the classes we defined. See how ``AddApplicationPart`` is used to append the module to the application. This way we can easily add new modules to application and extend it, without touching other application libraries.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Authorization;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using ModularEfCore.Context;
using ModularEfCore.Example.Database.Map;
using ModularEfCore.Example.Web.Controllers;
using ModularEfCore.Example.Web.Database;
using ModularEfCore.Factory;
using ModularEfCore.Map;
using ModularEfCore.Seed;


namespace ModularEfCore.Example.Web
{
    public class Startup
    {
        public IHostingEnvironment Environment { get; set; }

        public IConfiguration Configuration { get; }

        public Startup(IHostingEnvironment env)
        {
            Environment = env;

            Configuration = new ConfigurationBuilder()
                .SetBasePath(env.ContentRootPath)
                .AddJsonFile("appsettings.json")
                .AddEnvironmentVariables()
                .Build();
        }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // Add a CORS Policy to allow "Everything":
            services.AddCors(o =>
            {
                o.AddPolicy("Everything", p =>
                {
                    p.AllowAnyHeader()
                        .AllowAnyMethod()
                        .AllowAnyOrigin();
                });
            });

            // Register the Options:
            services.AddOptions();

            // Register Database Entity Maps:
            services.AddSingleton<IEntityTypeMap, CustomerMap>();

            // Register the Seed:
            services.AddSingleton<IDbContextSeed, DbContextSeed>();

            // Add the DbContextOptions:
            var dbContextOptions = new DbContextOptionsBuilder<ApplicationDbContext>()
                .UseSqlServer(Configuration.GetConnectionString("DefaultConnection"), x => x.MigrationsAssembly("ModularEfCore.Migrations"))
                .Options;

            services.AddSingleton(dbContextOptions);

            // Finally register the DbContextOptions:
            services.AddSingleton<ApplicationDbContextOptions>();

            // This Factory is used to create the DbContext from the custom DbContextOptions:
            services.AddSingleton<IApplicationDbContextFactory, ApplicationDbContextFactory>();

            // Finally Add the Applications DbContext:
            services.AddDbContext<ApplicationDbContext>();
            
            services
                // Use MVC:
                .AddMvc()
                // Add Application Modules:
                .AddApplicationPart(typeof(CustomerController).Assembly);
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env)
        {
            app.UseCors(policyName: "Everything");
            app.UseDefaultFiles();
            app.UseStaticFiles();
            app.UseMvc();
        }
    }
}
```

#### Starting the Application ####

What's left to do is to use the ``IWebHostBuilder`` to define the Startup class, create the Web Host and run it:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore;
using Microsoft.AspNetCore.Hosting;

namespace ModularEfCore.Example.Web
{
    public class Program
    {
        public static void Main(string[] args)
        {
            CreateWebHostBuilder(args).Build().Run();
        }

        public static IWebHostBuilder CreateWebHostBuilder(string[] args) =>
            WebHost.CreateDefaultBuilder(args)
                .UseStartup<Startup>();
    }
}
```

### Initializing the Database ###

First adjust the following Connection String the ``appsettings.json`` of the ``ModularEfCore.Example.Web`` project:

```
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=.\\SQLEXPRESS;Database=SampleDB;Trusted_Connection=True;"
  }
}
```

To create the Database run the following from the Package Manager Console:

```
PM> Update-Database
```

### Querying the Service ###

The ``curl`` CLI can be used to query the Application. Querying the ``/customers`` endpoint returns the two seeded customers:

```
C:\Users\bytefish>curl --verbose -X GET http://localhost:8000/customers
Note: Unnecessary use of -X or --request, GET is already inferred.
*   Trying ::1...
* TCP_NODELAY set
* Connected to localhost (::1) port 8000 (#0)
> GET /customers HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/7.55.1
> Accept: */*
>
< HTTP/1.1 200 OK
< Transfer-Encoding: chunked
< Content-Type: application/json; charset=utf-8
< Server: Kestrel
< X-SourceFiles: =?UTF-8?B?RDpcZ2l0aHViXE1vZHVsYXJFZkNvcmVcTW9kdWxhckVmQ29yZVxNb2R1bGFyRWZDb3JlLkV4YW1wbGUuV2ViXGN1c3RvbWVycw==?=
< X-Powered-By: ASP.NET
< Date: Sun, 19 Aug 2018 12:20:50 GMT
<
[{"id":1,"firstname":"Philipp","lastname":"Wagner"},{"id":2,"firstname":"Max","lastname":"Mustermann"}]* Connection #0 to host localhost left intact

C:\Users\bytefish>
```

## Conclusion ##

I feel very productive with EF Core 2.1 and it was really easy to extend it a bit. The Fluent Mapping API enables me to keep my Domain model clean and extract the database mappings into separate classes. It's easy to add and apply migrations without handwriting SQL scripts, and EF Core 2.1 even takes good care of seeding the data.