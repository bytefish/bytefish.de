title: Scheduling Messages with Quartz.NET
date: 2019-02-17 19:33
tags: quartz, csharp, dotnet
category: timeseries
slug: scheduling_with_quartz_net
author: Philipp Wagner
summary: This article shows how to schedule jobs with Quartz.NET.

Every sufficiently large project requires some kind of job scheduling at a point: Sending mails at night, 
scheduling push messages to be sent at specific times or executing other periodic tasks.

There was question in the [FcmSharp] issue tracker on how to schedule Push messages. Firebase Cloud Messaging 
does not support it out of the box, but the question makes a very nice excuse to learn how to work with 
[Quartz.NET] in .NET Core. ::smiling_face_with_halo::

In this post I want to show how to schedule Firebase Push Messages using Quartz.NET. As usual all code 
to reproduce this post can be found in my GitHub repository at:

* [https://github.com/bytefish/FcmSharp/tree/master/FcmSharp/Examples/CSharp/FcmSharp.Scheduler.Quartz](https://github.com/bytefish/FcmSharp/tree/master/FcmSharp/Examples/CSharp/FcmSharp.Scheduler.Quartz)

## Project Structure ##

The best way to explain a solution is to look at the project structure first and then break it down:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/scheduling_with_quartz_net/project.png">
        <img src="/static/images/blog/scheduling_with_quartz_net/project.png">
    </a>
</div>

## Getting the Data Right ##

Starting a project always starts with the data, because: If you get the entities in your problem right, then chance 
is good you have a slight clue of how things work. 

Every message has a *Status*, that will be defined in the ``StatusEnum``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace FcmSharp.Scheduler.Quartz.Database.Model
{
    public enum StatusEnum
    {
        Scheduled = 1,
        Finished = 2,
        Failed = 3
    }
}
```

And a message to be pushed also has a *Topic* it will be sent to, a *Title* and *Body* text. It also has a *Status* and most importantly:
 a *Scheduled Time* to be sent at:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace FcmSharp.Scheduler.Quartz.Database.Model
{
    public class Message
    {
        public int Id { get; set; }

        public string Topic { get; set; }

        public string Title { get; set; }

        public string Body { get; set; }

        public StatusEnum Status { get; set; }

        public DateTime ScheduledTime { get; set; }
    }
}
```

### Mapping it to a Database ###

I am using [Entity Framework Core] for all database-related work in C\#, it's a great library. Somehow [Entity Framework Core] has 
to know how to map between the C\# entity and a Database Table. This is configured in an ``IEntityTypeConfiguration`` implementation:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using FcmSharp.Scheduler.Quartz.Database.Model;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace FcmSharp.Scheduler.Quartz.Database.Configuration
{
    public class MessageTypeConfiguration : IEntityTypeConfiguration<Message>
    {
        public void Configure(EntityTypeBuilder<Message> builder)
        {
            builder
                .ToTable("message")
                .HasKey(x => x.Id);

            builder
                .Property(x => x.Id)
                .HasColumnName("message_id")
                .ValueGeneratedOnAdd();

            builder
                .Property(x => x.Topic)
                .HasColumnName("topic")
                .IsRequired();

            builder
                .Property(x => x.Title)
                .HasColumnName("title")
                .IsRequired();

            builder
                .Property(x => x.Body)
                .HasColumnName("body")
                .IsRequired();

            builder
                .Property(x => x.ScheduledTime)
                .HasColumnName("scheduled_time")
                .IsRequired();

            builder
                .Property(x => x.Status)
                .HasConversion<int>()
                .HasColumnName("status_id");
        }
    }
}
```

### Filling it with Data: Seeding Data using the ModelBuilder ###

If your project needs some initial data, you can use the ``ModelBuilder`` to tie data to your entity. I usually just 
define a static class with a static method, where the seeding is done. Keep it simple:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;

namespace FcmSharp.Scheduler.Quartz.Database.Configuration
{
    public static class Seeding
    {
        public static void SeedData(ModelBuilder modelBuilder)
        {
            // Seed initial data here...
        }
    }
}
```

### Accessing the Data using a DbContext ###

[DbContext]: https://docs.microsoft.com/en-us/ef/ef6/fundamentals/working-with-dbcontext
[Unit of Work]: https://martinfowler.com/eaaCatalog/unitOfWork.html
[Repository pattern]: https://www.martinfowler.com/eaaCatalog/repository.html 

Now it comes to getting the data in and out of the database. This is what the ``ApplicationDbContext`` is used for. 

The ``ApplicationDbContext`` extends the [DbContext]. A ``DbContext`` basically is a combination 
of a [Unit of Work] and [Repository pattern], that can be used to query data from a database, track 
changes and write back to the store as a unit.

In [Entity Framework Core] we can override the ``OnModelCreating`` method to apply the database configuration 
and seed the initial data. The sample application uses [SQLite] as database, so there is no additional database 
system to be configured:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using FcmSharp.Scheduler.Quartz.Database.Configuration;
using FcmSharp.Scheduler.Quartz.Database.Model;
using Microsoft.EntityFrameworkCore;

namespace FcmSharp.Scheduler.Quartz.Database
{

    public class ApplicationDbContext : DbContext
    {
        public DbSet<Message> Messages { get; set; }
        
        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlite(@"Data Source=Messaging.db");
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.ApplyConfiguration(new MessageTypeConfiguration());
            
            Seeding.SeedData(modelBuilder);
        }
    }
}
```

## Pushing a Message ##

### Convert the Message ###

[AutoMapper]: https://automapper.org/

The best programmer I know used to tell me: If you know how to convert data correctly, you are 80% done.

So in order to send a message with [FcmSharp], we need to translate our applications ``Message`` into the 
[FcmSharp] ``Message``-representation first. Instead of using [AutoMapper]-reflection-magic (see I am a little 
biased here), you can just write a simple static method for it:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using FcmSharp.Requests;
using SourceType = FcmSharp.Scheduler.Quartz.Database.Model.Message;
using TargetType = FcmSharp.Requests.FcmMessage;

namespace FcmSharp.Scheduler.Quartz.Services.Converters
{
    public static class MessageConverter
    {
        public static TargetType Convert(SourceType source)
        {
            if (source == null)
            {
                return null;
            }

            return new TargetType
            {
                ValidateOnly = false,
                Message = new Message
                {
                    Topic = source.Topic,
                    Notification = new Notification
                    {
                        Title = source.Title,
                        Body = source.Body
                    }
                }
            };
        }
    }
}
```

