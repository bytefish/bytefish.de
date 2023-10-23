title: Relationship-based Access Control with ASP.NET Core, EntityFramework Core and SQL
date: 2023-10-23 11:10
tags: aspnetcore, dotnet, csharp, sql, datamining
category: dotnet
slug: aspnetcore_rebac
author: Philipp Wagner
summary: This article shows a way to implement a Relationship-based Access Control in ASP.NET Core, EntityFramework Core and SQL.

[written an article about the Google Zanzibar Data Model]: https://www.bytefish.de/blog/relationship_based_acl_with_google_zanzibar.html

The Google Drive app starts and a moment later *your files* appear. It's magic. But have you 
ever wondered what's *your files* actually? How do these services actually know, which files 
*you are allowed* to see?

Are you part of an *Organization* and you are allowed to *view* all their files? Have you been 
assigned to a *Team*, that's allowed to *view* or *edit* files? Has someone shared *their files* 
with *you* as a *User*?

So in 2019 Google has lifted the curtain and has published a paper on *Google Zanzibar*, which 
is Google's central solution for providing authorization among its many services:

* [https://research.google/pubs/pub48190/](https://research.google/pubs/pub48190/)

The keyword here is *Relationship-based Access Control*, which is ...

> [...] an authorization paradigm where a subject's permission to access a resource is defined by the 
> presence of relationships between those subjects and resources.

I have previously [written an article about the Google Zanzibar Data Model], and also wrote some 
pretty nice SQL statements to make sense of the it. This article will make use of the ideas and 
queries, and takes a look at implementing Relationship-based Access Control using Microsoft 
SQL Server and ASP.NET Core.

All code in this article can be found in a repository at:

* [https://github.com/bytefish/RebacExperiments](https://github.com/bytefish/RebacExperiments)

## Table of contents ##

[TOC]

## Role-based and Relationship-based ACL ##

We are going to build a tiny part of a Task Management system.Tasks are basically everywhere in an 
organization, such as having tasks for signing documents, calling back customers or reminders to write 
invoices. They are a good example use case for authorization.

The situation for such a Task Management system is somewhat similar to the Google Drive example. You 
obviously don't want an entire organization to view, edit, delete or close *all* tasks. Given a sufficiently 
large headcount in a company, unauthorized access would quickly escalate into a chaos.

### Role-based Access Control (RBAC) ###

[Authoring an RBAC API for your application (by Stewart Adam)]: https://devblogs.microsoft.com/ise/2023/10/12/rbac-api-for-your-application/

One way to authorize a user is by using Role-based Access Control (RBAC).

Role-based Access Control is definitely among the most popular models for defining permissions and 
authorizing access to an organizations resources, such as our tasks. Highly simplified, a user is 
being assigned to a set of roles, where each role represents the users role within the organization.

In to our Task Management system, a regular user might be able to view tasks, while it requires elevated 
rights to actually delete a task. Likewise a user being assigned to the role *Software Development* should 
probably not be permitted to edit tasks created by the *Human Resources* people.

That said, there was recently a great Microsoft DevBlogs article by Stewart Adam, that discusses designing 
Role-based Access Control for applications and it's a great read. It discusses quite a similar use case 
and comes up with some solutions:

* [Authoring an RBAC API for your application (by Stewart Adam)]

As you can see in the article, a Role-based Access Control can get very complex, very quickly. "Subtree grants", 
"Entity Graph Scopes", "Nested Roles", "Permission Wildcards", ... it sounds great in theory, but sadly none of 
it is illustrated with *actual code*, and more importantly none of this exists in ASP.NET Core.

In my experience Role-based Access Control can take you very, very far. And it works great, as long as 
an organization strictly adheres to the roles defined. But as soon you need a more fine-grained control, 
you are out of luck with Roles.

Many, many projects taught me, that *there is always a special snowflake*, that doesn't fit the defined 
roles and needs a special treatment. This *may* lead to an explosion in roles, if you don't have compensation 
strategies as mentioned in "[Authoring an RBAC API for your application (by Stewart Adam)]".

### Relationship-based Access Control (ReBAC) ###

One way for having fine-grained Access Control is to employ something similar to Google Zanzibar. Google Zanzibar 
was first described by Google in a 2019 paper called *Zanzibar: Google’s Consistent, Global Authorization System* 
and the paper is available for download at:

* [https://research.google/pubs/pub48190/](https://research.google/pubs/pub48190/)

It describes the Google's motivation for building a unified authorization system and describes the 
data model, language and its API. After publishing the paper various vendors and open source 
implementations have materialized.

I think there are many excellent sources, that explain Google Zanzibar in detail, and much better, than I could:

* [Exploring Google Zanzibar: A Demonstration of Its Basics (by Ege Aytin)](https://www.permify.co/post/exploring-google-zanzibar-a-demonstration-of-its-basics)
* [Building Zanzibar from Scratch (by Sam Scott)](https://www.osohq.com/post/zanzibar)
* [Zanzibar-style ACLs with Prolog (by Radek Gruchalski)](https://gruchalski.com/posts/2022-09-03-zanzibar-style-acls-with-prolog/)

Highly, highly simplified, Google Zanzibar models relationships between `Objects` and `Subjects` using the following notation:

```
<object>#<relation>@<subject>#<subject_relation>
```

Say we have our system to manage tasks, then we could make up relations like this with the Google Zanzibar syntax:

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

We could build a Role-based Access Control upon the Google Zanzibar data model, something that's already been noted in 
Google's original paper ...

> [...] A number of Zanzibar clients have implemented RBAC policies on top of Zanzibar’s namespace configuration language. [...]

So using Role-based Access Control and Relationship-based Access Control is by no means a mutually exclusive decision. You can 
easily build a Role-based Access Control model upon Relationship-based Access Control... use what's best for your use case. As 
for ASP.NET Core, I imagine protecting the `Controller` with Roles and have Fine-Grained Access Control on Service-Level using 
Relationships.

## What we are going to build ##

We will build a small part of a Task Management System using ASP.NET Core and EntityFramework Core. The idea is 
to wrap the Check API and ListObjects API, developed in the previous Google Zanzibar article, with EntityFramework 
Core and integrate it into the ASP.NET Core pipeline. 

At the end of this article we will have a RESTful API, that's authorizes a user using a Relationship-based 
Access Control. We will see how to create the database, configure logging, run integration tests and use 
`.http` files for manual endpoint tests in Visual Studio.

Here is the Swagger Overview for the final API Endpoints. 

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/swagger_endpoints.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/swagger_endpoints.jpg" alt="Final Swagger Endpoints">
    </a>
</div>

## Database Design ##

If you are going to work with a relational database, then you should put all your database objects in version control. The 
best example for a SQL Server Database Project (SSDP) available out there is the [WideWorldImporters OLTP Database] example 
provided in the SQL Server examples repository:

* [https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt)

### Prerequisites ###

#### Project Structure ####

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

#### SQL Server Object Name Convention ####

[Naming convention]: https://en.wikipedia.org/wiki/Naming_convention_(programming)

What's a "*Naming Convention*"?

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

#### Auditing and Optimistic Locking ####

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

They don't hurt and they might turn out very useful. And if you don't need a history? Then just deactivate the Temporal Table and call it a day!

#### Temporal Tables ####

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

Like everything in software engineering, temporal tables do not magically solve all problems and are a trade-off. You might run into 
problems on high volume datasets. You have to deactivate temporal tables before migrations and probably need to put it into single user 
mode during schema migrations.

### Database Project Overview ###

It's a good idea to get an overview for our database project first. We create a SQL Server Database Project (SSDP), call 
it `RebacExperiments.Server.SSDT` and put all our Database Objects and Scripts into it.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/database_project_overview.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/database_project_overview.jpg" alt="Database Project Overview">
    </a>
</div>

There are two schemas named `[Identity]` and `[Application]`. The `[Identity]` schema, surprise, is going to hold all identity 
related stuff, such as a `User`, a `Role` and the `RelationTuple` for defining the relationships between entities. It's also 
going to hold the functions to list objects and check for permissions.

The `[Application]` schema is going to hold everything not directly related to the Identity management, such as `UserTask`, 
`Organization`, `Team`, ... entities. The `[Application]` schema takes a hard dependency on the `[Identity]` schema, because 
we refer to the `[Identity].[User]` table with a Foreign Key Constraint.

### Schema "Identity"  ###

#### Sequences ####

We are using Sequences instead of an Auto-Incrementing Primary Key. A Sequence has some advantadges, such as setting 
explicit start and increment values. And what's particularly interesting to us is, that we can use the Sequence to 
implement the Hi-Lo Pattern in code.

The EntityFramework documentation has the following to say about the Hi/Lo Algorithm:

> The Hi/Lo algorithm is useful when you need unique keys before committing changes. As a summary, the Hi-Lo 
> algorithm assigns unique identifiers to table rows while not depending on storing the row in the database 
> immediately. This lets you start using the identifiers right away, as happens with regular sequential 
> database IDs.

We define our sequences for all tables in their respective files as:

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

The application has a very simple `User` model. A user may be permitted to Logon using a Logon Name, the Logon Name 
is unique among all users. The password hashing is done on application-level, when logging into the system or 
registering users.

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

To build a Role-based Access Control on top of the Relationship-based model, we add a table `[Identity].[Role]` to hold all roles available in our system.

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

The table `[Identity].[RelationTuple]` is the secret sauce here, that's going to be at the heart of the Relationship-based Access Control. As 
you can see, the `[ObjectKey]` and `[SubjectKey]` has been defined as an `INT` column type, so we make the assumption, that all tables in our 
database have `INT` Primary Key. 

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

The Google Zanzibar "Check API" is implemented by the User Defined Function `[Identity].[udf_RelationTuples_Check]`, which 
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

And you want to answer questions like "What Tasks is a User allowed to see?", "What Organizations is a User 
member of?". This can be done by using the `ListObjects` function, that has been written in a previous 
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

The tables are system versioned, but for inserting the initial data with explicit `ValidFrom` and `ValidTo` values, 
we need to turn the versioning off. So we are adding a Stored Procedure `[Identity].[usp_TemporalTables_DeactivateTemporalTables]` to 
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

After the data has been inserted, we want to reactivate the versioning again. So we are also adding a Stored Procedure 
`[Identity].[usp_TemporalTables_ReactivateTemporalTables]`, that restores the system versioning.

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

The Task Management Application deals with... Tasks. I named this a *UserTask* for the sole reason, that *Task* is 
too ambigous in .NET and you'll often accidentally refer to a `System.Threading.Task`... without noticing.

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

A `UserTask` always has a priority assigned, so you know which task needs to be processed. 

We add a table `[Application].[UserTaskPriority]`.

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

A `UserTask` needs a status. Has the `UserTask` been assigned? Is it waiting for others? Has it been defered? Has it been 
completed? We add a table `[Application].[UserTaskStatus]`.

```sql
CREATE TABLE [Application].[UserTaskStatus](
    [UserTaskStatusID]      INT                                         NOT NULL,
    [Name]                  NVARCHAR(50)                                NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_UserTaskStatus] PRIMARY KEY ([UserTaskStatusID]),
    CONSTRAINT [FK_UserTaskStatus_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[UserTaskStatusHistory]));
```

A user may be part of a `Team`, so we can for example make a `User` a member of a `Team`, and we can 
assign a `viewer` permission from a `Team` to a `UserTask`.

```sql
CREATE TABLE [Application].[Team](
    [TeamID]                INT                                         CONSTRAINT [DF_Application_Team_TeamID] DEFAULT (NEXT VALUE FOR [Application].[sq_Team]) NOT NULL,
    [Name]                  NVARCHAR(255)                               NOT NULL,
    [Description]           NVARCHAR(2000)                              NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_Team] PRIMARY KEY ([TeamID]),
    CONSTRAINT [FK_Team_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[TeamHistory]));
```

A user may also be part of an `Organization`, so we can for example make a `User` a member of an `Organization`, and we can 
assign a `viewer` permission from an `Organization` to a `UserTask`.


```sql
CREATE TABLE [Application].[Organization](
    [OrganizationID]        INT                                         CONSTRAINT [DF_Application_Organization_OrganizationID] DEFAULT (NEXT VALUE FOR [Application].[sq_Organization]) NOT NULL,
    [Name]                  NVARCHAR(255)                               NOT NULL,
    [Description]           NVARCHAR(2000)                              NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_Organization] PRIMARY KEY ([OrganizationID]),
    CONSTRAINT [FK_Organization_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[OrganizationHistory]));
```

#### Stored Procedures ####

As mentioned, all our tables are system-versioned, and we need to deactivate them before running our initial 
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

Post-Deployment Scripts are used to seed the database with initial data. A `User` is needed to do anything in our system, 
the `UserTaskPriority` and `UserTaskStatus` tables need to have values, that map to an applications enumeration. 

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

We want to be able to re-run the Post-Deployment Scripts, without running into constraint violations, such 
as Primary Key conflicts. So we are using a `MERGE` statement, to only insert data, if it doesn't exist yet.

An example is the initial data for the `[Identity].[User]` table.

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
    ,(7, 'Max Mustermann',  'Max Mustermann',   1, 'max@mustermann.local',  'AQAAAAIAAYagAAAAELbMFL9utkwA7FK4QoUCZEK/jPiHhTMzuFllrszW7FuCJBHjLVBCWXJCuFFJyRllYg==', 1, @ValidFrom, @ValidTo) --5!F25GbKwU3P
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

## ASP.NET Core Backend with Relationship-based Access Control ##

### Prerequisites ###

There are some prerequisites, that we want to take a look at. It's because... for every project I have 
started I need to gather all the information from Microsoft Learn, GitHub or my previous projects, and 
its good to have it all here.

#### Logging ####

Logging is among the most important things, because *your application will fail* and you really need to be able to investigate 
the reasons.

ASP.NET Core now comes with the `Microsoft.Extensions.Logging` abstractions, so you can plug in any logging framework you 
like. I like Serilog a lot and use it in this example, but I've also had a good experience with NLog, so pick your 
favorite framework. By using the `Microsoft.Extensions.Logging` we can swap the Logging framework anyways.

For Serilog we start by adding the Serilog Core and its `Microsoft.Extensions.Logging` integration.

```xml
<PackageReference Include="Serilog" Version="3.0.1" />
<PackageReference Include="Serilog.Extensions.Logging" Version="7.0.0" />
```

In this example we configure a Console and a File sink, so we also need to add the following NuGet packages:

```xml
<PackageReference Include="Serilog.Sinks.Console" Version="4.1.0" />
<PackageReference Include="Serilog.Sinks.File" Version="5.0.0" />
```

And we want to enrich the Logs with the Machine and Environment Name, so we are adding a dependency on:

```xml
<PackageReference Include="Serilog.Enrichers.Environment" Version="2.3.0" />
```


At the beginning of the `Program.cs` (or where your Startup is) you configure and create a `Log.Logger` instance.

```csharp
// We will log to %LocalAppData%/RebacExperiments to store the Logs, so it doesn't need to be configured 
// to a different path, when you run it on your machine.
string logDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "RebacExperiments");

// We are writing with RollingFileAppender using a daily rotation, and we want to have the filename as 
// as "LogRebacExperiments-{Date}.log", the "{Date}" placeholder will be replaced by Serilog itself.
string logFilePath = Path.Combine(logDirectory, "LogRebacExperiments-.log");

// Configure the Serilog Logger. This Serilog Logger will be passed 
// to the Microsoft.Extensions.Logging LoggingBuilder using the 
// LoggingBuilder#AddSerilog(...) extension.
Log.Logger = new LoggerConfiguration()
    .Enrich.FromLogContext()
    .Enrich.WithMachineName()
    .Enrich.WithEnvironmentName()
    .WriteTo.Console(theme: AnsiConsoleTheme.Code)
    .WriteTo.File(logFilePath, rollingInterval: RollingInterval.Day)
    .CreateLogger();
```

We can then use the `LoggingBuilder#AddSerilog` extension method to register Serilog with the `Microsoft.Extensions.Logging` framework.

```csharp
// Logging
builder.Services.AddLogging(loggingBuilder => loggingBuilder.AddSerilog(dispose: true));
```

I suggest to wrap the entire Starup code inside a fat `try` block, so any error throwing during startup is caught and 
logged to a console or the file sink.

```csharp
// ...

try
{
    var builder = WebApplication.CreateBuilder(args);

    // Add services to the container
    builder.Services.AddSingleton<IUserService, UserService>();
    
    // ...
    
    var app = builder.Build();

    // Configure the HTTP request pipeline.
    app.UseHttpsRedirection();
    
    // ...

    app.Run();
} 
catch(Exception exception)
{
    Log.Fatal(exception, "An unhandeled exception occured.");
}
finally
{
    // Wait 0.5 seconds before closing and flushing, to gather the last few logs.
    await Task.Delay(TimeSpan.FromMilliseconds(500));
    await Log.CloseAndFlushAsync();
}
```

In your application you would then inject a `Microsoft.Extensions.Logging.ILogger` abstraction to your services, which 
is going to be created by the dependency injection container for you.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class AuthenticationController : ControllerBase
    {
        private readonly ILogger<AuthenticationController> _logger;

        public AuthenticationController(ILogger<AuthenticationController> logger)
        {
            _logger = logger;
        }
        
        // ... 
    }
}
```

You shouldn't use the `Log.Logger` singleton directly in your code, as this would make you take a hard dependency on Serilog. Just know, 
that it's totally possible to do so, if you ever need to take a shortcut for your logging or need features only the Serilog logger 
provides.

I have once worked in a .NET Framework project, which used log4net. And the log4net `ILog` abstraction comes with 
properties like `IsDebugEnabled` or `IsErrorEnabled` to check the Log Level. That's useful, because you sometimes 
need to prepare a log message, like transforming a list of objects into something human readable, only in a 
`Debug` log level.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Runtime.CompilerServices;

namespace RebacExperiments.Server.Api.Infrastructure.Logging
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
        
        // ...
    }
}
```

And sometimes you want to understand the flow of your application, when an error occurs... but you can't really debug against the 
production system. That's where a `ILogger<TLoggerType>#TraceMethodEntry` extension method comes in handy, to write logs in 
`Trace` mode and get more information. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Runtime.CompilerServices;

namespace RebacExperiments.Server.Api.Infrastructure.Logging
{
    public static class LoggerExtensions
    {
        // ...
        
        public static void TraceMethodEntry<TLoggerType>(this ILogger<TLoggerType> logger, [CallerFilePath] string? callerFilePath = null, [CallerLineNumber] int? callerLineNumber = null, [CallerMemberName] string callerMemberName = "")
        {
            if (logger.IsTraceEnabled())
            {
                logger.LogTrace("Method Entry (CallerFilePath = {CallerFilePath}, CallerLineNumber = {CallerLineNumber}, CallerMemberName = {CallerMemberName})", 
                    callerFilePath, callerLineNumber, callerMemberName);
            }
        }
    }
}
```

Don't try to be to clever and just add the method call at the top of every method invocation, that you'd like to see in `Trace` mode. No AOP with me!

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Services
{
    public class UserService : IUserService
    {
        private readonly ILogger<UserService> _logger;
        private readonly IPasswordHasher _passwordHasher;

        public UserService(ILogger<UserService> logger, IPasswordHasher passwordHasher)
        {
            _logger = logger;
            _passwordHasher = passwordHasher;
        }

        public async Task<List<Claim>> GetClaimsAsync(ApplicationDbContext context, string username, string password, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();
         
            ...
        }
    }
}
```

That's it for logging.

#### Error Handling ####

Something, that you should decide on early in a project is your error handling. How do you want to communicate 
errors to the programmer and the user? I think, that using Exceptions should be the preferred way of dealing 
with Errors in .NET.

For a user to make sense of errors we need `ErrorCodes`, that can be looked up in a documentation or somewhere.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Error Codes used in the Application.
    /// </summary>
    public static class ErrorCodes
    {
        /// <summary>
        /// General Authentication Error.
        /// </summary>
        public const string AuthenticationFailed = "Auth:000001";

        /// <summary>
        /// Entity has not been found.
        /// </summary>
        public const string EntityNotFound = "Entity:000001";

        /// <summary>
        /// Access to Entity has been unauthorized.
        /// </summary>
        public const string EntityUnauthorized = "Entity:000002";

        /// <summary>
        /// Entity has been modified concurrently.
        /// </summary>
        public const string EntityConcurrencyFailure = "Entity:000003";
    }
}
```

All exceptions in the application then derive from an abstract `ApplicationErrorException`, which requires you 
to define the Error Code for the type of Exception.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    /// <summary>
    /// Base Exception for the Application.
    /// </summary>
    public abstract class ApplicationErrorException : Exception
    {
        /// <summary>
        /// Gets the Error Code.
        /// </summary>
        public abstract string ErrorCode { get; }

        /// <summary>
        /// Gets the Error Message.
        /// </summary>
        public abstract string ErrorMessage { get; }

        protected ApplicationErrorException(string? message, Exception? innerException)
            : base(message, innerException)
        {
        }
    }
}
```

All specific exceptions in the application then derive from the `ApplicationErrorException`, such as an `EntityUnauthorizedAccessException`. 

The `EntityUnauthorizedAccessException` is thrown when you try to access an entity you are not authorized to access. To investigate 
such issues, the exception contains all required data, such as the Entity to be accessed and the User ID.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using RebacExperiments.Server.Api.Infrastructure.Errors;

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    public class EntityUnauthorizedAccessException : ApplicationErrorException
    {
        /// <summary>
        /// Gets or sets an error code.
        /// </summary>
        public override string ErrorCode => ErrorCodes.EntityNotFound;

        /// <summary>
        /// Gets or sets an error code.
        /// </summary>
        public override string ErrorMessage => $"EntityUnauthorizedAccess (User = {UserId}, Entity = {EntityName}, EntityID = {EntityId})";

        /// <summary>
        /// Gets or sets the User ID.
        /// </summary>
        public required int UserId { get; set; }

        /// <summary>
        /// Gets or sets the Entity Name.
        /// </summary>
        public required string EntityName { get; set; }

        /// <summary>
        /// Gets or sets the EntityId.
        /// </summary>
        public required int EntityId { get; set; }

        /// <summary>
        /// Creates a new <see cref="EntityNotFoundException"/>.
        /// </summary>
        /// <param name="message">Error Message</param>
        /// <param name="innerException">Reference to the Inner Exception</param>
        public EntityUnauthorizedAccessException(string? message = null, Exception? innerException = null)
            : base(message, innerException)
        {
        }
    }
}
```

[RFC 7807]: https://datatracker.ietf.org/doc/html/rfc7807

And how do you return the Errors to the caller of the API?

ASP.NET Core comes with `ProblemDetails` and its surrounding infrastructure. The `ProblemDetails` stems from the 
[RFC 7807], which tries to define *[...]  a "problem detail" as a way to carry machine-readable details of 
errors in a HTTP response to avoid the need to define new error response formats for HTTP APIs.*

I would suggest to use them.

I think for this application we can get away with an `ApplicationErrorHandler`, that handles the specific exceptions 
and transforms them into an `ObjectResult`. A younger me would have tried to make it as generic as possible. These 
days, I prefer doing the stuff in the most straightforward way.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Options for the <see cref="ApplicationErrorHandler"/>.
    /// </summary>
    public class ApplicationErrorHandlerOptions
    {
        /// <summary>
        /// Gets or sets the option to include the Exception Details in the response.
        /// </summary>
        public bool IncludeExceptionDetails { get; set; } = false;
    }

    /// <summary>
    /// Handles errors returned by the application.
    /// </summary>
    public class ApplicationErrorHandler
    {
        private readonly ILogger<ApplicationErrorHandler> _logger;
        
        private readonly ApplicationErrorHandlerOptions _options;

        public ApplicationErrorHandler(ILogger<ApplicationErrorHandler> logger, IOptions<ApplicationErrorHandlerOptions> options) 
        { 
            _logger = logger;
            _options = options.Value;
        }

        public ObjectResult HandleInvalidModelState(HttpContext httpContext, ModelStateDictionary modelStateDictionary)
        {
            _logger.TraceMethodEntry();

            var details = new ValidationProblemDetails(modelStateDictionary)
            {
                Title = "Validation Failed",
                Type = "ValidationError",
                Status = (int)HttpStatusCode.BadRequest,
                Instance = httpContext.Request.Path,
            };

            details.Extensions.Add("error-code", ErrorCodes.ValidationFailed);
            details.Extensions.Add("trace-id", httpContext.TraceIdentifier);

            return new ObjectResult(details)
            {
                ContentTypes = { "application/problem+json" },
                StatusCode = (int)HttpStatusCode.BadRequest,
            };
        }

        public ObjectResult HandleException(HttpContext httpContext, Exception exception)
        {
            _logger.TraceMethodEntry();

            _logger.LogError(exception, "Call to '{RequestPath}' failed due to an Exception", httpContext.Request.Path);

            return exception switch
            {
                AuthenticationFailedException e => HandleAuthenticationException(httpContext, e),
                EntityConcurrencyException e => HandleEntityConcurrencyException(httpContext, e),
                EntityNotFoundException e => HandleEntityNotFoundException(httpContext, e),
                EntityUnauthorizedAccessException e => HandleEntityUnauthorizedException(httpContext, e),
                Exception e => HandleSystemException(httpContext, e),
            };
         }

        private ObjectResult HandleAuthenticationException(HttpContext httpContext, AuthenticationFailedException e)
        {
            _logger.TraceMethodEntry();

            var details = new ProblemDetails
            {
                Title = e.ErrorMessage,
                Type = nameof(AuthenticationFailedException),
                Status = (int)HttpStatusCode.Unauthorized,
                Instance = httpContext.Request.Path,
            };

            details.Extensions.Add("error-code", ErrorCodes.AuthenticationFailed);
            details.Extensions.Add("trace-id", httpContext.TraceIdentifier);

            AddExceptionDetails(details, e);

            return new ObjectResult(details)
            {
                ContentTypes = { "application/problem+json" },
                StatusCode = (int)HttpStatusCode.Unauthorized,
            };
        }
        
        // ...

        private ObjectResult HandleSystemException(HttpContext httpContext, Exception e)
        {
            _logger.TraceMethodEntry();

            var details = new ProblemDetails
            {
                Title = "An Internal Server Error occured",
                Status = (int)HttpStatusCode.InternalServerError,
                Instance = httpContext.Request.Path,
            };

            details.Extensions.Add("error-code", ErrorCodes.InternalServerError);
            details.Extensions.Add("trace-id", httpContext.TraceIdentifier);

            AddExceptionDetails(details, e);

            return new ObjectResult(details)
            {
                ContentTypes = { "application/problem+json" },
                StatusCode = (int)HttpStatusCode.InternalServerError,
            };
        }

        private void AddExceptionDetails(ProblemDetails details, Exception e)
        {
            _logger.TraceMethodEntry();

            if(_options.IncludeExceptionDetails)
            {
                details.Extensions.Add("exception", e.ToString());
            }
        }
    }
}
```

"You could have used a `ProblemDetailsFactory`, `Exception Handler Lambdas`!" I hear you say. ASP.NET Core comes with a 
`ProblemDetailsFactory`, `Exception Handler Lambdas`, `ErrorHandlerMiddleware`, `IExceptionHandler`, a `ProblemDetailsService` 
and whatnot... I don't understand, what's the best approach and I don't want to deal with it.

In the Controllers we then pass the `ApplicationErrorHandler` to the Constructor and can use it to handle an invalid `ModelState` 
and handle any `Exception`, that's being thrown.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    [Route("UserTasks")]
    public class UserTasksController : ControllerBase
    {
        private readonly ILogger<UserTasksController> _logger;
        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public UserTasksController(ILogger<UserTasksController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [HttpPut]
        [Route("{id}")]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> PutUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromBody] UserTask userTask, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                await userTaskService.UpdateUserTaskAsync(context, userTask, User.GetUserId(), cancellationToken);

                return Ok(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
        
        // ...
    }
}
```

And that's it for the Error Handling.

#### Integration Tests with EntityFramework Core and a Database ####

Generations of Software developers have learnt, that tests are important. And if you follow a Test-Driven Development approach 
you are probably trying to write as much Unit Tests as possible. As a yound developer I fell into a trap, thinking everything 
needs an `interface` and everything needs to be mocked.

These days I think what really matters are Integration Tests. Is the data I am writing *actually written to the real database*? Did 
EntityFramework Core translate the `IQueryable` *correctly*? Did it map the results correctly back and forth between the SQL function 
and the application?

I think the easiest way to write Integration Tests with EntityFramework Core is to use something like the `TransactionalTestBase` from 
below. The idea is to start the Transaction in the setup for a test and to dispose it in the teardown, without a commit. 

This leaves your database in a consistent state, with all changes being rolled back at the end of each test. 

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
            // Create a fresh DbContext for each test, because you don't want the 
            // Change Tracker to cache entities and pollute the test.
            _applicationDbContext = GetApplicationDbContext(_configuration);

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
            await _applicationDbContext.DisposeAsync();
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

### Database Access with Entity Framework Core ###

The Go-To Data Access Framework for .NET is EntityFramework Core. There are strong opinions on EntityFramework Core and 
OR-Mappers in general, I will keep mine to myself and use EntityFramework Core in this example. So here is what the 
`DbContext` for the application looks like. I am calling it an `ApplicationDbContext`.

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

        /// <summary>
        /// Gets or sets the Users.
        /// </summary>
        public DbSet<User> Users { get; set; } = null!;

        /// <summary>
        /// Gets or sets the Roles.
        /// </summary>
        public DbSet<Role> Roles { get; set; } = null!;

        /// <summary>
        /// Gets or sets the UserTasks.
        /// </summary>
        public DbSet<UserTask> UserTasks { get; set; } = null!;

        /// <summary>
        /// Gets or sets the UserTasks.
        /// </summary>
        public DbSet<Team> Teams { get; set; } = null!;

        /// <summary>
        /// Gets or sets the UserTasks.
        /// </summary>
        public DbSet<Organization> Organizations { get; set; } = null!;

        /// <summary>
        /// Gets or sets the UserTasks.
        /// </summary>
        public DbSet<RelationTuple> RelationTuples { get; set; } = null!;

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

            // Map the Sequences and Tables here ...
        }
    }
}
```

We will register the `ApplicationDbContext` in the `Program.cs` using the `AddDbContext<TDbContext>` extension:

```sql
// Database
builder.Services.AddDbContext<ApplicationDbContext>(options =>
{
    var connectionString = builder.Configuration.GetConnectionString("ApplicationDatabase");

    if (connectionString == null)
    {
        throw new InvalidOperationException("No ConnectionString named 'ApplicationDatabase' was found");
    }

    options
        .EnableSensitiveDataLogging().UseSqlServer(connectionString);
});
```

### Authentication using ASP.NET Core Cookie Authentication ###

We start by creating a `UserService`, which is used to create the Claims for given credentials. All passwords in the database 
are hashed using a `PasswordHasher`. The `PasswordHasher` is a one to one adaption of the ASP.NET Core Identity package.

As you can see in the `UserService`, I am passing the `ApplicationDbContext` as a method parameter. Ugly signatures! But the 
reasoning for it is simple: I want all my services to register as a Singleton. I don't want to materialize the EntityFramework 
Core `DbContext` out of thin air, like so many tutorials suggest you to do.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Services
{
    public class UserService : IUserService
    {
        private readonly ILogger<UserService> _logger;
        private readonly IPasswordHasher _passwordHasher;

        public UserService(ILogger<UserService> logger, IPasswordHasher passwordHasher)
        {
            _logger = logger;
            _passwordHasher = passwordHasher;
        }

        public async Task<List<Claim>> GetClaimsAsync(ApplicationDbContext context, string username, string password, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var user = await context.Users
                .AsNoTracking()
                .FirstOrDefaultAsync(x => x.LogonName == username, cancellationToken);

            if(user == null)
            {
                throw new AuthenticationFailedException();
            }

            if (!user.IsPermittedToLogon)
            {
                throw new AuthenticationFailedException();
            }

            // Verify hashed password in database against the provided password
            var isVerifiedPassword = _passwordHasher.VerifyHashedPassword(user.HashedPassword, password);

            if (!isVerifiedPassword)
            {
                throw new AuthenticationFailedException();
            }

            // Load the Roles from the List of Objects
            var roles = await context
                .ListUserObjects<Role>(user.Id, Relations.Member)
                .AsNoTracking()
                .ToListAsync(cancellationToken);

            // Build the Claims for the ClaimsPrincipal
            var claims = CreateClaims(user, roles);

            return claims;
        }

        private List<Claim> CreateClaims(User user, List<Role> roles)
        {
            _logger.TraceMethodEntry();

            var claims = new List<Claim>();

            if (user.LogonName != null)
            {
                claims.Add(new Claim(ClaimTypes.NameIdentifier, user.LogonName));
                claims.Add(new Claim(ClaimTypes.Email, user.LogonName));
            }

            // Default Claims:
            claims.Add(new Claim(ClaimTypes.Sid, Convert.ToString(user.Id)));
            claims.Add(new Claim(ClaimTypes.Name, Convert.ToString(user.PreferredName)));

            // Roles:
            foreach (var role in roles)
            {
                claims.Add(new Claim(ClaimTypes.Role, role.Name));
            }

            return claims;
        }
    }
}
```

There are many options to authenticate a user, a popular one is using JSON Web Tokens and have it stateless. For our Backend 
a Cookie Authentication is simple and totally sufficient, we own both the Server and Clients. But you might want to consider 
using Windows Authentication or moving that pesky authentication to an external provider, if you don't want to deal with it 
yourself.

We need to configure the Cookie Authentication in the `Program.cs`:

```csharp
// Cookie Authentication
builder.Services
    .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.Cookie.HttpOnly = true;
        options.Cookie.SameSite = SameSiteMode.Lax; // We don't want to deal with CSRF Tokens

        options.Events.OnRedirectToAccessDenied = (context) =>
        {
            context.Response.StatusCode = StatusCodes.Status403Forbidden;

            return Task.CompletedTask;
        };

        options.Events.OnRedirectToLogin = (context) =>
        {
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;

            return Task.CompletedTask;
        };
    });
```

And we can then write a Controller `AuthenticationController`, that exposes a `sign-in` and `sign-out` method 
to authenticate a user against our database.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using RebacExperiments.Server.Api.Dto;
using RebacExperiments.Server.Api.Infrastructure.Database;
using RebacExperiments.Server.Api.Infrastructure.Errors;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Services;
using System.Security.Claims;

namespace RebacExperiments.Server.Api.Controllers
{
    [Route("Authentication")]
    public class AuthenticationController : ControllerBase
    {
        private readonly ILogger<AuthenticationController> _logger;

        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public AuthenticationController(ILogger<AuthenticationController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [HttpPost]
        [Route("sign-in")]
        public async Task<IActionResult> SignInUser([FromServices] ApplicationDbContext context, [FromServices] IUserService userService, [FromBody] CredentialsDto credentials, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                // Create ClaimsPrincipal from Database 
                var userClaims = await userService.GetClaimsAsync(
                    context: context,
                    username: credentials.Username,
                    password: credentials.Password,
                    cancellationToken: cancellationToken);

                // Create the ClaimsPrincipal
                var claimsIdentity = new ClaimsIdentity(userClaims, CookieAuthenticationDefaults.AuthenticationScheme);
                var claimsPrincipal = new ClaimsPrincipal(claimsIdentity);

                // It's a valid ClaimsPrincipal, sign in
                await HttpContext.SignInAsync(claimsPrincipal, new AuthenticationProperties { IsPersistent = credentials.RememberMe });

                return Ok();
            } 
            catch (Exception ex)
            {
                _logger.LogError(ex, "{ControllerAction} failed due to an Exception", nameof(SignInUser));

                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpPost]
        [Route("sign-out")]
        public async Task<IActionResult> SignOutUser()
        {
            _logger.TraceMethodEntry();

            try
            {
                await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            } 
            catch(Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }

            return Ok();
        }
    }
}
```

### Implementing the Relationship-based Access Control Code ###

#### CheckObject API ####

The function `[Identity].[udf_RelationTuples_Check]` checks, if a *Subject* (our `User`) is authorized to access an *Object* (our `UserTask`). 

The easiest way to execute the `[Identity].[udf_RelationTuples_Check]` function was using the new `DbContext#SqlQuery(...)` method and 
to just do a `[Identity].[udf_RelationTuples_Check](...)` SQL Query. We add the call in a static class `ApplicationDbContextExtensions` as 
extensions methods.

```
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Infrastructure.Database
{
    /// <summary>
    /// Extensions on the <see cref="ApplicationDbContext"/> to allow Relationship-based ACL.
    /// </summary>
    public static class ApplicationDbContextExtensions
    {
        /// <summary>
        /// Checks if a <typeparamref name="TSubjectType"/> is authorized to access an <typeparamref name="TObjectType"/>. 
        /// </summary>
        /// <typeparam name="TObjectType">Object Type</typeparam>
        /// <typeparam name="TSubjectType">Subject Type</typeparam>
        /// <param name="context">DbContext</param>
        /// <param name="objectId">Object Key</param>
        /// <param name="relation">Relation</param>
        /// <param name="subjectId">SubjectKey</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns><see cref="true"/>, if the <typeparamref name="TSubjectType"/> is authorized; else <see cref="false"/></returns>
        public static async Task<bool> CheckObject<TObjectType, TSubjectType>(this ApplicationDbContext context, int objectId, string relation, int subjectId, CancellationToken cancellationToken)
            where TObjectType : Entity
            where TSubjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            var result = await context.Database
                .SqlQuery<bool>($"SELECT [Identity].[udf_RelationTuples_Check]({typeof(TObjectType).Name}, {objectId}, {relation}, {typeof(TSubjectType).Name}, {subjectId})")
                .ToListAsync(cancellationToken);

            return result.First();
        }

        /// <summary>
        /// Checks if a <see cref="User"/> is authorized to access an <typeparamref name="TObjectType"/>. 
        /// </summary>
        /// <typeparam name="TObjectType">Object Type</typeparam>
        /// <param name="context">DbContext</param>
        /// <param name="objectId">Object Key</param>
        /// <param name="relation">Relation</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns><see cref="true"/>, if the <typeparamref name="TSubjectType"/> is authorized; else <see cref="false"/></returns>
        public static Task<bool> CheckUserObject<TObjectType>(this ApplicationDbContext context, int userId, int objectId, string relation, CancellationToken cancellationToken)
            where TObjectType : Entity
        {
            context.Logger.TraceMethodEntry();

            return CheckObject<TObjectType, User>(context, objectId, relation, userId, cancellationToken);
        }

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
    }
}
```

#### Integration Tests for the CheckObject API ####

What's left is to write some tests for the `CheckUserObjects<TObjectType>` methods. We follow the classic 
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
    public class CheckUserObjectTests : TransactionalTestBase
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
        public async Task CheckUserObject_OneUserTaskAssignedThroughOrganizationAndTeam()
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
            var isOwnerOfTask = await _applicationDbContext.CheckUserObject(user.Id, task, Relations.Owner, default);
            var isViewerOfTask = await _applicationDbContext.CheckUserObject(user.Id, task, Relations.Viewer, default);

            // Assert
            Assert.AreEqual(true, isOwnerOfTask);
            Assert.AreEqual(true, isViewerOfTask);
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
        public async Task CheckUserObject_TwoUserTasksAssignedToUser()
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
            var isOwnerOfTask1 = await _applicationDbContext.CheckUserObject(user.Id, task1, Relations.Owner, default);
            var isViewerOfTask1 = await _applicationDbContext.CheckUserObject(user.Id, task1, Relations.Viewer, default);
            
            var isOwnerOfTask2 = await _applicationDbContext.CheckUserObject(user.Id, task2, Relations.Owner, default);
            var isViewerOfTask2 = await _applicationDbContext.CheckUserObject(user.Id, task2, Relations.Viewer, default);

            // Assert
            Assert.AreEqual(false, isOwnerOfTask1);
            Assert.AreEqual(true, isViewerOfTask1);  
            
            Assert.AreEqual(true, isOwnerOfTask2);
            Assert.AreEqual(false, isViewerOfTask2);           
        }
    }
}
```

#### ListObjects API ####

For listing the authorized objects for a user we have mapped the `[Identity].[tvf_RelationTuples_ListObjects]` in the `DbContext`, 
this can be done using the `ModelBuilder#HasDbFunction(...)` method and tie it to a method `ApplicationDbContext#ListObjects`. The 
method signature should map to the Table-Value Function.

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

