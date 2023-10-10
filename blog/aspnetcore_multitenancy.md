title: Providing Multitenancy with ASP.NET Core and PostgreSQL Row Level Security
date: 2021-12-05 17:52
tags: aspnetcore, csharp, multitenancy
category: csharp
slug: aspnetcore_multitenancy
author: Philipp Wagner
summary: This article shows how to provide Multitenancy with ASP.NET Core and PostgreSQL Row Level Security.

I have written quite a lot of articles on Multitenancy with Spring Boot, but I am actually writing C\# for a living. 

So it's interesting to see how to provide Multitenancy with ASP.NET Core and Entity Framework Core.

In this article we are building a simple CRUD application to create, read and update customers. PostgreSQL Row Level 
Security is used to provide data isolation for multiple Tenants of the application:

* [https://github.com/bytefish/AspNetCoreMultitenancy](https://github.com/bytefish/AspNetCoreMultitenancy)

I've found most of the example implementations to be overly complicated. 

So here is my overly complicated implementation!

## Table of contents ##

[TOC]

## Creating the Database ##

Let's start with the database.

It's always a good idea to use a Database Schema:

```sql
CREATE SCHEMA IF NOT EXISTS sample;
```

In the database we will have a ``tenant`` table, which holds the applications Tenants:

```sql
CREATE TABLE IF NOT EXISTS sample.tenant
(
	tenant_id INTEGER PRIMARY KEY
	, name VARCHAR(255) NOT NULL
	, description VARCHAR(255) NOT NULL
    , UNIQUE(name)
);
```

And we are adding two example Tenants, that will be using the sample application:

```sql
INSERT INTO sample.tenant(tenant_id, name, description)
VALUES (1, '33F3857A-D8D7-449E-B71F-B5B960A6D89A', 'Tenant 1')
ON CONFLICT  DO NOTHING;

INSERT INTO sample.tenant(tenant_id, name, description)
VALUES (2, '7344384A-A2F4-4FC4-A382-315FCB421A72', 'Tenant 2')
ON CONFLICT  DO NOTHING;
```

The customers will be managed in a ``customer`` table, which also contains a ``tenant_name`` 
column to restrict, which rows can be returned by normal queries or inserted, updated, or 
deleted by data modification commands.

```sql
CREATE TABLE IF NOT EXISTS sample.customer
(
	customer_id SERIAL PRIMARY KEY
	, first_name VARCHAR(255) NOT NULL
	, last_name VARCHAR(255) NOT NULL
	, tenant_name VARCHAR(255) NOT NULL DEFAULT current_setting('app.current_tenant')::VARCHAR
);
```

I want to keep it simple, so the ``tenant_name`` is simply using the value of the variable ``current_setting('app.current_tenant')``, 
which is passed from ASP.NET Core down to PostgreSQL per session. That keeps the domain model clean from any tenant identifiers.

We don't want to connect to the database as a database owner, so we prevent bypassing the Row Level Security Policies. We add an ``app_user``:

```sql
---------------------------
-- USERS                 --
---------------------------
IF NOT EXISTS (
  SELECT FROM pg_catalog.pg_roles
  WHERE  rolname = 'app_user') THEN

  CREATE ROLE app_user LOGIN PASSWORD 'app_user';
  
END IF;
```

And finally set the Row Level Security Policies on your tables:

```sql
---------------------------
-- RLS                   --
---------------------------
ALTER TABLE sample.customer ENABLE ROW LEVEL SECURITY;

---------------------------
-- RLS POLICIES         --
---------------------------

DROP POLICY IF EXISTS tenant_customer_isolation_policy ON sample.customer;

CREATE POLICY tenant_customer_isolation_policy ON sample.customer
    USING (tenant_name = current_setting('app.current_tenant')::VARCHAR);

--------------------------------
-- GRANTS                     --
--------------------------------
GRANT USAGE ON SCHEMA sample TO app_user;

-------------------------------------
-- GRANT TABLE                     --
-------------------------------------
GRANT SELECT ON TABLE sample.tenant TO app_user;

GRANT ALL ON SEQUENCE sample.customer_customer_id_seq TO app_user;
GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE sample.customer TO app_user;
```

... and we are done!

## The ASP.NET Core application ##

### The Tenant Database ###

We start the implementation by defining the ``Tenant`` domain model:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AspNetCoreMultitenancy.Multitenancy
{
    /// <summary>
    /// A Tenant.
    /// </summary>
    public class Tenant
    {
        /// <summary>
        /// Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Name.
        /// </summary>
        public string? Name { get; set; }

        /// <summary>
        /// Description.
        /// </summary>
        public string? Description { get; set; }
    }
}
```

By implementing an ``IEntityTypeConfiguration<Tenant>`` interface we configure the database mapping:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace AspNetCoreMultitenancy.Multitenancy
{
    public class TenantEntityTypeConfiguration : IEntityTypeConfiguration<Tenant>
    {
        public void Configure(EntityTypeBuilder<Tenant> builder)
        {
            builder
                .ToTable("tenant", "sample")
                .HasKey(x => x.Id);

            builder
                .Property(x => x.Id)
                .HasColumnName("tenant_id");

            builder
                .Property(x => x.Name)
                .HasColumnName("name")
                .IsRequired();

            builder
                .Property(x => x.Description)
                .HasColumnName("description")
                .IsRequired();
        }
    }
}
```

It's useful to also provide a ``TenantDbContext`` to access the Tenant Database:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;

namespace AspNetCoreMultitenancy.Multitenancy
{
    /// <summary>
    /// A DbContext to access the Tenant Database.
    /// </summary>
    public class TenantDbContext : DbContext
    {
        public TenantDbContext(DbContextOptions<TenantDbContext> options)
            : base(options)
        {
        }

        /// <summary>
        /// Tenants.
        /// </summary>
        public DbSet<Tenant> Tenants { get; set; } = null!;

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.ApplyConfiguration(new TenantEntityTypeConfiguration());
        }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            base.OnConfiguring(optionsBuilder);
        }
    }
}
```

That's it for managing the Tenants.

### The Tenant Identifier in the ASP.NET Core application ###

#### Custom Middleware for extracting the Tenant Identifier ####

The Tenant Name is going to be passed to the ASP.NET Core application using a Header with the Name ``X-TenantName``. Using a 
custom Middleware we can extract the Tenant Name, look it up from the Tenant database and write it into the ``TenantExecutionContext``:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using System.Threading.Tasks;

namespace AspNetCoreMultitenancy.Multitenancy
{
    /// <summary>
    /// Used to write the Tenant Header into the <see cref="TenantExecutionContext"/> to 
    /// flow with the async. This uses the <see cref="TenantDbContext"/> to set the Tenant, 
    /// you might find more efficient ways.
    /// </summary>
    public class MultiTenantMiddleware
    {
        /// <summary>
        /// The Header "X-TenantName" the Request contains.
        /// </summary>
        private static readonly string TenantHeaderName = "X-TenantName";

        private readonly RequestDelegate _next;

        public MultiTenantMiddleware(RequestDelegate next)
        {
            _next = next;
        }

        public async Task InvokeAsync(HttpContext context, TenantDbContext tenantDbContext)
        {
            // Try to get the Tenant Name from the Header:
            if (context.Request.Headers.ContainsKey(TenantHeaderName))
            {
                string tenantName = context.Request.Headers[TenantHeaderName];

                // It's probably OK for the Tenant Name to be empty, which may or may not be valid for your scenario.
                if (!string.IsNullOrWhiteSpace(tenantName))
                {
                    var tenantNameString = tenantName.ToString();

                    var tenant = await tenantDbContext.Tenants
                        .AsNoTracking()
                        .FirstOrDefaultAsync(x => x.Name == tenantNameString, context.RequestAborted);

                    if (tenant == null)
                    {
                        context.Response.StatusCode = 400;
                        await context.Response.WriteAsync("Invalid Tenant Name", context.RequestAborted);

                        return;
                    }

                    // We know the Tenant, so set it in the TenantExecutionContext:
                    TenantExecutionContext.SetTenant(tenant);
                }
            }

            await _next(context);
        }
    }

    public static class TenantMiddlewareExtensions
    {
        public static IApplicationBuilder UseMultiTenant(this IApplicationBuilder builder)
        {
            return builder.UseMiddleware<MultiTenantMiddleware>();
        }
    }
}
```

