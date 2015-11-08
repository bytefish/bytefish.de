title: Custom JSON Serializer and JSON Deserializer for RestSharp
date: 2015-11-08 14:41
tags: c#, restsharp
category: c#
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

A custom serializer and deserializer for RestSharp simply needs to implement the [ISerializer] and [IDeserializer] interfaces. The example ``NewtonsoftJsonSerializer`` 
is using [Json.NET], which is a popular library for JSON serialization in the .NET world.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Newtonsoft.Json;
using RestSharp.Serializers;
using System.IO;
using RestSharp.Deserializers;

namespace GcmSharp.Serialization
{
    public class NewtonsoftJsonSerializer : ISerializer, IDeserializer
    {
        private Newtonsoft.Json.JsonSerializer jsonSerializer;

        public NewtonsoftJsonSerializer()
        {
            this.jsonSerializer = new Newtonsoft.Json.JsonSerializer()
            {
                NullValueHandling = NullValueHandling.Ignore
            };            
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
                    jsonSerializer.Serialize(jsonTextWriter, obj);

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
                    return jsonSerializer.Deserialize<T>(jsonTextReader);
                }
            }
        }
    }
}
```

Yes, you probably need to extend the constructor, in order to pass a configuration for the Newtonsoft JsonSerializer into the custom serializer. This 
might be neccessary to handle custom date formats, null value handling and so on.

## Using the Custom Serializer for Requests ##

[RestRequest]: https://github.com/restsharp/RestSharp/blob/master/RestSharp/RestRequest.cs

The custom Json converter needs to be set for a [RestRequest]. I am using a simple method to serialize an object to JSON 
and set it as content for a request.

```csharp
private void SetJsonContent(RestRequest request, object obj)
{
    request.RequestFormat = DataFormat.Json;
    request.JsonSerializer = new NewtonsoftJsonSerializer();
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
    client.AddHandler("application/json", new NewtonsoftJsonSerializer());
    client.AddHandler("text/json", new NewtonsoftJsonSerializer());
    client.AddHandler("text/x-json", new NewtonsoftJsonSerializer());
    client.AddHandler("text/javascript", new NewtonsoftJsonSerializer());
    client.AddHandler("*+json", new NewtonsoftJsonSerializer());

    return client;
}
```