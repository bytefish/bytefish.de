title: WideWorldImporters: Building an application with Angular, ASP.NET Core OData and EntityFramework Core
date: 2022-04-08 20:44
tags: aspnetcore, csharp, odata
category: csharp
slug: aspnet_core_odata_example
author: Philipp Wagner
summary: This article shows how to build a Frontend and Backend application with Angular, Clarity, ASP.NET Core OData, and Entity Framework Core.

"I just want to show some data in a table and filter it. Why is all this so, so complicated?", 
said everyone trying to quickly expose a dataset with an Angular application. It doesn't have 
to be this way.

In this article I will show you how to use ASP.NET Core OData and EF Core to quickly build Backends 
and how to use Angular to display, filter and paginate datasets. It's not complicated, but there had 
been quite a few pieces to the puzzle.

This is an article, that has been in the back of my mind for a year and I am glad I finally get it out.

All code can be found at:

* [https://github.com/bytefish/WideWorldImporters](https://github.com/bytefish/WideWorldImporters)

## What we are going to build ##

We will build a Backend and Frontend for the "Wide World Importers" database, which is a Microsoft SQL Server 
sample database for a fictional company:

* [https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is](https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is)

The Microsoft documentation describes the fictionous "Wide World Importers" as ...

> [...] a wholesale novelty goods importer and distributor operating from the San Francisco bay area.
> 
> As a wholesaler, WWI's customers are mostly companies who resell to individuals. WWI sells to retail customers 
> across the United States including specialty stores, supermarkets, computing stores, tourist attraction shops, 
> and some individuals. WWI also sells to other wholesalers via a network of agents who promote the products on 
> WWI's behalf. While all of WWI's customers are currently based in the United States, the company is intending to 
> push for expansion into other countries.
>
> WWI buys goods from suppliers including novelty and toy manufacturers, and other novelty wholesalers. They stock 
> the goods in their WWI warehouse and reorder from suppliers as needed to fulfil customer orders. They also purchase 
> large volumes of packaging materials, and sell these in smaller quantities as a convenience for the customers.
>
> Recently WWI started to sell a variety of edible novelties such as chilli chocolates. The company previously did 
> not have to handle chilled items. Now, to meet food handling requirements, they must monitor the temperature in their 
> chiller room and any of their trucks that have chiller sections.

I think it's a perfect non-trivial database to work with!

We are building a Backend, that scaffolds the WWI database and exposes the data with Microsoft ASP.NET Core OData 8. We will 
learn how to extend Microsoft ASP.NET Core OData 8 for spatial types, see how to generate the OData endpoints using T4 Text 
Templates and provide OpenAPI 3.0 documents for Frontend code generation goodies.

The Frontend is an Angular application to query the OData endpoints. We are going to use Angular components of the Clarity 
Design system, because Clarity takes a Desktop-first approach and has a very nice Datagrid, that's easy to extend:

* [https://clarity.design/](https://clarity.design/)

The final application will look like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/00_WWI_App.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/00_WWI_App.jpg">
    </a>
</div>

So let's go ahead and write an application. 👍

## The Wide World Importers Database ##

It's always a very time-consuming task to build interesting datasets for articles. So I had a 
look at the list of Microsoft SQL Server sample databases, because... I am sure a lot of thoughts 
have been put into them:

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/)

What I like about the "Wide World Importers" sample database is, that it has been crafted to work well with 
Scaffolding. It has Stored Procedures, Views, Temporal Tables, Spatial Types... basically a lot of things to 
explore (and traps to fall into):

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers)

### Creating the WWI Database ###

We are going to work with WideWorldImporters OLTP Databasem which is described at:

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt)

In the Releases for the Repository you can find a full Backup (``WideWorldImporters-Full.bak`` ):

* https://github.com/microsoft/sql-server-samples/releases/tag/wide-world-importers-v1.0

From the GitHub Release Page we are downloading the Backup ``WideWorldImporters-Full.bak`` and import it.

We start the SQL Server Management Studio and connect to our SQLEXPRESS instance, right click on Databases and select "Restore Database ...":

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/01_Restore_WWI_Database.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/01_Restore_WWI_Database.jpg">
    </a>
</div>

On the "General" page select "Device" as the Source and select the Backup like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/02_Restore_WWI_Database.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/02_Restore_WWI_Database.jpg">
    </a>
</div>

We are now ready to import the database:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/03_Restore_WWI_Database.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/03_Restore_WWI_Database.jpg">
    </a>
</div>

The default settings will fit. Click "Ok" and wait a moment for the backup to be restored.

And... that's it!

## Implementing the Backend ##

So it begins ... 

### Project Overview ###

It's a good idea to get an high-level overview of the project first, so you get a basic idea:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/00_Solution_Overview.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/00_Solution_Overview.jpg">
    </a>
</div>

The Solution consists of two projects:

* ``WideWorldImporters.Api``
    * A ASP.NET Core Web API project to define the OData EDM Model and provide endpoints for all entities.
* ``WideWorldImporters.Database``
    * A Library project, that contains the Scaffolded Model and Database Context for the Wide World Importers database.
    
A deeper drill-down shows what the reasoning behind the folder structure is:

* ``WideWorldImporters.Api``
    *  ``Controllers``
        * T4 Text Template to generate the ODataController to expose the ``EntitySet`` and add Swagger support.
    * ``Infrastructure``
        * ``Extensions``
            * Contains useful Extension methods to work with a ``JsonNode``.
        * ``Spatial``
            * A Filter Binder to add Geometric support to Microsoft ASP.NET Core OData 8.
    * ``Services``
        * Application Services to define and share the ``IEdmModel`` for the application.
    * ``Startup.cs``
        * Configures the Dependency Injection container and configures the ASP.NET Core request pipeline.
* ``WideWorldImporters.Database``
    * ``Models``
        * The Database Model and DbContext to access the database generated by EF Core Tooling.
    * ``Spatial``
        * ``Models``
            * Partial Classes to allow Spatial OData Queries for the Entity Types.
        * ``Context`` 
            * Partial Class to allow Spatial OData Queries.
    * ``WideWorldImportContext.cs``
        * The generated ``DbContext`` for the WWI Database.

And that's it.

### Code-First or Database-First? ###

We will use EntityFramework Core to access the database, so there are two development approaches: 

* Code-First
    * You describe the database in code using the Fluent API of EF Core. This basically means writing everything by hand.
* Database-First
    * This is basically "Reverse-Engineering" the database. The Model and DbContext is scaffolded from an existing database.

Doing a Code-First implementation for a database like the Wide World Importers is idiotic. So we are going Database-First and scaffold it.

### Scaffolding the WWI Model and DbContext with EF Core Tooling ###

We'll create a separate ``WideWorldImporters.Database`` project for it, so we can evolve the Database "independently" of the Api. 

Now Entity Framework 6 had a nice designer for Database-First development. It was loved by many and hated by many. With EF Core 
you are now using a Command Line Interface, that's loved by many and hated by many. Anyways... it needs to be installed first, so 
switch to the Package Manager Console (``View -> Other Windows -> Package Manager Console``) and type:

```
dotnet tool install --global dotnet-ef
```

According to the "Entity Framework Core tools reference" documentation we also need to install ``Microsoft.EntityFrameworkCore.Design`` to use the Database-first tooling:

```
dotnet add package Microsoft.EntityFrameworkCore.Design
```

And because the database has some spatial data types, we also add the following package:

```
PM> dotnet add package Microsoft.EntityFrameworkCore.SqlServer.NetTopologySuite
```

The best place to start is the "Reverse Engineering" documentation, which describes all the switches and parameters of the ``dotnet ef`` tooling:

