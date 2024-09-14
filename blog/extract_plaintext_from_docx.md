title: Extract Plain text from a Word Document 
date: 2024-08-12 13:15
tags: openxml, word, csharp
category: csharp
slug: extract_plaintext_from_docx
author: Philipp Wagner
summary: This article shows how to extract plain text from a docx file.

I am working on a small example for Fulltext Search using SQLite, and I want to 
enable reading Word documents, so we need a simple way to extract plain text from 
a `docx` file from .NET.

We can do this by using the OpenXml library and the following example may serve 
as a starting point.

## Table of contents ##

[TOC]

## Example Code ##

We define a small `DocumentMetadata` class, which is going to hold all extracted information.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace SqliteFulltextSearch.Api.Models
{
    /// <summary>
    /// Metadata for a Document, such as a PDF or Word Document.
    /// </summary>
    public class DocumentMetadata
    {
        /// <summary>
        /// Gets or sets the Author.
        /// </summary>
        public string? Author { get; set; }

        /// <summary>
        /// Gets or sets the Title.
        /// </summary>
        public string? Title { get; set; }

        /// <summary>
        /// Gets or sets the Subject.
        /// </summary>
        public string? Subject { get; set; }

        /// <summary>
        /// Gets or sets the Content.
        /// </summary>
        public string? Content { get; set; }

        /// <summary>
        /// Gets or sets the Creator.
        /// </summary>
        public string? Creator { get; set; }

        /// <summary>
        /// Gets or sets the Creation Date.
        /// </summary>
        public string? CreationDate { get; set; }
    }
}
```

And then we can use it to parse a given `docx` file, which is given as a `byte` array.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using SqliteFulltextSearch.Api.Models;
using SqliteFulltextSearch.Database.Model;
using SqliteFulltextSearch.Shared.Infrastructure;
using System.Globalization;
using System.Text;

namespace SqliteFulltextSearch.Api.Infrastructure.DocumentProcessing.Readers
{
    public class WordDocumentReader
    {
        private readonly ILogger<WordDocumentReader> _logger;

        public WordDocumentReader(ILogger<WordDocumentReader> logger)
        {
            _logger = logger;
        }

        public DocumentMetadata ExtractMetadata(byte[] data)
        {
            using (var ms = new MemoryStream(data))
            {
                using (var wpd = WordprocessingDocument.Open(ms, true))
                {
                    var element = wpd.MainDocumentPart?.Document.Body;

                    if (element == null)
                    {
                        return new DocumentMetadata();
                    }

                    var content = GetAsPlainText(element);

                    return new DocumentMetadata
                    {
                        Author = wpd.PackageProperties.Creator, // Not really, right?
                        Title = wpd.PackageProperties.Title,
                        Subject = wpd.PackageProperties.Subject,
                        Creator = wpd.PackageProperties.Creator,
                        Content = content,
                        CreationDate = wpd.PackageProperties.Created?.ToString(CultureInfo.InvariantCulture),
                    };
                }
            }
        }

        public string GetAsPlainText(OpenXmlElement element)
        {
            StringBuilder stringBuilder = new StringBuilder();

            foreach (var section in element.Elements())
            {
                switch (section.LocalName)
                {
                    case "t":
                        stringBuilder.Append(section.InnerText);
                        break;
                    case "cr":
                    case "br":
                        stringBuilder.Append('\n');
                        break;
                    case "tab":
                        stringBuilder.Append('\t');
                        break;
                    case "p":
                        stringBuilder.Append(GetAsPlainText(section));
                        stringBuilder.AppendLine(Environment.NewLine);
                        break;
                    default:
                        stringBuilder.Append(GetAsPlainText(section));
                        break;
                }
            }

            return stringBuilder.ToString();
        }
    }
}
```

And that's it!