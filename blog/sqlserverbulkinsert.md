title: Streaming Bulk Inserts to SQL Server with SqlServerBulkInsert
date: 2018-05-05 10:02
tags: dotnet, csharp, sqlserver
category: csharp
slug: sqlserverbulkinsert
author: Philipp Wagner
summary: This article shows how to stream bulk insert data to an SQL Server.

[FcmSharp]: https://github.com/bytefish/FcmSharp
[SqlServerBulkInsert]: https://github.com/bytefish/SqlServerBulkInsert
[Quality Controlled Local Climatological Data]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd
[Airline On-Time Performance Dataset]: https://www.transtats.bts.gov/Tables.asp?DB_ID=120&DB_Name=Airline%20On-Time%20Performance%20Data&DB_Short_Name=On-Time

[SqlServerBulkInsert] is a library for efficient bulk inserts to SQL Server databases in a streaming and non-streaming fashion. 

It wraps the [SqlBulkCopy](https://msdn.microsoft.com/de-de/library/system.data.sqlclient.sqlbulkcopy(v=vs.110).aspx) class behind a nice Fluent API.

## Installing SqlServerBulkInsert ##

You can use [NuGet](https://www.nuget.org) to install [SqlServerBulkInsert]. Run the following command 
in the [Package Manager Console](http://docs.nuget.org/consume/package-manager-console).

```
PM> Install-Package SqlServerBulkInsert
```


## Benchmark Results ##

[Benchmark]: https://github.com/bytefish/SqlServerBulkInsert/blob/master/SqlServerBulkInsert/SqlServerBulkInsert/SqlServerBulkInsert.Test/Integration/BatchSizeIntegrationTest.cs

The [Benchmark] bulk writes 1000000 entities to an SQL Server 2017 database and measures the elapsed time.

```
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 10000, Streaming = True)] Elapsed Time = 00:00:07.92
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 50000, Streaming = True)] Elapsed Time = 00:00:07.32
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 80000, Streaming = True)] Elapsed Time = 00:00:06.65
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 100000, Streaming = True)] Elapsed Time = 00:00:09.00
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 10000, Streaming = False)] Elapsed Time = 00:00:07.59
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 50000, Streaming = False)] Elapsed Time = 00:00:07.13
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 80000, Streaming = False)] Elapsed Time = 00:00:06.90
[BatchExperiment (NumberOfEntities = 1000000, BatchSize = 100000, Streaming = False)] Elapsed Time = 00:00:08.42
```

## Example ##

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using NUnit.Framework;
using System;
using System.Linq;
using System.Collections.Generic;
using System.Data.SqlClient;
using SqlServerBulkInsert.Mapping;
using SqlServerBulkInsert.Test.Base;

namespace SqlServerBulkInsert.Test.Mapping
{
    [TestFixture]
    public class BulkCopyTest : TransactionalTestBase
    {
        /// <summary>
        /// The strongly entity, which is going to be inserted.
        /// </summary>
        private class TestEntity
        {
            public Int32 Int32 { get; set; }
            public String String { get; set; }
        }

        /// <summary>
        /// Holds a TableDefinition and can return the full qualified name.
        /// </summary>
        private class TableDefintion
        {
            public readonly string SchemaName;
            public readonly string TableName;

            public TableDefintion(string schemaName, string tableName)
            {
                SchemaName = schemaName;
                TableName = tableName;
            }

            public string GetFullQualifiedName() 
            {
                return string.Format("[{0}].[{1}]", SchemaName, TableName);
            }
        }

        private class TestEntityMapping : AbstractMap<TestEntity>
        {
            public TestEntityMapping()
                : base("UnitTest", "BulkInsertSample")
            {
                Map("ColInt32", x => x.Int32);
                Map("ColString", x => x.String);
            }
        }

        /// <summary>
        /// The table definition used in the unit test.
        /// </summary>
        private TableDefintion tableDefinition;

        /// <summary>
        /// The SqlServerBulkInsert, which will be tested.
        /// </summary>
        private SqlServerBulkInsert<TestEntity> subject;

        protected override void OnSetupInTransaction()
        {
            tableDefinition = new TableDefintion("UnitTest", "BulkInsertSample");

            subject = new SqlServerBulkInsert<TestEntity>(new TestEntityMapping());

        }

        [Test]
        public void SmallIntMappingTest()
        {
            // Create the Table:
            CreateTable(tableDefinition);

            // Create the Test Data:
            var entity0 = new TestEntity()
            {
                Int32 = 10,
                String = "Hello World"
            };

            var entity1 = new TestEntity()
            {
                Int32 = 20,
                String = "Hello World 2.0"
            };

            // Save the test data as Bulk:
            subject.Write(connection, transaction, new[] { entity0, entity1 });

            // Check if we have inserted the correct amount of rows:
            Assert.AreEqual(2, GetRowCount(tableDefinition));

            // Now get all results and order them by their Int32 value:
            var orderedResults = GetAll(tableDefinition).OrderBy(x => x.Int32).ToArray();

            // And assert the result:
            Assert.AreEqual(10, orderedResults[0].Int32);
            Assert.AreEqual("Hello World", orderedResults[0].String);

            Assert.AreEqual(20, orderedResults[1].Int32);
            Assert.AreEqual("Hello World 2.0", orderedResults[1].String);

        }
     
        private int CreateTable(TableDefintion tableDefinition)
        {
            string cmd = string.Format("CREATE TABLE {0}(ColInt32 int, ColString varchar(50));", tableDefinition.GetFullQualifiedName());

            using (var sqlCommand = new SqlCommand(cmd))
            {
                sqlCommand.Connection = connection;
                sqlCommand.Transaction = transaction;

                return sqlCommand.ExecuteNonQuery();
            }
        }

        private int GetRowCount(TableDefintion tableDefinition)
        {
            string cmd = string.Format("SELECT COUNT(*) FROM {0};", tableDefinition.GetFullQualifiedName());
            using (var sqlCommand = new SqlCommand(cmd))
            {
                sqlCommand.Connection = connection;
                sqlCommand.Transaction = transaction;

                return (Int32) sqlCommand.ExecuteScalar();
            }
        }
        
        private List<TestEntity> GetAll(TableDefintion tableDefinition)
        {
            var results = new List<TestEntity>();
            
            using (var reader = GetAllRaw(tableDefinition))
            {
                while (reader.Read())
                {
                    results.Add(new TestEntity
                    {
                        Int32 = reader.GetInt32(reader.GetOrdinal("ColInt32")),
                        String = reader.GetString(reader.GetOrdinal("ColString"))
                    });
                }
            }

            return results;
        }

        private SqlDataReader GetAllRaw(TableDefintion tableDefinition)
        {
            string cmd = string.Format("SELECT * FROM {0};", tableDefinition.GetFullQualifiedName());
            using (var sqlCommand = new SqlCommand(cmd))
            {
                sqlCommand.Connection = connection;
                sqlCommand.Transaction = transaction;

                return sqlCommand.ExecuteReader();
            }
        }
    }
}
```

## On Side Projects ##

You may have noticed, that I also updated [FcmSharp] to the new Firebase HTTP v1 API. I am currently updating some more libraries, because they are 
feasible side projects to do. I worked on the recent Graph Database articles too long. 

The original plan for the Graph Database articles was to also do some data mining on the datasets. The plan was to use the 
[Airline On Time Performance Dataset] to identify the flights delayed by weather first. Then I wanted to use the 
[Quality Controlled Local Climatological Data] to see, if I can build a statistical model for predicting delayed flights.

This turned out to be a way too big side project, so I am scaling my plans a little down for future projects.