* [https://docs.microsoft.com/en-us/ef/core/managing-schemas/scaffolding](https://docs.microsoft.com/en-us/ef/core/managing-schemas/scaffolding)

We only want the tables in the ``Purchasing``, ``Sales`` and ``Warehouse`` schema to be scaffolded, so we add the following switch:

```
--schema Application --schema Purchasing --schema Sales --schema Warehouse
```

We want the models to go into the models folder``Models`` and assign the namespaces, so we add the following switch:

```
--context-dir "." --output-dir "Models"  --context-namespace "WideWorldImporters.Database" --namespace "WideWorldImporters.Database.Models"   
```

All this results in the following highly readable ``dotnet`` CLI command, which we will execute in the ``WideWorldImporters.Database`` folder:

```
PM> dotnet ef dbcontext scaffold "Server=localhost\SQLEXPRESS;Database=WideWorldImporters;Trusted_Connection=True;" Microsoft.EntityFrameworkCore.SqlServer  --schema Application --schema Purchasing --schema Sales --schema Warehouse --context-dir "." --output-dir "Models"  --context-namespace "WideWorldImporters.Database" --namespace "WideWorldImporters.Database.Models"   

Build started...
Build succeeded.
To protect potentially sensitive information in your connection string, you should move it out of source code. You can avoid scaffolding the connection string by using the Name= syntax to read it from configuration - see https://go.microsoft.com/fwlink/?linkid=2131148. For more guidance on storing connection strings, see http://go.microsoft.com/fwlink/?LinkId=723263.
```

Our Solution now contains the ``WideWorldImportersContext`` and all model classes:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/04_Scaffolding_WWI_Files.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/04_Scaffolding_WWI_Files.jpg">
    </a>
</div>

We need to register the ``WideWorldImportersContext`` in the Dependency Container of the ``WideWorldImporters.Api`` project, so we modify its ``Startup`` like this:

```csharp
// ...

namespace ODataSample.Backend
{
    public class Startup
    {
        // ...
		
        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // Register DbContexts:
            services.AddDbContext<WideWorldImportersContext>(options =>
            {
                options.EnableSensitiveDataLogging();
                options.UseSqlServer(@"Server=localhost\SQLEXPRESS;Database=WideWorldImporters;Trusted_Connection=True;", o => o.UseNetTopologySuite());
            });
			
            // ...
        }
    }
}
```

That's it for the Scaffolding!

### Adding ASP.NET Core OData 8 to the mix ###

What's ASP.NET Core OData? It's Microsofts implementation of the OData (Open Data Protocol) specification, which ...

> [...] is an ISO/IEC approved, OASIS standard that defines a set of best practices for building and consuming REST APIs. It enables 
> creation of REST-based services which allow resources identified using Uniform Resource Locators (URLs) and defined in a data model, 
> to be published and edited by Web clients using simple HTTP messages.

What I basically want from ASP.NET Core OData is...  

* Some piece of mind? 
    * ASP.NET Core OData (hopefully) removes discussions, if an endpoint is really RESTful according to the *holy writings* of Roy Fielding.
* Reduced Implementation efforts.
    * OData provides a standardized query language for selecting, expanding, filtering and paginating data. ASP.NET Core OData as the OData implementation supports it.

So we start by installing the ASP.NET Core OData library into the ``WideWorldImporters.Api`` project:

```
PM> dotnet add package Microsoft.AspNetCore.OData
```

Next we define an ``IEdmService`` to provide the applications ``IEdmModel``:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Edm;

namespace ODataSample.Backend.Services
{
    /// <summary>
    /// Provides access to an EdmModel.
    /// </summary>
    public interface IEdmService
    {
        /// <summary>
        /// Builds a <see cref="IEdmModel" />.
        /// </summary>
        /// <returns>The <see cref="IEdmModel"/> for the application</returns>
        IEdmModel GetEdmModel();
    }
}
```

The implementation uses the ``ODataConventionModelBuilder`` to build the ``IEdmModel`` based on conventions, like Key Names, Foreign Keys, ... . We have to 
configure the ``StockItemHolding`` entity type manually, because the database entity doesn't match OData conventions, but that's a quick one to fix:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Edm;
using Microsoft.OData.ModelBuilder;
using ODataSample.Backend.Database.Models;

namespace ODataSample.Backend.Services
{
    /// <summary>
    /// Uses an <see cref="ODataConventionModelBuilder"/> to build an <see cref="IEdmModel" />.
    /// </summary>
    public class EdmService : IEdmService
    {
        /// <summary>
        /// Builds a <see cref="IEdmModel" />.
        /// </summary>
        /// <returns>The <see cref="IEdmModel"/> for the application</returns>
        public IEdmModel GetEdmModel()
        {
            var modelBuilder = new ODataConventionModelBuilder();

            modelBuilder.EntitySet<BuyingGroup>("BuyingGroups");
            modelBuilder.EntitySet<City>("Cities");
            modelBuilder.EntitySet<ColdRoomTemperature>("ColdRoomTemperatures");
            modelBuilder.EntitySet<Color>("Colors");
            modelBuilder.EntitySet<Country>("Countries");
            modelBuilder.EntitySet<Customer>("Customers");
            modelBuilder.EntitySet<CustomerCategory>("CustomerCategories");
            modelBuilder.EntitySet<CustomerTransaction>("CustomerTransactions");
            modelBuilder.EntitySet<DeliveryMethod>("DeliveryMethods");
            modelBuilder.EntitySet<Invoice>("Invoices");
            modelBuilder.EntitySet<InvoiceLine>("InvoiceLines");
            modelBuilder.EntitySet<Order>("Orders");
            modelBuilder.EntitySet<OrderLine>("OrderLines");
            modelBuilder.EntitySet<PackageType>("PackageTypes");
            modelBuilder.EntitySet<PaymentMethod>("PaymentMethods");
            modelBuilder.EntitySet<Person>("People");
            modelBuilder.EntitySet<PurchaseOrder>("PurchaseOrders");
            modelBuilder.EntitySet<PurchaseOrderLine>("PurchaseOrderLines");
            modelBuilder.EntitySet<SpecialDeal>("SpecialDeals");
            modelBuilder.EntitySet<StateProvince>("StateProvinces");
            modelBuilder.EntitySet<StockGroup>("StockGroups");
            modelBuilder.EntitySet<StockItem>("StockItems");
            modelBuilder.EntitySet<StockItemHolding>("StockItemHoldings");
            modelBuilder.EntitySet<StockItemStockGroup>("StockItemStockGroup");
            modelBuilder.EntitySet<StockItemTransaction>("StockItemTransactions");
            modelBuilder.EntitySet<Supplier>("Suppliers");
            modelBuilder.EntitySet<SupplierCategory>("SupplierCategories");
            modelBuilder.EntitySet<SupplierTransaction>("SupplierTransactions");
            modelBuilder.EntitySet<SystemParameter>("SystemParameters");
            modelBuilder.EntitySet<TransactionType>("TransactionTypes");
            modelBuilder.EntitySet<VehicleTemperature>("VehicleTemperatures");

            // Configure EntityTypes, that could not be mapped using Conventions. We
            // could also add Attributes to the Model, but I want to avoid mixing the
            // EF Core Fluent API and Attributes.
            modelBuilder.EntityType<StockItemHolding>().HasKey(s => new { s.StockItemId });

            // ...

            // Send as Lower Camel Case Properties, so the JSON looks better:
            modelBuilder.EnableLowerCamelCase();

            return modelBuilder.GetEdmModel();
        }
    }
}
```

In the ``Startup`` we can now use the ``IServiceCollection#AddOData()`` extension to add all OData dependencies 
and configure the OData Routes. We are providing the ``IEdmModel`` by using our previously defined written 
``IEdmService``:

```csharp
// ...

namespace ODataSample.Backend
{
    public class Startup
    {
        // ...
		
        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
			// ...
            
            // Register ASP.NET Core Mvc:
            services
                // Register Web API Routes:
                .AddControllers()
                // Register OData Routes:
                .AddOData((opt, services) =>
                {
                    var edmService = services.GetRequiredService<IEdmService>();

                    opt.AddRouteComponents("odata", edmService.GetEdmModel())
                        .EnableQueryFeatures().Select().Expand().Count().Filter().SetMaxTop(250);
                });

        }
    }
}
```

We can now start the project and navigate to the following endpoint to get the full EDMX model:

```
http://localhost:5000/odata/$metadata
```

And drums please 🥁 ...

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/05_OData_Edmx_Model.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/05_OData_Edmx_Model.jpg">
    </a>
</div>

Job done! 👍

### Generating an ODataController using T4 Text Templates ###

As humans we tend to automate boring and repititve stuff... as Software Engineers we often tend to over-automate stuff. It's sometimes 
more transparent, more flexible and easier to just write it by hand or copy & paste. Anyway, here is how I automated the task of providing 
the OData Endpoints for the application.

The idea is to have CRUD Operations for each ``EntitySet`` and have a Swagger definition like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/06_Swagger_Crud.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/06_Swagger_Crud.jpg">
    </a>
</div>

To generate them we will use T4 Text Templates, the most underrated tool in .NET development:

* [https://docs.microsoft.com/en-us/visualstudio/modeling/code-generation-and-t4-text-templates?view=vs-2022](https://docs.microsoft.com/en-us/visualstudio/modeling/code-generation-and-t4-text-templates?view=vs-2022)

In the ``WideWorldImporters.Api`` project we create a new Folder ``Controllers`` and add a new Text Template named ``EntitiesController.tt``. Bad 
thing with a T4 Text Template is, that we cannot reuse the ``IEdmModel`` information, that has been already been defined. But there isn't much 
information we need to define the Endpoints, so I didn't invest more time thinking about it.

Here is it in all its beauty ...

```
<#@ output extension=".cs"#>
<#@ template language="C#" hostspecific="True" #>
<#
    // We cannot reuse the ApplicationEdmModel, so let's type the EntitySet names by hand:
    var entitySets = new EntitySet[] 
    {
        new EntitySet("BuyingGroups", "BuyingGroup", "buyingGroupsId", "int"),
        new EntitySet("Cities", "City", "cityId", "int"),
        new EntitySet("ColdRoomTemperatures", "ColdRoomTemperature", "coldRoomTemperatureId", "long"),
        new EntitySet("Colors", "Color", "colorId", "int"),
        new EntitySet("Countries", "Country", "countryId", "int"),
        new EntitySet("Customers", "Customer", "customerId", "int"),
        new EntitySet("CustomerCategories", "CustomerCategory", "customerCategoryId", "int"),
        new EntitySet("CustomerTransactions", "CustomerTransaction", "customerTransactionId", "int"),
        new EntitySet("DeliveryMethods", "DeliveryMethod", "deliveryMethodId", "int"),
        new EntitySet("Invoices", "Invoice", "invoiceId", "int"),
        new EntitySet("InvoiceLines", "InvoiceLine", "invoiceLineId", "int"),
        new EntitySet("Orders", "Order", "orderId", "int"),
        new EntitySet("OrderLines", "OrderLine", "orderLineId", "int"),
        new EntitySet("PackageTypes", "PackageType", "packageTypeId", "int"),
        new EntitySet("PaymentMethods", "PaymentMethod", "paymentMethodId", "int"),
        new EntitySet("People", "Person", "personId", "int"),
        new EntitySet("PurchaseOrders", "PurchaseOrder", "purchaseOrderId", "int"),
        new EntitySet("PurchaseOrderLines", "PurchaseOrderLine", "purchaseOrderLineId", "int"),
        new EntitySet("SpecialDeals", "SpecialDeal", "specialDealId", "int"),
        new EntitySet("StateProvinces", "StateProvince", "stateProvinceId", "int"),
        new EntitySet("StockGroups", "StockGroup", "stockGroupId", "int"),
        new EntitySet("StockItems", "StockItem", "stockItemId", "int"),
        new EntitySet("StockItemHoldings", "StockItemHolding", "stockItemId", "int"),
        new EntitySet("StockItemStockGroups", "StockItemStockGroup", "stockItemStockGroupId", "int"),
        new EntitySet("StockItemTransactions", "StockItemTransaction", "stockItemTransactionId", "int"),
        new EntitySet("Suppliers", "Supplier", "supplierId", "int"),
        new EntitySet("SupplierCategories", "SupplierCategory", "supplierCategoryId", "int"),
        new EntitySet("SupplierTransactions", "SupplierTransaction", "supplierTransactionId", "int"),
        new EntitySet("SystemParameters", "SystemParameter", "systemParameterId", "int"),
        new EntitySet("TransactionTypes", "TransactionType", "transactionTypeId", "int"),
        new EntitySet("VehicleTemperatures", "VehicleTemperature", "vehicleTemperatureId", "int"),
    };
#>
//------------------------------------------------------------------------------
// <auto-generated>
//     This code was generated from a template.
//
//     Manual changes to this file may cause unexpected behavior in your application.
//     Manual changes to this file will be overwritten if the code is regenerated.
// </auto-generated>
//------------------------------------------------------------------------------

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.OData.Deltas;
using Microsoft.AspNetCore.OData.Query;
using Microsoft.AspNetCore.OData.Routing.Controllers;
using WideWorldImporters.Api.Database;
using WideWorldImporters.Api.Database.Models;
using WideWorldImporters.Api.Services;
using Microsoft.OpenApi.OData;
using Microsoft.OpenApi.Extensions;
using Microsoft.OpenApi;

namespace WideWorldImporters.Api.Controllers
{
    public partial class EntitiesController : ODataController
    {
        private readonly WideWorldImportersContext _context;

        public EntitiesController(WideWorldImportersContext context)
        {
            _context = context;
        }

        #region Swagger Endpoint
        
        [HttpGet("odata/$swagger")]
        public IActionResult GetSwaggerDocument([FromServices] IEdmService edmService)
        {
            var edmModel = edmService.GetEdmModel();

            // Convert to OpenApi:
            var openApiSettings = new OpenApiConvertSettings
            {
                ServiceRoot = new("http://localhost:5000"),
                PathPrefix = "odata",
                EnableKeyAsSegment = true,
            };

            var openApiDocument = edmModel.ConvertToOpenApi(openApiSettings);
            var openApiDocumentAsJson = openApiDocument.SerializeAsJson(OpenApiSpecVersion.OpenApi3_0);

            return Content(openApiDocumentAsJson, "application/json");
        }

        #endregion Swagger Endpoint

<# foreach(var entitySet in entitySets) { #>
        #region <#= entitySet.EntitySetName #>

        [EnableQuery]
        [HttpGet("odata/<#= entitySet.EntitySetName #>")]
        public IActionResult Get<#= entitySet.EntitySetName #>()
        {
            return Ok(_context.<#= entitySet.EntitySetName #>);
        }

        [EnableQuery]
        [HttpGet("odata/<#= entitySet.EntitySetName #>/{<#= entitySet.EntityKeyName #>:<#= entitySet.EntityKeyType #>}")]
        public IActionResult Get<#= entitySet.EntitySetName #>(<#= entitySet.EntityKeyType #> <#= entitySet.EntityKeyName #>)
        {
            var entity = _context.<#= entitySet.EntitySetName #>.Find(<#= entitySet.EntityKeyName #>);

            if (entity == null)
            {
                return NotFound();
            }

            return Ok(entity);
        }

        [HttpPost("odata/<#= entitySet.EntitySetName #>")]
        public IActionResult Post<#= entitySet.EntitySetName #>([FromBody]<#= entitySet.EntityName #> entity, CancellationToken token)
        {
            _context.Add(entity);
            _context.SaveChanges();

            return Created(entity);
        }

        [HttpPut("odata/<#= entitySet.EntitySetName #>/{<#= entitySet.EntityKeyName #>:<#= entitySet.EntityKeyType #>}")]
        public IActionResult Put<#= entitySet.EntitySetName #>(<#= entitySet.EntityKeyType #> <#= entitySet.EntityKeyName #>, [FromBody] Delta<<#= entitySet.EntityName #>> delta)
        {
            var original = _context.<#= entitySet.EntitySetName #>.Find(<#= entitySet.EntityKeyName #>);
            if (original == null)
            {
                return NotFound($"Not found <#= entitySet.EntityName #> with <#= entitySet.EntityKeyName #> = {<#= entitySet.EntityKeyName #>}");
            }

            delta.Put(original);
            _context.SaveChanges();
            return Updated(original);
        }

        [HttpPatch("odata/<#= entitySet.EntitySetName #>/{<#= entitySet.EntityKeyName #>:<#= entitySet.EntityKeyType #>}")]
        public IActionResult Patch<#= entitySet.EntitySetName #>(<#= entitySet.EntityKeyType #> <#= entitySet.EntityKeyName #>, Delta<<#= entitySet.EntityName #> > delta)
        {
            var original = _context.<#= entitySet.EntitySetName #>.Find(<#= entitySet.EntityKeyName #>);

            if (original == null)
            {
                return NotFound($"Not found <#= entitySet.EntityName #> with <#= entitySet.EntityKeyName #> = {<#= entitySet.EntityKeyName #>}");
            }

            delta.Patch(original);

            _context.SaveChanges();

            return Updated(original);
        }

        [HttpDelete("odata/<#= entitySet.EntitySetName #>/{<#= entitySet.EntityKeyName #>:<#= entitySet.EntityKeyType #>}")]
        public IActionResult Delete<#= entitySet.EntitySetName #>(<#= entitySet.EntityKeyType #> <#= entitySet.EntityKeyName #>)
        {
            var original = _context.<#= entitySet.EntitySetName #>.Find(<#= entitySet.EntityKeyName #>);

            if (original == null)
            {
                return NotFound($"Not found <#= entitySet.EntityName #> with <#= entitySet.EntityKeyName #> = {<#= entitySet.EntityKeyName #>}");
            }

            _context.<#= entitySet.EntitySetName #>.Remove(original);
            _context.SaveChanges();
            return Ok();
        }


        #endregion <#= entitySet.EntitySetName #>

<# } #>
    }
}

<#+
	public class EntitySet 
    {
        public readonly string EntityName;
        public readonly string EntityKeyName;
        public readonly string EntityKeyType;
        public readonly string EntitySetName;
        
        public EntitySet (string entitySetName, string entityName, string entityKeyName, string entityKeyType) 
        {
            EntitySetName = entitySetName;
            EntityName = entityName;
            EntityKeyName = entityKeyName;
            EntityKeyType = entityKeyType;
        }
    } 
#>
```

The generated code looks good and best of it all... it actually compiles:

```csharp
//------------------------------------------------------------------------------
// <auto-generated>
//     This code was generated from a template.
//
//     Manual changes to this file may cause unexpected behavior in your application.
//     Manual changes to this file will be overwritten if the code is regenerated.
// </auto-generated>
//------------------------------------------------------------------------------

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.OData.Deltas;
using Microsoft.AspNetCore.OData.Query;
using Microsoft.AspNetCore.OData.Routing.Controllers;
using WideWorldImporters.Api.Services;
using Microsoft.OpenApi.OData;
using Microsoft.OpenApi.Extensions;
using Microsoft.OpenApi;
using WideWorldImporters.Database;
using WideWorldImporters.Database.Models;

namespace WideWorldImporters.Api.Controllers
{
    public partial class EntitiesController : ODataController
    {
        private readonly WideWorldImportersContext _context;

        public EntitiesController(WideWorldImportersContext context)
        {
            _context = context;
        }

        #region Swagger Endpoint
        
        [HttpGet("odata/$swagger")]
        public IActionResult GetSwaggerDocument([FromServices] IEdmService edmService)
        {
            var edmModel = edmService.GetEdmModel();

            // Convert to OpenApi:
            var openApiSettings = new OpenApiConvertSettings
            {
                ServiceRoot = new("http://localhost:5000"),
                PathPrefix = "odata",
                EnableKeyAsSegment = true,
            };

            var openApiDocument = edmModel.ConvertToOpenApi(openApiSettings);
            var openApiDocumentAsJson = openApiDocument.SerializeAsJson(OpenApiSpecVersion.OpenApi3_0);

            return Content(openApiDocumentAsJson, "application/json");
        }

        #endregion Swagger Endpoint

        #region BuyingGroups

        [EnableQuery]
        [HttpGet("odata/BuyingGroups")]
        public IActionResult GetBuyingGroups()
        {
            return Ok(_context.BuyingGroups);
        }

        [EnableQuery]
        [HttpGet("odata/BuyingGroups/{buyingGroupsId:int}")]
        public IActionResult GetBuyingGroups(int buyingGroupsId)
        {
            var entity = _context.BuyingGroups.Find(buyingGroupsId);

            if (entity == null)
            {
                return NotFound();
            }

            return Ok(entity);
        }

        [HttpPost("odata/BuyingGroups")]
        public IActionResult PostBuyingGroups([FromBody]BuyingGroup entity, CancellationToken token)
        {
            _context.Add(entity);
            _context.SaveChanges();

            return Created(entity);
        }

        [HttpPut("odata/BuyingGroups/{buyingGroupsId:int}")]
        public IActionResult PutBuyingGroups(int buyingGroupsId, [FromBody] Delta<BuyingGroup> delta)
        {
            var original = _context.BuyingGroups.Find(buyingGroupsId);
            if (original == null)
            {
                return NotFound($"Not found BuyingGroup with buyingGroupsId = {buyingGroupsId}");
            }

            delta.Put(original);
            _context.SaveChanges();
            return Updated(original);
        }

        [HttpPatch("odata/BuyingGroups/{buyingGroupsId:int}")]
        public IActionResult PatchBuyingGroups(int buyingGroupsId, Delta<BuyingGroup > delta)
        {
            var original = _context.BuyingGroups.Find(buyingGroupsId);

            if (original == null)
            {
                return NotFound($"Not found BuyingGroup with buyingGroupsId = {buyingGroupsId}");
            }

            delta.Patch(original);

            _context.SaveChanges();

            return Updated(original);
        }

        [HttpDelete("odata/BuyingGroups/{buyingGroupsId:int}")]
        public IActionResult DeleteBuyingGroups(int buyingGroupsId)
        {
            var original = _context.BuyingGroups.Find(buyingGroupsId);

            if (original == null)
            {
                return NotFound($"Not found BuyingGroup with buyingGroupsId = {buyingGroupsId}");
            }

            _context.BuyingGroups.Remove(original);
            _context.SaveChanges();
            return Ok();
        }


        #endregion BuyingGroups

        // ..
     
     }
}
```

Now let's start the Backend now and give it a shot, a browser is totally sufficient.

Navigating to ``http://localhost:5000/odata/Orders?$top=2`` is going to return 2 orders:

```json
{
  "@odata.context": "http://localhost:5000/odata/$metadata#Orders",
  "value": [
    {
      "orderId": 1,
      "customerId": 832,
      "salespersonPersonId": 2,
      "pickedByPersonId": null,
      "contactPersonId": 3032,
      "backorderOrderId": 45,
      "orderDate": "2013-01-01T00:00:00+01:00",
      "expectedDeliveryDate": "2013-01-02T00:00:00+01:00",
      "customerPurchaseOrderNumber": "12126",
      "isUndersupplyBackordered": true,
      "comments": null,
      "deliveryInstructions": null,
      "internalComments": null,
      "pickingCompletedWhen": "2013-01-01T12:00:00+01:00",
      "lastEditedBy": 7,
      "lastEditedWhen": "2013-01-01T12:00:00+01:00"
    },
    {
      "orderId": 2,
      "customerId": 803,
      "salespersonPersonId": 8,
      "pickedByPersonId": null,
      "contactPersonId": 3003,
      "backorderOrderId": 46,
      "orderDate": "2013-01-01T00:00:00+01:00",
      "expectedDeliveryDate": "2013-01-02T00:00:00+01:00",
      "customerPurchaseOrderNumber": "15342",
      "isUndersupplyBackordered": true,
      "comments": null,
      "deliveryInstructions": null,
      "internalComments": null,
      "pickingCompletedWhen": "2013-01-01T12:00:00+01:00",
      "lastEditedBy": 7,
      "lastEditedWhen": "2013-01-01T12:00:00+01:00"
    }
  ]
}
```

Navigating to ``http://localhost:5000/odata/Orders?$top=2&$expand=salespersonPerson`` returns 2 Orders with the Sales Person included in the response:

```json
{
  "@odata.context": "http://localhost:5000/odata/$metadata#Orders(salespersonPerson())",
  "value": [
    {
      "orderId": 1,
      "customerId": 832,
      "salespersonPersonId": 2,
      "pickedByPersonId": null,
      "contactPersonId": 3032,
      "backorderOrderId": 45,
      "orderDate": "2013-01-01T00:00:00+01:00",
      "expectedDeliveryDate": "2013-01-02T00:00:00+01:00",
      "customerPurchaseOrderNumber": "12126",
      "isUndersupplyBackordered": true,
      "comments": null,
      "deliveryInstructions": null,
      "internalComments": null,
      "pickingCompletedWhen": "2013-01-01T12:00:00+01:00",
      "lastEditedBy": 7,
      "lastEditedWhen": "2013-01-01T12:00:00+01:00",
      "salespersonPerson": {
        "personId": 2,
        "fullName": "Kayla Woodcock",
        "preferredName": "Kayla",
        "searchName": "Kayla Kayla Woodcock",
        "isPermittedToLogon": true,
        "logonName": "kaylaw@wideworldimporters.com",
        "isExternalLogonProvider": false,
        "hashedPassword": "YW6bVYl2Ul5/FNeA666AxoWGlY3JfFBttBji4sSeNA4=",
        "isSystemUser": true,
        "isEmployee": true,
        "isSalesperson": true,
        "userPreferences": "{\"theme\":\"humanity\",\"dateFormat\":\"dd/mm/yy\",\"timeZone\": \"PST\",\"table\":{\"pagingType\":\"full\",\"pageLength\": 50},\"favoritesOnDashboard\":true}",
        "phoneNumber": "(415) 555-0102",
        "faxNumber": "(415) 555-0103",
        "emailAddress": "kaylaw@wideworldimporters.com",
        "photo": null,
        "customFields": "{ \"OtherLanguages\": [\"Polish\",\"Chinese\",\"Japanese\"] ,\"HireDate\":\"2008-04-19T00:00:00\",\"Title\":\"Team Member\",\"PrimarySalesTerritory\":\"Plains\",\"CommissionRate\":\"0.98\"}",
        "otherLanguages": "[\"Polish\",\"Chinese\",\"Japanese\"]",
        "lastEditedBy": 1
      }
    },
    {
      "orderId": 2,
      "customerId": 803,
      "salespersonPersonId": 8,
      "pickedByPersonId": null,
      "contactPersonId": 3003,
      "backorderOrderId": 46,
      "orderDate": "2013-01-01T00:00:00+01:00",
      "expectedDeliveryDate": "2013-01-02T00:00:00+01:00",
      "customerPurchaseOrderNumber": "15342",
      "isUndersupplyBackordered": true,
      "comments": null,
      "deliveryInstructions": null,
      "internalComments": null,
      "pickingCompletedWhen": "2013-01-01T12:00:00+01:00",
      "lastEditedBy": 7,
      "lastEditedWhen": "2013-01-01T12:00:00+01:00",
      "salespersonPerson": {
        "personId": 8,
        "fullName": "Anthony Grosse",
        "preferredName": "Anthony",
        "searchName": "Anthony Anthony Grosse",
        "isPermittedToLogon": true,
        "logonName": "anthonyg@wideworldimporters.com",
        "isExternalLogonProvider": false,
        "hashedPassword": "L9i4OKPHd3jJkPRkBzqiPA7uAZdj7WqZx3RX6GkYGd4=",
        "isSystemUser": true,
        "isEmployee": true,
        "isSalesperson": true,
        "userPreferences": "{\"theme\":\"blitzer\",\"dateFormat\":\"mm/dd/yy\",\"timeZone\": \"PST\",\"table\":{\"pagingType\":\"simple_numbers\",\"pageLength\": 10},\"favoritesOnDashboard\":true}",
        "phoneNumber": "(415) 555-0102",
        "faxNumber": "(415) 555-0103",
        "emailAddress": "anthonyg@wideworldimporters.com",
        "photo": null,
        "customFields": "{ \"OtherLanguages\": [\"Croatian\",\"Dutch\",\"Bokm\u00e5l\"] ,\"HireDate\":\"2010-07-23T00:00:00\",\"Title\":\"Team Member\",\"PrimarySalesTerritory\":\"Mideast\",\"CommissionRate\":\"0.11\"}",
        "otherLanguages": "[\"Croatian\",\"Dutch\",\"Bokm\u00e5l\"]",
        "lastEditedBy": 1
      }
    }
  ]
}
```

And navigating to ``http://localhost:5000/odata/Orders/1`` returns the Order with ID ``1``:


```json
{
  "@odata.context": "http://localhost:5000/odata/$metadata#Orders/$entity",
  "orderId": 1,
  "customerId": 832,
  "salespersonPersonId": 2,
  "pickedByPersonId": null,
  "contactPersonId": 3032,
  "backorderOrderId": 45,
  "orderDate": "2013-01-01T00:00:00+01:00",
  "expectedDeliveryDate": "2013-01-02T00:00:00+01:00",
  "customerPurchaseOrderNumber": "12126",
  "isUndersupplyBackordered": true,
  "comments": null,
  "deliveryInstructions": null,
  "internalComments": null,
  "pickingCompletedWhen": "2013-01-01T12:00:00+01:00",
  "lastEditedBy": 7,
  "lastEditedWhen": "2013-01-01T12:00:00+01:00"
}
```

Great! 🙌

### Dealing with Spatial Data in OData ###

If you query some endpoints, you'll see a ``geometry`` data type in some tables... and the house of cards falls down. 

What's the problem?

Entity Framework Core uses the ``NetTopologySuite`` library for mapping Geographical types, so all scaffolded models contain it. But 
ASP.NET Core OData uses the ``Microsoft.Spatial`` library for Geographical types. If we would expose the ``NetTopologySuite`` objects 
in the ``IEdmModel`` an unserializable hell is awaiting us (most probably).

Let's not go crazy, and solve it step by step.

We start by adding the Microsoft.Spatial library to the ``WideWorldImporters.Database`` project:

```
dotnet add package Microsoft.Spatial
```

Why add it to the ``WideWorldImporters.Database`` project? You probably remember, that the OData EDM Model is generated from the 
Scaffolded Database model. All scaffolded classes are ``partial`` classes, that means we can weave additional information to 
them at compile-time. To facilitate this, we need to live in the same assembly as the partial classes.

So we start by creating a folder ``Spatial``, where all the Spatial stuff will go.

First we need a way to convert between both the ``Microsoft.Spatial`` and ``NetTopologySuite`` representation. So I am taking the 
dumbest approach possible... Geographical objects can be represented in a "Well Known Text (WKT)" format, and every library dealing 
with Geographical data should support it.

So we add a ``GeographyConverter`` ...

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Database.Spatial
{
    public class GeographyConverter
    {
        private static readonly Microsoft.Spatial.WellKnownTextSqlFormatter _wellKnownTextFormatter = Microsoft.Spatial.WellKnownTextSqlFormatter.Create();

        public static Microsoft.Spatial.Geography? ConvertTo(NetTopologySuite.Geometries.Geometry? dbGeometry)
        {
            if(dbGeometry == null)
            {
                return null;
            }

            // Take the simplest possible route and convert to Wkt:
            var wellKnownText = dbGeometry.AsText();

            // Then parse it based on the Source type:
            switch (dbGeometry)
            {
                case NetTopologySuite.Geometries.Point _:
                    return ConvertTo<Microsoft.Spatial.GeographyPoint>(wellKnownText);
                case NetTopologySuite.Geometries.MultiPoint _:
                    return ConvertTo<Microsoft.Spatial.GeographyMultiPoint>(wellKnownText);
                case NetTopologySuite.Geometries.Polygon _:
                    return ConvertTo<Microsoft.Spatial.GeographyPolygon>(wellKnownText);
                case NetTopologySuite.Geometries.MultiPolygon _:
                    return ConvertTo<Microsoft.Spatial.GeographyMultiPolygon>(wellKnownText);
                default:
                    throw new ArgumentException($"Conversion for Type '{dbGeometry.GeometryType}' not supported");
            };
        }

        private static Microsoft.Spatial.Geography ConvertTo<TResult>(string wellKnownText)
            where TResult : Microsoft.Spatial.Geography
        {
            using(var textReader = new StringReader(wellKnownText))
            {
                    return _wellKnownTextFormatter.Read<TResult>(textReader);
            }
        }

        public static NetTopologySuite.Geometries.Geometry? ConvertFrom(Microsoft.Spatial.Geography? geography)
        {
            if(geography == null)
            {
                return null;
            }

            string wellKnownText;

            using (var textWriter = new StringWriter())
            {
                _wellKnownTextFormatter.Write(geography, textWriter);

                wellKnownText = textWriter.ToString();
            }

            return new NetTopologySuite.IO.WKTReader().Read(wellKnownText);
        }
    }
}
```

Next we create a folder ``Models``, where we will add additional data to the generated model classes using the ``partial`` keyword. Why 
not directly edit the generated model classes? Because they have been generated and you don't want to recreate all the work, when you 
are updating your database model.

We add a partial class ``City`` and add a property ``EdmLocation`` with the ``Microsoft.Spatial`` datatype. This ``Microsoft.Spatial`` 
property is going to be used by ASP.NET Core OData, while the ``NetTopologySuite`` property is used to communicate with EF Core. 

Simple as that:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Spatial;
using WideWorldImporters.Database.Spatial;

namespace WideWorldImporters.Database.Models
{
    public partial class City
    {
        public Geography? EdmLocation 
        { 
            get 
            {
                if(Location == null)
                {
                    return default;
                }

                return GeographyConverter.ConvertTo(Location);
            }

            set
            {
                Location = GeographyConverter.ConvertFrom(value);
            }
        }
    }
}
```

Does adding an ``EdmLocation`` property pollute the model? Yes it does! Do I care? No!

But wait, EF Core doesn't know how to work with ``Microsoft.Spatial``! The Wide World Importers database doesn't have a ``EdmLocation`` column 
at all! Don't fear, the Scaffolded ``WideWorldImportersContext`` is also partial and has a ``partial`` method ``OnModelCreatingPartial``, that 
can be used to configure the ``ModelBuilder``. 

We will tell the EF Core ``ModelBuilder``, that it should ignore all of our ``Microsoft.Spatial`` properties:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using WideWorldImporters.Database.Models;

namespace WideWorldImporters.Database
{
    public partial class WideWorldImportersContext : DbContext
    {
        partial void OnModelCreatingPartial(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<City>().Ignore(x => x.EdmLocation);
            modelBuilder.Entity<Country>().Ignore(x => x.EdmBorder);
            modelBuilder.Entity<Customer>().Ignore(x => x.EdmDeliveryLocation);
            modelBuilder.Entity<Supplier>().Ignore(x => x.EdmDeliveryLocation);
            modelBuilder.Entity<StateProvince>().Ignore(x => x.EdmBorder);
            modelBuilder.Entity<SystemParameter>().Ignore(x => x.EdmDeliveryLocation);
        }
    }
}
```

Switch back to the ``WideWorldImporters.Api`` project and open the ``EdmService``, that defines the ``IEdmModel``. We now have to do the exact 
opposite of the Entity Framework Core approach, by ignoring the ``NetTopologySuite`` types and renaming our ``Edm...`` properties back into 
their "original" names:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Edm;
using Microsoft.OData.ModelBuilder;
using Microsoft.Spatial;
using WideWorldImporters.Database.Models;

namespace WideWorldImporters.Api.Services
{
    /// <summary>
    /// Uses an <see cref="ODataConventionModelBuilder"/> to build an <see cref="IEdmModel" />.
    /// </summary>
    public class EdmService : IEdmService
    {
        /// <summary>
        /// Builds a <see cref="IEdmModel" />.
        /// </summary>
        /// <returns>The <see cref="IEdmModel"/> for the application</returns>
        public IEdmModel GetEdmModel()
        {
            var modelBuilder = new ODataConventionModelBuilder();
            
            // ...
            
            // Build the Spatial Types:
            BuildGeometryTypes(modelBuilder);

            // Send as Lower Camel Case Properties, so the JSON looks better:
            modelBuilder.EnableLowerCamelCase();

            return modelBuilder.GetEdmModel();
        }

        private static void BuildGeometryTypes(ODataConventionModelBuilder modelBuilder)
        {
            modelBuilder.ComplexType<Geography>();

            modelBuilder.EntityType<City>().Ignore(x => x.Location);
            modelBuilder.EntityType<Country>().Ignore(x => x.Border);
            modelBuilder.EntityType<Customer>().Ignore(x => x.DeliveryLocation);
            modelBuilder.EntityType<Supplier>().Ignore(x => x.DeliveryLocation);
            modelBuilder.EntityType<StateProvince>().Ignore(x => x.Border);
            modelBuilder.EntityType<SystemParameter>().Ignore(x => x.DeliveryLocation);

            // We will rewrite the Property Name from EdmLocation -> Location, so
            // it matches fine with the EF Core Model for filtering.
            modelBuilder.OnModelCreating += (builder) =>
            {
                foreach (StructuralTypeConfiguration typeConfiguration in builder.StructuralTypes)
                {
                    foreach (PropertyConfiguration property in typeConfiguration.Properties)
                    {
                        // Let's not introduce magic strings and make it more safe for refactorings:
                        string propertyName = (typeConfiguration.Name, property.Name) switch
                        {
                            (nameof(City), nameof(City.EdmLocation)) => nameof(City.Location),
                            (nameof(Country), nameof(Country.EdmBorder)) => nameof(Country.Border),
                            (nameof(Customer), nameof(Customer.EdmDeliveryLocation)) => nameof(Customer.DeliveryLocation),
                            (nameof(Supplier), nameof(Supplier.EdmDeliveryLocation)) => nameof(Supplier.DeliveryLocation),
                            (nameof(StateProvince), nameof(StateProvince.EdmBorder)) => nameof(StateProvince.Border),
                            (nameof(SystemParameter), nameof(SystemParameter.EdmDeliveryLocation)) => nameof(SystemParameter.DeliveryLocation),
                            _ => property.Name,
                        };

                        property.Name = propertyName;
                    }
                }
            };
        }
    }
}
```

Start the ``WideWorldImporters.Api`` project and navigate to ``http://localhost:5000/swagger/index.html``, et voila, the model 
now uses the correct OData types:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/07_Schema_Edm_Geometry.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/07_Schema_Edm_Geometry.jpg">
    </a>
</div>

Querying for countries should now also return the Border Polygon:

```json
{
  "@odata.context": "http://localhost:5000/odata/$metadata#Countries",
  "@odata.count": 190,
  "value": [
    {
      "countryId": 1,
      "countryName": "Afghanistan",
      "formalName": "Islamic State of Afghanistan",
      "isoAlpha3Code": "AFG",
      "isoNumericCode": 4,
      "countryType": "UN Member State",
      "latestRecordedPopulation": 28400000,
      "continent": "Asia",
      "region": "Asia",
      "subregion": "Southern Asia",
      "lastEditedBy": 1,
      "border@odata.type": "#GeographyPolygon",
      "border": {
        "type": "Polygon",
        "coordinates": [
          [
            [ 74.89130859375001, 37.231640625 ],
            [ 74.87539062500002, 37.241992187499996 ],
            [ 74.83046875000002, 37.285937499999996 ],
            [ 74.73056640625, 37.35703125 ],
            [ 74.65937500000001, 37.394482421875 ],
            [ 74.52421875000002, 37.382373046874996 ],
            [ 74.444921875, 37.39560546875 ],
            [ 74.34902343750002, 37.418749999999996 ],
            [ 74.25966796875002, 37.415429687499994 ],
            [ 74.20351562500002, 37.372460937499994 ],
            [ 74.16708984375, 37.329443359375 ],
            [ 74.077734375, 37.316210937499996 ],
            [ 73.948828125, 37.283154296875 ],
            [ 73.749609375, 37.231787109375 ],
            [ 73.65351562500001, 37.23935546875 ],
            [ 73.6275390625, 37.261572265625 ],
            [ 73.64882812500002, 37.2912109375 ]
          ]
        ],
        "crs": {
          "type": "name",
          "properties": { "name": "EPSG:4326" }
        }
      }
    }
  ]
}
```

And what's all that good for? This enables you to add the Spatial functionality, that isn't provided by ASP.NET Core OData 8 as of writing:

* [https://devblogs.microsoft.com/odata/customizing-filter-for-spatial-data-in-asp-net-core-odata-8/](https://devblogs.microsoft.com/odata/customizing-filter-for-spatial-data-in-asp-net-core-odata-8/)

The article contains an example ``FilterBinder``, that implements the OData ``geo.distance`` function:

```csharp
// ...

namespace WideWorldImporters.Api.Infrastructure.Spatial.Binder
{
    public class GeoDistanceFilterBinder : FilterBinder
    {
        internal const string GeoDistanceFunctionName = "geo.distance";

        private static readonly MethodInfo distanceMethodDb = typeof(NetTopologySuite.Geometries.Geometry).GetMethod("Distance")!;

        public override Expression BindSingleValueFunctionCallNode(SingleValueFunctionCallNode node, QueryBinderContext context)
        {
            switch (node.Name)
            {
                case GeoDistanceFunctionName:
                    return BindGeoDistance(node, context);
                default:
                    return base.BindSingleValueFunctionCallNode(node, context);
            }
        }

        public Expression BindGeoDistance(SingleValueFunctionCallNode node, QueryBinderContext context)
        {
            var bindGeoDistanceExpression = InternalBindGeoDistance(node, context);

            if (bindGeoDistanceExpression == null)
            {
                throw new InvalidOperationException($"FilterBinder failed to bind FunctionName {GeoDistanceFunctionName}");
            }

            return bindGeoDistanceExpression;
        }

        public Expression? InternalBindGeoDistance(SingleValueFunctionCallNode node, QueryBinderContext context)
        {
            Expression[] arguments = BindArguments(node.Parameters, context);

            string? propertyName = null;

            foreach (var queryNode in node.Parameters)
            {
                if (queryNode != null && queryNode is SingleValuePropertyAccessNode)
                {
                    SingleValuePropertyAccessNode svpan = (SingleValuePropertyAccessNode)queryNode;

                    propertyName = svpan.Property.Name;
                }
            }

            Expression? expression = null;

            if (propertyName != null)
            {
                GetPointExpressions(arguments, propertyName, out MemberExpression? memberExpression, out ConstantExpression? constantExpression);

                if (memberExpression != null && constantExpression != null)
                {
                    expression = Expression.Call(memberExpression, distanceMethodDb, constantExpression);
                }

            }

            return expression;
        }

        private static void GetPointExpressions(Expression[] expressions, string propertyName, out MemberExpression? memberExpression, out ConstantExpression? constantExpression)
        {
            memberExpression = null;
            constantExpression = null;

            foreach (Expression expression in expressions)
            {
                var memberExpr = expression as MemberExpression;

                if (memberExpr == null)
                {
                    continue;
                }

                var constantExpr = memberExpr!.Expression as ConstantExpression;

                if (constantExpr != null)
                {
                    GeographyPoint? point = GetGeographyPointFromConstantExpression(constantExpr);

                    if (point != null)
                    {
                        constantExpression = Expression.Constant(CreatePoint(point.Latitude, point.Longitude));
                    }
                }
                else
                {
                    if (memberExpr.Expression != null)
                    {
                        memberExpression = Expression.Property(memberExpr.Expression, propertyName);
                    }
                }
            }
        }

        private static GeographyPoint? GetGeographyPointFromConstantExpression(ConstantExpression expression)
        {
            GeographyPoint? point = default;

            if (expression != null)
            {
                PropertyInfo? constantExpressionValuePropertyInfo = expression.Type.GetProperty("Property");

                if (constantExpressionValuePropertyInfo != null)
                {
                    point = constantExpressionValuePropertyInfo.GetValue(expression.Value) as GeographyPoint;
                }
            }

            return point;
        }

        private static Point CreatePoint(double latitude, double longitude)
        {
            // 4326 is most common coordinate system used by GPS/Maps
            var geometryFactory = NtsGeometryServices.Instance.CreateGeometryFactory(srid: 4326);

            // see https://docs.microsoft.com/en-us/ef/core/modeling/spatial
            // Longitude and Latitude
            var newLocation = geometryFactory.CreatePoint(new Coordinate(longitude, latitude));

            return newLocation;
        }
    }
}
```

In the ``Startup#ConfigureServices`` we need to add the ``GeoDistanceFilterBinder`` like this: 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace WideWorldImporters.Api
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
            
            // Register ASP.NET Core Mvc:
            services
                // Register Web API Routes:
                .AddControllers()
                // Customize the Json Output, so we can serialize and deserialize the data:
                .AddJsonOptions(options =>
                {
                    // Ignore objects when cycles have been detected in deserialization:
                    options.JsonSerializerOptions.ReferenceHandler = System.Text.Json.Serialization.ReferenceHandler.IgnoreCycles;
                })
                // Register OData Routes:
                .AddOData((opt, services) =>
                {
                    var edmService = services.GetRequiredService<IEdmService>();

                    opt.AddRouteComponents("odata", edmService.GetEdmModel(), svcs =>
                    {
                              svcs.AddSingleton<IFilterBinder, GeoDistanceFilterBinder>();
                    })
                    .EnableQueryFeatures().Select().Expand().OrderBy().Filter().Count(); 
                });

            
        }
        
        // ...
    }
}
```

Job done, and I think this section speaks for the extensibility of the ASP.NET Core OData API design. 👏 

It's a great effort by the (small) OData team. When I am grown up, I want to become such a good API designer, too. 

### Generating the OpenAPI Document ###

Now what's left for our Backend is how to generate the OpenAPI 3.0 document from the EDMX model. It would be error-prone and idiotic 
to write the Frontend model by hand, because absolutely everything that's needed is already described inside the EDMX model. 

Actually there is a package called ``Microsoft.OpenApi.OData.Reader``, that converts from EDMX to OpenAPI 3.0.  It's a million times better, 
than anything I could come up with (lacking knowledge of both EDMX and OpenAPI 3.0) , so I start by simply adding the 
``Microsoft.OpenApi.OData.Reader`` package:

```
dotnet add package Microsoft.OpenApi.OData.Reader
```

In the ``EntitiesController`` Template we can now define the Swagger Endpoint, that returns the OpenAPI Document:

```csharp
// usings ...

