title: Implementing a Code Search: A Frontend with ASP.NET Core Blazor (Part 3)
date: 2023-07-23 08:15
tags: aspnetcore, csharp, blazor
category: blazor
slug: elasticsearch_code_search_part3_frontend_blazor
author: Philipp Wagner
summary: This article shows how to write a Search Engine Frontend using ASP.NET Core Blazor.

In the previous two articles we have written a Backend (Part 1) and a Git Indexer for a Code Search (Part 2). What's 
left is a Frontend for searching and displaying results. We are going to use ASP.NET Core Blazor for it, because it 
enables us to share code and avoid the JavaScript ecosysten.

All code in this article can be found at:

* [https://codeberg.org/bytefish/ElasticsearchCodeSearch](https://codeberg.org/bytefish/ElasticsearchCodeSearch)

## Table of contents ##

[TOC]

## What we are going to build ##

The final result is a Search Engine, that allows us to search for code and sort the results by name, date and 
other fields. The idea is to index all repositories of an owner, such as Microsoft, and search code through 
their repositories.

There is going to be a Search Cluster Overview to see what our Elasticsearch Cluster is currently doing:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Home_Light.jpg">
        <img src="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Home_Light.jpg" alt="Home Overview for the Code Search Engine">
    </a>
</div>

... and also in Dark Mode:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Home_Dark.jpg">
        <img src="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Home_Dark.jpg" alt="Home Overview for the Code Search Engine as Dark Mode">
    </a>
</div>

And then there is the Search Page, which is used to search for code:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Search_Light.jpg">
        <img src="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Search_Light.jpg" alt="Home Overview for the Code Search Engine as Dark Mode">
    </a>
</div>

... which can also be used in Dark Mode:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Search_Dark.jpg">
        <img src="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch_Search_Dark.jpg" alt="Home Overview for the Code Search Engine as Dark Mode">
    </a>
</div>

## ElasticsearchCodeSearchService ##

Something could go wrong when calling the Backend, so we are adding an `ApiException` first:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Net;
using System.Runtime.Serialization;

namespace ElasticsearchCodeSearch.Shared.Exceptions
{
    [Serializable]
    public class ApiException : Exception
    {
        public ApiException()
        {
        }

        public ApiException(string? message) : base(message)
        {
        }

        public ApiException(string? message, Exception? innerException) : base(message, innerException)
        {
        }

        protected ApiException(SerializationInfo info, StreamingContext context) : base(info, context)
        {
        }

        /// <summary>
        /// Http status code.
        /// </summary>
        public required HttpStatusCode StatusCode { get; set; }
    }
}
```

And then we can write the `ElasticsearchCodeSearchService`, by using the JSON extension methods 
of the `HttpClient` it's very easy to serialize and deserialize the data. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace ElasticsearchCodeSearch.Shared.Services
{
    public class ElasticsearchCodeSearchService
    {
        private readonly ILogger<ElasticsearchCodeSearchService> _logger;
        private readonly HttpClient _httpClient;

        public ElasticsearchCodeSearchService(ILogger<ElasticsearchCodeSearchService> logger, HttpClient httpClient)
        {
            _httpClient = httpClient;
            _logger = logger;
        }

        public async Task<CodeSearchResultsDto?> QueryAsync(CodeSearchRequestDto codeSearchRequestDto, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var response = await _httpClient
                .PostAsJsonAsync("search-documents", codeSearchRequestDto, cancellationToken)
                .ConfigureAwait(false);

            if (!response.IsSuccessStatusCode)
            {
                throw new ApiException(string.Format(CultureInfo.InvariantCulture,
                    "HTTP Request failed with Status: '{0}' ({1})",
                    (int)response.StatusCode,
                    response.StatusCode))
                {
                    StatusCode = response.StatusCode
                };
            }

            return await response.Content
                .ReadFromJsonAsync<CodeSearchResultsDto>(cancellationToken: cancellationToken)
                .ConfigureAwait(false);
        }

        public async Task<List<CodeSearchStatisticsDto>?> SearchStatisticsAsync(CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var response = await _httpClient
                .GetAsync("search-statistics", cancellationToken)
                .ConfigureAwait(false);

            if (!response.IsSuccessStatusCode)
            {
                throw new ApiException(string.Format(CultureInfo.InvariantCulture,
                    "HTTP Request failed with Status: '{0}' ({1})",
                    (int)response.StatusCode,
                    response.StatusCode))
                {
                    StatusCode = response.StatusCode
                };
            }

            return await response.Content
                .ReadFromJsonAsync<List<CodeSearchStatisticsDto>>(cancellationToken: cancellationToken)
                .ConfigureAwait(false);
        }
    }
}
```

The `ElasticsearchCodeSearchService` also needs to be added to the Dependency Injection container 
using the `IServiceCollection#AddHttpClient` extension.

```csharp
builder.Services.AddHttpClient<ElasticsearchCodeSearchService>((services, client) =>
{
    client.BaseAddress = new Uri(builder.Configuration["ElasticsearchCodeSearchApi:BaseAddress"]!);
});
```

We add the base address of the service to `wwwroot/appsettings.json`.

```json
{
  "ElasticsearchCodeSearchApi": {
    "BaseAddress": "http://localhost:5000"
  }
}
```

And that's it. Everything else gets wired up automagically.


## Components ##

### SortOptionsSelector ###

The user is allowed to sort the results by the Owner, Repository and the latest commit date. We will 
put this into a `SortOptionEnum`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticsearchCodeSearch.Client.Models
{
    /// <summary>
    /// Sort Options for sorting search results.
    /// </summary>
    public enum SortOptionEnum
    {
        /// <summary>
        /// Sorts by Owner in ascending order.
        /// </summary>
        OwnerAscending = 1,

        /// <summary>
        /// Sorts by Owner in descending order.
        /// </summary>
        OwnerDescending = 2,

        /// <summary>
        /// Sorts by Repository in ascending order.
        /// </summary>
        RepositoryAscending = 3,

        /// <summary>
        /// Sorts by Respository in ascending order.
        /// </summary>
        RepositoryDescending = 4,

        /// <summary>
        /// Sorts by Latest Commit Date in ascending order.
        /// </summary>
        LatestCommitDateAscending = 5,

        /// <summary>
        /// Sorts by Latest Commit Date in descending order.
        /// </summary>
        LatestCommitDateDescending = 6,
    }
}
```

We want a simple way to translate an enumeration, so we add an extension method `TranslateEnum` to 
the `IStringLocalizer` interface.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Extensions.Localization;

namespace ElasticsearchCodeSearch.Client.Infrastructure
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

The Razor part now uses a `FluentSelect` to bind to the enumeration and notify consumers.

```razor
@using ElasticsearchCodeSearch.Client.Infrastructure;
@using ElasticsearchCodeSearch.Client.Models;
@using Microsoft.Fast.Components.FluentUI.Utilities;

@inherits FluentComponentBase
<FluentSelect @attributes="AdditionalAttributes" class="@Class" style="@Style"
              Id="@Id"
              Title="@Title"
              Disabled="@Disabled"
              Items="@SortOptions"
              OptionText="@(i => Loc.TranslateEnum(i))"
              OptionValue="@(i => i.ToString())"
              TOption=SortOptionEnum
              Value=@_value
              SelectedOption=@_sortOption
              SelectedOptionChanged="OnSelectedValueChanged">
</FluentSelect>
```

The Code-Behind is merely used for passing Parameters and Event-Handling.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Client.Localization;
using ElasticsearchCodeSearch.Client.Models;
using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;

namespace ElasticsearchCodeSearch.Client.Components
{
    public partial class SortOptionSelector
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
        /// All selectable Sort Options.
        /// </summary>
        [Parameter]
        public required SortOptionEnum[] SortOptions { get; set; }

        /// <summary>
        /// The Sort Option.
        /// </summary>
        [Parameter]
        public SortOptionEnum SortOption { get; set; }

        /// <summary>
        /// Invoked, when the SortOption has changed.
        /// </summary>
        [Parameter]
        public EventCallback<SortOptionEnum> SortOptionChanged { get; set; }

        /// <summary>
        /// Value.
        /// </summary>
        string? _value { get; set; }

        /// <summary>
        /// Filter Operator.
        /// </summary>
        private SortOptionEnum _sortOption { get; set; }

        protected override void OnParametersSet()
        {
            _sortOption = SortOption;
            _value = SortOption.ToString();
        }

        public void OnSelectedValueChanged(SortOptionEnum value)
        {
            _sortOption = value;
            _value = value.ToString();

            SortOptionChanged.InvokeAsync(_sortOption);
        }
    }
}
```

### SearchResult ###

In my mind I wanted to look the code box with the highlighted lines like this:

A `code-box` has a `code-box-title` and a `code-box-content`. In the `code-box-content` 
we have a list of `code-line`, where each `code-line` consists of a `code-line-number` 
on the left and the `code-line-content` on the right. 

We start with the Razor part in `Components/SearchResult/SearchResult.razor`.

```razor
@using ElasticsearchCodeSearch.Client.Extensions;
@using ElasticsearchCodeSearch.Shared.Dto;

<div class="code-box">
    <div class="code-box-title">
        <strong>@Item.Owner/@Item.Repository</strong> - <a href="@Item.Permalink">@Item.Path</a> - (Updated at @Item.LatestCommitDate.ToString("g"))
    </div>
    <div class="code-box-content">
        @foreach (var line in @Item.Content)
        {
            <div class="code-line @codeLineClass(line)">
                <div class="code-line-number">
                    <div>
                        <span class="noselect">@line.LineNo</span>
                    </div>
                </div>
                <div class="code-line-content">
                    @line.Content
                </div>
            </div>
        }
    </div>
</div>

@code {
    /// <summary>
    /// Determines the classes to add for the Line.
    /// </summary>
    /// <param name="highlightedContent">Highlighted Content</param>
    /// <returns></returns>
    string codeLineClass(HighlightedContentDto highlightedContent) => highlightedContent.IsHighlight ? "highlighted-line" : string.Empty;

    /// <summary>
    /// Filename.
    /// </summary>
    [Parameter]
    public required CodeSearchResultDto Item { get; set; }
}
```

And we add the styling for the `.code-box` in `Components/SearchResult/SearchResult.razor.css`. I love CSS Grids for finally 
enabling CSS *dilletantes* like me to style components. Once I understood CSS Grids it was so easy to 
implement the code box.

```css
.code-box {
    display: grid;
    grid-template-rows: auto 1fr auto;
    grid-template-columns: 1fr;
    grid-template-areas:
        "code-box-title"
        "code-box-content";
    border: 1px solid var(--neutral-foreground-rest);
    background-color: var(--neutral-layer-1);
}


    .code-box .code-box-title {
        grid-area: code-box-title;
        background-color: var(--neutral-layer-4);
        border-bottom: 1px solid var(--neutral-foreground-rest);
        padding: 10px 16px;
    }

    .code-box .code-box-content {
        display: grid;
        grid-area: code-box-content;
        grid-template-columns: 1fr;
        overflow: auto;
        white-space: nowrap;
        color: var(--neutral-foreground-rest);
        font-family: "JetBrains Mono","Menlo","DejaVu Sans Mono","Liberation Mono","Consolas","Ubuntu Mono","Courier New","andale mono","lucida console",monospace;
    }

        .code-box .code-box-content .highlighted-line {
            background-color: #f8eec7ab !important;
        }

        .code-box .code-box-content .code-line {
            display: grid;
            grid-template-columns: auto 1fr;
        }

            .code-box .code-box-content .code-line .code-line-number {
                display: grid;
                text-align: right;
                padding-right: 0.5rem;
                border-right: 1px solid var(--neutral-foreground-rest);
                min-width: 4rem;
            }

            .code-box .code-box-content .code-line .code-line-content {
                display: grid;
                text-align: left;
            }

.noselect {
    -webkit-touch-callout: none; /* iOS Safari */
    -webkit-user-select: none; /* Safari */
    -moz-user-select: none; /* Old versions of Firefox */
    -ms-user-select: none; /* Internet Explorer/Edge */
    user-select: none; /* Non-prefixed version, currently supported by Chrome, Edge, Opera and Firefox */
}
```

### Paginator ###

The Paginator has a `PaginatorState` used to hold the current page and page size:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Client.Infrastructure;

namespace ElasticsearchCodeSearch.Client.Components
{
    /// <summary>
    /// Holds state to represent pagination in a <see cref="FluentDataGrid{TGridItem}"/>.
    /// </summary>
    public class PaginatorState
    {
        /// <summary>
        /// Gets or sets the number of items on each page.
        /// </summary>
        public int ItemsPerPage { get; set; } = 10;

        /// <summary>
        /// Gets the current zero-based page index. To set it, call <see cref="SetCurrentPageIndexAsync(int)" />.
        /// </summary>
        public int CurrentPageIndex { get; set; }

        /// <summary>
        /// Gets the total number of items across all pages, if known. The value will be null until an
        /// associated component assigns a value after loading data.
        /// </summary>
        public int? TotalItemCount { get; set; }

        /// <summary>
        /// Gets the zero-based index of the last page, if known. The value will be null until <see cref="TotalItemCount"/> is known.
        /// </summary>
        public int? LastPageIndex => (TotalItemCount - 1) / ItemsPerPage;

        /// <summary>
        /// An event that is raised when the total item count has changed.
        /// </summary>
        public event EventHandler<int?>? TotalItemCountChanged;

        internal EventCallbackSubscribable<PaginatorState> CurrentPageItemsChanged { get; } = new();

        internal EventCallbackSubscribable<PaginatorState> TotalItemCountChangedSubscribable { get; } = new();

        /// <inheritdoc />
        public override int GetHashCode()
            => HashCode.Combine(ItemsPerPage, CurrentPageIndex, TotalItemCount);

        /// <summary>
        /// Sets the current page index, and notifies any associated <see cref="FluentDataGrid{TGridItem}"/>
        /// to fetch and render updated data.
        /// </summary>
        /// <param name="pageIndex">The new, zero-based page index.</param>
        /// <returns>A <see cref="Task"/> representing the completion of the operation.</returns>
        public Task SetCurrentPageIndexAsync(int pageIndex)
        {
            CurrentPageIndex = pageIndex;
            return CurrentPageItemsChanged.InvokeCallbacksAsync(this);
        }

        // Can be internal because this only needs to be called by FluentDataGrid itself, not any custom pagination UI components.
        public Task SetTotalItemCountAsync(int totalItemCount)
        {
            if (totalItemCount == TotalItemCount)
            {
                return Task.CompletedTask;
            }

            TotalItemCount = totalItemCount;

            if (CurrentPageIndex > 0 && CurrentPageIndex > LastPageIndex)
            {
                // If the number of items has reduced such that the current page index is no longer valid, move
                // automatically to the final valid page index and trigger a further data load.
                return SetCurrentPageIndexAsync(LastPageIndex.Value);
            }
            else
            {
                // Under normal circumstances, we just want any associated pagination UI to update
                TotalItemCountChanged?.Invoke(this, TotalItemCount);

                return TotalItemCountChangedSubscribable.InvokeCallbacksAsync(this);
            }
        }
    }
}
```

In `Components/Pagination/Paginator.razor` we define the user interface:

```razor
@inherits FluentComponentBase
<div class="paginator">
    @if (State.TotalItemCount.HasValue)
    {
        <nav role="navigation" class="paginator-nav">
            <FluentButton @onclick="GoFirstAsync" Disabled="@(!CanGoBack)" title="Go to first page" aria-label="Go to first page">
                <FluentIcon Name="@FluentIcons.ChevronDoubleLeft" Size="IconSize.Size20" />
            </FluentButton>
            <FluentButton @onclick="GoPreviousAsync" Disabled="@(!CanGoBack)" title="Go to previous page" aria-label="Go to previous page">
                <FluentIcon Name="@FluentIcons.ChevronLeft" Size="IconSize.Size20" />
            </FluentButton>
            <div class="pagination-text">
                Page <strong>@(State.CurrentPageIndex + 1)</strong>
                of <strong>@(State.LastPageIndex + 1)</strong>
            </div>
            <FluentButton @onclick="GoNextAsync" Disabled="@(!CanGoForwards)" title="Go to next page" aria-label="Go to next page">
                <FluentIcon Name="@FluentIcons.ChevronRight" Size="IconSize.Size20" />
            </FluentButton>
            <FluentButton @onclick="GoLastAsync" Disabled="@(!CanGoForwards)" title="Go to last page" aria-label="Go to last page">
                <FluentIcon Name="@FluentIcons.ChevronDoubleRight" Size="IconSize.Size20" />
            </FluentButton>
        </nav>
    }
</div>
```

The Code-Behind in `Components/Pagination/Paginator.razor.cs` interacts only with `PaginatorState` to react 
on changes to the `PaginatorState` and perform state changes through the `PaginatorState`. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Client.Infrastructure;
using Microsoft.AspNetCore.Components;
using Microsoft.Fast.Components.FluentUI;

namespace ElasticsearchCodeSearch.Client.Components
{

    /// <summary>
    /// A component that provides a user interface for <see cref="PaginatorState"/>.
    /// </summary>
    public partial class Paginator : FluentComponentBase, IDisposable
    {
        private readonly EventCallbackSubscriber<PaginatorState> _totalItemCountChanged;

        /// <summary>
        /// Specifies the associated <see cref="PaginatorState"/>. This parameter is required.
        /// </summary>
        [Parameter, EditorRequired] public PaginatorState State { get; set; } = default!;

        /// <summary>
        /// Optionally supplies a template for rendering the page count summary.
        /// </summary>
        [Parameter] public RenderFragment? SummaryTemplate { get; set; }

        /// <summary>
        /// Constructs an instance of <see cref="FluentPaginator" />.
        /// </summary>
        public Paginator()
        {
            // The "total item count" handler doesn't need to do anything except cause this component to re-render
            _totalItemCountChanged = new(new EventCallback<PaginatorState>(this, null));
        }

        private Task GoFirstAsync() => GoToPageAsync(0);
        private Task GoPreviousAsync() => GoToPageAsync(State.CurrentPageIndex - 1);
        private Task GoNextAsync() => GoToPageAsync(State.CurrentPageIndex + 1);
        private Task GoLastAsync() => GoToPageAsync(State.LastPageIndex.GetValueOrDefault(0));

        private bool CanGoBack => State.CurrentPageIndex > 0;
        private bool CanGoForwards => State.CurrentPageIndex < State.LastPageIndex;

        private Task GoToPageAsync(int pageIndex)
            => State.SetCurrentPageIndexAsync(pageIndex);

        /// <inheritdoc />
        protected override void OnParametersSet()
            => _totalItemCountChanged.SubscribeOrMove(State.TotalItemCountChangedSubscribable);

        /// <inheritdoc />
        public void Dispose()
            => _totalItemCountChanged.Dispose();
    }
}
```

The styling in `Components/Pagination/Paginator.razor.css` is short and the styles for the Fluent UI 
buttons get automatically applied:

```css
.paginator {
    display: flex;
    margin-top: 0.5rem;
    padding: 0.25rem 0;
    align-items: center;
}

.paginator-nav {
    padding: 0;
    display: flex;
    gap: 0.5rem;
    align-items: center;
    background-color: var(--neutral-layer-1);
}
```

## Pages ##

### Search Cluster Overview ###

The `CodeSearchStatisticsDto` comes with many properties, that contain the Elasticsearch properties:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

//...

namespace ElasticsearchCodeSearch.Shared.Dto
{
    public class CodeSearchStatisticsDto
    {
        /// <summary>
        /// Index Name.
        /// </summary>
        [JsonPropertyName("indexName")]
        public required string IndexName { get; set; }

        /// <summary>
        /// Total Index Size in bytes (indices.store.size_in_bytes).
        /// </summary>
        [JsonPropertyName("indexSizeInBytes")]
        public required long? IndexSizeInBytes { get; set; }

        // ...
    }
}
```

We want to display the data in a `FluentDataGrid`, so we start by flattening results into a 
list of `ElasticsearchMetric`, that contain a name, the original key and a (formatted) value.


```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticsearchCodeSearch.Client.Models
{
    public class ElasticsearchMetric
    {
        /// <summary>
        /// Name.
        /// </summary>
        public required string Name { get; set; }

        /// <summary>
        /// Elasticsearch Key.
        /// </summary>
        public required string Key { get; set; }

        /// <summary>
        /// Value.
        /// </summary>
        public required string? Value { get; set; }
    }
}
```

The `ElasticsearchIndexMetrics` is going to add the index name.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticsearchCodeSearch.Client.Models
{
    public class ElasticsearchIndexMetrics
    {
        /// <summary>
        /// Index.
        /// </summary>
        public required string Index { get; set; }

        /// <summary>
        /// Value.
        /// </summary>
        public required List<ElasticsearchMetric> Metrics { get; set; }
    }
}
```

The idea is to display the metrics for all indices, that 

```csharp
@using ElasticsearchCodeSearch.Client.Infrastructure;
@page "/"

<PageTitle>Search Cluster Overview</PageTitle>

<h1>Search Cluster Overview</h1>

<p>
    This page gives you an overview for all indices in your Elasticsearch cluster.
</p>

@foreach (var indexMetric in _elasticsearchIndexMetrics)
{
    <h2>Index "@indexMetric.Index"</h2>

    <FluentDataGrid Items="@indexMetric?.Metrics.AsQueryable()" ResizableColumns=true style="height: 500px; overflow:auto;">
        <PropertyColumn Title="Metric" Property="@(c => c.Name)" Sortable="true" Align="Align.Start" />
        <PropertyColumn Title="Value" Property="@(c => c.Value)" Sortable="true" Align="Align.Start" />
    </FluentDataGrid>
}
```

In the Code-Behind we now query the `search-statistics` endpoint to get a list of `CodeSearchStatisticsDto` and massage 
them into the `ElasticsearchIndexMetrics`.
`

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Client.Infrastructure;
using ElasticsearchCodeSearch.Client.Localization;
using ElasticsearchCodeSearch.Client.Models;
using ElasticsearchCodeSearch.Shared.Dto;
using ElasticsearchCodeSearch.Shared.Services;
using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;

namespace ElasticsearchCodeSearch.Client.Pages
{
    public partial class Index
    {
        /// <summary>
        /// Elasticsearch Search Client.
        /// </summary>
        [Inject]
        public ElasticsearchCodeSearchService ElasticsearchCodeSearchService { get; set; } = default!;

        /// <summary>
        /// Shared String Localizer.
        /// </summary>
        [Inject]
        public IStringLocalizer<SharedResource> Loc { get; set; } = default!;

        /// <summary>
        /// Search Statistics.
        /// </summary>
        private List<ElasticsearchIndexMetrics> _elasticsearchIndexMetrics = new List<ElasticsearchIndexMetrics>();

        protected override async Task OnInitializedAsync()
        {
            var codeSearchStatistics = await ElasticsearchCodeSearchService.SearchStatisticsAsync(default);

            _elasticsearchIndexMetrics = ConvertToElasticsearchIndexMetric(codeSearchStatistics);
        }

        private List<ElasticsearchIndexMetrics> ConvertToElasticsearchIndexMetric(List<CodeSearchStatisticsDto>? codeSearchStatistics)
        {
            if(codeSearchStatistics == null)
            {
                return new List<ElasticsearchIndexMetrics>();
            }

            return codeSearchStatistics
                .Select(x => new ElasticsearchIndexMetrics
                {
                    Index = x.IndexName,
                    Metrics = ConvertToElasticsearchMetrics(x)
                })
                .ToList();

        }

        private List<ElasticsearchMetric> ConvertToElasticsearchMetrics(CodeSearchStatisticsDto codeSearchStatistic)
        {
            return new List<ElasticsearchMetric>()
            {
                new ElasticsearchMetric
                {
                    Name = Loc["Metrics_IndexSize"],
                    Key = "indices.store.size_in_bytes",
                    Value = DataSizeUtils.TotalMegabytesString(codeSearchStatistic.IndexSizeInBytes ?? 0)
                },
                new ElasticsearchMetric
                {
                    Name = Loc["Metrics_TotalNumberOfDocumentsIndexed"],
                    Key = "indices.docs.count",
                    Value = codeSearchStatistic.TotalNumberOfDocumentsIndexed?.ToString()
                },
                // ...
            };
        }
    }
}
```

And that's it.

### Search Page ###

The Search Page contains the search box, the search results, and a paginator. That's 
all we need for now. I *think* you could divide the page into more components, so 
feel free to make a PR!

```razor
@page "/Search"

@using ElasticsearchCodeSearch.Client.Components
@using ElasticsearchCodeSearch.Client.Extensions;
@using ElasticsearchCodeSearch.Client.Infrastructure;
@using ElasticsearchCodeSearch.Shared.Dto;

<PageTitle>Elasticsearch Code Search Experiments</PageTitle>

<div class="search-container">
    <div class="search-header">

        <div class="search-box">
            <FluentSearch @bind-Value="_queryString" @onkeyup="@EnterSubmit" Class="w-100" />
            <FluentButton @onclick=@QueryAsync>Search</FluentButton>
            <SortOptionSelector SortOptions="_sortOptions" @bind-SortOption="_selectedSortOption">
            </SortOptionSelector>
        </div>
    </div>
    <div class="search-results-total">
        <span>@_totalItemCount Results (@_tookInSeconds seconds)</span>
    </div>
    <div class="search-results">
        @foreach (var searchResult in _codeSearchResults)
        {
            <SearchResult Item="@searchResult"></SearchResult>
        }
    </div>
    <div class="search-paginator">
        <Paginator State="@_pagination"></Paginator>
    </div>
</div>
```

In the Code Behind `Pages/Search.razor.cs` we inject the `ElasticsearchCodeSearchService` to query the search 
service and wire up the Fluent UI components. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Client.Infrastructure;
using ElasticsearchCodeSearch.Shared.Dto;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components;
using ElasticsearchCodeSearch.Shared.Services;
using ElasticsearchCodeSearch.Client.Components;
using ElasticsearchCodeSearch.Client.Models;

namespace ElasticsearchCodeSearch.Client.Pages
{
    public partial class Search : IAsyncDisposable
    {
        /// <summary>
        /// Elasticsearch Search Client.
        /// </summary>
        [Inject]
        public ElasticsearchCodeSearchService ElasticsearchCodeSearchService { get; set; } = default!;

        /// <summary>
        /// The current Query String to send to the Server (Elasticsearch QueryString format).
        /// </summary>
        [Parameter]
        public string? QueryString { get; set; }

        /// <summary>
        /// The Selected Sort Option:
        /// </summary>
        [Parameter]
        public SortOptionEnum? SortOption { get; set; }

        /// <summary>
        /// Page Number.
        /// </summary>
        [Parameter]
        public int? Page { get; set; }

        /// <summary>
        /// Page Number.
        /// </summary>
        [Parameter]
        public int? PageSize { get; set; }

        /// <summary>
        /// Pagination.
        /// </summary>
        private PaginatorState _pagination = new PaginatorState
        {
            ItemsPerPage = 10,
            TotalItemCount = 10
        };

        /// <summary>
        /// Reacts on Paginator Changes.
        /// </summary>
        private readonly EventCallbackSubscriber<PaginatorState> _currentPageItemsChanged;

        /// <summary>
        /// Sort Options for all available fields.
        /// </summary>
        private static readonly SortOptionEnum[] _sortOptions = new[]
        {
            SortOptionEnum.OwnerAscending,
            SortOptionEnum.OwnerDescending,
            SortOptionEnum.RepositoryAscending,
            SortOptionEnum.RepositoryDescending,
            SortOptionEnum.LatestCommitDateAscending,
            SortOptionEnum.LatestCommitDateDescending,
        };

        /// <summary>
        /// The currently selected Sort Option
        /// </summary>
        private SortOptionEnum _selectedSortOption { get; set; }
        
        /// <summary>
        /// When loading data, we need to cancel previous requests.
        /// </summary>
        private CancellationTokenSource? _pendingDataLoadCancellationTokenSource;

        /// <summary>
        /// Search Results for a given query.
        /// </summary>
        private List<CodeSearchResultDto> _codeSearchResults { get; set; } = new List<CodeSearchResultDto>();

        /// <summary>
        /// The current Query String to send to the Server (Elasticsearch QueryString format).
        /// </summary>
        private string _queryString { get; set; } = string.Empty;

        /// <summary>
        /// Total Item Count.
        /// </summary>
        private int _totalItemCount { get; set; } = 0;

        /// <summary>
        /// Processing Time.
        /// </summary>
        private decimal _tookInSeconds { get; set; } = 0;

        public Search()
        {
            _currentPageItemsChanged = new(EventCallback.Factory.Create<PaginatorState>(this, QueryAsync));
        }

        /// <inheritdoc />
        protected override Task OnParametersSetAsync()
        {
            // Set bound values, so we don't modify the parameters directly
            _queryString = QueryString ?? string.Empty;
            _selectedSortOption = SortOption ?? SortOptionEnum.LatestCommitDateDescending;
            _pagination.CurrentPageIndex = Page ?? 0;
            _pagination.ItemsPerPage = PageSize ?? 10;

            // The associated pagination state may have been added/removed/replaced
            _currentPageItemsChanged.SubscribeOrMove(_pagination.CurrentPageItemsChanged);

            return Task.CompletedTask;
        }

        /// <summary>
        /// Queries the Backend and cancels all pending requests.
        /// </summary>
        /// <returns>An awaitable task</returns>
        public async Task QueryAsync()
        {
            // Do not execute empty queries ...
            if(string.IsNullOrWhiteSpace(_queryString))
            {
                return;
            }

            try
            {
                // Cancel all Pending Search Requests
                _pendingDataLoadCancellationTokenSource?.Cancel();

                // Initialize the new CancellationTokenSource
                var loadingCts = _pendingDataLoadCancellationTokenSource = new CancellationTokenSource();

                // Get From and Size for Pagination:
                var from = _pagination.CurrentPageIndex * _pagination.ItemsPerPage;
                var size = _pagination.ItemsPerPage;

                // Get the Sort Field to Sort results for
                var sortField = GetSortField(_selectedSortOption);

                // Construct the Request
                var searchRequestDto = new CodeSearchRequestDto
                {
                    Query = _queryString,
                    From = from,
                    Size = size,
                    Sort = new List<SortFieldDto>() { sortField }
                };

                // Query the API
                var results = await ElasticsearchCodeSearchService.QueryAsync(searchRequestDto, loadingCts.Token);

                if (results == null)
                {
                    return; // TODO Show Error ...
                }

                // Set the Search Results:
                _codeSearchResults = results.Results;
                _tookInSeconds = results.TookInMilliseconds / (decimal) 1000;
                _totalItemCount = (int)results.Total;

                // Refresh the Pagination:
                await _pagination.SetTotalItemCountAsync(_totalItemCount);
            } 
            catch(Exception e)
            {
                // Pokemon Exception Handling for now. It should display an error and
                // indicate, why the Search has failed (Backend not reachable, ...).
            }

            StateHasChanged();
        }

        private async Task EnterSubmit(KeyboardEventArgs e)
        {
            if (e.Key == "Enter")
            {
                await QueryAsync();
            }
        }

        private static SortOptionEnum GetSortOption(string? sortOptionString, SortOptionEnum defaultValue)
        {
            if(string.IsNullOrWhiteSpace(sortOptionString))
            {
                return defaultValue;
            }

            bool success = Enum.TryParse<SortOptionEnum>(sortOptionString, true, out var parsedSortOption);

            if(!success)
            {
                return defaultValue;
            }

            return parsedSortOption;
        }

        private static SortFieldDto GetSortField(SortOptionEnum sortOptionEnum)
        {
            return sortOptionEnum switch
            {
                SortOptionEnum.OwnerAscending => new SortFieldDto() { Field = "owner", Order = SortOrderEnumDto.Asc },
                SortOptionEnum.OwnerDescending => new SortFieldDto() { Field = "owner", Order = SortOrderEnumDto.Desc },
                SortOptionEnum.RepositoryAscending => new SortFieldDto() { Field = "repository", Order = SortOrderEnumDto.Asc },
                SortOptionEnum.RepositoryDescending => new SortFieldDto() { Field = "repository", Order = SortOrderEnumDto.Desc },
                SortOptionEnum.LatestCommitDateAscending => new SortFieldDto() { Field = "latestCommitDate", Order = SortOrderEnumDto.Asc },
                SortOptionEnum.LatestCommitDateDescending => new SortFieldDto() { Field = "latestCommitDate", Order = SortOrderEnumDto.Desc },
                _ => throw new ArgumentException($"Unknown SortField '{sortOptionEnum}'"),
            };
        }

        public ValueTask DisposeAsync()
        {
            _currentPageItemsChanged.Dispose();
            
            GC.SuppressFinalize(this);

            return ValueTask.CompletedTask;
        }
    }
}
```

The CSS in `Pages/Index.razor.css` makes heavy use of the new CSS Grid features, that make it simple 
to style the page and align its content. We are going to have the `search-results` to fill up the 
content (`1fr`, all other columns `auto`).

```css
.search-container {
    display: grid;
    height: 100%;
    grid-template-rows: auto auto 1fr auto;
    grid-template-columns: 1fr;
    grid-row-gap: 10px;
    grid-template-areas:
        "search-header"
        "search-results-total"
        "search-results"
        "search-paginator"
}

.search-header {
    display: grid;
    grid-area: search-header;
    grid-template-columns: minmax(auto, 900px);
    grid-template-rows: auto 1fr;
    justify-content: center;
    padding: 1rem;
    border-bottom: 1px solid var(--neutral-foreground-rest);
}

    .search-header .search-title {
        color: black;
    }

.search-title {
    display: grid;
    justify-content: center;
}

.search-box {
    display: grid;
    min-width: 500px;
    justify-content: center;
    grid-template-columns: 1fr auto auto;
    grid-column-gap: 10px;
}

.search-results-total {
    display: grid;
    grid-area: search-results-total;
    justify-content: center;
    grid-template-columns: auto;
}

.search-results {
    display: grid;
    grid-area: search-results;
    grid-template-columns: 1fr;
    grid-auto-rows: max-content;
    max-width: 1000px;
    margin: 0 auto;
    grid-row-gap: 20px;
}

.search-paginator {
    display: grid;
    grid-area: search-paginator;
    min-width: 500px;
    justify-content: center;
    grid-template-columns: auto;
}
```


## Conclusion ##

And that's it. You can now start your Elasticsearch instance, and start the solution. It will 
automatically start the Backend and the Frontend. By indexing data through the PowerShell script 
you can fill the index with code to search for.