As of now the `ListObjects` expects us to pass `string` values and an `integer` for the subject key. 

We want to simplify this and I want to have a nice API like this:

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

We don't put these methods directly into the `ApplicationDbContext`, but define them as Extension methods in a static class we call `ApplicationDbContextExtensions`.

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

#### Using Relationship-based Access Control in the Application Services ####

Now let's use the `ListObjects` and `CheckObject` API to provide `UserTask`. With the extension methods 
in place it's really easy to understand what's going on. We basically pass the `ApplicationDbContext` to 
the Create, Read, Update and Delete methods to check for permissions and list the objects for a user.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using RebacExperiments.Server.Api.Infrastructure.Constants;
using RebacExperiments.Server.Api.Infrastructure.Database;
using RebacExperiments.Server.Api.Infrastructure.Exceptions;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Models;

namespace RebacExperiments.Server.Api.Services
{
    public class UserTaskService : IUserTaskService
    {
        private readonly ILogger<UserTaskService> _logger;

        public UserTaskService(ILogger<UserTaskService> logger)
        {
            _logger = logger;
        }

        public async Task<UserTask> CreateUserTaskAsync(ApplicationDbContext context, UserTask userTask, int currentUserId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            using (var transaction = await context.Database.BeginTransactionAsync(cancellationToken))
            {
                // Make sure the Current User is the last editor:
                userTask.LastEditedBy = currentUserId;

                // Add the new Task, the HiLo Pattern automatically assigns a new Id using the HiLo Pattern
                await context.AddAsync(userTask, cancellationToken);

                // The User is Viewer and Owner of the Task
                await context.AddRelationshipAsync<UserTask, User>(userTask.Id, Relations.Viewer, currentUserId, null, currentUserId, cancellationToken);
                await context.AddRelationshipAsync<UserTask, User>(userTask.Id, Relations.Owner, currentUserId, null, currentUserId, cancellationToken);

                // We want the created task to be visible by all members of the organization the user is in
                var organizations = await context
                    .ListUserObjects<Organization>(currentUserId, Relations.Member)
                    .AsNoTracking()
                    .ToListAsync(cancellationToken);

                foreach (var organization in organizations)
                {
                    await context.AddRelationshipAsync<UserTask, Organization>(userTask.Id, Relations.Viewer, organization.Id, Relations.Member, currentUserId, cancellationToken);
                }

                await context.SaveChangesAsync(cancellationToken);

                await transaction.CommitAsync(cancellationToken);
            }

            return userTask;
        }