namespace ODataSample.Backend.Controllers
{
    public partial class EntitiesController : ODataController
    {
        private readonly WideWorldImportersContext _context;

        public EntitiesController(WideWorldImportersContext context)
        {
            _context = context;
        }

        #region Swagger Endpoint
        
        [HttpGet("odata/$swagger")]
        public IActionResult GetSwaggerDocument([FromServices] IEdmService edmService)
        {
            var edmModel = edmService.GetEdmModel();

            // Convert to OpenApi:
            var openApiSettings = new OpenApiConvertSettings
            {
                ServiceRoot = new("http://localhost:5000"),
                PathPrefix = "odata",
                EnableKeyAsSegment = true,
            };

            var openApiDocument = edmModel.ConvertToOpenApi(openApiSettings);
            var openApiDocumentAsJson = openApiDocument.SerializeAsJson(OpenApiSpecVersion.OpenApi3_0);

            return Content(openApiDocumentAsJson, "application/json");
        }

        #endregion Swagger Endpoint
        
    }
}
```

In the ``Startup`` class we can configure Swagger like this:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

//...

namespace WideWorldImporters.Api
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
            
            // Swagger:
            services.AddSwaggerGen();

            // ...            
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
                app.UseSwagger();
                app.UseSwaggerUI(options =>
                {
                    options.SwaggerEndpoint("/odata/$swagger", "OData Swagger API");
                });
            }
            else
            {
                app.UseExceptionHandler("/Error");
            }
            
            // ...
        }
    }
}
```