### Adding a little Logging Abstraction ###

Some people hate me for it, but I usually log the following way: I check if a Log Level is enabled, before 
actually logging the message. This is done, because I sometimes need to prepare the data a little bit for 
debugging and it's not useful to put this into yet another method.

So I first add a set of extension methods to use my Logging style:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Extensions.Logging;

namespace FcmSharp.Scheduler.Quartz.Extensions
{
    public static class LoggerExtensions
    {
        public static bool IsDebugEnabled<TLoggerType>(this ILogger<TLoggerType> logger)
        {
            return logger.IsEnabled(LogLevel.Debug);
        }

        public static bool IsCriticalEnabled<TLoggerType>(this ILogger<TLoggerType> logger)
        {
            return logger.IsEnabled(LogLevel.Critical);
        }

        public static bool IsErrorEnabled<TLoggerType>(this ILogger<TLoggerType> logger)
        {
            return logger.IsEnabled(LogLevel.Error);
        }

        public static bool IsInformationEnabled<TLoggerType>(this ILogger<TLoggerType> logger)
        {
            return logger.IsEnabled(LogLevel.Information);
        }
        
        public static bool IsTraceEnabled<TLoggerType>(this ILogger<TLoggerType> logger)
        {
            return logger.IsEnabled(LogLevel.Trace);
        }
        