#### Passing the Tenant Identifier through the application ####

The idea here is to just let the ``Tenant`` flow with the async execution by using a global ``AsyncLocal<Tenant>``. I am calling the class ``TenantExecutionContext``:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Threading;

namespace AspNetCoreMultitenancy.Multitenancy
{
    /// <summary>
    /// Holds the Tenant in an Ambient Context, which simplifies the code.
    /// </summary>
    public static class TenantExecutionContext
    {
        /// <summary>
        /// Holds the Tenant in an <see cref="AsyncLocal{T}"/>, so it flows top-down.
        /// </summary>
        private static AsyncLocal<Tenant> tenant = new AsyncLocal<Tenant>();

        /// <summary>
        /// Gets the current Tenant 
        /// </summary>
        public static Tenant? Tenant => tenant.Value;

        public static void SetTenant(Tenant value)
        {
            if(value == null)
            {
                throw new InvalidOperationException($"Tried set an empty Tenant");
            }

            var currentTenant = tenant.Value;

            if(currentTenant == null || string.Equals(currentTenant.Name, value.Name, StringComparison.InvariantCulture))
            {
                tenant.Value = value;

                return;
            }

            throw new InvalidOperationException($"Tried assign the Tenant to '{value.Name}', but it is already set to {currentTenant.Name}");
       }
    }
}
```

#### Passing the Tenant Identifier to Postgres ####

Remember how Postgres used a Session variable to resolve the current Tenant Name? By implementing a ``DbConnectionInterceptor`` we 
can set the ``app.current_tenant`` session variable, when the Database connection is opened:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore.Diagnostics;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace AspNetCoreMultitenancy.Multitenancy
{
    public class PostgresTenantDbConnectionInterceptor : DbConnectionInterceptor
    {
        public override void ConnectionOpened(DbConnection connection, ConnectionEndEventData eventData)
        {
            if(TenantExecutionContext.Tenant != null)
            {
                using (var cmd = connection.CreateCommand())
                {
                    PrepareCommand(cmd, TenantExecutionContext.Tenant);

                    cmd.ExecuteNonQuery();
                }
            }
        }

        public override async Task ConnectionOpenedAsync(DbConnection connection, ConnectionEndEventData eventData, CancellationToken cancellationToken = default)
        {
            if (TenantExecutionContext.Tenant != null)
            {
                using (var cmd = connection.CreateCommand())
                {
                    PrepareCommand(cmd, TenantExecutionContext.Tenant);

                    await cmd.ExecuteNonQueryAsync(cancellationToken);
                }
            }
        }

        private void PrepareCommand(DbCommand cmd, Tenant tenant)
        {
            cmd.CommandText = $"SET app.current_tenant = '{tenant.Name}'";
        }
    }
}
```