Navigating to ``http://localhost:5000/swagger/index.html`` now shows the API Documentation:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/08_Swagger_UI.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/08_Swagger_UI.jpg">
    </a>
</div>

It renders without errors, so I assume it is a valid OpenAPI 3.0 document.

### Generating the TypeScript model ###

Generating the TypeScript model for the Frontend is now easy.

I'll download *NSwagStudio* from:

* [https://github.com/RicoSuter/NSwag/wiki/NSwagStudio](https://github.com/RicoSuter/NSwag/wiki/NSwagStudio)

On the starting page I set the path to the OpenAPI Document (``http://localhost:5000/odata/$swagger``) and configure it like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/09_NSwagStudio_TypeScript.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/09_NSwagStudio_TypeScript.jpg">
    </a>
</div>

And then we can see how it generates all these beautiful TypeScript classes:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/10_NSwagStudio_TypeScript_Results.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/10_NSwagStudio_TypeScript_Results.jpg">
    </a>
</div>

I'll just copy and paste these to the Frontend. 

And that's it for the Backend. I think we are done.

## Building the Frontend ###

[Remy Porter]: https://thedailywtf.com/
[Remy's Law of Requirements Gathering]: https://twitter.com/RemyPorter/status/752913168624746497
 
[Remy Porter] has once stated the so called [Remy's Law of Requirements Gathering], which goes like this ...

> Remy's Law of Requirements Gathering: no matter what the actual requirements, what your users really want is for you to implement Excel.

So what do I want in a Frontend project? A Datagrid, that allows me to sort, filter and paginate data!



### The Page Structure ###

The application should be a *desktop-first* application. We want a side menu, that allows us to have a menu in a classic 
tree structure. To allow fast access of important data, you want to have a header menu, that contains a few links only. And 
finally you want a Drop Down in the Header for things like Settings, Profile or Signing Out of the application. 

So let's define what a Menu item looks like in ``models/menu-items.ts``:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { AppIcons } from "./icons";

// A Menu Item:
export interface MenuItem {
    
    /**
     * A unique Id.
     */
    id: string;

    /**
     * Is the Menu Item active?
     */
    active?: boolean;

    /**
     * An Icon, that needs to be part of the ``AppIcons`` enum, 
     * so we can guarantee it's available.
     */
    icon?: AppIcons;

    /**
     * The Name.
     */
    name: string;

    /**
     * The description.
     */
    description: string;

    /**
     * Accessibility.
     */
    ariaLabel: string;

    /**
     * The Router URL.
     */
    url?: string;

    /**
     * The Children.
     */
    children?: MenuItem[];
}
```

We then define the Application entry point, the ``AppComponent``. 

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { DropdownItem } from './models/dropdown-item';
import { MenuItem } from './models/menu-item';
import { MenuService } from './services/menu.service';
import { TranslationService } from './services/translation.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {

  sidenavMenu$!: Observable<MenuItem[]>;
  headerMenu$!: Observable<MenuItem[]>;
  dropdownMenu$!: Observable<MenuItem[]>;

  constructor(public menuItemService: MenuService, public translations: TranslationService) {

  }

  ngOnInit(): void {
    this.sidenavMenu$ = this.menuItemService.sidenav();
    this.headerMenu$ = this.menuItemService.header();
    this.dropdownMenu$ = this.menuItemService.dropdown();
  }

  getChildren(menuItem: MenuItem): MenuItem[] | undefined {
    return menuItem.children;
  }
}
```

And in the template we are defining the website layout, with a header and side navigation. We are using the 
``MenuService`` to generate the menu items and the ``TranslationService`` to translate the labels. All content 
will go into the ``<router-outlet>``.

```html
<div class="main-container">
    <header class="header header-6">
        <div class="branding">
          <cds-icon shape="world" size="md"></cds-icon>
            <a href="javascript://" class="nav-link">
              <span class="title">{{translations.keys.header.title}}</span>
            </a>
          </div>
          <div class="header-nav">
              <ng-container *ngIf="headerMenu$ | async as headerMenuItems">
                <a *ngFor="let headerMenuItem of headerMenuItems" class="nav-link nav-text" [routerLink]="headerMenuItem.url">{{headerMenuItem.name}}</a>
              </ng-container>
          </div>
          <div class="header-actions">
            <clr-dropdown [clrCloseMenuOnItemClick]="false">
                <button clrDropdownTrigger class="me-1" aria-label="Dropdown">
                    <cds-icon shape="cog" class="me-1" size="md"></cds-icon>         
                    <cds-icon shape="angle"  direction="down"></cds-icon>
                </button>
                <clr-dropdown-menu *clrIfOpen clrPosition="bottom-right" >
                  <label class="dropdown-header" aria-hidden="true">{{translations.keys.dropdown.title}}</label>
                  <ng-container *ngIf="dropdownMenu$ | async as dropdownMenu">
                    <div *ngFor="let dropdownMenuItem of dropdownMenu" [attr.aria-label]="dropdownMenuItem.ariaLabel" clrDropdownItem>{{dropdownMenuItem.name}}</div>
                    </ng-container>
                </clr-dropdown-menu>
              </clr-dropdown>
          </div>
    </header>
    <div class="content-container">
        <nav class="sidenav m-2">
            <section *ngIf="sidenavMenu$ | async as sidenavMenuItems" class="sidenav-content">
              <clr-tree>
                <clr-tree-node [clrExpanded]="true" *clrRecursiveFor="let sidenavMenuItem of sidenavMenuItems;getChildren: getChildren">
                  <a class="clr-treenode-link" [routerLink]="sidenavMenuItem.url" routerLinkActive="active" >{{sidenavMenuItem.name}}</a>
                </clr-tree-node>
              </clr-tree>

            </section>
        </nav>
        <div class="content-area">
            <router-outlet></router-outlet>
        </div>
    </div>
</div>
```

### Querying the OData Web service ###

We start the OData integration by defining what an OData Response looks like and how it is constructed from a ``HttpResponse``. We 
will create a file ``models/odata-response.ts`` with the following content:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpResponse } from "@angular/common/http";

/**
 * Base class for all OData Responses.
 */
export abstract class ODataResponse {

    /**
     * The HTTP Status Code, such as ``200`` (OK) or ``404`` (Not Found).
     */
    public readonly status: number;

    /**
     * The Response Headers.
     */
    public readonly headers: Array<[string, string | null]>;

    /**
     * The ``Map<string, any>``, that holds the OData Metadata.
     */
    public readonly metadata: Map<string, any>;

    /**
     * Initialized common data for all ``ODataResponse`` implementations, such as 
     * status, headers and metadata.
     * 
     * @param response - Response returned by the Webservice
     */
    constructor(response: HttpResponse<any>) {
        this.status = response.status;
        this.headers = response.headers.keys().map(k => [k, response.headers.get(k)])
        this.metadata = this.getMetadata(response.body);
    }

    /**
     * Builds up the OData Metadata, which are basically all keys prefixed with ``@odata``.
     * 
     * @param data - The untyped response body
     * @returns A map of Metadata
     */
    private getMetadata(data: any): Map<string, any> {
        const metadata = new Map<string, any>();
        Object.keys(data)
            .filter((key) => key.startsWith("@odata"))
            .forEach((key) => metadata.set(key.replace("@odata.", ""), data[key]));
        return metadata;
    }
};

/**
 * An OData response containing a single entity, such as a lookup by ID.
 */
export class ODataEntityResponse<T> extends ODataResponse {

    /**
     * An entity of type ``T`` or ``null``, if the response didn't return data.
     */
    public readonly entity: T | null;

    /**
     * Constructs a new ``ODataEntityResponse`` by parsing the response body.
     * 
     * @param response - The HTTP Response.
     */
    constructor(response: HttpResponse<any>) {
        super(response);

        this.entity = this.getEntity(response.body);
    }

    /**
     * Returns the entity of type ``T`` or ``null``.
     * 
     * @param data - The untyped response body
     * @returns Entity of type ``T``
     */
    private getEntity(data: any): T{

        let entity = {} as T;
        
        Object.keys(data)
            .filter((key) => !key.startsWith("@odata"))
            .forEach((key) => entity[key as keyof T] = data[key]);

        return entity;
    }
}

/**
 * Returns an entities array of type ``T``.
 */
export class ODataEntitiesResponse<T> extends ODataResponse {

    public readonly entities: T[];

    /**
     * Constructs a new ``ODataEntityResponse`` by parsing the response body.
     * 
     * @param response - The HTTP Response.
     */
     constructor(response: HttpResponse<any>) {
        super(response);

        this.entities = this.getEntities(response.body);
    }

    /**
     * Returns an array entities of type ``T`` returned by the OData-enabled endpoint.
     * 
     * @param data - The untyped response body
     * @returns Array of type ``T`` elements
     */
    private  getEntities(data: any): T[] {
        const keys = Object.keys(data).filter((key) => !key.startsWith("@odata"));
        if (keys.length === 1 && keys[0] === "value") {
            return (data.value as T[]);
        }
        return [];
    }
}
```

Now that we know the shape of our response, we can define a ``ODataService`` to query the API for an array of entities or a single entity:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { map, Observable } from "rxjs";
import { ODataEntitiesResponse, ODataEntityResponse } from "../models/odata-response";

/**
 * The ``ODataService`` provides functionality to query an OData-enabled 
 * endpoint and parse the HTTP response to a type-safe entity and its 
 * metadata.
 */
@Injectable({
    providedIn: `root`
})
export class ODataService {

    /**
     * Constructs an ``ODataService``.
     * 
     * @param httpClient - The ``HttpClient`` to be used for queries.
     */
    constructor(private httpClient: HttpClient) {
    }

    /**
     * Queries a OData-enabled enpoint for a single entity of type ``T``. The 
     * response also contains all metadata of the response data.
     *
     * @typeParam T - Type of the entity
     * @param url - URL for an OData-enabled enpoint
     * @returns Response containing metadata and entity
     */
    getEntity<T>(url: string): Observable<ODataEntityResponse<T>> {
        return this.httpClient
            .get<any>(url, { observe: 'response' } )
            .pipe(map(response => new ODataEntityResponse<T>(response)));
    }

    /**
     * Queries a OData-enabled enpoint for a entities of type ``T``. The response also 
     * contains all metadata of the response data.
     *
     * @typeParam T - Type of the entity
     * @param url - URL for an OData-enabled enpoint
     * @returns Response containing metadata and entities
     */
     getEntities<T>(url: string): Observable<ODataEntitiesResponse<T>> {
        return this.httpClient
            .get<any>(url, { observe: 'response' } )
            .pipe(map(response => new ODataEntitiesResponse<T>(response)));
    }
}
```

And that's it for the OData queries. There is no fancy builder to abstract away the ``$expand`` and ``$select`` query parameters. Writing 
them by hand for your use cases makes everything much easier, implementation-wise... a little bit of code duplication is better than an 
expensive abstraction!

### Building a Filter Model ###

We need to send a ``$filter`` parameter to the OData service, to filter entities. So we start by creating a small Filter API in a file 
``models/filters.ts``. The idea is, that you have Filters of various types (``Numeric``, ``String``, ``Date``, ``Boolean``) and Filter 
operators (``StartsWith``, ``EndsWith``, ...). 

A Datagrid column can then have a ``ColumnFilter`` applied, which requires you to return a ``ODataFilter`` representation of itself, such 
as an ``ODataStringFilter``, ``ODataNumericFilter``, ``ODataBooleanFilter``, ... From this array of ``ODataFilter`` statements, we can 
construct the ``$filter`` string.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Temporal } from "@js-temporal/polyfill";

// Each Filter has a Type:
export enum FilterType {
    NumericFilter = "numericFilter",
    StringFilter = "stringFilter",
    DateFilter = "dateFilter",
    BooleanFilter = "booleanFilter",
};

// All Filters share a common set of FilterOperators, such as "Greater Than"...
export enum FilterOperator {
    None = "none",
    Before = "before",
    After = "after",
    IsEqualTo = "isEqualTo",
    IsNotEqualTo = "isNotEqualTo",
    Contains = "contains",
    NotContains = "notContains",
    StartsWith = "startsWith",
    EndsWith = "endsWith",
    IsNull = "isNull",
    IsNotNull = "isNotNull",
    IsEmpty = "isEmpty",
    IsNotEmpty = "isNotEmpty",
    IsGreaterThanOrEqualTo = "isGreaterThanOrEqualTo",
    IsGreaterThan = "isGreaterThan",
    IsLessThanOrEqualTo = "isLessThanOrEqualTo",
    IsLessThan = "isLessThan",
    BetweenInclusive = "betweenInclusive",
    BetweenExclusive = "betweenExclusive",
    Yes = "yes",
    No = "no",
    All = "all"
};

// We need a way to return a Filter for each column:
export interface ColumnFilter {

    // Field.
    field: string;

    // FilterOperator.
    filterOperator: FilterOperator;

    // Applies a Filter
    applyFilter(): void;

    // Resets a Filter
    resetFilter(): void;

    // Returns a Filter
    toODataFilter(): ODataFilter;
}

// Every OData Filter is applied to a specific field:
export interface ODataFilter {

    // Field to Filter.
    field: string;

    // Operator.
    operator: FilterOperator;

    // Serializes the OData Filter.
    toODataString(): string | null;
};

// An OData Filter on Strings:
export class ODataStringFilter implements ODataFilter {

    field: string;
    operator: FilterOperator;
    value: string | null;

    constructor(field: string, operator: FilterOperator, value: string | null) {
        this.field = field;
        this.operator = operator;
        this.value = value;
    }

    toODataString(): string | null {

        if (this.operator == FilterOperator.None) {
            return null;
        }
   
        switch (this.operator) {
            case FilterOperator.IsNull:
                return `${this.field} eq null`;
            case FilterOperator.IsNotNull:
                return `${this.field} ne null`;
            case FilterOperator.IsEqualTo:
                return `${this.field}  eq '${this.value}'`;
            case FilterOperator.IsNotEqualTo:
                return `${this.field} neq '${this.value}'`;
            case FilterOperator.IsEmpty:
                return `(${this.field} eq null) or (${this.field} eq '')`
            case FilterOperator.IsNotEmpty:
                return `(${this.field} ne null) and (${this.field} ne '')`
            case FilterOperator.Contains:
                return `contains(${this.field}, '${this.value}')`;
            case FilterOperator.NotContains:
                return `indexof(${this.field}, '${this.value}') eq -1`;
            case FilterOperator.StartsWith:
                return `startswith(${this.field}, '${this.value}')`;
            case FilterOperator.EndsWith:
                return `endswith(${this.field}, '${this.value}')`;
            default:
                throw new Error(`${this.operator} is not supported`);
        }
    }
}

// An OData Filter on Dates and Date Ranges:
export class ODataDateFilter implements ODataFilter {

    readonly field: string;
    readonly operator: FilterOperator;
    readonly startDate: Temporal.ZonedDateTime | null;
    readonly endDate: Temporal.ZonedDateTime | null;

    constructor(field: string, operator: FilterOperator, startDate: Temporal.ZonedDateTime | null, endDate: Temporal.ZonedDateTime | null) {
        this.field = field;
        this.operator = operator;
        this.startDate = startDate;
        this.endDate = endDate;
    }

    toODataString(): string | null {

        if (this.operator == FilterOperator.None) {
            return null;
        }

        const startDate = this.toODataDateTime(this.startDate);
        const endDate =  this.toODataDateTime(this.endDate);

        switch (this.operator) {
            case FilterOperator.IsNull:
                return `${this.field} eq null`;
            case FilterOperator.IsNotNull:
                return `${this.field} ne null`;
            case FilterOperator.IsEqualTo:
                return `${this.field}  eq ${startDate}`;
            case FilterOperator.IsNotEqualTo:
                return `${this.field}  neq ${startDate}`;
            case FilterOperator.After:
            case FilterOperator.IsGreaterThan:
                return `${this.field} gt ${startDate}`;
            case FilterOperator.IsGreaterThanOrEqualTo:
                return `${this.field} ge ${startDate}`;
            case FilterOperator.Before:
            case FilterOperator.IsLessThan:
                return `${this.field} lt ${startDate}`;
            case FilterOperator.IsLessThanOrEqualTo:
                return `${this.field} le ${startDate}`;
            case FilterOperator.BetweenExclusive:
                return `(${this.field} gt ${startDate}) and (${this.field} lt ${endDate})`;
            case FilterOperator.BetweenInclusive:
                return `(${this.field} ge ${startDate}) and (${this.field} le ${endDate})`;
            default:
                throw new Error(`${this.operator} is not supported`);
        }
    }

    toODataDateTime(zonedDateTime: Temporal.ZonedDateTime | null): string | null {
        if(zonedDateTime == null) {
            return null;
        }

        const utcZonedDateTimeString = zonedDateTime
            .withTimeZone('UTC')
            .toString({ smallestUnit: 'seconds', timeZoneName: 'never', offset: 'never'});
        
        return `${utcZonedDateTimeString}Z`;
    }
};

// An OData Filter on Boolean Values:
export class ODataBooleanFilter implements ODataFilter {

    readonly field: string;
    readonly operator: FilterOperator;

    constructor(field: string, operator: FilterOperator) {
        this.field = field;
        this.operator = operator;
    }

    toODataString(): string | null {
        
        if (this.operator == FilterOperator.None) {
            return null;
        }

        switch (this.operator) {
            case FilterOperator.IsNull:
                return `${this.field} eq null`;
            case FilterOperator.IsNotNull:
                return `${this.field} ne null`;
            case FilterOperator.Yes:
                return `${this.field} eq true`;
            case FilterOperator.No:
                return `${this.field} eq false`;
            default:
                return null;
        }
    }
}

// A Filter on Numeric Values:
export class ODataNumericFilter implements ODataFilter {

    readonly field: string;
    readonly operator: FilterOperator;
    readonly low: number | null;
    readonly high: number | null;

    constructor(field: string, operator: FilterOperator, low: number | null, high: number | null) {
        this.field = field;
        this.operator = operator;
        this.low = low;
        this.high = high;
    }

    toODataString(): string | null {

        if (this.operator == FilterOperator.None) {
            return null;
        }

        switch (this.operator) {
            case FilterOperator.IsNull:
                return `${this.field} eq null`;
            case FilterOperator.IsNotNull:
                return `${this.field} ne null`;
            case FilterOperator.IsGreaterThan:
                return `${this.field} gt ${this.low}`; 
            case FilterOperator.IsGreaterThanOrEqualTo:
                return `${this.field} ge ${this.low}`;
            case FilterOperator.IsLessThan:
                return `${this.field} lt ${this.low}`;
            case FilterOperator.IsLessThan:
                return `${this.field} le ${this.low}`;
            case FilterOperator.BetweenExclusive:
                return `(${this.field} gt ${this.low}) and (${this.field} lt ${this.high})`;
            case FilterOperator.BetweenInclusive:
                return `(${this.field} ge ${this.low}) and (${this.field} le ${this.high})`;
            default:
                return null;
        }
    }
}
```

### Integrating it into Clarity ###

We can then implement the Components to integrate into the Clarity Datagrid, such as a ``StringFilterComponent``. To simplify 
implementation, we are only implementing it for Server-side Filtering. If you want to implement Client-side filtering, you need 
to implement the ``ClrDatagridFilterInterface#accepts(item: any)`` method to filter elements.

Here is a Filter, that can be used as a starting point. 

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { AfterViewInit, Component, Input } from "@angular/core";
import { ClrDatagridFilter, ClrDatagridFilterInterface, ClrPopoverEventsService } from "@clr/angular";
import { Subject } from "rxjs";
import { ODataFilter, FilterOperator, FilterType, ColumnFilter, ODataStringFilter } from "src/app/models/filter";
import { TranslationService } from "src/app/services/translation.service";

/**
 * A Filter for search string values.
 */
@Component({
    selector: 'app-string-filter',
    template: `
        <form clrForm clrLayout="horizontal"  clrLabelSize="4">
        <clr-select-container>
                <label>{{translations.keys.filters.numericFilter.labelOperator}}</label>
                <select clrSelect name="operators" [(ngModel)]="filterOperator">
                    <option *ngFor="let operator of filterOperators" [value]="operator">{{translations.keys.filterOperators[operator]}}</option>
                </select>
            </clr-select-container>
            <clr-input-container>
                <label>{{translations.keys.filters.numericFilter.labelValue}}</label>
                <input clrInput [placeholder]="translations.keys.filters.stringFilter.placeholder" name="input" [(ngModel)]="search" 
                    [disabled]="filterOperator === 'none' || filterOperator === 'isNull' || filterOperator === 'isNotNull' || filterOperator === 'isEmpty' || filterOperator === 'isNotEmpty'" />
            </clr-input-container>
            <div class="clr-row filter-actions">
                <div class="clr-col">
                    <button class="btn btn-primary btn-block" (click)="applyFilter()">{{translations.keys.filters.applyFilter}}</button>
                </div>
                <div class="clr-col">
                    <button class="btn btn-block" (click)="resetFilter()">{{translations.keys.filters.resetFilter}}</button>
                </div>
            </div>
        </form>
    `,
    styles: ['.filter-actions { margin-top: 1.2rem; }']
})
export class StringFilterComponent implements ClrDatagridFilterInterface<any>, ColumnFilter, AfterViewInit  {

    /**
     * Filter operators valid for the component.
     */
    readonly filterOperators: FilterOperator[] = [
        FilterOperator.None,
        FilterOperator.IsNull, 
        FilterOperator.IsNotNull, 
        FilterOperator.IsEmpty, 
        FilterOperator.IsNotEmpty, 
        FilterOperator.IsEqualTo, 
        FilterOperator.IsNotEqualTo, 
        FilterOperator.Contains, 
        FilterOperator.NotContains, 
        FilterOperator.StartsWith, 
        FilterOperator.EndsWith,
    ];

    /**
     * The name of the field, which has to match the model.
     */
    @Input()
    field!: string;
 
     /**
      * The Filter operator selected by the user.
      */
    @Input()
    filterOperator: FilterOperator = FilterOperator.None;
 

    /**
     * Search Value entered by the user.
     */
    @Input()
    search: string | null = null;

    /**
     * Required by the ``ClrDatagridFilterInterface`` so the Datagrid knows something has changed.
     */
    changes = new Subject<any>();

    /**
     * Creates a new ``StringFilterComponent``.
     * 
     * @param filterContainer - The Clarity Datagrid ``ClrDatagridFilter`` filter container to register to
     * @param translations - Translations to be used in the component.
     * @param clrPopoverEventsService - The popover service to control the behavior of the popout.
     */
    constructor(private filterContainer: ClrDatagridFilter, public translations: TranslationService, private clrPopoverEventsService: ClrPopoverEventsService) {
        filterContainer.setFilter(this);
    }

    /**
     * Applies the Filter.
     */
    applyFilter(): void {
        this.changes.next(null);
    }
    
    /**
     * Resets the Filter.
     */
    resetFilter(): void {
        this.filterOperator = FilterOperator.None;
        this.search = null;

        this.changes.next(null);
    }

    /**
     * Returns ``true`` if this Filter is enabled.
     * 
     * @returns ``true`` if the Filter is valid.
     */
    isActive(): boolean {
        return this.filterOperator !== FilterOperator.None;
    }

    /**
     * This method needs to be implemented for Client-side Filtering. We will do all 
     * filtering on Server-side and just pipe everything through here.
     * 
     * @param item - Item to Filter for
     * @returns At the moment this method only returns ``true``
     */
    accepts(item: any): boolean {
        return true;
    }
    
    /**
     * Turns this component into an ``ODataFilter``.
     * 
     * @returns The OData Filter for the component.
     */
    toODataFilter(): ODataFilter {
        return new ODataStringFilter(this.field, this.filterOperator, this.search);
    }

    /**
     * After the Component has been initialized we need to tell its ``ClrPopoverEventsService`` to 
     * not close, when the User has accidentally clicked outside the filter. And if the Filter has been 
     * initialized, we tell the Datagrid to refresh the filters.
     */
     ngAfterViewInit() {
		this.clrPopoverEventsService.outsideClickClose = false;

        if(this.filterOperator != FilterOperator.None) {
            this.applyFilter();
        }
	}
}
```

These filters can be used to build an OData string for the current Datagrid's state. The class ``ODataUtils#asODataString`` takes 
the Datagrid state to set the ``$filter``, ``$sort``, ``$top``, ``$skip`` and ``$count`` query parameters. Optionally the ``$select`` 
and ``$expand`` parameters can be added.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpParams } from "@angular/common/http";
import { ClrDatagridStateInterface } from "@clr/angular";
import { ColumnFilter, ODataFilter } from "../models/filter";
import { HttpQueryParamType } from "../types/type-utils";
import { StringUtils } from "./string-utils";

/**
 * Utilities for working with OData Data Sources.
  */
export class ODataUtils {

    /**
     * Serializes a ``ClrDatagridStateInterface`` into an OData query with filters,
     * pagination and sort parameters. The result will also include a $count to get 
     * the total result set size.
     *
     * @param endpoint - OData-enabled endpoint we are querying.
     * @param state - The State of the DataGrid.
     * @param params - Addition $select and $expand parameters.
     * @returns OData query with Sorting, Filters and Pagination. 
     */
     public static asODataString(endpoint: string, state: ClrDatagridStateInterface, params: Partial<{ $select?: string, $expand?: string }>): string {

        const httpQueryParameters: HttpQueryParamType = {
            ...this.getSelectParameter(params.$select),
            ...this.getExpandParameter(params.$expand),
            ...this.toODataFilterStatements(state),
            ...this.getPaginationParameters(state),
            ...this.getSortParameters(state),
            ...{ "$count": true }
        };

        const httpParameters: HttpParams = new HttpParams().appendAll(httpQueryParameters);

        if (StringUtils.isNullOrWhitespace(httpParameters.toString())) {
            return endpoint;
        }

        return `${endpoint}?${httpParameters.toString()}`;
    }

    /**
     * Returns the $select part of the OData query.
     *
     * @param select - The raw select string.
     * @returns The OData $select statement.
     */
    private static getSelectParameter(select?: string): HttpQueryParamType {

        if(!select) {
            return {};
        }

        return { "$select": select };
    }

     /**
     * Returns the $select part of the OData query.
     *
     * @param select - The raw select string.
     * @returns The OData $select statement.
     */
         private static getExpandParameter(expand?: string): HttpQueryParamType {
            if(!expand) {
                return {};
            }
    
            return { "$expand": expand };
        }

    /**
     * Serializes the filters of a ``ClrDatagridStateInterface`` into a ``HttpQueryParamType``, containing 
     * the ``$filter`` statements of an OData query.
     *
     * @param clrDataGridState - The state of the DataGrid.
     * @returns The OData $filter parameters.
     */
    private static toODataFilterStatements(clrDataGridState: ClrDatagridStateInterface): HttpQueryParamType {

        // Get all OData Filters from the Grid:
        const filters: ODataFilter[] = ODataUtils.castToODataFilters(clrDataGridState);

        // Serialize the to OData strings:
        const serializedFilters = ODataUtils.serializeAllFilters(filters);

        if (!serializedFilters) {
            return {};
        }

        return {
            "$filter": serializedFilters
        };
    }

    /**
     * Gets the ``ODataFilter[]`` from the ``ClrDatagridStateInterface#filter`` property.
     *
     * @param clrDataGridState - An array of ``ODataFilter``.
     * @returns The OData $filter value.
     */
    private static castToODataFilters(clrDataGridState: ClrDatagridStateInterface): ODataFilter[] {

        if (!clrDataGridState.filters) {
            return [];
        }

        return clrDataGridState.filters
            .filter(filter => (filter as ColumnFilter).toODataFilter) // Typescript has no "instanceof", so use some duck typing...
            .map(filterProvider => filterProvider.toODataFilter());
    }

    /**
     * Serializes all $filter statement generated by a given array of ``ODataFilter``.
     *
     * @param filters - An array of ``ODataFilter``.
     * @returns The OData $filter value.
     */
    private static serializeAllFilters(filters: ODataFilter[]): string {
        // Serialize the Filters:
        return filters
            // Format as OData string:
            .map((filter) => filter.toODataString())
            // There may be empty OData-strings:
            .filter(filter => !StringUtils.isNullOrWhitespace(filter))
            // Wrap it in parentheses, so concatenating filters doesn't lead to problems:
            .map((filter) => `(${filter})`)
            // Concat all Filters with AND:
            .join(' and ');
    }

    /**
     * Returns the optional OData $sort parameter.
     *
     * @param clrDataGridState - The state of the Data Grid.
     * @returns The OData $orderby statement.
     */
    private static getSortParameters(clrDataGridFilter: ClrDatagridStateInterface): HttpQueryParamType {

        if (!clrDataGridFilter.sort) {
            return {};
        }

        const by: string = clrDataGridFilter.sort.by.toString();

        if (StringUtils.isNullOrWhitespace(by)) {
            return {};
        }

        const result: HttpQueryParamType = {};

        if (clrDataGridFilter.sort.reverse) {
            result["$orderby"] = `${by} desc`;
        } else {
            result["$orderby"] = `${by}`;
        }

        return result;
    }

    /**
     * Gets the optional Pagination parameters ``$top`` and ``$skip``.
     *
     * @param clrDataGridState - The state of the Data Grid.
     * @returns The OData ``$top`` and ``$skip`` statements.
     */
    private static getPaginationParameters(clrDataGridFilter: ClrDatagridStateInterface): HttpQueryParamType {

        const page = clrDataGridFilter.page;

        if (!page) {
            return {};
        }

        const result: HttpQueryParamType = {};

        if (page.size) {
            result["$top"] = page.size;
        }

        if (page.current && page.size) {
            result["$skip"] = (page.current - 1) * page.size;
        }

        return result;
    }
}
```

And that's it for the OData infrastructure code!

### Query the OData Endpoint and Display the Data ###

With all the infrastructure code in place, we can finally query the data. 

As an example I will show how to query for cities and also include values of related entities: 

* ``stateProvince``
    * Information about the city's state. 
* ``lastEditedByNavigation`` 
    * Person that was modifying the city.

The Code-behind uses ``ODataUtils`` to build a OData Query string from a Clarity Datagrid state, and 
then use the ``ODataService`` to query for the data. Once the data has been loaded, we will bind it to 
the ``tableData`` instance variable.

```
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Component } from '@angular/core';
import { ClrDatagridStateInterface } from '@clr/angular';
import { ODataEntitiesResponse } from 'src/app/models/odata-response';
import { City, Country } from 'src/app/models/entities';
import { ODataService } from 'src/app/services/odata-service';
import { TranslationService } from 'src/app/services/translation.service';
import { ODataUtils } from 'src/app/utils/odata-utils';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-cities-table',
  templateUrl: 'app-cities-table.component.html',
})
export class CitiesTableComponent {