        public static bool IsWarningEnabled<TLoggerType>(this ILogger<TLoggerType> logger)
        {
            return logger.IsEnabled(LogLevel.Warning);
        }
    }
}
```

### Sending a Message ###

[Dependency Injection]: https://en.wikipedia.org/wiki/Dependency_injection
[Constructor Injection]: http://misko.hevery.com/2009/02/19/constructor-injection-vs-setter-injection/
[ILogger]: https://docs.microsoft.com/en-us/aspnet/core/fundamentals/logging/?view=aspnetcore-2.2
[IFcmClient]: https://github.com/bytefish/FcmSharp#sending-a-notification

I will now define a ``MessagingService``, that is used to send a Push Message. The ``MessageService`` gets an [ILogger] 
and an [IFcmClient] injected. See I use [Dependency Injection] a lot in projects and when I do it, I do it the right 
way: using [Constructor Injection]. 

The ``ApplicationDbContext`` is used to query for a message and tp update its status on success or failure:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using FcmSharp.Scheduler.Quartz.Database;
using FcmSharp.Scheduler.Quartz.Database.Model;
using FcmSharp.Scheduler.Quartz.Extensions;
using FcmSharp.Scheduler.Quartz.Services.Converters;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;

namespace FcmSharp.Scheduler.Quartz.Services
{
    public interface IMessagingService : IDisposable
    {
        Task SendScheduledMessageAsync(int messageId, CancellationToken cancellationToken);
    }

    public class MessagingService : IMessagingService
    {
        private readonly ILogger<MessagingService> logger;
        private readonly IFcmClient client;

        public MessagingService(ILogger<MessagingService> logger, IFcmClient client)
        {
            this.logger = logger;
            this.client = client;
        }

        public async Task SendScheduledMessageAsync(int messageId, CancellationToken cancellationToken)
        {
            if (logger.IsDebugEnabled())
            {
                logger.LogDebug($"Sending scheduled Message ID {messageId}");
            }

            var message = await GetScheduledMessageAsync(messageId, cancellationToken);

            await SendMessageAsync(message, cancellationToken);
        }

        private async Task SendMessageAsync(Message message, CancellationToken cancellationToken)
        {
            var target = MessageConverter.Convert(message);

            try
            {
                await client.SendAsync(target, cancellationToken);

                if (logger.IsDebugEnabled())
                {
                    logger.LogDebug($"Finished sending Message ID {message.Id}");
                }

                await SetMessageStatusAsync(message, StatusEnum.Finished, cancellationToken);
            }
            catch (Exception exception)
            {
                if (logger.IsErrorEnabled())
                {
                    logger.LogError(exception, $"Error sending Message ID {message.Id}");
                }

                await SetMessageStatusAsync(message, StatusEnum.Failed, cancellationToken);
            }
        }

        private Task<Message> GetScheduledMessageAsync(int messageId, CancellationToken cancellationToken)
        {
            using (var context = new ApplicationDbContext())
            {
                return context.Messages
                    .Where(x => x.Status == StatusEnum.Scheduled)
                    .Where(x => x.Id == messageId)
                    .AsNoTracking()
                    .FirstAsync(cancellationToken);
            }
        }

        private async Task SetMessageStatusAsync(Message message, StatusEnum status, CancellationToken cancellationToken)
        {
            using (var context = new ApplicationDbContext())
            {
                context.Attach(message);

                // Set the new Status Value:
                message.Status = status;

                // Mark the Status as modified, so it is the only updated value:
                context
                    .Entry(message)
                    .Property(x => x.Status).IsModified = true;

                await context.SaveChangesAsync(cancellationToken);
            }
        }

        public void Dispose()
        {
            client?.Dispose();
        }
    }
}
```

### Mocking the FcmClient ###

