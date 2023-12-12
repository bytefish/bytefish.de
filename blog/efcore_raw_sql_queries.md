title: Using Raw SQL with EntityFramework Core for Efficient SQL Queries
date: 2023-12-12 20:30
tags: sql, efcore, dotnet
category: dotnet
slug: efcore_raw_sql_queries
author: Philipp Wagner
summary: This article shows how to use EntityFramework Core and JSON for efficient queries. 

If I start a new .NET project, I often think to myself: "No! I don't want a dependency on EntityFramework Core. 
ORMs are a leaky abstraction and it's a dependency clocking in at literally a 100.000 lines of code and a LINQ 
Provider so complicated... it needs expert .NET knowledge!".

And then you'll suddently find yourself mapping an ADO.NET `DbDataReader` to Data Transfer Objects, you'll find 
yourself knee-deep in your own abstraction layers and at some point you think to yourself: "Why? I don't want 
to develop EntityFramework Core myself!".

That said... EntityFramework Core, makes it pretty easy to work with raw SQL these days.

Why not combine both?

I hit an interesting problem lately, where I couldn't make EntityFramework Core work. Just using the Raw SQL 
capabilities of EntityFramework Core made it really easy to work around it and I think it's nice sharing it.

## An Example for using Raw SQL Queries with Entity Framework Core ##

I have a class `AclSubject`, which can either be an `AclSubjectId` or an `AclSubjectSet`. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Models
{
    /// <summary>
    /// Base class for Subjects, which is either a <see cref="AclSubjectId"/> or a <see cref="AclSubjectSet"/>.
    /// </summary>
    public abstract record AclSubject
    {
        // ...
    }
    
    /// <summary>
    /// A Subject Set.
    /// </summary>
    public record AclSubjectSet : AclSubject
    {
        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public required string Namespace { get; set; }

        /// <summary>
        /// Gets or sets the Object.
        /// </summary>
        public required string Object { get; set; }

        /// <summary>
        /// Gets or sets the Relation.
        /// </summary>
        public required string Relation { get; set; }
    }
    
    /// <summary>
    /// A Subject ID.
    /// </summary>
    public record AclSubjectId : AclSubject
    {
        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public required string Namespace { get; set; }

        /// <summary>
        /// Gets or sets the ID.
        /// </summary>
        public required string Id { get; set; }
    }
}
```

The Subjects are going to be queried from a table `[Identity].[RelationTuple]` with the following structure:

```sql
CREATE TABLE [Identity].[RelationTuple](
    [RelationTupleID]       INT                                         CONSTRAINT [DF_Identity_RelationTuple_RelationTupleID] DEFAULT (NEXT VALUE FOR [Identity].[sq_RelationTuple]) NOT NULL,
    [Namespace]             NVARCHAR(50)                                NOT NULL,
    [Object]                NVARCHAR(50)                                NOT NULL,
    [Relation]              NVARCHAR(50)                                NOT NULL,
    [SubjectNamespace]      NVARCHAR(50)                                NOT NULL,
    [Subject]               NVARCHAR(50)                                NOT NULL,
    [SubjectRelation]       NVARCHAR(50)                                NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    -- ...
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[RelationTupleHistory]));
```

I want to solve a simple problem: 

> Get all relation tuples, where, given a list of Subjects, the `SubjectNamespace` and `Subject` match and the `SubjectRelation` is either `NULL` or matches.

I came up with the following method signature in the Service:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AclExperiments.Models;

namespace AclExperiments.Stores
{
    public interface IRelationTupleStore
    {
        /// <summary>
        /// Get Objects by a list of Subjects.
        /// </summary>
        /// <param name="namespace">The target objects Namespace</param>
        /// <param name="relation">The target objects relation</param>
        /// <param name="subjects">A List of Subjects to query</param>
        /// <param name="cancellationToken">CancellationToken to cancel asynchronous processing</param>
        /// <returns>List of Relations</returns>
        Task<List<AclRelation>> GetRelationTuplesAsync(string @namespace, string relation, List<AclSubject> subjects, CancellationToken cancellationToken);
        
        // ...
    }
}
```

So how would you solve this efficiently with LINQ and EntityFramework Core? A `ICollection#Contains` is not going to work, 
multiple `Where` Statements wouldn't cut it either. Trying to come up with a `PredicateBuilder`? Running the query 
multiple times? How efficient is that? 

