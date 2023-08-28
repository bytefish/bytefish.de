title: Using the GitHub REST API with .NET
date: 2023-08-28 09:31
tags: dotnet, csharp, git
category: dotnet
slug: github_rest_api_with_dotnet
author: Philipp Wagner
summary: This article shows how to use the GitHub REST API from .NET.

In this article I will show how to query the GitHub REST API from your .NET application. It's 
not really complicated, but I thought it's worth sharing code.

## Table of contents ##

[TOC]

## REST API Client for .NET ##

### Options ###

It starts with Options to configure the `GitHubClient` we are going to write. For the API 
we need an Access Token, that you can create for your GitHub user. I have also added a 
request delay to not hit rate limits.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticsearchCodeSearch.Indexer.Client.Options
{
    /// <summary>
    /// GitHub Client Options.
    /// </summary>
    public class GitHubClientOptions
    {
        /// <summary>
        /// The Fine-Grained Access Token.
        /// </summary>
        public string AccessToken { get; set; } = string.Empty;

        /// <summary>
        /// Time to delay multiple requests.
        /// </summary>
        public int RequestDelayInMilliseconds { get; set; }
    }
}
```

### Exceptions ###

The API might throw exceptions, due to bad requests or reaching rate limits. We will throw a 
`GitHubApiException` in such situations.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Runtime.Serialization;

namespace ElasticsearchCodeSearch.Indexer.Client.Exceptions
{
    [Serializable]
    public class GitHubApiException : Exception
    {
        public GitHubApiException()
        {
        }

        public GitHubApiException(string? message) : base(message)
        {
        }

        public GitHubApiException(string? message, Exception? innerException) : base(message, innerException)
        {
        }

        protected GitHubApiException(SerializationInfo info, StreamingContext context) : base(info, context)
        {
        }
    }
}
```

### Data Transfer Objects (DTO) ###

The API returns paginated results for various endpoints, so you do not query too much 
data at once. The response contains a link to the first, previous, next and last page, 
if they are available.

We call this a `PaginatedResultsDto`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticsearchCodeSearch.Indexer.Client.Dto
{
    public class PaginatedResultsDto<TEntity>
    {
        /// <summary>
        /// Gets or sets the entities fetched.
        /// </summary>
        public required List<TEntity>? Values { get; set; }

        /// <summary>
        /// Gets or sets the Page Number.
        /// </summary>
        public required int PageNumber { get; set; }

        /// <summary>
        /// Gets or sets the Page Size.
        /// </summary>
        public required int PageSize { get; set; }
 
        /// <summary>
        /// Gets or sets the link to the first page.
        /// </summary>
        public string? FirstPage { get; set; }

        /// <summary>
        /// Gets or sets the link to the previous page.
        /// </summary>
        public string? PreviousPage { get; set; }

        /// <summary>
        /// Gets or sets the link to the next page.
        /// </summary>
        public string? NextPage { get; set; }

        /// <summary>
        /// Gets or sets the link to the last page.
        /// </summary>
        public string? LastPage { get; set; }
    }
}
```

The Endpoint to query for repositories defines various entities, such as a repository owner 
and the repository metadata itself. We start with the `RepositoryOwnerDto`, and we only 
need the `login` for my use case.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace ElasticsearchCodeSearch.Indexer.Client.Dto
{
    public class RepositoryOwnerDto
    {
        [JsonPropertyName("login")]
        public required string Login { get; set; }
    }
}
```

