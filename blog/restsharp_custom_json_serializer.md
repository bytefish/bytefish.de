title: Custom JSON Serializer and JSON Deserializer for RestSharp
date: 2015-11-08 14:41
tags: csharp, restsharp
category: csharp
slug: restsharp_custom_json_serializer
author: Philipp Wagner
summary: This article shows how to use a custom JSON serializer and JSON deserializer for RestSharp.

[RestSharp]: https://github.com/restsharp/RestSharp
[MIT License]: https://opensource.org/licenses/MIT
[Json.NET]: http://www.newtonsoft.com/json

[RestSharp] is a popular library for querying RESTful APIs with .NET. This article shows how to use a custom JSON serializer and deserializer for [RestSharp] requests and responses.

## Custom JSON Serializer / Deserializer ##

[ISerializer]: https://github.com/restsharp/RestSharp/blob/master/RestSharp/Serializers/ISerializer.cs
[IDeserializer]: https://github.com/restsharp/RestSharp/blob/master/RestSharp/Deserializers/IDeserializer.cs

### NewtonsoftJsonSerializer ###

A custom serializer and deserializer for RestSharp simply needs to implement the [ISerializer] and [IDeserializer] interfaces.

The example ``NewtonsoftJsonSerializer`` is using [Json.NET], which is a popular library for JSON serialization in the .NET world. We do this 
by writing a class, that implements RestSharps ``ISerializer`` and ``IDeserializer`` interfaces and wraps a ``Newtonsoft.Json.JsonSerializer``. 
We are also providing a default getter (``Default``), which returns a new ``NewtonsoftJsonSerializer`` with sane default values.

If the default ``Newtonsoft.Json.JsonSerializer`` doesn't fit your needs, you simply instantiate the correct serializer by using the constructor.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Newtonsoft.Json;
using System.IO;
using RestSharp.Serializers;
using RestSharp.Deserializers;

namespace GcmSharp.Serialization
{
    public class NewtonsoftJsonSerializer : ISerializer, IDeserializer
    {
        private Newtonsoft.Json.JsonSerializer serializer;

        public NewtonsoftJsonSerializer(Newtonsoft.Json.JsonSerializer serializer)
        {
            this.serializer = serializer;           
        }

        public string ContentType {
            get { return "application/json"; } // Probably used for Serialization?
            set { }
        }
        
        public string DateFormat { get; set; }

        public string Namespace { get; set; }

        public string RootElement { get; set; }

        public string Serialize(object obj)
        {
            using (var stringWriter = new StringWriter())
            {
                using (var jsonTextWriter = new JsonTextWriter(stringWriter))
                {
                    serializer.Serialize(jsonTextWriter, obj);

                    return stringWriter.ToString();
                }
            }
        }
        
        public T Deserialize<T>(RestSharp.IRestResponse response)
        {
            var content = response.Content;

            using (var stringReader = new StringReader(content))
            {
                using (var jsonTextReader = new JsonTextReader(stringReader))
                {
                    return serializer.Deserialize<T>(jsonTextReader);
                }
            }
        }

        public static NewtonsoftJsonSerializer Default
        {
            get
            {
                return new NewtonsoftJsonSerializer(new Newtonsoft.Json.JsonSerializer()
                {
                    NullValueHandling = NullValueHandling.Ignore,
                }); 
            }
        }
    }
}
```

### Using the Custom Serializer for Requests ###

[RestRequest]: https://github.com/restsharp/RestSharp/blob/master/RestSharp/RestRequest.cs

The custom Json converter needs to be set for a [RestRequest]. I am using a simple method to serialize an object to JSON 
and set it as content for a request.

```csharp
private void SetJsonContent(RestRequest request, object obj)
{
    request.RequestFormat = DataFormat.Json;
    request.JsonSerializer = NewtonsoftJsonSerializer.Default;
    request.AddJsonBody(obj);
}
```

## Using the Custom Deserializer for incoming Responses ##

[RestClient]: https://github.com/restsharp/RestSharp/blob/master/RestSharp/RestClient.cs
[look at the code]: https://github.com/restsharp/RestSharp/blob/master/RestSharp/RestClient.cs

When creating a fresh [RestClient] we need to set our custom Deserializer for the available JSON Content Types, which is done by using the ``AddHandler`` method. 
If you [look at the code] you can see ``AddHandler`` doesn't add a handler, but overrides the existing registration for a ContentType.

In my code I am using a method similar to the following.

```csharp
private RestClient CreateClient(string baseUrl)
{
    var client = new RestClient(baseUrl);

    // Override with Newtonsoft JSON Handler
    client.AddHandler("application/json", NewtonsoftJsonSerializer.Default);
    client.AddHandler("text/json", NewtonsoftJsonSerializer.Default);
    client.AddHandler("text/x-json", NewtonsoftJsonSerializer.Default);
    client.AddHandler("text/javascript", NewtonsoftJsonSerializer.Default);
    client.AddHandler("*+json", NewtonsoftJsonSerializer.Default);

    return client;
}
```