title: Visualizing Graphs with Edge Constraints of the SQL Server 2019 Graph Database (SQL Server 2019 CTP 2.0)
date: 2018-10-21 10:11
tags: dotnet, csharp, sqlserver, graph
category: csharp
slug: sql_server_2019_graph_database
author: Philipp Wagner
summary: This article shows how to visualize Graphs using the Edge Constraints Feature of the SQL Server 2019 CTP 2.0 Graph Database.

The SQL Server 2019 Preview has an interesting feature for its Graph Database Engine: Edge Constraints. 

The [Public Preview of Graph Edge Constraints] explains:

> In the first release of SQL Graph, an edge could connect any node to any other node in the 
> database. With Edge Constraints users can enforce specific semantics on the edge tables. The 
> constraints also help in maintaining data integrity.

Edge Constraints finally make it possible to query the for Graph Schema, so I want to use this feature to visualize a Airline On Time Performance Graph Schema from [my previous post on the SQL Server Graph Database].

The source code for this article can be found in my GitHub repository at:

* [https://github.com/bytefish/SqlServer2019GraphDatabase/](https://github.com/bytefish/SqlServer2019GraphDatabase/)

## What we are going to build ##

The plan is to display the Graph model for the [Airline On-Time Performance Dataset], which contains:

> [...] on-time arrival data for non-stop domestic flights by major air carriers, and provides such additional 
> items as departure and arrival delays, origin and destination airports, flight numbers, scheduled and actual departure 
> and arrival times, cancelled or diverted flights, taxi-out and taxi-in times, air time, and non-stop distance.

The Graph model is heavily based on the Neo4j Flight Database example by [Nicole White].

### The Final Application ###

We will be writing a small Web application, that uses [vis.js] for rendering a Graph Schema stored in the SQL Server 2019:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/sql_server_2019_graph_database/graph.jpg">
        <img src="/static/images/blog/sql_server_2019_graph_database/graph.jpg" alt="Resulting Graph of the sample Schema">
    </a>
</div>

## From the Idea to the Implementation ##

The approach for the implementation is quite simple: 

1. Create the Schemas 
2. Create the Graph Node Tables
3. Create the Graph Edge Tables with Edge Constraints
4. Write a TSQL function to output the Graph as JSON using ``FOR JSON``
5. Create a ASP.NET Core Web application
6. Query the SQL function as a Scalar with [ADO.NET]
7. Write an API Endpoint to Query the Graph
8. Convert the Graph into a [vis.js]-compatible JSON representation
9. Display the Graph using the great [vis.js] library

## Implementing the SQL-side ##

### Creating the Schemas ###

I use [Database Schemas] to keep my database clean. In this project I want to group my objects into ``Nodes``, ``Edges`` and ``Functions``:

```sql
IF NOT EXISTS (SELECT name FROM sys.schemas WHERE name = 'Nodes')
BEGIN

    EXEC('create schema [Nodes]')

END
GO

IF NOT EXISTS (SELECT name FROM sys.schemas WHERE name = 'Edges')
BEGIN

    EXEC('create schema [Edges]')

END
GO

IF NOT EXISTS (SELECT name FROM sys.schemas WHERE name = 'Functions')
BEGIN

    EXEC('create schema [Functions]')

END
GO
```

### Creating the Nodes ###

```sql

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[Country]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[Country] (
        [CountryID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Name] [NVARCHAR](255),
        [IsoCode] [NVARCHAR](255)
    ) AS NODE;
    
END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[State]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[State] (
        [StateID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Code] [NVARCHAR](255),
        [Name] [NVARCHAR](255)
    ) AS NODE;
    
END
GO


IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[City]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[City] (
        [CityID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Name] [NVARCHAR](255)
    ) AS NODE;
    
END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[Airport]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[Airport](
        [AirportID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Identifier] NVARCHAR(255) NOT NULL,
        [Abbr] NVARCHAR(55),
        [Name] NVARCHAR(255),
        [City] NVARCHAR(255),
        [StateCode] NVARCHAR(255),
        [StateName] NVARCHAR(255),
        [Country] NVARCHAR(255),
        [CountryIsoCode] NVARCHAR(255),
    ) AS NODE;
    
END
GO


IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[Aircraft]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[Aircraft](
        [AircraftID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [TailNumber] [NVARCHAR](255) NOT NULL
    ) AS NODE;
    
END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[Carrier]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[Carrier](
        [CarrierID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Code] [NVARCHAR](255),
        [Description] [NVARCHAR](255)
    ) AS NODE;
    
END
GO


IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[Flight]') AND type in (N'U'))
BEGIN
     
    CREATE TABLE [Nodes].[Flight](
        [FlightID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Year] [NUMERIC](9, 0),
        [Month] [NUMERIC](9, 0),
        [DayOfMonth] [NUMERIC](9, 0),
        [DayOfWeek] [NUMERIC](9, 0),
        [FlightDate] [DATETIME2],
        [UniqueCarrier] [NVARCHAR](255),
        [TailNumber] [NVARCHAR](255),
        [FlightNumber] [NVARCHAR](255),
        [OriginAirport] [NVARCHAR](55),
        [OriginState] [NVARCHAR](55),
        [DestinationAirport] [NVARCHAR](55),
        [DestinationState] [NVARCHAR](55),
        [DepartureDelay] [NUMERIC](9, 0),
        [TaxiOut] [NUMERIC](9, 0),
        [TaxiIn] [NUMERIC](9, 0),
        [ArrivalDelay] [NUMERIC](9, 0),
        [CancellationCode] [NVARCHAR](255),
        [CarrierDelay] [NUMERIC](9, 0),
        [WeatherDelay] [NUMERIC](9, 0),
        [NasDelay] [NUMERIC](9, 0),
        [SecurityDelay] [NUMERIC](9, 0),
        [LateAircraftDelay] [NUMERIC](9, 0)
    ) AS NODE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Nodes].[Reason]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Nodes].[Reason] (
        [ReasonID] [INTEGER] IDENTITY(1,1) PRIMARY KEY,
        [Code] [NVARCHAR](55) NOT NULL,
        [Description] [NVARCHAR](255) NOT NULL
    ) AS NODE;
    
END
GO
```

### Creating the Edges with Edge Constraints ###

```sql
IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[InCountry]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[InCountry]
    (
        CONSTRAINT EC_IN_COUNTRY CONNECTION ([Nodes].[Airport] TO [Nodes].[Country])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[InState]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[InState]
    (
        CONSTRAINT EC_IN_STATE CONNECTION ([Nodes].[Airport] TO [Nodes].[State])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[InCity]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[InCity] 
    (
        CONSTRAINT EC_IN_CITY CONNECTION ([Nodes].[Airport] TO [Nodes].[City])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[Origin]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[Origin] 
    (
        taxi_time integer, 
        dep_delay integer,
        CONSTRAINT EC_ORIGIN CONNECTION ([Nodes].[Flight] TO [Nodes].[Airport])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[Destination]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[Destination]
    (
        taxi_time integer, 
        arr_delay integer,
        CONSTRAINT EC_DESTINATION CONNECTION ([Nodes].[Flight] TO [Nodes].[Airport])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[Carrier]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[Carrier]
    (
        CONSTRAINT EC_CARRIER CONNECTION ([Nodes].[Flight] TO [Nodes].[Carrier])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[CancelledBy]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[CancelledBy](
            CONSTRAINT EC_CANCELED_BY CONNECTION ([Nodes].[Flight] TO [Nodes].[Reason])
    ) AS EDGE;

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[DelayedBy]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[DelayedBy]
    (
        time INTEGER,
        CONSTRAINT EC_DELAYED_BY CONNECTION ([Nodes].[Flight] TO [Nodes].[Reason])
    ) AS EDGE;
    

END
GO

IF  NOT EXISTS 
    (SELECT * FROM sys.objects 
     WHERE object_id = OBJECT_ID(N'[Edges].[Aircraft]') AND type in (N'U'))
BEGIN

    CREATE TABLE [Edges].[Aircraft]
    (
        CONSTRAINT EC_AIRCRAFT CONNECTION ([Nodes].[Flight] TO [Nodes].[Aircraft])
    )
    AS EDGE;

END
GO
```

### Creating the Graph Schema Function ###

The SQL Function ``[Functions].[GetGraphSchema]`` is used to query a Schema for a Graph. 

The idea is to use the SQL Server ``[sys].[tables]`` table to query for the Nodes first. Then I am using the ``[sys].[columns]`` table to get the Columns of each Node table, which represent the attributes of the given Node. I serialize the result sets into JSON using the ``FOR JSON PATH`` operator of SQL Server.

Then I am using the new Edge Constraint Table in SQL Server 2019 to query for the Edges. This is described in great detail in the blog post: [Public Preview of Graph Edge Constraints]. Again for each Edge I am querying the ``[sys].[columns]`` table to get the attributes:

```sql
IF OBJECT_ID(N'[Functions].[GetGraphSchema]', N'FN') IS NOT NULL
BEGIN
    DROP FUNCTION [Functions].[GetGraphSchema]
END
GO 


CREATE FUNCTION [Functions].[GetGraphSchema](@NodesSchemaName nvarchar(max))
 RETURNS NVARCHAR(MAX)  
AS  
BEGIN  

    DECLARE @NodesSchemaId int = (select schema_id from sys.schemas where [Name] = @NodesSchemaName);

    RETURN (
                SELECT 
                    [name] = @NodesSchemaName,
                    nodes = (SELECT [node].[name] as node_name, 
                                    [node].[object_id] as node_id, 
                                    [attributes] = (SELECT [column].[name] as name, [column].[is_nullable] as is_nullable
                                                    FROM sys.columns as [column]
                                                    WHERE [column].[graph_type] is null and [node].[object_id] = [column].[object_id]
                                                    FOR JSON PATH)
                FROM [sys].[tables] as [node]
                WHERE is_node = 1 and schema_id = @NodesSchemaId
                FOR JSON PATH),
                   edges = (SELECT EC.name AS edge_constraint_name, 
                                   OBJECT_NAME(EC.parent_object_id) AS edge_table_name, 
                                   EC.parent_object_id AS edge_table_id,
                                   OBJECT_NAME(ECC.from_object_id) AS from_node_table_name, 
                                   ECC.from_object_id AS from_node_table_id,
                                   OBJECT_NAME(ECC.to_object_id) AS to_node_table_name, 
                                   ECC.to_object_id AS to_node_table_id,
                                   [attributes] = (SELECT [column].[name] as name, [column].[is_nullable] as is_nullable
                                                   FROM sys.columns as [column]
                                                   WHERE [column].[graph_type] is null and  EC.parent_object_id = [column].[object_id]
                                                   FOR JSON PATH)
                            FROM sys.edge_constraints EC
                                INNER JOIN sys.edge_constraint_clauses ECC ON EC.object_id = ECC.object_id
                            FOR JSON PATH)
            FOR JSON PATH)

END
GO
```

## Implementing the Web Application ##

For the Web Application I am using the Visual Studio 2017 Wizard to create a new ``ASP.NET Core Web Application``. 

We are left with a fresh Web Application, that uses Razor Pages as Template Engine.

### The Graph Model ###

With the Graph Model fresh in mind, we start by modelling the Graph using [Json.NET] for the mapping between the model and the JSON representation. 

You can see how the ``JsonProperty`` attributes map 1:1 to the SQL Server JSON above. I like to explicitly attribute the properties instead of relying on deserialization conventions. This makes it very easy to rename the Objects Property names, without having to touch any of the SQL Server / JSON parts.

#### Graph ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using Newtonsoft.Json;

namespace SqlServer2019Graph.Model
{
    public class Graph
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("nodes")]
        public IList<Node> Nodes { get; set; }

        [JsonProperty("edges")]
        public IList<Edge> Edges { get; set; }
    }
}
```

#### Node ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using Newtonsoft.Json;

namespace SqlServer2019Graph.Model
{
    public class Node
    {
        [JsonProperty("node_id")]
        public int Id { get; set; }

        [JsonProperty("node_name")]
        public string Name { get; set; }

        [JsonProperty("attributes")]
        public IList<Attribute> Attributes { get; set; }
    }
}
```

