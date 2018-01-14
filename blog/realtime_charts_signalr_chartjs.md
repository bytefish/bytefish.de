title: Real-time Charts with ASP.NET Core SignalR and Chart.js
date: 2018-01-07 20:14
tags: csharp, signalr, javascript
category: csharp
slug: realtime_charts_signalr_chartjs
author: Philipp Wagner
summary: This article is an introduction to ASP.NET Core SignalR and Chart.js.

[ASP.NET Core SignalR] has [recently been announced by Microsoft] as:

> [...] a new library for ASP.NET Core developers that makes it incredibly simple to add 
> real-time web functionality to your applications. What is "real-time web" functionality? It's the ability 
> to have your server-side code push content to the connected clients as it happens, in real-time.

So how simple is it really to work with SignalR?

The GitHub repository for this article can be found at:

* [https://github.com/bytefish/SignalRSample](https://github.com/bytefish/SignalRSample)

[recently been announced by Microsoft]: https://blogs.msdn.microsoft.com/webdev/2017/09/14/announcing-signalr-for-asp-net-core-2-0/

## What we are going to build ##

Something everyone wants on their dashboards are Real-time Charts, which display incoming values. 

And with the amazing [Chart.js] library it is really easy to provide great looking Real-time Charts. SignalR will 
be used to send the measurements to the Web application.

<a href="/static/images/blog/realtime_charts_signalr_chartjs/screenshot.jpg">
	<img src="/static/images/blog/realtime_charts_signalr_chartjs/screenshot.jpg" alt="Final Application" />
</a>

## Data Model ##

The Chart should display measurements, so I am first defining a ``Measurement`` model, which will be used in the application:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using Newtonsoft.Json;

namespace SignalRSample.Core.Models
{
    public class Measurement
    {
        [JsonProperty("timestamp")]
        public DateTime Timestamp { get; set; }

        [JsonProperty("value")]
        public double Value { get; set; }

        public override string ToString()
        {
            return string.Format("Measurement (Timestamp = {0}, Value = {1})", Timestamp, Value);
        }
    }
}
```

## SignalR Client ##

### NuGet Packages ###

The first thing is to add the ``Microsoft.AspNetCore.SignalR.Client`` package, which is currently a Pre-Release. I am also 
adding the ``Microsoft.Extensions.Logging`` package, so some basic Logging functionality can be used.

```xml
<PackageReference Include="Microsoft.AspNetCore.SignalR.Client" Version="1.0.0-alpha2-final" />
<PackageReference Include="Microsoft.Extensions.Logging" Version="2.0.0" />
```

### Simulating Measurements ###

The Console Application is responsible for connecting to the SignalR Hub on the Server side and send the Measurements to it. The SignalR 
Server is then responsible to broadcast the Measurements to all SignalR Clients listening on the ``Broadcast`` message: 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.SignalR.Client;
using Microsoft.Extensions.Logging;
using SignalRSample.Core.Models;

namespace SignalRSample.ConsoleApp
{
    public class Program
    {
        private static readonly ILogger logger = CreateLogger("Program");

        public static void Main(string[] args)
        {
            var cancellationTokenSource = new CancellationTokenSource();
            
            Task.Run(() => MainAsync(cancellationTokenSource.Token).GetAwaiter().GetResult(), cancellationTokenSource.Token);
            
            Console.WriteLine("Press Enter to Exit ...");
            Console.ReadLine();

            cancellationTokenSource.Cancel();
        }

        private static async Task MainAsync(CancellationToken cancellationToken)
        {
            var hubConnection = new HubConnectionBuilder()
                .WithUrl("http://localhost:5000/sensor")
                .Build();

            await hubConnection.StartAsync();
            
            // Initialize a new Random Number Generator:
            Random rnd = new Random();

            double value = 0.0d;

            while (!cancellationToken.IsCancellationRequested)
            {
                await Task.Delay(250, cancellationToken);

                // Generate the value to Broadcast to Clients:
                value = Math.Min(Math.Max(value + (0.1 - rnd.NextDouble() / 5.0), -1), 1);

                // Create the Measurement with a Timestamp assigned:
                var measurement = new Measurement() {Timestamp = DateTime.UtcNow, Value = value};

                // Log informations:
                if (logger.IsEnabled(LogLevel.Trace))
                {
                    Console.WriteLine("Broadcasting Measurement to Clients ({0})", measurement);
                }

                // Finally send the value:
                await hubConnection.InvokeAsync("Broadcast", "Sensor", measurement, cancellationToken);
            }

            await hubConnection.DisposeAsync();
        }

        private static ILogger CreateLogger(string loggerName)
        {
            return new LoggerFactory()
                .AddConsole(LogLevel.Trace)
                .CreateLogger(loggerName);
        }
    }
}
```


## SignalR Webserver ##

What's next is the Server, that implements the SignalR Hub and serves the Web application.

### NuGet Packages ###

On the Server-side I am adding the following NuGet References:

```xml
<PackageReference Include="Microsoft.AspNetCore.Cors" Version="2.0.1" />
<PackageReference Include="Microsoft.AspNetCore.Diagnostics" Version="2.0.1" />
<PackageReference Include="Microsoft.AspNetCore.Hosting" Version="2.0.1" />
<PackageReference Include="Microsoft.AspNetCore.Server.Kestrel" Version="2.0.1" />
<PackageReference Include="Microsoft.AspNetCore.SignalR" Version="1.0.0-alpha2-final" />
<PackageReference Include="Microsoft.AspNetCore.StaticFiles" Version="2.0.1" />
<PackageReference Include="Microsoft.Extensions.Configuration.CommandLine" Version="2.0.0" />
<PackageReference Include="Microsoft.Extensions.Logging.Console" Version="2.0.0" />
```

### Program ###

ASP.NET Core allows you to self-host your Web application using the Kestrel Server. The Webserver should serve 
the ``index.html`` with the Real-time Charts, so I am also setting the Content Root of the host. The Content Root 
name defaults to ``wwwroot``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.IO;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace SignalRSample.Web
{
    public class Program
    {
        static void Main(string[] args)
        {
            var config = new ConfigurationBuilder()
                .AddCommandLine(args)
                .Build();

            var host = new WebHostBuilder()
                .UseConfiguration(config)
                .UseSetting(WebHostDefaults.PreventHostingStartupKey, "true")
                .ConfigureLogging(factory =>
                {
                    factory.AddConsole();
                })
                .UseKestrel()
                .UseContentRoot(Directory.GetCurrentDirectory())
                .UseEnvironment("Development")
                .UseStartup<Startup>()
                .Build();

            host.Run();
        }
    }
}
```

### Startup ###

[ASP.NET Core] requires you to write ``Startup`` class, which configures the application and its services. 

In my ``Startup`` code you can see, that I set a CORS policy and add SignalR to the list of Services. You also 
have to map the SignalR Hub Routes using ``app.UseSignalR(...)`` method.


```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.DependencyInjection;
using SignalRSample.Web.Hubs;

namespace SignalRSample.Web
{
    public class Startup
    {
        public void ConfigureServices(IServiceCollection services)
        {
            services.AddSignalR();

            services.AddCors(o =>
            {
                o.AddPolicy("Everything", p =>
                {
                    p.AllowAnyHeader()
                        .AllowAnyMethod()
                        .AllowAnyOrigin();
                });
            });
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }

            app.UseFileServer();

            app.UseCors("Everything");
            
            app.UseSignalR(routes =>
            {
                routes.MapHub<SensorHub>("sensor");
            });
        }
    }
}
```

### SensorHub ###

And now we write the ``SensorHub``, which receives a Measurement and broadcasts it to all registered clients. 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Threading.Tasks;
using Microsoft.AspNetCore.SignalR;
using SignalRSample.Core.Models;

namespace SignalRSample.Web.Hubs
{
    public class SensorHub : Hub
    {
        public Task Broadcast(string sender, Measurement measurement)
        {
            return Clients
                // Do not Broadcast to Caller:
                .AllExcept(new [] { Context.ConnectionId })
                // Broadcast to all connected clients:
                .InvokeAsync("Broadcast", sender, measurement);
        }
    }
}
```

