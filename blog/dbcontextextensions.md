title: DbContextExtensions: An approach to managing the EF Core DbContext 
date: 2021-10-17 21:04
tags: dotnet, architecture
category: dotnet
slug: dbcontextextensions
author: Philipp Wagner
summary: Extensions for EntityFramework Core to simplify building application.

EntityFramework Core is a magnificient piece of technology. Just extend a ``DbContext``, add some ``DbSet`` and 
off you go to query the database. In this article I will discuss a little library I am working on to simplify 
working with EntityFramework Core even a little more.

You can find it at:

* [https://github.com/bytefish/DbContextExtensions](https://github.com/bytefish/DbContextExtensions)

It can be installed with [NuGet](https://www.nuget.org/) with the following command in the 
[Package Manager Console](http://docs.nuget.org/consume/package-manager-console):

```
PM> Install-Package DbContextScope.Core
```

## DbContextScope: Scoping the DbContext for a simpler Software Architecture ##

I like starting out with a simple Software Architecture. Life is complicated enough. 

For an EF Core-based application I want to know exactely: 

* *Who* created my ``DbContext``?
* *How* is it passed through the application?
* *Who* actually writes the changes to the database? 
* *When* are those changes written?

### So yes... Who actually calls SaveChanges on my DbContext? ###

If you are following the official documentation and tutorials on EF Core, then most probably the Dependency Injection 
container is responsible for creating and disposing your ``DbContext`` instances. The lifetime of a ``DbContext`` then 
is often bound to a requests lifetime. 

The official documentation and tutorials suggest to pass the ``DbContext`` using constructor injection. We can find the 
following example in the Microsoft docs on "Implementing the infrastructure persistence layer with Entity Framework Core":

```csharp
namespace Microsoft.eShopOnContainers.Services.Ordering.Infrastructure.Repositories
{
    public class BuyerRepository : IBuyerRepository
    {
        private readonly OrderingContext _context;

        public BuyerRepository(OrderingContext context)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
        }

        public Buyer Add(Buyer buyer)
        {
            return _context.Buyers.Add(buyer).Entity;
        }

        public async Task<Buyer> FindAsync(string buyerIdentityGuid)
        {
            var buyer = await _context.Buyers
                .Include(b => b.Payments)
                .Where(b => b.FullName == buyerIdentityGuid)
                .SingleOrDefaultAsync();

            return buyer;
        }
    }
}
```

Looks simple. Looks clean. Looks *great*.

But it get's complicated as soon as you break out of a Per-Request Scope with its clearly defined boundaries. Say 
what's the correct lifetime of the ``DbContext`` in a Windows Service? Or in a WinForms application? What's the Request 
Scope there?

Not so easy to answer.

*How* and *when* does the Dependency Injection Container, arguably an infrastructure level component, instantiate and 
dispose a ``DbContext`` in such a scenario? Is the DI container really the correct place to start and end a Business 
Transaction? Why should it dictate the lifetime of your business transaction?

Again not so easy to answer.

And if my Service-layer wasn't responsible for creating the ``DbContext``, then why is my Service-layer responsible 
to commit or rollback it at all? And how do I make sure, that the ``DbContext`` wasn't reused beyond the scope of the 
Business Transaction? Remember you do not control its lifetime, the DI container does...

Again no simple answers here.

The only fool-proof way I can think of is:

* Take a dependency on an ``IDbContextFactory<TContext>``
    * Create a ``DbContext`` when we start the Business Transaction.
* Pass a ``DbContext`` as a parameter into Repositories. 
    * Repositories and Services then no longer carry the ``DbContext`` and everything can be registered as a ``Singleton``.

This is making the DI Container configuration much, much simpler to reason about:

```csharp
// Repository ...
public class BuyerRepository
{
    public Buyer Add(OrderingContext context, Buyer buyer)
    {
        return context.Buyers.Add(buyer).Entity;
    }

    public async Task<Buyer> FindAsync(OrderingContext context, string buyerIdentityGuid)
    {
        var buyer = await context.Buyers
            .Include(b => b.Payments)
            .Where(b => b.FullName == buyerIdentityGuid)
            .SingleOrDefaultAsync();

        return buyer;
    }
}

// Service ...
public class BuyerService
{
    private readonly IDbContextFactory<OrderingContext> dbContextFactory;

    public BuyerRepository(IDbContextFactory<OrderingContext> dbContextFactory, IBuyerRepository buyerRepository)
    {
        this.dbContextFactory = dbContextFactory;
    }

    public Buyer Add(Buyer buyer)
    {
        using(var context = dbContextFactory.Create()) 
        {
            return buyerRepository.Add(context, buyer);
        }
    }
    
    // ...
}
``` 

The questionable and potentially dangerous passing of the ``DbContext`` directly into a repository aside... this probably works great, as long 
as 1 Service method equals 1 Business Transaction. But what happens, if I need to coordinate between multiple Service-level methods? What if two 
methods need to call each other? 

In the above example both methods create a separate ``DbContext``? Bad. Should they use the same instance? I don't know. 

Not easy to say.

#### And how does Microsoft work with the EF Core DbContext? ####

That makes me think: Are my software architecture skills really so, so poor? Am I too stupid? Do I probably get it all wrong here? Am I 
overthinking it? Could all these issues be solved using some magical CQRS-style architecture, that's all the hype? But still with Commands 
and all that we'll need to design all layers below the Commands, no? And there... we'll come back to all questions above.

So. Microsoft has a DDD example project "eShopOnContainers", which is their ".NET Microservices Sample Reference Application". It uses EF Core 
in one of its Microservices so... how does Microsoft address some of my questions? Let's take a deep dive into the implementation of the Order 
Microservice (*a single Microservice*), to validate or invalidate my concerns.

Looking at the ``Startup`` Dependency Injection configuration for the Ordering Web service we can see, that the ``DbContext`` 
(``OrderingContext``) is scoped to the Lifetime of the Request. There is even a nice comment on how the graph of objects 
starts within the HTTP request ([Permalink](https://github.com/dotnet-architecture/eShopOnContainers/blob/46219957ef763305030a0924d039fe4a25831b06/src/Services/Ordering/Ordering.API/Startup.cs#L235)):

```csharp
// ...

services.AddDbContext<OrderingContext>(options =>
       {
           options.UseSqlServer(configuration["ConnectionString"],
               sqlServerOptionsAction: sqlOptions =>
               {
                   sqlOptions.MigrationsAssembly(typeof(Startup).GetTypeInfo().Assembly.GetName().Name);
                   sqlOptions.EnableRetryOnFailure(maxRetryCount: 15, maxRetryDelay: TimeSpan.FromSeconds(30), errorNumbersToAdd: null);
               });
       },
           ServiceLifetime.Scoped  //Showing explicitly that the DbContext is shared across the HTTP request scope (graph of objects started in the HTTP request)
       );

// ...
```

Looks good to me! 👍 

The ``DbContext`` then is abstracted away behind an ``IUnitOfWork`` inteface and injected down into repositories:

```csharp
using System;
// ...

namespace Microsoft.eShopOnContainers.Services.Ordering.Infrastructure.Repositories
{
    public class OrderRepository
        : IOrderRepository
    {
        private readonly OrderingContext _context;

        public IUnitOfWork UnitOfWork
        {
            get
            {
                return _context;
            }
        }

        public OrderRepository(OrderingContext context)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
        }

        public Order Add(Order order)
        {
            return _context.Orders.Add(order).Entity;
        }
        
        // ...
   }
}
```

These repositories in turn are injected to a MediatR ``IRequestHandler`` implementation, which basically contains the business logic to 
handle an incoming requests to a Web service endpoint. Everything looks good so far. We can see, that through some layers of indirection 
a ``SaveChanges`` is called on the underlying ``OrderingContext``:

```csharp
namespace Microsoft.eShopOnContainers.Services.Ordering.API.Application.Commands
{
    // ...

    // Regular CommandHandler
    public class CreateOrderCommandHandler
        : IRequestHandler<CreateOrderCommand, bool>
    {
        private readonly IOrderRepository _orderRepository;
        private readonly IIdentityService _identityService;
        private readonly IMediator _mediator;
        private readonly IOrderingIntegrationEventService _orderingIntegrationEventService;
        private readonly ILogger<CreateOrderCommandHandler> _logger;

        // Using DI to inject infrastructure persistence Repositories
        public CreateOrderCommandHandler(IMediator mediator,
            IOrderingIntegrationEventService orderingIntegrationEventService,
            IOrderRepository orderRepository,
            IIdentityService identityService,
            ILogger<CreateOrderCommandHandler> logger)
        {
            // ...
        }

        public async Task<bool> Handle(CreateOrderCommand message, CancellationToken cancellationToken)
        {
            // Add Integration event to clean the basket
            var orderStartedIntegrationEvent = new OrderStartedIntegrationEvent(message.UserId);

            await _orderingIntegrationEventService.AddAndSaveEventAsync(orderStartedIntegrationEvent);

            // Add/Update the Buyer AggregateRoot
            // DDD patterns comment: Add child entities and value-objects through the Order Aggregate-Root
            // methods and constructor so validations, invariants and business logic 
            // make sure that consistency is preserved across the whole aggregate
            var address = new Address(message.Street, message.City, message.State, message.Country, message.ZipCode);
            var order = new Order(message.UserId, message.UserName, address, message.CardTypeId, message.CardNumber, message.CardSecurityNumber, message.CardHolderName, message.CardExpiration);

            foreach (var item in message.OrderItems)
            {
                order.AddOrderItem(item.ProductId, item.ProductName, item.UnitPrice, item.Discount, item.PictureUrl, item.Units);
            }

            _logger.LogInformation("----- Creating Order - Order: {@Order}", order);

            _orderRepository.Add(order);

            return await _orderRepository.UnitOfWork.SaveEntitiesAsync(cancellationToken);
        }
    }
    
    // ...
}
```

Now here comes the interesting thing. 

Can you tell me *when* changes are actually written to the database just from looking at this? 

* *Who* is calling the actual ``SaveChanges`` on the ``DbContext``?
* *When*  are the changes written to the database? 

Is it called from the ``AddAndSaveEventAsync`` method? Because it's entirely possible... the ``OrderingIntegrationEventService`` takes 
a dependency on the ``OrderingContext``. Or does it happen in the final call to the ``_orderRepository.UnitOfWork.SaveEntitiesAsync``? 
Totally possible.

It's not that simple. 

Actually the ``Order`` here is an "``IAggregateRoot``" and its constructor raises a ``OrderStartedDomainEvent``, see here:

```csharp
// ...

namespace Microsoft.eShopOnContainers.Services.Ordering.Domain.AggregatesModel.OrderAggregate
{
    public class Order
        : Entity, IAggregateRoot
    {
        // ...
        
        public Order(string userId, string userName, Address address, int cardTypeId, string cardNumber, string cardSecurityNumber,
                string cardHolderName, DateTime cardExpiration, int? buyerId = null, int? paymentMethodId = null) : this()
        {
            //...
            
            // Add the OrderStarterDomainEvent to the domain events collection 
            // to be raised/dispatched when comitting changes into the Database [ After DbContext.SaveChanges() ]
            AddOrderStartedDomainEvent(userId, userName, cardTypeId, cardNumber, cardSecurityNumber, cardHolderName, cardExpiration);
        }
    }
}
```

This ``DomainEvent`` is added to a List of Domain Events in the ``Order`` Entity itself. And who handles an ``OrderStartedDomainEvent``? It's handled 
by the ``ValidateOrAddBuyerAggregateWhenOrderStartedDomainEventHandler``, that actually also calls a ``SaveEntitiesAsync`` on the underlying context 
as we learn:

```csharp
//...

namespace Ordering.API.Application.DomainEventHandlers.OrderStartedEvent
{
    public class ValidateOrAddBuyerAggregateWhenOrderStartedDomainEventHandler
                        : INotificationHandler<OrderStartedDomainEvent>
    {
        private readonly ILoggerFactory _logger;
        private readonly IBuyerRepository _buyerRepository;
        private readonly IIdentityService _identityService;
        private readonly IOrderingIntegrationEventService _orderingIntegrationEventService;

        public ValidateOrAddBuyerAggregateWhenOrderStartedDomainEventHandler(
            ILoggerFactory logger,
            IBuyerRepository buyerRepository,
            IIdentityService identityService,
            IOrderingIntegrationEventService orderingIntegrationEventService)
        {
            // ...
        }

        public async Task Handle(OrderStartedDomainEvent orderStartedEvent, CancellationToken cancellationToken)
        {
            // ...
            
            await _buyerRepository.UnitOfWork.SaveEntitiesAsync(cancellationToken);

            // ...
        }
    }
}
```

If we look into the ``IBuyerRepository`` implementation we'll find it's the same ``OrderingContext`` used for the ``IOrderRepository``:

```csharp
//...

namespace Microsoft.eShopOnContainers.Services.Ordering.Infrastructure.Repositories
{
    public class BuyerRepository
        : IBuyerRepository
    {
        private readonly OrderingContext _context;
        public IUnitOfWork UnitOfWork
        {
            get
            {
                return _context;
            }
        }

        public BuyerRepository(OrderingContext context)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
        }
        
        // ...
}
```

Can you still follow me? Is it really the same ``OrderingContext`` for both the ``BuyerRepository`` and the ``OrderRepository``? I guess... I mean, 
*I don't know*? That probably depends on who actually *executes* Domain Events? Or is it configured in the DI container? I don't research this for 
now.

*Who* executes the Domain Events? It's the ``OrderingContext`` itself! 

We can find the following implementation in the ``OrderingContext``:

```csharp
// ...

namespace Microsoft.eShopOnContainers.Services.Ordering.Infrastructure
{
    public class OrderingContext : DbContext, IUnitOfWork
    {
        // ...

        public async Task<bool> SaveEntitiesAsync(CancellationToken cancellationToken = default(CancellationToken))
        {
            // Dispatch Domain Events collection. 
            // Choices:
            // A) Right BEFORE committing data (EF SaveChanges) into the DB will make a single transaction including  
            // side effects from the domain event handlers which are using the same DbContext with "InstancePerLifetimeScope" or "scoped" lifetime
            // B) Right AFTER committing data (EF SaveChanges) into the DB will make multiple transactions. 
            // You will need to handle eventual consistency and compensatory actions in case of failures in any of the Handlers. 
            await _mediator.DispatchDomainEventsAsync(this);

            // After executing this line all the changes (from the Command Handler and Domain Event Handlers) 
            // performed through the DbContext will be committed
            var result = await base.SaveChangesAsync(cancellationToken);

            return true;
        }
    }
}
```

``DispatchDomainEventsAsync`` is an extension method, that gets all ``Entity`` objects in the ``DbContext``, that have Domain Events 
attached. It then saves these Domain Events in a temporary list, clears the Domain Events in all entities and then executes the Domain 
Events one-by-one:

```csharp
// ...

static class MediatorExtension
{
    public static async Task DispatchDomainEventsAsync(this IMediator mediator, OrderingContext ctx)
    {
        var domainEntities = ctx.ChangeTracker
            .Entries<Entity>()
            .Where(x => x.Entity.DomainEvents != null && x.Entity.DomainEvents.Any());

        var domainEvents = domainEntities
            .SelectMany(x => x.Entity.DomainEvents)
            .ToList();

        domainEntities.ToList()
            .ForEach(entity => entity.Entity.ClearDomainEvents());

        foreach (var domainEvent in domainEvents)
            await mediator.Publish(domainEvent);
    }
}
```

Now back to my original question: 

* *Who* calls ``DbContext#SaveChanges``? 

The moment we called ``_orderRepository.UnitOfWork.SaveEntitiesAsync(cancellationToken)`` in the Command Handler, we are dispatching the Domain Events first. 
So the first ``SaveChanges`` on the ``OrderingContext`` is actually done by the ``ValidateOrAddBuyerAggregateWhenOrderStartedDomainEventHandler``, because it 
uses the same ``OrderingContext``.

Does it have side-effects to operate on the same ``DbContext`` and commit it to the database mutliple times? Isn't each handler there using its own 
transaction then? How could you rollback the whole thing into a consistent state then? How do we solve such an issue? 

Yes exactely, by wrapping it all in a Transaction... regardless if needed one or not:

```csharp
public class TransactionBehaviour<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
{
    private readonly ILogger<TransactionBehaviour<TRequest, TResponse>> _logger;
    private readonly OrderingContext _dbContext;
    private readonly IOrderingIntegrationEventService _orderingIntegrationEventService;

    public TransactionBehaviour(OrderingContext dbContext,
        IOrderingIntegrationEventService orderingIntegrationEventService,
        ILogger<TransactionBehaviour<TRequest, TResponse>> logger)
    {
        _dbContext = dbContext ?? throw new ArgumentException(nameof(OrderingContext));
        _orderingIntegrationEventService = orderingIntegrationEventService ?? throw new ArgumentException(nameof(orderingIntegrationEventService));
        _logger = logger ?? throw new ArgumentException(nameof(ILogger));
    }

    public async Task<TResponse> Handle(TRequest request, CancellationToken cancellationToken, RequestHandlerDelegate<TResponse> next)
    {
        var response = default(TResponse);
        var typeName = request.GetGenericTypeName();

        try
        {
            if (_dbContext.HasActiveTransaction)
            {
                return await next();
            }

            var strategy = _dbContext.Database.CreateExecutionStrategy();

            await strategy.ExecuteAsync(async () =>
            {
                Guid transactionId;

                using (var transaction = await _dbContext.BeginTransactionAsync())
                using (LogContext.PushProperty("TransactionContext", transaction.TransactionId))
                {
                    _logger.LogInformation("----- Begin transaction {TransactionId} for {CommandName} ({@Command})", transaction.TransactionId, typeName, request);

                    response = await next();

                    _logger.LogInformation("----- Commit transaction {TransactionId} for {CommandName}", transaction.TransactionId, typeName);

                    await _dbContext.CommitTransactionAsync(transaction);

                    transactionId = transaction.TransactionId;
                }

                await _orderingIntegrationEventService.PublishEventsThroughEventBusAsync(transactionId);
            });

            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "ERROR Handling transaction for {CommandName} ({@Command})", typeName, request);

            throw;
        }
    }
}
```

Please bear with me, this shouldn't come off negative. All I want to say is, that it's not easy to understand the lifetime of a Unit of Work 
in such DDD examples. I find myself knee-deep in Dependency Injection configurations, when trying to understand it and reason about the code. 

I know the eShopOnContainers application serves the purpose to showcase how Domain Driven Design could be implemented in .NET, how Docker and 
Kubernetes can be used. And the eShopOnContainers application probably doesn't need the same strict transactional guarantees as a traditional, 
boring, enterprise CRUD application. 

Still I find it *extremly hard* to understand the lifetime of the ``DbContext`` in the Microservice example.

### DbContextScope: Managing the DbContext in an Ambient way ###

Let's go a different route and manage the ``DbContext`` in an ambient way. The idea for the ``DbContextScope`` is taken from 
Mehdi El Gueddari and his blog post is a perfect explanation on it:

* [https://mehdi.me/ambient-dbcontext-in-ef6/](https://mehdi.me/ambient-dbcontext-in-ef6/)

The idea is to wrap a ``DbContext`` in a ``DbContextScope``, that only allows the outer-most scope to commit 
the actual Unit of Work. It's basically how the ``TransactionScope`` works and it ensures, that all calls 
within the scope are using the same ``DbContext``.

Additionally an exception is thrown, when you attempt to directly call ``SaveChanges`` on the ``DbContext``.

The common usage is like this:

```
using (var dbContextScope = dbContextScopeFactory.Create())
{
    var dbContext = dbContextScope.GetDbContext();

    // Add some fake data:
    await dbContext.Set<Person>()
        .AddAsync(new Person() { FirstName = "Philipp", LastName = "Wagner", BirthDate = new DateTime(2013, 1, 1) });

    dbContextScope1.Complete();
}
```

Just like with the ``TransactionScope``, if you don't call complete on a writable ``DbContextScope`` all changes will be rolled back.

## DbContextScope: Full Example ##

I could write an entire article on it, but understanding the ``DbContextScope`` usage is probably easy by looking at an example. 

As with the *Tour of Heroes* in Angular, we want to build a small application to manage Heroes and their Superpowers. It 
should follow a simple Layered Architecture approach with a Domain Model, Business Layer and a Data Abstraction Layer. We 
want to use Entity Framework Core to provide the persistence.

### Domain Model: Our Heroes and Superpowers ###

A ``Hero`` has a Name and a list of Superpowers.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Test.Utils;
using System.Collections.Generic;

namespace DbContextExtensions.Test.Example.Entities
{
    /// <summary>
    /// A Hero.
    /// </summary>
    public class Hero
    {
        /// <summary>
        /// Primary Key.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Name.
        /// </summary>
        public string Name { get; set; }

        /// <summary>
        /// Superpowers.
        /// </summary>
        public ICollection<Superpower> Superpowers { get; set; }

        /// <summary>
        /// Returns a Hero as a String.
        /// </summary>
        /// <returns>String Representation for a Hero</returns>
        public override string ToString()
        {
            return $"Hero (Id={Id}, Name={Name}, Superpowers=[{StringUtils.ListToString(Superpowers)}])";
        }
    }
}
```

A Superpower has a Name and Description for now. A Superpower can be assigned to many Heroes.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;

namespace DbContextExtensions.Test.Example.Entities
{
    public class Superpower
    {
        /// <summary>
        /// Primary Key.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Name.
        /// </summary>
        public string Name { get; set; }

        /// <summary>
        /// Description.
        /// </summary>
        public string Description { get; set; }

        /// <summary>
        /// Heroes for this Superpower.
        /// </summary>
        public ICollection<Hero> Heroes { get; set; }

        /// <summary>
        /// Returns a Superpower as a String.
        /// </summary>
        /// <returns>String Representation for a Superpower</returns>
        public override string ToString()
        {
            return $"Superpower (Id={Id}, Name={Name})";
        }
    }
}
```

And the ``HeroSuperpower`` is the association table between the Hero and Superpower.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace DbContextExtensions.Test.Example.Entities
{
    /// <summary>
    /// Association Table for a Hero and a Superpower.
    /// </summary>
    public class HeroSuperpower
    {
        /// <summary>
        /// The Hero.
        /// </summary>
        public Hero Hero { get; set; }

        /// <summary>
        /// The Superpower.
        /// </summary>
        public Superpower Superpower { get; set; }

        /// <summary>
        /// Hero FK reference.
        /// </summary>
        public int HeroId { get; set; }

        /// <summary>
        /// Superpower FK reference.
        /// </summary>
        public int SuperpowerId { get; set; }
    }
}
```

### Mappings: Where you are defining your Database structure ###

All Entities implement an ``EntityMap<TEntityType>``, so we know how to map between the database and the Entity classes. 

Please note how the HiLo-Pattern is used to generate temporary Primary Keys, while the Entities aren't commited to the database 
yet. Why? Because only the outer-most scope is going to commit to the database and that's where we would get the PK from, if we 
don't use a HiLo Generated ID.

I think this is one of the most common questions when implementing such an architecture. The alternative would be to commit to the 
database and get a PK, which would somehow... defeat the usage of a Unit of Work, right?

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Mappings;
using DbContextExtensions.Test.Example.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace DbContextExtensions.Test.Example.Database
{
    public class HeroEntityMap : EntityMap<Hero>
    {
        protected override void InternalMap(ModelBuilder model, EntityTypeBuilder<Hero> entity)
        {
            model
                .HasSequence("SeqHero", seq_builder => seq_builder.IncrementsBy(10));

            entity
                .HasKey(x => x.Id);

            entity
                .Property(x => x.Id)
                .UseHiLo("SeqHero")
                .HasColumnName("HeroID");

            entity
                .Property(x => x.Name)
                .HasColumnName("Name")
                .IsRequired();

            entity
                .HasMany(x => x.Superpowers)
                .WithMany(x => x.Heroes)
                .UsingEntity<HeroSuperpower>(
                    configureLeft: j => j.HasOne(x => x.Hero).WithMany().HasForeignKey(x => x.HeroId),
                    configureRight: j => j.HasOne(x => x.Superpower).WithMany().HasForeignKey(x => x.SuperpowerId));
        }
    }
}
```

The Superpower also uses the HiLo-Pattern to generate valid Primary Keys:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Mappings;
using DbContextExtensions.Test.Example.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace DbContextExtensions.Test.Example.Database
{
    public class SuperpowerEntityMap : EntityMap<Superpower>
    {
        protected override void InternalMap(ModelBuilder model, EntityTypeBuilder<Superpower> entity)
        {
            model
                .HasSequence("SeqSuperpower", seq_builder => seq_builder.IncrementsBy(10));

            entity
                .HasKey(x => x.Id);

            entity
                .Property(x => x.Id)
                .UseHiLo("SeqSuperpower")
                .HasColumnName("SuperpowerID");

            entity
                .Property(x => x.Name)
                .HasColumnName("Name")
                .IsRequired();

            entity
                .Property(x => x.Description)
                .HasColumnName("Description");

            entity
                .HasMany(x => x.Heroes)
                .WithMany(x => x.Superpowers)
                .UsingEntity<HeroSuperpower>(
                    configureLeft: j => j.HasOne(x => x.Superpower).WithMany().HasForeignKey(x => x.SuperpowerId),
                    configureRight: j => j.HasOne(x => x.Hero).WithMany().HasForeignKey(x => x.HeroId));
        }
    }
}
```

And finally for the ``HeroSuperpower`` we can add Foreign Keys to enforce consistent data.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Mappings;
using DbContextExtensions.Test.Example.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace DbContextExtensions.Test.Example.Database
{
    public class HeroSuperpowerEntityMap : EntityMap<HeroSuperpower>
    {
        protected override void InternalMap(ModelBuilder model, EntityTypeBuilder<HeroSuperpower> entity)
        {
            entity
                .HasKey(x => new { x.HeroId, x.SuperpowerId });

            entity
                .Property(x => x.HeroId);

            entity
                .HasOne(x => x.Hero)
                .WithMany()
                .HasForeignKey(x => x.HeroId)
                .HasConstraintName("FK_HeroSuperpower_Hero");

            entity
                .HasOne(x => x.Superpower)
                .WithMany()
                .HasForeignKey(x => x.SuperpowerId)
                .HasConstraintName("FK_HeroSuperpower_Superpower");
        }
    }
}
```

That's it!

### Repositories: Where you are sharing your LINQ queries ###

A Repository should be used to encapsulate common queries, so we don't rewrite LINQ statements all over. I am also 
not a huge friend of abstracting everything behind a Specification pattern. Just give you method a good name, pass 
your arguments and off you go. You may ask what's the difference between a Data Access Object and a Repository 
here? I actually don't know and don't care.

To resolve the ``DbContext`` from the current ``DbContextScope`` you are using an ``IDbContextAccessor``. You can call 
``SaveChanges`` on the ``DbContext`` in the repository of course, but this would result in an exception. Why? Because it 
should be clear *who* commits the ``DbContext`` and *when* it's commited.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Context;
using DbContextExtensions.Scope;
using DbContextExtensions.Test.Example.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace DbContextExtensions.Test.Example.Repositories
{
    public class HeroRepository : IHeroRepository
    {
        private readonly ILogger<HeroRepository> logger;
        private readonly IDbContextAccessor dbContextAccessor;

        public HeroRepository(ILogger<HeroRepository> logger, IDbContextAccessor dbContextAccessor)
        {
            this.logger = logger;
            this.dbContextAccessor = dbContextAccessor;
        }

        public async Task AddHeroAsync(Hero hero, CancellationToken cancellationToken)
        {
            logger.LogDebug("Adding {@Hero} ...", hero);

            await Context.AddAsync(hero, cancellationToken);
        }

        public Task<List<Hero>> GetAllHeroesWithSuperpowersAsync(CancellationToken cancellationToken)
        {
            return Context.Set<Hero>()
                .Include(x => x.Superpowers)
                .ToListAsync(cancellationToken);
        }

        protected ApplicationDbContext Context => dbContextAccessor.GetDbContext<ApplicationDbContext>();
    }
}
```

### Services: Where your Business Logic happens ###

Now in the Business Layer we have the ``HeroService`` to implement Business logic. To start a new ``DbContextScope`` you 
are using an ``IDbContextScopeFactory<TDbContext>``. If let's say you are already in a ``DbContextScope`` the current 
method simply attaches and uses the same ``DbContext``.

By calling ``DbContextScope#Complete()`` you are basically telling the ``DbContextScope`` to write the data, when we are 
the outer-most scope and else you are acknowledging saving the data, just like a ``TransactionScope`` would behave.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Context;
using DbContextExtensions.Scope;
using DbContextExtensions.Test.Example.Entities;
using DbContextExtensions.Test.Example.Repositories;
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace DbContextExtensions.Test.Example.Business
{
    /// <summary>
    /// Entity Framework-based <see cref="IHeroService"/> implementation.
    /// </summary>
    public class HeroService : IHeroService
    {
        private readonly IDbContextScopeFactory<ApplicationDbContext> dbContextScopeFactory;
        private readonly IHeroRepository heroRepository;

        public HeroService(IDbContextScopeFactory<ApplicationDbContext> dbContextScopeFactory, IHeroRepository heroRepository)
        {
            this.dbContextScopeFactory = dbContextScopeFactory;
            this.heroRepository = heroRepository;
        }

        /// <summary>
        /// Adds a new Hero asynchronously.
        /// </summary>
        /// <param name="hero">Hero</param>
        /// <param name="cancellationToken">CancellationToken to cancel from within async code</param>
        /// <returns>An awaitable Task</returns>
        public async Task AddHero(Hero hero, CancellationToken cancellationToken = default)
        {
            if(hero == null)
            {
                throw new ArgumentNullException(nameof(hero));
            }

            using (var scope = dbContextScopeFactory.Create())
            {
                await heroRepository.AddHeroAsync(hero, cancellationToken);

                scope.Complete();
            }
        }

        /// <summary>
        /// Gets all Heroes available.
        /// </summary>
        /// <param name="cancellationToken">CancellationToken to cancel from within async code</param>
        /// <returns>List of all Heroes</returns>
        public async Task<List<Hero>> GetHeroes(CancellationToken cancellationToken = default)
        {
            using (var scope = dbContextScopeFactory.Create(isReadOnly: true))
            {
                return await heroRepository.GetAllHeroesWithSuperpowersAsync(cancellationToken);
            }
        }
    }
}
```

### App: Putting it all together ###

In the ``SampleApplicationTests`` we are finally putting it all together and validate it all works as expected. All 
that needs to be registered for the ``DbContextScope`` to work is registering these options in the ASP.NET DI container 
and off we go:

```csharp
// Configure the DbContextFactory, which instantiates the DbContext:
services.AddDbContextFactory<ApplicationDbContext>((services, options) =>
{
    // Access the Unit Tests Configuration, which is configured by the Container:
    var configuration = services.GetRequiredService<IConfiguration>();

    options.UseSqlServer(configuration.GetConnectionString("DefaultConnection"));
});

// Register Scoping dependencies:
services.AddSingleton<IDbContextAccessor, DbContextAccessor>();
services.AddSingleton<IDbContextScopeFactory<ApplicationDbContext>, DbContextScopeFactory<ApplicationDbContext>>();
```

And the full ``SampleApplicationTests`` example now is:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Context;
using DbContextExtensions.Mappings;
using DbContextExtensions.Scope;
using DbContextExtensions.Test.Example.Business;
using DbContextExtensions.Test.Example.Database;
using DbContextExtensions.Test.Example.Entities;
using DbContextExtensions.Test.Example.Repositories;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using NUnit.Framework;
using System.Linq;
using System.Threading.Tasks;

namespace DbContextExtensions.Test.Example.App
{
    public class SampleApplicationTests : AbstractTestBase
    {
        [SetUp]
        public void Setup()
        {
            var dbContextFactory = GetService<IDbContextFactory<ApplicationDbContext>>();

            using (var applicationDbContext = dbContextFactory.CreateDbContext())
            {
                applicationDbContext.Database.EnsureDeleted();
                applicationDbContext.Database.EnsureCreated();
            }
        }

        [Test]
        public async Task ExecuteService()
        {
            var heroService = GetService<IHeroService>();
            var loggerFactory = GetService<ILoggerFactory>();

            // Add Magneto:
            {
                var hero = new Hero
                {
                    Name = "Magneto",
                    Superpowers = new[]
                    {
                        new Superpower { Name = "Magnetism", Description = "Can control Magnetism."},
                        new Superpower { Name = "Sarcasm", Description = "Can turn irony to sarcasm."},
                    }
                };

                await heroService.AddHero(hero);
            }

            // Get all Heroes:
            var heroes = await heroService.GetHeroes();

            foreach (var hero in heroes)
            {
                loggerFactory
                    .CreateLogger<SampleApplicationTests>()
                    .LogInformation($"Created Hero: {hero}");
            }

            Assert.AreEqual(1, heroes.Count);

            Assert.GreaterOrEqual(1, heroes[0].Id); 
            Assert.AreEqual("Magneto", heroes[0].Name);

            Assert.IsNotNull(heroes[0].Superpowers);
            Assert.AreEqual(2, heroes[0].Superpowers.Count);

            Assert.AreEqual(true, heroes[0].Superpowers.Any(x => string.Equals(x.Name, "Magnetism")));
            Assert.AreEqual(true, heroes[0].Superpowers.Any(x => string.Equals(x.Name, "Sarcasm")));
        }

        protected override void RegisterDependencies(ServiceCollection services)
        {
            // Logging:
            services.AddLogging();

            // Configure the DbContextFactory, which instantiates the DbContext:
            services.AddDbContextFactory<ApplicationDbContext>((services, options) =>
            {
                // Access the Unit Tests Configuration, which is configured by the Container:
                var configuration = services.GetRequiredService<IConfiguration>();

                options.UseSqlServer(configuration.GetConnectionString("DefaultConnection"));
            });

            // Register the Mappings:
            services.AddSingleton<IEntityMap, HeroEntityMap>();
            services.AddSingleton<IEntityMap, SuperpowerEntityMap>();
            services.AddSingleton<IEntityMap, HeroSuperpowerEntityMap>();

            // Register Scoping dependencies:
            services.AddSingleton<IDbContextAccessor, DbContextAccessor>();
            services.AddSingleton<IDbContextScopeFactory<ApplicationDbContext>, DbContextScopeFactory<ApplicationDbContext>>();

            // Register the Repositories:
            services.AddSingleton<IHeroRepository, HeroRepository>();

            // Register the Services:
            services.AddSingleton<IHeroService, HeroService>();
        }
    }
}
```

### Conclusion ###

A ``DbContextScope`` allows to better reason about *how* the DbContext is created, *when* it's created, *who* commits it and *when* it's actually 
commited. Does it cover each and every use case? Probably not. Is it going to simplify the Data Access Layer and make it easier to reuse for different 
scenarios? I hope so!

Time will tell... and I will update this article.


## EntityMap: Building modular DbContext's ##

Your application grows and so does the amount of ``DbSet`` properties in your ``DbContext``. There is a simple way 
to avoid it, by using an ``IEntityTypeConfiguration`` and automatically register the mappings in the ``DbContext``. 
By using ``DbContext#Set<TEntityType>`` we can then access the underlying ``DbSet``.

But looking at the ``IEntityTypeConfiguration`` interface, I can see I would lose access to the ``ModelBuilder``:

```csharp
// Licensed to the .NET Foundation under one or more agreements.
// The .NET Foundation licenses this file to you under the MIT license.

using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Microsoft.EntityFrameworkCore
{
    public interface IEntityTypeConfiguration<TEntity>
        where TEntity : class
    {
        void Configure(EntityTypeBuilder<TEntity> builder);
    }
}
```

So first of all we define an interface, which can be used to configure the ``ModelBuilder``:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;

namespace DbContextExtensions.Mappings
{
    /// <summary>
    /// Implements Entity Framework Core Type Configurations using the 
    /// <see cref="ModelBuilder"/>. This class is used as an abstraction, 
    /// so we can pass the <see cref="IEntityTypeConfiguration{TEntity}"/> 
    /// into a <see cref="DbContext"/>.
    /// </summary>
    public interface IEntityMap
    {
        /// <summary>
        /// Configures the <see cref="ModelBuilder"/> for an entity.
        /// </summary>
        /// <param name="builder"><see cref="ModelBuilder"/></param>
        void Map(ModelBuilder builder);
    }
}
```

And we can then define an ``EntityMap<TEntityType>`` base class, which can be used to configure the ``ModelBuilder`` 
and the ``EntityTypeBuilder<TEntityType>`` at the same time:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace DbContextExtensions.Mappings
{
    /// <summary>
    /// A base class for providing simplified access to a <see cref="EntityTypeBuilder{TEntityType}"/> for a 
    /// given <see cref="TEntityType"/>. This is used to enable mappings for each type individually.
    /// </summary>
    /// <typeparam name="TEntityType"></typeparam>
    public abstract class EntityMap<TEntityType> : IEntityMap
            where TEntityType : class
    {
        /// <summary>
        /// Implements the <see cref="IEntityMap"/>.
        /// </summary>
        /// <param name="builder"><see cref="ModelBuilder"/> passed from the <see cref="DbContext"/></param>
        public void Map(ModelBuilder builder)
        {
            InternalMap(builder, builder.Entity<TEntityType>());
        }

        /// <summary>
        /// Implementy the Entity Type configuration for a <see cref="TEntityType"/>.
        /// </summary>
        /// <param name="model">The <see cref="ModelBuilder"/> to configure</param>
        /// <param name="entity">The <see cref="EntityTypeBuilder{TEntity}"/> to configure</param>
        protected abstract void InternalMap(ModelBuilder model, EntityTypeBuilder<TEntityType> entity);
    }
}
```

And finally we can define an ``ApplicationDbContext`` as the basis for the application:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DbContextExtensions.Mappings;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Linq;

namespace DbContextExtensions.Context
{
    /// <summary>
    /// A base class for a <see cref="DbContext"/> using <see cref="IEntityMap"/> mappings.
    /// </summary>
    public class ApplicationDbContext : DbContext
    {
        private readonly IReadOnlyCollection<IEntityMap> mappings;

        /// <summary>
        /// Creates a new <see cref="DbContext"/> to query the database.
        /// </summary>
        /// <param name="loggerFactory">A Logger Factory to enable EF Core Logging facilities</param>
        /// <param name="mappings">The <see cref="IEntityMap"/> mappings for mapping query results</param>
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options, IEnumerable<IEntityMap> mappings)
            : base(options)
        {
            this.mappings = mappings
                .ToList()
                .AsReadOnly();
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            ApplyMappings(modelBuilder);
        }

        private void ApplyMappings(ModelBuilder modelBuilder)
        {
            foreach (var mapping in mappings)
            {
                Logger.LogDebug("Applying EntityMap {EntityMap}", mapping.GetType());

                mapping.Map(modelBuilder);
            }
        }

        protected ILogger<ApplicationDbContext> Logger => this.GetService<ILogger<ApplicationDbContext>>();
    }
}
```

### Example: Using the ApplicationDbContext and EntityMap's ###

We define the ``Person`` class first:

```csharp
class Person
{
    public int Id { get; set; }

    public string FirstName { get; set; }

    public string LastName { get; set; }

    public DateTime BirthDate { get; set; }
}
```

And its ``IEntityMap`` implementation using the ``EntityMap`` base class like this:

```csharp
// The Fluent EF Core Mapping.
class PersonEntityMap : EntityMap<Person>
{
    protected override void InternalMap(ModelBuilder model, EntityTypeBuilder<Person> entity)
    {
        model
            .HasSequence("SeqPerson", seq_builder => seq_builder.IncrementsBy(10));

        entity
            .ToTable("Person", "dbo")
            .HasKey(x => x.Id);

        entity
            .Property(x => x.Id)
            .UseHiLo("SeqDocument")
            .HasColumnName("PersonID");

        entity
            .Property(x => x.FirstName)
            .HasColumnName("FirstName");

        entity
            .Property(x => x.LastName)
            .HasColumnName("LastName");

        entity
            .Property(x => x.BirthDate)
            .HasColumnName("BirthDate");
    }
}
```

Now what's left is to register the ``IEntityMap`` implementations and the ``ApplicationDbContext`` in the DI Container:

```csharp
// Register the Mappings:
services.AddSingleton<IEntityMap, PersonEntityMap>();

// Configure the DbContextFactory, which instantiates the DbContext:
services.AddDbContext<ApplicationDbContext>((options) =>
{
    options.UseSqlServer(Configuration.GetConnectionString("DefaultConnection"));
});

// Configure the DbContextFactory, which can be used to instantiate DbContexts, when needed:
services.AddDbContextFactory<ApplicationDbContext>((services, options) =>
{
    options.UseSqlServer(configuration.GetConnectionString("DefaultConnection"));
});
```

The method ``DbContext#Set<T>`` can then be used on the ``ApplicationDbContext`` to query the entity:

```csharp
public class PersonService 
{
    private readonly ApplicationDbContext context;
    
    public PersonService(ApplicationDbContext context)
    {
        this.context = context;
    }
    
    public List<Person> GetAll() 
    {
        return context
            .Set<Person>()
            .ToList();
    }
}
```

And that's it.

[Enterprise Application Architecture (Archived)](https://web.archive.org/web/20020329184043/http://www.martinfowler.com/isa/concurrency.html)
[Unit Of Work]: https://martinfowler.com/eaaCatalog/unitOfWork.html
[Wayback Machine]: https://web.archive.org/web/20020408184339/http://martinfowler.com/isa/index.html
[Enterprise Application Architecture (Archived)]: https://web.archive.org/web/20020329184043/http://www.martinfowler.com/isa/concurrency.html
