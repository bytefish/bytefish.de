title: Implementing Relationship-based Access Control with ASP.NET Core and SQL
date: 2018-01-01 10:24
tags: aspnetcore, dotnet, csharp, sql, datamining
category: dotnet
slug: aspnetcore_rebac
author: Philipp Wagner
summary: This article shows a way to implement a Relationship-based Access Control in ASP.NET Core and SQL.

You are opening your Google Drive app, and a moment later *your files* appear. It's magic. But 
have you ever wondered what's *your files* actually? How do these services actually know, which 
files you are allowed to see?

Are you part of an *Organization*, that is allowed to *view* all files of the *Organization* 
itself? Have you been assigned to a *Team*, that's allowed to *view* or *edit* files? Has 
someone shared *their files* with *you* as a *User*?

In 2019 Google has published a paper on "Google Zanzibar", which is Google's central solution 
for providing authorization among its many services:

* [https://research.google/pubs/pub48190/](https://research.google/pubs/pub48190/)

The keyword here is *Relationship-based Access Control*, which is ...

> [...] an authorization paradigm where a subject's permission to access a resource is defined by the 
> presence of relationships between those subjects and resources.

So let's find out about it! 

I have previously [written an article about the Google Zanzibar Data Model], and also wrote some 
pretty nice SQL statements to make sense of the it. This article will make use of the queries 
and takes a look at implementing Relationship-based Access Control using Microsoft SQL Server 
and ASP.NET Core.

All code in this article can be found in a repository at:

* [https://github.com/bytefish/RebacExperiments](https://github.com/bytefish/RebacExperiments)

## Table of contents ##

[TOC]

## What we are going to build ##

We are going to build out a tiny part of a Task Management system. Why? Because tasks are basically 
everywhere in an organization, such as having tasks for signing documents, calling back customers or 
reminders to write invoices. They are a good example use case for authorization.

The situation is now somewhat similar to the Google Drive example. You obviously don't want an entire 
organization to view, edit, delete or close all tasks. Given a sufficiently large headcount it would 
quickly escalate into a chaos, if we don't authorize users.

### Role-based Access Control (RBAC) ###

One way to authorize users is Role-based Access Control.

Role-based Access Control is definitely among the most popular models for defining permissions and 
authorizing access to an organizations resources, such as our tasks. Highly simplified, a user is 
being assigned a set of roles, where each role represents the users role within the organization.

So a regular user of our fictional task management system might be able to view, edit and close 
tasks, while it requires elevated rights to actually delete a task. Likewise a user being assigned 
to the role *Software Development* should probably not be permitted to view or edit tasks created 
by the *Human Resources* department.

There was recently a great Microsoft DevBlogs article by Stewart Adam, that discusses designing Role-based 
Access Control for applications and it's a great read:

* [Authoring an RBAC API for your application (by Stewart Adam)](https://devblogs.microsoft.com/ise/2023/10/12/rbac-api-for-your-application/)

And as you can see in the article, a Role-based Access Control can get very complex, very quickly. We have 
"Subtree grants", "Entity Graph Scopes", "Nested Roles", "Permission Wildcards", ... and sadly none of 
it is illustrated with *actual code*.

In my experience Role-based Access Control can take you very far, but as soon you need more fine-grained 
control, you are most probably out of luck. 

### Relationship-based Access Control (ReBAC) ###

Google Zanzibar was described by Google in a 2019 paper called "Zanzibar: Google’s Consistent, Global Authorization 
System" and the paper is available for download at:

* [https://research.google/pubs/pub48190/](https://research.google/pubs/pub48190/)

It describes the Google's motivation for building a unified authorization system and describes the 
data model, language and its API. After publishing the paper various vendors and open source 
implementations have materialized, like Permify, OSO or SpiceDB, ... to name a few.

There are many excellent sources, that explain Google Zanzibar in detail and help you learning 
about it. I've basically consulted the following articles to get started and :

* [Exploring Google Zanzibar: A Demonstration of Its Basics (by Ege Aytin)](https://www.permify.co/post/exploring-google-zanzibar-a-demonstration-of-its-basics)
* [Building Zanzibar from Scratch (by Sam Scott)](https://www.osohq.com/post/zanzibar)
* [Zanzibar-style ACLs with Prolog (by Radek Gruchalski)](https://gruchalski.com/posts/2022-09-03-zanzibar-style-acls-with-prolog/)

Highly, highly simplified, Google Zanzibar models relationships between `Objects` and `Subjects` using the following notation:

```
<object>#<relation>@<subject> 
```

This allows Google Zanzibar to model relationships between an `Object` and a `Subject`. Say we have our system to manage 
tasks, then we could make up relations like this with the Google Zanzibar syntax:

```
task323#owner@philipp
task323#viewer@org1#member
task152#viewer@org1#member
task152#viewer@org2#member
org1#member@philipp
org1#member@hannes
org2#member@alexander
```

Where ...

* `task323#owner@philipp`
    * `philipp` is the `owner` of `task323`.
* `task323#viewer@org1#member`
    * `members` of `org1` are `viewer` of `task323`
* `task152#viewer@org1#member`
    * `members` of `org1` are `viewer` of `task152`
* `task152#viewer@org2#member`
    * `members` of `org2` are `viewer` of `task323`
* `org1#member@philipp`
    * `philipp` is a `member` of `org1`
* `org1#member@hannes`
    * `hannes` is a `member` of `org1`
* `org2#member@alexander`
    * `alexander` is a `member` of `org1`
    
As you can see, it's pretty easy to build a Role-based Access Control upon the Google Zanzibar data model. And 
it's something, that's often done in these systems. It's already been noted in the original paper, that ...

> [...] A number of Zanzibar clients have implemented RBAC policies on top of Zanzibar’s namespace configuration language. [...]

### RASP.NET Core 

At the end of this article we will have a RESTful API, that secures it's endpoint using Relationship-based 
Access Control. 

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/swagger_endpoints.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/swagger_endpoints.jpg" alt="Final Swagger Endpoints">
    </a>
</div>


## Designing the Database ##

If you are going to work with a relational database you should put all your database objects in version control. The 
best example for a SQL Server Database Project (SSDP) available out there is the [WideWorldImporters OLTP Database] 
example provided in the SQL Server examples repository:

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt)

### Project Structure ###

Before starting any database application, a team should *agree* on structure and naming conventions. You'll need to 
have a consistent style from the very start. Everyone has to know *where to put files* and the naming conventions to 
apply.

The high level structure for our SQL Server Database Project uses the [WideWorldImporters OLTP Database] structure:

* `«Schema»`
    * `Function`
        * Functions go here ...
    * `Indexes`
        * Indexes go here ...
    * `Sequences`
        * Sequences go here ...
    * `Stored Procedures`
        * Stored Procedures go here ...
    * `Tables`
        * Tables go here ...
    * `Views`
        * Views go here ...
    * `«Schema».sql`
        * Creates the Schema
* `Scripts`
    * `«Schema»`
        * Deployment Scripts for a Schema go here ...
    * `Script.PostDeployment1.sql`
        * Post Deployment Script to execute SQL scripts go here ...

### SQL Server Object Name Convention ###

[Naming convention]: https://en.wikipedia.org/wiki/Naming_convention_(programming)

What's that "*Naming Conventions*" I am talking about?

A [Naming convention] is a set of rules for choosing the character sequence to be used for 
identifiers which denote variables, types, functions, and other entities in source code 
and documentation.

Reasons for using a naming convention (as opposed to allowing programmers to choose any character sequence) 
include the following:

- To reduce the effort needed to read and understand source code.
- To enable code reviews to focus on more important issues than arguing over syntax and naming standards.
- To enable code quality review tools to focus their reporting mainly on significant issues other than syntax and style preferences.

For SQL Server the following table is a good start.

| Object                                   | Notation   | Length | Plural | Prefix  | Suffix    | Example                                                  |
|------------------------------------------| ---------- |-------:|--------|---------|-----------|----------------------------------------------------------|
|  Database                                | PascalCase |     30 | No     | No      | No        | `MyDatabase`                                             |
|  Schema                                  | PascalCase |     30 | No     | No      | No        | `MySchema`                                               |
|  Global Temporary Table                  | PascalCase |    117 | No     | No      | No        | `##MyTable`                                              |
|  Local Temporary Table                   | PascalCase |    116 | No     | No      | No        | `#MyTable`                                               |
|  File Table                              | PascalCase |    128 | No     | `FT_`   | No        | `FT_MyTable`                                             |
|  Temporal Table                          | PascalCase |    128 | No     | No      | `History` | `MyTableHistory`                                         |
|  Table Column                            | PascalCase |    128 | No     | No      | No        | `MyColumn`                                               |
|  Columns Check Constraint                | PascalCase |    128 | No     | `CTK_`  | No        | `CTK_MyTable_MyColumn_AnotherColumn`                     |
|  Column Check Constraint                 | PascalCase |    128 | No     | `CK_`   | No        | `CK_MyTable_MyColumn`                                    |
|  Column Default Values                   | PascalCase |    128 | No     | `DF_`   | No        | `DF_MyTable_MyColumn`                                    |
|  Table Primary Key                       | PascalCase |    128 | No     | `PK_`   | No        | `PK_MyTable`                                             |
|  Table Unique (Alternative) Key          | PascalCase |    128 | No     | `AK_`   | No        | `AK_MyTable_MyColumn_AnotherColumn`                      |
|  Table Foreign Key                       | PascalCase |    128 | No     | `FK_`   | No        | `FK_MyTable_MyColumn_ReferencedTable_ReferencedColumn`   |
|  Table Clustered Index                   | PascalCase |    128 | No     | `IXC_`  | No        | `IXC_MyTable_MyColumn_AnotherColumn`                     |
|  Table Non Clustered Index               | PascalCase |    128 | No     | `IX_`   | No        | `IX_MyTable_MyColumn_AnotherColumn`                      |
|  Table Unique Index                      | PascalCase |    128 | No     | `UX_`   | No        | `UX_MyTable_MyColumn_AnotherColumn`                      |
|  DDL Trigger                             | PascalCase |    128 | No     | `TR_`   | `_DDL`    | `TR_LogicalName_DDL`                                     |
|  DML Trigger                             | PascalCase |    128 | No     | `TR_`   | `_DML`    | `TR_MyTable_LogicalName_DML`                             |
|  Logon Trigger                           | PascalCase |    128 | No     | `TR_`   | `_LOG`    | `TR_LogicalName_LOG`                                     |
|  View                                    | PascalCase |    128 | No     | `VI_`   | No        | `VI_LogicalName`                                         |
|  Indexed View                            | PascalCase |    128 | No     | `VIX_`  | No        | `VIX_LogicalName`                                        |
|  Statistic                               | PascalCase |    128 | No     | `ST_`   | No        | `ST_MyTable_MyColumn_AnotherColumn`                      |
|  Stored Procedure                        | PascalCase |    128 | No     | `usp_`  | No        | `usp_LogicalName`                                        |
|  Scalar User-Defined Function            | PascalCase |    128 | No     | `udf_`  | No        | `udf_FunctionLogicalName`                                |
|  Table-Valued Function                   | PascalCase |    128 | No     | `tvf_`  | No        | `tvf_FunctionLogicalName`                                |
|  Sequence                                | PascalCase |    128 | No     | `sq_`   | No        | `sq_TableName`                                           |

### Natural vs. Surrogate Primary Keys ###

In our application we want to make assumptions about the tables, so we set the convention to always 
set a Surrogate Primary Key. So a Table like `User` is going to have a `UserID` Primary Key, no 
matter if there are suitable natural Primary Keys.

### Auditing and Optimistic Locking ###

In my experience every database table should support optimistic locking and auditing baked in from the 
start, because:

* You'll always need a way to recover from accidental data changes or application errors. 
* You'll always need a way to audit who was responsible for changes to the data. 
* You'll always need a way to prevent applications from overriding each others data.

So as a convention *every* table in our application gets the following 4 additional columns:

| Column Name     | Data Type       | Allow NULL |  Description                                                  |
|-----------------| ----------------|------------|-------------------------------------------------------------------------------------|
|  RowVersion     | `ROWVERSION`    | Yes        | A Version automatically generated by SQL Server, to serve as a Concurrency Token)   |
|  LastEditedBy   | `INT`           | No         | A Foreign Key to a `User` to track changes to the data                              |
|  ValidFrom      | `DATETIME2(7)`  | No         | Period start column: The system records the start time for the row in this column   |
|  ValidTo        | `DATETIME2(7)`  | No         | Period end column: The system records the end time for the row in this column       |

They don't hurt and they bring a lot of usefulness to the table. And if you don't need a history, just deactivate 
the Temporal Table and call it a day.

### Temporal Tables ###

Few developers know about Temporal tables, also known as ...

> [...] system-versioned temporal tables, are a database feature that brings built-in support for providing information 
> about data stored in the table at any point in time, rather than only the data that is correct at the current moment 
> in time.

Why do you want to use a Temporal Table at all?

> Real data sources are dynamic and more often than not business decisions rely on insights that analysts can get from 
> data evolution. Use cases for temporal tables include:
>
> - Auditing all data changes and performing data forensics when necessary
> - Reconstructing state of the data as of any time in the past
> - Calculating trends over time
> - Maintaining a slowly changing dimension for decision support applications
> - Recovering from accidental data changes and application errors

It's easy to enable system versioning in Microsoft SQL Server, like we are doing for a `[Tasks].[Task]` table, 
that's going to hold all Tasks assigned to a user:

```sql
CREATE TABLE [Application].[UserTask](
    [UserTaskID]            INT                                         CONSTRAINT [DF_Application_UserTask_UserTaskID] DEFAULT (NEXT VALUE FOR [Application].[sq_UserTask]) NOT NULL,
    [Title]                 NVARCHAR(50)                                NOT NULL,
    [Description]           NVARCHAR(2000)                              NOT NULL,
    -- ...
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_UserTask] PRIMARY KEY ([UserTaskID]),
    -- ...
    CONSTRAINT [FK_UserTask_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    CONSTRAINT [FK_UserTask_User_AssignedTo] FOREIGN KEY ([AssignedTo]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskHistory]));
```

You can learn everything about Temporal Tables in the SQL Server documentation at:

* [https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables](https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables)

## Errors, Exceptions, ... ##



## Integration Tests ##

For integration tests we are writing a `TransactionalTestBase` class, which basically opens a `System.Transaction.TransactionScope` 
before executing a test and disposes it, when tearing it down. This will reset your database back into a consistent state for the 
next test to execute. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Tests
{
    /// <summary>
    /// Will be used by all integration tests, that need an <see cref="ApplicationDbContext"/>.
    /// </summary>
    public class TransactionalTestBase
    {
        /// <summary>
        /// We can assume the Configuration has been initialized, when the Tests 
        /// are run. So we inform the compiler, that this field is intentionally 
        /// left uninitialized.
        /// </summary>
        protected IConfiguration _configuration = null!;

        /// <summary>
        /// We can assume the DbContext has been initialized, when the Tests 
        /// are run. So we inform the compiler, that this field is intentionally 
        /// left uninitialized.
        /// </summary>
        protected ApplicationDbContext _applicationDbContext = null!;

        public TransactionalTestBase()
        {
            _configuration = ReadConfiguration();
            _applicationDbContext = GetApplicationDbContext(_configuration);
        }

        /// <summary>
        /// Read the appsettings.json for the Test.
        /// </summary>
        /// <returns></returns>
        private IConfiguration ReadConfiguration()
        {
            return new ConfigurationBuilder()
                .AddJsonFile("appsettings.json")
                .Build();
        }

        /// <summary>
        /// The SetUp called by NUnit to start the transaction.
        /// </summary>
        /// <returns>An awaitable Task</returns>
        [SetUp]
        protected async Task Setup()
        {
            await OnSetupBeforeTransaction();
            await _applicationDbContext.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, default);
            await OnSetupInTransaction();
        }

        /// <summary>
        /// The TearDown called by NUnit to rollback the transaction.
        /// </summary>
        /// <returns>An awaitable Task</returns>
        [TearDown]
        protected async Task Teardown()
        {
            await OnTearDownInTransaction();
            await _applicationDbContext.Database.RollbackTransactionAsync(default);
            await OnTearDownAfterTransaction();
        }

        /// <summary>
        /// Called before the transaction starts.
        /// </summary>
        /// <returns>An awaitable task</returns>
        public virtual Task OnSetupBeforeTransaction()
        {
            return Task.CompletedTask;
        }

        /// <summary>
        /// Called inside the transaction.
        /// </summary>
        /// <returns>An awaitable task</returns>
        public virtual Task OnSetupInTransaction()
        {
            return Task.CompletedTask;
        }

        /// <summary>
        /// Called before rolling back the transaction.
        /// </summary>
        /// <returns>An awaitable task</returns>
        public virtual Task OnTearDownInTransaction()
        {
            return Task.CompletedTask;
        }

        /// <summary>
        /// Called after transaction has been rolled back.
        /// </summary>
        /// <returns>An awaitable task</returns>
        public virtual Task OnTearDownAfterTransaction()
        {
            return Task.CompletedTask;
        }

        /// <summary>
        /// Builds an <see cref="ApplicationDbContext"/> based on a given Configuration. We 
        /// expect the Configuration to have a Connection String "ApplicationDatabase" to 
        /// be defined.
        /// </summary>
        /// <param name="configuration">A configuration provided by the appsettings.json</param>
        /// <returns>An initialized <see cref="ApplicationDbContext"/></returns>
        /// <exception cref="InvalidOperationException">Thrown when no Connection String "ApplicationDatabase" was found</exception>
        private ApplicationDbContext GetApplicationDbContext(IConfiguration configuration)
        {
            var connectionString = configuration.GetConnectionString("ApplicationDatabase");

            if (connectionString == null)
            {
                throw new InvalidOperationException($"No Connection String named 'ApplicationDatabase' found in appsettings.json");
            }

            return GetApplicationDbContext(connectionString);
        }

        /// <summary>
        /// Builds an <see cref="ApplicationDbContext"/> based on a given Connection String 
        /// and enables sensitive data logging for eventual debugging. 
        /// </summary>
        /// <param name="connectionString">Connection String to the Test database</param>
        /// <returns>An initialized <see cref="ApplicationDbContext"/></returns>
        private ApplicationDbContext GetApplicationDbContext(string connectionString)
        {
            var dbContextOptionsBuilder = new DbContextOptionsBuilder<ApplicationDbContext>().UseSqlServer(connectionString);

            return new ApplicationDbContext(
                logger: new NullLogger<ApplicationDbContext>(), 
                options: dbContextOptionsBuilder.Options);
        }
    }
}
```




## Running an Example ##

First of all we need to sign in, by sending the following JSON Payload to the `sign-in` endpoint:

```json
{
  "username": "philipp@bytefish.de",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

