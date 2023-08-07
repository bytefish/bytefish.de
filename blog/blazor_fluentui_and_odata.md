title: Implementing a Code Search: A Frontend with ASP.NET Core Blazor (Part 3)
date: 2023-07-23 08:15
tags: aspnetcore, csharp, blazor
category: blazor
slug: elasticsearch_code_search_part3_frontend_blazor
author: Philipp Wagner
summary: This article shows how to write a Search Engine Frontend using ASP.NET Core Blazor.

This repository shows how to use Blazor, Fluent UI Blazor and OData to display data 
in a Fluent UI Data Grid. It uses the WideWorldImporters Backend to provide the 
data.

All code in this article can be found at:

* [https://github.com/bytefish/ElasticsearchCodeSearch](https://github.com/bytefish/ElasticsearchCodeSearch)

## Table of contents ##

[TOC]

## What we are going to build ##

The idea is to use an ASP.NET Core OData for a Backend and a Blazor Frontend, that uses the FluentUI 
Components. FluentUI provides a nice and extensible DataGrid component, which we are going to add 
components to. The result is going to look like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

It's possible to provide filters for each column, we can for example set a filter on text:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid_ColumnFilter_String.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Customer_Grid_ColumnFilter_String.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

## The Plan ##

Everyone has a plan, and so do I.

It's obvious from my previous articles, that I really like the Blazor FluentUI component library. The library 
is actively maintained by Microsoft and it allows you to build Blazor Frontends, that looks and behaves similar 
to the Windows 11 User Interface.

A lot of applications I am working on need Data Grids and the FluentUI library contains a great Data Grid. But 
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
and sort data in a Data Grid. The Backend is an ASP.NET Core OData-based Webservice, so we have a 
powerful and standardized language to query data sets.

## Generating the Blazor WebAssembly Project ##

We are building a Blazor WebAssembly project, so we need to create it first. The Fluent UI Blazor library 
comes with a set of project templates, that do the job for us. 

Switch to a terminal and run:

```
dotnet new installMicrosoft.Fast.Templates.FluentUI.nupkg
```

Next create a Blazor WebAssembly project `BlazorDataGridExample` by running:

```
dotnet new fluentuiblazorwasm -o BlazorDataGrid
```

I then used the Demo page of Fluent UI Blazor to have a *great* looking starting point, that already 
comes with a responsive Navigation Bar and all components (such as Icons) wired up: 

* [https://github.com/microsoft/fluentui-blazor/tree/main/examples](https://github.com/microsoft/fluentui-blazor/tree/main/examples)

It's actually the 3.0.0 Preview version, but I think Fluent UI Blazor 3.0.0 will be released some time soon.

## Generating the OData Client ##

We start by creating a shared Class Library project called `BlazorDataGridExample.Shared`, which is 
going to contain the OData Client, the Filter data model and some classes to translate the filters to 
an OData query.

You don't want to handwrite an OData Client, just use the `OData Connected Service 2022+` plugin, which 
allows you to add a Connected Service and generate the Models and the OData Client:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Install_Extension.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Install_Extension.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

Right click on the `BlazorDataGridExample.Shared` and select `Add -> Connected Service`:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Add_Connected_Service.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Add_Connected_Service.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

Click on OData Connected Service in the `Other Services` section:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Add_New_Connected_Service.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Add_New_Connected_Service.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

In the Endpoint Configuration we only need to set the URL to the OData Service $metadata, which is 
`http://localhost:5000/odata/$metadata` for the WideWorldImporters OData Service:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Endpoint_Configuration.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Endpoint_Configuration.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

You can then accept all other defaults and generate the code.

This will generate the following code into you `BlazorDataGridExample.Shared` project:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Generated_Code.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/OData_Connected_Service_Generated_Code.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

Finally switch to the `BlazorDataGridExample` Blazor project and wire up the generated `Container` as a Scoped Service:

```
// OData
builder.Services.AddScoped(sp =>
{
    return new WideWorldImportersService.Container(new Uri("http://localhost:5000/odata"))
    {
        HttpRequestTransportMode = HttpRequestTransportMode.HttpClient
    };
});
```

That's it for the OData Client!

## Implementing Filtering and Sorting ##

Switch to the `BlazorDataGridExample.Shared` project and create a new Folder `Models`. This will hold the data model 
for filtering and sorting. It should be possible to filter various column types, such as a boolean, text, number, date 
or datetime types. 

### Data Model ###

That's the starting point, so add a `FilterTypeEnum`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace BlazorDataGridExample.Shared.Models
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

namespace BlazorDataGridExample.Shared.Models
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

namespace BlazorDataGridExample.Shared.Models
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
    
    // ...
    
}
```

All Filters for specific types then derive from a `FilterDescriptor` and add their required or 
optional properties.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace BlazorDataGridExample.Shared.Models
{

    // ...

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
    
    // ...
}
```

That's all there is for the Filter model. What's left is to provide a model for 
sorting, because we want to sort the Data Grid by their properties after 
all. 

Something, that's needed is a sort direction for sure.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace BlazorDataGridExample.Shared.Models
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

namespace BlazorDataGridExample.Shared.Models
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
        public required SortDirection SortDirection { get; set; }
    }
}
```

### Building the OData Query with Filtering and Sorting ###

Now that we have the various `FilterDescriptor` implementations, we need a way to convert from a 
List of `FilterDescriptor` to an OData Query String. Since we have a very narrow goal of combining 
all `FilterDescriptor` with an `and` it looks rather simple.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using BlazorDataGridExample.Shared.Models;
using System.Globalization;

namespace BlazorDataGridExample.Shared.Extensions
{
    public static class ODataUtils
    {
        public static string Translate(List<FilterDescriptor> filterDescriptors)
        {
            if(filterDescriptors.Count == 0)
            {
                return string.Empty;
            }

            List<string> filters = new();

            foreach(FilterDescriptor filterDescriptor in filterDescriptors)
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
                    return TranslateDateFilter((DateFilterDescriptor) filterDescriptor);
                case FilterTypeEnum.DateTimeFilter:
                    return TranslateDateTimeFilter((DateTimeFilterDescriptor) filterDescriptor);
                case FilterTypeEnum.StringFilter:
                    return TranslateStringFilter((StringFilterDescriptor) filterDescriptor);
                case FilterTypeEnum.NumericFilter:
                    return TranslateNumericFilter((NumericFilterDescriptor) filterDescriptor);
                default:
                    throw new ArgumentException($"Could not translate Filter Type '{filterDescriptor.FilterType}'");
                
            }
        }

        private static string TranslateBooleanFilter(BooleanFilterDescriptor filterDescriptor)
        {
            switch(filterDescriptor.FilterOperator)
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
            if(dateTimeOffset == null)
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

For Blazor we start by adding the following `PropertyGroup` to the `BlazorDataGridExample.csproj` 
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

namespace BlazorDataGridExample.Localization
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

using BlazorDataGridExample.Localization;

namespace BlazorDataGridExample.Components
{
    public partial class FilterSelector
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

namespace BlazorDataGridExample.Infrastructure
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

The Filters defined for the DataGrid need to go *somewhere*. For the lack of a better name I called 
the container a `FilterState`, which has methods to add and remove filters for a column. Please note, 
that in this model you can only assign a single `FilterDescriptor` to a column.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using BlazorDataGridExample.Infrastructure;
using BlazorDataGridExample.Shared.Models;
using Microsoft.Fast.Components.FluentUI;
using System.Collections.Concurrent;

namespace BlazorDataGridExample.Components
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
@using BlazorDataGridExample.Shared.Models;
@using BlazorDataGridExample.Infrastructure;
@using Microsoft.Fast.Components.FluentUI.Utilities;

@inherits FluentComponentBase
<FluentSelect @attributes="AdditionalAttributes" class="@Class" style="@Style"
              Id="@Id"
              Title="@Title"
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

using BlazorDataGridExample.Localization;
using BlazorDataGridExample.Shared.Models;
using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;

namespace BlazorDataGridExample.Components
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

The new FluentUI Blazor components come with a `FluentGrid`, which allows us to easily build 
responsive designs. I previously played around with a CSS Grid, but why though? We can define 
all of it with Razor Components.

A Filter Component should always look the same. It needs to have a `FilterOperatorSelector` to 
select the operation, a value and two buttons to apply or reset a filter. We end up with the 
following Razor.

```razor
@using BlazorDataGridExample.Shared.Models;
@using Microsoft.Fast.Components.FluentUI.Utilities;