        public async Task<UserTask> GetUserTaskByIdAsync(ApplicationDbContext context, int userTaskId, int currentUserId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var userTask = await context.UserTasks
                .AsNoTracking()
                .FirstOrDefaultAsync(x => x.Id == userTaskId, cancellationToken);

            if(userTask == null)
            {
                throw new EntityNotFoundException() 
                {
                    EntityName = nameof(UserTask),
                    EntityId = userTaskId,
                };
            }

            bool isAuthorized = await context.CheckUserObject(currentUserId, userTask, Relations.Viewer, cancellationToken);

            if(!isAuthorized)
            {
                throw new EntityUnauthorizedAccessException()
                {
                    EntityName = nameof(UserTask),
                    EntityId = userTaskId,
                    UserId = currentUserId,
                };
            }

            return userTask;
        }

        public async Task<List<UserTask>> GetUserTasksAsync(ApplicationDbContext context, int currentUserId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            var userTasks = context
                .ListUserObjects<UserTask>(currentUserId, new[] { Relations.Viewer, Relations.Owner })
                .ToListAsync(cancellationToken);

            return await userTasks;
        }

        public async Task<UserTask> UpdateUserTaskAsync(ApplicationDbContext context, UserTask userTask, int currentUserId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            bool isAuthorized = await context.CheckUserObject(currentUserId, userTask, Relations.Owner, cancellationToken);

            if (!isAuthorized)
            {
                throw new EntityUnauthorizedAccessException()
                {
                    EntityName = nameof(UserTask),
                    EntityId = userTask.Id,
                    UserId = currentUserId,
                };
            }

            int rowsAffected = await context.UserTasks
                .Where(t => t.Id == userTask.Id && t.RowVersion == userTask.RowVersion)
                .ExecuteUpdateAsync(setters => setters
                    .SetProperty(x => x.Title, userTask.Title)
                    .SetProperty(x => x.Description, userTask.Description)
                    .SetProperty(x => x.DueDateTime, userTask.DueDateTime)
                    .SetProperty(x => x.CompletedDateTime, userTask.CompletedDateTime)
                    .SetProperty(x => x.ReminderDateTime, userTask.ReminderDateTime)
                    .SetProperty(x => x.AssignedTo, userTask.AssignedTo)
                    .SetProperty(x => x.UserTaskPriority, userTask.UserTaskPriority)
                    .SetProperty(x => x.UserTaskStatus, userTask.UserTaskStatus)
                    .SetProperty(x => x.LastEditedBy, currentUserId), cancellationToken);

            if(rowsAffected == 0)
            {
                throw new EntityConcurrencyException()
                {
                    EntityName = nameof(UserTask),
                    EntityId = userTask.Id,
                };
            }

            return userTask;
        }

