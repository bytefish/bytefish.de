title: Implementing Relationship-based Access Control with ASP.NET Core and SQL
date: 2018-01-01 10:24
tags: aspnetcore, dotnet, csharp, sql, datamining
category: dotnet
slug: aspnetcore_rebac
author: Philipp Wagner
summary: This article shows a way to implement a Relationship-based Access Control in ASP.NET Core and SQL.

[written an article about the Google Zanzibar Data Model]: https://www.bytefish.de/blog/relationship_based_acl_with_google_zanzibar.html

You are opening your Google Drive app, and a moment later *your files* appear. It's magic. But 
have you ever wondered what's *your files* actually? How do these services actually know, which 
files *you are allowed* to see?

Are you part of an *Organization* and you are allowed to *view* all their files? Have you been 
assigned to a *Team*, that's allowed to *view* or *edit* files? Has someone shared *their files* 
with *you* as a *User*?

So in 2019 Google has published a paper on "Google Zanzibar", which is Google's central solution 
for providing authorization among its many services:

* [https://research.google/pubs/pub48190/](https://research.google/pubs/pub48190/)

The keyword here is *Relationship-based Access Control*, which is ...

> [...] an authorization paradigm where a subject's permission to access a resource is defined by the 
> presence of relationships between those subjects and resources.

Let's find out about it! 

I have previously [written an article about the Google Zanzibar Data Model], and also wrote some 
pretty nice SQL statements to make sense of the it. This article will make use of the ideas, queries 
and takes a look at implementing Relationship-based Access Control using Microsoft SQL Server and 
ASP.NET Core.

All code in this article can be found in a repository at:

* [https://github.com/bytefish/RebacExperiments](https://github.com/bytefish/RebacExperiments)

## Table of contents ##

[TOC]

## Role-based and Relationship-based ACL ##

We are going to build out a tiny part of a Task Management system. Why? Because tasks are basically 
everywhere in an organization, such as having tasks for signing documents, calling back customers or 
reminders to write invoices. They are a good example use case for authorization.

The situation is now somewhat similar to the Google Drive example. You obviously don't want an entire 
organization to view, edit, delete or close all tasks. Given a sufficiently large headcount it would 
quickly escalate into a chaos, if we don't authorize users.

### Role-based Access Control (RBAC) ###

[Authoring an RBAC API for your application (by Stewart Adam)]: https://devblogs.microsoft.com/ise/2023/10/12/rbac-api-for-your-application/

Role-based Access Control is definitely among the most popular models for defining permissions and 
authorizing access to an organizations resources, such as our tasks. Highly simplified, a user is 
being assigned a set of roles, where each role represents the users role within the organization.

Back to our Task Management system, a regular user might be able to view, edit and close tasks, while 
it requires elevated rights to actually delete a task. Likewise a user being assigned to the role 
*Software Development* should probably not be permitted to view or edit tasks created by the 
*Human Resources* people.

There was recently a great Microsoft DevBlogs article by Stewart Adam, that discusses designing Role-based 
Access Control for applications and it's a great read. It discusses quite a similar use case and comes up 
with solutions:

* [Authoring an RBAC API for your application (by Stewart Adam)]

As you can see in the article, a Role-based Access Control can get very complex, very quickly. We have 
"Subtree grants", "Entity Graph Scopes", "Nested Roles", "Permission Wildcards", ... and sadly none of 
it is illustrated with *actual code*, none of this exists in ASP.NET Core.

In my experience Role-based Access Control can take you very, very far. And it works great, as long as 
an organization strictly adheres to the roles defined. But as soon you need a more fine-grained control, 
you are most probably out of luck. 

And in so many projects I've learnt, that *there is always a special snowflake*, that doesn't fit the 
roles and needs a special role. This *may* lead to an explosion in roles, or you apply the compensation 
mentioned in [Authoring an RBAC API for your application (by Stewart Adam)] (oh, or you just give up 
and grant the user elevated rights).

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

So using Role-based Access Control and Relationship-based Access Control is not a mutually exclusive decision. You can 
easily build Role-based Access Control upon the Google Zanzibar data model and use the Access Control system, that 
works best for your use case. 

## What we are going to build ##

We will build a small part of a Task Management System using ASP.NET Core and EntityFramework Core. The idea is 
to wrap the Check API and ListObjects API developed in the previous Google Zanzibar article with EntityFramework 
Core and integrate it into the ASP.NET Core pipeline. 

At the end of this article we will have a RESTful API, that's authorizes a user using a Relationship-based 
Access Control, based on the Google Zanzibar data model. Here is the Swagger Overview.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/swagger_endpoints.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/swagger_endpoints.jpg" alt="Final Swagger Endpoints">
    </a>
</div>

Maybe in a later article we will develop a Blazor application to query it.

## Database Design ##

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

They don't hurt and they might turn out very useful. And if you don't need a history? 🤷, just deactivate the Temporal Table and call it a day!

Do Temporal Tables solve all problems? Oh, for sure they don't and they are a trade-off, like everything in software 
development. You might run into problems on high volume data, you have to deactivate temporal tables before 
migrations and need to set 

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

#### Short Story on Auditing with EntityFramework Core ####

The canonical EntityFramework Core example you'll find for auditing, usually works by overriding the 
`DbContext#SaveChanges` method or intercepting its call, and then inspect the `DbContext` Change 
Tracker for changes.

This is illustrated by the following code snippet, which implements a `SaveChangesInterceptor`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using EfCoreAudit.Model;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;

namespace EfCoreAudit.Database.Interceptors
{
    /// <summary>
    /// A <see cref="SaveChangesInterceptor"/> for adding auditing metadata.
    /// </summary>
    internal class AuditingInterceptor : SaveChangesInterceptor
    {
        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(DbContextEventData eventData, InterceptionResult<int> result, CancellationToken cancellationToken = default)
        {
            DbContext ctx = eventData.Context!;

            if (ctx == null)
            {
                return base.SavingChangesAsync(eventData, result, cancellationToken);
            }

            var auditableEntities = ctx.ChangeTracker.Entries<AuditableEntity>().ToList();

            foreach (var auditableEntity in auditableEntities)
            {

                if (auditableEntity.State == EntityState.Added)
                {
                    auditableEntity.Property(x => x.CreatedDateTime).CurrentValue = DateTime.UtcNow;
                }

                if (auditableEntity.State == EntityState.Modified)
                {
                    auditableEntity.Property(x => x.ModifiedDateTime).CurrentValue = DateTime.UtcNow;
                }
            }

            return base.SavingChangesAsync(eventData, result, cancellationToken);
        }
    }
}
```

It's a bad advice, because it works only as long as all your entities are tracked, but a Change Tracker is an expensive 
thing... and more importantly, as soon as you are using the modern `DbSet<T>#ExecuteUpdateAsync` you are out of luck 
with this approach. And what about Stored Procedures? One-Time Scripts? Migrations? 

Just let your (very) expensive database handle it and use Temporal Tables. And by the way, I've asked the .NET community 
on Mastodon, what's their strategy for auditing changes to their database and Change Data Capture (CDC) came up, so this 
might also a path.

### Schemas ###

Now the wall of text is over. Let's get to actual code!

We have two schemas named `[Identity]` and `[Application]`. The `[Identity]` schema, surprise, is going to hold all 
identity related stuff, such as a `User`, a `Role` and the `RelationTuple` for defining the permissions. It's also 
going to hold the functions to list objects and check for permissions. 

The `[Application]` schema is going to hold everything not directly related to the Identity management, such as `UserTask`, 
`Organization`, `Team`, ... entities.  


#### Sequences ####

By using Sequences offer several advantadges over an Auto-Incrementing Primary Key. We can set the start value and 
increment values of the Sequence, which is useful when inserting the initial data with fixed IDs and 
having it automatically incrementing right after. 

And what's particularly interesting to us is, that we can use it to implement the Hi-Lo Pattern. The EntityFramework 
documentation has the following to say about the Hi/Lo Algorithm:

> The Hi/Lo algorithm is useful when you need unique keys before committing changes. As a summary, the Hi-Lo 
> algorithm assigns unique identifiers to table rows while not depending on storing the row in the database 
> immediately. This lets you start using the identifiers right away, as happens with regular sequential 
> database IDs.

So we define our sequences for all tables.

```sql
CREATE SEQUENCE [Identity].[sq_User]
    AS INT
    START WITH 38187
    INCREMENT BY 1;
    
CREATE SEQUENCE [Identity].[sq_Role]
    AS INT
    START WITH 38187
    INCREMENT BY 1;
    
CREATE SEQUENCE [Identity].[sq_RelationTuple]
    AS INT
    START WITH 38187
    INCREMENT BY 1;
```

#### Tables ####

The application has a very simple `User` model for now. A user may be permitted to Logon using a Logon Name, 
the Logon Name is unique among all users. The password hashing needs to be done in the application, when adding 
a user to the system.

```sql
CREATE TABLE [Identity].[User](
    [UserID]                INT                                         CONSTRAINT [DF_Identity_User_UserID] DEFAULT (NEXT VALUE FOR [Identity].[sq_User]) NOT NULL,
    [FullName]              NVARCHAR(50)                                NOT NULL,
    [PreferredName]         NVARCHAR(50)                                NULL,
    [IsPermittedToLogon]    BIT                                         NOT NULL,
    [LogonName]             NVARCHAR (256)                              NULL,
    [HashedPassword]        NVARCHAR (MAX)                              NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_User] PRIMARY KEY ([UserID]),
    CONSTRAINT [FK_User_LastEditedBy_User_UserID] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[UserHistory]));
```

To build a Role-based Access Control on top of the Relationship-based model, we add a table `[Identity].[Role]` to hold the roles in our system.

```sql
CREATE TABLE [Identity].[Role](
    [RoleID]                INT                                         CONSTRAINT [DF_Identity_Role_RoleID] DEFAULT (NEXT VALUE FOR [Identity].[sq_Role]) NOT NULL,
    [Name]                  NVARCHAR(255)                               NOT NULL,
    [Description]           NVARCHAR(2000)                              NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_Role] PRIMARY KEY ([RoleID]),
    CONSTRAINT [FK_Role_LastEditedBy_User_UserID] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[RoleHistory]));
```

The table `[Identity].[RelationTuple]` is the secret sauce here, that's going to be at the heart of the Relationship-based Access Control.

```sql
CREATE TABLE [Identity].[RelationTuple](
    [RelationTupleID]       INT                                         CONSTRAINT [DF_Identity_RelationTuple_RelationTupleID] DEFAULT (NEXT VALUE FOR [Identity].[sq_RelationTuple]) NOT NULL,
    [ObjectKey]             INT                                         NOT NULL,
    [ObjectNamespace]       NVARCHAR(50)                                NOT NULL,
    [ObjectRelation]        NVARCHAR(50)                                NOT NULL,
    [SubjectKey]            INT                                         NOT NULL,
    [SubjectNamespace]      NVARCHAR(50)                                NOT NULL,
    [SubjectRelation]       NVARCHAR(50)                                NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_RelationTupleID] PRIMARY KEY ([RelationTupleID]),
    CONSTRAINT [FK_RelationTuple_LastEditedBy_User_UserID] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[RelationTupleHistory]));
```

#### Functions ####

[Exploring Relationship-based Access Control (ReBAC) with Google Zanzibar]: https://www.bytefish.de/blog/relationship_based_acl_with_google_zanzibar.html

The Google Zanzibar Check API is implemented by the User Defined Function `[Identity].[udf_RelationTuples_Check]`, which 
is explained in great detail in my article [Exploring Relationship-based Access Control (ReBAC) with Google Zanzibar].

```sql
CREATE FUNCTION [Identity].[udf_RelationTuples_Check]
(
     @ObjectNamespace NVARCHAR(50)
    ,@ObjectKey INT
    ,@ObjectRelation NVARCHAR(50)
    ,@SubjectNamespace NVARCHAR(50)
    ,@SubjectKey INT
)
RETURNS BIT
AS
BEGIN

    DECLARE @IsAuthorized BIT = 0;

    WITH RelationTuples AS
    (
       SELECT
    	   [RelationTupleID]
          ,[ObjectNamespace]
          ,[ObjectKey]
          ,[ObjectRelation]
          ,[SubjectNamespace]
          ,[SubjectKey]
          ,[SubjectRelation]
    	  , 0 AS [HierarchyLevel]
        FROM
          [Identity].[RelationTuple]
        WHERE
    		[ObjectNamespace] = @ObjectNamespace AND [ObjectKey] = @ObjectKey AND [ObjectRelation] = @ObjectRelation
    	  
    	UNION All
    	
    	SELECT        
    	   r.[RelationTupleID]
    	  ,r.[ObjectNamespace]
          ,r.[ObjectKey]
          ,r.[ObjectRelation]
          ,r.[SubjectNamespace]
          ,r.[SubjectKey]
          ,r.[SubjectRelation]
    	  ,[HierarchyLevel] + 1 AS [HierarchyLevel]
      FROM 
    	[Identity].[RelationTuple] r, [RelationTuples] cte
      WHERE 
    	cte.[SubjectKey] = r.[ObjectKey] 
    		AND cte.[SubjectNamespace] = r.[ObjectNamespace] 
    		AND cte.[SubjectRelation] = r.[ObjectRelation]
    )
    SELECT @IsAuthorized =
    	CASE
    		WHEN EXISTS(SELECT 1 FROM [RelationTuples] WHERE [SubjectNamespace] = @SubjectNamespace AND [SubjectKey] = @SubjectKey) 
    			THEN 1
    		ELSE 0
    	END;

    RETURN @IsAuthorized;
END
```

You want to answer questions like "What Tasks is a User allowed to see?", "What Organizations is a User 
member of?". This can be done by using the ListObjects function, that has been written in a previous 
article.

```sql
CREATE FUNCTION [Identity].[tvf_RelationTuples_ListObjects]
(
     @ObjectNamespace NVARCHAR(50) 
    ,@ObjectRelation NVARCHAR(50)
    ,@SubjectNamespace NVARCHAR(50)
    ,@SubjectKey INT
)
RETURNS @returntable TABLE
(

     [RelationTupleID]   INT
    ,[ObjectNamespace]   NVARCHAR(50)
    ,[ObjectKey]         INT
    ,[ObjectRelation]    NVARCHAR(50)
    ,[SubjectNamespace]  NVARCHAR(50)
    ,[SubjectKey]        INT
    ,[SubjectRelation]   NVARCHAR(50)
)
AS
BEGIN

    WITH RelationTuples AS
    (
       SELECT
	       [RelationTupleID]
          ,[ObjectNamespace]
          ,[ObjectKey]
          ,[ObjectRelation]
          ,[SubjectNamespace]
          ,[SubjectKey]
          ,[SubjectRelation]
	      , 0 AS [HierarchyLevel]
        FROM
          [Identity].[RelationTuple]
        WHERE
		    [SubjectNamespace] = @SubjectNamespace AND [SubjectKey] = @SubjectKey
	  
	    UNION All
	
	    SELECT        
	       r.[RelationTupleID]
	      ,r.[ObjectNamespace]
          ,r.[ObjectKey]
          ,r.[ObjectRelation]
          ,r.[SubjectNamespace]
          ,r.[SubjectKey]
          ,r.[SubjectRelation]
	      ,[HierarchyLevel] + 1 AS [HierarchyLevel]
      FROM 
	    [Identity].[RelationTuple] r, [RelationTuples] cte
      WHERE 
	    cte.[ObjectKey] = r.[SubjectKey] 
		    AND cte.[ObjectNamespace] = r.[SubjectNamespace] 
		    AND cte.[ObjectRelation] = r.[SubjectRelation]
    )
    INSERT 
        @returntable
    SELECT DISTINCT 
	    [RelationTupleID], [ObjectNamespace], [ObjectKey], [ObjectRelation], [SubjectNamespace], [SubjectKey], [SubjectRelation]
    FROM 
	    [RelationTuples] 
    WHERE
	    [ObjectNamespace] = @ObjectNamespace AND [ObjectRelation] = @ObjectRelation;

    RETURN;

END
```

#### Stored Procedures ####

The tables are system versioned, but for inserting the initial data we need to turn it off. So 
we are adding a Stored Procedure `[Identity].[usp_TemporalTables_DeactivateTemporalTables]` to 
deactivate the versioning.

```sql
CREATE PROCEDURE [Identity].[usp_TemporalTables_DeactivateTemporalTables]
AS BEGIN
	IF OBJECTPROPERTY(OBJECT_ID('[Identity].[User]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Identity].[User]'

		ALTER TABLE [Identity].[User] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Identity].[User] DROP PERIOD FOR SYSTEM_TIME;
	END

    IF OBJECTPROPERTY(OBJECT_ID('[Identity].[Role]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Identity].[Role]'

		ALTER TABLE [Identity].[Role] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Identity].[Role] DROP PERIOD FOR SYSTEM_TIME;
	END


	IF OBJECTPROPERTY(OBJECT_ID('[Identity].[RelationTuple]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Identity].[RelationTuple]'

		ALTER TABLE [Identity].[RelationTuple] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Identity].[RelationTuple] DROP PERIOD FOR SYSTEM_TIME;
	END

END
```

After the data has been inserted, we want to reactivate the versioning again. So we are adding 
a Stored Procedure `[Identity].[usp_TemporalTables_ReactivateTemporalTables]`, that restores 
the system versioning.

```sql
CREATE PROCEDURE [Identity].[usp_TemporalTables_ReactivateTemporalTables]
AS BEGIN

	IF OBJECTPROPERTY(OBJECT_ID('[Identity].[User]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Identity].[User]'

		ALTER TABLE [Identity].[User] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Identity].[User] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[UserHistory], DATA_CONSISTENCY_CHECK = ON));
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Identity].[Role]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Identity].[Role]'

		ALTER TABLE [Identity].[Role] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Identity].[Role] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[RoleHistory], DATA_CONSISTENCY_CHECK = ON));
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Identity].[RelationTuple]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Identity].[RelationTuple]'

		ALTER TABLE [Identity].[RelationTuple] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Identity].[RelationTuple] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[RelationTupleHistory], DATA_CONSISTENCY_CHECK = ON));
	END
    
END
```

### Schema: Application ###

#### Tables ####

```sql
CREATE TABLE [Application].[UserTask](
    [UserTaskID]            INT                                         CONSTRAINT [DF_Application_UserTask_UserTaskID] DEFAULT (NEXT VALUE FOR [Application].[sq_UserTask]) NOT NULL,
    [Title]                 NVARCHAR(50)                                NOT NULL,
    [Description]           NVARCHAR(2000)                              NOT NULL,
    [DueDateTime]           DATETIME2(7)                                NULL,
    [ReminderDateTime]      DATETIME2(7)                                NULL,
    [CompletedDateTime]     DATETIME2(7)                                NULL,
    [AssignedTo]            INT                                         NULL,
    [UserTaskPriorityID]    INT                                         NOT NULL,
    [UserTaskStatusID]      INT                                         NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_UserTask] PRIMARY KEY ([UserTaskID]),
    CONSTRAINT [FK_UserTask_UserTaskPriority_UserTaskPriorityID] FOREIGN KEY ([UserTaskPriorityID]) REFERENCES [Application].[UserTaskPriority] ([UserTaskPriorityID]),
    CONSTRAINT [FK_UserTask_UserTaskStatus_UserTaskStatusID] FOREIGN KEY ([UserTaskStatusID]) REFERENCES [Application].[UserTaskStatus] ([UserTaskStatusID]),
    CONSTRAINT [FK_UserTask_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    CONSTRAINT [FK_UserTask_User_AssignedTo] FOREIGN KEY ([AssignedTo]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskHistory]));
```

```sql
CREATE TABLE [Application].[UserTaskPriority](
    [UserTaskPriorityID]    INT                                         NOT NULL,
    [Name]                  NVARCHAR(50)                                NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_UserTaskPriority] PRIMARY KEY ([UserTaskPriorityID]),
    CONSTRAINT [FK_UserTaskPriority_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskPriorityHistory]));
```

```sql

```

#### Stored Procedures ####

As discussed, all our tables are system-versioned, and we need to deactivate them before running our initial 
inserts. So we add a Stored Procedure `[Application].[usp_TemporalTables_DeactivateTemporalTables]` to deactivate 
the versioning.

```sql
CREATE PROCEDURE [Application].[usp_TemporalTables_DeactivateTemporalTables]
AS BEGIN
	IF OBJECTPROPERTY(OBJECT_ID('[Application].[UserTask]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Application].[UserTask]'

		ALTER TABLE [Application].[UserTask] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Application].[UserTask] DROP PERIOD FOR SYSTEM_TIME;
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Application].[UserTaskPriority]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Application].[UserTaskPriority]'

		ALTER TABLE [Application].[UserTaskPriority] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Application].[UserTaskPriority] DROP PERIOD FOR SYSTEM_TIME;
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Application].[UserTaskStatus]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Application].[UserTaskStatus]'

		ALTER TABLE [Application].[UserTaskStatus] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Application].[UserTaskStatus] DROP PERIOD FOR SYSTEM_TIME;
	END
    
	IF OBJECTPROPERTY(OBJECT_ID('[Application].[Organization]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Application].[Organization]'

		ALTER TABLE [Application].[Organization] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Application].[Organization] DROP PERIOD FOR SYSTEM_TIME;
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Application].[Team]'), 'TableTemporalType') = 2
	BEGIN
		PRINT 'Deactivate Temporal Table for [Application].[Team]'

		ALTER TABLE [Application].[Team] SET (SYSTEM_VERSIONING = OFF);
		ALTER TABLE [Application].[Team] DROP PERIOD FOR SYSTEM_TIME;
	END

END
```

After running the Post-Deployment Scripts, we are reactivating the System-Versioning by executing 
the Stored Procedure `[Application].[usp_TemporalTables_ReactivateTemporalTables]`.

```sql
CREATE PROCEDURE [Application].[usp_TemporalTables_ReactivateTemporalTables]
AS BEGIN

	IF OBJECTPROPERTY(OBJECT_ID('[Application].[UserTask]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Application].[UserTask]'

		ALTER TABLE [Application].[UserTask] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Application].[UserTask] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskHistory], DATA_CONSISTENCY_CHECK = ON));
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Application].[UserTaskPriority]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Application].[UserTaskPriority]'

		ALTER TABLE [Application].[UserTaskPriority] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Application].[UserTaskPriority] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskPriorityHistory], DATA_CONSISTENCY_CHECK = ON));
	END

	IF OBJECTPROPERTY(OBJECT_ID('[Application].[UserTaskStatus]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Application].[UserTaskStatus]'

		ALTER TABLE [Application].[UserTaskStatus] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Application].[UserTaskStatus] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskStatusHistory], DATA_CONSISTENCY_CHECK = ON));
	END
    
	IF OBJECTPROPERTY(OBJECT_ID('[Application].[Organization]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Application].[Organization]'

		ALTER TABLE [Application].[Organization] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Application].[Organization] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[OrganizationHistory], DATA_CONSISTENCY_CHECK = ON));
	END
    
	IF OBJECTPROPERTY(OBJECT_ID('[Application].[Team]'), 'TableTemporalType') = 0
	BEGIN
		PRINT 'Reactivate Temporal Table for [Application].[Team]'

		ALTER TABLE [Application].[Team] ADD PERIOD FOR SYSTEM_TIME([ValidFrom], [ValidTo]);
		ALTER TABLE [Application].[Team] SET (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[TeamHistory], DATA_CONSISTENCY_CHECK = ON));
	END
    
END
```

### Post Deployment Scripts ###

Post-Deployment Scripts are used to insert the initial data. A `User` is needed to do anything in our system, a `UserTaskPriority` 
table needs to have some values, that map to an applications enumeration. 

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/post_deployment_scripts.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/post_deployment_scripts.jpg" alt="Post Deployment Scripts Folder Overview">
    </a>
</div>

The `Script.PostDeployment1.sql` script starts by deactivating the System-Versioning on the tables and then runs 
the scripts for creating data in the `[Identity]` and `[Application]` schema.

```powershell
/*
Post-Deployment Script Template                            
--------------------------------------------------------------------------------------
 This file contains SQL statements that will be appended to the build script.        
 Use SQLCMD syntax to include a file in the post-deployment script.            
 Example:      :r .\myfile.sql                                
 Use SQLCMD syntax to reference a variable in the post-deployment script.        
 Example:      :setvar TableName MyTable                            
               SELECT * FROM [$(TableName)]                    
--------------------------------------------------------------------------------------
*/

/*
  We need to deactivate all Temporal Tables before the initial data load.
*/

EXEC [Identity].[usp_TemporalTables_DeactivateTemporalTables]
GO

EXEC [Application].[usp_TemporalTables_DeactivateTemporalTables]
GO

/* 
    Set the initial data for the [Identity] schema
*/
:r .\Identity\pds-100-ins-identity-users.sql
GO

:r .\Identity\pds-110-ins-identity-roles.sql
GO

:r .\Identity\pds-120-ins-identity-relation-tuples.sql
GO

/* 
    Set the initial data for the [Application] schema
*/
:r .\Application\pds-100-ins-application-task-priority.sql
GO

:r .\Application\pds-110-ins-application-task-status.sql
GO

:r .\Application\pds-120-ins-application-user-task.sql
GO

:r .\Application\pds-130-ins-application-organization.sql
GO

:r .\Application\pds-140-ins-application-team.sql
GO

/*
  We need to reactivate all Temporal Tables after the initial data load.
*/
EXEC [Identity].[usp_TemporalTables_ReactivateTemporalTables]
GO

EXEC [Application].[usp_TemporalTables_ReactivateTemporalTables]
GO
```

We want to be able to re-run the Post-Deployment Scripts on every deployment, without running into constraint 
violations. So we are using a `MERGE` statement, to only insert data, if it doesn't exist yet.

```sql
PRINT 'Inserting [Identity].[User] ...'

-----------------------------------------------
-- Global Parameters
-----------------------------------------------
DECLARE @ValidFrom datetime2(7) = '20130101'
DECLARE @ValidTo datetime2(7) =  '99991231 23:59:59.9999999'

-----------------------------------------------
-- [Identity].[User]
-----------------------------------------------
MERGE INTO [Identity].[User] AS [Target]
USING (VALUES 
     (1, 'Data Conversion Only', 'Data Conversion Only', 0, NULL, NULL, 1, @ValidFrom, @ValidTo)
    ,(2, 'Philipp Wagner',  'Philipp Wagner',   1, 'philipp@bytefish.de',   'AQAAAAIAAYagAAAAELbMFL9utkwA7FK4QoUCZEK/jPiHhTMzuFllrszW7FuCJBHjLVBCWXJCuFFJyRllYg==', 1, @ValidFrom, @ValidTo) --5!F25GbKwU3P
    ,(3, 'John Doe',        'John Doe',         0, 'john@doe.localhost',    NULL, 1, @ValidFrom, @ValidTo)
    ,(4, 'Max Powers',      'Max Powers',       0, 'max@powers.localhost',  NULL, 1, @ValidFrom, @ValidTo)
    ,(5, 'James Bond',      '007',              0, 'james@bond.localhost',  NULL, 1, @ValidFrom, @ValidTo)
    ,(6, 'John Connor',     'John Connor',      0, 'john@connor.localhost', NULL, 1, @ValidFrom, @ValidTo)
) AS [Source]([UserID], [FullName], [PreferredName], [IsPermittedToLogon], [LogonName], [HashedPassword], [LastEditedBy], [ValidFrom], [ValidTo])
ON ([Target].[UserID] = [Source].[UserID])
WHEN NOT MATCHED BY TARGET THEN
    INSERT 
        ([UserID], [FullName], [PreferredName], [IsPermittedToLogon], [LogonName], [HashedPassword], [LastEditedBy], [ValidFrom], [ValidTo])
    VALUES 
        ([Source].[UserID], [Source].[FullName], [Source].[PreferredName], [Source].[IsPermittedToLogon], [Source].[LogonName], [Source].[HashedPassword], [Source].[LastEditedBy], [Source].[ValidFrom], [Source].[ValidTo]);

```

### Deploying the Database ###

The database is done, so we can now deploy it.

You start by doing a Right Click on the database project and select `Publish ...`.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/database_deployment_001_publish.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/database_deployment_001_publish.jpg" alt="Step 1: Publish the SSDT Project by Right Click and selecting Publish">
    </a>
</div>

In the dialog we can see, that the Target Database Connection is empty, and we don't have a database yet. So we 
create one by clicking the `Edit ...` button.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/database_deployment_002_edit_connections.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/database_deployment_002_edit_connections.jpg" alt="Step 2: Click Edit in the Dialog to add a Target Database">
    </a>
</div>

I want to have it running on a local database, so I am selecting `Local` in the Tree View, and select the SQLEXPRESS 
instance. The Server Name and so on gets automatically filled, and we just need to set our database name. I have named 
it `ZanzibarExperiments`, but feel free to select any database name you like.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/database_deployment_003_add_database.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/database_deployment_003_add_database.jpg" alt="Step 3: Select the SQL Server and enter a Database name">
    </a>
</div>

As we can see, the Target Database Connection is now automatically set, and we just need to click the `Publish` button.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/database_deployment_004_run_publish.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/database_deployment_004_run_publish.jpg" alt="Step 4: Run Publish on the Target Database">
    </a>
</div>

The database is now being published and we can inspect the `Data Tools Operation` pane, to see if it worked.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/database_deployment_005_data_tools_operation_output.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/database_deployment_005_data_tools_operation_output.jpg" alt="Step 5: Check the Data Tools Operations Output Window">
    </a>
</div>

Congratulations!

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

## ASP.NET Core ##

### Integrating the ListObjects API ###

We have written a Table-Valued Function `[Identity].[tvf_RelationTuples_ListObjects]` to list all objects a user 
has access to. Let's copy and paste it from the previous article, so you don't have to jump back and forth.

```sql
CREATE FUNCTION [Identity].[tvf_RelationTuples_ListObjects]
(
     @ObjectNamespace NVARCHAR(50) 
    ,@ObjectRelation NVARCHAR(50)
    ,@SubjectNamespace NVARCHAR(50)
    ,@SubjectKey INT
)
RETURNS @returntable TABLE
(

     [RelationTupleID]   INT
    ,[ObjectNamespace]   NVARCHAR(50)
    ,[ObjectKey]         INT
    ,[ObjectRelation]    NVARCHAR(50)
    ,[SubjectNamespace]  NVARCHAR(50)
    ,[SubjectKey]        INT
    ,[SubjectRelation]   NVARCHAR(50)
)
AS
BEGIN

    WITH RelationTuples AS
    (
       SELECT
	       [RelationTupleID]
          ,[ObjectNamespace]
          ,[ObjectKey]
          ,[ObjectRelation]
          ,[SubjectNamespace]
          ,[SubjectKey]
          ,[SubjectRelation]
	      , 0 AS [HierarchyLevel]
        FROM
          [Identity].[RelationTuple]
        WHERE
		    [SubjectNamespace] = @SubjectNamespace AND [SubjectKey] = @SubjectKey
	  
	    UNION All
	
	    SELECT        
	       r.[RelationTupleID]
	      ,r.[ObjectNamespace]
          ,r.[ObjectKey]
          ,r.[ObjectRelation]
          ,r.[SubjectNamespace]
          ,r.[SubjectKey]
          ,r.[SubjectRelation]
	      ,[HierarchyLevel] + 1 AS [HierarchyLevel]
      FROM 
	    [Identity].[RelationTuple] r, [RelationTuples] cte
      WHERE 
	    cte.[ObjectKey] = r.[SubjectKey] 
		    AND cte.[ObjectNamespace] = r.[SubjectNamespace] 
		    AND cte.[ObjectRelation] = r.[SubjectRelation]
    )
    INSERT 
        @returntable
    SELECT DISTINCT 
	    [RelationTupleID], [ObjectNamespace], [ObjectKey], [ObjectRelation], [SubjectNamespace], [SubjectKey], [SubjectRelation]
    FROM 
	    [RelationTuples] 
    WHERE
	    [ObjectNamespace] = @ObjectNamespace AND [ObjectRelation] = @ObjectRelation;

    RETURN;

END
```

We have previously defined a `RelationTuple` entity, that maps just fine to the function.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace RebacExperiments.Server.Api.Models
{
    public class RelationTuple : Entity
    {
        /// <summary>
        /// Gets or sets the ObjectKey.
        /// </summary>
        public int ObjectKey { get; set; }

        /// <summary>
        /// Gets or sets the ObjectNamespace.
        /// </summary>
        public required string ObjectNamespace { get; set; }

        /// <summary>
        /// Gets or sets the ObjectRelation.
        /// </summary>
        public required string ObjectRelation { get; set; }

        /// <summary>
        /// Gets or sets the SubjectKey.
        /// </summary>
        public required int SubjectKey { get; set; }

        /// <summary>
        /// Gets or sets the SubjectNamespace.
        /// </summary>
        public string? SubjectNamespace { get; set; }

        /// <summary>
        /// Gets or sets the SubjectRelation.
        /// </summary>
        public string? SubjectRelation { get; set; }
    }
}
```

What's left is mapping the Table-Valued Function in the `ApplicationDbContext` as the `ListObjects` method.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using RebacExperiments.Server.Api.Models;

namespace RebacExperiments.Server.Api.Infrastructure.Database
{
    /// <summary>
    /// A <see cref="DbContext"/> to query the database.
    /// </summary>
    public class ApplicationDbContext : DbContext
    {
        /// <summary>
        /// Logger.
        /// </summary>
        internal ILogger<ApplicationDbContext> Logger { get; }

        /// <summary>
        /// Constructor.
        /// </summary>
        /// <param name="options">Options to configure the base <see cref="DbContext"/></param>
        public ApplicationDbContext(ILogger<ApplicationDbContext> logger, DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
            Logger = logger;
        }
        
        // ...

        /// <summary>
        /// List Objects.
        /// </summary>
        /// <param name="objectNamespace">Object Namespace</param>
        /// <param name="objectRelation">Object Relation</param>
        /// <param name="subjectNamespace">Subject Namespace</param>
        /// <param name="subjectKey">Subject Key</param>
        /// <returns></returns>
        public IQueryable<RelationTuple> ListObjects(string objectNamespace, string objectRelation, string subjectNamespace, int subjectKey)
            => FromExpression(() => ListObjects(objectNamespace, objectRelation, subjectNamespace, subjectKey));

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            // Add ListObjects Function, so we can use it in LINQ:
            modelBuilder
                .HasDbFunction(
                    methodInfo: typeof(ApplicationDbContext).GetMethod(nameof(ListObjects), new[] { typeof(string), typeof(string), typeof(string), typeof(int) })!,
                    builderAction: builder => builder
                        .HasSchema("Identity")
                        .HasName("tvf_RelationTuples_ListObjects"));
                        
            // ...
            
            base.OnModelCreating(modelBuilder);
        }
    }
}
```

And that's it!

#### Extension Methods to simplify the ListObjects API ####

As of now the `ListObjects` expects us to pass `string` values and an `integer` for the subject key. We want to simplify 
this, and I want to have a method I can call like this:

```csharp
// Get all owned UserTasks for a given user:
var userTasks = _applicationDbContext
    .ListUserObjects<UserTask>(user.Id, Relations.Owner)
    .AsNoTracking()
    .ToList();
    
// Get all Organizations and explicitly define the Object and Subject:
var organizations = _applicationDbContext
    .ListObjects<Organization, User>(user.Id, Relations.Member)
    .AsNoTracking()
    .ToList();
    
// Get all viewable or owned UserTasks for a given user:
var userTasksAsViewerOrOwner = _applicationDbContext
    .ListUserObjects<UserTask>(user.Id, Relations.Viewer, Relations.Owner)
    .AsNoTracking()
    .ToList();
```

We don't put these methods directly into the `ApplicationDbContext`, but define them as Extension methods in 
a static class we call `ApplicationDbContextExtensions`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Models;

namespace RebacExperiments.Server.Api.Infrastructure.Database
{
    /// <summary>
    /// Extensions on the <see cref="ApplicationDbContext"/> to allow Relationship-based ACL.
    /// </summary>
    public static class ApplicationDbContextExtensions
    {
        /// <summary>
        /// Checks if a <see cref="User"/> is authorized to access an <typeparamref name="TObjectType"/>. 
        /// </summary>
        /// <typeparam name="TObjectType">Object Type</typeparam>
        /// <param name="context">DbContext</param>
        /// <param name="objectId">Object Key</param>
        /// <param name="relation">Relation</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns><see cref="true"/>, if the <typeparamref name="TSubjectType"/> is authorized; else <see cref="false"/></returns>
        public static Task<bool> CheckUserObject<TObjectType>(this ApplicationDbContext context, int userId, TObjectType @object, string relation, CancellationToken cancellationToken)
            where TObjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            return CheckObject<TObjectType, User>(context, @object.Id, relation, userId, cancellationToken);
        }

        /// <summary>
        /// Returns all <typeparamref name="TObjectType"/> for a given <typeparamref name="TSubjectType"/> and <paramref name="relation"/>.
        /// </summary>
        /// <param name="subjectId">Subject Key to resolve</param>
        /// <param name="relation">Relation between the Object and Subject</param>
        /// <returns>All <typeparamref name="TEntityType"/> the user is related to</returns>
        public static IQueryable<TObjectType> ListObjects<TObjectType, TSubjectType>(this ApplicationDbContext context, int subjectId, string relation)
            where TObjectType : Entity
            where TSubjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            return
                from entity in context.Set<TObjectType>()
                join objects in context.ListObjects(typeof(TObjectType).Name, relation, typeof(TSubjectType).Name, subjectId)
                    on entity.Id equals objects.ObjectKey
                select entity;
        }

        /// <summary>
        /// Returns all <typeparamref name="TObjectType"/> for a given <typeparamref name="TSubjectType"/> and a list of Relations.
        /// </summary>
        /// <param name="subjectId">Subject Key to resolve</param>
        /// <param name="relation">Relation between the Object and Subject</param>
        /// <returns>All <typeparamref name="TEntityType"/> the user is related to</returns>
        public static IQueryable<TObjectType> ListObjects<TObjectType, TSubjectType>(this ApplicationDbContext context, int subjectId, string[] relations)
            where TObjectType : Entity
            where TSubjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            return relations
                .Select(relation => ListObjects<TObjectType, TSubjectType>(context, subjectId, relation))
                .Aggregate((current, next) => current.Union(next));
        }

        /// <summary>
        /// Returns all <typeparamref name="TEntityType"/> for a given <paramref name="userId"/> and <paramref name="relation"/>.
        /// </summary>
        /// <param name="userId">UserID</param>
        /// <param name="relation">Relation between the User and a <typeparamref name="TEntityType"/></param>
        /// <returns>All <typeparamref name="TEntityType"/> the user is related to</returns>
        public static IQueryable<TEntityType> ListUserObjects<TEntityType>(this ApplicationDbContext context, int userId, string relation)
            where TEntityType : Entity
        {
            context.Logger.TraceMethodEntry();

            return context.ListObjects<TEntityType, User>(userId, relation);
        }

        /// <summary>
        /// Returns all <typeparamref name="TEntityType"/> for a given <paramref name="userId"/> and <paramref name="relation"/>.
        /// </summary>
        /// <param name="userId">UserID</param>
        /// <param name="relation">Relation between the User and a <typeparamref name="TEntityType"/></param>
        /// <returns>All <typeparamref name="TEntityType"/> the user is related to</returns>
        public static IQueryable<TEntityType> ListUserObjects<TEntityType>(this ApplicationDbContext context, int userId, string[] relations)
            where TEntityType : Entity
        {
            context.Logger.TraceMethodEntry();

            return context.ListObjects<TEntityType, User>(userId, relations);
        }

        /// <summary>
        /// Creates a Relationship between a <typeparamref name="TObjectType"/> and a <typeparamref name="TSubjectType"/>.
        /// </summary>
        /// <typeparam name="TObjectType">Type of the Object</typeparam>
        /// <typeparam name="TSubjectType">Type of the Subject</typeparam>
        /// <param name="context">DbContext</param>
        /// <param name="object">Object Entity</param>
        /// <param name="relation">Relation between Object and Subject</param>
        /// <param name="subject">Subject Entity</param>
        /// <param name="subjectRelation">Relation to the Subject</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns></returns>
        public static async Task AddRelationshipAsync<TObjectType, TSubjectType>(this ApplicationDbContext context, TObjectType @object, string relation, TSubjectType subject, string? subjectRelation, int lastEditedBy, CancellationToken cancellationToken = default)
            where TObjectType : Entity
            where TSubjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            var relationTuple = new RelationTuple
            {
                ObjectNamespace = typeof(TObjectType).Name,
                ObjectKey = @object.Id,
                ObjectRelation = relation,
                SubjectNamespace = typeof(TSubjectType).Name,
                SubjectKey = subject.Id,
                SubjectRelation = subjectRelation,
                LastEditedBy = lastEditedBy
            };

            await context.Set<RelationTuple>().AddAsync(relationTuple, cancellationToken);
        }

        /// <summary>
        /// Creates a Relationship between a <typeparamref name="TObjectType"/> and a <typeparamref name="TSubjectType"/>.
        /// </summary>
        /// <typeparam name="TObjectType">Type of the Object</typeparam>
        /// <typeparam name="TSubjectType">Type of the Subject</typeparam>
        /// <param name="context">DbContext</param>
        /// <param name="objectId">Object Entity</param>
        /// <param name="relation">Relation between Object and Subject</param>
        /// <param name="subjectId">Subject Entity</param>
        /// <param name="subjectRelation">Relation to the Subject</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns></returns>
        public static async Task AddRelationshipAsync<TObjectType, TSubjectType>(this ApplicationDbContext context, int objectId, string relation, int subjectId, string? subjectRelation, int lastEditedBy, CancellationToken cancellationToken = default)
            where TObjectType : Entity
            where TSubjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            var relationTuple = new RelationTuple
            {
                ObjectNamespace = typeof(TObjectType).Name,
                ObjectKey = objectId,
                ObjectRelation = relation,
                SubjectNamespace = typeof(TSubjectType).Name,
                SubjectKey = subjectId,
                SubjectRelation = subjectRelation,
                LastEditedBy = lastEditedBy
            };

            await context.Set<RelationTuple>().AddAsync(relationTuple, cancellationToken);
        }
    }
}
```

#### Integration Tests for the ListObjects API ####

What's left is to write some tests for the `ListUserObjects<TObjectType>` methods. We follow the classic 
Arrange-Act-Assert pattern for these tests. It's important for these tests to have an extensive description, 
because while they are pretty short it takes quite some mental overhead to digest the relationships.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using NUnit.Framework;
using RebacExperiments.Server.Api.Infrastructure.Constants;
using RebacExperiments.Server.Api.Infrastructure.Database;
using RebacExperiments.Server.Api.Models;
using System.Linq;
using System.Threading.Tasks;

namespace RebacExperiments.Server.Api.Tests
{
    public class ListUserObjectsTests : TransactionalTestBase
    {
        /// <summary>
        /// In this test we create a <see cref="User"/> (user) and a <see cref="UserTask"/> (task). The 'user' is member of 
        /// a <see cref="Team"/> (team). The 'user' is also a member of an <see cref="Organization"/> (oganization). Members 
        /// of the 'organization' are viewers of the 'task' and members of the 'team' are owners of the 'task'.
        /// 
        /// The Relationship-Table is given below.
        /// 
        /// ObjectKey           |  ObjectNamespace  |   ObjectRelation  |   SubjectKey          |   SubjectNamespace    |   SubjectRelation
        /// --------------------|-------------------|-------------------|-----------------------|-----------------------|-------------------
        /// :team.id:           |   Team            |       member      |   :user.id:           |       User            |   NULL
        /// :organization.id:   |   Organization    |       member      |   :user.id:           |       User            |   NULL
        /// :task.id:           |   UserTask        |       viewer      |   :organization.id:   |       Organization    |   member
        /// :task.id:           |   UserTask        |       owner       |   :team.id:           |       Team            |   member
        /// </summary>
        [Test]
        public async Task ListUserObjects_OneUserTaskAssignedThroughOrganizationAndTeam()
        {
            // Arrange
            var user = new User
            {
                FullName = "Test-User",
                PreferredName = "Test-User",
                IsPermittedToLogon = false,
                LastEditedBy = 1,
                LogonName = "test-user@test-user.localhost"
            };

            await _applicationDbContext.AddAsync(user);
            await _applicationDbContext.SaveChangesAsync();

            var organization = new Organization
            {
                Name = "Test-Organization",
                Description = "Organization for Unit Test",
                LastEditedBy = user.Id
            };

            await _applicationDbContext.AddAsync(organization);
            await _applicationDbContext.SaveChangesAsync();

            var team = new Team
            {
                Name = "Test-Team",
                Description = "Team for Unit Test",
                LastEditedBy = user.Id
            };

            await _applicationDbContext.AddAsync(team);
            await _applicationDbContext.SaveChangesAsync();

            var task = new UserTask
            {
                Title = "Test-Task",
                Description = "My Test-Task",
                LastEditedBy = user.Id,
                UserTaskPriority = UserTaskPriorityEnum.High,
                UserTaskStatus = UserTaskStatusEnum.InProgress
            };

            await _applicationDbContext.AddAsync(task);
            await _applicationDbContext.SaveChangesAsync();

            await _applicationDbContext.AddRelationshipAsync(team, Relations.Member, user, null, user.Id);
            await _applicationDbContext.AddRelationshipAsync(organization, Relations.Member, user, null, user.Id);
            await _applicationDbContext.AddRelationshipAsync(task, Relations.Viewer, organization, Relations.Member, user.Id);
            await _applicationDbContext.AddRelationshipAsync(task, Relations.Owner, team, Relations.Member, user.Id);
            await _applicationDbContext.SaveChangesAsync();

            // Act
            var userTasks_Owner = _applicationDbContext
                .ListUserObjects<UserTask>(user.Id, Relations.Owner)
                .AsNoTracking()
                .ToList();

            var userTasks_Viewer = _applicationDbContext
                .ListUserObjects<UserTask>(user.Id, Relations.Viewer)
                .AsNoTracking()
                .ToList();

            var team_Member = _applicationDbContext
                .ListUserObjects<Team>(user.Id, Relations.Member)
                .AsNoTracking()
                .ToList();

            var organization_Member = _applicationDbContext
                .ListUserObjects<Organization>(user.Id, Relations.Member)
                .AsNoTracking()
                .ToList();

            // Assert
            Assert.AreEqual(1, userTasks_Owner.Count);
            Assert.AreEqual(task.Id, userTasks_Owner[0].Id);

            Assert.AreEqual(1, userTasks_Viewer.Count);
            Assert.AreEqual(task.Id, userTasks_Viewer[0].Id);

            Assert.AreEqual(1, team_Member.Count);
            Assert.AreEqual(team.Id, team_Member[0].Id);

            Assert.AreEqual(1, organization_Member.Count);
            Assert.AreEqual(organization.Id, organization_Member[0].Id);
        }

        /// <summary>
        /// In this test we create a <see cref="User"/> (user) and assign two <see cref="UserTask"/> (tas1, task2). The 'user' 
        /// is 'viewer' for 'task1' and an 'owner' for 'task2'.
        /// 
        /// The Relationship-Table is given below.
        /// 
        /// ObjectKey           |  ObjectNamespace  |   ObjectRelation  |   SubjectKey          |   SubjectNamespace    |   SubjectRelation
        /// --------------------|-------------------|-------------------|-----------------------|-----------------------|-------------------
        /// :task1.id:          |   UserTask        |       viewer      |   :user.id:           |       User            |   NULL
        /// :task2.id:          |   UserTask        |       owner       |   :user.id:           |       User            |   NULL
        /// </summary>
        [Test]
        public async Task ListUserObjects_TwoUserTasksAssignedToOrganizationAndTeam()
        {
            // Arrange
            var user = new User
            {
                FullName = "Test-User",
                PreferredName = "Test-User",
                IsPermittedToLogon = false,
                LastEditedBy = 1,
                LogonName = "test-user@test-user.localhost"
            };

            await _applicationDbContext.AddAsync(user);
            await _applicationDbContext.SaveChangesAsync();

            var task1 = new UserTask
            {
                Title = "Task 1",
                Description = "Task 1",
                LastEditedBy = user.Id,
                UserTaskPriority = UserTaskPriorityEnum.High,
                UserTaskStatus = UserTaskStatusEnum.InProgress
            };
            
            var task2 = new UserTask
            {
                Title = "Task2",
                Description = "Task2",
                LastEditedBy = user.Id,
                UserTaskPriority = UserTaskPriorityEnum.High,
                UserTaskStatus = UserTaskStatusEnum.InProgress
            };

            await _applicationDbContext.AddRangeAsync(new[] { task1, task2 });
            await _applicationDbContext.SaveChangesAsync();

            await _applicationDbContext.AddRelationshipAsync(task1, Relations.Viewer, user, null, user.Id);
            await _applicationDbContext.AddRelationshipAsync(task2, Relations.Owner, user, null, user.Id);
            await _applicationDbContext.SaveChangesAsync();

            // Act
            var userTasks = _applicationDbContext
                .ListUserObjects<UserTask>(user.Id, new[] { Relations.Viewer, Relations.Owner })
                .AsNoTracking()
                .ToList();

            Assert.AreEqual(2, userTasks.Count);
            Assert.IsTrue(userTasks.Any(x => x.Id == task1.Id));
            Assert.IsTrue(userTasks.Any(x => x.Id == task2.Id));
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

