title: Using Relationship-based Access Control in a .NET application
date: 2023-06-17 11:16
tags: sql, tsql, authorization, identity
category: sql
slug: dotnet_backend_for_relationship_based_acl
author: Philipp Wagner
summary: This article shows how to write a simple ASP.NET Core Backend, that makes use of Relationship-based Access Control.

In the previous article, we have learnt about Google Zanzibar and have 
written two Stored Procedures for the Check and Read API. Now it's time 
to see how to use these procedures in a .NET application!

All code can be found in a GitHub repository at:

* [https://github.com/bytefish/AuthorizationExperiments](https://github.com/bytefish/AuthorizationExperiments)

## Table of contents ##

[TOC]

## What we are going to build ##

Imagine you have a Task Management application and users have relationships to 
tasks. We make up some sample data, to have some data to start with. The 
relationships look like this:

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

In the previous article we have seen, that we are able to check for user 
permissions on objects and we can inversely list all objects an object 
has access to.

Now let's build the database for the application, all Tables go into an 
`[Application]` schema.

### Database Tables ###

Every `Task` in the application has some kind of Priority, such as `Low`, `Normal` 
and `High`, so users can decide what task to tackle next. We add the 
`[Application].[TaskPriority]` table as:

```sql
CREATE TABLE [Application].[TaskPriority](
    [TaskPriorityID]    INT                                         NOT NULL,
    [Name]              NVARCHAR(50)                                NOT NULL,
    [RowVersion]        ROWVERSION                                  NULL,
    [LastEditedBy]      INT                                         NOT NULL,
    [ValidFrom]         DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]           DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_TaskPriority] PRIMARY KEY ([TaskPriorityID]),
    CONSTRAINT [FK_TaskPriority_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[TaskPriorityHistory]));
```

In a Post-Deployment script we are insert the Priorities `Low`, `Normal` and `High`:

```sql
PRINT 'Inserting [Application].[TaskPriority] ...'

-----------------------------------------------
-- Global Parameters
-----------------------------------------------
DECLARE @ValidFrom datetime2(7) = '20130101'
DECLARE @ValidTo datetime2(7) =  '99991231 23:59:59.9999999'

-----------------------------------------------
-- [Application].[TaskPriority]
-----------------------------------------------
MERGE INTO [Application].[TaskPriority] AS [Target]
USING (VALUES 
			  (1, 'Low', 1, @ValidFrom, @ValidTo)
			, (2, 'Normal', 1, @ValidFrom, @ValidTo)
			, (3, 'High', 1, @ValidFrom, @ValidTo)
		) AS [Source]([TaskPriorityID], [Name], [LastEditedBy], [ValidFrom], [ValidTo])
ON ([Target].[TaskPriorityID] = [Source].[TaskPriorityID])
WHEN NOT MATCHED BY TARGET THEN
	INSERT 
		([TaskPriorityID], [Name], [LastEditedBy], [ValidFrom], [ValidTo]) 
	VALUES 
		([Source].[TaskPriorityID], [Source].[Name], [Source].[LastEditedBy], [Source].[ValidFrom], [Source].[ValidTo]);
```

We also need to know, what status a `Task` is in. Has it been completed? Are we 
waiting on others to continue the work? Has it been deferred? So we add a 
`[Application].[TaskStatus]` table:

```sql
CREATE TABLE [Application].[TaskStatus](
    [TaskStatusID]      INT                                         NOT NULL,
    [Name]              NVARCHAR(50)                                NOT NULL,
    [RowVersion]        ROWVERSION                                  NULL,
    [LastEditedBy]      INT                                         NOT NULL,
    [ValidFrom]         DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]           DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_TaskStatus] PRIMARY KEY ([TaskStatusID]),
    CONSTRAINT [FK_TaskStatus_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[TaskStatusHistory]));
```

In a Post-Deployment script we are adding the various states, such as `Not Started`, `In Progress`, ...

```sql
PRINT 'Inserting [Application].[TaskStatus] ...'

-----------------------------------------------
-- Global Parameters
-----------------------------------------------
DECLARE @ValidFrom datetime2(7) = '20130101'
DECLARE @ValidTo datetime2(7) =  '99991231 23:59:59.9999999'

-----------------------------------------------
-- [Application].[TaskStatus]
-----------------------------------------------
MERGE INTO [Application].[TaskStatus] AS [Target]
USING (VALUES 
			  (1, 'Not Started', 1, @ValidFrom, @ValidTo)
			, (2, 'In Progress', 1, @ValidFrom, @ValidTo)
			, (3, 'Completed', 1, @ValidFrom, @ValidTo)
			, (4, 'Waiting On Others', 1, @ValidFrom, @ValidTo)
			, (5, 'Deferred', 1, @ValidFrom, @ValidTo)
		) AS [Source]([TaskStatusID], [Name], [LastEditedBy], [ValidFrom], [ValidTo])
ON ([Target].[TaskStatusID] = [Source].[TaskStatusID])
WHEN NOT MATCHED BY TARGET THEN
	INSERT 
		([TaskStatusID], [Name], [LastEditedBy], [ValidFrom], [ValidTo])
	VALUES 
		([Source].[TaskStatusID], [Source].[Name], [Source].[LastEditedBy], [Source].[ValidFrom], [Source].[ValidTo]);
```


Finally we can create the `{Application].[Task]` table, which we are going to query and that holds all tasks for the users of the application:

```sql
CREATE TABLE [Application].[Task](
    [TaskID]                INT                                         CONSTRAINT [DF_Application_Task_TaskID] DEFAULT (NEXT VALUE FOR [Application].[sq_Task]) NOT NULL,
    [Title]                 NVARCHAR(50)                                NOT NULL,
    [Description]           NVARCHAR(2000)                              NOT NULL,
    [DueDateTime]           DATETIME2(7)                                NULL,
    [ReminderDateTime]      DATETIME2(7)                                NULL,
    [CompletedDateTime]     DATETIME2(7)                                NULL,
    [AssignedTo]            INT                                         NULL,
    [TaskPriorityID]        INT                                         NOT NULL,
    [TaskStatusID]          INT                                         NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_Task] PRIMARY KEY ([TaskID]),
    CONSTRAINT [FK_Task_TaskPriority_TaskPriorityID] FOREIGN KEY ([TaskPriorityID]) REFERENCES [Application].[TaskPriority] ([TaskPriorityID]),
    CONSTRAINT [FK_Task_TaskStatus_TaskStatusID] FOREIGN KEY ([TaskStatusID]) REFERENCES [Application].[TaskStatus] ([TaskStatusID]),
    CONSTRAINT [FK_Task_User_LastEditedBy] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    CONSTRAINT [FK_Task_User_AssignedTo] FOREIGN KEY ([AssignedTo]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Application].[TaskHistory]));
```

In a Post-Deployment Script we are adding the two tasks `323` and `152`, that have been used in the relation tuples:

```sql
PRINT 'Inserting [Application].[Task] ...'

-----------------------------------------------
-- Global Parameters
-----------------------------------------------
DECLARE @ValidFrom datetime2(7) = '20130101'
DECLARE @ValidTo datetime2(7) =  '99991231 23:59:59.9999999'

-----------------------------------------------
-- [Application].[Task]
-----------------------------------------------
MERGE INTO [Application].[Task] AS [Target]
USING (VALUES 
     (323, 'Task #323', 'Description for Task #323', NULL, NULL, NULL, NULL, 2, 1, 1, @ValidFrom, @ValidTo)
    ,(152, 'Task #152', 'Description for Task #152', NULL, NULL, NULL, NULL, 3, 1, 1, @ValidFrom, @ValidTo)
) AS [Source] ([TaskID], [Title], [Description], [DueDateTime], [ReminderDateTime], [CompletedDateTime],[AssignedTo], [TaskPriorityID], [TaskStatusID], [LastEditedBy], [ValidFrom], [ValidTo])
ON ([Target].[TaskID] = [Source].[TaskID])
WHEN NOT MATCHED BY TARGET THEN
	INSERT 
		([TaskID], [Title], [Description], [DueDateTime], [ReminderDateTime], [CompletedDateTime],[AssignedTo], [TaskPriorityID], [TaskStatusID], [LastEditedBy], [ValidFrom], [ValidTo])
	VALUES 
		([Source].[TaskID], [Source].[Title], [Source].[Description], [Source].[DueDateTime], [Source].[ReminderDateTime], [Source].[CompletedDateTime],[Source].[AssignedTo], [Source].[TaskPriorityID], [Source].[TaskStatusID], [Source].[LastEditedBy], [Source].[ValidFrom], [Source].[ValidTo]);
```

### Stored Procedures ###

Now we need to write a Stored Procedure for reading a single task and for reading a 
list of tasks. These Stored Procedures are going to use Relationship-based Authorization 
developed in the previous article.

#### usp_Task_ReadTask - Reading a Single Task ####

To read a single task we are adding the Stored Procedure `[Application].[usp_Task_ReadTask]`. It uses 
the `[Identity].[udf_RelationTuples_Check]` function to determine, if the given user has sufficient 
permissions to read the task.

```sql
CREATE PROCEDURE [Application].[usp_Task_ReadTask]
     @TaskID INT
    ,@UserID INT
AS
BEGIN TRY
    SET NOCOUNT ON;
    
    IF @TaskID IS NULL
        THROW 50000, N'TaskID is required', 16;

    IF @UserID IS NULL
        THROW 50000, N'UserID is required', 16;

    IF (SELECT 1 FROM [Identity].[User] WHERE [UserID] = @UserID) IS NULL
        THROW 50000, N'User for UserID was not found', 16;

    IF (SELECT 1 FROM [Application].[Task] WHERE [TaskID] = @TaskID) IS NULL
        THROW 50000, N'Task for TaskID was not found', 16;

    IF (SELECT [Identity].[udf_RelationTuples_Check]('task', @TaskID, 'viewer', 'user', @UserID)) = 0
        THROW 50000, 'Insufficient Permissions', 16

    SELECT 
        *
    FROM 
        [Application].[Task]
    WHERE
        TaskID = @TaskID;

END TRY
BEGIN CATCH
    IF(@@TRANCOUNT > 0)
        ROLLBACK TRAN;

    THROW;
END CATCH
```

#### usp_Task_ReadTasks - Reading multiple Tasks ####

To read multiple tasks, we are adding a Stored Procedure `[Application].[usp_Task_ReadTasks]`. This Stored 
Procedure makes use of the Table-Valued Function `[Identity].[tvf_RelationTuples_ListObjects]` to get the 
lists of tasks a user can see:

```sql
CREATE PROCEDURE [Application].[usp_Task_ReadTasks]
    @UserID INT
AS
BEGIN TRY
    SET NOCOUNT ON;
    
    IF @UserID IS NULL
        THROW 50000, N'UserID is required', 16;

    IF (SELECT 1 FROM [Identity].[User] WHERE [UserID] = @UserID) IS NULL
        THROW 50000, N'User for UserID was not found', 16;

    SELECT 
        *
    FROM 
        [Application].[Task] t
            CROSS APPLY [Identity].[tvf_RelationTuples_ListObjects]('task', 'viewer', 'user', @UserID) o
    WHERE
        o.ObjectKey = t.TaskID

END TRY
BEGIN CATCH
    IF(@@TRANCOUNT > 0)
        ROLLBACK TRAN;

    THROW;
END CATCH
```

We only needed a `CROSS APPLY` and that's it, basically. Impressive how easy it is with SQL!

## .NET Backend ##

In the following sections we are going to provide the groundwork to execute the Stored 
Procedures and use them in an ASP.NET Core Web API Controller, that provides HTTP endpoints.

### Domain Model ###

Let's start with the Domain model.

We need an enumeration, that maps to the `[Application].[TaskPriority]` table:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AuthorizationExperiment.Api.Models.Application
{
    /// <summary>
    /// The Priority of a Task, such as Low, Normal, High.
    /// </summary>
    public enum TaskPriorityEnum
    {
        /// <summary>
        /// No Priority.
        /// </summary>
        None = 0,

        /// <summary>
        /// Low Priority.
        /// </summary>
        Low = 1,

        /// <summary>
        /// Normal Priority.
        /// </summary>
        Normal = 2,

        /// <summary>
        /// High Priority.
        /// </summary>
        High = 3,
    }
}
```

Then we need an enumeration to map to the `[Application].[TaskStatus]` table:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AuthorizationExperiment.Api.Models.Application
{
    /// <summary>
    /// Status of a Task, such as "Assigned", "Completed", ...
    /// </summary>
    public enum TaskStatusEnum
    {
        /// <summary>
        /// No Task Status.
        /// </summary>
        None = 0,

        /// <summary>
        /// Task has not been started.
        /// </summary>
        NotStarted = 1,

        /// <summary>
        /// Task is in progress.
        /// </summary>
        InProgress = 2,
        
        /// <summary>
        /// Task has been completed.
        /// </summary>
        Completed = 3,

        /// <summary>
        /// Task is waiting on others.
        /// </summary>
        WaitingOnOthers = 4,

        /// <summary>
        /// Task has been deferred.
        /// </summary>
        Deferred = 5,
    }
}
```

What's left is a Domain model for the `[Application].[Task]` table:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AuthorizationExperiment.Api.Models.Application
{
    /// <summary>
    /// A Task to be processed.
    /// </summary>
    public class Task
    {
        /// <summary>
        /// Gets or sets the Id.
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Gets or sets the Title.
        /// </summary>
        public string Title { get; set; } = null!;

        /// <summary>
        /// Gets or sets the Description.
        /// </summary>
        public string Description { get; set; } = null!;

        /// <summary>
        /// Gets or sets the Priority.
        /// </summary>
        public TaskPriorityEnum TaskPriority { get; set; }

        /// <summary>
        /// Gets or sets the Status.
        /// </summary>
        public TaskStatusEnum TaskStatus { get; set; }

        /// <summary>
        /// Gets or sets the Due Date.
        /// </summary>
        public DateTime? DueDateTime { get; set; }

        /// <summary>
        /// Gets or sets the Reminder Date.
        /// </summary>
        public DateTime? ReminderDateTime { get; set; }

        /// <summary>
        /// Gets or sets the Completed Date.
        /// </summary>
        public DateTime? CompletedDateTime { get; set; }

        /// <summary>
        /// Gets or sets Assigned To.
        /// </summary>
        public int? AssignedTo { get; set; }

        /// <summary>
        /// Gets or sets the Row Version.
        /// </summary>
        public byte[] RowVersion { get; set; } = null!;

        /// <summary>
        /// Gets or sets Last Edited By.
        /// </summary>
        public int LastEditedBy { get; set; }

        /// <summary>
        /// Gets or sets Valid From.
        /// </summary>
        public DateTime ValidFrom { get; set; }

        /// <summary>
        /// Gets or sets Valid To.
        /// </summary>
        public DateTime ValidTo { get; set; }
    }
}
```

### Executing SQL Queries and Stored Procedures using SqlQuery ###

We need to execute SQL Queries and call into Stored Procedures. Your first insinct is to 
use EntityFramework Core or Dapper probably. But I think both of them are highly opinionated 
frameworks, for all the good and the bad.

You don't need any of it.

This is how I want to execute a Stored Procedure, when using them in a .NET application:

```csharp
var table = new SqlQuery(connection, transaction)
    .Proc("[usp_MyStoredProcedure")
    .Param("Param1", value1)
    .Param("Param2", value2)
    .ExecuteDataTableAsync();
    
var result = ConvertToResult(table);

// ...
```

So we add a class `SqlQuery`, which implements just that.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Data;
using System.Data.Common;

namespace AuthorizationExperiment.Api.Base.Query
{
    /// <summary>
    /// Provides a very thin wrapper over ADO.NET.
    /// </summary>
    public class SqlQuery
    {
        /// <summary>
        /// Connection to the database.
        /// </summary>
        public DbConnection Connection { get; private set; }

        /// <summary>
        /// Connection to the database.
        /// </summary
        public DbTransaction? Transaction { get; private set; }

        /// <summary>
        /// Command to be executed.
        /// </summary>
        public DbCommand? Command { get; private set; }

        public SqlQuery(DbConnection connection)
                : this(connection, null)
        {
        }

        public SqlQuery(DbConnection connection, DbTransaction? transaction)
        {
            Connection = connection;
            Transaction = transaction;
        }

        /// <summary>
        /// Sets the <see cref="DbCommand"/> to execute.
        /// </summary>
        /// <param name="command"><see cref="DbCommand"/> to execute</param>
        /// <returns>SqlQuery with <see cref="DbCommand"/></returns>
        public SqlQuery SetCommand(DbCommand command)
        {
            Command = command;

            return this;
        }

        /// <summary>
        /// Sets the Command Type.
        /// </summary>
        /// <param name="commandType">Command Type</param>
        /// <returns>SqlQuery with Command Type</returns>
        public SqlQuery SetCommandType(CommandType commandType)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            Command.CommandType = commandType;

            return this;
        }

        /// <summary>
        /// Sets the Command Timeout.
        /// </summary>
        /// <param name="commandTimeout">Command Timeout</param>
        /// <returns>SqlQuery with Command Timeout</returns>
        public SqlQuery SetCommandTimeout(TimeSpan commandTimeout)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            Command.CommandTimeout = (int)commandTimeout.TotalSeconds;

            return this;
        }

        /// <summary>
        /// Adds a Parameter to the Query.
        /// </summary>
        /// <param name="name">Name</param>
        /// <param name="type">Type</param>
        /// <param name="value">Value</param>
        /// <param name="size">Size</param>
        /// <returns><see cref="SqlQuery"/> with Parameter added</returns>
        public SqlQuery AddParameter(string name, DbType type, object? value, int size = 0)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            var parameter = Command.CreateParameter();

            parameter.ParameterName = name;
            parameter.DbType = type;
            parameter.Value = value;
            parameter.Size = size;

            if (size == 0)
            {
                bool isTextType = type == DbType.AnsiString || type == DbType.String;

                if (value != null && isTextType)
                {
                    parameter.Size = 100 * (value.ToString()!.Length / 100 + 1);
                }
            }
            else
            {
                parameter.Size = size;
            }

            Command.Parameters.Add(parameter);

            return this;
        }

        /// <summary>
        /// Executes the <see cref="SqlQuery"/> and returns a <see cref="DataSet"/> for the query results.
        /// </summary>
        /// <param name="connection">Connection</param>
        /// <param name="transaction">Transaction</param>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A <see cref="DataSet"/> with the query results.</returns>
        public async Task<DataSet> ExecuteDataSetAsync(CancellationToken cancellationToken)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            Command.Connection = Connection;
            Command.Transaction = Transaction;

            DataSet dataset = new DataSet();

            using (var reader = await Command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false))
            {
                while (!reader.IsClosed)
                {
                    DataTable dataTable = new DataTable();
                    dataTable.Load(reader);

                    dataset.Tables.Add(dataTable);
                }
            }

            return dataset;
        }

        /// <summary>
        /// Executes the <see cref="SqlQuery"/> and returns a <see cref="DataTable"/> for the query results.
        /// </summary>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A <see cref="DataSet"/> with the query results.</returns>
        public async Task<DataTable> ExecuteDataTableAsync(CancellationToken cancellationToken)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            Command.Connection = Connection;
            Command.Transaction = Transaction;

            DataTable dataTable = new DataTable();

            using (var reader = await Command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false))
            {
                dataTable.Load(reader);
            }

            return dataTable;
        }

        /// <summary>
        /// Executes the <see cref="SqlQuery"/> and returns a <see cref="DataSet"/> for the query results.
        /// </summary>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A <see cref="DataSet"/> with the query results.</returns>
        public async Task<int> ExecuteNonQueryAsync(CancellationToken cancellationToken)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            Command.Connection = Connection;
            Command.Transaction = Transaction;

            int numberOfRowsAffected = await Command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);

            return numberOfRowsAffected;
        }

        /// <summary>
        /// Executes the <see cref="SqlQuery"/> and returns a <see cref="DataSet"/> for the query results.
        /// </summary>
        /// <param name="cancellationToken">Cancellation Token</param>
        /// <returns>A <see cref="DataSet"/> with the query results.</returns>
        public async Task<object?> ExecuteScalarAsync(CancellationToken cancellationToken)
        {
            if (Command == null)
            {
                throw new InvalidOperationException("Command is not set");
            }

            Command.Connection = Connection;
            Command.Transaction = Transaction;

            object? scalarValue = await Command.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false);

            return scalarValue;
        }
    }
}
```

We add some SQL Server-related extensions for preparing the `Command` and Parameters:

```sql
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Data.SqlClient;
using System.Data;

namespace AuthorizationExperiment.Api.Base.Query
{
    /// <summary>
    /// SQL Server Extensions for the <see cref="SqlQuery"/>.
    /// </summary>
    public static class SqlQueryExtensions
    {
        /// <summary>
        /// Sets the Command Text for the <see cref="SqlQuery"/>.
        /// </summary>
        /// <param name="query"></param>
        /// <param name="commandText"></param>
        /// <returns></returns>
        public static SqlQuery Sql(this SqlQuery query, string commandText, int commandTimeOutInSeconds = 60)
        {
            var cmd = new SqlCommand()
            {
                CommandText = commandText,
                CommandType = CommandType.Text,
                CommandTimeout = commandTimeOutInSeconds
            };

            return query.SetCommand(cmd);
        }

        /// <summary>
        /// Sets the Command Text for the <see cref="SqlQuery"/>.
        /// </summary>
        /// <param name="query"></param>
        /// <param name="commandText"></param>
        /// <returns></returns>
        public static SqlQuery Proc(this SqlQuery query, string storedProcedureName, int commandTimeOutInSeconds = 60)
        {
            var cmd = new SqlCommand()
            {
                CommandText = storedProcedureName,
                CommandType = CommandType.StoredProcedure,
                CommandTimeout = commandTimeOutInSeconds
            };

            return query.SetCommand(cmd);
        }

        /// <summary>
        /// Add a parameter with specified value to the mapper.
        /// </summary>
        /// <param name="mapper">Mapper where the parameter will be added.</param>
        /// <param name="name">Name of the parameter.</param>
        /// <param name="value">Value of the parameter.</param>
        /// <returns>Mapper object.</returns>
        public static SqlQuery Param(this SqlQuery query, string name, object? value)
        {
            if (value == null)
            {
                value = DBNull.Value;
            }

            if (query.Command is SqlCommand command)
            {
                var p = command.Parameters.AddWithValue(name, value);

                if (p.SqlDbType == SqlDbType.NVarChar
                    || p.SqlDbType == SqlDbType.VarChar)
                {
                    p.Size = 100 * (value.ToString()!.Length / 100 + 1);
                }
            }

            return query;
        }
    }
}
```

That's it.

### Providing Database Connections ###

We obviously don't want to pass a Connection String through the entire application, but have it 
a little configurable. So we add a `ISqlConnectionFactory` interface, that's responsible for 
producing a fresh and opened `DbConnection`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Data.Common;

namespace AuthorizationExperiment.Api.Base.Connections
{
    /// <summary>
    /// Creates a <see cref="DbConnection"/>.
    /// </summary>
    public interface ISqlConnectionFactory
    {
        /// <summary>
        /// Gets an opened <see cref="DbConnection"/>.
        /// </summary>
        /// <param name="cancellationToken">Cancellation Token to cancel asynchronous processing</param>
        /// <returns>An opened <see cref="DbConnection"/></returns>
        Task<DbConnection> GetDbConnectionAsync(CancellationToken cancellationToken);
    }
}
```

The `Microsoft.Data.SqlClient` comes with a `SqlConnection`, which has a Retry logic 
built in. There is no need for us to reinvent the wheel. Let's implement the 
`ISqlConnectionFactory`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Data.SqlClient;
using System.Data.Common;

namespace AuthorizationExperiment.Api.Base.Connections
{
    /// <summary>
    /// SQL Server implementation for a <see cref="ISqlConnectionFactory"/>.
    /// </summary>
    public class SqlServerConnectionFactory : ISqlConnectionFactory
    {
        /// <summary>
        /// Gets or sets the Connection String.
        /// </summary>
        public string ConnectionString { get; set; }

        /// <summary>
        /// Gets or sets the Retry Logic Provider.
        /// </summary>
        public SqlRetryLogicBaseProvider SqlRetryLogicProvider { get; set; }

        /// <summary>
        /// Creates a new <see cref="SqlServerConnectionFactory"/> based 
        /// </summary>
        /// <param name="connectionString"></param>
        public SqlServerConnectionFactory(string connectionString)
            : this(connectionString, GetExponentialBackoffProvider(5, 1, 20))
        {
        }

        public SqlServerConnectionFactory(string connectionString, SqlRetryLogicBaseProvider sqlRetryLogicProvider)
        {
            // Enable Preview Features
            SetFeatureFlags();

            ConnectionString = connectionString;
            SqlRetryLogicProvider = sqlRetryLogicProvider;
        }

        public async Task<DbConnection> GetDbConnectionAsync(CancellationToken cancellationToken)
        {
            // Create the SqlConnection for the given connection string
            var dbConnection = new SqlConnection()
            {
                ConnectionString = ConnectionString,
                RetryLogicProvider = SqlRetryLogicProvider
            };

            await dbConnection.OpenAsync(cancellationToken);

            return dbConnection;
        }

        /// <summary>
        /// Creates a default Exponential Backoff Provider, 
        /// </summary>
        /// <param name="numberOfTries">Number of Retries for transient errors</param>
        /// <param name="deltaTimeInSeconds">Time in Seconds to wait between retries</param>
        /// <param name="maxTimeIntervalInSeconds">The maximum amount to wait between retries</param>
        /// <returns></returns>
        private static SqlRetryLogicBaseProvider GetExponentialBackoffProvider(int numberOfTries = 5, int deltaTimeInSeconds = 1, int maxTimeIntervalInSeconds = 20)
        {
            // Define the retry logic parameters
            var options = new SqlRetryLogicOption()
            {
                // Tries 5 times before throwing an exception
                NumberOfTries = numberOfTries,
                // Preferred gap time to delay before retry
                DeltaTime = TimeSpan.FromSeconds(deltaTimeInSeconds),
                // Maximum gap time for each delay time before retry
                MaxTimeInterval = TimeSpan.FromSeconds(maxTimeIntervalInSeconds)
            };

            return SqlConfigurableRetryFactory.CreateExponentialRetryProvider(options);
        }

        /// <summary>
        /// Sets the AppSwitch to enable retry-logic.
        /// </summary>
        private static void SetFeatureFlags()
        {
            // https://learn.microsoft.com/en-us/sql/connect/ado-net/appcontext-switches?view=sql-server-ver16#enable-configurable-retry-logic
            AppContext.SetSwitch("Switch.Microsoft.Data.SqlClient.EnableRetryLogic", true);
        }
    }
}
```

In the `Program.cs` we register the `SqlServerConnectionFactory` as a Singleton:

```csharp
// ...

builder.Services.AddSingleton<ISqlConnectionFactory>(services =>
{
    var connectionString = builder.Configuration.GetConnectionString("ApplicationDatabase");

    if (string.IsNullOrWhiteSpace(connectionString))
    {
        throw new InvalidOperationException("No ConnectionString for 'ApplicationDatabase' found");
    }

    return new SqlServerConnectionFactory(connectionString);
});

// ...
```

And add the Connection String goes into `appsettings.json`, my database is named `ZanzibarExperiment`:

```json
{
  "ConnectionStrings": {
    "ApplicationDatabase": "Server=.\\SQLEXPRESS;Database=ZanzibarExperiment;Trusted_Connection=True;TrustServerCertificate=True;"
  }
}
```

Job done!

### Calling the Stored Procedures ###

And finally we can implement the `TaskManager`, which is responsible for calling the Stored 
Procedures. It shouldn't include too much Business Logic, because this should be put into 
the Stored Procedures:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AuthorizationExperiment.Api.Base.Connections;
using AuthorizationExperiment.Api.Base.Extensions;
using AuthorizationExperiment.Api.Base.Query;
using System.Data;

namespace AuthorizationExperiment.Api.Services.Application
{
    public class TaskManager
    {
        private readonly ISqlConnectionFactory _connectionFactory;

        public TaskManager(ISqlConnectionFactory connectionFactory)
        {
            _connectionFactory = connectionFactory;
        }

        public async Task CreateTaskAsync(Models.Application.Task task, int userId, CancellationToken cancellationToken)
        {
            using (var connection = await _connectionFactory.GetDbConnectionAsync(cancellationToken).ConfigureAwait(false))
            {
                var query = new SqlQuery(connection).Proc("[Application].[usp_Task_Create]")
                    .Param("Title", task.Title)
                    .Param("Description", task.Description)
                    .Param("AssignedTo", task.AssignedTo)
                    .Param("DueDateTime", task.DueDateTime)
                    .Param("ReminderDateTime", task.ReminderDateTime)
                    .Param("TaskPriorityID", (int)task.TaskPriority)
                    .Param("TaskStatusID", (int)task.TaskStatus)
                    .Param("UserID", userId);

                var results = await query
                    .ExecuteDataTableAsync(cancellationToken)
                    .ConfigureAwait(false);

                if (results.Rows.Count != 1)
                {
                    throw new Exception($"Expected '1' row, but got '{results.Rows.Count}'");
                }

                ConvertTask(results.Rows[0], task);
            }
        }

        public async Task<Models.Application.Task?> ReadTaskAsync(int taskId, int userId, CancellationToken cancellationToken)
        {
            using (var connection = await _connectionFactory.GetDbConnectionAsync(cancellationToken).ConfigureAwait(false))
            {
                var query = new SqlQuery(connection).Proc("[Application].[usp_Task_ReadTask]")
                    .Param("TaskID", taskId)
                    .Param("UserID", userId);

                var results = await query
                    .ExecuteDataTableAsync(cancellationToken)
                    .ConfigureAwait(false);

                if (results.Rows.Count != 1)
                {
                    throw new Exception($"Expected '1' row, but got '{results.Rows.Count}'");
                }

                var task = new Models.Application.Task();

                ConvertTask(results.Rows[0], task);

                return task;
            }
        }

        public async Task<List<Models.Application.Task>> ReadTasksAsync(int userId, CancellationToken cancellationToken)
        {
            using (var connection = await _connectionFactory.GetDbConnectionAsync(cancellationToken).ConfigureAwait(false))
            {
                var query = new SqlQuery(connection).Proc("[Application].[usp_Task_ReadTasks]")
                    .Param("UserID", userId);

                var results = await query
                    .ExecuteDataTableAsync(cancellationToken)
                    .ConfigureAwait(false);

                var tasks = new List<Models.Application.Task>();

                foreach (DataRow row in results.Rows)
                {
                    var task = new Models.Application.Task();

                    ConvertTask(row, task);

                    tasks.Add(task);
                }

                return tasks;
            }
        }

        public async Task UpdateTaskAsync(Models.Application.Task task, int lastEditedBy, CancellationToken cancellationToken)
        {
            using (var connection = await _connectionFactory.GetDbConnectionAsync(cancellationToken).ConfigureAwait(false))
            {
                var query = new SqlQuery(connection).Proc("[Application].[usp_Task_Update]")
                    .Param("TaskID", task.Id)
                    .Param("Title", task.Title)
                    .Param("Description", task.Description)
                    .Param("AssignedTo", task.AssignedTo)
                    .Param("DueDateTime", task.DueDateTime)
                    .Param("ReminderDateTime", task.ReminderDateTime)
                    .Param("CompletedDateTime", task.CompletedDateTime)
                    .Param("TaskPriorityID", (int)task.TaskPriority)
                    .Param("TaskStatusID", (int)task.TaskStatus)
                    .Param("RowVersion", task.RowVersion)
                    .Param("UserID", lastEditedBy);

                var results = await query
                    .ExecuteDataTableAsync(cancellationToken)
                    .ConfigureAwait(false);

                if (results.Rows.Count != 1)
                {
                    throw new Exception($"Expected '1' row, but got '{results.Rows.Count}'");
                }

                ConvertTask(results.Rows[0], task);
            }
        }

        public async Task<int> DeleteTaskAsync(int taskId, int userId, CancellationToken cancellationToken)
        {
            using (var connection = await _connectionFactory.GetDbConnectionAsync(cancellationToken).ConfigureAwait(false))
            {
                var query = new SqlQuery(connection).Proc("[Application].[usp_Task_Delete]")
                    .Param("TaskID", taskId)
                    .Param("UserID", userId);

                int numberOfRowsAffected = await query.ExecuteNonQueryAsync(cancellationToken);

                if (numberOfRowsAffected != 1)
                {
                    throw new Exception($"Query affected '{numberOfRowsAffected}', but expected '1'");
                }

                return numberOfRowsAffected;
            }
        }

        private static void ConvertTask(DataRow row, Models.Application.Task task)
        {
            task.Id = row.GetInt32("TaskID");
            task.Title = row.GetString("Title");
            task.Description = row.GetString("Description");
            task.TaskPriority = (Models.Application.TaskPriorityEnum)row.GetInt32("TaskPriorityID");
            task.TaskStatus = (Models.Application.TaskStatusEnum)row.GetInt32("TaskStatusID");
            task.AssignedTo = row.GetNullableInt32("AssignedTo");
            task.DueDateTime = row.GetNullableDateTime("DueDateTime");
            task.CompletedDateTime = row.GetNullableDateTime("CompletedDateTime");
            task.ReminderDateTime = row.GetNullableDateTime("ReminderDateTime");
            task.RowVersion = row.GetByteArray("RowVersion");
            task.LastEditedBy = row.GetInt32("LastEditedBy");
            task.ValidFrom = row.GetDateTime("ValidFrom");
            task.ValidTo = row.GetDateTime("ValidTo");
        }
    }
}
```

In the `Program.cs` we add it as a Singleton:

```csharp
builder.Services.AddSingleton<TaskManager>();
```

And that's it.

### ASP.NET Core Web API Endpoints ###

What's left are the two endpoints, that we wanted to provide. By using the `[FromServices]` attribute, we 
can easily inject the `TaskManager`. It is a contrived example, so we are not converting from the Business 
Object to a Data Transfer Object, which you should do in production.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AuthorizationExperiment.Api.Services.Application;
using Microsoft.AspNetCore.Mvc;

namespace AuthorizationExperiment.Api.Controllers
{
    [ApiController]
    public class TasksController : ControllerBase
    {
        private readonly ILogger<TasksController> _logger;
        
        public TasksController(ILogger<TasksController> logger)
        {
            _logger = logger;
        }

        [HttpGet("/task")]
        public async Task<IActionResult> GetTask([FromServices] TaskManager taskManager, [FromQuery(Name = "taskId")] int taskId, [FromQuery(Name = "userId")] int userId, CancellationToken cancellationToken)
        {
            _logger.LogDebug("Loading Task {taskId} for User {userId}", taskId, userId);

            try
            {
                var task = await taskManager.ReadTaskAsync(taskId, userId, cancellationToken);

                return Ok(task);
            }
            catch (Exception ex)
            {
                return BadRequest(ex.Message);
            }
        }

        [HttpGet("/tasks")]
        public async Task<IActionResult> GetTasks([FromServices] TaskManager taskManager, [FromQuery(Name = "userId")] int userId, CancellationToken cancellationToken)
        {
            _logger.LogDebug("Loading Tasks for User {userId}", userId);

            try
            {
                var tasks = await taskManager.ReadTasksAsync(userId, cancellationToken);

                return Ok(tasks);
            } 
            catch(Exception ex)
            {
                return BadRequest(ex.Message);
            }
        }
    }
}
```

To make it easy to query the endpoints, we are adding a dependency on `Swashbuckle` and register 
it in the `Program.cs` like this:


```csharp

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
builder.Services.AddSwaggerGen();


// Configure the HTTP request pipeline.

app.UseSwagger();
app.UseSwaggerUI();
```

You can now start the ASP.NET Core Web API project and can query your heart out.

## Conclusion ##

In this article we have seen, that it's quite easy to go from an idea to an implementation. By using 
a bit of SQL and ADO.NET we have written an ASP.NET Core Web API Backend, that allows us to apply 
Relationship-based Access Control when querying the data.

From here it's probably a small way to use it for OData queries.