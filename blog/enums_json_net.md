title: Serializing and Deserializing Enumerations with Json.NET 
date: 2015-11-07 13:22
tags: c#, rest, software design
category: c#
slug: enums_json_net
author: Philipp Wagner
summary: This article describes how to serialize and deserialize enums with Json.NET.

[Json.NET]: http://www.newtonsoft.com/json
[GcmSharp]: https://github.com/bytefish/GcmSharp
[MIT License]: https://opensource.org/licenses/MIT

This article shows you how to serialize and deserialize enums with [Json.NET]. 

If you write a client for a RESTful API, then you often have to deal with error codes. In a typed language like C# you should never throw strings at the 
user of your API client (for your users sanity), so error codes need to be converted from their string representation into an enumeration of your library.

Some time ago I have written [GcmSharp], which is a client for the Google Cloud Messaging (GCM) API. This example is based on the implementation at:

* [https://github.com/bytefish/GcmSharp](https://github.com/bytefish/GcmSharp)

The error codes for the Google Cloud Messaging API are described in the [HTTP Server Reference: Error Codes](https://developers.google.com/cloud-messaging/http-server-ref#error-codes).

## ErrorCode Enum ##

First of all we are going to define the enum, that matches the error codes in the documentation ([HTTP Server Reference: Error Codes](https://developers.google.com/cloud-messaging/http-server-ref#error-codes)).

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace GcmSharp.Responses
{
    public enum ErrorCode
    {
        InvalidRegistration,
        NotRegistered,
        MessageTooBig,
        MissingRegistration,
        Unavailable,
        MismatchSenderId,
        InvalidDataKey,
        InvalidTtl,
        InternalServerError,
        InvalidPackageName,
        DeviceMessageRateExceeded,
        TopicsMessageRateExceeded
    }
}
```

## ErrorCodeConverter ##

Next we define a custom [JsonConverter](http://www.newtonsoft.com/json/help/html/T_Newtonsoft_Json_JsonConverter.htm), which is going to be used by [Json.NET] for serialization and deserialization.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Newtonsoft.Json;
using System;

namespace GcmSharp.Responses.Converter
{
    public class ErrorCodeConverter : JsonConverter
    {
        public override void WriteJson(JsonWriter writer, object value, JsonSerializer serializer)
        {
            ErrorCode messageTransportResponseStatus = (ErrorCode)value;

            switch (messageTransportResponseStatus)
            {
                case ErrorCode.MissingRegistration:
                    writer.WriteValue("MissingRegistration");
                    break;
                case ErrorCode.InvalidRegistration:
                    writer.WriteValue("InvalidRegistration");
                    break;
                case ErrorCode.NotRegistered:
                    writer.WriteValue("NotRegistered");
                    break;
                case ErrorCode.InvalidPackageName:
                    writer.WriteValue("InvalidPackageName");
                    break;
                case ErrorCode.MismatchSenderId:
                    writer.WriteValue("MismatchSenderId");
                    break;
                case ErrorCode.MessageTooBig:
                    writer.WriteValue("MessageTooBig");
                    break;
                case ErrorCode.InvalidDataKey:
                    writer.WriteValue("InvalidDataKey");
                    break;
                case ErrorCode.InvalidTtl:
                    writer.WriteValue("InvalidTtl");
                    break;
                case ErrorCode.Unavailable:
                    writer.WriteValue("Unavailable");
                    break;
                case ErrorCode.InternalServerError:
                    writer.WriteValue("InternalServerError");
                    break;
                case ErrorCode.DeviceMessageRateExceeded:
                    writer.WriteValue("DeviceMessageRateExceeded");
                    break;
                case ErrorCode.TopicsMessageRateExceeded:
                    writer.WriteValue("TopicsMessageRateExceeded");
                    break;
            }
        }

        public override object ReadJson(JsonReader reader, Type objectType, object existingValue, JsonSerializer serializer)
        {
            var enumString = (string)reader.Value;

            return Enum.Parse(typeof(ErrorCode), enumString, true);
        }

        public override bool CanConvert(Type objectType)
        {
            return objectType == typeof(string);
        }
    }
}
```

## Using the JsonConverter for your Object ##

All you have to do now is to annotate your ``ErrorCode`` property with a [JsonConverter attribute](http://www.newtonsoft.com/json/help/html/T_Newtonsoft_Json_JsonConverterAttribute.htm).

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GcmSharp.Responses;
using GcmSharp.Responses.Converter;
using Newtonsoft.Json;

namespace GcmSharp.Test.Responses.Converter
{
    public class SampleEntity
    {
        [JsonProperty("error")]
        [JsonConverter(typeof(ErrorCodeConverter))]
        public ErrorCode Error { get; set; }
    }
}
```

## Unit Test ##

And finally we can write some [Unit Tests](https://en.wikipedia.org/wiki/Unit_testing) to ensure everything works correctly.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using GcmSharp.Responses;
using Newtonsoft.Json;
using NUnit.Framework;
using System.Collections.Generic;

namespace GcmSharp.Test.Responses.Converter
{
    [TestFixture]
    public class ErrorCodeConverterTest
    {
        [Test]
        public void DeserializeErrorCodeTest()
        {
            Dictionary<string, ErrorCode> expectations = GetErrorCodeMapping();

            foreach (var kv in expectations)
            {
                var jsonString = string.Format("{{ \"error\" : \"{0}\" }}", kv.Key);
                var deserializedObject = JsonConvert.DeserializeObject<SampleEntity>(jsonString);
                Assert.AreEqual(kv.Value, deserializedObject.Error);
            }
        }

        [Test]
        public void SerializeErrorCodeTest()
        {
            Dictionary<string, ErrorCode> expectations = GetErrorCodeMapping();

            foreach (var kv in expectations)
            {
                var obj = new SampleEntity { Error = kv.Value };
                
                var expectedJsonString = string.Format("{{\"error\":\"{0}\"}}", kv.Key);
                var actualJsonString = JsonConvert.SerializeObject(obj);

                Assert.AreEqual(expectedJsonString, actualJsonString);
            }
        }

        private Dictionary<string, ErrorCode> GetErrorCodeMapping()
        {
            return new Dictionary<string, ErrorCode>()
            {
                { "MissingRegistration", ErrorCode.MissingRegistration},
                { "InvalidRegistration", ErrorCode.InvalidRegistration},
                { "NotRegistered", ErrorCode.NotRegistered},
                { "InvalidPackageName", ErrorCode.InvalidPackageName},
                { "MismatchSenderId", ErrorCode.MismatchSenderId},
                { "MessageTooBig", ErrorCode.MessageTooBig},
                { "InvalidDataKey", ErrorCode.InvalidDataKey},
                { "InvalidTtl", ErrorCode.InvalidTtl},
                { "Unavailable", ErrorCode.Unavailable},
                { "InternalServerError", ErrorCode.InternalServerError},
                { "DeviceMessageRateExceeded",ErrorCode.DeviceMessageRateExceeded },
                { "TopicsMessageRateExceeded", ErrorCode.TopicsMessageRateExceeded},
            };
        }
    }
}
```