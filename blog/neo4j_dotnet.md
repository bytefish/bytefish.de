title: Neo4J with .NET
date: 2018-04-28 21:15
tags: dotnet, csharp, neo4j, graph
category: csharp
slug: neo4j_dotnet
author: Philipp Wagner
summary: This article shows how to work with Neo4J with .NET.

Document Databases, Map Reduce, Hadoop... NoSQL. Name a hype technology from the 2000s and chance is good 
I was a **huge** fanboy. Then I started working and realized: one of the few constants in our industry are 
Relational Database Management Systems. So by now I am a **huge** RDBMS fanboy (of course) and advertise 
to use SQL for everything. 

My rule of thumb for every new project is: 

> When in doubt use PostgreSQL. 

## A Silver Bullet? ##

But sometimes, no matter how hard you try, no matter how often you iterate over your relational model, your 
queries are hell. A product of sweat, tears and 23 Joins stuck inside a chain of [Common Table Expressions], 
that only a query planner could make sense of. It's hard to admit, but sometimes SQL doesn't fit.

That's the reason why I have taught myself how to work with [Elasticsearch in .NET] [and Java], how to do 
[Stream Data Processing with Apache Flink] and [Complex Event Processing] for detecting complex patterns in 
temporal data. 

I still advertise using a Relational Database as your Primary Datastore, but complement it with the best 
tools and data representations for the job at hand.

[Common Table Expressions]: https://en.wikipedia.org/wiki/Hierarchical_and_recursive_queries_in_SQL#Common_table_expression
[Elasticsearch in .NET]: https://bytefish.de/blog/elasticsearch_net/
[and Java]: https://bytefish.de/blog/elasticsearch_java/
[Stream Data Processing with Apache Flink]: https://bytefish.de/blog/stream_data_processing_flink/
[Complex Event Processing]: https://bytefish.de/blog/apache_flink_series_5/
[SQL Server Column Store]: https://github.com/bytefish/WeatherDataColumnStore

## Enter Graph Databases ##

[Microsoft has a perfect introduction to Graph Databases]: https://docs.microsoft.com/en-us/sql/relational-databases/graphs/sql-graph-overview?view=sql-server-2017

In real life you often have to deal complex many-to-many relationships in your data, think of big Social Networks, with all its evolving relationships 
in the data. Analyzing these relationships in a relational database often becomes a tedious job, adding new relationships to the database can be a hard 
job.

[Microsoft has a perfect introduction to Graph Databases] and their use cases :

> ### What is a graph database ###
>
> A graph database is a collection of nodes (or vertices) and edges (or relationships). A node represents an entity (for example, 
> a person or an organization) and an edge represents a relationship between the two nodes that it connects (for example, likes or 
> friends). Both nodes and edges may have properties associated with them. Here are some features that make a graph database unique:
>
> * Edges or relationships are first class entities in a Graph Database and can have attributes or properties associated with them.
> * A single edge can flexibly connect multiple nodes in a Graph Database.
> * You can express pattern matching and multi-hop navigation queries easily.
> * You can express transitive closure and polymorphic queries easily.
>
> ### When to use a graph database ###
>
> There is nothing a graph database can achieve, which cannot be achieved using a relational database. However, 
> a graph database can make it easier to express certain kind of queries. Also, with specific optimizations, certain 
> queries may perform better. Your decision to choose one over the other can be based on following factors:
>
> * Your application has hierarchical data. The HierarchyID datatype can be used to implement hierarchies, but it has some limitations. For example, it does not allow you to store multiple parents for a node.
> * Your application has complex many-to-many relationships; as application evolves, new relationships are added.
> * You need to analyze interconnected data and relationships.

### Should I care? Do Graph Databases matter? ###

Graph database can be a very, very useful tool to simplify your life, when SQL queries become your painful enemy. But is it useful to 
learn about them? Do they matter? I think so, because parts of the industry are currently betting big on Graph data processing, like:

... Microsoft:

* [CosmosDB](https://docs.microsoft.com/en-us/azure/cosmos-db/introduction)
* [Graph Engine](https://www.graphengine.io/)
* [SQL Server 2017 Graph Database](https://docs.microsoft.com/en-us/sql/relational-databases/graphs/sql-graph-overview?view=sql-server-2017)

... or SAP:

* [SAP HANA Graph Engine](https://blogs.sap.com/2016/08/01/what-s-new-in-sap-hana-sps12-sap-hana-graph-engine/)

... or Oracle:

* [Oracle Spatial and Graph](http://www.oracle.com/technetwork/database/options/spatialandgraph/overview/index.html)

So your database might already include Graph database capabilities!

## Neo4j ##

[Cypher Query Language]: https://en.wikipedia.org/wiki/Cypher_Query_Language
[Neo4j]: https://neo4j.com
[DB-Engines Ranking of Graph DBMS]: https://db-engines.com/en/ranking/graph+dbms

So what Graph database should I use for learning? The SQL Server 2017 Graph Database would be interesting, but it is at an early stage of development, and it comes with 
limited [Cypher Query Language] support. I don't have a SAP HANA License and no Oracle at hand. So I decided to base this Graph database example on the most popular 
Open Source Graph Database [Neo4j] (according to the [DB-Engines Ranking of Graph DBMS]).

> [Neo4j] is a graph database management system developed by Neo4j, Inc. Described by its developers as an ACID-compliant transactional database 
> with native graph storage and processing, Neo4j is the most popular graph database according to DB-Engines ranking.

## The Project: The Movie Database ##

The canonical Neo4j introduction is the [Movie Database](https://neo4j.com/developer/movie-database/):

> The movie database is a traditional dataset for graph databases, similiar to IMDB it contains movies and actors, 
> directors, producers etc. It could be extended with Genres, Publishers, Ratings and more.

There are sample projects for Movie database applications in languages like Java, .NET, JavaScript, Python, Ruby, Elixir and even Haskell:

* [https://github.com/neo4j-examples](https://github.com/neo4j-examples/)

But all of these projects only deal with querying the dataset. As a developer I ask myself instantly: How is the data actually imported? How do you Bulk Insert data 
efficiently? It turns out, that the data import for the Movie database applications is done with CSV files and uses the Neo4j ``LOAD CSV`` statement: 

* [https://neo4j.com/developer/example-project/#_data_setup](https://neo4j.com/developer/example-project/#_data_setup)

### What we are going to build ###

And that's where things get hairy. The Neo4j is very quiet about .

### Domain Model ###


* Movie
    * ID
    * Title

* Person
    * ID
    * Name

* Genre
    * Name
    
* MovieInformation
    * Movie
    * Director
    * Genres
    * Cast