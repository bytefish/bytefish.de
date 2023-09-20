title: Accessing the Elsevier Article Retrieval API from .NET
date: 2020-02-20 08:48
tags: dotnet, elsevier, datamining
category: covid-19
slug: elsevier_fulltext_api
author: Philipp Wagner
summary: Accessing the Elsevier Article Retrieval API from .NET

During the [COVID-19] outbreak a lot is written on Open Research and Open Access to journals, 
so that the research throughout the world is stimulated by removing journal paywalls and 
subscription fees.

According to Wikipedia Open Access is ...

> ... a set of principles and a range of practices through which research outputs are 
> distributed online, free of cost or other access barriers. With open access strictly 
> defined (according to the 2001 definition), or libre open access, barriers to copying 
> or reuse are also reduced or removed by applying an open license for copyright.

Elsevier, which is one of the largest publishers in scientific, technical, and medical 
content, also has dedicated some of its resources to Open Science:

* [https://www.elsevier.com/about/open-science](https://www.elsevier.com/about/open-science)

I wanted to learn how to use the Elsevier [Article (Full Text) Retrieval API] to get Open Access 
articles in a structured form, that it could be used for further data analytics. 

The Elsevier developer portal has a good documentation on its APIs:

* [https://dev.elsevier.com/index.html](https://dev.elsevier.com/index.html)

There was no .NET Client to query the [Article Retrieval API], so I wrote the [ElsevierFulltextApi] library.

[COVID-19]: https://en.wikipedia.org/wiki/Coronavirus_disease_2019
[Article (Full Text) Retrieval API]: https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl
[Article Retrieval API]: https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl
[ElsevierFulltextApi]: https://codeberg.org/bytefish/ElsevierFulltextApi

## Usage ##

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using NUnit.Framework;
using System.IO;
using System.Threading.Tasks;

namespace ElsevierFulltextApi.Test
{
    [TestFixture, Explicit("This Test requires a valid Elsevier API Key")]
    public class TestModelDeserialization
    {
        [Test]
        public async Task RunTestAsync()
        {
            // Read the Elsevier API Key from a File, so it isn't hardcoded here:
            var apiKey = File.ReadAllText(@"D:\elsevier_api_key.txt");

            // ... then create the API client using the API Key:
            var client = new ElsevierFulltextApiClient(apiKey);

            // ... query the Article API for a DOI:
            var fullText = await client.GetArticleByDOI(@"10.1016/j.adro.2019.05.007");

            // ... make sure it has been converted:
            Assert.IsNotNull(fullText);

            // ... work with your data:
            var creators = fullText.Coredata.Creators;

            Assert.IsNotNull(creators);
            Assert.AreEqual(13, creators.Count);
        }
    }
}
```

## License ##

The code is released under terms of the [MIT License].

[MIT License]: https://opensource.org/licenses/MIT
[The Lancet]: https://www.journals.elsevier.com/the-lancet
[John Hopkins University]: [https://systems.jhu.edu/]