  loading: boolean = true;
  filterOpen: boolean = false;
  tableData!: ODataEntitiesResponse<City>;

  constructor(public odataService: ODataService, public translations: TranslationService) {

  }

  refresh(state: ClrDatagridStateInterface) {
    
    const query = ODataUtils.asODataString(`${environment.baseUrl}/Cities`, state, { $expand: "stateProvince, lastEditedByNavigation" });

    this.loading = true;

    this.odataService.getEntities<City>(query)
      .subscribe(res => {
        this.tableData = res;
        this.loading = false;
      });
  }
}
```

In the corresponding template

```html
<clr-datagrid  (clrDgRefresh)="refresh($event)" [clrDgLoading]="loading">
    <clr-dg-column [clrDgField]="'cityId'">
        <clr-dg-filter>
            <app-string-filter field="cityId"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.cityId }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'cityName'">
        <clr-dg-filter>
            <app-string-filter field="cityName"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.cityName }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'stateProvince'">
        <clr-dg-filter>
            <app-string-filter field="stateProvince/stateProvinceName"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.stateProvince }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'latestRecordedPopulation'">
        <clr-dg-filter>
            <app-numeric-filter field="latestRecordedPopulation"></app-numeric-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.latestRecordedPopulation }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'lastEditedBy'">
        <clr-dg-filter>
            <app-string-filter field="lastEditedByNavigation/fullName"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.countries.lastEditedBy}}
    </clr-dg-column>
    <!-- Row Binding -->
    <clr-dg-row *ngFor="let city of tableData?.entities">
        <clr-dg-cell>{{city.cityId}}</clr-dg-cell>
        <clr-dg-cell>{{city.cityName}}</clr-dg-cell>
        <clr-dg-cell>{{city.stateProvince?.stateProvinceName}}</clr-dg-cell>
        <clr-dg-cell>{{city.latestRecordedPopulation}}</clr-dg-cell>
        <clr-dg-cell>{{city.lastEditedByNavigation?.fullName}}</clr-dg-cell>
    </clr-dg-row>
    <!-- Footer -->
    <clr-dg-footer>
        <clr-dg-pagination #pagination [clrDgPageSize]="10"
            [clrDgTotalItems]="tableData?.metadata?.get('count')">
            <clr-dg-page-size [clrPageSizeOptions]="[10,20,50,100]">{{ translations.keys.core.datagrid.pagination.items_per_page }}</clr-dg-page-size>
            {{pagination.firstItem + 1}} - {{pagination.lastItem + 1}} {{ translations.keys.core.datagrid.pagination.of }} {{pagination.totalItems}}  {{ translations.keys.core.datagrid.pagination.items }}
        </clr-dg-pagination>
    </clr-dg-footer>
