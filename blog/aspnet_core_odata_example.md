title: An ASP.NET Core OData Example using the Wide WorldImporters database and Entity Framework Core
date: 2022-08-24 20:03
tags: aspnetcore, csharp, odata
category: csharp
slug: aspnet_core_odata_example
author: Philipp Wagner
summary: This article shows how to build a Frontend and Backend application with Angular, Clarity, ASP.NET Core OData, and Entity Framework Core.

In this article I will show you how to use ASP.NET Core OData and EF Core to quickly build Backends 
and how to use Angular to display, filter and paginate datasets. It's not complicated, but there had 
been quite a few pieces to the puzzle.

This article deals with the Backend with ASP.NET Core OData, the article for the Frontend is available at:

* [https://www.bytefish.de/blog/aspnet_core_odata_frontend.html](https://www.bytefish.de/blog/aspnet_core_odata_frontend.html)

All code can be found at:

* [https://github.com/bytefish/WideWorldImporters](https://github.com/bytefish/WideWorldImporters)

## Table of contents ##

[TOC]

## What we are going to build ##

We will build a Backend and Frontend for the "Wide World Importers" database, which is a Microsoft SQL Server 
sample database for a fictional company:

* [https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is](https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is)

We are building a Backend, that scaffolds the WWI database and exposes the data with Microsoft ASP.NET Core OData 8. We will 
learn how to extend Microsoft ASP.NET Core OData 8 for spatial types, see how to generate the OData endpoints using T4 Text 
Templates and provide OpenAPI 3.0 documents for Frontend code generation goodies.

The Frontend is an Angular application to query the OData endpoints. We are going to use Angular components of the Clarity 
Design system, because Clarity takes a Desktop-first approach and has a very nice Datagrid, that's easy to extend:

* [https://clarity.design/](https://clarity.design/)

The final application will look like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/00_WWI_App.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/00_WWI_App.jpg" alt="The final Angular application, that's going to be built">
    </a>
</div>

So let's go ahead and write an application. 👍

## Wide World Importers Database ##

It's always a very time-consuming task to build interesting datasets for articles. So I had a 
look at the list of Microsoft SQL Server sample databases, because... I am sure a lot of thoughts 
have been put into them:

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/)

What I like about the "Wide World Importers" sample database is, that it has been crafted to work well with 
Scaffolding. It has Stored Procedures, Views, Temporal Tables, Spatial Types... basically a lot of things to 
explore (and traps to fall into):

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers)

### About the Database ###

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

### Starting a SQL Server 2022 using Docker ###

The easiest way to get started is to use Docker and go to the `docker` folder of the GitHub repository. 

If you run 

```powershell
docker compose up
```

A new container will be created with the Wide World Importers OLTP database.

### Importing the Database Backup Manually ###

We are going to work with WideWorldImporters OLTP Database which is described at:

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt)

In the Releases for the Repository you can find a full Backup (``WideWorldImporters-Full.bak`` ):