        public async Task DeleteUserTaskAsync(ApplicationDbContext context, int userTaskId, int currentUserId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            bool isAuthorized = await context.CheckUserObject<UserTask>(currentUserId, userTaskId, Relations.Owner, cancellationToken);

            if (!isAuthorized)
            {
                throw new EntityUnauthorizedAccessException()
                {
                    EntityName = nameof(UserTask),
                    EntityId = userTaskId,
                    UserId = currentUserId,
                };
            }

            using (var transaction = await context.Database.BeginTransactionAsync(cancellationToken))
            {
                var userTask = await context.UserTasks
                    .AsNoTracking()
                    .FirstOrDefaultAsync(x => x.Id == userTaskId);

                if (userTask == null)
                {
                    throw new EntityNotFoundException()
                    {
                        EntityName = nameof(UserTask),
                        EntityId = userTaskId,
                    };
                }

                // Start by deleting all Relationships, where UserTask is the Object ...
                {
                    int numRowsDeleted = await context
                        .RelationTuples.Where(x => x.ObjectNamespace == nameof(UserTask) && x.ObjectKey == userTask.Id)
                        .ExecuteDeleteAsync(cancellationToken);

                    if (_logger.IsDebugEnabled())
                    {
                        _logger.LogDebug("'{NumRowsDeleted}' Relations deleted for Object UserTask (Id = {UserTaskId})", numRowsDeleted, userTaskId);
                    }
                }

                // ... then delete all Relationships, where UserTask is the Subject ...
                {
                    int numRowsDeleted = await context
                        .RelationTuples.Where(x => x.SubjectNamespace == nameof(UserTask) && x.SubjectKey == userTask.Id)
                        .ExecuteDeleteAsync(cancellationToken);

                    if (_logger.IsDebugEnabled())
                    {
                        _logger.LogDebug("'{NumRowsDeleted}' Relations deleted for Subject UserTask (Id = {UserTaskId})", numRowsDeleted, userTaskId);
                    }
                }

                // After removing all possible references, delete the UserTask itself
                int rowsAffected = await context.UserTasks
                    .Where(t => t.Id == userTask.Id)
                    .ExecuteDeleteAsync(cancellationToken);

                // No Idea if this could happen, because we are in a Transaction and there
                // is a row, which should be locked. So this shouldn't happen at all...
                if (rowsAffected == 0)
                {
                    throw new EntityConcurrencyException()
                    {
                        EntityName = nameof(UserTask),
                        EntityId = userTaskId,
                    };
                }

                await transaction.CommitAsync(cancellationToken);
            }
        }
    }
}
```

The `UserService` is then passed into the Controller methods (using the `[FromServices]` attribute). As you can 
see, we apply the Role-based Access Control on an endpoint level using the `[Authorize]` attribute combined with 
a policy. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    [Route("UserTasks")]
    public class UserTasksController : ControllerBase
    {
        private readonly ILogger<UserTasksController> _logger;
        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public UserTasksController(ILogger<UserTasksController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [HttpGet]
        [Route("{id}")]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> GetUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromRoute(Name = "id")] int userTaskId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                var userTask = await userTaskService.GetUserTaskByIdAsync(context, userTaskId, User.GetUserId(), cancellationToken);

                return Ok(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpGet]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> GetUserTasks([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                var userTasks = await userTaskService.GetUserTasksAsync(context, User.GetUserId(), cancellationToken);

                return Ok(userTasks);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpPost]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> PostUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromBody] UserTask userTask, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                await userTaskService.CreateUserTaskAsync(context, userTask, User.GetUserId(), cancellationToken);

                return Ok(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpPut]
        [Route("{id}")]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> PutUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromBody] UserTask userTask, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                await userTaskService.UpdateUserTaskAsync(context, userTask, User.GetUserId(), cancellationToken);

                return Ok(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpDelete]
        [Route("{id}")]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> DeleteUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromRoute(Name = "id")] int userTaskId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                await userTaskService.DeleteUserTaskAsync(context, userTaskId, User.GetUserId(), cancellationToken);

                return Ok();
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
    }
}
```