</clr-datagrid>
```

And the result is a beautiful data grid, that allows us to sort, filter and paginate our hearts out:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/11_Cities_Table.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/11_Cities_Table.jpg">
    </a>
</div>

The GitHub repository contains more tables, so you get a feeling on how to work with it.

### Translation for Clarity Controls ###

You may have seen the ``TranslationService`` and wondered how the Clarity Controls are translated? Clarity uses a simple approach, that I like a 
lot, because it's so transparent and not magic. The framework wants you to configure the translations in the ``ClrCommonStringsService`` for every 
language you want to support. 

I will just inject the current Locale using Angular ``LOCAL_ID`` injection token, and then set the ``ClrCommonStrings`` for all locales, that contain 
the required translations. The translations are given in the file ``app/data/clr-common-strings.ts``, it's just some static data that gets imported.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Inject, Injectable, LOCALE_ID } from "@angular/core";
import { ClrCommonStrings, ClrCommonStringsService, commonStringsDefault } from "@clr/angular";
import { germanLocale } from "../data/clr-common-strings";

/**
 * The ``CommonStringService`` is used to initialize the Clarity ``ClrCommonStringsService`` with the 
 * values of a given Locale, which is injected by Angulars Dependency Injection framework as a Injection 
 * Token.
 * 
 * @public
 */
@Injectable({
    providedIn: `root`
})
export class CommonStringsService {

    /**
     * The available Clarity component translations.
     */
    translations: Map<string, ClrCommonStrings> = new Map([
        [ 'en', commonStringsDefault ],
        [ 'de', germanLocale ],
    ]);

    /**
     * Initializes the ``CommonStringsService``.
     * 
     * @param locale - Application locale
     * @param clrCommonStringsService - The ``ClrCommonStringsService`` Clarity uses for translations.
     */
    constructor(@Inject(LOCALE_ID) locale: string, private clrCommonStringsService: ClrCommonStringsService) {
        this.set(locale);
    }

    /**
     * Sets the Locale and updates the wrapped ``ClrCommonStringsService``.
     * 
     * @param locale - Application locale
     */
    public set(locale: string) {
        this.clrCommonStringsService.localize(this.get(locale));    
    }

    /**
     * Gets the ``ClrCommonStrings`` for a given locale.
     * 
     * @param locale - Application Locale
     * @returns The ``ClrCommonStrings`` for a given locale
     */
    private get(locale: string) : ClrCommonStrings {
        return this.translations.has(locale) ? this.translations.get(locale)! : commonStringsDefault;
    }
  }
``` 