#### Edge ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using Newtonsoft.Json;

namespace SqlServer2019Graph.Model
{
    public class Edge
    {
        [JsonProperty("edge_table_name")]
        public string Name { get; set; }

        [JsonProperty("edge_table_id")]
        public int Id { get; set; }

        [JsonProperty("from_node_table_id")]
        public int From { get; set; }

        [JsonProperty("to_node_table_id")]
        public int To { get; set; }

        [JsonProperty("attributes")]
        public IList<Attribute> Attributes { get; set; }
    }
}
```

#### Attribute ####

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Newtonsoft.Json;

namespace SqlServer2019Graph.Model
{
    public class Attribute
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("is_nullable")]
        public bool IsNullable { get; set; }
    }
}
```

### The Graph Service ###

The ``GraphService`` will be used to query the function ``[Functions].[GetGraphSchema]`` for the JSON and deserialize it from JSON into the Graph model.

We start by defining the ``IGraphService`` interface, if we ever need to switch the Database:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using SqlServer2019Graph.Model;

namespace SqlServer2019Graph.Services
{
    public interface IGraphService
    {
        Graph GetGraphSchema(string schemaName);
    }
}
```

And now we can finally query the SQL Server 2019 Database, invoke the function and deserialize the JSON result into the ``Graph`` model:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Data;
using System.Data.SqlClient;
using System.Linq;
using Newtonsoft.Json;
using SqlServer2019Graph.Model;

namespace SqlServer2019Graph.Services
{
    public class GraphService : IGraphService
    {
        private readonly string connectionString;

        public GraphService(string connectionString)
        {
            this.connectionString = connectionString;
        }

        public Graph GetGraphSchema(string schemaName)
        {
            var json = GetSchemaAsJsonString(schemaName);

            return JsonConvert
                .DeserializeObject<Graph[]>(json)
                .FirstOrDefault();
        }

        private string GetSchemaAsJsonString(string schemaName)
        {
            if (schemaName == null)
            {
                throw new ArgumentNullException("schemaName");
            }

            using (var connection = new SqlConnection(connectionString))
            {
                connection.Open();

                using (IDbCommand command = connection.CreateCommand())
                {
                    // Build the Stored Procedure Command:
                    command.CommandText = "SELECT [Functions].[GetGraphSchema](@SchemaName)";
                    command.CommandType = CommandType.Text;

                    // Create the Schema Name Parameter:
                    SqlParameter parameter = new SqlParameter();

                    parameter.ParameterName = "@SchemaName";
                    parameter.SqlDbType = SqlDbType.NVarChar;
                    parameter.Direction = ParameterDirection.Input;
                    parameter.Value = schemaName;

                    command.Parameters.Add(parameter);

                    return command.ExecuteScalar() as string;
                }
            }
        }
    }
}
```