@inherits FluentComponentBase

<div class="filter-container">
    <FluentGrid Justify="JustifyContent.Center">
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Filter Operator:</FluentLabel>
            <FilterOperatorSelector FilterOperators="filterOperatorOptions" @bind-FilterOperator="_filterOperator"></FilterOperatorSelector>
        </FluentGridItem>
        <FluentGridItem xs="12">
            <FluentLabel Typo="Typography.Body">Lower Value:</FluentLabel>
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

using BlazorDataGridExample.Shared.Models;
using Microsoft.AspNetCore.Components;

namespace BlazorDataGridExample.Components
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
@using BlazorDataGridExample.Shared.Models;
@using Microsoft.Fast.Components.FluentUI.Utilities;

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
handled by the `FluentNumberField` component, that's built into FluentUI Blazor. Thanks!

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using BlazorDataGridExample.Shared.Models;
using Microsoft.AspNetCore.Components;

namespace BlazorDataGridExample.Components
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
            return  _filterOperator == FilterOperatorEnum.None
                || _filterOperator == FilterOperatorEnum.IsNull 
                || _filterOperator == FilterOperatorEnum.IsNotNull;
        }

        private bool IsUpperValueDisabled()
        {
            return (_filterOperator != FilterOperatorEnum.BetweenInclusive && _filterOperator != FilterOperatorEnum.BetweenExclusive);
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
            if(!FilterState.Filters.TryGetValue(PropertyName, out var filterDescriptor))
            {
                _filterOperator = FilterOperatorEnum.None;
                _lowerValue = null;
                _upperValue = null;

                return;            
            }

            var numericFilterDescriptor = filterDescriptor as NumericFilterDescriptor;

            if(numericFilterDescriptor == null)
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

The `FluentDatePicker` is a new FluentUI component, that allows to either enter the date by hand or select it 
from a calendar view. 

`FluentDatePicker` 

```razor
@using BlazorDataGridExample.Shared.Models;
@using Microsoft.Fast.Components.FluentUI.Utilities;

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

using BlazorDataGridExample.Shared.Models;
using Microsoft.AspNetCore.Components;

namespace BlazorDataGridExample.Components
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
            return (_filterOperator != FilterOperatorEnum.BetweenInclusive && _filterOperator != FilterOperatorEnum.BetweenExclusive);
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
@using BlazorDataGridExample.Shared.Models;
@using Microsoft.Fast.Components.FluentUI.Utilities;

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

using BlazorDataGridExample.Shared.Models;
using Microsoft.AspNetCore.Components;

namespace BlazorDataGridExample.Components
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
            return (_filterOperator != FilterOperatorEnum.BetweenInclusive && _filterOperator != FilterOperatorEnum.BetweenExclusive);
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


## DataGrid ##

### Understanding the OData Client ###

We have installed the `OData Connected Service 2022+` extension and generate a Service client for 
the WideWorldImporters OData Backend. But what did we actually generate there? Let's investigate the 
parts important to us!

When adding the Connected Service we have defined the URL to the EDM Schema. The EDM Schema metadata 
contains all Entity Sets and Entity Types exposed by the ASP.NET Core OData Service. You can find 
it by navigating to `http://localhost:5000/odata/$metadata`.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Blazor_Shared_Generated_Files_Edmx_Schema.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Blazor_Shared_Generated_Files_Edmx_Schema.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

The `OData Connected Service 2022+` extension then generates all C\# entities and a `Container` from the 
given EDM Schema. A `Container` is a `Microsoft.OData.Client.DataServiceContext`, that allows us to 
execute queries against all Entity Sets and implements change tracking.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/blazor_fluentui_and_odata/Blazor_Shared_Generated_Files.jpg">
        <img src="/static/images/blog/blazor_fluentui_and_odata/Blazor_Shared_Generated_Files.jpg" alt="Final Result for the Data Grid">
    </a>
</div>

The whole concept is similar to the `DbContext`, you probably know from Entity Framework Core. You 
can access the EntitySets as Properties and all entities are automatically tracked (or not 
depending on the configuration in our dependency injection setup).

We could for example write a Grid Component, that uses the container to return *all* customers in 
a few lines of code. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace BlazorDataGridExample.Pages
{
    public partial class CustomerDataGrid
    {
        /// <summary>
        /// The <see cref="DataServiceContext"/> to access the OData Service.
        /// </summary>
        [Inject]
        public required Container Container { get; set; }

        // ...
        
        private List<Customer> GetAllCustomers()
        {
            return Container.Customers.ToList();
        }
    }
}
```

The data in the Entity Set can be huge, so it needs to be sorted and paginated at least. The cool thing 
is, that we can apply LINQ operators on the `DataServiceQuery<Customer>` (the actual thing the `Customer` 
property returns).

So to paginate the dataset and order it by the `CustomerId` we could come up with something like this:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace BlazorDataGridExample.Pages
{
    public partial class CustomerDataGrid
    {
        /// <summary>
        /// The <see cref="DataServiceContext"/> to access the OData Service.
        /// </summary>
        [Inject]
        public required Container Container { get; set; }

        // ...
        
        private List<Customer> GetCustomers(int skip, int top)
        {
            return Container.Customers
                .Skip(skip)
                .Take(top)
                .OrderBy(x => x.CustomerId)            
                .ToList();
        }
    }
}
```

With the knowledge in place we can write a class `ODataExtensions` to add some useful methods 
to the `DataServiceQuery<T>`, that simplifies working with a Data Grid.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using BlazorDataGridExample.Shared.Models;
using Microsoft.OData.Client;

namespace BlazorDataGridExample.Shared.Extensions
{
    /// <summary>
    /// OData Extensions to simplify working with a Grid in a WinUI 3 application.
    /// </summary>
    public static class ODataExtensions
    {
        /// <summary>
        /// Adds the $top and $skip clauses to the <see cref="DataServiceQuery"/> to add pagination.
        /// </summary>
        /// <remarks>
        /// The <paramref name="pageNumber"/> starts with 1.
        /// </remarks>
        /// <typeparam name="TElement">Entity to query for</typeparam>
        /// <param name="dataServiceQuery">The <see cref="DataServiceQuery"/> to modify</param>
        /// <param name="pageNumber">Page Number (starting with 1)</param>
        /// <param name="pageSize">Page size</param>
        /// <returns><see cref="DataServiceQuery"/> with Pagination</returns>
        public static DataServiceQuery<TElement> Page<TElement>(this DataServiceQuery<TElement> dataServiceQuery, int pageNumber, int pageSize)
        {
            var skip = (pageNumber - 1) * pageSize;
            var top = pageSize;

            var query = dataServiceQuery
                .Skip(skip)
                .Take(top);

            return (DataServiceQuery<TElement>) query;
        }

        /// <summary>
        /// Adds a $filter clause to a <see cref="DataServiceQuery"/>.
        /// </summary>
        /// <typeparam name="TElement">Entity to Filter</typeparam>
        /// <param name="dataServiceQuery">DataServiceQuery to add the $filter clause to</param>
        /// <param name="filters">Filters to apply</param>
        /// <returns><see cref="DataServiceQuery"/> with filtering</returns>
        public static DataServiceQuery<TElement> Filter<TElement>(this DataServiceQuery<TElement> dataServiceQuery, List<FilterDescriptor> filters)
        {
            if(filters.Count == 0)
            {
                return dataServiceQuery;
            }

            var filter = ODataUtils.Translate(filters);

            if (!string.IsNullOrWhiteSpace(filter))
            {
                dataServiceQuery = dataServiceQuery.AddQueryOption("$filter", filter);
            }

            return dataServiceQuery;
        }

        /// <summary>
        /// Adds the $orderby clause to a <see cref="DataServiceQuery"/>.
        /// </summary>
        /// <typeparam name="TElement">Entity to Query for</typeparam>
        /// <param name="dataServiceQuery">DataServiceQuery to add the $orderby clause to</param>
        /// <param name="columns">Columns to sort</param>
        /// <returns><see cref="DataServiceQuery"/> with sorting</returns>
        public static DataServiceQuery<TElement> SortBy<TElement>(this DataServiceQuery<TElement> dataServiceQuery, List<SortColumn> columns)
        {
            var sortColumns = GetOrderByColumns(columns);

            if (!string.IsNullOrWhiteSpace(sortColumns))
            {
                dataServiceQuery = dataServiceQuery.AddQueryOption("$orderby", sortColumns);
            }

            return dataServiceQuery;
        }

        /// <summary>
        /// Sorts the DataGrid by the specified column, updating the column header to reflect the current sort direction.
        /// </summary>
        /// <param name="columns">The Columns to sort.</param>
        public static string GetOrderByColumns(List<SortColumn> columns)
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
    }
}
```

You'll notice, that I raved about LINQ and somehow build the OData `$filter` and `$orderby` parameters by hand. This is 
because I want to keep it simple for the example and I am not *that* familiar with Razor to pass LINQ queries to the 
components.

### The Customer Data Grid ###

We are very close to *finally* display the FluentUI Data Grid and use our Filter components. The best place to understand 
how a FluentUI Data Grid works is the Demo pages over at:

* [https://www.fluentui-blazor.net/DataGrid](https://www.fluentui-blazor.net/DataGrid)

The idea is to use the `ItemsProvider` of the `FluentDataGrid` for providing the data to it. For Pagination we can 
use the `FluentPaginator` and pass it to the data grid. All `PropertyColumn` in FluentUI come with `ColumnOptions` 
to add components for something like filtering.

We end up with the Razor page like this. 

```razor
@page "/Customers"
@using BlazorDataGridExample.Components
@using BlazorDataGridExample.Shared.Models;
@using BlazorDataGridExample.Shared.Extensions;
@using Microsoft.OData.Client;
@using WideWorldImportersService;

@inject WideWorldImportersService.Container Container

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

There is an interesting thing to see in this example. You can also use properties of a navigation property. But you need 
to make sure, that you address the Navigation Property by using the OData syntax, by using a `/` instead of a `.` (for example 
`LastEditedByNavigation/PreferredName`).

```razor
<PropertyColumn Title="Last Edited By" Property="@(c => c!.LastEditedByNavigation!.PreferredName)" Sortable="true" Align=Align.Start>
    <ColumnOptions>
        <StringFilter PropertyName="LastEditedByNavigation/PreferredName" FilterState="FilterState"></StringFilter>
    </ColumnOptions>
</PropertyColumn>
```

In the Code-Behind we are now using the `Container` to query the data. The `ODataExtensions` are used for adding 
pagination, sorting and filtering. Some converting between `FluentUI` and our data model is done, but it's left 
out here on purpose.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using BlazorDataGridExample.Components;
using BlazorDataGridExample.Infrastructure;
using BlazorDataGridExample.Shared.Extensions;
using BlazorDataGridExample.Shared.Models;
using Microsoft.AspNetCore.Components;
using Microsoft.Fast.Components.FluentUI;
using Microsoft.OData.Client;
using WideWorldImportersService;

namespace BlazorDataGridExample.Pages
{
    public partial class CustomerDataGrid
    {
        /// <summary>
        /// The <see cref="DataServiceContext"/> to access the OData Service.
        /// </summary>
        [Inject]
        public required Container Container { get; set; }

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

        public CustomerDataGrid()
        {
            CurrentFiltersChanged = new(EventCallback.Factory.Create<FilterState>(this, RefreshData));
        }

        protected override Task OnInitializedAsync()
        {
            CustomerProvider = async request =>
            {
                var response = await GetCustomers(request);

                return GridItemsProviderResult.From(items: response.ToList(), totalItemCount: (int)response.Count);
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

        private async Task<QueryOperationResponse<Customer>> GetCustomers(GridItemsProviderRequest<Customer> request)
        {
            var sorts = DataGridUtils.GetSortColumns(request);
            var filters = FilterState.Filters.Values.ToList();

            var dataServiceQuery = GetDataServiceQuery(sorts, filters, Pagination.CurrentPageIndex, Pagination.ItemsPerPage);

            var result = await dataServiceQuery.ExecuteAsync(request.CancellationToken);

            return (QueryOperationResponse<Customer>)result;
        }

        private DataServiceQuery<Customer> GetDataServiceQuery(List<SortColumn> sortColumns, List<FilterDescriptor> filters,  int pageNumber, int pageSize)
        {
            var query = Container.Customers.Expand(x => x.LastEditedByNavigation)
                .Page(pageNumber + 1, pageSize)
                .Filter(filters)
                .SortBy(sortColumns)
                .IncludeCount(true);

            return (DataServiceQuery<Customer>)query;
        }
    }
}
```

And we are done!

## Conclusion ##

You now have a good idea how to add a powerful Data Grid to your Blazor application. It's easy to add your 
own filter components and integrate them into it. If you come up with a better API surface and extensibility 
I'd be glad to update the code.

My personal opinion is, that Microsoft is sitting on something great with Blazor FluentUI and OData. In this 
article and my previous articles on OData Authorization and Relationship-based Access Control, you see me 
trying to connect the dots.

By using OData you have a standardized and documented language. There is simply *no need* for (esoteric) 
discussions about "RESTfuly-ness" of an API and a lot of problems have been solved for you (filtering, batching, 
error models, ...). A lot of Restful APIs these days end up re-inventing an undocumented OData specification.

The `OData Connected Service 2022+` extension can be used to generate a high-quality service client. And nothing 
needs to be handwritten. I want to update the Contracts? It's as simple as a right click to refresh my Connected 
Service and I don't need to leave Visual Studio at all. 

