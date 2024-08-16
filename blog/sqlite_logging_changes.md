title: Auditing and Versioning Data in SQLite
date: 2024-08-16 09:04
tags: sqlite, sql
category: sqlite
slug: sqlite_logging_changes
author: Philipp Wagner
summary: This article shows how to log changes to tables in SQLite.

I am working on a small SQLite project as a learning excercise, so that I 
know its capabilities and its limitations, when it comes to putting it in 
production.

There's a requirement, that almost every project has and that's versioning 
and auditing of data changes. How could we do this with SQLite? Is it possible 
without application code?

All code can be found in a Git repository at:

* [https://github.com/bytefish/SQLiteFulltextSearch](https://github.com/bytefish/SQLiteFulltextSearch)

## Table of contents ##

[TOC]

## What is SQLite? ##

SQLite is ... 

> SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, 
> full-featured, SQL database engine. SQLite is the most used database engine in the world. SQLite 
> is built into all mobile phones and most computers and comes bundled inside countless other 
> applications that people use every day. 

But you cannot compare SQLite to a client/server database, such as PostgreSQL or SQL 
Server. SQLite tries to provide local data storage for applications, rather than providing 
a shared repository for all your enterprise data. Keep that in mind!

The documentation says ...

> SQLite does not compete with client/server databases. SQLite competes with fopen().

I think it of like this: SQLite is married to your application and not to your enterprise. It 
doesn't aim at replacing your PostgreSQL or SQL Server instances, and relies on your application 
as being a fully-fledged programmable database engine.

There's nothing like a Stored Procedures in SQLite, that you could write. There are no variables 
to allow for complex business logic inside SQLite. Although you could plugin your own C Extensions, 
you cannot write functions in SQL.

## Why Auditing Data Changes? ##

"Oh No! Help!!!! I've accidentally deleted all my data! The work of weeks is gone! 
Everything is lost! How could we revert my changes?". That's a common theme, you'll 
find in every sufficiently complex user-facing application.

And this could happen in a client/server situation, just like it could happen for the 
local use of SQLite. I want to prevent this to happen right from the start, when dealing 
with new SQLite applications. 

So let's take a look at it!

## Problem: There's no notion of Transaction Time in SQLite ##

My initial thought was this: I'll just grab the time of the transaction, use some triggers 
to write a `valid_from` and `valid_to` column and call it a day! Oh, that was naive.

See, if you take a look at how SQL Server implements their Temporal Tables, you'll see, that 
the validity of a row is depending on the *Transaction Time* (`SysStartTime`). So if you execute 
data changes to multiple rows, you are guaranteed, that all those changes have the same stable 
time of the transaction:

* [https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-table-usage-scenarios?view=sql-server-ver16](https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-table-usage-scenarios?view=sql-server-ver16)

Sadly SQLite doesn't have a notion of *Transaction Time*, that stays stable for the entire 
transaction. Functions like `CURRENT_TIMESTAMP` or `strftime('%Y-%m-%d %H:%M:%f', 'now')` 
are stable only within a *Statement*.

That means something like this:

```sql
INSERT INTO myTable(date1 text, date2 text)
VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
```

Would yield the same `CURRENT_TIMESTAMP` for both columns.

But if, say, you have two `AFTER UPDATE` triggers using the `CURRENT_TIMESTAMP`: 

```sql
CREATE TRIGGER IF NOT EXISTS tableA_update_trigger
    AFTER UPDATE ON tableA FOR EACH ROW
BEGIN
        
    UPDATE 
        tableA
    SET 
        valid_from = CURRENT_TIMESTAMP
    WHERE 
        rowid = NEW.rowid;
    
END;

CREATE TRIGGER IF NOT EXISTS tableB_update_trigger
    AFTER UPDATE ON tableB FOR EACH ROW
BEGIN
        
    UPDATE 
        tableB
    SET 
        valid_from = CURRENT_TIMESTAMP
    WHERE 
        rowid = NEW.rowid;
    
END;
```

The `CURRENT_TIMESTAMP` for both triggers will differ, depending on how long each trigger runs. And worse it's 
non-deterministic to say who comes first, because you can not rely on triggers to be executed in order.

There has actually been some work in the SQLite repository on providing a stable transaction time:

* [https://sqlite.org/forum/forumpost/b20010f8a9d45fde?t=h](https://sqlite.org/forum/forumpost/b20010f8a9d45fde?t=h)

But it has been reverted, because of it's not easy to define what a Transaction in SQLite *actually means*. Dr. 
Richard Hipp, the primary author of SQLite, writes ...

> [...]
>
> Part of the problem is that SQLite does not have the concept of a transaction at the database connection 
> level. Individual database files are either in a transaction or not. But a single SQLite database connection 
> can be talking to multiple database files at once. So how do we define a connection-level transaction? 
>
> Is it when one or more files have an active transaction? Do read-transactions count, or should we only count 
> write-transactions? What do you do with the VALUES statement that does no database I/O?
> 
> These problems don't come up as severely with client/server database engines because client/server systems 
> are not re-entrant in the way that SQLite is. The TCL script above is able to start and run new SQL statements 
> in the middle of other SQL statements. By contrast, SQL statements in a single PostgreSQL database connection 
> are strictly serialized - one must run to completion before the next one starts by virtual of the client/server 
> protocol.

There it is... I've researched it for you.

## Audit Changes with Triggers ##

It's a good thing to know your limitations, so we are not operating on false premises. Since we don't have 
a 100% accurate *transaction time* (and don't have access to a *transaction id*) inside SQLite, it's impossible 
to know exactly which historic entries belong together.

Still I think it's useful to audit the changes to our data, so we can still do data forensics and *maybe* 
revert changes to a previous row version. I like to show with an example how it could be done.

We start by defining a table `suggestion`, that looks like this:

```sql
CREATE TABLE IF NOT EXISTS suggestion (
    suggestion_id integer PRIMARY KEY AUTOINCREMENT,
    name text not null
        CHECK (length(name) <= 255),
    last_edited_by integer not null,
    row_version integer default 1,
    valid_from text not null default (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    valid_to text null default '9999-12-31',
    CONSTRAINT suggestion_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES user(user_id) 
);
```

All changes to the data will be written into a `suggestion_history` table:

```sql
CREATE TABLE IF NOT EXISTS suggestion_history (
    suggestion_history_id integer PRIMARY KEY AUTOINCREMENT,
    suggestion_id integer,
    name text not null,
    last_edited_by integer not null,
    row_version integer,
    valid_from text not null,
    valid_to text not null
);
```

We'll need to track `UPDATE` and `DELETE` operations. An `INSERT` doesn't go into the historic 
table, because it's the *current* view on the data and there's nothing to go into the history, 
right?

```sql
-- History Triggers "suggestion"
CREATE TRIGGER IF NOT EXISTS suggestion_update_trigger
    AFTER UPDATE ON suggestion FOR EACH ROW
BEGIN

    INSERT INTO 
        suggestion_history(suggestion_id, name, last_edited_by, row_version, valid_from, valid_to)
    SELECT 
        OLD.suggestion_id, OLD.name, OLD.last_edited_by, OLD.row_version, OLD.valid_from, strftime('%Y-%m-%d %H:%M:%f', 'now');

    UPDATE 
        suggestion
    SET 
        row_version = row_version + 1,
        valid_from = (SELECT valid_to FROM suggestion_history WHERE suggestion_history_id = last_insert_rowid())
    WHERE 
        rowid = NEW.rowid;

END;

CREATE TRIGGER IF NOT EXISTS suggestion_delete_trigger
    AFTER DELETE ON suggestion FOR EACH ROW
BEGIN
    INSERT INTO 
        suggestion_history(suggestion_id, name, last_edited_by, row_version, valid_from, valid_to)
    SELECT
        suggestion_id, name, last_edited_by, row_version, valid_from, strftime('%Y-%m-%d %H:%M:%f', 'now');
END;
```

We now start a new SQLite database:

```
> sqlite3 sample.db
```

And copy and paste all the above statements into it, then we'll add some data:

```sql
INSERT INTO 
    suggestion(suggestion_id, name, last_edited_by)
VALUES 
    (1, 'Machine Learning with OpenCV', 1);
```

And we can see, that the entry with a `valid_from` and `valid_to` timestamp has been 
written. The `row_version` is set to `1` initially:

```sql
sqlite> SELECT * FROM suggestion; 
1|Machine Learning with OpenCV|1|1|2024-08-16 06:47:13.199|9999-12-31
```

The `suggestion_history` table is still empty:

```sql
sqlite> SELECT count(*) FROM suggestion_history;
0
```

Let's now update the suggestion to `OpenCV Machine Learning Guide`:

```sql
sqlite> UPDATE suggestion SET name='OpenCV Machine Learning Guide' WHERE suggestion_id = 1;
```

We can see, that the `suggestion` now has a new `valid_from` timestamp and the `row_version` has been increased to `2`:

```sql
sqlite> SELECT * FROM suggestion where suggestion_id = 1;
1|OpenCV Machine Learning Guide|1|2|2024-08-16 06:50:13.874|9999-12-31
```

The `suggestion_history` now contains the previous version of the data, also showing the validity of the row:

```sql
sqlite> SELECT * FROM suggestion_history where suggestion_id = 1;
1|1|Machine Learning with OpenCV|1|1|2024-08-16 06:47:13.199|2024-08-16 06:50:13.874
```

Updating it again to the previous values shows, that the change is also audited:

```sql
sqlite> UPDATE suggestion SET name='Machine Learning with OpenCV' WHERE suggestion_id = 1;
sqlite> SELECT * FROM suggestion_history where suggestion_id = 1;
1|1|Machine Learning with OpenCV|1|1|2024-08-16 06:47:13.199|2024-08-16 06:50:13.874
2|1|OpenCV Machine Learning Guide|1|2|2024-08-16 06:50:13.874|2024-08-16 06:54:54.487
```

And that's it!

## Conclusion ##

I am not sure, that I am arriving at the correct conclusions here. 

It's not possible to provide an equivalent to Temporal Tables from within SQLite, because 
it lacks a stable transaction time to be used throughout multiple triggers. You could come 
up with some workarounds, but I fear they introduce a new set of problems.

What I came up with in this article is probably *good enough* for a wide range of projects, at 
least those I aiming for. You cannot do time-travel with it or restore the data to a previous 
version with 100% certainity (you could do a "best guess" though 🤷‍♂️).

But you have everything logged, and that's a big plus for doing data forensics.