### Preparing the Glue ###

#### appsettings.json ####

We start by defining the Application configuration in the ``appsettings.json`` file, which will be automatically read by ASP.NET Core on Startup.

Here we can define the Database Connection String without having to hardcode it into the application:

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Debug"
    }
  },
  "ConnectionStrings": {
    "SqlServer2019": "Data Source=.\\MSSQLSERVER2019;Integrated Security=true;"
  },
  "AllowedHosts": "*"
}
```

### Registering the GraphService ###

In order for being able to automatically inject the ``GraphService`` into other components, we need to register it in the ``Startup`` class of ASP.NET Core.

I am first reading the Connection String from the ``Configuration`` and then register the ``GraphService`` as a Singleton. At the same time I am also setting the CORS Policy to allow everything, so we don't have any problems with Chrome making Pre-Flight CORS Request.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using SqlServer2019Graph.Services;

namespace SqlServer2019Graph
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

            var connectionString = Configuration.GetConnectionString("SqlServer2019");

            services.AddSingleton<IGraphService>(new GraphService(connectionString));

            services
                .AddMvc()
                .SetCompatibilityVersion(CompatibilityVersion.Version_2_1);
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env)
        {
            app
                .UseDeveloperExceptionPage()
                .UseCors(policyName: "Everything")
                .UseStaticFiles()
                .UseMvc();
        }
    }
}
```