## A sample Multi-Tenant application ##

We will be writing a sample multi-tenant application, that is used to manage customers.

### Data Model ###
We start by defining the Domain Model ``Customer``, which will be managed by the ASP.NET Core application:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AspNetCoreMultitenancy.Models
{
    /// <summary>
    /// Customer.
    /// </summary>
    public class Customer
    {
        /// <summary>
        /// Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// First Name.
        /// </summary>
        public string? FirstName { get; set; }

        /// <summary>
        /// Last Name.
        /// </summary>
        public string? LastName { get; set; }
    }
}
```

### Database ###

... and implement an ``IEntityTypeConfiguration<Customer>`` to configure the database mapping:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AspNetCoreMultitenancy.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace AspNetCoreMultitenancy.Database.Mappings
{
    public class CustomerEntityTypeConfiguration : IEntityTypeConfiguration<Customer>
    {
        public void Configure(EntityTypeBuilder<Customer> builder)
        {
            builder
                .ToTable("customer", "sample")
                .HasKey(x => x.Id);

            builder
                .Property(x => x.Id)
                .HasColumnName("customer_id");

            builder
                .Property(x => x.FirstName)
                .HasColumnName("first_name");

            builder
                .Property(x => x.LastName)
                .HasColumnName("last_name");
        }
    }
}
```

And we will provide the database access using the ``ApplicationDbContext``:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AspNetCoreMultitenancy.Database.Mappings;
using AspNetCoreMultitenancy.Models;
using Microsoft.EntityFrameworkCore;

