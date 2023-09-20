title: Authentication and Authorization for an ASP.NET Core OData API
date: 2022-11-28 10:21
tags: aspnetcore, csharp, odata
category: csharp
slug: aspnet_core_odata_authorization
author: Philipp Wagner
summary: This article shows how to secure an ASP.NET Core OData API using the ODataAuthorization library.

In the last article I have shown how to quickly build a Backend and a Frontend using ASP.NET Core OData and 
Angular. But what's keeping us from putting it in production? We didn't add any authentication and 
authorization. Ouch.

What's the problem?

An OData query gives a client a lot of freedom. That's great! But it's maybe way too much freedom. Do you want to 
allow all users to `$expand` related entities without checking, if they are authorized to do so? What about using 
OData navigation properties to address related data? We need to validate these requests.

The ASP.NET Core Authorization-middleware can only secure the access to an endpoint. That's totally fine, if you 
disallow `$expand` queries and do not include any navigation properties in your entity model. But for anything 
more sophisticated... it won't work.

So this article introduces `ODataAuthorization`, which uses the permissions defined in the capability annotations of 
the OData model to apply authorization policies to an OData-enabled Web API . It is a fork of the [WebApiAuthorization] 
library and basically just updates it to .NET 6 and ASP.NET Core OData 8.

So all credit goes to them!

All code can be found at:

* [https://codeberg.org/bytefish/ODataAuthorization](https://codeberg.org/bytefish/ODataAuthorization)

[WebApiAuthorization]: https://github.com/OData/WebApiAuthorization

## Table of contents ##

[TOC]

## What we are going to build ##

We are going to look at a small sample application, that has been written for `Microsoft.AspNetCore.OData.Authorization`. So 
again all credit goes to them.

The example shows how to secure an OData API using Cookue authentication and the capability annotations in the OData EDM model. The 
Web API, that's going to be created has a single entity set `Products` and only supports the basic CRUD requests. 

A user querying the OData model has to provide the following claims for accessing the data:

| Endpoint                  | Required permissions                      |            
|---------------------------|--------------------------------------------
|`GET /odata/Products`      | `Product.Read`                            |    
|`GET /odata/Products/1`    | `Product.Read` or `Product.ReadByKey`     |
|`DELETE /odata/Products/1` | `Product.Delete`                          |
|`POST /odata/Products`     | `Product.Create`                          |
|`PATCH /odata/Products(1)` | `Product.Update`                          |

The Postman application is used to query the Web API, which is ...

> [...] an API platform for building and using APIs. Postman simplifies each step of the API lifecycle and 
> streamlines collaboration so that you can create better APIs faster.

You can use the Postman collections provided in the `/samples` folder of the project to get started:

* [https://codeberg.org/bytefish/ODataAuthorization/src/branch/main/samples](https://codeberg.org/bytefish/ODataAuthorization/src/branch/main/samples)

## CookieAuthenticationSample ##


We start by adding the `ODataAuthorization` to the project:

```
> Install-Package ODataAuthorization -Version 1.0.0
```

### Database Setup ###

We want to do CRUD operations on a `Product`:

```csharp
namespace ODataAuthorizationDemo.Models
{
    public class Product
    {
        public int Id { get; set; }

        public string Name { get; set; }

        public int Price { get; set; }
    }
}
```

Entity Framework Core is used, so we create `DbContext` and add a `DbSet<Product>`:

```csharp
using Microsoft.EntityFrameworkCore;

namespace ODataAuthorizationDemo.Models
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
        {
        }

        public DbSet<Product> Products { get; set; }
    }
}
```

And in the Startup the DbContext is configured to use an In-Memory Database:

```csharp
namespace ODataAuthorizationDemo
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
            services.AddDbContext<AppDbContext>(opt => opt.UseInMemoryDatabase("ODataAuthDemo"));
            
            // ...
        }
        
        // ...
    }
    
}
```

### Authentication Endpoints ###

The idea of the sample application is to login with a set of requested scopes, that the user has:

So we add a `LoginData` model:

```csharp
namespace ODataAuthorizationDemo.Models
{
    public class LoginData
    {
        public string[] RequestedScopes { get; set; }
    }
}
```

This set of scopes is then passed to the `AuthController`, which provides a `/login` and `/logout` endpoint. On login a `ClaimsPrincipal` is 
created with all requested scopes. Under the hood the `ClaimsPrincipal` then is serialized, written into a Session Cookie and passed back to 
the client. 

```csharp
using System.Linq;
using System.Security.Claims;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using ODataAuthorizationDemo.Models;

namespace ODataAuthorizationDemo.Controllers
{
    [Route("[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        [HttpPost]
        [Route("login")]
        public async Task<IActionResult> Login([FromBody] LoginData data)
        {
            // create a claim for each request scope
            var claims = data.RequestedScopes.Select(s => new Claim("Scope", s));

            var claimsIdentity = new ClaimsIdentity(
                claims, CookieAuthenticationDefaults.AuthenticationScheme);

            var user = new ClaimsPrincipal(claimsIdentity);

            await HttpContext.SignInAsync(
                CookieAuthenticationDefaults.AuthenticationScheme,
                user);

            return Ok();
        }

        [HttpPost]
        [Route("logout")]
        public async Task<IActionResult> Logout()
        {
            await HttpContext.SignOutAsync(
                CookieAuthenticationDefaults.AuthenticationScheme);

            return Ok();
        }
    }
}
```

Now download the Postman Collection for the CookieAuthenticationSample and import it to Postman:

* https://codeberg.org/bytefish/ODataAuthorization/src/branch/main/samples/CookieAuthenticationSample.postman_collection.json](https://codeberg.org/bytefish/ODataAuthorization/src/branch/main/samples/CookieAuthenticationSample.postman_collection.json)

And executing the `/auth/login` endpoint shows, that the response contains a Cookie named `.AspNetCore.Cookies` with some Base64 value:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_authorization/AuthEndpoint_Login_Scopes.jpg">
        <img src="/static/images/blog/aspnet_core_odata_authorization/AuthEndpoint_Login_Scopes.jpg" alt="Cookies for Endpoint">
    </a>
</div>

To logout make a POST `/auth/logout` request.

### Product Endpoints ###

And we finally add an `ODataController`, that provides the CRUD enpoints for a Product. It uses the `AppDbContext` for reading and writing to a database:

```csharp
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.OData.Deltas;
using Microsoft.AspNetCore.OData.Routing.Controllers;
using ODataAuthorizationDemo.Models;

namespace ODataAuthorizationDemo.Controllers
{
    public class ProductsController: ODataController
    {
        private AppDbContext _dbContext;

        public ProductsController(AppDbContext dbContext)
        {
            _dbContext = dbContext;
        }

        public IActionResult Get()
        {
            return Ok(_dbContext.Products);
        }

        public IActionResult Get(int key)
        {
            return Ok(_dbContext.Products.Find(key));
        }

        public async Task<IActionResult> Post([FromBody] Product product)
        {
            _dbContext.Products.Add(product);
            await _dbContext.SaveChangesAsync();
            return Ok(product);
        }

        public async Task<IActionResult> Patch(int key, [FromBody] Delta<Product> delta)
        {
            var product = await _dbContext.Products.FindAsync(key);
            delta.Patch(product);
            _dbContext.Products.Update(product);
            await _dbContext.SaveChangesAsync();
            return Ok(product);
        }

        public async Task<IActionResult> Delete(int key)
        {
            var product = await _dbContext.Products.FindAsync(key);
            _dbContext.Products.Remove(product);
            await _dbContext.SaveChangesAsync();
            return Ok(product);
        }
    }
}
```

And that's it!

## Configuring the OData Model ##

To secure the API we are going to use the restrictions vocabulary defined in the OData specification and 
assign Scope names to them. 

The scopes are:

| Scope                     | Description                       |          
|---------------------------|-----------------------------------|
|`Product.Read`             | Reads all products                |    
|`Product.ReadByKey`        | Read a single product by its key  |
|`Product.Create`           | Creates a new product             |
|`Product.Update`           | Updates a product                 |
|`Product.Delete`           | Deletes a product                 |


By using the `ODataConventionModelBuilder` the implementation in the `AppEdmModel` looks like this:

```csharp
using Microsoft.OData.Edm;
using Microsoft.OData.ModelBuilder;

namespace ODataAuthorizationDemo.Models
{
    public static class AppEdmModel
    {
        public static IEdmModel GetModel()
        {
            var builder = new ODataConventionModelBuilder();

            var products = builder.EntitySet<Product>("Products");

            products.HasReadRestrictions()
                .HasPermissions(p =>
                    p.HasSchemeName("Scheme").HasScopes(s => s.HasScope("Product.Read")))
                .HasReadByKeyRestrictions(r => r.HasPermissions(p =>
                    p.HasSchemeName("Scheme").HasScopes(s => s.HasScope("Product.ReadByKey"))));

            products.HasInsertRestrictions()
                .HasPermissions(p => p.HasSchemeName("Scheme").HasScopes(s => s.HasScope("Product.Create")));

            products.HasUpdateRestrictions()
                .HasPermissions(p => p.HasSchemeName("Scheme").HasScopes(s => s.HasScope("Product.Update")));

            products.HasDeleteRestrictions()
                .HasPermissions(p => p.HasSchemeName("Scheme").HasScopes(s => s.HasScope("Product.Delete")));

            return builder.GetEdmModel();
        }
    }
}
```

You can learn more about the available Restrictions here:

* [https://github.com/oasis-tcs/odata-vocabularies/blob/main/vocabularies/Org.OData.Capabilities.V1.md](https://github.com/oasis-tcs/odata-vocabularies/blob/main/vocabularies/Org.OData.Capabilities.V1.md)

## Registering the Middleware ##

Now in the `Startup` we are adding Cookie Authentication and use the `IServiceCollection#AddODataAuthorization` extension method to add OData Authorization. To resolve 
the scopes available for a given `ClaimsPrincipal`, you need to configure the `ScopeFinder` for the OData authorization middleware:

```csharp
// ...

namespace ODataAuthorizationDemo
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
            // ...

            services
                .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
                .AddCookie((options) =>
                {
                    options.AccessDeniedPath = string.Empty;

                    options.Events.OnRedirectToAccessDenied = (context) =>
                    {
                        context.Response.StatusCode = StatusCodes.Status403Forbidden;

                        return Task.CompletedTask;
                    };

                    options.Events.OnRedirectToLogin = (context) =>
                    {
                        context.Response.StatusCode = StatusCodes.Status401Unauthorized;

                        return Task.CompletedTask;
                    };
                });

            services
                .AddControllers()
                // Add OData Routes:
                .AddOData((opt) => opt
                    .AddRouteComponents("odata", AppEdmModel.GetModel())
                    .EnableQueryFeatures())
                // Add OData Authorization:
                .AddODataAuthorization((options) =>
                {
                    options.ScopesFinder = context =>
                    {
                        // Select all "Scope" Claims of the ClaimsPrincipal:
                        var scopes = context.User
                            .FindAll("Scope")
                            .Select(claim => claim.Value);

                        return Task.FromResult(scopes);
                    };
           });
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
        {
            // ...
            
            app.UseAuthentication();
            app.UseAuthorization();
           
            // ...
        }
    }
```

## Examples ##

Let's see how it works.

### Product.ReadByKey ###

Imagine we want to allow the user to only read a Product by its key. This is useful, if a user should be able to get a single product, but 
should not be able to query the entire `EntitySet`.

We are sending the following `/auth/login` request:

```json
{
    "RequestedScopes": ["Product.ReadByKey"]
}
```

A HTTP GET on `/odata/Products` now returns a HTTP Status 403 (Forbidden), because we lack the `Product.Read` scope:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_ReadByKeyOnly_GetAll.jpg">
        <img src="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_ReadByKeyOnly_GetAll.jpg" alt="Shows the 403 Error when Scope is Missing">
    </a>
</div>

A HTTP GET on `/odata/Products(1)` for reading by key returns the HTTP Status 200 (OK) and contains the expected payload:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_ReadByKeyOnly_GetByKey.jpg">
        <img src="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_ReadByKeyOnly_GetByKey.jpg" alt="Shows the 200 Status (OK) with data, when Scope is available">
    </a>
</div>

The endpoints for create, update and delete will also return a HTTP Status 403 (Forbidden), because we are not authorized.

### Product.Create and Product.ReadByKey ###

Imagine we want to allow a user to also create a product. This requires us to pass the `Product.Create`.

We are sending the following `/auth/login` request:

```json
{
    "RequestedScopes": ["Product.Create", "Product.ReadByKey"]
}
```

The user is now allowed to create an entity by sending a HTTP POST to the `/odata/Products` endpoint: 

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_Create_CreateProduct.jpg">
        <img src="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_Create_CreateProduct.jpg" alt="A Product is created, because the user has the Product.Create Scope">
    </a>
</div>

The fresh product can now be queried by calling `/odata/Products(10)`:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_Create_ReadByKey.jpg">
        <img src="/static/images/blog/aspnet_core_odata_authorization/ProductEndpoint_Create_ReadByKey.jpg" alt="A Query for the Product, that has been created">
    </a>
</div>

## Conclusion ##

This article introduced the `ODataAuthorization` library for ASP.NET Core OData 8. 

It provides a way to protected your OData API using scopes extracted from a `ClaimsPrincipal`, so you can 
restrict access to your data model in a similar way to the Microsoft Graph API.