I don't want to use the real Firebase Cloud Messaging servers for my initial tests, so I write a simple Mock to be injected:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Threading;
using System.Threading.Tasks;
using FcmSharp.Requests;
using FcmSharp.Responses;
using FcmSharp.Scheduler.Quartz.Extensions;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace FcmSharp.Scheduler.Quartz.Testing
{
    public class MockFcmClient : IFcmClient
    {
        private readonly ILogger<MockFcmClient> logger;

        public MockFcmClient(ILogger<MockFcmClient> logger)
        {
            this.logger = logger;
        }

        public Task<FcmMessageResponse> SendAsync(FcmMessage message, CancellationToken cancellationToken = new CancellationToken())
        {
            if (logger.IsDebugEnabled())
            {
                var messageContent = JsonConvert.SerializeObject(message, Formatting.Indented);

                logger.LogDebug($"Sending Message with Content = {messageContent}");
            }

            return Task.FromResult(new FcmMessageResponse());
        }

        public Task<TopicManagementResponse> SubscribeToTopic(TopicManagementRequest request, CancellationToken cancellationToken = new CancellationToken())
        {
            return Task.FromResult(new TopicManagementResponse());
        }

        public Task<TopicManagementResponse> UnsubscribeFromTopic(TopicManagementRequest request, CancellationToken cancellationToken = new CancellationToken())
        {
            return Task.FromResult(new TopicManagementResponse());
        }

        public void Dispose()
        {
        }
    }
}
```

## Scheduling a Message with Quartz.NET ##

The ``IMessagingService`` has dealt with reading a message and pushing it to the Firebase servers. The ``ISchedulerService`` 
now deals with writing the message into the database and scheduling it with [Quartz.NET]. 

There are very few key concepts to understand, when working with [Quartz.NET]:

* ``IScheduler``: The main API for interacting with the scheduler.
* ``IJob``: An interface to be implemented by components that you wish to have executed by the scheduler.
* ``IJobDetail``: Used to define instances of Jobs.
* ``ITrigger``: A component that defines the schedule upon which a given Job will be executed.
* ``JobBuilder``: Used to define/build JobDetail instances, which define instances of Jobs.
* ``TriggerBuilder``: Used to define/build Trigger instances.

### Processing Scheduled Messages ###

We wish to send a Message to Firebase at a Scheduled time, so we first need to implement an ``IJob``. We 
also associate the Message ID with the job, so it can be used to correlate the scheduled message:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Threading.Tasks;
using FcmSharp.Scheduler.Quartz.Services;
using Quartz;

namespace FcmSharp.Scheduler.Quartz.Quartz.Jobs
{
    public class ProcessMessageJob : IJob
    {
        public static readonly string JobDataKey = "MESSAGE_ID";

        private readonly IMessagingService messagingService;

        public ProcessMessageJob(IMessagingService messagingService)
        {
            this.messagingService = messagingService;
        }

        public async Task Execute(IJobExecutionContext context)
        {
            var cancellationToken = context.CancellationToken;
            var messageId = GetMessageId(context);

            await messagingService.SendScheduledMessageAsync(messageId, cancellationToken);
        }

        private int GetMessageId(IJobExecutionContext context)
        {
            JobDataMap jobDataMap = context.JobDetail.JobDataMap;

            return jobDataMap.GetIntValue(JobDataKey);
        }
    }
}
```

It's using a ``JobDataMap`` to store additional data, the Quartz.NET documentation writes on it:

> While a job class that you implement has the code that knows how do do the actual work of the particular type of job, 
> Quartz.NET needs to be informed about various attributes that you may wish an instance of that job to have. This is done 
> via the ``JobDetail`` class.
>
> JobDetail instances are built using the JobBuilder class. JobBuilder allows you to describe your job’s details using a fluent interface.

### A custom JobFactory ###

The ``ProcessMessageJob`` gets an ``IMessagingService`` injected. Quartz.NET uses an ``IJobFactory`` to create the jobs, so I implement 
it using the Dependency Injection container of Microsoft: ``IServiceProvider``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using Quartz;
using Quartz.Spi;