### Translations for the Application ###

I want type-safety for the translations. In my opinion there is nothing worse, than operating on strings and suddenly have placeholders popping 
up in the UI... or even worse (embarassing) key names. So I will simply use the Clarity approach and define a class called ``AppCommonStrings``, 
that provides type-safe access to all translations in the application.

That has the following advantadges:

* Locales need to implement the ``AppCommonStrings`` interface: 
    * TypeScript ensures, that you have defined all your keys for all locales.
* Templates using the ``TranslationService`` can access the Translations by property:
    * TypeScript ensures, that you are accessing valid properties and fails on mistyped properties.

The ``TranslationService`` is then initialized just like the ``ClrCommonStringsService`` for all locales to be supported.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Inject, Injectable, LOCALE_ID } from "@angular/core";
import { AppCommonStrings, defaultCommonStrings, germanCommonStrings } from "../data/app-common-strings";

/** */
@Injectable({
    providedIn: 'root',
  })
  export class TranslationService {

    /**
     * Holds the Translations available for the application. This could also 
     * be provided using dependency injection.
     */
    translations: Map<string, AppCommonStrings> = new Map([
        [ 'en', defaultCommonStrings ],
        [ 'de', germanCommonStrings ],
    ]);

    /**
     * Constructs a ``TranslationService`` with a given locale.
     * 
     * @param locale - Application locale
     */
    constructor(@Inject(LOCALE_ID) locale: string) {
        this.set(locale);
    }

    /**
     * Sets the translations for the given locale.
     * 
     * @param locale - Locale to use
     */
    public set(locale: string) {
        var translations = this.get(locale);

        this.localize(translations);
    }

    /**
     * Gets the translations for a given locale.
     * 
     * @param locale 
     * @returns 
     */
    private get(locale: string) : AppCommonStrings {
        return this.translations.has(locale) ? this.translations.get(locale)! : defaultCommonStrings;
    }
    
    private _strings = defaultCommonStrings;
  
    /**
     * Allows you to pass in new overrides for localization
     */
    localize(overrides: Partial<AppCommonStrings>) {
      this._strings = { ...this._strings, ...overrides };
    }
  
    /**
     * Access to all of the keys as strings
     */
    get keys(): Readonly<AppCommonStrings> {
      return this._strings;
    }
  
    /**
     * Parse a string with a set of tokens to replace
     */
    parse(source: string, tokens: { [key: string]: string } = {}) {
      const names = Object.keys(tokens);
      let output = source;
      if (names.length) {
        names.forEach(name => {
          output = output.replace(`{${name}}`, tokens[name]);
        });
      }
      return output;
    }
}
```

### Final Plumbing Steps ###

A little bit of plumbing is necessary to setup the Routes and the Angular Dependency Injection container.

In the ``app-routing.module.ts`` we are defining the routes for the application:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CitiesTableComponent } from './components/tables/cities-table/app-cities-table.component';
import { CountriesTableComponent } from './components/tables/countries-table/app-countries-table.component';
import { CustomersTableComponent } from './components/tables/customer-table/app-customer-table.component';


const routes: Routes = [
  { path: 'tables/cities', component: CitiesTableComponent },
  { path: 'tables/countries', component: CountriesTableComponent },
  { path: 'tables/customers', component: CustomersTableComponent },
  
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
```