The Policies have been defined in the `Program.cs` as ...

```csharp
// Add Policies
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy(Policies.RequireUserRole, policy => policy.RequireRole(Roles.User));
    options.AddPolicy(Policies.RequireAdminRole, policy => policy.RequireRole(Roles.Administrator));
});

```

## Running an Example with the Sample Data ##

We got everything in place. We can now start the application and use Swagger to query it. But Visual Studio 2022 
has now comes with the "Endpoints Explorer" to execute HTTP Requests against HTTP endpoints. Though it's not 
fully-fledged yet, I think it'll improve with time and it already covers a lot of use cases.

You can find the Endpoints Explorer at:

* `View -> Other Windows -> Endpoints Explorer`

The Endpoints Explorer for our API looks like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac/visual_studio_endpoints_explorer.jpg">
        <img src="/static/images/blog/aspnetcore_rebac/visual_studio_endpoints_explorer.jpg" alt="Endpoints Explorer for the Task Management API">
    </a>
</div>

By clicking on `RebacExperiments.Server.Api.http` the HTTP script with the sample requests comes up.

### The Example Setup ###

We have got 2 Tasks:

* `task_152`: "Sign Document"
* `task 323`: "Call Back Philipp Wagner"

And we have got two users: 

* `user_philipp`: "Philipp Wagner"
* `user_max`: "Max Mustermann"