namespace FcmSharp.Scheduler.Quartz.Quartz.JobFactory
{
    public class JobFactory : IJobFactory
    {
        private readonly IServiceProvider container;

        public JobFactory(IServiceProvider container)
        {
            this.container = container;
        }

        public IJob NewJob(TriggerFiredBundle bundle, IScheduler scheduler)
        {
            var jobType = bundle.JobDetail.JobType;

            return container.GetService(jobType) as IJob;
        }

        public void ReturnJob(IJob job)
        {
        }
    }
}
```

### Putting Jobs into the Scheduler ###

The idea is quite easy. There is a Service called ``SchedulerService``, that gets an ``IScheduler`` injected and has a method 
``ScheduleMessageAsync``, which:

1. Saves the Message to the Database.
2. Builds the ``IJobDetail`` to be scheduled.
3. Builds a Trigger to define the Scheduled time.
4. Schedules the Job using the Trigger.
5. Returns the created message.

All this should be done asynchronously to have an asynchronous implementation from top to bottom:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Threading;
using System.Threading.Tasks;
using FcmSharp.Scheduler.Quartz.Database;
using FcmSharp.Scheduler.Quartz.Database.Model;
using FcmSharp.Scheduler.Quartz.Quartz.Jobs;
using Quartz;

namespace FcmSharp.Scheduler.Quartz.Services
{
    public interface ISchedulerService
    {
        Task<Message> ScheduleMessageAsync(Message message, CancellationToken cancellationToken);
    }

    public class SchedulerService : ISchedulerService
    {
        private readonly IScheduler scheduler;

        public SchedulerService(IScheduler scheduler)
        {
            this.scheduler = scheduler;
        }

        public async Task<Message> ScheduleMessageAsync(Message message, CancellationToken cancellationToken)
        {
            await SaveJob(message, cancellationToken);

            IJobDetail job = JobBuilder.Create<ProcessMessageJob>()
                .WithIdentity(Guid.NewGuid().ToString())
                .UsingJobData(ProcessMessageJob.JobDataKey, message.Id)
                .Build();

            ITrigger trigger = TriggerBuilder.Create()
                .WithIdentity(Guid.NewGuid().ToString())
                .StartAt(message.ScheduledTime)
                .Build();

            await scheduler.ScheduleJob(job, trigger, cancellationToken);

            return message;
        }

        private Task SaveJob(Message message, CancellationToken cancellationToken)
        {
            using (var context = new ApplicationDbContext())
            {
                context.Messages.Add(message);

                return context.SaveChangesAsync(cancellationToken);
            }
        }
    }
}
```

## A Web service for scheduling Messages ##

The simplest way to host the scheduler and offer a way to schedule new messages is to self-host a small REST API.

### The Contract ###

The Web service contract looks strikingly similar to the Database model. No matter, always keep the concerns separated 
and define a contract on its own:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace FcmSharp.Scheduler.Quartz.Web.Contracts
{
    public enum StatusEnum
    {
        Scheduled = 1,
        Finished = 2,
        Failed = 3
    }
}
```

The API uses JSON as the Content-Type, so the ``Message`` is attributed with ``JsonProperty`` of the Newtonsoft.JSON library:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using System;

namespace FcmSharp.Scheduler.Quartz.Web.Contracts
{
    public class Message
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("topic")]
        public string Topic { get; set; }

        [JsonProperty("title")]
        public string Title { get; set; }

        [JsonProperty("body")]
        public string Body { get; set; }

        [JsonProperty("status")]
        [JsonConverter(typeof(StringEnumConverter))]
        public StatusEnum Status { get; set; }

        [JsonProperty("scheduledTime")]
        public DateTime ScheduledTime { get; set; }
    }
}
```

### Converting from Contract to Database Model ###

Then there are static methods to convert between the Web service and the Database representation. All this can be done 
in a very simple static class:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;

