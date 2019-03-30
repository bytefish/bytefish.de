title: Bookmarks, Blogs and Software Design
date: 2019-03-30 22:20
tags: misc
category: misc
slug: bookmarks_blogs_and_software_design
author: Philipp Wagner
summary: Sharing Blog posts and thoughts on Software design.

I am finally cleaning my bookmarks. And this gives me a chance to share some of my favorite posts. 

At the same time I also want to share some thoughts on programming and software design.

## Time Series Analysis: Resampling and Interpolation ##

[Caleb Welton]: https://github.com/cwelton
[lag]: https://docs.microsoft.com/en-us/sql/t-sql/functions/lag-transact-sql
[lead]: https://docs.microsoft.com/en-us/sql/t-sql/functions/lead-transact-sql
[PgBulkInsert]: https://github.com/bytefish/PgBulkInsert
[PostgreSQLCopyHelper]: https://github.com/bytefish/PostgreSQLCopyHelper
[Time Series Analysis Part 3: Resampling and Interpolation]: https://content.pivotal.io/blog/time-series-analysis-part-3-resampling-and-interpolation

The first bookmark is a post by [Caleb Welton]. It shows how to perform Timeseries Analysis with PostgreSQL and how to interpolate values:

* [Time Series Analysis Part 3: Resampling and Interpolation]

In early 2017 I had to deal with a lot timeseries data and tried to convince people to not leave SQL. 

The post showed me how to work with SQL [lag] and [lead] operators and how to use Common Table Expressions (CTE) to make queries simpler. 
I have to credit the post with getting me started with PostgreSQL again!

After reading the post I wrote [PgBulkInsert] and [PostgreSQLCopyHelper] to understand how the Postgres ``COPY`` Protocol works.

## Time-series data: Why (and how) to use a relational database instead of NoSQL ##

[Timescale]: https://www.timescale.com
[TimescaleDB]: https://www.timescale.com
[Time-series data: Why (and how) to use a relational database instead of NoSQL]: https://blog.timescale.com/time-series-data-why-and-how-to-use-a-relational-database-instead-of-nosql-d0cd6975e87c/

In 2017 a new Time series database also hit the scene: [TimescaleDB]. The blog post showed me, that you do not necessarily have 
to leave your SQL comfort zone for processing large amounts of Timeseries data. But my priorities at work shifted and I wasn't 
able to go much further:

* [Time-series data: Why (and how) to use a relational database instead of NoSQL]

[TimescaleDB] always stuck in my mind until 2019 when I finally found time to evaluate various Time series databases:

* [https://github.com/bytefish/GermanWeatherDataExample](https://github.com/bytefish/GermanWeatherDataExample)

## Everything Easy is Hard Again ##

[npm]: https://www.npmjs.com/
[CSS]: https://developer.mozilla.org/en-US/docs/Learn/CSS/Introduction_to_CSS
[SCSS]: https://sass-lang.com/
[JavaScript]: https://developer.mozilla.org/en-US/docs/Web/JavaScript
[TypeScript]: https://www.typescriptlang.org/docs/handbook/basic-types.html
[Everything Easy is Hard Again]: https://frankchimero.com/writing/everything-easy-is-hard-again/
[Frank Chimero]: https://frankchimero.com
[webpack]: https://webpack.js.org/

In late 2017 I got into Web Development again and my bookmarks suddenly saw a lot of good articles on Frontend development:

* [TypeScript Documentation](https://www.typescriptlang.org/docs/home.html)
* [Vue + Vuex — Getting started](https://medium.com/wdstack/vue-vuex-getting-started-f78c03d9f65)
* [Angular - Tour of Heroes](https://angular.io/tutorial)

But honestly. As a developer being proficient in various programming languages it was quite a frustrating fight to get 
"comfortable" with the JavaScript ecosystem and the modern Frontend stack in general: [webpack], [npm], [CSS], 
[SCSS], [JavaScript] and [TypeScript]. 

Every simple thing felt overly complex.

Position two elements next to each other? Oh dear. ::loudly_crying_face:: 

At the time an article by [Frank Chimero] restored a little faith in humanity:

* [Everything Easy is Hard Again]

## From JavaScript Fatigue to Graph Databases ##

[Eric Clemmons]: https://medium.com/@ericclemmons
[Javascript Fatigue]: https://medium.com/@ericclemmons/javascript-fatigue-48d4011b6fc4
[Nicole White]: https://github.com/nicolewhite/
[Nicole]: https://github.com/nicolewhite/
[neo4j]: https://neo4j.com/
[Cypher]: https://neo4j.com/developer/cypher-query-language/
[Intro to Cypher]: https://www.youtube.com/watch?v=VdivJqlPzCI
[A Neo4j database of flights]: https://github.com/nicolewhite/neo4j-flights

It's hard to not get frustrated when doing modern Frontend development for weeks. [Javascript Fatigue] anyone? 

This is put nicely in in a quote shared by [Eric Clemmons]:

> Saul: "How's it going?"
>
> Me: "Fatigued."
>
> Saul: "Family?"
>
> Me: "No, Javascript."

So after a month of struggling with [JavaScript] frameworks professionally, I needed some small side projects to 
turn frustration into code. ::flexed_biceps:: 

Around this time I stumbled upon a Youtube Video by [Nicole White]. It's a great introduction to [neo4j] and 
the [Cypher] query language:

* [Intro to Cypher] (Youtube)

In  the video [Nicole] explains how to model a Graph with [neo4j] and designs a Graph schema for querying Flight data:

* [A Neo4j database of flights] (Github)

This got me interested in [neo4j] and as a C\# programmer I evaluated how to use it with .NET:

* [https://bytefish.de/blog/neo4j_dotnet/](https://bytefish.de/blog/neo4j_dotnet/)
* [https://bytefish.de/blog/neo4j_at_scale_airline_dataset/](https://bytefish.de/blog/neo4j_at_scale_airline_dataset/)

Professionally I deal with the Microsoft SQL Server a lot, so it also got me interested in the Graph Database of SQL Server:

* [https://bytefish.de/blog/sql_server_2017_graph_database/](https://bytefish.de/blog/sql_server_2017_graph_database/)

## Microservices and Monoliths ##

[Microservices]: https://en.wikipedia.org/wiki/Microservices
[Stackoverflow]: https://www.stackoverflow.com
[Stack Overflow: The Architecture - 2016 Edition]: https://nickcraver.com/blog/2016/02/17/stack-overflow-the-architecture-2016-edition/
[Docker]: https://www.docker.com/
[Kubernetes]: https://en.wikipedia.org/wiki/Kubernetes
[Chef]: https://www.chef.io/
[Helm]: https://github.com/helm/helm
[Filter Bubble]: https://en.wikipedia.org/wiki/Filter_bubble
[RabbitMQ]: https://www.rabbitmq.com/
[Honest Status Page]: https://twitter.com/honest_update?lang=en
[etcd]: https://github.com/etcd-io/etcd
[rkt]: https://coreos.com/rkt/docs/latest/ 

> We replaced our monolith with micro services, so that every outage could be more like a murder mystery. ([Honest Status Page])

I live in an Anti-Microservices [Filter Bubble]. So most of my bookmarks have been in favor monoliths of course:

* [Give Me Back My Monolith](http://www.craigkerstiens.com/2019/03/13/give-me-back-my-monolith/) (Craig Kerstiens)
* [Developers Are The Problem, Not Monoliths](https://codeboje.de/developers-problem-not-monoliths/) (Jens Boje)
* [Goodbye Microservices: From 100s of problem children to 1 superstar](https://segment.com/blog/goodbye-microservices/) (Alexandra Noonan)

I try to avoid *everything*, that comes with Microservices: [Docker], [Kubernetes], [etcd], [Helm], [RabbitMQ], [rkt]... the list is long. 

Please don't jugde! ::relieved_face::

## Software Architecture ##

[Pokémon Architecture]: https://www.alexhudson.com/2017/07/20/pokemon-architecture/
[Software architecture is failing]: https://www.alexhudson.com/2017/10/14/software-architecture-failing/
[Layers, Onions, Ports, Adapters: it's all the same]: https://blog.ploeh.dk/2013/12/03/layers-onions-ports-adapters-its-all-the-same/
[Layered Architecture]: https://en.wikipedia.org/wiki/Multitier_architecture
[Layered Architectures]: https://en.wikipedia.org/wiki/Multitier_architecture
[Command Query Responsibility Segregation (CQRS)]: https://en.wikipedia.org/wiki/Command%E2%80%93query_separation
[Event Sourcing]: https://martinfowler.com/eaaDev/EventSourcing.html
[Onion Architecture]: https://jeffreypalermo.com/2008/07/the-onion-architecture-part-1/
[Hexagonal Architecture (Ports and Adapters)]: https://hackernoon.com/demystifying-the-hexagon-5e58cb57bbda
[eShopOnContainers - Microservices Architecture and Containers based Reference Application]: https://github.com/dotnet-architecture/eShopOnContainers
[Domain-Driven Design (DDD)]: https://en.wikipedia.org/wiki/Domain-driven_design
[Mark Seemann]: https://blog.ploeh.dk/
[Pokémon Exception Handling]: http://wiki.c2.com/?PokemonExceptionHandling
[Anemic Domain Model]: https://www.martinfowler.com/bliki/AnemicDomainModel.html
[eShopOnContainers]: https://github.com/dotnet-architecture/eShopOnContainers
 
I have thought *a lot* about software architecture in my career, so my bookmarks are full of links on software architecture.

You name an architecture and chance is good I experimented with it:

* [Layered Architecture]
* [Command Query Responsibility Segregation (CQRS)]
* [Event Sourcing]
* [Onion Architecture]
* [Hexagonal Architecture (Ports and Adapters)]
* ...

But it's like this ...

> Developers talk too much about architecture. ([Pokémon Architecture])

### Domain-Driven Design ###

There has been a lot of talk in the industry about [Domain-Driven Design (DDD)] for years. And over the past years I read most 
of the blogs and articles I could find in the internet on DDD. 

But at the bottom of my heart I am a programmer. I want to see code. I want to see the elegance in the architectures using the 
sacred Domain-Driven Design methodology.

Once you start digging a little deeper you will notice, that real DDD examples are a scarce good. ::thinking_face::

Especially in .NET.

The only somewhat larger .NET application I know of, that employs DDD / CQRS pattern is Microsofts [eShopOnContainers] project:

* [eShopOnContainers - Microservices Architecture and Containers based Reference Application]

And if you ask me if I'd rather maintain a DDD or a CRUD version of a Catalog Service:

* [Catalog Service (DDD)](https://github.com/dotnet-architecture/eShopOnContainers/tree/dev/src/Services/Catalog)
* [Catalog Service (Monolith)](https://github.com/dotnet-architecture/eShopOnContainers/tree/dev/src/Web/WebMonolithic/eShopWeb)

Oh Boy... 

Then I am a 1000% in the CRUD camp!

### On Layered Architectures ###

[buggy]: http://www.bailis.org/papers/acidrain-sigmod2017.pdf
[Google Cloud Platform]: https://cloud.google.com/blog/products/gcp/why-you-should-pick-strong-consistency-whenever-possible

So after years of reading and experimenting with Software architecture and being in various teams I came to the following two conclusions: 

1. 99% of the projects should start with a dead-simple [Layered Architecture].
2. 99% of the projects should start with a Relational Database.

Why? 

1. Everyone in a project understands [Layered Architectures].
2. Everyone knows where to put things in a [Layered Architecture], even if it's a huge *Service* or *Manager* anti-pattern class using [Anemic Domain Model] anti-pattern classes. 
3. Everyone understands ER-Diagrams and I am able to explain the domain. 
4. Everyone can learn a little SQL to play around & make sense of data.

And giving up on **A**tomicity, **C**onsistency, **I**solation, **D**urability guarantees of a Relational Database early in a project is outright dangerous.

There is a reason, why the [Google Cloud Platform] blog says:

* [Why you should pick strong consistency, whenever possible](https://cloud.google.com/blog/products/gcp/why-you-should-pick-strong-consistency-whenever-possible)

Because what happens when you introduce Eventual Consistency in a CQRS/ES application? What happens when using a NoSQL database, that doesn't have 
strong consistency guarantees?

> To take advantage of "transactions" in database systems that have limited or no strong consistency across documents/objects/rows, 
> you have to design your application schema such that you never need to make a change that involves multiple "things" at the same 
> time. That’s a huge restriction and workarounds at the application layer are painful, complex, and often [buggy]. 
> ([Google Cloud Platform] Blog)

Does a Layered Architecture scale? Probably not. 

But know what?

I will handle the problem, when the problem is real.

## Conclusion ##

[Hacker News]: https://news.ycombinator.com
[/r/programming]: https://www.reddit.com/r/programming
[FcmSharp]: https://github.com/bytefish/FcmSharp
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser

Full Stop.

In the past years I have read a lot articles on Software Development, Software Architecture and Project Management. I was constantly thinking about 
how to improve. Improve the code. Improve myself. I have spent countless hours reading discussions on [Hacker News] and [/r/programming].

But you know what made me a happier programmer? I stopped overthinking things.

* I started writing small libraries like [FcmSharp] or [TinyCsvParser], that make my life a little easier and hopefully yours.
* When designing software I make sure everyone in a team understands the design and knows where to put things.
* I try to get *something* done and not aim for the perfect abstraction. I stopped worrying about future, non-existing problems.