* [https://github.com/microsoft/sql-server-samples/releases/tag/wide-world-importers-v1.0](https://github.com/microsoft/sql-server-samples/releases/tag/wide-world-importers-v1.0)

From the GitHub Release Page we are downloading the Backup ``WideWorldImporters-Full.bak`` and import it.

We start the SQL Server Management Studio and connect to our SQLEXPRESS instance, right click on Databases and select "Restore Database ...":

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/01_Restore_WWI_Database.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/01_Restore_WWI_Database.jpg" alt="Restoring the WWI database in SQL Server Management Studio">
    </a>
</div>

On the "General" page select "Device" as the Source and select the Backup like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/02_Restore_WWI_Database.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/02_Restore_WWI_Database.jpg" alt="Selecting the Backup Source">
    </a>
</div>

We are now ready to import the database:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/03_Restore_WWI_Database.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/03_Restore_WWI_Database.jpg" alt="Final step for restoring the WWI database">
    </a>
</div>

The default settings will fit. Click "Ok" and wait a moment for the backup to be restored.

And... that's it!

## ASP.NET Core OData Backend ##

### Solution Overview ###

It's a good idea to get an high-level overview of the project first, so you get a basic idea:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/00_Solution_Overview.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/00_Solution_Overview.jpg" alt="High-Level View on the Solution structure">
    </a>
</div>

The Solution consists of two projects:

* ``WideWorldImporters.Api``
    * A ASP.NET Core Web API project to define the OData EDM Model and provide endpoints for all entities.
* ``WideWorldImporters.Database``
    * A Library project, that contains the Scaffolded Model and Database Context for the Wide World Importers database.
    
A deeper drill-down shows what the reasoning behind the folder structure is:

* ``WideWorldImporters.Api``
    *  ``/Controllers``
        * T4 Text Template to generate the ODataController
    * ``/Infrastructure``
        * ``/Spatial``
            * Adds Geometric support to Microsoft ASP.NET Core OData 8.
    * ``/Models``
        * The EDM Model for the Application.
    * ``Startup.cs``
        * Configures the ASP.NET Core request pipeline.
* ``WideWorldImporters.Database``
    * ``/Context`` 
        * ``DbContext`` generated by the Scaffolding.
    * ``/Models``
        * Database Models generated by the Scaffolding.
    * ``Spatial``
        * Partial Classes to allow Spatial OData Queries for the Entity Types.
    * ``WideWorldImportContext.cs``
        * The generated ``DbContext`` for the WWI Database.

### Scaffolding the Database ###

We'll create a separate ``WideWorldImporters.Database`` project first, so we can evolve the Database "independently" of the Api. 

#### Installing the dotnet-ef Command Line Interface ####

In EF Core you are using a ``dotnet-ef`` Command Line Interface for Scaffolding. It needs to be installed first, so switch to the 
Package Manager Console (``View -> Other Windows -> Package Manager Console``) and type:

```
dotnet tool install --global dotnet-ef
```

#### Installing EntityFramework Core dependencies ####

According to the "Entity Framework Core tools reference" documentation we also need to install ``Microsoft.EntityFrameworkCore.Design`` to use the Database-first tooling:

```
dotnet add package Microsoft.EntityFrameworkCore.Design
```

And because the database has some spatial data types, we also add the following package:

```
PM> dotnet add package Microsoft.EntityFrameworkCore.SqlServer.NetTopologySuite
```

#### Scaffold the Database using the dotnet-ef CLI ####


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
        <img src="/static/images/blog/aspnet_core_odata_example/04_Scaffolding_WWI_Files.jpg" alt="The scaffolded Model classes and DbContext in the Database project">
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

### Adding ASP.NET Core OData 8 ###

What's ASP.NET Core OData? It's Microsofts implementation of the OData (Open Data Protocol) specification, which ...

> [...] is an ISO/IEC approved, OASIS standard that defines a set of best practices for building and consuming REST APIs. It enables 
> creation of REST-based services which allow resources identified using Uniform Resource Locators (URLs) and defined in a data model, 
> to be published and edited by Web clients using simple HTTP messages.

So we start by installing the ASP.NET Core OData library into the ``WideWorldImporters.Api`` project:

```
PM> dotnet add package Microsoft.AspNetCore.OData
```

#### Application EDM Data Model ###

We define an ``ApplicationEdmModel`` class to provide the applications ``IEdmModel``, which is used to build the 
EDM Schema by ASP.NET Core OData. We will add all generated models as an ``EntitySet``, so they can be queried:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Edm;
using Microsoft.OData.ModelBuilder;
using Microsoft.Spatial;
using WideWorldImporters.Database.Models;

namespace WideWorldImporters.Api.Models
{
    public static class ApplicationEdmModel
    {
        public static IEdmModel GetEdmModel()
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
            modelBuilder.EntitySet<StockItemStockGroup>("StockItemStockGroups");
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

            // Send as Lower Camel Case Properties, so the JSON looks better:
            modelBuilder.EnableLowerCamelCase();

            return modelBuilder.GetEdmModel();
        }

    }
}
```

#### Adding OData Services to ASP.NET Core ####

In the ``Startup`` we can now use the ``IServiceCollection#AddOData()`` extension to add all OData dependencies 
and configure the OData Routes. We are providing the ``IEdmModel``:

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
                .AddOData((opt) =>
                {
                    opt.AddRouteComponents("odata", ApplicationEdmModel.GetEdmModel())
                        .EnableQueryFeatures().SetMaxTop(250);
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
        <img src="/static/images/blog/aspnet_core_odata_example/05_OData_Edmx_Model.jpg" alt="EDMX Model returned by the $metadata endpoint">
    </a>
</div>

Job done! 👍

#### Creating an OData-enabled Controller ####

The Entity sets are exposed with an ``ODataController`` in ASP.NET Core OData. I want to have a ``Get``, ``GetById``, ``Put``, 
``Patch`` and ``Delete`` endpoint for every Entity set. And I am lazy, so I don't want to write it by hand, that needs to be 
generated. 

We can use T4 Text Templates, easily the most underrated tool in .NET development:

* [https://docs.microsoft.com/en-us/visualstudio/modeling/code-generation-and-t4-text-templates?view=vs-2022](https://docs.microsoft.com/en-us/visualstudio/modeling/code-generation-and-t4-text-templates?view=vs-2022)

In the ``WideWorldImporters.Api`` project we create a new Folder ``Controllers`` and add a new Text Template named ``EntitiesController.tt``:

```
<#@ output extension=".cs"#>
<#@ template language="C#" hostspecific="True" #>
<#
    // We cannot reuse the ApplicationEdmModel, so let's type the EntitySet names by hand:
    var entitySets = new EntitySet[] 
    {
        new EntitySet("BuyingGroups", "BuyingGroup", "buyingGroupsId", "int"),
        // ...
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
        
        // ... GetById, Post, Put, Patch, Delete left out ...

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
using Microsoft.OpenApi.OData;
using Microsoft.OpenApi.Extensions;
using Microsoft.OpenApi;
using WideWorldImporters.Api.Models;
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
        
        [HttpGet("odata/swagger.json")]
        public IActionResult GetSwaggerDocument()
        {
            var edmModel = ApplicationEdmModel.GetEdmModel();

            // Convert to OpenApi:
            var openApiSettings = new OpenApiConvertSettings
            {
                ServiceRoot = new("http://localhost:5000"),
                PathPrefix = "odata",
                EnableKeyAsSegment = true,
            };

            var openApiDocument = edmModel
                .ConvertToOpenApi(openApiSettings)
                .SerializeAsJson(OpenApiSpecVersion.OpenApi3_0);

            return Content(openApiDocument, "application/json");
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

        // ...
        
    }
}
```

### Running OData Queries against the Wide World Importers database ###

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

## Spatial Data in ASP.NET Core OData ##

If you query some endpoints, you'll see a ``geometry`` data type in some tables... and booom! 

It crashes.

What's the problem?

Entity Framework Core uses the ``NetTopologySuite`` library for mapping Geographical types, so all scaffolded models contain it. But 
ASP.NET Core OData uses the ``Microsoft.Spatial`` library for Geographical types. What a bummer. If we expose the ``NetTopologySuite`` 
objects in the ``EdmModel`` an unserializable hell is awaiting (most probably).

But let's not go crazy and solve it step by step!

### Adding Microsoft.Spatial to the Scaffolded Data Model ###

It's impossible for me to add NetTopologySuite support to ASP.NET Core OData (Sorry!), and it's impossible for me to add support for 
``Microsoft.Spatial`` to Entity Framework Core (Sorry!). So we need to find a way to convert between both of them.

We start by adding the Microsoft.Spatial library to the ``WideWorldImporters.Database`` project:

```
dotnet add package Microsoft.Spatial
```

The OData EDM Model uses the Scaffolded Database model. All scaffolded classes are ``partial`` classes, that means we can weave additional 
information to them at compile-time. Nice! This allows us all dirty tricks. To facilitate this, we need to live in the same assembly as 
the partial classes. 

See where this goes?

### Extending Partial Classes with Microsoft.Spatial properties ###

The idea: We add ``Microsoft.Spatial`` properties prefixed with ``Edm...`` to the generated model using a partial class. OData knows how to work 
with it. At the same time we tell the ``ODataModelBuilder`` to ignore the ``NetTopologySuite`` properties. On the other side, we will tell the 
Entity Framework Core ``DbContext`` to please ignore the ``Microsoft.Spatial`` types.

#### Convert between Microsoft.Spatial and NetTopologySuite ####

What's left is a little conversion between both. So we need a way to convert between both the ``Microsoft.Spatial`` and ``NetTopologySuite`` 
representation. So I am taking the dumbest approach possible... Geographical objects can be represented in a "Well Known Text (WKT)" format, 
and every library dealing with Geographical data should support it:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Database.Spatial
{
    public class GeographyConverter
    {
        private static readonly Microsoft.Spatial.WellKnownTextSqlFormatter _wellKnownTextFormatter = Microsoft.Spatial.WellKnownTextSqlFormatter.Create();

        public static TSpatialType? ConvertTo<TSpatialType>(NetTopologySuite.Geometries.Geometry? dbGeometry)
            where TSpatialType : Microsoft.Spatial.Geography
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
                case NetTopologySuite.Geometries.MultiPoint _:
                case NetTopologySuite.Geometries.Polygon _:
                case NetTopologySuite.Geometries.MultiPolygon _:
                    return ConvertTo(wellKnownText);
                default:
                    throw new ArgumentException($"Conversion for Type '{dbGeometry.GeometryType}' not supported");
            };

            TSpatialType ConvertTo(string wellKnownText)
            {
                using (var textReader = new StringReader(wellKnownText))
                {
                    return _wellKnownTextFormatter.Read<TSpatialType>(textReader);
                }
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

#### Adding Microsoft.Spatial Properties to the Data Model ####

Next we create a folder ``Models``, where we will add additional data to the generated model classes using the ``partial`` keyword. Why 
not directly edit the generated model classes? Because they have been generated and you don't want to recreate all the work, when you 
are updating your database model.

We add a partial class ``City`` and add a property ``EdmLocation`` with the ``Microsoft.Spatial`` datatype. This ``Microsoft.Spatial`` 
property is going to be used by ASP.NET Core OData, while the ``NetTopologySuite`` property is used to communicate with EF Core. 

It's now as simple as:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Spatial;
using WideWorldImporters.Database.Spatial;

namespace WideWorldImporters.Database.Models
{
    public partial class City
    {
        public GeographyPoint? EdmLocation 
        { 
            get 
            {
                if(Location == null)
                {
                    return default;
                }

                return GeographyConverter.ConvertTo<GeographyPoint>(Location);
            }

            set
            {
                Location = GeographyConverter.ConvertFrom(value);
            }
        }
    }
}
```
#### Configuring the DbContext for Spatial types ###