namespace FcmSharp.Scheduler.Quartz.Web.Converters
{
    public static class MessageConverter
    {
        public static Database.Model.Message Convert(Contracts.Message source)
        {
            if (source == null)
            {
                return null;
            }

            return new Database.Model.Message
            {
                Id = source.Id,
                Topic = source.Topic,
                Title = source.Title,
                Body = source.Body,
                ScheduledTime = source.ScheduledTime,
                Status = Convert(source.Status)
            };
        }

        public static Database.Model.StatusEnum Convert(Contracts.StatusEnum source)
        {
            switch (source)
            {
                case Contracts.StatusEnum.Scheduled:
                    return Database.Model.StatusEnum.Scheduled;
                case Contracts.StatusEnum.Finished:
                    return Database.Model.StatusEnum.Finished;
                case Contracts.StatusEnum.Failed:
                    return Database.Model.StatusEnum.Failed;
                default:
                    throw new ArgumentException($"Unknown Source StatusEnum {source}");
            }
        }

        public static Contracts.Message Convert(Database.Model.Message source)
        {
            if (source == null)
            {
                return null;
            }

            return new Contracts.Message
            {
                Id = source.Id,
                Topic = source.Topic,
                Title = source.Title,
                Body = source.Body,
                ScheduledTime = source.ScheduledTime,
                Status = Convert(source.Status)
            };
        }

        public static Contracts.StatusEnum Convert(Database.Model.StatusEnum source)
        {
            switch (source)
            {
                case Database.Model.StatusEnum.Scheduled:
                    return Contracts.StatusEnum.Scheduled;
                case Database.Model.StatusEnum.Finished:
                    return Contracts.StatusEnum.Finished;
                case Database.Model.StatusEnum.Failed:
                    return Contracts.StatusEnum.Failed;
                default:
                    throw new ArgumentException($"Unknown Source StatusEnum {source}");
            }
        }
    }
}
```

### The Controller ###

The ``SchedulerController`` now exposes the REST interface to the consumer. The ``Route`` attribute is 
used, so a HTTP POST to ``http://localhost:5000/scheduler`` is sufficient for scheduling a new job:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Threading;
using System.Threading.Tasks;
using FcmSharp.Scheduler.Quartz.Services;
using FcmSharp.Scheduler.Quartz.Web.Contracts;
using FcmSharp.Scheduler.Quartz.Web.Converters;
using Microsoft.AspNetCore.Mvc;

namespace FcmSharp.Scheduler.Quartz.Web.Controllers
{
    [Controller]
    [Route("scheduler")]
    public class SchedulerController : ControllerBase
    {
        private readonly ISchedulerService schedulerService;

        public SchedulerController(ISchedulerService schedulerService)
        {
            this.schedulerService = schedulerService;
        }

        [HttpPost]
        public async Task<IActionResult> Post([FromBody] Message message, CancellationToken cancellationToken)
        {
            // Convert into the Database Representation:
            var target = MessageConverter.Convert(message);

            // Save and Schedule:
            var result = await schedulerService.ScheduleMessageAsync(target, cancellationToken);

            return Ok(result);
        }
    }
}
```

## Connecting all the things ##

In the Main method of the Application we build the ``WebHost``, integrate it with the IIS and define the ``Startup`` class 
to be used for bootstrapping the server. I have also set the URL to ``http://localhost:5000`` there:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore;
using Microsoft.AspNetCore.Hosting;

namespace FcmSharp.Scheduler.Quartz
{
    class Program
    {
        public static void Main(string[] args)
        {
            BuildWebHost(args)
                .Run();
        }