And I think to myself: It would be so simple, by just passing a Table-Valued Parameter! Then it dawned upon me... Why not 
simply pass some JSON and use it? I fired up a SQL Server Management Studio and typed out an example query:

```sql
DECLARE @json NVARCHAR(MAX) = N'[
	{
		"SubjectNamespace": "Test",
		"Subject": "Test",
		"SubjectRelation": "Test"
	}
]';

DECLARE @namespace NVARCHAR(50) = 'Test';
DECLARE @relation NVARCHAR(50) = 'Test';

WITH QuerySubjects AS (
	SELECT [SubjectNamespace], [Subject], [SubjectRelation]
	FROM OPENJSON(@json) WITH (
		[SubjectNamespace] NVARCHAR(50) '$.SubjectNamespace',
		[Subject] NVARCHAR(50) '$.Subject',
		[SubjectRelation] NVARCHAR(50) '$.SubjectRelation'
	)
)
SELECT r.*
FROM [Identity].[RelationTuple] r
	INNER JOIN QuerySubjects q ON r.[SubjectNamespace] = q.[SubjectNamespace] 
		AND r.[Subject] = q.[Subject]
		AND ((r.[SubjectRelation] = q.[SubjectRelation]) OR (r.[SubjectRelation] IS NULL AND q.[SubjectRelation] IS NULL))
WHERE
	r.[Namespace] = @namespace AND r.[Relation] = @relation

```

By using the `FromSqlInterpolated` method of the `DbSet` we can copy and paste it into our code. The only thing 
that needs to be done is to change the parameters to the interpolation syntax and prepare the JSON string 
ourselves.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AclExperiments.Stores
{
    public class SqlRelationTupleStore : IRelationTupleStore
    {
        private readonly IDbContextFactory<ApplicationDbContext> _dbContextFactory;

        public SqlRelationTupleStore(IDbContextFactory<ApplicationDbContext> dbContextFactory)
        {
            _dbContextFactory = dbContextFactory;
        }
        
        // ...

        public async Task<List<AclRelation>> GetRelationTuplesAsync(string@namespace, string relation,  List<AclSubject> subjects, CancellationToken cancellationToken)
        {
            // I am not sure, if should be proud or ashamed for this 🤭. 
            var parameters = subjects
                .Select(x => ExtractComponents(x))
                .Select(x => new
                {
                    SubjectNamespace = x.Namespace,
                    Subject = x.Object,
                    SubjectRelation = x.Relation,
                })
                .ToList();

            // Serialize the Tuples to JSON.
            var json = JsonSerializer.Serialize(parameters);

            // Now execute a raw SQL using the JSON String as Parameters.
            using (var context = await _dbContextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false))
            {
                var tuples = context.RelationTuples
                    .FromSqlInterpolated(@$"
                        WITH QuerySubjects AS (
	                        SELECT [SubjectNamespace], [Subject], [SubjectRelation]
	                        FROM OPENJSON({json}) WITH (
		                        [SubjectNamespace] NVARCHAR(50) '$.SubjectNamespace',
		                        [Subject] NVARCHAR(50) '$.Subject',
		                        [SubjectRelation] NVARCHAR(50) '$.SubjectRelation'
	                        )
                        )
                        SELECT r.*
                        FROM [Identity].[RelationTuple] r
	                        INNER JOIN QuerySubjects q ON r.[SubjectNamespace] = q.[SubjectNamespace] 
		                        AND r.[Subject] = q.[Subject]
		                        AND ((r.[SubjectRelation] = q.[SubjectRelation]) OR (r.[SubjectRelation] IS NULL AND q.[SubjectRelation] IS NULL))
                        WHERE
	                        r.[Namespace] = {@namespace} AND r.[Relation] = {relation}")
                    .ToList();

                return tuples
                    .Select(ConvertToAclRelation)
                    .ToList();
            }
        }

        (string? Namespace, string Object, string? Relation) ExtractComponents(AclSubject subject)
        {
            switch (subject)
            {
                case AclSubjectId subjectId:
                    return (subjectId.Namespace, subjectId.Id, null);
                case AclSubjectSet subjectSet:
                    return (subjectSet.Namespace, subjectSet.Object, subjectSet.Relation);
                default:
                    throw new NotImplementedException();
            }
        }
        
        // ...
    }
}
```

And that's it.

How do you solve such queries in EntityFramework Core? Maybe I am missing something obvious here.