The `RepositoryMetadataDto` contains all metadata for a GitHub repository, that I need for 
a use case I am working on. You may need to add the properties you are interested in. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace ElasticsearchCodeSearch.Indexer.Client.Dto
{
    public class RepositoryMetadataDto
    {
        [JsonPropertyName("id")]
        public required int Id { get; set; }

        [JsonPropertyName("node_id")]
        public required string NodeId { get; set; }

        [JsonPropertyName("name")]
        public required string Name { get; set; }

        [JsonPropertyName("full_name")]
        public required string FullName { get; set; }

        [JsonPropertyName("default_branch")]
        public required string DefaultBranch { get; set; }

        [JsonPropertyName("owner")]
        public required RepositoryOwnerDto Owner { get; set; }

        [JsonPropertyName("url")]
        public string? Url { get; set; }

        [JsonPropertyName("git_url")]
        public string? GitUrl { get; set; }
        
        [JsonPropertyName("clone_url")]
        public string? CloneUrl { get; set; }

        [JsonPropertyName("sshUrl")]
        public string? SshUrl { get; set; }

        [JsonPropertyName("updated_at")]
        public required DateTime UpdatedAt { get; set; }
        
        [JsonPropertyName("created_at")]
        public required DateTime CreatedAt { get; set; }

        [JsonPropertyName("pushed_at")]
        public required DateTime PushedAt { get; set; }

        [JsonPropertyName("size")]
        public required int Size { get; set; }

        [JsonPropertyName("language")]
        public string? Language { get; set; }

    }
}
```

### GitHubClient ###

And finally we can define the `GitHubClient`, which calls the GitHub REST API and returns 
the list of GitHub repositories for an organization or a specific repository.


```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Indexer.Client.Dto;
using ElasticsearchCodeSearch.Indexer.Client.Options;
using ElasticsearchCodeSearch.Shared.Exceptions;
using ElasticsearchCodeSearch.Shared.Logging;
using Microsoft.Extensions.Options;
using System.Globalization;

namespace ElasticsearchCodeSearch.Indexer.Client
{
    public class GitHubClient : IDisposable
    {
        private readonly ILogger<GitHubClient> _logger;
        private readonly GitHubClientOptions _options;
        private readonly HttpClient _httpClient;
        private bool disposedValue;

        public GitHubClient(ILogger<GitHubClient> logger, IOptions<GitHubClientOptions> options)
            : this(logger, options, new HttpClient())
        {
        }

        public GitHubClient(ILogger<GitHubClient> logger, IOptions<GitHubClientOptions> options, HttpClient httpClient)
        {
            _logger = logger;
            _options = options.Value;
            _httpClient = httpClient;
        }

        public async Task<List<RepositoryMetadataDto>> GetAllRepositoriesByOrganizationAsync(string organization, int pageSize, CancellationToken cancellationToken)
        {
            // Holds the Results:
            List<RepositoryMetadataDto> repositories = new List<RepositoryMetadataDto>();

            // Get the first page:
            var page = await GetRepositoriesByOrganizationAsync(organization, 1, pageSize, cancellationToken).ConfigureAwait(false);

            // If it has values, add them to the result:
            if (page.Values != null)
            {
                repositories.AddRange(page.Values);
            }

            await Task.Delay(_options.RequestDelayInMilliseconds, cancellationToken).ConfigureAwait(false);

            // If there is a next page, we iterate to it:
            while (page.NextPage != null)
            {
                page = await GetRepositoriesByOrganizationAsync(organization, page.PageNumber + 1, pageSize, cancellationToken).ConfigureAwait(false);

                if (page.Values != null)
                {
                    repositories.AddRange(page.Values);
                }

                await Task.Delay(_options.RequestDelayInMilliseconds, cancellationToken).ConfigureAwait(false);
            }

            return repositories;
        }

        public async Task<RepositoryMetadataDto?> GetRepositoryByOwnerAndRepositoryAsync(string owner, string repository, CancellationToken cancellationToken)
        {
            var httpRequestMessage = new HttpRequestMessage
            {
                Method = HttpMethod.Get,
                RequestUri = new Uri($"https://api.github.com/orgs/repos/{owner}/{repository}"),
                Headers =
                {
                    { "User-Agent", "curl/8.0.1" },
                    { "Accept", "application/vnd.github+json" },
                    { "Authorization", $"Bearer {_options.AccessToken}" },
                    { "X-GitHub-Api-Version", $"2022-11-28" },
                }
            };

            var response = await _httpClient
                .SendAsync(httpRequestMessage, cancellationToken)
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

            var repositoryMetadata = await response.Content
                .ReadFromJsonAsync<RepositoryMetadataDto>(cancellationToken: cancellationToken)
                .ConfigureAwait(false);

            return repositoryMetadata;
        }