Both users are permitted to login, so they are allowed to query for data, given a permitted role and permissions.

There are two Organizations:

* Organization 1: "Organization #1"
* Organization 2: "Organization #2"

And 2 Roles:

* `role_user`: "User" (Allowed to Query for UserTasks)
* `role_admin`: "Administrator" (Allowed to Delete a UserTask)

The Relationships between the entities are the following:

```
The Relationship-Table is given below.

ObjectKey           |  ObjectNamespace  |   ObjectRelation  |   SubjectKey          |   SubjectNamespace    |   SubjectRelation
--------------------|-------------------|-------------------|-----------------------|-----------------------|-------------------
:task_323  :        |   UserTask        |       viewer      |   :organization_1:    |       Organization    |   member
:task_152  :        |   UserTask        |       viewer      |   :organization_1:    |       Organization    |   member
:task_152  :        |   UserTask        |       viewer      |   :organization_2:    |       Organization    |   member
:organization_1:    |   Organization    |       member      |   :user_philipp:      |       User            |   NULL
:organization_2:    |   Organization    |       member      |   :user_max:          |       User            |   NULL
:role_user:         |   Role            |       member      |   :user_philipp:      |       User            |   NULL
:role_admin:        |   Role            |       member      |   :user_philipp:      |       User            |   NULL
:role_user:         |   Role            |       member      |   :user_max:          |       User            |   NULL
:task_323:          |   UserTask        |       owner       |   :user_2:            |       User            |   member
```

