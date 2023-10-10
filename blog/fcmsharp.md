﻿title: Firebase Cloud Messaging (FCM) with .NET
date: 2018-04-22 13:15
tags: dotnet, csharp, fcmsharp, fcm
category: csharp
slug: fcmsharp
author: Philipp Wagner
summary: This article shows how to work with FcmSharp for Firebase Cloud Messaging in C#.

For one of my .NET projects I needed a simple way to send Push Messages with Firebase Cloud Messaging (FCM), so I wrote [FcmSharp]:

* [https://github.com/bytefish/FcmSharp](https://github.com/bytefish/FcmSharp)

[FcmSharp] implements the Firebase Cloud Messaging HTTP v1 API:

* [https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages)

[FcmSharp] supports .NET Core as of Version 1.0.0.

## Installing FcmSharp ##

You can use [NuGet](https://www.nuget.org) to install [FcmSharp]. Run the following command 
in the [Package Manager Console](http://docs.nuget.org/consume/package-manager-console).

```
PM> Install-Package FcmSharp
```

## Quickstart ##

The Quickstart shows you how to work with [FcmSharp] in C#.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;
using System.Threading;
using FcmSharp.Requests;
using FcmSharp.Settings;

namespace FcmSharp.Console
{
    internal class Program
    {
        public static void Main(string[] args)
        {
            // Read the Credentials from a File, which is not under Version Control:
            var settings = FileBasedFcmClientSettings.CreateFromFile("your_app", @"D:\credentials.json");

            // Construct the Client:
            using (var client = new FcmClient(settings))
            {
                // Construct the Data Payload to send:
                var data = new Dictionary<string, string>()
                {
                    {"A", "B"},
                    {"C", "D"}
                };

                // The Message should be sent to the News Topic:
                var message = new FcmMessage()
                {
                    ValidateOnly = false,
                    Message = new Message
                    {
                        Topic = "news",
                        Data = data
                    }
                };
                
                // Finally send the Message and wait for the Result:
                CancellationTokenSource cts = new CancellationTokenSource();

                // Send the Message and wait synchronously:
                var result = client.SendAsync(message, cts.Token).GetAwaiter().GetResult();

                // Print the Result to the Console:
                System.Console.WriteLine("Message ID = {0}", result.Name);

                System.Console.ReadLine();
            }
        }
    }
}
```

## How to do Synchronous API Calls ##

The ``FcmClient`` only provides an asynchronous API, and a synchronous API won't be added. I know that 
asynchronous programming can be very challenging for beginners, so here is how you can turn an async 
call into a synchronous one:

```csharp
var result = client.SendAsync(message, cts.Token).GetAwaiter().GetResult();
```

[FcmSharp]: https://github.com/bytefish/FcmSharp
[Firebase Quickstart with Android]: https://github.com/firebase/quickstart-android/tree/master/messaging
[Firebase Cloud Messaging (FCM) API]: https://firebase.google.com
[Firebase Cloud Messaging HTTP Protocol]: https://firebase.google.com/docs/cloud-messaging/http-server-ref