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

* [https://github.com/bytefish/ElasticsearchCodeSearch](https://github.com/bytefish/ElasticsearchCodeSearch)

## What we are going to build ##

The final result is a Search Engine, that allows us to search for code and sort the results by name, date and 
other fields. The idea is to index all repositories of an owner, such as Microsoft, and search code through 
their repositories.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch.jpg">
        <img src="/static/images/blog/elasticsearch_code_search_part1_backend_elasticsearch/ElasticsearchCodeSearch.jpg" alt="Final Result for the Code Search Engine">
    </a>
</div>

## Querying the Backend: ElasticsearchCodeSearchService ##

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
of the `HttpClient` it's very easy to serialize and deserialize the data. We only need a single 
method for querying, because the indexing is done by the PowerShell script of Part2.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Shared.Dto;
using ElasticsearchCodeSearch.Shared.Exceptions;
using ElasticsearchCodeSearch.Shared.Logging;
using Microsoft.Extensions.Logging;
using System.Globalization;
using System.Net.Http.Json;

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

## Pages ##

In my mind there are only 3 Components we need:

* A "Search Box" component to enter the Search Query
* A "Search Result" component to display a single search result
* A "Paginator" component to paginate the search results

I would love to know how someone versed in Blazor would divide the UI into components. My 
*feeling* is, that there need to be more components and it could be made way more losely 
coupled. Anyways!

### Search Page ###

The Search Page contains the search box, the search results, a paginator and a footer. That's 
all we need for now. I *think* you could divide the Page into more components (such as a 
`SearchBox` and `SearchResultList` component), so feel free to make a PR!

```razor
@page "/"

<PageTitle>Elasticsearch Code Search Experiments</PageTitle>

<div class="search-container">
    <div class="search-header">
        <div class="search-title">
            <h1>Elasticsearch Code Search</h1>
        </div>
        <div class="search-box">
            <FluentSearch @bind-Value="QueryString" @onkeyup="@EnterSubmit" Class="w-100" />
            <FluentButton @onclick=@QueryAsync>Search</FluentButton>
            <FluentSelect Items="@SortOptions"
                          OptionText="@(i => i.Text)"
                          OptionValue="@(i => i.Value)"
                          OptionSelected="@(i => i.Selected)"
            @bind-SelectedOption="@SelectedSortOption">
            </FluentSelect>
        </div>
    </div>
    <div class="search-results-total">
        <p>@TotalItemCount Documents found</p>
    </div>
    <div class="search-results">
        @foreach (var searchResult in CodeSearchResults)
        {
            <SearchResult Item="@searchResult"></SearchResult>
        }
    </div>
    <div class="search-paginator">
        <Paginator State="@Pagination"></Paginator>
    </div>
    <div class="search-footer">
        <span>Elasticsearch Code Search</span>
    </div>
</div>
```

In the Code Behind `Pages/Index.razor.cs` we inject the `ElasticsearchCodeSearchService` to query the search 
service and wire up the Fluent UI components. Please note, that I had to use source code of the Fluent UI 
project, because most parts of the Paginator API had been intended for `internal` use only.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Client.Infrastructure;
using ElasticsearchCodeSearch.Shared.Dto;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components;
using Microsoft.Fast.Components.FluentUI;
using ElasticsearchCodeSearch.Shared.Services;
using ElasticsearchCodeSearch.Client.Components.Pagination;

namespace ElasticsearchCodeSearch.Client.Pages
{
    public partial class Index : IAsyncDisposable
    {
        /// <summary>
        /// Elasticsearch Search Client.
        /// </summary>
        [Inject]
        public ElasticsearchCodeSearchService ElasticsearchCodeSearchService { get; set; } = default!;

        /// <summary>
        /// Pagination.
        /// </summary>
        private readonly PaginatorState Pagination = new PaginatorState { ItemsPerPage = 25, TotalItemCount = 10 };

        /// <summary>
        /// Reacts on Paginator Changes.
        /// </summary>
        private readonly EventCallbackSubscriber<PaginatorState> CurrentPageItemsChanged;

        /// <summary>
        /// Sort Options for all available fields.
        /// </summary>
        private static readonly List<Option<string>> SortOptions = new()
        {
            { new Option<string> { Value = "owner_asc", Text = "Owner (Ascending)" } },
            { new Option<string> { Value = "owner_desc", Text = "Owner (Descending)" } },
            { new Option<string> { Value = "repository_asc", Text = "Repository (Ascending)" } },
            { new Option<string> { Value = "repository_desc", Text = "Repository (Descending)" } },
            { new Option<string> { Value = "latestCommitDate_asc", Text = "Recently Updated (Ascending)" } },
            { new Option<string> { Value = "latestCommitDate_desc", Text = "Recently Updated (Descending)", Selected = true } },
        };

        /// <summary>
        /// The Selected Sort Option:
        /// </summary>
        public Option<string> SelectedSortOption { get; set; }
        
        /// <summary>
        /// When loading data, we need to cancel previous requests.
        /// </summary>
        private CancellationTokenSource? _pendingDataLoadCancellationTokenSource;

        /// <summary>
        /// Search Results for a given query.
        /// </summary>
        List<CodeSearchResultDto> CodeSearchResults { get; set; } = new List<CodeSearchResultDto>();

        /// <summary>
        /// The current Query String to send to the Server (Elasticsearch QueryString format).
        /// </summary>
        string QueryString { get; set; } = string.Empty;

        /// <summary>
        /// Total Item Count.
        /// </summary>
        int TotalItemCount { get; set; } = 0;

        public Index()
        {
            CurrentPageItemsChanged = new(EventCallback.Factory.Create<PaginatorState>(this, QueryAsync));
            SelectedSortOption = SortOptions.First(x => x.Value == "latestCommitDate_desc");
        }

        /// <inheritdoc />
        protected override Task OnParametersSetAsync()
        {
            // The associated pagination state may have been added/removed/replaced
            CurrentPageItemsChanged.SubscribeOrMove(Pagination?.CurrentPageItemsChanged);

            return Task.CompletedTask;
        }


        /// <summary>
        /// Queries the Backend and cancels all pending requests.
        /// </summary>
        /// <returns>An awaitable task</returns>
        public async Task QueryAsync()
        {
            // Cancel all Pending Search Requests
            _pendingDataLoadCancellationTokenSource?.Cancel();
            
            // Initialize the new CancellationTokenSource
            var loadingCts = _pendingDataLoadCancellationTokenSource = new CancellationTokenSource();

            // Get From and Size for Pagination:
            var from = Pagination.CurrentPageIndex * Pagination.ItemsPerPage;
            var size = Pagination.ItemsPerPage;

            // Get the Sort Field to Sort results for
            var sortField = GetSortField();

            // Construct the Request
            var searchRequestDto = new CodeSearchRequestDto
            {
                Query = QueryString,
                From = from,
                Size = size,
                Sort = new List<SortFieldDto>() { sortField }
            };
            
            // Query the API
            var results = await ElasticsearchCodeSearchService.QueryAsync(searchRequestDto, loadingCts.Token);

            if(results == null)
            {
                return; // TODO Show Error ...
            }

            // Set the Search Results:
            CodeSearchResults = results.Results;
            TotalItemCount = results.Total;

            // Refresh the Pagination:
            await Pagination.SetTotalItemCountAsync(results.Total);

            StateHasChanged();
        }

        private async Task EnterSubmit(KeyboardEventArgs e)
        {
            if (e.Key == "Enter")
            {
                await QueryAsync();
            }
        }

        private SortFieldDto GetSortField()
        {
            return SelectedSortOption.Value switch
            {
                "owner_asc" => new SortFieldDto() { Field = "owner", Order = SortOrderEnumDto.Asc },
                "owner_desc" => new SortFieldDto() { Field = "owner", Order = SortOrderEnumDto.Desc },
                "repository_asc" => new SortFieldDto() { Field = "repository", Order = SortOrderEnumDto.Asc },
                "repository_desc" => new SortFieldDto() { Field = "repository", Order = SortOrderEnumDto.Desc },
                "latestCommitDate_asc" => new SortFieldDto() { Field = "latestCommitDate", Order = SortOrderEnumDto.Asc },
                "latestCommitDate_desc" => new SortFieldDto() { Field = "latestCommitDate", Order = SortOrderEnumDto.Desc },
                _ => throw new ArgumentException($"Unknown SortField '{SelectedSortOption.Value}'"),
            };
        }

        public ValueTask DisposeAsync()
        {
            CurrentPageItemsChanged.Dispose();
            
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
    grid-template-rows: auto auto 1fr auto auto;
    grid-template-columns: 1fr;
    grid-template-areas:
        "search-header"
        "search-results-total"
        "search-results"
        "search-paginator"
        "search-footer";
}

.search-header {
    display: grid;
    grid-area: search-header;
    grid-template-columns: minmax(auto, 900px);
    grid-template-rows: auto 1fr;
    justify-content: center;
    padding: 1rem;
    background-color: #f7f7f7;
    border-bottom: 1px solid #d6d5d5;
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
    grid-template-columns: 1fr;
    grid-template-rows: 1fr;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    grid-row-gap: 20px;
    background-color: #ffffff;
}

.search-results {
    display: grid;
    grid-area: search-results;
    grid-template-columns: 1fr;
    grid-auto-rows: max-content;
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
    grid-row-gap: 20px;
    background-color: #ffffff;
}

.search-paginator {
    display: grid;
    grid-area: search-paginator;
    min-width: 500px;
    justify-content: center;
    grid-template-columns: auto;
    grid-column-gap: 10px;
}

.search-footer {
    display: grid;
    grid-area: search-footer;
    background-color: #f7f7f7;
    border-top: 1px solid #d6d5d5;
    justify-content: center;
    padding: 10px;
}
```


## Components ##


### Search Result ###

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
                    @line.LineNo
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
    border: 1px solid #dcdcde;
    background-color: #fff;
}

    .code-box .code-box-title {
        grid-area: code-box-title;
        background-color: #fbfafd;
        border-bottom: 1px solid #dcdcde;
        padding: 10px 16px;
    }

    .code-box .code-box-content {
        display: grid;
        grid-area: code-box-content;
        grid-template-columns: 1fr;
        overflow: auto;
        white-space: nowrap;
        color: #333;
        font-family: "JetBrains Mono","Menlo","DejaVu Sans Mono","Liberation Mono","Consolas","Ubuntu Mono","Courier New","andale mono","lucida console",monospace;
    }

        .code-box .code-box-content .highlighted-line {
            background-color: #f8eec7 !important;
        }

        .code-box .code-box-content .code-line {
            display: grid;
            grid-template-columns: auto 1fr;
        }

            .code-box .code-box-content .code-line .code-line-number {
                display: grid;
                text-align: right;
                padding-right: 0.5rem;
                border-right: 1px solid #dcdcde;
                min-width: 4rem;
            }

            .code-box .code-box-content .code-line .code-line-content {
                display: grid;
                text-align: left;
            }
```

### Paginator ###

```csharp
using ElasticsearchCodeSearch.Client.Infrastructure;

namespace ElasticsearchCodeSearch.Client.Components.Pagination
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
        public int CurrentPageIndex { get; private set; }

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
using ElasticsearchCodeSearch.Client.Infrastructure;
using Microsoft.AspNetCore.Components;
using Microsoft.Fast.Components.FluentUI;

namespace ElasticsearchCodeSearch.Client.Components.Pagination
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

## Conclusion ##

And that's it. You can now start your Elasticsearch instance, and start the solution. It will 
automatically start the Backend and the Frontend. By indexing data through the PowerShell script 
you can fill the index with code to search for.