We can draw the following conclusions here: A `member` of `organization_1` is `viewer` of `task_152` and `task_323`. A `member` 
of `organization_2` is a `viewer` of `task_152` only. `user_philipp` is member of `organization_1`, so the user is able to see 
both tasks as `viewer`. `user_max` is member of `organization_2`, so he is a `viewer` of `task_152` only. `user_philipp` has the 
`User` and `Administrator` roles assigned, so he can create, query and delete a `UserTask`. `user_max` only has the `User` role 
assigned, so he is not authorized to delete a `UserTask`. Finally `user_philipp` is also the `owner` of `task_323` so he is 
permitted to update the data of the `UserTask`.

### HTTP Endpoints Explorer Script ###

We start by signing in `philipp@bytefish.de`:

```
### Sign In "philipp@bytefish.de"

POST {{RebacExperiments.Server.Api_HostAddress}}/Authentication/sign-in
Content-Type: application/json

{
  "username": "philipp@bytefish.de",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

And then get all Tasks by querying `/UserTasks` endpoint:

```
### Get all UserTasks

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
```

As expected by the example setup, we task `152` and `323`:

```
[
  {
    "title": "Call Back",
    "description": "Call Back Philipp Wagner",
    "dueDateTime": null,
    "reminderDateTime": null,
    "completedDateTime": null,
    "assignedTo": null,
    "userTaskPriority": 1,
    "userTaskStatus": 1,
    "id": 152,
    "rowVersion": "AAAAAAAAB\u002Bw=",
    "lastEditedBy": 1,
    "validFrom": "2013-01-01T00:00:00",
    "validTo": "9999-12-31T23:59:59.9999999"
  },
  {
    "title": "Sign Document",
    "description": "You need to Sign a Document",
    "dueDateTime": null,
    "reminderDateTime": null,
    "completedDateTime": null,
    "assignedTo": null,
    "userTaskPriority": 2,
    "userTaskStatus": 2,
    "id": 323,
    "rowVersion": "AAAAAAAAB\u002B0=",
    "lastEditedBy": 1,
    "validFrom": "2013-01-01T00:00:00",
    "validTo": "9999-12-31T23:59:59.9999999"
  }
]
```

We sign out `philipp@bytefish.de`:

```
### Sign Out "philipp@bytefish.de"