        public static IWebHost BuildWebHost(string[] args) =>
            WebHost.CreateDefaultBuilder(args)
                .UseKestrel()
                .UseUrls("http://localhost:5000")
                .UseIISIntegration()
                .UseStartup<Startup>()
                .Build();
    }
}
```

### The Startup class ###

The ``Startup`` class is used to configure the Web server. In it we define all the dependencies in the application, create 
the database and start the [Quartz.NET] scheduler thread:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using FcmSharp.Scheduler.Quartz.Quartz.Jobs;
using FcmSharp.Scheduler.Quartz.Services;
using FcmSharp.Scheduler.Quartz.Testing;
using FcmSharp.Scheduler.Quartz.Web.Extensions;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace FcmSharp.Scheduler.Quartz
{
    public class Startup
    {
        public IHostingEnvironment Environment { get; set; }

        public IConfiguration Configuration { get; }

        public Startup(IHostingEnvironment env)
        {
            Environment = env;

            Configuration = new ConfigurationBuilder()
                .SetBasePath(env.ContentRootPath)
                .AddEnvironmentVariables()
                .Build();
        }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // Add a CORS Policy to allow "Everything":
            services.AddCors(o =>
            {
                o.AddPolicy("Everything", p =>
                {
                    p.AllowAnyHeader()
                        .AllowAnyMethod()
                        .AllowAnyOrigin();
                });
            });

            services
                .AddOptions()
                .AddQuartz()
                .AddTransient<ProcessMessageJob>()
                .AddTransient<IFcmClient, MockFcmClient>()
                .AddTransient<ISchedulerService, SchedulerService>()
                .AddTransient<IMessagingService, MessagingService>()
                .AddMvc();
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env)
        {
            app.EnsureDatabaseCreated()
               .UseCors("Everything")
               .UseStaticFiles()
               .UseQuartz()
               .UseMvc();
        }
    }
}
```

### Quartz Extension ###

I have put the [Quartz.NET] configuration into its own extension methods: ``UseQuartz`` and ``AddQuartz``. You can see, 
that the ``JobFactory`` and the ``IScheduler`` are defined as Singletons, because we want them to be a single instance 
throughout the entire application:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using FcmSharp.Scheduler.Quartz.Quartz.JobFactory;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

using Quartz;
using Quartz.Impl;
using Quartz.Spi;

namespace FcmSharp.Scheduler.Quartz.Web.Extensions
{
    public static class QuartzExtensions
    {
        public static IApplicationBuilder UseQuartz(this IApplicationBuilder app)
        {
            var scheduler = app.ApplicationServices.GetService<IScheduler>();

            scheduler.Start().GetAwaiter().GetResult();

            return app;
        }

        public static IServiceCollection AddQuartz(this IServiceCollection services)
        {
            services.AddSingleton<IJobFactory, JobFactory>();
            services.AddSingleton<IScheduler>(provider =>
            {
                var schedulerFactory = new StdSchedulerFactory();
                var scheduler = schedulerFactory.GetScheduler().GetAwaiter().GetResult();

                scheduler.JobFactory = provider.GetService<IJobFactory>();

                return scheduler;
            });

            return services;
        }
    }
}
```

### Database Extension ###

If we want to put data into the database it must exist of course. The ``EnsureDatabaseCreated`` extension method 
makes sure the database has been created on application startup:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using FcmSharp.Scheduler.Quartz.Database;
using Microsoft.AspNetCore.Builder;

namespace FcmSharp.Scheduler.Quartz.Web.Extensions
{
    public static class DatabaseExtensions
    {
        public static IApplicationBuilder EnsureDatabaseCreated(this IApplicationBuilder app)
        {
            using (var context = new ApplicationDbContext())
            {
                context.Database.EnsureCreated();
            }

            return app;
        }
    }
}
```

## Conclusion ##

And that's it. You can now boot the service and schedule Firebase messages by posting messages to ``http://localhost:5000/scheduler``:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/scheduling_with_quartz_net/postman.png">
        <img src="/static/images/blog/scheduling_with_quartz_net/postman.png">
    </a>
</div>


[SQLite]: https://www.sqlite.org
[Entity Framework Core]: https://docs.microsoft.com/en-us/ef/core/
[Quartz.NET]: https://github.com/quartznet/quartznet
[FcmSharp]: https://github.com/bytefish/FcmSharp