        public async Task<PaginatedResultsDto<RepositoryMetadataDto>> GetRepositoriesByOrganizationAsync(string organization, int pageNum, int pageSize, CancellationToken cancellationToken)
        {
            var httpRequestMessage = new HttpRequestMessage
            {
                Method = HttpMethod.Get,
                RequestUri = new Uri($"https://api.github.com/orgs/{organization}/repos?page={pageNum}&per_page={pageSize}"),
                Headers = 
                {
                    { "User-Agent", "curl/8.0.1" },
                    { "Accept", "application/vnd.github+json" },
                    { "Authorization", $"Bearer {_options.AccessToken}" },
                    { "X-GitHub-Api-Version", $"2022-11-28" },
                }
            };

            var response = await _httpClient
                .SendAsync(httpRequestMessage, cancellationToken)
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

            // Get the pagination links from the response
            var links = ParseLinks(response);

            var repositories = await response.Content
                .ReadFromJsonAsync<List<RepositoryMetadataDto>>(cancellationToken: cancellationToken)
                .ConfigureAwait(false);

            return new PaginatedResultsDto<RepositoryMetadataDto>
            {
                PageNumber = pageNum,
                PageSize = pageSize,
                FirstPage = links.FirstUrl,
                PreviousPage = links.PrevUrl,
                NextPage = links.NextUrl,
                LastPage = links.LastUrl,
                Values = repositories
            };
        }

        /// <summary>
        /// Parses the Links in the Response's "Links" Header into the components.
        /// </summary>
        /// <param name="httpResponseMessage">Response Header with the Links Header</param>
        /// <returns>Links to the various pages</returns>
        public (string? FirstUrl, string? PrevUrl, string? NextUrl, string? LastUrl) ParseLinks(HttpResponseMessage httpResponseMessage)
        {
            // Get the Value for the first "Links" header, which looks like this
            //
            // <https://api.github.com/organizations/6154722/repos?per_page=1&page=2>; rel="next", <https://api.github.com/organizations/6154722/repos?per_page=1&page=5762>; rel="last"
            //
            if (!httpResponseMessage.Headers.TryGetValues("Link", out var linkHeaders)) 
            {
                return (null, null, null, null);
            }

            var linkValue = linkHeaders.FirstOrDefault();

            if (linkValue == null)
            {
                return (null, null, null, null);
            }

            // Split at the comma, so we get it like this:
            // [0] <https://api.github.com/organizations/6154722/repos?per_page=1&page=2>; rel="next"
            // [1] <https://api.github.com/organizations/6154722/repos?per_page=1&page=5762>; rel="last"
            var linksEntries = linkValue.Split(',', StringSplitOptions.TrimEntries);

            // Build a Dictionary with the link Types available
            var links = linksEntries
                // Split at semicolon, so it looks like this
                //
                //      [0] <https://api.github.com/organizations/6154722/repos?per_page=1&page=2>
                //      [1] rel="next"
                .Select(x => x.Split(";"))
                // We need two elements here, so we can make up a dictionary, that 
                // maps a type (first, prev, ...) to a link.
                .Where(x => x.Length == 2)
                // Get the Type and the Link, so it looks like this:
                //
                //      ["next"] = https://api.github.com/organizations/6154722/repos?per_page=1&page=2
                // 
                .ToDictionary(x => GetLinkType(x[1]).Trim(), x => GetLinkValue(x[0]).Trim());


            return (links.GetValueOrDefault("first"), links.GetValueOrDefault("prev"), links.GetValueOrDefault("next"), links.GetValueOrDefault("last"));
        }

        private string GetLinkType(string source)
        {
            return source
                .Replace("rel=\"", string.Empty)
                .Replace("\"", string.Empty);
        }

        private string GetLinkValue(string source)
        {
            return source
                .Replace("<", string.Empty)
                .Replace(">", string.Empty);
        }

        protected virtual void Dispose(bool disposing)
        {
            if (!disposedValue)
            {
                if (disposing)
                {
                    _httpClient?.Dispose();
                }

                disposedValue = true;
            }
        }

        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }
    }
}
```

## Registering the Client ##

We don't want to store the GitHub Token anywhere near our source code, to not 
accidentally leak it. So we use an Environment variable and configure the 
`GitHubClientOptions` to use the `GH_TOKEN` environment variable.

```csharp
// Create the GitClientOptions by using the GH_TOKEN Key:
builder.Services.Configure<GitHubClientOptions>(o =>
{
    o.RequestDelayInMilliseconds = 0;
    o.AccessToken = Environment.GetEnvironmentVariable("GH_TOKEN")!;
});
```

The `GitHubClient` can safely be defined as a Singleton.

```csharp
builder.Services.AddSingleton<GitHubClient>();
```

## Using it ##

After injecting the `GitHubClient` to your Service, it's as easy as calling:

```csharp
var response = await _gitHubClient
    .GetRepositoriesByOrganizationAsync(organization, 1, 20, cancellationToken)
    .ConfigureAwait(false);
```