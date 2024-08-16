title: Experimenting with SQLite FTS5
date: 2024-08-10 10:25
tags: sqlite, sql
category: sql
slug: experimenting_with_sqlite_fts5
author: Philipp Wagner
summary: This article shows how to work with the SQLite FTS5 module.

I am working on a sample application using SQLite and FTS5 for Full Text Search. So 
I have experimented with the SQLite FTS5 extension. This is a short write up on it.

## Table of contents ##

[TOC]

## Database Schema ##

We want to model some kind of document management system, that allows us to upload documents 
to and add some metadata, such as suggestions and keywords.

### Tables ###

So we start by adding the tables.

```sql
-- Tables
CREATE TABLE IF NOT EXISTS user (
    user_id integer PRIMARY KEY AUTOINCREMENT,
    email text not null
        CHECK (length(email) <= 1000),
    preferred_name text not null
        CHECK (length(preferred_name) <= 1000),
    last_edited_by integer not null,
    row_version integer default 1,
    valid_from text not null default (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    valid_to text null default '9999-12-31',
    CONSTRAINT user_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES user(user_id)
);

CREATE TABLE IF NOT EXISTS document (
    document_id integer PRIMARY KEY AUTOINCREMENT,
    title text not null
        CHECK (length(title) <= 1000),
    filename text not null
        CHECK (length(filename) <= 1000),
    data blob null,
    last_edited_by integer not null,
    row_version integer default 1,
    valid_from text not null default (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    valid_to text null default '9999-12-31',
    CONSTRAINT document_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES user(user_id)

);

CREATE TABLE IF NOT EXISTS keyword (
    keyword_id integer PRIMARY KEY AUTOINCREMENT,
    name text not null
        CHECK (length(name) <= 255),
    last_edited_by integer not null,
    row_version integer default 1,
    valid_from text not null default (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    valid_to text null default '9999-12-31',
    CONSTRAINT keyword_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES user(user_id)
);

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
        REFERENCES user(user_id),
    CHECK (length(name) <= 255) 
);

CREATE TABLE IF NOT EXISTS document_keyword (
    document_keyword_id integer PRIMARY KEY AUTOINCREMENT,
    document_id int not null,
    keyword_id int not null,
    last_edited_by integer not null,
    row_version integer default 1,
    valid_from text not null default (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    valid_to text null default '9999-12-31',
    CONSTRAINT document_keyword_document_id_fkey 
        FOREIGN KEY (document_id)
        REFERENCES document(document_id),
    CONSTRAINT document_keyword_keyword_id_fkey 
        FOREIGN KEY (keyword_id)
        REFERENCES keyword(keyword_id),
    CONSTRAINT document_keyword_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES user(user_id)
);

CREATE TABLE IF NOT EXISTS document_suggestion (
    document_suggestion_id integer PRIMARY KEY AUTOINCREMENT,
    document_id int not null,
    suggestion_id int not null,
    last_edited_by integer not null,
    row_version integer default 1,
    valid_from text not null default (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    valid_to text null default '9999-12-31',
    CONSTRAINT document_suggestion_document_id_fkey 
        FOREIGN KEY (document_id)
        REFERENCES document(document_id),
    CONSTRAINT document_suggestion_suggestion_id_fkey 
        FOREIGN KEY (suggestion_id)
        REFERENCES suggestion(suggestion_id),
    CONSTRAINT document_suggestion_last_edited_by_fkey 
        FOREIGN KEY (last_edited_by)
        REFERENCES user(user_id)
);
```

## Create and use the FTS5 table ##

We can then create a virtual table for the document search using the `fts5` function: 

```sql
-- FTS5 Document Search Table
CREATE VIRTUAL TABLE fts_document 
    USING fts5(title, content);
```

And we can then insert the sample data:

```sql
-- Sample Data
INSERT INTO user(user_id, email, preferred_name, last_edited_by) 
    VALUES 
        (1, 'philipp@bytefish.de', 'Data Conversion User', 1);

-- Document "Machine Learning with OpenCV"
INSERT INTO 
    document(document_id, title, filename, last_edited_by)
VALUES 
    (1, 'Machine Learning with OpenCV', 'machinelearning.pdf', 1);
    
INSERT INTO 
    keyword(keyword_id, name, last_edited_by)
VALUES 
    (1, 'Machine Learning', 1);
    
INSERT INTO 
    keyword(keyword_id, name, last_edited_by)
VALUES 
    (2, 'OpenCV', 1);
    
INSERT INTO 
    document_keyword(document_keyword_id, document_id, keyword_id, last_edited_by)
VALUES 
    (1, 1, 1, 1);
    
INSERT INTO 
    document_keyword(document_keyword_id, document_id, keyword_id, last_edited_by)
VALUES 
    (2, 1, 2, 1);

INSERT INTO 
    document_keyword(document_keyword_id, document_id, keyword_id, last_edited_by)
VALUES 
    (2, 1, 2, 1);
    
INSERT INTO 
    suggestion(suggestion_id, name, last_edited_by)
VALUES 
    (1, 'Machine Learning with OpenCV', 1);
    
INSERT INTO 
    document_suggestion(document_suggestion_id, document_id, suggestion_id, last_edited_by)
VALUES 
    (1, 1, 1, 1);

-- Insert document data        
INSERT INTO 
    fts_document(rowid, title, content)
VALUES
    (1, 'Machine Learning with OpenCV', concat('This document covers the Machine Learning API of the OpenCV2 C++ API.'
            ,' It helps you with setting up your system, gives a brief introduction into Support Vector Machines'
            ,' and Neural Networks and shows how it’s implemented with OpenCV.')),
    (2, 'Face Recognition with GNU Octave/MATLAB', concat('In this document I’ll show you how to implement the Eigenfaces [13] and Fisherfaces [3] method'
            ,' with GNU Octave/MATLAB , so you’ll understand the basics of Face Recognition. All concepts'
            , ' are explained in detail, but a basic knowledge of GNU Octave/MATLAB is assumed.'));
            
```

And finally we can write a simple query to get results matching `OpenCV`, with a snippet included. 

We want to load related data, so we use SQLite's `json_object` and `json_group_array` functions:

```sql
-- Query for all documents matching "OpenCV"
WITH documents_cte AS 
(
    SELECT f.rowid document_id, 
        snippet(f.fts_document, 0, 'match→', '←match', '', 32) match_title, 
        snippet(f.fts_document, 1, 'match→', '←match', '', 32) match_content
    FROM 
        fts_document f
    WHERE 
        f.fts_document MATCH '{title content}: OpenCV' 
    ORDER BY f.rank
) 
SELECT json_object(
    'document_id', documents_cte.document_id,
    'match_title', documents_cte.match_title,
    'match_content', documents_cte.match_content,
    'keywords', (
        SELECT json_group_array(k.name)
        FROM document_keyword dk
            INNER JOIN keyword k on dk.keyword_id = k.keyword_id
        WHERE 
            dk.document_id = documents_cte.document_id
     ),
     'suggestions', (
        SELECT json_group_array(s.name)
        FROM document_suggestion ds
            INNER JOIN suggestion s on ds.suggestion_id = s.suggestion_id
        WHERE 
            ds.document_id = documents_cte.document_id
     )    
)
FROM documents_cte; 
```

And it yields the match with the documents metadata included. 

```json
{
  "document_id": 1,
  "match_title": "Machine Learning with match→OpenCV←match",
  "match_content": "It helps you with setting up your system, gives a brief introduction into Support Vector Machines and Neural Networks and shows how it’s implemented with match→OpenCV←match.",
  "keywords": [ "Machine Learning", "OpenCV" ],
  "suggestions": [ "Machine Learning with OpenCV" ]
}
```