POST {{RebacExperiments.Server.Api_HostAddress}}/Authentication/sign-out
```

And trying to query the `/UserTasks`: 

```
### Check for 401 Unauthorized when not Authenticated

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
```

Returns a `401` Status Code:

```
Status: 401 UnauthorizedTime: 7,48 msSize: 0 bytes
```

Next sign in `max@mustermann.local`:

```
### Sign In as "max@mustermann.local"

POST {{RebacExperiments.Server.Api_HostAddress}}/Authentication/sign-in
Content-Type: application/json

{
  "username": "max@mustermann.local",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

And querying the `/UserTasks` endpoint:

```
### Get all UserTasks for "max@mustermann.local"

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
```

Returns only `UserTask` with ID `152` as expected:

```
[
  {
    "title": "Call Back",
    "description": "Call Back Philipp Wagner",
    "dueDateTime": null,
    "reminderDateTime": null,
    "completedDateTime": null,
    "assignedTo": null,
    "userTaskPriority": 1,
    "userTaskStatus": 1,
    "id": 152,
    "rowVersion": "AAAAAAAAB\u002Bw=",
    "lastEditedBy": 1,
    "validFrom": "2013-01-01T00:00:00",
    "validTo": "9999-12-31T23:59:59.9999999"
  }
]
```

We are not the Owner of the Task, so let's try to delete the task:

```
### Delete UserTask 152 as "max@mustermann.local" (he is not the owner)
DELETE {{RebacExperiments.Server.Api_HostAddress}}/UserTasks/152
```

And as expected, we are not permitted to delete the task:

```
Status: 403 ForbiddenTime: 190,91 msSize: 1154 bytes

application/problem+json; charset=utf-8, 1154 bytes

{
  "type": "EntityUnauthorizedAccessException",
  "title": "EntityUnauthorizedAccess (User = 7, Entity = UserTask, EntityID = 152)",
  "status": 403,
  "instance": "/UserTasks/152",
  "error-code": "Entity:000002",
  "trace-id": "0HMUJJ9QPSEE0:00000001",
  "exception": "RebacExperiments.Server.Api.Infrastructure.Exceptions.EntityUnauthorizedAccessException: Exception of type \u0027RebacExperiments.Server.Api.Infrastructure.Exceptions.EntityUnauthorizedAccessException\u0027 was thrown.\r\n   at RebacExperiments.Server.Api.Services.UserTaskService.DeleteUserTaskAsync(ApplicationDbContext context, Int32 userTaskId, Int32 currentUserId, CancellationToken cancellationToken) in C:\\Users\\philipp\\source\\repos\\bytefish\\RebacExperiments\\RebacExperiments\\RebacExperiments.Server.Api\\Services\\UserTaskService.cs:line 148\r\n   at RebacExperiments.Server.Api.Controllers.UserTasksController.DeleteUserTask(ApplicationDbContext context, IUserTaskService userTaskService, Int32 userTaskId, CancellationToken cancellationToken) in C:\\Users\\philipp\\source\\repos\\bytefish\\RebacExperiments\\RebacExperiments\\RebacExperiments.Server.Api\\Controllers\\UserTasksController.cs:line 141"
}
```

The `max@mustermann.local` is allowed to create a `UserTask`. We have seen, that the person creating 
a `UserTask` is automatically the `owner` of the task and the users entire organization can view it.

```
### Create a new UserTask "API HTTP File Example" as "max@mustermann.local"

POST {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
Content-Type: application/json

{
    "title": "API HTTP File Example",
    "description": "API HTTP File Example",
    "dueDateTime": null,
    "reminderDateTime": null,
    "completedDateTime": null,
    "assignedTo": null,
    "userTaskPriority": 2,
    "userTaskStatus": 2
}
```

And we get a successful response with the created task as the response payload:

```
Status: 200 OKTime: 264,41 msSize: 335 bytes

{
  "title": "API HTTP File Example",
  "description": "API HTTP File Example",
  "dueDateTime": null,
  "reminderDateTime": null,
  "completedDateTime": null,
  "assignedTo": null,
  "userTaskPriority": 2,
  "userTaskStatus": 2,
  "id": 38188,
  "rowVersion": "AAAAAAAAB/k=",
  "lastEditedBy": 7,
  "validFrom": "2023-10-23T08:02:41.8051703",
  "validTo": "9999-12-31T23:59:59.9999999"
}
```

If we now sign-in "philipp@bytefish.de":

```

### Sign In "philipp@bytefish.de"

POST {{RebacExperiments.Server.Api_HostAddress}}/Authentication/sign-in
Content-Type: application/json

{
  "username": "philipp@bytefish.de",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

And query for the `UserTasks`:

```
### Get all UserTasks for "philipp@bytefish.de"

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
```

We cannot see the "API HTTP File Example" Task created by the other user, because 
`philipp@bytefish.de` isn't part of the Organization and has no relationship to the 
task.

And this is where our example ends. Feel free to play around with the example as much as you like.

## Conclusion ##

And we come to an end here. There are more things to explore in the code, like Rate Limiting!

I didn't want to write such a long post initially and at times it it went off-topic. But I think it's 
important for the .NET community to give "different ways" of building applications. You don't need to have 
complex architectures, you don't need a lot of code.

I have used this article to showcase several things.

First of all we have learnt how to design a database project. We have decided on a project structure and naming 
conventions to use for database objects. It's important to have a consistent approach, because your application 
will die, but the data (and your database) lives forever.

Then we have taken a look at Logging with ASP.NET Core and have learnt how to add Serilog. Serilog has a 
wide range of useful Logging Sinks, the example used a File Appender and a Console Logger. If you want to 
get fancy you could also learn about Structured Logging and Open Telemetry.

EntityFramework Core made it easy to access the data. In this article we opted to map the database 
manually, but the *EntityFramework Core Power Tools* Extension generates the same code with the 
press of a button.

We came up with a very nice API for providing Relationship-based Access Control using Extension methods on the 
EntityFramework Core `DbContext`, and also provided a Role-based Access Control on top. Both have been used in 
the ASP.NET Core Controllers and the Services.

By using the new Visual Studio 2022 Endpoints Explorer, we have create a `.http` file and have been able to 
play around with the data and see how everything works out in practice.