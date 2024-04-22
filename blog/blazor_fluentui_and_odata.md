title: Extending a Fluent UI Blazor DataGrid for Filtering and Sorting with OData
date: 2023-08-07 12:53
tags: aspnetcore, csharp, blazor, odata
category: blazor
slug: blazor_fluentui_and_odata
author: Philipp Wagner
summary: This article shows how to use Fluent UI Blazor, OData and Kiota to add Filtering to DataGrid. 

This repository shows how to use Blazor, Fluent UI, OData and Kiota to display 
data in a Fluent UI Data Grid. It uses the WideWorldImporters Backend to provide the 
data.

All code can be found in a Git repository at:

* [https://github.com/bytefish/WideWorldImporters](https://github.com/bytefish/WideWorldImporters)

## Table of contents ##

[TOC]

## What we are going to build ##

The idea is to use an ASP.NET Core OData for a Backend and a Blazor Frontend, that uses the Fluent UI 
Components. Fluent UI Blazor provides a nice and extensible DataGrid component, which we are going to add 
components to. The result is going to look like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

It's possible to provide filters for each column, we can for example set a filter for a number range:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid_ColumnFilter_Numeric.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid_ColumnFilter_Numeric.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

## What we are going to build ##

A lot of applications I am working on need Data Grids and Fluent UI Blazor contains a great Data Grid. But 
it lacks components to filter for data and this is a must have for a lot of applications. I understand the reasons 
for not having built-in filters, because everyone expects something different.

So let's change that and add some filtering!

The final result should make it easy to add filters for columns and also support filtering for something like 
nested properties, if our data model looks like it. I am thinking of Navigation Properties, if you are familiar 
with OData.

When writing some Pseudo-Razor code, before starting, I came up with something similar to this:

```razor
<FluentDataGrid @ref="DataGrid" ItemsProvider="@CustomerProvider" Pagination="@Pagination" TGridItem=Customer>
    <PropertyColumn Title="Customer ID" Property="@(c => c!.CustomerId)" Sortable="true" Align=Align.Start>
        <ColumnOptions>
            <NumericFilter TItem="int" PropertyName="CustomerId" FilterState="FilterState"></NumericFilter>
        </ColumnOptions>
    </PropertyColumn>
    <PropertyColumn Title="Name" Property="@(c => c!.CustomerName)" Sortable="true" Align=Align.Start>
        <ColumnOptions>
            <StringFilter PropertyName="CustomerName" FilterState="FilterState"></StringFilter>
        </ColumnOptions>
    </PropertyColumn>
    <!-- ... -->
    <PropertyColumn Title="Last Edited By" Property="@(c => c!.LastEditedByNavigation!.PreferredName)" Sortable="true" Align=Align.Start>
        <ColumnOptions>
            <StringFilter PropertyName="LastEditedByNavigation/PreferredName" FilterState="FilterState"></StringFilter>
        </ColumnOptions>
    </PropertyColumn>
</FluentDataGrid>

<FluentPaginator State="@Pagination" />
```

In this article I will walk you through building a Blazor Frontend, that enables you to show, filter 
and sort data in a FluentUI Data Grid. The Backend is an ASP.NET Core OData-based Webservice, so we have 
a powerful and standardized language to query data sets.

## WideWorldImporters ##

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

### Using Docker to Restore the Database Backup ###

The easiest way to get started is to use Docker.

Go to the `docker` folder of the GitHub repository:

* [/docker](https://github.com/bytefish/WideWorldImporters/tree/main/docker)

And run ...

```powershell
docker compose up
```

A container will be created, that has an SQL Server 2022+ (Port `1533`) and the Wide World Importers OLTP database.

## Building high Quality API Sdks with Kiota ##

How are we going to query the WideWorldImporters OData Service?

The Microsoft Graph API is an OData API and it has thousands of endpoints. It's useful to understand how 
Microsoft themselves are generating their Microsoft Graph SDK. While it's literally impossible to know 
their exact stack, my best guess is, that it's the following two steps:

1. Convert the EDMX Schema to an OpenAPI 3 Schema, using the `Microsoft.OpenApi.OData`.
2. Generate the Microsoft Graph SDK from the OpenAPI 3 Schema, using the Kiota CLI.

Kiota is available at:

* [https://aka.ms/kiota](https://aka.ms/kiota)

It's a command line tool for generating API Clients and is described as ...

> [...] a command line tool for generating an API client to call any OpenAPI-described API 
> you are interested in. The goal is to eliminate the need to take a dependency on a different 
> API SDK for every API that you need to call. Kiota API clients provide a strongly typed 
> experience with all the features you expect from a high quality API SDK, but without 
> having to learn a new library for every HTTP API.

### Generating the OpenAPI 3.0 Schema ###

The WideWorldImporters Services uses the `Microsoft.OpenApi.OData` library to convert the OData `IEdmModel` to an 
`OpenApiDocument`, and return it as JSON. The OpenAPI Schema can then be consumed by the Swagger UI and Kiota.

The Server Code looks like this

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace WideWorldImporters.Server.Api.Controllers
{
    /// <summary>
    /// This Controller exposes an Endpoint for the OpenAPI Schema, which will be generated from an <see cref="IEdmModel"/>.
    /// </summary>
    public class OpenApiController : ControllerBase
    {
        // ...
        
        [HttpGet("odata/openapi.json")]
        public IActionResult GetOpenApiJson()
        {
            var edmModel = ApplicationEdmModel.GetEdmModel();

            var openApiSettings = new OpenApiConvertSettings
            {
                ServiceRoot = new("https://localhost:5000"),
                PathPrefix = "odata",
                EnableKeyAsSegment = true,
            };

            var openApiDocument = edmModel.ConvertToOpenApi(openApiSettings);

            var openApiDocumentAsJson = openApiDocument.SerializeAsJson(OpenApiSpecVersion.OpenApi3_0);

            return Content(openApiDocumentAsJson, "application/json");
        }
    }
}
```

In the Server we configure Swashbuckle to point to our OpenAPI Schema like this:

```csharp
// ...

if (app.Environment.IsDevelopment() || app.Environment.IsStaging())
{
    app.UseSwagger();
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("https://localhost:5000/odata/openapi.json", "TaskManagement Service");
    });
}

// ...
```

### Generate the C\# Model and ApiClient ###

We can now use the OpenAPI endpoint `odata\openapi.json` of the WideWorldImporters Service to generate the client.

We create a new Solution, that's going to hold the Generated SDK at:

* `src/WideWorldImporters.Shared/WideWorldImporters.Shared.ApiSdk`

In the Microsoft repositories we can often see a file called `makesdk.bat` in the root folder, so 
we also create a `makesdk.bat` and put the kiota call in it, like this:

```
@echo off

:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

:: Kiota Executable
set KIOTA_EXECUTABLE=kiota

:: Parameters for the Code Generator
set PARAM_OPENAPI_SCHEMA="https://localhost:5000/odata/openapi.json"
set PARAM_LANGUAGE=csharp
set PARAM_NAMESPACE=WideWorldImporters.Shared.ApiSdk 
set PARAM_OUT_DIR=%~dp0/src/WideWorldImporters.Shared/WideWorldImporters.Shared.ApiSdk
set PARAM_LOG_LEVEL=Trace

:: Run the "kiota generate" command to create the client
%KIOTA_EXECUTABLE% generate^
    --openapi %PARAM_OPENAPI_SCHEMA%^
    --language %PARAM_LANGUAGE%^
    --namespace-name %PARAM_NAMESPACE%^
    --log-level %PARAM_LOG_LEVEL%^
    --output %PARAM_OUT_DIR%
```

We are running it and it comes up with clean model classes and client. It even got the Enumerations right.

```
PS C:\Users\philipp\source\repos\...> tree /f
Folder PATH listing for volume OS
C:.
│   ApiClient.cs
│   kiota-lock.json
│   WideWorldImporters.Shared.ApiSdk.csproj
│
├───Models
│   ├───Edm
│   │       Geometry.cs
│   │       GeometryCollection.cs
│   │       ...
│   │
│   └───WideWorldImportersService
│       │   BuyingGroup.cs
│       │   BuyingGroupCollectionResponse.cs
│       │   City.cs
│       │   CityCollectionResponse.cs
│       │   ColdRoomTemperature.cs
│       │   ColdRoomTemperatureCollectionResponse.cs
│       │   ...
│       │
│       └───ODataErrors
│               ErrorDetails.cs
│               InnerError.cs
│               MainError.cs
│               ODataError.cs```

### Registering the Kiota ApiClient and Dependencies ###

And finally we can add all dependencies for the generated `ApiClient` in the `Program.cs`:

```csharp
// ...

// Add the Kiota Client.
builder.Services.AddScoped<IAuthenticationProvider, AnonymousAuthenticationProvider>();

builder.Services
    .AddHttpClient<IRequestAdapter, HttpClientRequestAdapter>(client => client.BaseAddress = new Uri("https://localhost:5000"))
    .AddHttpMessageHandler<CookieHandler>();

builder.Services.AddScoped<ApiClient>();

// ...
```

We can now query the OData API from Blazor using the `ApiClient`!

## Implementing Filtering and Sorting ##

We now switch to the `WideWorldImporters.Client.Blazor` project and create a new Folder `Models`. This will hold the data model 
for filtering and sorting. 

### Data Model ###

It should be possible to filter various column types, such as a boolean, text, number, date 
or datetime. And that's the starting point. 

We add an enumeration `FilterTypeEnum`, that holds all available filter types:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Shared.Models
{
    public enum FilterTypeEnum
    {
        None = 0,
        BooleanFilter = 1,
        StringFilter = 2,
        NumericFilter = 3,
        DateFilter = 4,
        DateTimeFilter = 5,
    }
}
```

Each Filter is going to expose several operations to filter for, something like a `StartsWith`, `EndsWith` 
or `Contains` operator comes to mind for textual values. So we add all filter operations we can think of 
right now to a `FilterOperatorEnum`. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Shared.Models
{
    public enum FilterOperatorEnum
    {
        None = 0,
        Before = 1,
        After = 2,
        IsEqualTo = 3,
        IsNotEqualTo = 4,
        Contains = 5,
        NotContains = 6,
        StartsWith = 7,
        EndsWith = 8,
        IsNull = 9,
        IsNotNull = 10,
        IsEmpty = 11,
        IsNotEmpty = 12,
        IsGreaterThanOrEqualTo = 13,
        IsGreaterThan = 14,
        IsLessThanOrEqualTo = 15,
        IsLessThan = 16,
        BetweenInclusive = 17,
        BetweenExclusive = 18,
        Yes = 19,
        No = 20,
        All = 21
    }
}
```

All Filters should work on a property name and set a filter operation, both properties 
should be required. And all Filters belong to a filter type, which we have defined in 
the `FilterTypeEnum`.

We end up with something I called a `FilterDescriptor`, that looks like this:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Shared.Models
{
    /// <summary>
    /// Filter Descriptor to filter for a property.
    /// </summary>
    public abstract class FilterDescriptor
    {
        /// <summary>
        /// Gets or sets the Property to filter.
        /// </summary>
        public required string PropertyName { get; set; }

        /// <summary>
        /// Gets or sets the Filter Operator.
        /// </summary>
        public required FilterOperatorEnum FilterOperator { get; set; }

        /// <summary>
        /// Gets or sets the Filter Type.
        /// </summary>
        public abstract FilterTypeEnum FilterType { get; }
    }
}
```

All Filters for specific types then derive from a `FilterDescriptor` and add their required or 
optional properties.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Shared.Models
{
    /// <summary>
    /// A Boolean Filter to filter for Boolean values.
    /// </summary>
    public class BooleanFilterDescriptor : FilterDescriptor
    {
        /// <summary>
        /// Gets the Filter Type.
        /// </summary>
        public override FilterTypeEnum FilterType => FilterTypeEnum.BooleanFilter;
    }

    /// <summary>
    /// A String Filter to filter for text.
    /// </summary>
    public class StringFilterDescriptor : FilterDescriptor
    {
        /// <summary>
        /// Gets or sets the string value.
        /// </summary>
        public string? Value { get; set; }

        /// <summary>
        /// Gets the Filter Type.
        /// </summary>
        public override FilterTypeEnum FilterType => FilterTypeEnum.StringFilter;
    }

    /// <summary>
    /// Numeric Filter to filter between an lower and upper value.
    /// </summary>
    public class NumericFilterDescriptor : FilterDescriptor
    {
        /// <summary>
        /// Gets or sets the lower value.
        /// </summary>
        public double? LowerValue { get; set; }

        /// <summary>
        /// Gets or sets the upper value.
        /// </summary>
        public double? UpperValue { get; set; }

        /// <summary>
        /// Gets the Filter Type.
        /// </summary>
        public override FilterTypeEnum FilterType => FilterTypeEnum.NumericFilter;
    }

    /// <summary>
    /// Date Range Filter to filter between a start and end date.
    /// </summary>
    public class DateFilterDescriptor : FilterDescriptor
    {
        /// <summary>
        /// Start Date for range filtering.
        /// </summary>
        public DateTimeOffset? StartDate { get; set; }

        /// <summary>
        /// End Date for range filtering.
        /// </summary>
        public DateTimeOffset? EndDate { get; set; }

        /// <summary>
        /// Gets the Filter Type.
        /// </summary>
        public override FilterTypeEnum FilterType => FilterTypeEnum.DateFilter;
    }

    /// <summary>
    /// Date Range Filter to filter between a start and end date.
    /// </summary>
    public class DateTimeFilterDescriptor : FilterDescriptor
    {
        /// <summary>
        /// Start Date for range filtering.
        /// </summary>
        public DateTimeOffset? StartDateTime { get; set; }

        /// <summary>
        /// End Date for range filtering.
        /// </summary>
        public DateTimeOffset? EndDateTime { get; set; }

        /// <summary>
        /// Gets the Filter Type.
        /// </summary>
        public override FilterTypeEnum FilterType => FilterTypeEnum.DateTimeFilter;
    }
}
```

That's all there is for the Filter model. What's left is to provide a model for 
sorting, because we want to sort the Data Grid by their properties after 
all. 

Something, that's needed is a sort direction for sure.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Shared.Models
{
    /// <summary>
    /// Sort Direction.
    /// </summary>
    public enum SortDirectionEnum
    {
        /// <summary>
        /// Ascending.
        /// </summary>
        Ascending = 0,

        /// <summary>
        /// Descending.
        /// </summary>
        Descending = 1
    }
}
```

And we need something like a `SortColumn` to allow sorting by a property name and direction: 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Shared.Models
{
    /// <summary>
    /// A SortColumn in a Filter.
    /// </summary>
    public sealed class SortColumn
    {
        /// <summary>
        /// Gets or sets the property name.
        /// </summary>
        public required string PropertyName { get; set; }

        /// <summary>
        /// Gets or sets the sort direction.
        /// </summary>
        public required SortDirectionEnum SortDirection { get; set; }
    }
}
```

### Building the OData Query with Filtering and Sorting ###

Now that we have the various `FilterDescriptor` implementations, we need a way to convert from a 
List of `FilterDescriptor` to an OData Query String. Since we have a very narrow goal of combining 
all `FilterDescriptor` with an `and` it looks rather simple.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Globalization;
using WideWorldImporters.Client.Blazor.Shared.Models;

namespace WideWorldImporters.Client.Blazor.Shared.OData
{
    public static class ODataUtils
    {
        public static string Translate(List<FilterDescriptor> filterDescriptors)
        {
            if (filterDescriptors.Count == 0)
            {
                return string.Empty;
            }

            List<string> filters = new();

            foreach (FilterDescriptor filterDescriptor in filterDescriptors)
            {
                if (filterDescriptor.FilterOperator == FilterOperatorEnum.None)
                {
                    continue;
                }

                var filter = TranslateFilter(filterDescriptor);

                filters.Add(filter);
            }

            return string.Join(" and ", filters
                .Select(filter => $"({filter})"));
        }

        private static string TranslateFilter(FilterDescriptor filterDescriptor)
        {
            switch (filterDescriptor.FilterType)
            {
                case FilterTypeEnum.BooleanFilter:
                    return TranslateBooleanFilter((BooleanFilterDescriptor)filterDescriptor);
                case FilterTypeEnum.DateFilter:
                    return TranslateDateFilter((DateFilterDescriptor)filterDescriptor);
                case FilterTypeEnum.DateTimeFilter:
                    return TranslateDateTimeFilter((DateTimeFilterDescriptor)filterDescriptor);
                case FilterTypeEnum.StringFilter:
                    return TranslateStringFilter((StringFilterDescriptor)filterDescriptor);
                case FilterTypeEnum.NumericFilter:
                    return TranslateNumericFilter((NumericFilterDescriptor)filterDescriptor);
                default:
                    throw new ArgumentException($"Could not translate Filter Type '{filterDescriptor.FilterType}'");

            }
        }

        private static string TranslateBooleanFilter(BooleanFilterDescriptor filterDescriptor)
        {
            switch (filterDescriptor.FilterOperator)
            {
                case FilterOperatorEnum.IsNull:
                    return $"{filterDescriptor.PropertyName} eq null";
                case FilterOperatorEnum.IsNotNull:
                    return $"{filterDescriptor.PropertyName} ne null";
                case FilterOperatorEnum.All:
                    return $"{filterDescriptor.PropertyName} ne null";
                case FilterOperatorEnum.Yes:
                    return $"{filterDescriptor.PropertyName} eq true";
                case FilterOperatorEnum.No:
                    return $"{filterDescriptor.PropertyName} eq false";
                default:
                    throw new ArgumentException($"Could not translate Filter Operator '{filterDescriptor.FilterOperator}'");
            }
        }

        private static string TranslateDateFilter(DateFilterDescriptor filterDescriptor)
        {
            var startDate = ToODataDate(filterDescriptor.StartDate);
            var endDate = ToODataDate(filterDescriptor.EndDate);

            switch (filterDescriptor.FilterOperator)
            {
                case FilterOperatorEnum.IsNull:
                    return $"{filterDescriptor.PropertyName} eq null";
                case FilterOperatorEnum.IsNotNull:
                    return $"{filterDescriptor.PropertyName} ne null";
                case FilterOperatorEnum.IsEqualTo:
                    return $"date({filterDescriptor.PropertyName}) eq {startDate}";
                case FilterOperatorEnum.IsNotEqualTo:
                    return $"date({filterDescriptor.PropertyName}) ne {startDate}";
                case FilterOperatorEnum.After:
                case FilterOperatorEnum.IsGreaterThan:
                    return $"date({filterDescriptor.PropertyName}) gt {startDate}";
                case FilterOperatorEnum.IsGreaterThanOrEqualTo:
                    return $"date({filterDescriptor.PropertyName}) ge {startDate}";
                case FilterOperatorEnum.Before:
                case FilterOperatorEnum.IsLessThan:
                    return $"date({filterDescriptor.PropertyName}) lt {startDate}";
                case FilterOperatorEnum.IsLessThanOrEqualTo:
                    return $"date({filterDescriptor.PropertyName}) le {startDate}";
                case FilterOperatorEnum.BetweenExclusive:
                    return $"(date({filterDescriptor.PropertyName}) gt {startDate}) and (date({filterDescriptor.PropertyName}) lt {endDate})";
                case FilterOperatorEnum.BetweenInclusive:
                    return $"(date({filterDescriptor.PropertyName}) ge {startDate}) and (date({filterDescriptor.PropertyName}) le {endDate})";
                default:
                    throw new ArgumentException($"Could not translate Filter Operator '{filterDescriptor.FilterOperator}'");
            }
        }

        private static string TranslateDateTimeFilter(DateTimeFilterDescriptor filterDescriptor)
        {
            var startDate = ToODataDateTime(filterDescriptor.StartDateTime);
            var endDate = ToODataDateTime(filterDescriptor.EndDateTime);

            switch (filterDescriptor.FilterOperator)
            {
                case FilterOperatorEnum.IsNull:
                    return $"{filterDescriptor.PropertyName} eq null";
                case FilterOperatorEnum.IsNotNull:
                    return $"{filterDescriptor.PropertyName} ne null";
                case FilterOperatorEnum.IsEqualTo:
                    return $"{filterDescriptor.PropertyName} eq {startDate}";
                case FilterOperatorEnum.IsNotEqualTo:
                    return $"{filterDescriptor.PropertyName} ne {startDate}";
                case FilterOperatorEnum.After:
                case FilterOperatorEnum.IsGreaterThan:
                    return $"{filterDescriptor.PropertyName} gt {startDate}";
                case FilterOperatorEnum.IsGreaterThanOrEqualTo:
                    return $"{filterDescriptor.PropertyName} ge {startDate}";
                case FilterOperatorEnum.Before:
                case FilterOperatorEnum.IsLessThan:
                    return $"{filterDescriptor.PropertyName} lt {startDate}";
                case FilterOperatorEnum.IsLessThanOrEqualTo:
                    return $"{filterDescriptor.PropertyName} le {startDate}";
                case FilterOperatorEnum.BetweenExclusive:
                    return $"({filterDescriptor.PropertyName} gt {startDate}) and ({filterDescriptor.PropertyName} lt {endDate})";
                case FilterOperatorEnum.BetweenInclusive:
                    return $"({filterDescriptor.PropertyName} ge {startDate}) and ({filterDescriptor.PropertyName} le {endDate})";
                default:
                    throw new ArgumentException($"Could not translate Filter Operator '{filterDescriptor.FilterOperator}'");
            }
        }

        private static string TranslateStringFilter(StringFilterDescriptor filterDescriptor)
        {
            switch (filterDescriptor.FilterOperator)
            {
                case FilterOperatorEnum.IsNull:
                    return $"{filterDescriptor.PropertyName} eq null";
                case FilterOperatorEnum.IsNotNull:
                    return $"{filterDescriptor.PropertyName} ne null";
                case FilterOperatorEnum.IsEqualTo:
                    return $"{filterDescriptor.PropertyName} eq '{filterDescriptor.Value}'";
                case FilterOperatorEnum.IsNotEqualTo:
                    return $"{filterDescriptor.PropertyName} ne '{filterDescriptor.Value}'";
                case FilterOperatorEnum.IsEmpty:
                    return $"({filterDescriptor.PropertyName} eq null) or ({filterDescriptor.PropertyName} eq '')";
                case FilterOperatorEnum.IsNotEmpty:
                    return $"({filterDescriptor.PropertyName} ne null) and ({filterDescriptor.PropertyName} ne '')";
                case FilterOperatorEnum.Contains:
                    return $"contains({filterDescriptor.PropertyName}, '{filterDescriptor.Value}')";
                case FilterOperatorEnum.NotContains:
                    return $"indexof({filterDescriptor.PropertyName}, '{filterDescriptor.Value}') eq - 1";
                case FilterOperatorEnum.StartsWith:
                    return $"startswith({filterDescriptor.PropertyName}, '{filterDescriptor.Value}')";
                case FilterOperatorEnum.EndsWith:
                    return $"endswith({filterDescriptor.PropertyName}, '{filterDescriptor.Value}')";
                default:
                    throw new ArgumentException($"Could not translate Filter Operator '{filterDescriptor.FilterOperator}'");
            }
        }

        private static string TranslateNumericFilter(NumericFilterDescriptor filterDescriptor)
        {
            var low = filterDescriptor.LowerValue?.ToString(CultureInfo.InvariantCulture);
            var high = filterDescriptor.UpperValue?.ToString(CultureInfo.InvariantCulture);

            switch (filterDescriptor.FilterOperator)
            {
                case FilterOperatorEnum.IsNull:
                    return $"{filterDescriptor.PropertyName} eq null";
                case FilterOperatorEnum.IsNotNull:
                    return $"{filterDescriptor.PropertyName} ne null";
                case FilterOperatorEnum.IsEqualTo:
                    return $"{filterDescriptor.PropertyName} eq {low}";
                case FilterOperatorEnum.IsNotEqualTo:
                    return $"{filterDescriptor.PropertyName} ne {low}";
                case FilterOperatorEnum.IsGreaterThan:
                    return $"{filterDescriptor.PropertyName} gt {low}";
                case FilterOperatorEnum.IsGreaterThanOrEqualTo:
                    return $"{filterDescriptor.PropertyName} ge {low}";
                case FilterOperatorEnum.IsLessThan:
                    return $"{filterDescriptor.PropertyName} lt {low}";
                case FilterOperatorEnum.IsLessThanOrEqualTo:
                    return $"{filterDescriptor.PropertyName} le {low}";
                case FilterOperatorEnum.BetweenExclusive:
                    return $"({filterDescriptor.PropertyName} gt {low}) and({filterDescriptor.PropertyName} lt {high})";
                case FilterOperatorEnum.BetweenInclusive:
                    return $"({filterDescriptor.PropertyName} ge {low}) and({filterDescriptor.PropertyName} le {high})";
                default:
                    throw new ArgumentException($"Could not translate Filter Operator '{filterDescriptor.FilterOperator}'");
            }
        }

        private static string? ToODataDate(DateTimeOffset? dateTimeOffset)
        {
            if (dateTimeOffset == null)
            {
                return null;
            }

            return dateTimeOffset.Value.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        }

        private static string? ToODataDateTime(DateTimeOffset? dateTimeOffset)
        {
            if (dateTimeOffset == null)
            {
                return null;
            }

            return dateTimeOffset.Value
                // ... Convert to Utc Zone
                .ToUniversalTime()
                // ... in ISO 8601 Format
                .ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture);
        }
    }
}
```

## Implementing the Blazor Frontend ##

### Localization using a Shared Resource ###

Localization in ASP.NET Core and Blazor works something like this: You dependency inject 
an `IStringLocalizer<TResource>`, where `TResource` is the name of the class associated 
with the Resource. 

For Blazor we start by adding the following `PropertyGroup` to the `WideWorldImporters.Client.Blazor.csproj` 
project file, which instructs Blazor to load all Globalization data:

```xml
<Project Sdk="Microsoft.NET.Sdk.BlazorWebAssembly">

    <!-- ... -->

    <PropertyGroup>
        <BlazorWebAssemblyLoadAllGlobalizationData>true</BlazorWebAssemblyLoadAllGlobalizationData>
    </PropertyGroup>
    
    <!-- ... -->
    
</Project>
```

Then we register the ASP.NET Core Localization services for the `WebAssemblyHostBuilder`, which 
is defined in the `Program.cs`:

```csharp
builder.Services.AddLocalization();
```

Next we create a new Folder `Localization` and add an empty class `SharedResource`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace WideWorldImporters.Client.Blazor.Localization
{
    public class SharedResource
    {
    }
}
```

... and add a new Resource File by right clicking on the `Localization` folder and click 
`Add` -> `New Item ...`, then search for `Resource File` and add name it 
`SharedResource.resx`.

This file is going to contain all shared localizations in the Blazor frontend. For such 
small projects I don't see a need for having more Resource files, maybe there are different 
opinions.

In the Resource File we are adding translations for the `FilterOperatorEnum` for example:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Blazor_Shared_ResourceFile.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Blazor_Shared_ResourceFile.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

We can then inject the `IStringLocalizer<SharedResource>` into our classes and access all shared 
translations.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;
using WideWorldImporters.Client.Blazor.Localization;

namespace WideWorldImporters.Client.Blazor.Components
{
    public partial class FilterOperatorSelector
    {
        /// <summary>
        /// Localizer.
        /// </summary>
        [Inject]
        public IStringLocalizer<SharedResource> Loc { get; set; } = default!;
        
        // ...
    }
}
```

Translations for enumerations for our application always follow the pattern `<EnumName>_<EnumMember>`, 
which enables us to add a small Extension methods on the `IStringLocalizer<T>` to translate an `enum` 
easily.
 
```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Extensions.Localization;

namespace WideWorldImporters.Client.Blazor.Infrastructure
{
    public static class StringLocalizerExtensions
    {
        public static string TranslateEnum<TResource, TEnum>(this IStringLocalizer<TResource> localizer, TEnum enumValue)
        {
            var key = $"{typeof(TEnum).Name}_{enumValue}";

            var res = localizer.GetString(key);

            return res;
        }
    }
}
```

### Blazor Filter Components ###

#### Filter State ####

The Filters defined for the DataGrid need to go *somewhere*. For the lack of a better name I called 
the container a `FilterState`, which has methods to add and remove filters for a column. Please note, 
that in this model you can only assign a single `FilterDescriptor` to a column.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using System.Collections.Concurrent;
using WideWorldImporters.Client.Blazor.Infrastructure;

namespace WideWorldImporters.Client.Blazor.Components
{
    /// <summary>
    /// Holds state to represent filters in a <see cref="FluentDataGrid{TGridItem}"/>.
    /// </summary>
    public class FilterState
    {
        /// <summary>
        /// Read-Only View of Column Filters.
        /// </summary>
        public IReadOnlyDictionary<string, FilterDescriptor> Filters => _filters;

        /// <summary>
        /// Column Filters.
        /// </summary>
        private readonly ConcurrentDictionary<string, FilterDescriptor> _filters = new();

        /// <summary>
        /// Invoked, when the list of filters change.
        /// </summary>
        public EventCallbackSubscribable<FilterState> CurrentFiltersChanged { get; } = new();

        /// <summary>
        /// Applies a Filter.
        /// </summary>
        /// <param name="filter"></param>
        public Task AddFilterAsync(FilterDescriptor filter)
        {
            _filters[filter.PropertyName] = filter;

            return CurrentFiltersChanged.InvokeCallbacksAsync(this);
        }

        /// <summary>
        /// Removes a Filter.
        /// </summary>
        /// <param name="propertyName"></param>
        public Task RemoveFilterAsync(string propertyName)
        {
            _filters.Remove(propertyName, out var _);

            return CurrentFiltersChanged.InvokeCallbacksAsync(this);
        }
    }
}
```

#### FilterOperatorSelector  ####

All filters need to select a `FilterOperatorEnum`, so we define a component, which is going to be shared 
by all filters. I have called this a `FilterOperatorSelector`. 

In the `FilterOperatorSelector.razor` we are using a `FluentSelect` to select `FilterOperatorEnum` from a 
given list of available operators. See how the `TranslateEnum` extension method is used on the 
`IStringLocalizer<SharedResource>` injected into the component.

```razor
@using WideWorldImporters.Client.Blazor.Shared.Models
@using WideWorldImporters.Client.Blazor.Infrastructure

@namespace WideWorldImporters.Client.Blazor.Components

@inherits FluentComponentBase
<FluentSelect @attributes="AdditionalAttributes" class="@Class" style="@Style"
              Id="@Id"
              AriaLabel="@Title"
              Disabled="@Disabled"
              Items="@FilterOperators"
              OptionText="@(i => Loc.TranslateEnum(i))"
              OptionValue="@(i => i.ToString())"
              TOption=FilterOperatorEnum
              Value=@_value
              SelectedOption=@_filterOperator
              SelectedOptionChanged="OnSelectedValueChanged">
</FluentSelect>
```

The Code-Behind defines the variables the Razor component binds to and exposes an 
`EventCallback`, so a parent component can react on changes.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;
using WideWorldImporters.Client.Blazor.Localization;

namespace WideWorldImporters.Client.Blazor.Components
{
    public partial class FilterOperatorSelector
    {
        /// <summary>
        /// Localizer.
        /// </summary>
        [Inject]
        public IStringLocalizer<SharedResource> Loc { get; set; } = default!;

        /// <summary>
        /// Text used on aria-label attribute.
        /// </summary>
        [Parameter]
        public virtual string? Title { get; set; }

        /// <summary>
        /// If true, will disable the list of items.
        /// </summary>
        [Parameter]
        public virtual bool Disabled { get; set; } = false;

        /// <summary>
        /// Gets or sets the content to be rendered inside the component.
        /// In this case list of FluentOptions
        /// </summary>
        [Parameter]
        public virtual RenderFragment? ChildContent { get; set; }

        /// <summary>
        /// All selectable Filter Operators.
        /// </summary>
        [Parameter]
        public required FilterOperatorEnum[] FilterOperators { get; set; }

        /// <summary>
        /// The FilterOperator.
        /// </summary>
        [Parameter]
        public FilterOperatorEnum FilterOperator { get; set; }

        /// <summary>
        /// Invoked, when the Filter Operator has changed.
        /// </summary>
        [Parameter]
        public EventCallback<FilterOperatorEnum> FilterOperatorChanged { get; set; }

        /// <summary>
        /// Value.
        /// </summary>
        string? _value { get; set; }

        /// <summary>
        /// Filter Operator.
        /// </summary>
        private FilterOperatorEnum _filterOperator { get; set; }

        protected override void OnParametersSet()
        {
            _filterOperator = FilterOperator;
            _value = FilterOperator.ToString();
        }

        public void OnSelectedValueChanged(FilterOperatorEnum value)
        {
            _filterOperator = value;
            _value = value.ToString();

            FilterOperatorChanged.InvokeAsync(_filterOperator);
        }
    }
}
```

#### StringFilter ####

The new Fluent UI Blazor components come with a `FluentGrid`, which allows us to easily build 
responsive designs. I previously played around with a CSS Grid, but why though? We can define 
all of it with Razor Components.

A Filter Component should always look the same. It needs to have a `FilterOperatorSelector` to 
select the operation, a value and two buttons to apply or reset a filter. We end up with the 
following Razor.

```razor
@using Microsoft.FluentUI.AspNetCore.Components
@using WideWorldImporters.Client.Blazor.Shared.Models

@namespace WideWorldImporters.Client.Blazor.Components

@inherits FluentComponentBase

<div class="filter-container">
    <FluentGrid Justify="JustifyContent.Center">
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Filter Operator:</FluentLabel>
            <FilterOperatorSelector FilterOperators="filterOperatorOptions" @bind-FilterOperator="_filterOperator"></FilterOperatorSelector>
        </FluentGridItem>
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Value:</FluentLabel>
            <FluentTextField @bind-Value="_value" Disabled="IsValueDisabled()" Class="w-100"></FluentTextField>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Neutral" OnClick="@(async () => await RemoveFilterAsync())">Reset</FluentButton>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Accent" OnClick="@(async () => await ApplyFilterAsync())">Apply</FluentButton>
        </FluentGridItem>
    </FluentGrid>
</div>
```

The Code-Behind expects a `FilterState` as a Parameter, which is updated when a user clicks 
the `Apply` or `Reset` button.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using Microsoft.AspNetCore.Components;

namespace WideWorldImporters.Client.Blazor.Components
{
    public partial class StringFilter
    {
        /// <summary>
        /// The Property Name.
        /// </summary>
        [Parameter]
        public required string PropertyName { get; set; }

        /// <summary>
        /// The current FilterState.
        /// </summary>
        [Parameter]
        public required FilterState FilterState { get; set; }

        /// <summary>
        /// Filter Options available for the String Filter.
        /// </summary>
        private readonly FilterOperatorEnum[] filterOperatorOptions = new[]
        {
            FilterOperatorEnum.IsEmpty,
            FilterOperatorEnum.IsNotEmpty,
            FilterOperatorEnum.IsNull,
            FilterOperatorEnum.IsNotNull,
            FilterOperatorEnum.IsEqualTo,
            FilterOperatorEnum.IsNotEqualTo,
            FilterOperatorEnum.Contains,
            FilterOperatorEnum.NotContains,
            FilterOperatorEnum.StartsWith,
            FilterOperatorEnum.EndsWith,
        };

        private bool IsValueDisabled()
        {
            return _filterOperator == FilterOperatorEnum.None
                || _filterOperator == FilterOperatorEnum.IsNull
                || _filterOperator == FilterOperatorEnum.IsNotNull;
        }

        protected string? _value { get; set; }

        protected FilterOperatorEnum _filterOperator { get; set; }

        protected override void OnInitialized()
        {
            base.OnInitialized();

            SetFilterValues();
        }

        private void SetFilterValues()
        {
            if (!FilterState.Filters.TryGetValue(PropertyName, out var filterDescriptor))
            {
                _filterOperator = FilterOperatorEnum.None;
                _value = null;

                return;
            }

            var stringFilterDescriptor = filterDescriptor as StringFilterDescriptor;

            if (stringFilterDescriptor == null)
            {
                _filterOperator = FilterOperatorEnum.None;
                _value = null;

                return;
            }

            _filterOperator = stringFilterDescriptor.FilterOperator;
            _value = stringFilterDescriptor.Value;
        }

        protected virtual Task ApplyFilterAsync()
        {
            var stringFilter = new StringFilterDescriptor
            {
                PropertyName = PropertyName,
                FilterOperator = _filterOperator,
                Value = _value
            };

            return FilterState.AddFilterAsync(stringFilter);
        }

        protected virtual async Task RemoveFilterAsync()
        {
            _filterOperator = FilterOperatorEnum.None;
            _value = null;

            await FilterState.RemoveFilterAsync(PropertyName);
        }
    }
}
```

#### NumericFilter ####

The `NumericFilter` allows to filter for numeric values or a range of values. It is somewhat 
"special", because it takes a `typeparam` which is the type of the filtered column, such as 
`int`, `decimal`, `double`, ...

```razor
@using Microsoft.FluentUI.AspNetCore.Components
@using WideWorldImporters.Client.Blazor.Shared.Models

@namespace WideWorldImporters.Client.Blazor.Components

@typeparam TItem

@inherits FluentComponentBase

<div class="filter-container">
    <FluentGrid Justify="JustifyContent.Center">
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Filter Operator:</FluentLabel>
            <FilterOperatorSelector FilterOperators="filterOperatorOptions" @bind-FilterOperator="_filterOperator"></FilterOperatorSelector>
        </FluentGridItem>
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Lower Value:</FluentLabel>
            <FluentNumberField @bind-Value="_lowerValue" Disabled="IsLowerValueDisabled()" Class="w-100"></FluentNumberField>
        </FluentGridItem>
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Upper Value:</FluentLabel>
            <FluentNumberField @bind-Value="_upperValue" Disabled="IsUpperValueDisabled()" Class="w-100"></FluentNumberField>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Neutral" OnClick="@(async () => await RemoveFilterAsync())">Reset</FluentButton>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Accent" OnClick="@(async () => await ApplyFilterAsync())">Apply</FluentButton>
        </FluentGridItem>
    </FluentGrid>
</div>
```

The Code-Behind is nothing special, all parsing and conversion to the `TItem` is already 
handled by the `FluentNumberField` component, that's built into Fluent UI Blazor. Thanks!

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using Microsoft.AspNetCore.Components;

namespace WideWorldImporters.Client.Blazor.Components
{
    public partial class NumericFilter<TItem>
    {
        /// <summary>
        /// The Property Name.
        /// </summary>
        [Parameter]
        public required string PropertyName { get; set; }

        /// <summary>
        /// The current FilterState.
        /// </summary>
        [Parameter]
        public required FilterState FilterState { get; set; }

        /// <summary>
        /// Filter Options available for the NumericFilter.
        /// </summary>
        private readonly FilterOperatorEnum[] filterOperatorOptions = new[]
        {
            FilterOperatorEnum.None,
            FilterOperatorEnum.IsNull,
            FilterOperatorEnum.IsNotNull,
            FilterOperatorEnum.IsEqualTo,
            FilterOperatorEnum.IsNotEqualTo,
            FilterOperatorEnum.IsGreaterThan,
            FilterOperatorEnum.IsGreaterThanOrEqualTo,
            FilterOperatorEnum.IsLessThan,
            FilterOperatorEnum.IsLessThanOrEqualTo,
            FilterOperatorEnum.BetweenExclusive,
            FilterOperatorEnum.BetweenInclusive
        };

        private bool IsLowerValueDisabled()
        {
            return _filterOperator == FilterOperatorEnum.None
                || _filterOperator == FilterOperatorEnum.IsNull
                || _filterOperator == FilterOperatorEnum.IsNotNull;
        }

        private bool IsUpperValueDisabled()
        {
            return _filterOperator != FilterOperatorEnum.BetweenInclusive && _filterOperator != FilterOperatorEnum.BetweenExclusive;
        }

        protected double? _lowerValue { get; set; }

        protected double? _upperValue { get; set; }

        protected FilterOperatorEnum _filterOperator { get; set; }

        protected override void OnInitialized()
        {
            base.OnInitialized();

            SetFilterValues();
        }

        private void SetFilterValues()
        {
            if (!FilterState.Filters.TryGetValue(PropertyName, out var filterDescriptor))
            {
                _filterOperator = FilterOperatorEnum.None;
                _lowerValue = null;
                _upperValue = null;

                return;
            }

            var numericFilterDescriptor = filterDescriptor as NumericFilterDescriptor;

            if (numericFilterDescriptor == null)
            {
                _filterOperator = FilterOperatorEnum.None;
                _lowerValue = null;
                _upperValue = null;

                return;
            }

            _filterOperator = numericFilterDescriptor.FilterOperator;
            _lowerValue = numericFilterDescriptor.LowerValue;
            _upperValue = numericFilterDescriptor.UpperValue;
        }

        protected virtual Task ApplyFilterAsync()
        {
            var numericFilter = new NumericFilterDescriptor
            {
                PropertyName = PropertyName,
                FilterOperator = _filterOperator,
                LowerValue = _lowerValue,
                UpperValue = _upperValue,
            };

            return FilterState.AddFilterAsync(numericFilter);
        }

        protected virtual async Task RemoveFilterAsync()
        {
            _filterOperator = FilterOperatorEnum.None;
            _lowerValue = null;
            _upperValue = null;

            await FilterState.RemoveFilterAsync(PropertyName);
        }
    }
}
```

#### DateFilter ####

Although the column type is a `DateTime`, your users often want to filter by a date and aren't interested 
in the time component. So we will have `DateFilter` and a `DateTimeFilter` component, so you can chose which 
filter to use, based on the use case. 

```razor
@using Microsoft.FluentUI.AspNetCore.Components
@using WideWorldImporters.Client.Blazor.Shared.Models

@namespace WideWorldImporters.Client.Blazor.Components

@inherits FluentComponentBase

<div class="filter-container">
    <FluentGrid Justify="JustifyContent.Center">
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Filter Operator:</FluentLabel>
            <FilterOperatorSelector FilterOperators="filterOperatorOptions" @bind-FilterOperator="_filterOperator"></FilterOperatorSelector>
        </FluentGridItem>
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Start Date:</FluentLabel>
            <FluentDatePicker @bind-Value="_startDateTime" Disabled="IsStartDateTimeDisabled()" Class="w-100"></FluentDatePicker>
        </FluentGridItem>
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">End Date:</FluentLabel>
            <FluentDatePicker @bind-Value="_endDateTime" Disabled="IsEndDateTimeDisabled()" Class="w-100"></FluentDatePicker>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Neutral" OnClick="@(async () => await RemoveFilterAsync())">Reset</FluentButton>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Accent" OnClick="@(async () => await ApplyFilterAsync())">Apply</FluentButton>
        </FluentGridItem>
    </FluentGrid>
</div>
```

The Code-Behind is nothing special, because the `FluentDatePicker` takes care of all date conversions. I 
am unsure about the timezone, but this is a point for later uses.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using Microsoft.AspNetCore.Components;
using WideWorldImporters.Client.Blazor.Components;

namespace WideWorldImporters.Client.Blazor.Components
{
    public partial class DateFilter
    {
        /// <summary>
        /// The Property Name.
        /// </summary>
        [Parameter]
        public required string PropertyName { get; set; }

        /// <summary>
        /// The current FilterState.
        /// </summary>
        [Parameter]
        public required FilterState FilterState { get; set; }
        /// <summary>
        /// Filter Options available for the DateTimeFilter.
        /// </summary>
        private readonly FilterOperatorEnum[] filterOperatorOptions = new[]
        {
            FilterOperatorEnum.IsNull,
            FilterOperatorEnum.IsNotNull,
            FilterOperatorEnum.IsEqualTo,
            FilterOperatorEnum.IsNotEqualTo,
            FilterOperatorEnum.After,
            FilterOperatorEnum.IsGreaterThan,
            FilterOperatorEnum.IsGreaterThanOrEqualTo,
            FilterOperatorEnum.Before,
            FilterOperatorEnum.IsLessThan,
            FilterOperatorEnum.IsLessThanOrEqualTo,
            FilterOperatorEnum.BetweenExclusive,
            FilterOperatorEnum.BetweenInclusive
        };

        protected FilterOperatorEnum _filterOperator { get; set; }

        protected DateTime? _startDateTime { get; set; }

        protected DateTime? _endDateTime { get; set; }

        protected override void OnInitialized()
        {
            base.OnInitialized();

            SetFilterValues();
        }

        private bool IsStartDateTimeDisabled()
        {
            return _filterOperator == FilterOperatorEnum.None
                || _filterOperator == FilterOperatorEnum.IsNull
                || _filterOperator == FilterOperatorEnum.IsNotNull;
        }

        private bool IsEndDateTimeDisabled()
        {
            return _filterOperator != FilterOperatorEnum.BetweenInclusive && _filterOperator != FilterOperatorEnum.BetweenExclusive;
        }

        private void SetFilterValues()
        {
            if (!FilterState.Filters.TryGetValue(PropertyName, out var filterDescriptor))
            {
                _filterOperator = FilterOperatorEnum.None;
                _startDateTime = null;
                _endDateTime = null;

                return;
            }

            var dateFilterDescriptor = filterDescriptor as DateFilterDescriptor;

            if (dateFilterDescriptor == null)
            {
                _filterOperator = FilterOperatorEnum.None;
                _startDateTime = null;
                _endDateTime = null;

                return;
            }

            _filterOperator = dateFilterDescriptor.FilterOperator;
            _startDateTime = dateFilterDescriptor.StartDate?.DateTime;
            _endDateTime = dateFilterDescriptor.EndDate?.DateTime;
        }

        protected virtual Task ApplyFilterAsync()
        {
            var numericFilter = new DateFilterDescriptor
            {
                PropertyName = PropertyName,
                FilterOperator = _filterOperator,
                StartDate = _startDateTime,
                EndDate = _endDateTime,
            };

            return FilterState.AddFilterAsync(numericFilter);
        }

        protected virtual async Task RemoveFilterAsync()
        {
            _filterOperator = FilterOperatorEnum.None;
            _startDateTime = null;
            _endDateTime = null;

            await FilterState.RemoveFilterAsync(PropertyName);
        }
    }
}
```

#### DateTimeFilter ####

The `DateTimeFilter` component uses both, the `FluentDatePicker` and the `FluentTimePicker`. This allows you 
to set the Date and the Time component of a `DateTime`. You can see, that both fields can bind to the same 
`DateTime`.

```razor
@using Microsoft.FluentUI.AspNetCore.Components
@using WideWorldImporters.Client.Blazor.Shared.Models

@namespace WideWorldImporters.Client.Blazor.Components

@inherits FluentComponentBase

<div class="filter-container">
    <FluentGrid Justify="JustifyContent.Center">
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Filter Operator:</FluentLabel>
            <FilterOperatorSelector FilterOperators="filterOperatorOptions" @bind-FilterOperator="_filterOperator"></FilterOperatorSelector>
        </FluentGridItem>
        <FluentGridItem xs="8">
            <FluentLabel Typo="Typography.Body">Start Date:</FluentLabel>
            <FluentDatePicker @bind-Value="_startDateTime" Disabled="IsStartDateTimeDisabled()" Class="w-100"></FluentDatePicker>
        </FluentGridItem>
        <FluentGridItem xs="4">
            <FluentLabel Typo="Typography.Body">Start Time:</FluentLabel>
            <FluentTimePicker @bind-Value="_startDateTime" Disabled="IsStartDateTimeDisabled()" Class="w-100"></FluentTimePicker>
        </FluentGridItem>
        <FluentGridItem xs="8">
            <FluentLabel Typo="Typography.Body">End Date:</FluentLabel>
            <FluentDatePicker @bind-Value="_endDateTime" Disabled="IsEndDateTimeDisabled()" Class="w-100"></FluentDatePicker>
        </FluentGridItem>
        <FluentGridItem xs="4">
            <FluentLabel Typo="Typography.Body">End Time:</FluentLabel>
            <FluentTimePicker @bind-Value="_endDateTime" Disabled="IsEndDateTimeDisabled()" Class="w-100"></FluentTimePicker>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Neutral" OnClick="@(async () => await RemoveFilterAsync())">Reset</FluentButton>
        </FluentGridItem>
        <FluentGridItem xs="6">
            <FluentButton Class="w-100" Appearance="Appearance.Accent" OnClick="@(async () => await ApplyFilterAsync())">Apply</FluentButton>
        </FluentGridItem>
    </FluentGrid>
</div>
```

The Code-Behind is a Copy and Paste from the `DateFilter`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;
using Microsoft.AspNetCore.Components;
using WideWorldImporters.Client.Blazor.Components;

namespace WideWorldImporters.Client.Blazor.Components
{
    public partial class DateTimeFilter
    {
        /// <summary>
        /// The Property Name.
        /// </summary>
        [Parameter]
        public required string PropertyName { get; set; }

        /// <summary>
        /// The current FilterState.
        /// </summary>
        [Parameter]
        public required FilterState FilterState { get; set; }
        /// <summary>
        /// Filter Options available for the DateTimeFilter.
        /// </summary>
        private readonly FilterOperatorEnum[] filterOperatorOptions = new[]
        {
            FilterOperatorEnum.IsNull,
            FilterOperatorEnum.IsNotNull,
            FilterOperatorEnum.IsEqualTo,
            FilterOperatorEnum.IsNotEqualTo,
            FilterOperatorEnum.After,
            FilterOperatorEnum.IsGreaterThan,
            FilterOperatorEnum.IsGreaterThanOrEqualTo,
            FilterOperatorEnum.Before,
            FilterOperatorEnum.IsLessThan,
            FilterOperatorEnum.IsLessThanOrEqualTo,
            FilterOperatorEnum.BetweenExclusive,
            FilterOperatorEnum.BetweenInclusive
        };

        protected FilterOperatorEnum _filterOperator { get; set; }

        protected DateTime? _startDateTime { get; set; }

        protected DateTime? _endDateTime { get; set; }

        protected override void OnInitialized()
        {
            base.OnInitialized();

            SetFilterValues();
        }

        private bool IsStartDateTimeDisabled()
        {
            return _filterOperator == FilterOperatorEnum.None
                || _filterOperator == FilterOperatorEnum.IsNull
                || _filterOperator == FilterOperatorEnum.IsNotNull;
        }

        private bool IsEndDateTimeDisabled()
        {
            return _filterOperator != FilterOperatorEnum.BetweenInclusive && _filterOperator != FilterOperatorEnum.BetweenExclusive;
        }

        private void SetFilterValues()
        {
            if (!FilterState.Filters.TryGetValue(PropertyName, out var filterDescriptor))
            {
                _filterOperator = FilterOperatorEnum.None;
                _startDateTime = null;
                _endDateTime = null;

                return;
            }

            var dateTimeFilterDescriptor = filterDescriptor as DateTimeFilterDescriptor;

            if (dateTimeFilterDescriptor == null)
            {
                _filterOperator = FilterOperatorEnum.None;
                _startDateTime = null;
                _endDateTime = null;

                return;
            }

            _filterOperator = dateTimeFilterDescriptor.FilterOperator;
            _startDateTime = dateTimeFilterDescriptor.StartDateTime?.DateTime;
            _endDateTime = dateTimeFilterDescriptor.EndDateTime?.DateTime;
        }

        protected virtual Task ApplyFilterAsync()
        {
            var numericFilter = new DateTimeFilterDescriptor
            {
                PropertyName = PropertyName,
                FilterOperator = _filterOperator,
                StartDateTime = _startDateTime,
                EndDateTime = _endDateTime,
            };

            return FilterState.AddFilterAsync(numericFilter);
        }

        protected virtual async Task RemoveFilterAsync()
        {
            _filterOperator = FilterOperatorEnum.None;
            _startDateTime = null;
            _endDateTime = null;

            await FilterState.RemoveFilterAsync(PropertyName);
        }
    }
}
```


## Using the Filters in the DataGrid ##

The best place to understand how the FluentUI Data Grid works is the Demo page over at:

* [https://www.fluentui-blazor.net/DataGrid](https://www.fluentui-blazor.net/DataGrid)

So we add a page `CustomersDataGrid`, which provides the Data Grid for Customers and adds 
a Filter Component on each of the rows. You can see how the `ApiClient` is injected into 
the component, so we can query the OData API.

```razor
@page "/Customers"
@using WideWorldImporters.Client.Blazor.Components
@using WideWorldImporters.Shared.ApiSdk;
@using WideWorldImporters.Shared.ApiSdk.Models.WideWorldImportersService;

@inject ApiClient ApiClient;

<PageTitle>Customers</PageTitle>

<h1>Customers</h1>

@if (CustomerProvider == null)
{
    <p><em>Loading...</em></p>
}
else
{
    <FluentDataGrid @ref="DataGrid" ItemsProvider="@CustomerProvider" Pagination="@Pagination" TGridItem=Customer>
        <PropertyColumn Title="Customer ID" Property="@(c => c!.CustomerId)" Sortable="true" Align=Align.Start>
            <ColumnOptions>
                <NumericFilter TItem="int" PropertyName="CustomerId" FilterState="FilterState"></NumericFilter>
            </ColumnOptions>
        </PropertyColumn>
        <PropertyColumn Title="Name" Property="@(c => c!.CustomerName)" Sortable="true" Align=Align.Start>
            <ColumnOptions>
                <StringFilter PropertyName="CustomerName" FilterState="FilterState"></StringFilter>
            </ColumnOptions>
        </PropertyColumn>
        <PropertyColumn Title="Account Opened" Property="@(c => c!.AccountOpenedDate)" Format="yyyy-MM-dd" Sortable="true" Align=Align.Start>
            <ColumnOptions>
                <DateFilter PropertyName="AccountOpenedDate" FilterState="FilterState"></DateFilter>
            </ColumnOptions>
        </PropertyColumn>
        <PropertyColumn Title="Is On Credit Hold" Property="@(c => c!.IsOnCreditHold)" Sortable="true" Align=Align.Start>
            <ColumnOptions>
                <BooleanFilter PropertyName="IsOnCreditHold" FilterState="FilterState"></BooleanFilter>
            </ColumnOptions>
        </PropertyColumn>
        <PropertyColumn Title="Last Edited By" Property="@(c => c!.LastEditedByNavigation!.PreferredName)" Sortable="true" Align=Align.Start>
            <ColumnOptions>
                <StringFilter PropertyName="LastEditedByNavigation/PreferredName" FilterState="FilterState"></StringFilter>
            </ColumnOptions>
        </PropertyColumn>
    </FluentDataGrid>

    <FluentPaginator State="@Pagination" />
}
```

In the Code-Behind we are now connecting the `FluentDataGrid`, `PaginationState`, `FilterState` and `ApiClient` to query for the data. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Components;
using WideWorldImporters.Shared.ApiSdk.Models.WideWorldImportersService;
using WideWorldImporters.Shared.ApiSdk;
using WideWorldImporters.Client.Blazor.Shared.OData;
using WideWorldImporters.Client.Blazor.Infrastructure;
using WideWorldImporters.Client.Blazor.Extensions;
using Microsoft.FluentUI.AspNetCore.Components;
using WideWorldImporters.Client.Blazor.Components;

namespace WideWorldImporters.Client.Blazor.Pages
{
    public partial class CustomersDataGrid
    {
        /// <summary>
        /// Provides the Data Items.
        /// </summary>
        private GridItemsProvider<Customer> CustomerProvider = default!;

        /// <summary>
        /// DataGrid.
        /// </summary>
        private FluentDataGrid<Customer> DataGrid = default!;

        /// <summary>
        /// The current Pagination State.
        /// </summary>
        private readonly PaginationState Pagination = new() { ItemsPerPage = 10 };

        /// <summary>
        /// The current Filter State.
        /// </summary>
        private readonly FilterState FilterState = new();

        /// <summary>
        /// Reacts on Paginator Changes.
        /// </summary>
        private readonly EventCallbackSubscriber<FilterState> CurrentFiltersChanged;

        public CustomersDataGrid()
        {
            CurrentFiltersChanged = new(EventCallback.Factory.Create<FilterState>(this, RefreshData));
        }

        protected override Task OnInitializedAsync()
        {
            CustomerProvider = async request =>
            {
                var response = await GetCustomers(request);

                if (response == null)
                {
                    return GridItemsProviderResult.From(items: new List<Customer>(), totalItemCount: 0);
                }

                var entities = response.Value;

                if (entities == null)
                {
                    return GridItemsProviderResult.From(items: new List<Customer>(), totalItemCount: 0);
                }

                int count = response.GetODataCount();

                return GridItemsProviderResult.From(items: entities, totalItemCount: count);
            };

            return base.OnInitializedAsync();
        }

        /// <inheritdoc />
        protected override Task OnParametersSetAsync()
        {
            // The associated filter state may have been added/removed/replaced
            CurrentFiltersChanged.SubscribeOrMove(FilterState.CurrentFiltersChanged);

            return Task.CompletedTask;
        }

        private Task RefreshData()
        {
            return DataGrid.RefreshDataAsync();
        }

        private async Task<CustomerCollectionResponse?> GetCustomers(GridItemsProviderRequest<Customer> request)
        {
            // Extract all Sort Columns from the Blazor FluentUI DataGrid
            var sortColumns = DataGridUtils.GetSortColumns(request);

            // Extract all Filters from the Blazor FluentUI DataGrid
            var filters = FilterState.Filters.Values.ToList();

            // Build the ODataQueryParameters using the ODataQueryParametersBuilder
            var parameters = ODataQueryParameters.Builder
                .SetPage(Pagination.CurrentPageIndex + 1, Pagination.ItemsPerPage)
                .SetFilter(filters)
                .AddExpand(nameof(Customer.LastEditedByNavigation))
                .AddOrderBy(sortColumns)
                .Build();

            // Get the Data using the ApiClient from the SDK
            return await ApiClient.Odata.Customers.GetAsync(request =>
            {
                request.QueryParameters.Count = true;
                
                request.QueryParameters.Top = parameters.Top;
                request.QueryParameters.Skip = parameters.Skip;

                if(parameters.Expand != null)
                {
                    request.QueryParameters.Expand = parameters.Expand;
                }

                if (!string.IsNullOrWhiteSpace(parameters.Filter))
                {
                    request.QueryParameters.Filter = parameters.Filter;
                }

                if (parameters.OrderBy != null)
                {
                    request.QueryParameters.Orderby = parameters.OrderBy;
                }
            });
        }
    }
}
```

To get the `SortColumn` list from the `FluentDataGrid`, we are defining a `DataGridUtils` class.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.FluentUI.AspNetCore.Components;
using WideWorldImporters.Client.Blazor.Shared.Models;

namespace WideWorldImporters.Client.Blazor.Infrastructure
{
    /// <summary>
    /// Utility methods for a <see cref="GridItemsProvider{TGridItem}"/>.
    /// </summary>
    public static class DataGridUtils
    {
        /// <summary>
        /// Gets list of <see cref="SortColumn"/> from a given <see cref="GridItemsProvider{TGridItem}"/>.
        /// </summary>
        /// <typeparam name="TGridItem">Type of the GridItem</typeparam>
        /// <param name="request">Request for providing data</param>
        /// <returns>List of <see cref="SortColumn"/></returns>
        public static List<SortColumn> GetSortColumns<TGridItem>(GridItemsProviderRequest<TGridItem> request)
        {
            var sortByProperties = request.GetSortByProperties();

            return Converters.ConvertToSortColumns(sortByProperties);
        }
    }
}
```

And I have defined a class `ODataQueryParameters`, which encapsulates all logic for translating the `FilterDescriptors` and `SortColumns`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Client.Blazor.Shared.Models;

namespace WideWorldImporters.Client.Blazor.Shared.OData
{
    /// <summary>
    /// Holds the values for the OData $skip, $top, $filter and $orderby clauses.
    /// </summary>
    public class ODataQueryParameters
    {
        /// <summary>
        /// Gets or sets the number of elements to skip.
        /// </summary>
        public int? Skip { get; set; }

        /// <summary>
        /// Gets or sets the number of elements to take.
        /// </summary>
        public int? Top { get; set; }

        /// <summary>
        /// Gets or sets the filter clause.
        /// </summary>
        public string? Filter { get; set; }

        /// <summary>
        /// Gets or sets the expand clause.
        /// </summary>
        public string[]? Expand { get; set; }

        /// <summary>
        /// Gets or sets the order by clause.
        /// </summary>
        public string[]? OrderBy { get; set; }

        /// <summary>
        /// Gets or sets the option to include the count (default: <see cref="true"/>).
        /// </summary>
        public bool IncludeCount { get; set; } = true;

        /// <summary>
        /// Gets an <see cref="ODataQueryParametersBuilder"/> to create <see cref="ODataQueryParameters"/>.
        /// </summary>
        public static ODataQueryParametersBuilder Builder => new ODataQueryParametersBuilder();
    }

    /// <summary>
    /// A Builder to simplify building <see cref="ODataQueryParameters"/>.
    /// </summary>
    public class ODataQueryParametersBuilder
    {
        private int? _skip;
        private int? _top;
        private string? _filter;
        private List<string> _orderby = new();
        private List<string> _expand = new();

        /// <summary>
        /// Sets the $top and $skip clauses using the page information.
        /// </summary>
        /// <param name="pageNumber">Page number to request</param>
        /// <param name="pageNumber">Page size to request</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $top and $skip clauses set</returns>
        public ODataQueryParametersBuilder SetPage(int pageNumber, int pageSize)
        {
            _skip = (pageNumber - 1) * pageSize;
            _top = pageSize;

            return this;
        }


        /// <summary>
        /// Sets the $filter clause.
        /// </summary>
        /// <param name="filterDescriptors">Filter Descriptors to filter for</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $filter clause set</returns>
        public ODataQueryParametersBuilder SetFilter(List<FilterDescriptor> filterDescriptors)
        {
            _filter = ODataUtils.Translate(filterDescriptors);

            return this;
        }

        /// <summary>
        /// Sets the $expand clause.
        /// </summary>
        /// <param name="filterDescriptors">Filter Descriptors to filter for</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $filter clause set</returns>
        public ODataQueryParametersBuilder AddExpand(string expand)
        {
            if (!_expand.Contains(expand))
            {
                _expand.Add(expand);
            }

            return this;
        }

        /// <summary>
        /// Sets the $orderby clause.
        /// </summary>
        /// <param name="columns">List of Columns to sort by</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $orderby clause set</returns>
        public ODataQueryParametersBuilder AddOrderBy(SortColumn column)
        {
            var orderByClause = GetOrderByColumns(new[] { column });

            if (string.IsNullOrWhiteSpace(orderByClause))
            {
                _orderby.Add(orderByClause);
            }

            return this;
        }

        /// <summary>
        /// Sets the $orderby clause.
        /// </summary>
        /// <param name="columns">List of Columns to sort by</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $orderby clause set</returns>
        public ODataQueryParametersBuilder AddOrderBy(List<SortColumn> columns)
        {
            if (columns.Count == 0)
            {
                return this;
            }

            var orderbyClause = GetOrderByColumns(columns);

            if (string.IsNullOrWhiteSpace(orderbyClause))
            {
                return this;
            }

            _orderby.Add(orderbyClause);

            return this;
        }

        /// <summary>
        /// Translates the given <paramref name="columns"/> to OData string.
        /// </summary>
        /// <param name="columns">Columns to convert into the OData $orderby string</param>
        /// <returns>The $orderby clause from the given columns</returns>
        private string GetOrderByColumns(ICollection<SortColumn> columns)
        {
            var sortColumns = columns
                // We need a Tag with the OData Path:
                .Where(column => column.PropertyName != null)
                // Turn into OData string:
                .Select(column =>
                {
                    var sortDirection = column.SortDirection == SortDirectionEnum.Descending ? "desc" : "asc";

                    return $"{column.PropertyName} {sortDirection}";
                });

            return string.Join(",", sortColumns);
        }

        /// <summary>
        /// Builds the <see cref="ODataQueryParameters"/> object with the clauses set.
        /// </summary>
        /// <returns><see cref="ODataQueryParameters"/> with the OData clauses applied</returns>
        public ODataQueryParameters Build()
        {
            return new ODataQueryParameters
            {
                Skip = _skip,
                Top = _top,
                Filter = _filter,
                Expand = _expand.Any() ? _expand.ToArray() : null,
                OrderBy = _orderby.Any() ? _orderby.ToArray() : null,
            };
        }
    }
}
```

And we are done!

## Conclusion ##

You now have a good idea how to add a powerful Data Grid to your Blazor application. It's easy to add your 
own filter components and integrate them into it. A lot of the code can be generalized I think to allow for 
other protocols, but I don't feel the need.

My personal opinion is, that Microsoft is sitting on something great with Fluent UI Blazor and OData.