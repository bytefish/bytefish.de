title: Executing git Commands from .NET
date: 2023-08-26 10:21
tags: dotnet, csharp, git
category: dotnet
slug: executing_git_commands_dotnet
author: Philipp Wagner
summary: This article shows how to execute GIT commands from .NET

I recently needed some metadata off of `git` repositories, like a list of indexed files. I 
initially tried to use LibGit2Sharp, but it often failed to return file information for 
things like merge commits. 

So I just executed the `git` executable from .NET using a `Process`, and called it a 
`GitExecutor` for lack of a better name. Maybe it is useful for someone else attempting 
to do the same, so I am sharing it here.

## Table of contents ##

[TOC]

## Executing Git Commands: The GitExecutor ##

// Licensed under the MIT license. See LICENSE file in the project root for full license information.

```csharp
namespace ElasticsearchCodeSearch.Indexer.Git.Exceptions
{
    public class GitException : Exception
    {
        public readonly int ExitCode;
        public readonly string Errors;

        public GitException(int exitCode, string errors) 
        { 
            ExitCode = exitCode;
            Errors = errors;
        }
    }
}
```

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchCodeSearch.Indexer.Git.Exceptions;
using ElasticsearchCodeSearch.Shared.Logging;
using Microsoft.Extensions.Logging;
using System.Diagnostics;
using System.Text;

namespace ElasticsearchCodeSearch.Indexer.Git
{
    public class GitExecutor
    {
        private readonly ILogger<GitExecutor> _logger;

        public GitExecutor(ILogger<GitExecutor> logger) 
        {
            _logger = logger;
        }

        public async Task Clone(string repository_url, string repository_directory, CancellationToken cancellationToken)
        {
            await RunAsync($"clone {repository_url} {repository_directory}", string.Empty, cancellationToken);
        }

        public async Task<string> SHA1(string repository_directory, string path, CancellationToken cancellationToken)
        {
            var result = await RunAsync($"ls-files -s {path}", repository_directory, cancellationToken);

            return result.Split(" ").Skip(1).First();
        }

        public async Task<string> CommitHash(string repository_directory, string path, CancellationToken cancellationToken)
        {
            var result = await RunAsync($"log --pretty=format:\"%H\" -n 1 -- {path}", repository_directory, cancellationToken);

            return result;
        }

        public async Task<DateTime> LatestCommitDate(string repository_directory, string path, CancellationToken cancellationToken)
        {
            var result = await RunAsync($" log -1  --date=iso-strict --format=\"%ad\" -- {path}", repository_directory, cancellationToken);

            if(DateTime.TryParse(result, out var date))
            {
                return date;
            }

            return default;
        }

        public async Task<string[]> ListFiles(string repository_directory, CancellationToken cancellationToken)
        {
            var result = await RunAsync($"ls-files", repository_directory, cancellationToken);

            var files = result
                .Split("\r\n")
                .ToArray();

            return files;
        }

        public async Task<string> RunAsync(string arguments, string workingDirectory, CancellationToken cancellationToken)
        {
            var result = await RunProcessAsync("git", arguments, workingDirectory, cancellationToken);

            if(result.ExitCode != 0)
            {
                throw new GitException(result.ExitCode, result.Errors);
            }

            return result.Output;
        }

        private async Task<(int ExitCode, string Output, string Errors)> RunProcessAsync(string application, string arguments, string workingDirectory, CancellationToken cancellationToken)
        {
            using (var process = new Process())
            {
                process.StartInfo = new ProcessStartInfo
                {
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    RedirectStandardError = true,
                    RedirectStandardOutput = true,
                    FileName = application,
                    Arguments = arguments,
                    WorkingDirectory = workingDirectory,
                };

                var outputBuilder = new StringBuilder();
                var errorsBuilder = new StringBuilder();

                process.OutputDataReceived += (_, args) => outputBuilder.AppendLine(args.Data);
                process.ErrorDataReceived += (_, args) => errorsBuilder.AppendLine(args.Data);

                process.Start();

                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                await process.WaitForExitAsync(cancellationToken);

                var exitCode = process.ExitCode;
                var output = outputBuilder.ToString().Trim();
                var errors = errorsBuilder.ToString().Trim();

                return (exitCode, output, errors);
            }
        }
    }
}
```

In the code I start by adding it as a Singleton in the Starup:

```csharp
builder.Services.AddSingleton<GitExecutor>();
```

And then use it like this:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace ElasticsearchCodeSearch.Indexer.Services
{
    /// <summary>
    /// Git Indexer.
    /// </summary>
    public class GitIndexerService
    {
        private readonly GitExecutor _git;
        
        public GitIndexerService(GitExecutor git)
        {
            _git = git;
        }

        public async ValueTask IndexRepositoryAsync(RepositoryMetadataDto repositoryMetadata, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            try
            {
                // ...
                
                await _git
                    .Clone(repositoryMetadata.CloneUrl, workingDirectory, cancellationToken)
                    .ConfigureAwait(false);

                // Get the list of allowed files, by matching against allowed extensions (.c, .cpp, ...)
                // and allowed filenames (.gitignore, README, ...). We don't want to parse binary data.
                var batches =  (await _git.ListFiles(workingDirectory, cancellationToken).ConfigureAwait(false))
                    .Where(filename => IsAllowedFile(filename, allowedExtensions, allowedFilenames))
                    .Chunk(_options.BatchSize);

                var parallelOptions = new ParallelOptions()
                {
                    MaxDegreeOfParallelism = _options.MaxParallelBulkRequests,
                    CancellationToken = cancellationToken
                };

                await Parallel
                    .ForEachAsync(source: batches, parallelOptions: parallelOptions, body: (source, cancellationToken) => IndexDocumentsAsync(repositoryMetadata, source, cancellationToken))
                    .ConfigureAwait(false);
            } 
            catch(Exception e)
            {
                _logger.LogError(e, "Indexing Repository '{Repository}' failed", repositoryMetadata.FullName);

                throw;
            } 
            finally
            {
                // ...
            }
        }
        
        // ...

    ]
}
```