## The Website: Providing Real-time Charts with SignalR and Chart.js ##

### JavaScript libraries: signalr-client and Chart.js ###

First of all we need to obtain the two required JavaScript libraries, the SignalR Client and Chart.js:

```
> npm install @aspnet/signalr-client --save
> npm install chartjs --save
```

This leaves you with a folder ``node_modules``, from which we can easily extract the libraries:

* ``node_modules\@aspnet\signalr-client\dist\browser\signalr-client-1.0.0-alpha2-final.js``
* ``node_modules\chart.js\dist\Chart.bundle.js``

I renamed the files to ``signalr-client.js`` and ``Chart.js``, and put them in the folder ``wwwwroot/js`` so they can be served by the server.

### Using SignalR to update Chart.js charts ###

The index.html simply consists of a ``canvas`` element, which is going to be populated by [Chart.js]. 

With the ``signalr-client`` I am going to first open a connection to the ``SensorHub``, then register on the ``Broadcast`` message 
and finally update the Chart with the received measurement. 

The JavaScript [Chart.js] part was originally written by [Simon Brunel](https://github.com/simonbrunel) and is available [here](https://plnkr.co/Imxwl9OQJuaMepLNy6ly).

```html
<!DOCTYPE html>

<html lang="en" xmlns="http://www.w3.org/1999/xhtml">

<head>
    <meta charset="utf-8" />
    <title>SignalR Real-time Chart Example</title>
    <script src="js/Chart.js"></script>
    <script src="js/signalr-client.js"></script>
    <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {
            // Real-time Chart Example written by Simon Brunel (Plunker: https://plnkr.co/edit/Imxwl9OQJuaMepLNy6ly?p=info)
            var samples = 100;
            var speed = 250;
            var values = [];
            var labels = [];
            var charts = [];
            var value = 0;

            values.length = samples;
            labels.length = samples;
            values.fill(0);
            labels.fill(0);

            var chart = new Chart(document.getElementById("chart"),
                {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                data: values,
                                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                                borderColor: 'rgb(255, 99, 132)',
                                borderWidth: 2,
                                lineTension: 0.25,
                                pointRadius: 0
                            }
                        ]
                    },
                    options: {
                        responsive: false,
                        animation: {
                            duration: speed * 1.5,
                            easing: 'linear'
                        },
                        legend: false,
                        scales: {
                            xAxes: [
                                {
                                    display: false
                                }
                            ],
                            yAxes: [
                                {
                                    ticks: {
                                        max: 1,
                                        min: -1
                                    }
                                }
                            ]
                        }
                    }
                });

            var connection = new signalR.HubConnection("sensor");

            connection.on('Broadcast',
                function(sender, message) {
                    values.push(message.value);
                    values.shift();

                    chart.update();
                });

            connection.start();
        });
    </script>

</head>

<body>
    <canvas id="chart" style="width: 512px; height: 320px"></canvas>
</body>

</html>
```

Amazingly, this is already everything!

## Conclusion ##

And that's it! 

Start the Server, start the client, connect to ``http://localhost:5000`` and enjoy the magic.

It was really refreshing to work with [ASP.NET Core SignalR]. Although I have no clue about how Websockets 
work and almost no experience in JavaScript: I got a chart with real-time updates running within minutes!

Hats off to the [ASP.NET Core] Team!

[ASP.NET Core]: https://github.com/aspnet
[Chart.js]: http://www.chartjs.org/
[ASP.NET Core SignalR]: https://github.com/aspnet/SignalR