And in the ``app.module.ts`` we define the application roots dependency injection container.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { CUSTOM_ELEMENTS_SCHEMA, LOCALE_ID, NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ClarityModule } from '@clr/angular';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { CommonModule, registerLocaleData } from '@angular/common';
import localeDe from '@angular/common/locales/de';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

// CDS Web Components: 
import '@cds/core/icon/register.js';
import '@cds/core/date/register.js';
import '@cds/core/time/register.js';
import '@cds/core/input/register.js';
import '@cds/core/select/register.js';

import { ClarityIcons, cloudIcon, cogIcon, homeIcon, arrowIcon } from '@cds/core/icon';

// Filters:
import { BooleanFilterComponent } from './components/filters/boolean-filter/boolean-filter.component';
import { DateRangeFilterComponent } from './components/filters/date-range-filter/date-range-filter.component';
import { StringFilterComponent } from './components/filters/string-filter/string-filter-component.component';
import { NumericFilterComponent } from './components/filters/numeric-filter/numeric-filter-component.component';

// Components:
import { ZonedDatePickerComponent } from './components/core/zoned-date-picker.component';
import { CountriesTableComponent } from './components/tables/countries-table/app-countries-table.component';
import { CitiesTableComponent } from './components/tables/cities-table/app-cities-table.component';
import { CustomersTableComponent } from './components/tables/customer-table/app-customer-table.component';

// Add Icons used in the Application:
ClarityIcons.addIcons(homeIcon, cogIcon, cloudIcon, arrowIcon);

registerLocaleData(localeDe);

@NgModule({
  declarations: [
    AppComponent,
    // Common
    ZonedDatePickerComponent,
    // Filter
    BooleanFilterComponent,
    DateRangeFilterComponent,
    StringFilterComponent,
    NumericFilterComponent,
    // Tables
    CitiesTableComponent,
    CountriesTableComponent,
    CustomersTableComponent
  ],
  imports: [
    // Angular
    AppRoutingModule,
    BrowserModule,
    BrowserAnimationsModule,
    CommonModule,
    FormsModule,
    HttpClientModule,
    // Clarity    
    ClarityModule,
  ],
  providers: [{ provide: LOCALE_ID, useValue: 'en' }],
  bootstrap: [AppComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule { }
```

And that's it!