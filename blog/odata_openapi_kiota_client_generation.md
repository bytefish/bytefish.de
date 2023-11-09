title: OData, OpenAPI and Kiota for building API Clients and using it in Blazor
date: 2023-11-09 12:35
tags: aspnetcore, dotnet, odata
category: dotnet
slug: odata_openapi_kiota_client_generation
author: Philipp Wagner
summary: This article shows how to use OData, OpenAPI and Kiota to build API Clients.

So we have been developing an ASP.NET Core OData Service, that models a simplified Task Management 
system. We have added Relationship-based Access Control on top of it, so we can allow fine-grained 
access to the data.

By using EntityFramework Core, we have got a pretty nice way to query the data, and it has been 
easy to integrate it with an ASP.NET Core OData Service. The ASP.NET Core OData Service exposes 
a nice schema, that a client can be generated from.

In this article we will see how to use OpenAPI and [Kiota](https://aka.ms/kiota) to generate a C\# Client. This client will 
be added to a Blazor application, which is going to display the User Tasks in a Data Grid. I have 
previously written about Data Grids with Blazor Fluent UI.

All Code in this article can be found in the Git Repository at:

* [https://github.com/bytefish/ODataRebacExperiments](https://github.com/bytefish/ODataRebacExperiments) 

## What's the Problem? ##

As a solo developer or in a small team you really don't want to hand-roll a API SDK for all your 
endpoints and for all languages you want to support. It's time-consuming to keep everything in sync, 
and it requires a lot of experience to determine the extension points your API surface needs.

So what we are going to do is to use Kiota, which is Microsofts command line tool to generate 
API Clients for languages such as C\#, Python, Go, ... and many others. It provides some very 
nice abstractions, as you will see.

At the end of the article we will be able to query the OData Service and display all Tasks in a DataGrid:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/odata_openapi_kiota_client_generation/blazor_data_grid.jpg">
        <img src="/static/images/blog/odata_openapi_kiota_client_generation/blazor_data_grid.jpg" alt="Final Swagger Endpoints">
    </a>
</div>

## Generating the API Client SDK ##

The Microsoft Graph API is an OData API and it has thousands of endpoints. It's useful to understand how 
Microsoft themselves are generating their Microsoft Graph SDK. While it's literally impossible to know 
their exact stack, my best guess is, that it's the following two steps:

1. Convert the EDMX Schema to an OpenAPI 3 Schema, using the `Microsoft.OpenApi.OData`.
2. Generate the Microsoft Graph SDK from the OpenAPI 3 Schema, using the Kiota CLI.

Kiota is a command line tool for generating API Clients and is described as ...

> [...] a command line tool for generating an API client to call any OpenAPI-described API 
> you are interested in. The goal is to eliminate the need to take a dependency on a different 
> API SDK for every API that you need to call. Kiota API clients provide a strongly typed 
> experience with all the features you expect from a high quality API SDK, but without 
> having to learn a new library for every HTTP API.

### Generating the OpenAPI 3.0 Schema ###

We start by creating a new endpoint, that uses the `Microsoft.OpenApi.OData` library to convert the OData `IEdmModel` to an 
`OpenApiDocument`, and return it as JSON. The OpenAPI Schema can then be consumed by the Swagger UI and Kiota.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;
using Microsoft.OpenApi.OData;
using Microsoft.OpenApi;
using RebacExperiments.Server.Api.Infrastructure.Errors;
using RebacExperiments.Server.Api.Infrastructure.OData;
using Microsoft.OpenApi.Extensions;
using Microsoft.OData.Edm;

namespace RebacExperiments.Server.Api.Controllers
{
    /// <summary>
    /// This Controller exposes an Endpoint for the OpenAPI Schema, which will be generated from an <see cref="IEdmModel"/>.
    /// </summary>
    public class OpenApiController : ControllerBase
    {
        private readonly ILogger<AuthenticationController> _logger;

        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public OpenApiController(ILogger<AuthenticationController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [HttpGet("odata/openapi.json")]
        public IActionResult GetOpenApiJson()
        {
            try
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
            catch(Exception ex)
            {
                _logger.LogError(ex, "Failed to generate the OpenAPI Schema from the EDM Schema");

                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
    }
}
```

We configure Swashbuckle to point to our OpenAPI Schema like this:

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

We can now use the OpenAPI endpoint `odata\openapi.json` to generate the client.

We create a new Solution, that's going to hold the Generated SDK at:

* `src/Shared/RebacExperiments.Shared.ApiSdk`

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
set PARAM_NAMESPACE=RebacExperiments.Shared.ApiSdk 
set PARAM_OUT_DIR=%~dp0/src/Shared/RebacExperiments.Shared.ApiSdk
set PARAM_LOG_LEVEL=Trace

:: Run the "kiota generate" command to create the client
%KIOTA_EXECUTABLE% generate^
    --openapi %PARAM_OPENAPI_SCHEMA%^
    --language %PARAM_LANGUAGE%^
    --namespace-name %PARAM_NAMESPACE%^
    --log-level %PARAM_LOG_LEVEL%^
    --output %PARAM_OUT_DIR%
```

We are running it and... to my *very surprise* we end up with clean model classes and a client! It even got the Enumerations right.

```
PS C:\Users\philipp\source\repos\bytefish\ODataRebacExperiments\src\Shared\RebacExperiments.Shared.ApiSdk> tree /f
Folder PATH listing for volume OS
Volume serial number is 1274-2B9B
C:.
│   ApiClient.cs
│   kiota-lock.json
│   RebacExperiments.Shared.ApiSdk.csproj
│
├───Models
│   │   UserTask.cs
│   │   UserTaskCollectionResponse.cs
│   │   UserTaskPriorityEnum.cs
│   │   UserTaskStatusEnum.cs
│   │
│   └───ODataErrors
│           ErrorDetails.cs
│           InnerError.cs
│           MainError.cs
│           ODataError.cs
│
└───Odata
    │   OdataRequestBuilder.cs
    │
    ├───SignInUser
    │       SignInUserPostRequestBody.cs
    │       SignInUserRequestBuilder.cs
    │
    ├───SignOutUser
    │       SignOutUserRequestBuilder.cs
    │
    └───UserTasks
        │   UserTasksRequestBuilder.cs
        │
        ├───Count
        │       CountRequestBuilder.cs
        │
        └───Item
                UserTasksItemRequestBuilder.cs
```

## Adding it to Blazor ##

### Sending the Browser Cookies for all Requests ###

We are doing Cookie Authentication, so all our HTTP Requests should send along the Authentication Cookie. We 
start by adding a `CookieHandler` like this, so we configure the `HttpRequestMessage` to also send the Cookies.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Components.WebAssembly.Http;

namespace RebacExperiments.Blazor.Infrastructure
{
    public class CookieHandler : DelegatingHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            request.SetBrowserRequestCredentials(BrowserRequestCredentials.Include);

            return await base.SendAsync(request, cancellationToken);
        }
    }
}
```

And we add it in the `Program.cs` as:

```csharp
// ... 

// We need the CookieHandler to send the Authentication Cookie to the Server.
builder.Services.AddScoped<CookieHandler>();

// ...
```

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

### ODataQueryParameters to hold the OData Clauses ###

Since we don't take additional dependencies on OData libraries, we need to add a class, that 
holds all OData Parameters we are going to send to our OData Endpoints using the Kiota generated 
`ApiClient`:

```csharp
using RebacExperiments.Blazor.Shared.Extensions;

namespace RebacExperiments.Blazor.Shared.Models
{
    /// <summary>
    /// Holds the values for the OData $skip, $top, $filter and $orderby clauses.
    /// </summary>
    public class ODataQueryParameters
    {
        /// <summary>
        /// Gets or sets the number of elements to skip.
        /// </summary>
        public int? Skip { get; set; } = null;

        /// <summary>
        /// Gets or sets the number of elements to take.
        /// </summary>
        public int? Top { get; set; } = null;

        /// <summary>
        /// Gets or sets the filter clause.
        /// </summary>
        public string? Filter { get; set; } = null;

        /// <summary>
        /// Gets or sets the order by clause.
        /// </summary>
        public string? OrderBy { get; set; } = null;

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
        private string? _orderby;
        private string? _filter;

        /// <summary>
        /// Sets the $top and $skip clauses using the page information.
        /// </summary>
        /// <param name="pageNumber">Page number to request</param>
        /// <param name="pageNumber">Page size to request</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $top and $skip clauses set</returns>
        public ODataQueryParametersBuilder Page(int pageNumber, int pageSize)
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
        public ODataQueryParametersBuilder Filter(List<FilterDescriptor> filterDescriptors)
        {
            _filter = ODataUtils.Translate(filterDescriptors);

            return this;
        }

        /// <summary>
        /// Sets the $orderby clause.
        /// </summary>
        /// <param name="columns">List of Columns to sort by</param>
        /// <returns>The <see cref="ODataQueryParametersBuilder"/> with the $orderby clause set</returns>
        public ODataQueryParametersBuilder OrderBy(List<SortColumn> columns)
        {
            _orderby = GetOrderByColumns(columns);

            return this;
        }

        /// <summary>
        /// Translates the given <paramref name="columns"/> to OData string.
        /// </summary>
        /// <param name="columns">Columns to convert into the OData $orderby string</param>
        /// <returns>The $orderby clause from the given columns</returns>
        private string GetOrderByColumns(List<SortColumn> columns)
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
                OrderBy = _orderby,
                Filter = _filter,
            };
        }
    }
}
```

## Using the Kiota ApiClient in Blazor ##

We have a FluentUI DataGrid, that should display all User Tasks, so we start by injecting the `ApiClient` 
using the `@inject` directive like this:

```razor
@inject ApiClient ApiClient
```

The Razor Page `UserTasksDataGrid.razor` now looks like this:

```razor
@page "/UserTasks"

<!-- ... -->

@inject ApiClient ApiClient

<PageTitle>User Tasks</PageTitle>

<h1>User Tasks</h1>

<FluentDataGrid @ref="DataGrid" ItemsProvider="@UserTasksProvider" Pagination="@Pagination" TGridItem=UserTask>
    <PropertyColumn Title="Customer ID" Property="@(c => c!.Id)" Sortable="true" Align=Align.Start>
        <ColumnOptions>
            <NumericFilter TItem="int" PropertyName="Id" FilterState="FilterState"></NumericFilter>
        </ColumnOptions>
    </PropertyColumn>
    <!-- ... -->
</FluentDataGrid>
```

In the Code-Behind `UserTasksDataGrid.razor.cs` we can then use the `ApiClient` to get the UserTasks, you 
can see how the `ODataQueryParameters` are built and passed to the `ApiClient` Request. Event without 
knowing the details, it's very readable.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Blazor.Pages
{
    public partial class UserTasksDataGrid
    {
        
        // ...

        private async Task<UserTaskCollectionResponse?> GetUserTasks(GridItemsProviderRequest<UserTask> request)
        {
            // Extract all Sort Columns from the Blazor FluentUI DataGrid
            var sortColumns = DataGridUtils.GetSortColumns(request);

            // Extract all Filters from the Blazor FluentUI DataGrid
            var filters = FilterState.Filters.Values.ToList();

            // Build the ODataQueryParameters using the ODataQueryParametersBuilder
            var parameters = ODataQueryParameters.Builder
                .Page(Pagination.CurrentPageIndex + 1, Pagination.ItemsPerPage)
                .Filter(filters)
                .OrderBy(sortColumns)
                .Build();

            // Get the Data using the ApiClient from the SDK
            return await ApiClient.Odata.UserTasks.GetAsync(request =>
            {
                request.QueryParameters.Count = true;
                request.QueryParameters.Top = parameters.Top;
                request.QueryParameters.Skip = parameters.Skip;

                if(!string.IsNullOrWhiteSpace(parameters.Filter))
                {
                    request.QueryParameters.Filter = parameters.Filter;
                }

                if (!string.IsNullOrWhiteSpace(parameters.OrderBy))
                {
                    request.QueryParameters.Orderby = new[] { parameters.OrderBy };
                }
            });    
        }
    }
}
```


This method will be called by `GridItemsProvider<UserTask>` required for the FluentUI DataGrid, 
and as you can see, it's very easy to work with the results. The `GetODataCount(...)` is an 
extension method used to extract metadata from the response:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Blazor.Pages
{
    public partial class UserTasksDataGrid
    {
        
        // ...

        protected override Task OnInitializedAsync()
        {
            UserTasksProvider = async request =>
            {
                var response = await GetUserTasks(request);

                if(response == null)
                {
                    return GridItemsProviderResult.From(items: new List<UserTask>(), totalItemCount: 0);
                }

                var entities = response.Value;

                if (entities == null)
                {
                    return GridItemsProviderResult.From(items: new List<UserTask>(), totalItemCount: 0);
                }

                int count = response.GetODataCount();

                return GridItemsProviderResult.From(items: entities, totalItemCount: count);
            };
            
            return base.OnInitializedAsync();
        }
        
    // ...
    
    }
}
```

## Conclusion ##

And that's it! 

We have successfully used `Microsoft.OpenApi.OData` to build an OpenAPI document, which has been consumed by 
the Kiota command line tool to generate a C\# client. This C\# client has been integrated into a Blazor 
application.

All in all... I like this setup a lot!

## Next steps ##

[Get kiota](https://aka.ms/get/kiota) and try it for yourself! It also features commands to search for public APIs we did not explore this time. Provides filtering capabilities when generating the client, and supports many languages!