namespace AspNetCoreMultitenancy.Database
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) 
            : base(options)
        {
        }

        /// <summary>
        /// Customers.
        /// </summary>
        public DbSet<Customer> Customers { get; set; } = null!;

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.ApplyConfiguration(new CustomerEntityTypeConfiguration());
        }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            base.OnConfiguring(optionsBuilder);
        }
    }
}
```

### Web Service  ###

#### Domain Transfer Object ####

It's always a good idea to separate your Domain Model and your Web service model. In this example it's a little 
overkill, but let's be a good citizen and define a DTO for the Web service endpoints:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace AspNetCoreMultitenancy.Dto
{
    /// <summary>
    /// A Customer.
    /// </summary>
    public class CustomerDto
    {
        /// <summary>
        /// Id.
        /// </summary>
        [JsonPropertyName("id")]
        public int Id { get; set; }

        /// <summary>
        /// First Name.
        /// </summary>
        [JsonPropertyName("firstName")]
        public string? FirstName { get; set; }

        /// <summary>
        /// Last Name.
        /// </summary>
        [JsonPropertyName("lastName")]
        public string? LastName { get; set; }
    }
}
```

In the ``CustomerConverter`` we are converting between the Model and DTOs:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AspNetCoreMultitenancy.Dto;
using AspNetCoreMultitenancy.Models;

namespace AspNetCoreMultitenancy.Converters
{
    public static class CustomerConverter
    {
        public static Customer ToModel(CustomerDto source)
        {
            return new Customer
            {
                Id = source.Id,
                FirstName = source.FirstName,
                LastName = source.LastName,
            };
        }

        public static CustomerDto ToDto(Customer source)
        {
            return new CustomerDto
            {
                Id = source.Id,
                FirstName = source.FirstName,
                LastName = source.LastName,
            };
        }
    }
}
```

#### ASP.NET Core WebAPI Controller ####

In the ``CustomerController`` we are now providing the RESTful CRUD Endpoints:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AspNetCoreMultitenancy.Converters;
using AspNetCoreMultitenancy.Database;
using AspNetCoreMultitenancy.Dto;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AspNetCoreMultitenancy.Controllers
{
    [Route("api/customer")]
    [ApiController]
    public class CustomerController : ControllerBase
    {
        private readonly ApplicationDbContext applicationDbContext;

        public CustomerController(ApplicationDbContext applicationDbContext)
        {
            this.applicationDbContext = applicationDbContext;
        }

        [HttpGet]
        public async Task<IActionResult> Get(CancellationToken cancellationToken)
        {
            var customers = await applicationDbContext.Customers
                .AsNoTracking()
                .ToListAsync(cancellationToken);

            var customerDtos = customers?
                .Select(customer => CustomerConverter.ToDto(customer))
                .ToList();

            return Ok(customerDtos);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> Get(int id, CancellationToken cancellationToken)
        {
            var customer = await applicationDbContext.Customers.FindAsync(id);

            if(customer == null)
            {
                return NotFound();
            }

            var customerDto = CustomerConverter.ToDto(customer);

            return Ok(customerDto);
        }

        [HttpPost]
        public async Task<IActionResult> Post([FromBody] CustomerDto customerDto, CancellationToken cancellationToken)
        {
            if(!ModelState.IsValid)
            {
                return BadRequest(ModelState);
            }

            var customer = CustomerConverter.ToModel(customerDto);

            await applicationDbContext.AddAsync(customer, cancellationToken);
            await applicationDbContext.SaveChangesAsync(cancellationToken);

            return CreatedAtAction(nameof(Get), new { id = customer.Id }, CustomerConverter.ToDto(customer));
        }

        [HttpPut("{id}")]
        public async Task<IActionResult> Put(int id, [FromBody] CustomerDto customerDto, CancellationToken cancellationToken)
        {
            if (!ModelState.IsValid)
            {
                return BadRequest(ModelState);
            }

            var customer = CustomerConverter.ToModel(customerDto);

            applicationDbContext.Customers.Update(customer);
            await applicationDbContext.SaveChangesAsync(cancellationToken);

            return NoContent();
        }

        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(int id, CancellationToken cancellationToken)
        {
            var customer = await applicationDbContext.Customers.FindAsync(id);

            if(customer == null)
            {
                return NotFound();
            }

            applicationDbContext.Customers.Remove(customer);

            await applicationDbContext.SaveChangesAsync(cancellationToken);

            return NoContent();
        }
    }
}
```

#### Enabling Multitenancy on Startup ####

Did you see anything related to Multitenancy yet? 

No, because the magic happens in the ``Startup`` for the application. 