### Displaying the Graph ###

Now it comes to displaying the Graph. Hold on, we are almost done! 

Several sources in the internet (Stackoverflow) point to [d3.js] as the best way to displaying Graphs. But learning [d3.js] is impossible for a small weekend project, because it has such a steep learning curve. I found [vis.js], which is a high-quality library and very easy to use. It's a perfect fit for this project!

#### Getting vis.js ####

First thing I do is downloading [vis.js] from:

* [http://visjs.org/](http://visjs.org/)

And saving both files to the ``wwwroot``. ``vis.min.css`` goes to ``~/css``. ``vis.min.js`` goes to ``~/js``.

#### Preparing the Base Layout ####

Then I go into the Razor Pages base layout in the file ``Pages/Shared/_Layout.cshtml``:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />

    <title>@ViewData["Title"] - SQL Server 2019 Examples</title>

    <link rel="stylesheet" href="~/css/vis.min.css" />

    <script src="~/js/vis.min.js"></script>

</head>
<body>
    @RenderBody()
 
    @RenderSection("Scripts", required: false)
</body>
</html>
```

#### Displaying the Graph ####

And now in the entry page of the application ```Pages/Index.cshtml`` I add:

* Some inline CSS for Background and Graph Width
* A ``<div>`` placeholder the Graph will be displayed in 
* The [HTML5 Fetch API] to get the JSON for the Graph


```html
@page
@model IndexModel
@{
    ViewData["Title"] = "Home page";
}

<style>
    body {
        color: #d3d3d3;
        font: 12pt arial;
        background-color: #ffffff;
    }

    #mynetwork {
        width: 800px;
        height: 800px;
        background-color: #fff;
    }
</style>


<div id="mynetwork"></div>

<script type="text/javascript">
    
    fetch('api/graph/schema')
        .then((response) => {
            // Now process the JSON:
            response.json().then((data) => {

                // Log the data :
                console.log(data);

                // Now display the graph using vis.js:
                var options = {
                    edges: {
                        arrows: {
                            to: { enabled: true },
                            from: { enabled: false }
                        }
                    }
                };

                var container = document.getElementById('mynetwork');
                
                new vis.Network(container, data, options);
            });
        })
        .catch((err) => {
            alert("Fetching Graph Schema Failed: " + err);
        });

</script>
```

### Graph REST API ###

But how do we get the [vis.js] Graph?

#### Graph API Controller ####

The API Controller defines a single Endpoint ``GetNodesSchema``, that returns JSON to be displayed by [vis.js]. 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;
using SqlServer2019Graph.Controllers.Converter;
using SqlServer2019Graph.Controllers.DTO;
using SqlServer2019Graph.Services;

namespace SqlServer2019Graph.Controllers
{
    [Controller]
    [Route("api/graph")]
    public class GraphController : ControllerBase
    {
        private readonly IGraphService service;

        public GraphController(IGraphService service)
        {
            this.service = service;
        }

        [HttpGet("schema")]
        public ActionResult<GraphDto> GetNodesSchema()
        {
            var source = service.GetGraphSchema("Nodes");

            var target = Converters.Convert(source);

            return Ok(target);
        }
    }
}
```

#### Defining the vis.js Model ####

The JSON expected by [vis.js] is described in great detail in their docs at:

* [http://visjs.org/docs/network/](http://visjs.org/docs/network/)

We can easily define a model, which I will call ``GraphDto`` to highlight the fact it is a Data Transfer Object for the consumer of the library.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using Newtonsoft.Json;

namespace SqlServer2019Graph.Controllers.DTO
{
    
    public class GraphDto
    {
        [JsonProperty("nodes")]
        public IList<NodeDto> Nodes { get; set; }

        [JsonProperty("edges")]
        public IList<EdgeDto> Edges { get; set; }
    }

    public class NodeDto
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("label")]
        public string Label { get; set; }

        [JsonProperty("group")]
        public string Group { get; set; }
    }

    public class EdgeDto
    {
        [JsonProperty("from")]
        public int From { get; set; }

        [JsonProperty("to")]
        public int To { get; set; }

        [JsonProperty("label")]
        public string Label { get; set; }
    }
}
```

#### Converting between the Graph Model and vis.js Model ####

And promised: The last glue left in the project is to convert from the ``Graph`` model into the vis.js compatible model. I have a huge dislike for projects like ``AutoMapper``, because you can easily shoot yourself in the foot with Reflection-magic / Convention-magic. 

By writing such a simple thing on your own, you can set a Breakpoint where ever you want and debug things. This is gold.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using System.Linq;
using SqlServer2019Graph.Controllers.DTO;
using SqlServer2019Graph.Model;

namespace SqlServer2019Graph.Controllers.Converter
{
    public static class Converters
    {
        public static GraphDto Convert(Graph source)
        {
            if (source == null)
            {
                return null;
            }

            return new GraphDto
            {
                Nodes = ConvertNodes(source.Nodes),
                Edges = ConvertEdges(source.Edges)
            };
        }

        private static IList<NodeDto> ConvertNodes(IList<Node> source)
        {
            if (source == null)
            {
                return null;
            }

            return source
                .Select(x => ConvertNode(x))
                .ToList();
        }

        private static NodeDto ConvertNode(Node source)
        {
            if (source == null)
            {
                return null;
            }

            return new NodeDto
            {
                Label = source.Name,
                Id = source.Id,
                Group = source.Name
            };
        }

        private static IList<EdgeDto> ConvertEdges(IList<Edge> source)
        {
            if (source == null)
            {
                return null;
            }

            return source
                .Select(x => ConvertEdge(x))
                .ToList();
        }

        private static EdgeDto ConvertEdge(Edge source)
        {
            if (source == null)
            {
                return null;
            }

            return new EdgeDto
            {
                Label = source.Name,
                From = source.From,
                To = source.To
            };
        }
    }
}
```

## Conclusion ##

And that's it! You can start the Web Application and the browser should display the Graph.

The SQL Server 2019 Edge Constraints make it very easy to query for a Graph schema. And [vis.js] turned out to be a great library to visualize graphs. 

I hope you had fun reading this article and participating in my though process. 

[Public Preview of Graph Edge Constraints]: https://blogs.msdn.microsoft.com/sqlserverstorageengine/2018/09/28/public-preview-of-graph-edge-constraints-on-sql-server-2019/
[vis.js]: http://visjs.org
[ADO.NET]: https://docs.microsoft.com/en-us/dotnet/framework/data/adonet/ado-net-overview
[Database Schemas]: https://en.wikipedia.org/wiki/Database_schema
[Json.NET]: https://www.newtonsoft.com/json
[d3.js]: https://d3js.org/
[HTML5 Fetch API]: https://developers.google.com/web/updates/2015/03/introduction-to-fetch
[my previous post on the SQL Server Graph Database]: https://bytefish.de/blog/sql_server_2017_graph_database/
[Nicole White]: https://nicolewhite.github.io/
[Airline On-Time Performance Dataset]: https://www.transtats.bts.gov/Tables.asp?DB_ID=120&DB_Name=Airline%20On-Time%20Performance%20Data&DB_Short_Name=On-Time