We finally tell the EF Core ``ModelBuilder``, that it should ignore all of our ``Microsoft.Spatial`` properties:

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

#### Configuring the EDM Model for Spatial types ###

Switch back to the ``WideWorldImporters.Api`` project and open the ``ApplicationEdmModel``, that defines the ``IEdmModel``. 

We now have to do the exact opposite of the Entity Framework Core approach, by ignoring the ``NetTopologySuite`` types and 
renaming our ``Edm...`` properties back into their "original" names:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Edm;
using Microsoft.OData.ModelBuilder;
using Microsoft.Spatial;
using WideWorldImporters.Database.Models;

namespace WideWorldImporters.Api.Models
{
    /// <summary>
    /// Uses an <see cref="ODataConventionModelBuilder"/> to build an <see cref="IEdmModel" />.
    /// </summary>
    public static class class ApplicationEdmModel
    {
        /// <summary>
        /// Builds a <see cref="IEdmModel" />.
        /// </summary>
        /// <returns>The <see cref="IEdmModel"/> for the application</returns>
        public static IEdmModel GetEdmModel()
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

### Running Spatial Queries ###

Start the ``WideWorldImporters.Api`` project and navigate to ``http://localhost:5000/swagger/index.html``, et voila, the model now uses the correct OData types:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/07_Schema_Edm_Geometry.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/07_Schema_Edm_Geometry.jpg" alt="EDMX Model with the correct types for Geography">
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

### Custom FilterBinder for Geo distance queries ###

And what's all that good for? 

This enables you to add the Spatial functionality, that isn't provided by ASP.NET Core OData 8 as of writing:

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

Now register the FilterBinder by registering it in the ``IServiceCollection#AddOData`` method provided by ASP.NET Core OData, like this:

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
                // ...
                // Register OData Routes:
                .AddOData((opt) =>
                {
                    opt.AddRouteComponents("odata", ApplicationEdmModel.GetEdmModel(), svcs =>
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
#### Running Spatial Queries using the FilterBinder ####
Let's try!

New York should be somewhere around ``POINT(-73.9814311179 40.7614927583)`` if I am not mistaken. 

So what Cities in our database, are in a 100m Radius of New York?

```
http://localhost:5000/odata/Cities?$select=CityName&$filter=geo.distance(Location, geography'POINT(-73.9814311179 40.7614927583)') lt 100
```

Ah, really? It's New York only?

```json
{
  "@odata.context": "http://localhost:5000/odata/$metadata#Cities(cityName)",
  "value": [ { "cityName": "New York" } ]
}
```

And if we extend it to 10 kilometers?

```
http://localhost:5000/odata/Cities?$select=CityName&$filter=geo.distance(Location, geography'POINT(-73.9814311179 40.7614927583)') lt 10000
```

We get back a lot more Cities in our database and they look correct to me:

```json
{
  "@odata.context": "http://localhost:5000/odata/$metadata#Cities(cityName)",
  "value": [
    { "cityName": "Cliffside Park" },
    { "cityName": "Edgewater" },
    { "cityName": "Fort Lee" },
    { "cityName": "Guttenberg" },
    { "cityName": "Hoboken" },
    { "cityName": "Jersey City" },
    { "cityName": "Manhattan" },
    { "cityName": "New York" },
    { "cityName": "North Bergen" },
    { "cityName": "Palisades Park" },
    { "cityName": "Ridgefield" },
    { "cityName": "Secaucus" },
    { "cityName": "Union City" },
    { "cityName": "Weehawken" },
    { "cityName": "West New York" }
  ]
}
```

So our ``geo.distance`` function works fine. 

## Conclusion ##

And we come to an end here! 

ASP.NET Core OData was a fun experiment and I think it is a great piece of technology. The Microsoft team has 
done a great job enabling OData for ASP.NET Core applications. The API design makes it possible to "easily" extend 
the framework (a relative term when it comes to ``Expression`` trees).

And I hope the next article won't take another 10 months. 😓