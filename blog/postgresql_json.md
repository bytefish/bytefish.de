title: JSON Generation with PostgreSQL
date: 2015-03-08 12:54
tags: sql
category: sql
slug: postgresql_json
author: Philipp Wagner

[json_functions]: http://www.postgresql.org/docs/current/static/functions-json.html
[json_build_object]: http://www.postgresql.org/docs/current/static/functions-json.html
[json_agg]: http://www.postgresql.org/docs/9.3/static/functions-aggregate.html
[createdb]: http://www.postgresql.org/docs/8.4/static/app-createdb.html

PostgreSQL 9.4 comes with a set of features for generating and querying [JSON][json_functions] documents. This post deals with 
generating JSON data from a relational schema. We are building a tiny database application for managing images with associated 
tags and comments.

You can get the scripts in this article from:

* [https://github.com/bytefish/bytefish.de/tree/master/code/pgsample](https://github.com/bytefish/bytefish.de/tree/master/code/pgsample)

## User and Database  ##

First of all we need to create the ``sampledb`` database for this article. You connect to your local PostgreSQL instance as the 
default user *postgres* (or any other user with administrative rights) and create a new user and database.

```
PS C:\Users\philipp> psql -U postgres
psql (9.4.1)
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
postgres=# CREATE DATABASE sampledb
postgres-#   WITH OWNER philipp;
CREATE DATABASE
```

## create_database.cmd ##

I have seen a lot of tutorials, which require you to copy and paste DDL scripts. This might work for very small applications, 
but it won't scale for any real project. You need to automate the task of creating and migrating a database as early as possible 
in your project.

I am working in a Windows environment right now, so I have used a [Batch](http://en.wikipedia.org/wiki/Batch_file) file to automate 
the database setup. There is no magic going on, I am just setting the path to ``psql`` and use the ``PGPASSWORD`` environment variable 
to pass the password to the command line.

```bat
@echo off

set PGSQL_EXECUTABLE="C:\Program Files\PostgreSQL\9.4\bin\psql.exe"
set STDOUT=stdout.log
set STDERR=stderr.log
set LOGFILE=query_output.log

set HostName=localhost
set PortNumber=5432
set DatabaseName=sampledb
set UserName=philipp
set Password=

call :AskQuestionWithYdefault "Use Host (%HostName%) Port (%PortNumber%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y] (
	set /p HostName="Enter HostName: "
	set /p PortNumber="Enter Port: "
)

call :AskQuestionWithYdefault "Use Database (%DatabaseName%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y]  (
	set /p ServerName="Enter Database: "
)

call :AskQuestionWithYdefault "Use User (%UserName%) [Y,n]?" reply_
if /i [%reply_%] NEQ [y]  (
	set /p UserName="Enter User: "
)

set /p PGPASSWORD="Password: "

1>stdout.log 2>stderr.log (
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 01_create_schema.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 02_create_tables.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 03_create_keys.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 04_create_functions.sql -L %LOGFILE%
)

goto :end

:: The question as a subroutine
:AskQuestionWithYdefault
	setlocal enableextensions
	:_asktheyquestionagain
	set return_=
	set ask_=
	set /p ask_="%~1"
	if "%ask_%"=="" set return_=y
	if /i "%ask_%"=="Y" set return_=y
	if /i "%ask_%"=="n" set return_=n
	if not defined return_ goto _asktheyquestionagain
	endlocal & set "%2=%return_%" & goto :EOF

:end
pause
```

We can execute this script to create the database schema. Now let's write the SQL scripts!

## 01_create_schema.sql ##

I am using [Schemas](http://www.postgresql.org/docs/8.2/static/ddl-schemas.html) to keep my database organized, and so should you! The next statements
will create the schema ``im`` if it is not available in the database.

```
DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'im') THEN

  CREATE SCHEMA im;

END IF;

END;
$$;
```

## 02_create_tables.sql ##

Next we'll create the tables. We want to manage **Images**, **Tags** and **Comments** in our database. An **Image** consist of a *Hash*, *Description* 
and a *Creation date*. Each image can be associated with many tags, a tag can be associated with many images. That's a many-to-many relationship, so we 
need a mapping table. Finally each image can have multiple comments, a one-to-many relation with a foreign key on the comments side.

```
DO $$
BEGIN

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'image'
) THEN

CREATE TABLE im.Image
(
	ImageID SERIAL PRIMARY KEY,
	Hash VARCHAR(64) NOT NULL,
	Description VARCHAR(2000) NULL,
	CreatedOn TIMESTAMP WITHOUT TIME ZONE DEFAULT(NOW() AT TIME ZONE 'utc')
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'tag'
) THEN

CREATE TABLE im.Tag
(
	TagID SERIAL PRIMARY KEY,
	Name VARCHAR(255) NOT NULL
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'image_tag'
) THEN

CREATE TABLE im.Image_Tag
(
	ImageID INTEGER NOT NULL,
	TagID INTEGER NOT NULL,
	PRIMARY KEY (ImageID, TagID)  
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'im' 
	AND table_name = 'comment'
) THEN

CREATE TABLE im.Comment
(
	CommentID SERIAL PRIMARY KEY,
	ImageID INTEGER NOT NULL,
	Text VARCHAR(2000) NOT NULL,
	CreatedOn TIMESTAMP WITHOUT TIME ZONE DEFAULT(NOW() AT TIME ZONE 'utc')
);

END IF;

END;
$$;
```

## 03_create_keys.sql ##

And what's a database without referential integrity?

```
DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'image_tag_imageid_fkey') THEN
	ALTER TABLE im.image_tag
		ADD CONSTRAINT image_tag_imageid_fkey
		FOREIGN KEY (ImageID) REFERENCES im.Image(ImageID);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'image_tag_tagid_fkey') THEN
	ALTER TABLE im.image_tag
		ADD CONSTRAINT image_tag_tagid_fkey
		FOREIGN KEY (TagID) REFERENCES im.Tag(TagID);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'comment_imageid_fkey') THEN
	ALTER TABLE im.comment
		ADD CONSTRAINT comment_imageid_fkey
		FOREIGN KEY (ImageID) REFERENCES im.Image(ImageID);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_tag_name') THEN
	ALTER TABLE im.tag
		ADD CONSTRAINT uk_tag_name
		UNIQUE (Name);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_image_hash') THEN
	ALTER TABLE im.Image
		ADD CONSTRAINT uk_image_hash
		UNIQUE (Hash);
END IF;

END;
$$;
```

## Data ##

It's hard to run useful queries without data, so let's populate the database!

```sql
-- Populate Image Database

INSERT INTO im.image(imageid, hash, description)
    VALUES (1, 'a3b0c44', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (2, 'a9b0c44', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (3, 'e3b0c44', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (4, 'a3c0c74', 'Some Description');

INSERT INTO im.image(imageid, hash, description)
    VALUES (5, 'e301244', 'Some Description');
    
INSERT INTO im.image(imageid, hash, description, createdon)
    VALUES (6, 'e301214', 'Some Description', '2014-03-09T22:00:00.132');

-- Populate Tag Database

INSERT INTO im.tag (tagid, name)
    VALUES (1, 'Cool');

INSERT INTO im.tag (tagid, name)
    VALUES (2, 'Berlin');

INSERT INTO im.tag (tagid, name)
    VALUES (3, 'Erlang');

-- Assign Images
INSERT INTO im.image_tag (imageid,tagid)
    VALUES (1,1);

INSERT INTO im.image_tag (imageid,tagid)
    VALUES (1,2);

INSERT INTO im.image_tag (imageid, tagid)
    VALUES (2,1);
    
INSERT INTO im.image_tag (imageid, tagid)
    VALUES (2,3);

-- Comments
INSERT INTO im.comment (commentid, imageid, text)
	VALUES(1, 1, 'Awesome!');

INSERT INTO im.comment (commentid, imageid, text)
	VALUES(2, 1, 'This is just a second comment.');
```

## 04_create_functions.sql ##

Now we can finally get some JSON out of this database! PostgreSQL 9.3 introduced a new aggregate function [json_agg], to aggregate
values (of any type) into a JSON array. The following query uses ``json_agg`` to get a list of all tags available.

```sql
SELECT json_agg(r.*) as tags
FROM (SELECT tagid, name from im.tag) AS r;
```

Result:

```
              tags
--------------------------------
 [{"tagid":1,"name":"Cool"},   +
  {"tagid":2,"name":"Berlin"}, +
  {"tagid":3,"name":"Erlang"}]

(1 row)
```

While it's nice to build a JSON representation of our relational data with [json_agg], it's going to get tedious for more complex objects. So [json_build_object] was introduced in 
PostgreSQL 9.4 and it can be used to build arbitrarily complex json trees. ``json_build_object`` takes a variadic arguments, where the argument list consists of alternating 
key-value pairs. 

Let's write the function to pull an image with associated tags and comments off the database. Note how ``json_agg`` and ``json_build_object`` are used to build the final result.

```postgresql
-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns an image by id.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_image(image_id int) RETURNS json AS 
$BODY$
DECLARE
  found_image im.image;
  image_tags json;
  image_comments json;
BEGIN
  -- Load the image data:
  SELECT * INTO found_image 
  FROM im.image i 
  WHERE i.imageid = image_id;  
  
  -- Get assigned tags:
  SELECT CASE WHEN COUNT(x) = 0 THEN '[]' ELSE json_agg(x) END INTO image_tags 
  FROM (SELECT t.* 
        FROM im.image i
        INNER JOIN im.image_tag it ON i.imageid = it.imageid
        INNER JOIN im.tag t ON it.tagid = t.tagid
        WHERE i.imageid = image_id) x;

  -- Get assigned comments:
  SELECT CASE WHEN COUNT(y) = 0 THEN '[]' ELSE json_agg(y) END INTO image_comments 
  FROM (SELECT * 
        FROM im.comment c 
        WHERE c.imageid = image_id) y;

  -- Build the JSON Response:
  RETURN (SELECT json_build_object(
    'imageid', found_image.imageid,
    'hash', found_image.hash,
    'description', found_image.description,
    'created_on', found_image.createdon, 
    'comments', image_comments,
    'tags', image_tags));

END
$BODY$
LANGUAGE 'plpgsql';
```

You can now call ``im.get_image`` with an ImageID.

```sql
select im.get_image(1);
```

The result set contains an image with two comments and two tags:

```
                get_image
--------------------------------------------------------------
 {"imageid" : 1, 
  "hash" : "a3b0c44", 
  "description" : "Some Description", 
  "created_on" : "2015-03-09T22:00:45.111", 
  "comments" : [{"commentid":1, "imageid":1, "text":"Awesome!", "createdon":"2015-03-09T22:58:47.783"},
                {"commentid":2, "imageid":1, "text":"This is just a second comment.", "createdon" : "2015-03-09T22:58:47.783"}], 
  "tags" : [{"tagid":1,"name":"Cool"}, 
            {"tagid":2,"name":"Berlin"}]}
(1 row)
```

Once we have defined the ``get_image`` function, we can build upon it quite easily. 

You probably want to get the set of images, which belong to a given list of tags. We can easily define a function with a variable 
number of arguments by using the ``VARIADIC`` keyword.

```postgresql
-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns the (distinct) set of images matching the given tags.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_image_by_tag(VARIADIC tags varchar[]) RETURNS SETOF json AS 
$BODY$
BEGIN

    RETURN QUERY
    SELECT im.get_image(x.imageid)
    FROM (SELECT DISTINCT i.imageid as imageid
          FROM im.image i
            INNER JOIN im.image_tag it on i.imageid = it.imageid
            INNER JOIN im.tag t on t.tagid = it.tagid
          WHERE t.name = ANY(tags)) x;

END
$BODY$
LANGUAGE 'plpgsql';
```

The function returns two rows for the tags ``Cool`` and ``Erlang`` (ImageID: ``[1, 2]``).

```
sampledb=> select count(r.*) from (select im.get_image_by_tag('Cool', 'Erlang')) r;
 count
-------
     2
(1 row)
```

Or if you only want to get images added in a given timespan, you can use the interval data type.

```postgresql
-----------------------------------------------------------------------
-- 2015/03/08 Philipp Wagner
--
-- Returns the images in added between now() and now() - interval.
-----------------------------------------------------------------------
CREATE OR REPLACE FUNCTION im.get_latest(timespan interval) RETURNS SETOF json AS 
$BODY$
BEGIN
    
    RETURN QUERY
    SELECT im.get_image(i.imageid)
    FROM im.image i
    WHERE i.createdon > (NOW() - timespan);
    
END
$BODY$
LANGUAGE 'plpgsql';
```

Querying the results in the last month will return 5 images only.

```
sampledb=> select count(l.*) from (select im.get_latest(interval '1 month')) l;
 count
-------
     5
(1 row)
```