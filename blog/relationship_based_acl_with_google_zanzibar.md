title: Exploring Relationship-based Access Control (ReBAC) with Google Zanzibar
date: 2023-06-17 08:40
tags: sql, tsql, authorization, identity
category: sql
slug: relationship_based_acl_with_google_zanzibar
author: Philipp Wagner
summary: This article explores Relationship-based Access Control (ReBAC) with Google Zanzibar

I have recently read about a paper on Google Zanzibar, which is Google's 
solution for providing authorization among its many services:

* [https://research.google/pubs/pub48190/](https://research.google/pubs/pub48190/)

In this article we will take a look at the data model of Google Zanzibar and play 
around with some data. It's not meant to be a production-ready implementation, but 
to show some SQL and play with ideas.

All code can be found in a GitHub repository at:

* [https://github.com/bytefish/AuthorizationExperiments](https://github.com/bytefish/AuthorizationExperiments)

## Table of contents ##

[TOC]

## What's the Problem ##

[ported the Microsoft WebApiAuthorization library]: https://www.bytefish.de/blog/aspnet_core_odata_authorization.html

Ever since learning about OData, I have wondered: How on earth can you limit the data a 
user has access to? I have even [ported the Microsoft WebApiAuthorization library] to 
the most recent ASP.NET OData 8, so Role-based permissions can be used for queries.

While I think Role-based Authorization can get you far, I don't think it's fine-grained 
enough for limiting what objects a user is authorized to see. Say a user is only allowed to 
see "their own data", then what is the role for "my data"?

Am I assigned to an organization and may see their data? Have I been assigned as a member 
of a team and am allowed to view the team files? Has someone shared a file with me? 

We need a flexible way to model these relationships.

Enter Google Zanzibar, which implements "Relationship-based Access Control". 

## What we are going to build ##

In this example we are going to take a look at the Google Zanzibar data model and see 
how to implement it in T-SQL. We will also implement two methods of the Google Zanzibar 
paper, for doing a check and to read objects. 

## Database Project Structure ##

[WideWorldImporters OLTP Database]: https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/wide-world-importers/wwi-ssdt/

Before starting a database application, a team should *agree* on structure and naming conventions. You'll need to 
have a consistent style from the start. Everyone has to know *where to put files* and *how to name things*.

The high level structure for our SQL Server Database Project uses the [WideWorldImporters OLTP Database] structure:

* `«Schema»`
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

So for the Task Management System we will have a Schema `[Application]` and `[Identity]`, so the layout looks like this:

* `Application`
    * `Indexes`
        * `UX_TaskPriority_Name.sql`
        * ...
    * `Sequences`
        * `sq_Task.sql`
    * `Stored Procedures`
        * `usp_Task_Create.sql`
        * ...
    * `Tables`
        * `Task.sql`
        * ...
    * `Application.sql`
* `Identity`
    * `Indexes`
        * ...
    * `Sequences`
        * ...
    * `Stored Procedures`
        * ...
    * `Tables`
        * ...
    * `Identity.sql`  
* `Scripts`
    * `Application`
        * `pds-100-ins-application-task-priority.sql`
        * ...
    * `Identity`
        * ...
    * `Script.PostDeployment1.sql`

## Getting Started with Google Zanzibar ##

There are many excellent sources, that explain Google Zanzibar in detail. I've basically consulted 
the following articles to get started:

* [Ege Aytin - Exploring Google Zanzibar: A Demonstration of Its Basics](https://www.permify.co/post/exploring-google-zanzibar-a-demonstration-of-its-basics)
* [Sam Scott - Building Zanzibar from Scratch](https://www.osohq.com/post/zanzibar)
* [Radek Gruchalski - Zanzibar-style ACLs with Prolog](https://gruchalski.com/posts/2022-09-03-zanzibar-style-acls-with-prolog/)

Google Zanzibar basically models relationships between `Objects` and `Subjects` using the following notation:

```
<object>#<relation>@<subject> 
```

This allows Google Zanzibar to model relationships between `an Object` and `Subject`. Say we 
have a system to manage tasks, then we could make up relations like this with the syntax given 
in the Zanzibar paper:

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
* `org2#member@hannes`
    * `alexander` is a `member` of `org1`

## Database Design ##

All Tables and Stored Procedures should go into a Schema `[Identity]`:

```sql
CREATE SCHEMA [Identity];
```

### User Table ###

Then we are creating the `[Identity].[User]` table:

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

And now we can insert the users we have referenced in our sample relationship tuples:

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
    ,(2, 'Philipp Wagner', 'Philipp Wagner', 0, NULL, NULL, 1, @ValidFrom, @ValidTo)
    ,(3, 'Hannes Wolf ', 'Hannes Wolf', 0, NULL, NULL, 1, @ValidFrom, @ValidTo)
    ,(4, 'Alexander Meier', 'Alex Meier', 0, NULL, NULL, 1, @ValidFrom, @ValidTo)
) AS [Source]([UserID], [FullName], [PreferredName], [IsPermittedToLogon], [LogonName], [HashedPassword], [LastEditedBy], [ValidFrom], [ValidTo])
ON ([Target].[UserID] = [Source].[UserID])
WHEN NOT MATCHED BY TARGET THEN
    INSERT 
        ([UserID], [FullName], [PreferredName], [IsPermittedToLogon], [LogonName], [HashedPassword], [LastEditedBy], [ValidFrom], [ValidTo])
    VALUES 
        ([Source].[UserID], [Source].[FullName], [Source].[PreferredName], [Source].[IsPermittedToLogon], [Source].[LogonName], [Source].[HashedPassword], [Source].[LastEditedBy], [Source].[ValidFrom], [Source].[ValidTo]);
```

#### Relationship Table ####

The relationship tuples go into the `[Identity].[RelationTuples]` table. 

And then we can define the database structure to model the relationship tuples. We basically need 
to have an Object, which consists of a `Namespace` and a `Key`. We need a `Subject`, which consists 
of a `Namespace` and a `Key`. The `Object` has a `Relation` to a `Subject`. The `Subject` itself 
can have can have a `Relation` to an `Object`, so we can model a hierarchy.

We end up with the following table: 

```sql
CREATE TABLE [Identity].[RelationTuple](
    [RelationTupleID]       INT                                         CONSTRAINT [DF_Identity_RelationTuple_RelationTupleID] DEFAULT (NEXT VALUE FOR [Identity].[sq_RelationTuple]) NOT NULL,
    [ObjectKey]             INT                                         NOT NULL,
    [ObjectNamespace]       NVARCHAR(50)                                NOT NULL,
    [ObjectRelation]        NVARCHAR(50)                                NOT NULL,
    [SubjectKey]            INT                                         NOT NULL,
    [SubjectNamespace]      NVARCHAR(50)                                NULL,
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

And we need to make sure, that we have unique relations, so we add a `UNIQUE` constraint:

```sql
CREATE UNIQUE INDEX [UX_RelationTuple_UniqueTuple] ON [Identity].[RelationTuple] 
(
     [ObjectKey]       
    ,[ObjectNamespace] 
    ,[ObjectRelation]  
    ,[SubjectKey]      
    ,[SubjectNamespace]
    ,[SubjectRelation] 
);
```

Now we can insert the relations for the sample data, which looked like this:

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
* `org2#member@hannes`
    * `alexander` is a `member` of `org1`

We can insert the relationships with the following Post-Deployment Script:

```sql
PRINT 'Inserting [Identity].[RelationTuple] ...'

-----------------------------------------------
-- Global Parameters
-----------------------------------------------
DECLARE @ValidFrom datetime2(7) = '20130101'
DECLARE @ValidTo datetime2(7) =  '99991231 23:59:59.9999999'

-----------------------------------------------
-- [Identity].[RelationTuple]
-----------------------------------------------
MERGE INTO [Identity].[RelationTuple] AS [Target]
USING (VALUES 
      (1, 'task', 323, 'owner', 'user',   2, NULL, 1, @ValidFrom, @ValidTo)
     ,(2, 'task', 323, 'viewer', 'org',   1, 'member', 1, @ValidFrom, @ValidTo)
     ,(3, 'task', 152, 'viewer', 'org',   2, 'member', 1, @ValidFrom, @ValidTo)
     ,(4, 'task', 152, 'viewer', 'org',   1, 'member', 1, @ValidFrom, @ValidTo)
     ,(5, 'org',  1,   'member', 'user',  2, NULL, 1, @ValidFrom, @ValidTo)
     ,(6, 'org',  1,   'member', 'user',  3, NULL, 1, @ValidFrom, @ValidTo)
     ,(7, 'org',  2,   'member', 'user',  4, NULL, 1, @ValidFrom, @ValidTo)
) AS [Source]
(
     [RelationTupleID] 
    ,[ObjectNamespace] 
    ,[ObjectKey]       
    ,[ObjectRelation]  
    ,[SubjectNamespace]
    ,[SubjectKey]      
    ,[SubjectRelation] 
    ,[LastEditedBy]    
    ,[ValidFrom]       
    ,[ValidTo]         
)
ON (
    [Target].[RelationTupleID] = [Source].[RelationTupleID]
)
WHEN NOT MATCHED BY TARGET THEN
    INSERT 
        (
             [RelationTupleID]
            ,[ObjectNamespace]
            ,[ObjectKey]
            ,[ObjectRelation]
            ,[SubjectNamespace]
            ,[SubjectKey]
            ,[SubjectRelation]
            ,[LastEditedBy]
            ,[ValidFrom]
            ,[ValidTo]
        )
    VALUES 
        (
             [Source].[RelationTupleID]
            ,[Source].[ObjectNamespace]
            ,[Source].[ObjectKey]
            ,[Source].[ObjectRelation]
            ,[Source].[SubjectNamespace]
            ,[Source].[SubjectKey]
            ,[Source].[SubjectRelation]
            ,[Source].[LastEditedBy]
            ,[Source].[ValidFrom]
            ,[Source].[ValidTo]
        );
```

### The Google Zanzibar Check API ###

We start with the Check API, which is used in Google Zanzibar to check, if a 
specific Subject (for example a `user` or `userset`) has a Relation to a 
specific object (for example a `task`).

I switch into the SQL Server Management Studio, which is a great way to play 
around with data and start by defining some variables:


```sql
DECLARE @ObjectNamespace NVARCHAR(255) = 'task';
DECLARE @ObjectKey NVARCHAR(255) = '323';
DECLARE @ObjectRelation NVARCHAR(255) = 'owner';

DECLARE @SubjectNamespace NVARCHAR(255) = 'user'
DECLARE @SubjectKey NVARCHAR(255) = '2';
```

We want to answer the question, if `user` with the key `2` is an 
`owner` of `task` with key `323`. We can see in our first relation 
tuple with the Primary Key `1`, that this should hold:

```sql
(1, 'task', 323, 'owner', 'user',   2, ...)
```

How can we solve this? We start with the simple case, that the 
`user` has a direct relation to the `object`:

```sql
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
)
SELECT 
	CASE
		WHEN EXISTS(SELECT 1 FROM [RelationTuples] WHERE [SubjectNamespace] = @SubjectNamespace AND [SubjectKey] = @SubjectKey) 
			THEN 1
		ELSE 0
	END
```

Now we check, if the user is also a `viewer` for the given task. Remember a `member` 
of `organization 1` is a `viewer` of `task 323`. So we are setting the `@ObjectRelation` 
variable: 

```
DECLARE @ObjectRelation NVARCHAR(255) = 'viewer';
```

And executing it returns:

```
0
```

This is logical, because we didn't look at the `member` relationship from the `user` to 
the `organization` at all. We can fix this, by using Recursive CTE:

```sql
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
SELECT 
	CASE
		WHEN EXISTS(SELECT 1 FROM [RelationTuples] WHERE [SubjectNamespace] = @SubjectNamespace AND [SubjectKey] = @SubjectKey) 
			THEN 1
		ELSE 0
	END
```

And executing it returns:

```
1
```

Amazing! We have just implemented a crude version of the Check API.

What's left is to copy and paste the query from the SQL Server Management Studio and 
put it into a function, which we are going to call `udf_RelationTuples_Check`:


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

### The Google Zanzibar Read API ###

This is great, but I don't want to check every single object to find out, if a subject 
has access to a specific object. Say I want to ask for all `tasks` a `user` is allowed 
to view?

We have already written a Recursive CTE for the Check API already, so we can modify it 
a little bit to do a reverse lookup from the `Subject` to the `Object`, instead of 
going from `Object` to `Subject`.

We modify it slightly to get all tasks

```sql
DECLARE @ObjectNamespace NVARCHAR(255) = 'task';
DECLARE @ObjectRelation NVARCHAR(255) = 'viewer';

DECLARE @SubjectNamespace NVARCHAR(255) = 'user'
DECLARE @SubjectKey NVARCHAR(255) = '2';

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
SELECT DISTINCT 
    [ObjectNamespace], [ObjectKey], [ObjectRelation]
FROM 
    [RelationTuples] 
WHERE
    [ObjectNamespace] = @ObjectNamespace AND [ObjectRelation] = @ObjectRelation;
```

And for `user 2` we get the following objects:

```
task	152	viewer
task	323	viewer
```

That makes sense:

* `user 2` is `member` of `org 1`, a `member` of `org 1` is `viewer` of `task 323`
* `user 2` is `member` of `org 2`, a `member` of `org 1` is `viewer` of `task 152`

Let's take a look at `user 4` instead. 

* `user 4` is a `member` of `org 2`, a member of `org 2` is `viewer` of `task 152`.

Running the query with `user 4` returns only `1` object:

```
task	152	viewer
```

Great!

What's left is to copy and paste the query from the SQL Server Management Studio and 
put it into a Table-Valued Function, which we are going to call 
`[Identity].[tvf_RelationTuples_ListObjects]`:

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
     [ObjectNamespace]   NVARCHAR(50)
    ,[ObjectKey]         INT
    ,[ObjectRelation]    NVARCHAR(50)
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
	    [ObjectNamespace], [ObjectKey], [ObjectRelation]
    FROM 
	    [RelationTuples] 
    WHERE
	    [ObjectNamespace] = @ObjectNamespace AND [ObjectRelation] = @ObjectRelation;

    RETURN;

END
```


## Conclusion ##

And that's it! In this article we have taken a look at Google Zanzibar and how 
its Check and Read API could be implemented. Does it scale though? No, it does 
not in this incarnation.

In the next article, we will see how to use both Stored Procedures for a simple 
.NET backend, that allows a user to query for data they have permission for. 

