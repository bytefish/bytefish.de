title: SqlQuery with EntityFramework Core 3
date: 2020-06-20 08:10
tags: dotnet, efcore
category: dotnet
slug: sqlquery_with_ef_core
author: Philipp Wagner
summary: This article shows how to implement a SqlQuery extension for EntityFramework Core.

One thing I am missing in EntityFramework Core is a way to run raw SQL queries and map the results 
to a class, just like the EntityFramework 6 ``DbContext.Database.SqlQuery<T>`` method. So why on earth 
would you want to execute raw SQL? 

For small projects it's much simpler to write a small query, than fiddling with abstractions like... [LINQ] 
if you are in C\# or [JPQL] if you are in Java. I firmly believe a good query can save you hundred lines of 
code. Does it create a maintenance nightmare? Probably.

Anyway! On GitHub [@davidbaxterbrowne] shared a quite nice solution to the problem. I think it's worth sharing, 
because it is quite hard to find being buried in a GitHub issue. The method takes a ``FormattableString``, so 
it does parameter binding under the hood to avoid SQL injections.

All credit goes to [@davidbaxterbrowne]:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace EasyTimeTracking.Web.Database.Extensions
{
    // Please see the GitHub Issue for the Original Code:
    //
    //      https://github.com/dotnet/efcore/issues/1862
    //
    public static class SqlQueryExtensions
    {
        public static Task<List<T>> SqlQueryAsync<T>(this DbContext db, FormattableString sql, CancellationToken cancellationToken) where T : class
        {            
            using (var contextForQuery = new ContextForQueryType<T>(db.Database.GetDbConnection()))
            {
                return contextForQuery.Set<T>()
                    .FromSqlInterpolated(sql)
                    .AsNoTracking()
                    .ToListAsync(cancellationToken);
            }
        }
        
        private class ContextForQueryType<T> : DbContext where T : class
        {
            private readonly DbConnection connection;

            public ContextForQueryType(DbConnection connection)
            {
                this.connection = connection;
            }

            protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
            {
                optionsBuilder.UseNpgsql(connection);

                base.OnConfiguring(optionsBuilder);
            }

            protected override void OnModelCreating(ModelBuilder modelBuilder)
            {
                modelBuilder.Entity<T>().HasNoKey();

                base.OnModelCreating(modelBuilder);
            }
        }
    }
}
```

And now you can use the Extension method on a DbContext like this:

```csharp
public async Task<List<MyObject>> GetEntitiesAsync(DateTime startDate, CancellationToken cancellationToken)
{
    using (var context = new ApplicationDbContext())
    {
        return await context
            .SqlQueryAsync<MyObject>($@"select *
                                      from my_database_table t
                                      where t.date >= {startDate}", cancellationToken);    
    }
}
```

It's not perfect, because you still need to hardcode the provider in the ``OnConfiguring`` method of the 
``DbContext``, but I didn't find a simple way in the EntityFramework Core API surface to get the original 
options.

Let me know, if you have ideas on how to improve the code.

[@davidbaxterbrowne]: https://github.com/davidbaxterbrowne
[LINQ]: https://docs.microsoft.com/en-us/dotnet/csharp/programming-guide/concepts/linq/
[JPQL]: https://en.wikipedia.org/wiki/Java_Persistence_Query_Language