By using the ``UseMultiTenant()`` extension you are enabling the Multitenant Middleware and by adding the 
``PostgresTenantDbConnectionInterceptor`` you are setting the ``app.current_tenant`` for each PostgreSQL 
session:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AspNetCoreMultitenancy.Database;
using AspNetCoreMultitenancy.Multitenancy;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace AspNetCoreMultitenancy
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // Register Scoped DbContexts:
            services
                // Register the Tenant Database:
                .AddDbContext<TenantDbContext>(options => options.UseNpgsql("Host=localhost;Port=5432;Database=sampledb;Pooling=false;User Id=app_user;Password=app_user;"))
                // Register the Application Database:
                .AddDbContext<ApplicationDbContext>(options => options
                    .AddInterceptors(new PostgresTenantDbConnectionInterceptor())
                    .UseNpgsql("Host=localhost;Port=5432;Database=sampledb;Pooling=false;User Id=app_user;Password=app_user;"));

            services.AddControllers();
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }
            else
            {
                app.UseExceptionHandler("/Error");
            }

            app.UseStaticFiles();

            app.UseMultiTenant();

            app.UseRouting();

            app.UseEndpoints(endpoints =>
            {
                endpoints.MapControllers();
            });
        }
    }
}
```

And that's it.

#### Does it work? ####

We start with inserting customers to the database of Tenant ``Tenant 1`` (``33F3857A-D8D7-449E-B71F-B5B960A6D89A``):

```
> curl -H "X-TenantName: 33F3857A-D8D7-449E-B71F-B5B960A6D89A" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Philipp\", \"lastName\" : \"Wagner\"}"  http://localhost:5000/api/customer

{"id":1,"firstName":"Philipp","lastName":"Wagner"}

> curl -H "X-TenantName: 33F3857A-D8D7-449E-B71F-B5B960A6D89A" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Max\", \"lastName\" : \"Mustermann\"}"  http://localhost:5000/api/customer

{"id":2,"firstName":"Max","lastName":"Mustermann"}
```

Getting a list of all customers for ``Tenant 1`` will now return two customers:

```
> curl -H "X-TenantName: 33F3857A-D8D7-449E-B71F-B5B960A6D89A" -H "Content-Type: application/json" -X GET http://localhost:5000/api/customer

[{"id":1,"firstName":"Philipp","lastName":"Wagner"},{"id":2,"firstName":"Max","lastName":"Mustermann"}]
```

While requesting a list of all customers for ``Tenant 2`` (``7344384A-A2F4-4FC4-A382-315FCB421A72``) returns an empty list:

```
> curl -H "X-TenantName: 7344384A-A2F4-4FC4-A382-315FCB421A72" -H "Content-Type: application/json" -X GET http://localhost:5000/api/customer

[]
```

We can now insert a customer for ``Tenant 2``:

```
> curl -H "X-TenantName: 7344384A-A2F4-4FC4-A382-315FCB421A72" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Hans\", \"lastName\" : \"Wurst\"}"  http://localhost:5000/api/customer

{"id":3,"firstName":"Hans","lastName":"Wurst"}
```

Querying the database with ``Tenant 1`` still returns the two customers:

```
> curl -H "X-TenantName: 33F3857A-D8D7-449E-B71F-B5B960A6D89A" -H "Content-Type: application/json" -X GET http://localhost:5000/api/customer

[{"id":1,"firstName":"Philipp","lastName":"Wagner"},{"id":2,"firstName":"Max","lastName":"Mustermann"}]
```

Querying with ``Tenant 2`` will now return the inserted customer:

```
> curl -H "X-TenantName: 7344384A-A2F4-4FC4-A382-315FCB421A72" -H "Content-Type: application/json" -X GET http://localhost:5000/api/customer

[{"id":3,"firstName":"Hans","lastName":"Wurst"}]
```

Works!

## Discussion ##

The article has provoked some discussion at Twitter and I think it's worth adding the points noted by [@roji](https://github.com/roji) here.

I am quoting from the [original Twitter thread](https://twitter.com/shayrojansky/status/1478826905348587524):

> Careful where you add the tenant ID from. This sample takes it from the HTTP request, which means 
> the client application can decide to be anyone they want - you probably want to use actual authentication 
> to manage this.
> 
> The interceptor approach adds a roundtrip before each and every database command, just to set the tenant ID, 
> not amazing for perf. I'd instead do that roundtrip once, when the DbContext is set up for the scope 
> (roundtrip-per-web-request instead of roundtrip-per-db-command).
> 
> Finally, the tenant ID is managed via AsyncLocal, from the middleware to the interceptor. That's OK, but it 
> should be pretty simply to use standard DI techniques instead. I'd personally not resort to AsyncLocal unless 
> there's specific difficulties with the DI approach.