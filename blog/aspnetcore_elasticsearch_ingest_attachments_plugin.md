title: Using the Elasticsearch Ingest Attachments plugin with .NET
date: 2024-07-24 09:36
tags: aspnetcore, elasticsearch
category: dotnet
slug: aspnetcore_elasticsearch_ingest_attachments_plugin
author: Philipp Wagner
summary: This article shows how to use the Elasticsearch attachments processor.

If you want to index PDF, Markdown or Microsoft Word files with Elasticsearch, you often need to extract 
the content and metadata in these documents. Elasticsearch comes with the Ingest Attachments plugin built-in, 
which ...

> [...] lets Elasticsearch extract file attachments in common formats (such as PPT, XLS, and PDF) by 
> using the Apache text extraction library Tika.

In this article we will take a look at using the Elasticsearch attachments processor in .NET.

All code can be found in a Git repository at:

* [https://github.com/bytefish/ElasticsearchFulltextExample](https://github.com/bytefish/ElasticsearchFulltextExample)

## .NET Implementation for using the Attachments Plugin ##

We start our implementation by adding a class `ElasticConstants`, that holds constants for our document to be 
written and the attachment to be stored. This is done, so the field names in Elasticsearch are explicitly set, 
instead of having to infer them. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace ElasticsearchFulltextExample.Shared.Constants
{
    public static class ElasticConstants
    {
        /// <summary>
        /// Pipeline Constants, such as Names.
        /// </summary>
        public static class Pipelines
        {
            /// <summary>
            /// Name of the Attachments Processor Pipeline.
            /// </summary>
            public const string Attachments = "attachments";
        }

        // ...

        /// <summary>
        /// Property Names for the Elasticsearch Documents.
        /// </summary>
        public static class DocumentNames
        {
            /// <summary>
            /// Document ID.
            /// </summary>
            public const string Id = "id";

            /// <summary>
            /// Title.
            /// </summary>
            public const string Title = "title";

            /// <summary>
            /// Filename.
            /// </summary>
            public const string Filename = "filename";

            /// <summary>
            /// Binary Data.
            /// </summary>
            public const string Data = "data";

            /// <summary>
            /// List of Keywords.
            /// </summary>
            public const string Keywords = "keywords";

            /// <summary>
            /// List of Suggestions.
            /// </summary>
            public const string Suggestions = "suggestions";

            /// <summary>
            /// Date the File has been indexed at.
            /// </summary>
            public const string IndexedOn = "indexed_on";

            /// <summary>
            /// Attachment.
            /// </summary>
            public const string Attachment = "attachment";
        }

        /// <summary>
        /// Attachment Metadata populated by the Elasticsearch Plugin, which 
        /// in turn uses Apache Tika for extracting data off of files. The 
        /// Properties have been taken off of Apache Tika.
        /// </summary>
        public static class AttachmentNames
        {
            public const string Content = "content";

            public const string Title = "title";

            public const string Author = "author";

            public const string Date = "date";

            public const string Keywords = "keywords";

            public const string ContentType = "content_type";

            public const string ContentLength = "content_length";

            public const string Language = "language";

            public const string Modified = "modified";

            public const string Format = "format";

            public const string Identifier = "identifier";

            public const string Contributor = "contributor";

            public const string Coverage = "converage";

            public const string Modifier = "modifier";

            public const string CreatorTool = "creator_tool";

            public const string Publisher = "publisher";

            public const string Relation = "relation";

            public const string Rights = "rights";

            public const string Source = "source";

            public const string Type = "type";

            public const string Description = "description";

            public const string PrintDate = "print_date";

            public const string MetadataDate = "metadata_date";

            public const string Latitude = "latitude";

            public const string Longitude = "longitude";

            public const string Altitude = "altitude";

            public const string Rating = "rating";

            public const string Comments = "comments";
        }
    }
}
```

### Domain Model for Documents and Attachments ###

We then define the `ElasticsearchAttachment`, which holds the output of the Ingest Attachments processor. The previously 
defined constants can be used as a `JsonPropertyName` for properties. A list of available properties extracted by Apache 
Tika can be found at:

* [https://www.elastic.co/guide/en/elasticsearch/reference/8.14/attachment.html](https://www.elastic.co/guide/en/elasticsearch/reference/8.14/attachment.html)

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchFulltextExample.Shared.Constants;
using System.Text.Json.Serialization;

namespace ElasticsearchFulltextExample.Api.Infrastructure.Elasticsearch.Models
{
    /// <summary>
    /// Properties extracted by the Tika Plugin (https://www.elastic.co/guide/en/elasticsearch/reference/8.14/attachment.html).
    /// </summary>
    public class ElasticsearchAttachment
    {
        [JsonPropertyName(ElasticConstants.AttachmentNames.Content)]
        public string? Content { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Title)]
        public string? Title { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Author)]
        public string? Author { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Date)]
        public string? Date { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Keywords)]
        public string[]? Keywords { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.ContentType)]
        public string? ContentType { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.ContentLength)]
        public long? ContentLength { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Language)]
        public string? Language { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Modified)]
        public string? Modified { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Format)]
        public string? Format { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Identifier)]
        public string? Identifier { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Contributor)]
        public string? Contributor { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Coverage)]
        public string? Coverage { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Modifier)]
        public string? Modifier { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.CreatorTool)]
        public string? CreatorTool { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Publisher)]
        public string? Publisher { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Relation)]
        public string? Relation { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Rights)]
        public string? Rights { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Source)]
        public string? Source { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Type)]
        public string? Type { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Description)]
        public string? Description { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.PrintDate)]
        public string? PrintDate { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.MetadataDate)]
        public string? MetadataDate { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Latitude)]
        public string? Latitude { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Longitude)]
        public string? Longitude { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Altitude)]
        public string? Altitude { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Rating)]
        public string? Rating { get; set; }

        [JsonPropertyName(ElasticConstants.AttachmentNames.Comments)]
        public string? Comments { get; set; }
    }
}
```

The `ElasticsearchDocument` is going to be indexed by Elasticsearch and it has the binary data in the `"data"` field. The 
document also needs to have a property `attachment`, which is an `ElasticsearchAttachment`. This field is populated by the 
Ingest Attachments processor, thus being nullable.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ElasticsearchFulltextExample.Shared.Constants;
using System.Text.Json.Serialization;

namespace ElasticsearchFulltextExample.Api.Infrastructure.Elasticsearch.Models
{
    public class ElasticsearchDocument
    {
        /// <summary>
        /// A unique document id.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Id)]
        public required string Id { get; set; }

        /// <summary>
        /// The Title of the Document for Suggestion.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Title)]
        public required string Title { get; set; }

        /// <summary>
        /// The Original Filename of the uploaded document.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Filename)]
        public required string Filename { get; set; }

        /// <summary>
        /// The Data of the Document.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Data)]
        public byte[]? Data { get; set; }

        /// <summary>
        /// Keywords to filter for.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Keywords)]
        public required string[] Keywords { get; set; }

        /// <summary>
        /// Suggestions for the Autocomplete Field.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Suggestions)]
        public required string[] Suggestions { get; set; }

        /// <summary>
        /// The Date the document was indexed on.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.IndexedOn)]
        public DateTime? IndexedOn { get; set; }

        /// <summary>
        /// The Attachment generated by Elasticsearch.
        /// </summary>
        [JsonPropertyName(ElasticConstants.DocumentNames.Attachment)]
        public ElasticsearchAttachment? Attachment { get; set; }
    }
}
```

### Creating the Elasticsearch Index for Documents ###

We can then create the `document` index, where all documents are indexed to. All properties 
have been mapped explicitly, because automagically mapping properties for indices often leads 
to (bad) surprises.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace ElasticsearchFulltextExample.Api.Infrastructure.Elasticsearch
{
    public class ElasticsearchSearchClient
    {
        private readonly ILogger<ElasticsearchSearchClient> _logger;

        private readonly ElasticsearchClient _client;
        private readonly string _indexName;

        public ElasticsearchSearchClient(ILogger<ElasticsearchSearchClient> logger, IOptions<ElasticsearchSearchClientOptions> options)
        {
            _logger = logger;
            _indexName = options.Value.IndexName;
            _client = CreateClient(options.Value);
        }
        
        // ...

        public async Task<CreateIndexResponse> CreateIndexAsync(CancellationToken cancellationToken)
        {
            var createIndexResponse = await _client.Indices.CreateAsync(_indexName, descriptor => descriptor
                .Settings(settings => settings
                    .Codec("best_compression")
                    .Analysis(analysis => analysis
                         .Tokenizers(tokenizers => tokenizers
                            .Standard("fts_tokenizer"))
                        .Analyzers(analyzers => analyzers
                            .Custom("fts_analyzer", custom => custom
                                .Tokenizer("fts_tokenizer")
                                .Filter([ "lowercase", "asciifolding"])))))
                .Mappings(mapping => mapping
                    .Properties<ElasticsearchDocument>(properties => properties
                        .Text(ElasticConstants.DocumentNames.Id)
                        .Text(ElasticConstants.DocumentNames.Title, c => c
                            .Analyzer("fts_analyzer")
                            .Store(true))
                        .Text(ElasticConstants.DocumentNames.Filename)
                        .Binary(ElasticConstants.DocumentNames.Data)
                        .Date(ElasticConstants.DocumentNames.IndexedOn)
                        .Keyword(ElasticConstants.DocumentNames.Keywords)
                        .Completion(ElasticConstants.DocumentNames.Suggestions)
                        .Object(ElasticConstants.DocumentNames.Attachment, attachment => attachment
                                .Properties(attachmentProperties => attachmentProperties
                                    .Text(ElasticConstants.AttachmentNames.Content, c => c
                                        .IndexOptions(IndexOptions.Positions)
                                        .Analyzer("fts_analyzer")
                                        .TermVector(TermVectorOption.WithPositionsOffsetsPayloads)
                                        .Store(true))
                                    .Text(ElasticConstants.AttachmentNames.Title, c => c
                                        .Analyzer("fts_analyzer")
                                        .Store(true))
                                    .Text(ElasticConstants.AttachmentNames.Author, c => c
                                        .Analyzer("fts_analyzer")
                                        .Store(true))
                                    .Date(ElasticConstants.AttachmentNames.Date)
                                    .Text(ElasticConstants.AttachmentNames.Keywords)
                                    .Text(ElasticConstants.AttachmentNames.ContentType)
                                    .LongNumber(ElasticConstants.AttachmentNames.ContentLength)
                                    .Text(ElasticConstants.AttachmentNames.Language)
                                    .Text(ElasticConstants.AttachmentNames.Modified)
                                    .Text(ElasticConstants.AttachmentNames.Format)
                                    .Text(ElasticConstants.AttachmentNames.Identifier)
                                    .Text(ElasticConstants.AttachmentNames.Contributor)
                                    .Text(ElasticConstants.AttachmentNames.Coverage)
                                    .Text(ElasticConstants.AttachmentNames.Modifier)
                                    .Text(ElasticConstants.AttachmentNames.CreatorTool)
                                    .Text(ElasticConstants.AttachmentNames.Publisher)
                                    .Text(ElasticConstants.AttachmentNames.Relation)
                                    .Text(ElasticConstants.AttachmentNames.Rights))))), cancellationToken);

            if (_logger.IsDebugEnabled())
            {
                _logger.LogDebug("CreateIndexResponse DebugInformation: {DebugInformation}", createIndexResponse.DebugInformation);
            }

            return createIndexResponse;
        }
        
        // ...
    }
}
```

### Creating the Attachments Pipeline ###

Now what needs to be done is to create a Pipeline, that uses the `Attachments` processor coming with Elasticsearch. It 
works like this: It reads the binary data from the `"data"` field and populates the `"attachment"` as the target 
field. 

By using the `RemoveBinary` method, we are deleting the binary data after processing it.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace ElasticsearchFulltextExample.Api.Infrastructure.Elasticsearch
{
    public class ElasticsearchSearchClient
    {
        private readonly ILogger<ElasticsearchSearchClient> _logger;

        private readonly ElasticsearchClient _client;
        private readonly string _indexName;

        public ElasticsearchSearchClient(ILogger<ElasticsearchSearchClient> logger, IOptions<ElasticsearchSearchClientOptions> options)
        {
            _logger = logger;
            _indexName = options.Value.IndexName;
            _client = CreateClient(options.Value);
        }
        
        // ...

        public async Task<PutPipelineResponse> CreatePipelineAsync(CancellationToken cancellationToken)
        {
            var putPipelineResponse = await _client.Ingest.PutPipelineAsync(ElasticConstants.Pipelines.Attachments, p => p
                .Description("Document attachment pipeline")
                .Processors(pr => pr
                    .Attachment<ElasticsearchDocument>(a => a
                        .Field(new Field(ElasticConstants.DocumentNames.Data))
                        .TargetField(new Field(ElasticConstants.DocumentNames.Attachment))
                    .RemoveBinary(true))), cancellationToken).ConfigureAwait(false);

            if (_logger.IsDebugEnabled())
            {
                _logger.LogDebug($"PutPipelineResponse DebugInformation: {putPipelineResponse.DebugInformation}");
            }

            return putPipelineResponse;
        }

        // ...
    }
}
```

### Indexing a Document and using the Attachments Pipeline ###

And what's left is indexing an `ElasticsearchDocument` and invoking the previously created `attachments` 
pipeline. We define a new method `ElasticsearchSearchClient.IndexAsync(...)` method, which takes a document 
with the binary data included.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace ElasticsearchFulltextExample.Api.Infrastructure.Elasticsearch
{
    public class ElasticsearchSearchClient
    {
        private readonly ILogger<ElasticsearchSearchClient> _logger;

        private readonly ElasticsearchClient _client;
        private readonly string _indexName;

        public ElasticsearchSearchClient(ILogger<ElasticsearchSearchClient> logger, IOptions<ElasticsearchSearchClientOptions> options)
        {
            _logger = logger;
            _indexName = options.Value.IndexName;
            _client = CreateClient(options.Value);
        }
        
        // ...

        public async Task<IndexResponse> IndexAsync(ElasticsearchDocument document, CancellationToken cancellationToken)
        {
            var indexResponse = await _client
                .IndexAsync(document: document, idx => idx
                    .Index(_indexName)
                    .Pipeline(ElasticConstants.Pipelines.Attachments)
                    .OpType(OpType.Index), cancellationToken)
                .ConfigureAwait(false);

            if (_logger.IsDebugEnabled())
            {
                _logger.LogDebug("IndexResponse DebugInformation: {DebugInformation}", indexResponse.DebugInformation);
            }

            return indexResponse;
        }
        
        // ...
    }
}
```

And that's it!


### Conclusion ###

I think using the Attachments plugin was easier with NEST, because it already had an `Attachments` class, that mapped 
to the Plugin. But by looking at the documentation it has been easy to create our own `ElasticsearchAttachment` class 
and populate it using the Attachments processor.

You can see it in full action by running the ElasticsearchFulltextExample at:

* [https://github.com/bytefish/ElasticsearchFulltextExample](https://github.com/bytefish/ElasticsearchFulltextExample)
