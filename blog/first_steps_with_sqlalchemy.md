title: First steps with SQLAlchemy
date: 2014-12-21 21:08
tags: python, sqlalchemy
category: python
slug: first_steps_with_sqlalchemy
author: Philipp Wagner

I am working on a small RESTful Web service with [Flask](http://flask.pocoo.org/), and I am currently evaluating 
[SQLAlchemy](http://sqlalchemy.org) for the database persistence. It's the first time I am using [SQLAlchemy](http://sqlalchemy.org) 
and I want to start with a tiny example.

[Flask]: http://flask.pocoo.org
[SQLAlchemy]: http://sqlalchemy.org
[virtualenv]: https://virtualenv.pypa.io
[ipython]: http://ipython.org
[pip]: https://pip.pypa.io

## Prerequisites ##

### virtualenv ###

I like working with [virtualenv](https://virtualenv.pypa.io), because it keeps your Python installation clean and
prevents you from messing around with Package dependencies. You can install [virtualenv] with [pip] (administrative 
privileges may be required):

```
pip install virtualenv
```

Once you have installed [virtualenv], decide where you want to create the virtual environments at. ``virtualenv`` normally 
creates environments in the current working directory. I have created a separate folder ``virtualenv``, where my Python 
environments go to.

To create the ``sqlalchemy`` virtual environment for this tutorial simply type:

```
PS D:\virtualenv> virtualenv sqlalchemy
New python executable in sqlalchemy\Scripts\python.exe
Installing setuptools, pip...done.
```

``virtualenv`` created a new directory ``sqlalchemy`` and the scripts to activate the virtual environment:

```
PS D:\virtualenv> .\sqlalchemy\Scripts\activate
```

The virtual environment is activated and the name of the virtual environment is prepended to the command line prompt:

```
(sqlalchemy) PS D:\virtualenv>
```

### ipython ###

[ipython] is an *amazing* command shell for Python. I use it for all my Python development and you can also use it for this tutorial.

Install [ipython] with:

```
pip install ipython
```

Then simply start it. And whenever you see a code snippet in this tutorial, you can copy it to the clipboard and then use ipythons [paste magic]:

```
>>> %paste
```

[paste magic]: http://ipython.org/ipython-doc/dev/interactive/tutorial.html


### sqlalchemy ###

Finally install [SQLAlchemy] with:

```
pip install SQLAlchemy
```

## SQLAlchemy ##

Every sufficiently complex application needs to persist data, and there are a million ways to persist data. You could use a flat 
file, a [document-oriented approach][3] or a [Relational database][4]. [SQLAlchemy](http://sqlalchemy.org), as the name implies, 
is a SQL Toolkit and Object-Relational Mapper. 

### Scope of this Article ###

The scope of this article is an introduction to [SQLAlchemy]. It's not a complete guide and it does not cover any essential parts for 
real database access, like sessions, [caching], database migrations or any other advanced topics. It is only meant to be a quick 
introduction and show how to build mapping tables and query data with [SQLAlchemy]. 

[caching]: http://docs.sqlalchemy.org/en/rel_0_9/orm/examples.html#beaker-caching

## The Example ##

The database application we are going to build should persist images with associated likes, tags and comments. In a later article I want to 
use it to build a small Web service around it.

So let's take look at the entities first. An image consist of a UUID and its associated number of likes. Each image can be associated with 
many tags, a tag can be associated with many images. That's a many-to-many relationship, so we need a mapping table. Finally each image can 
have multiple comments, a one-to-many relation with a foreign key on the comments side.

### Model ###

This tutorial uses the declarative extensions of SQLAlchemy. ``declarative_base`` is a factory function, that returns a base class 
(actually a metaclass), and the entities are going to inherit from it. Once the definition of the class is done, the Table and mapper 
will be generated automatically. There is some magic involved, but on the other hand SQLAlchemy forces you to explicitly define things like 
the table name, primary keys and relationships.

First create the ``Base`` class:

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

The entities are classes, which derive from the ``Base`` class. We are also using the ``relationship`` function to define the 
relationships between the entities. The many-to-many relationship between tags and images requires us to define an association 
table, which we'll be joining over. 

When defining the ``images`` relationships, we are also using the ``backref`` parameter, which adds the image properties to the 
``tags`` and ``comments`` entities. We want those references to be dynamically loaded, because we probably don't want to load all
images, when accessing these entities.

The code is relatively straightforward to read:

```python
from datetime import datetime, timedelta
from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

tags = Table('tag_image', Base.metadata,
    Column('tag_id', Integer, ForeignKey('tags.id')),
    Column('image_id', Integer, ForeignKey('images.id'))
)
 
class Image(Base):
    
    __tablename__ = 'images'
    
    id          =   Column(Integer, primary_key=True)
    uuid        =   Column(String(36), unique=True, nullable=False)
    likes       =   Column(Integer, default=0)
    created_at  =   Column(DateTime, default=datetime.utcnow)
    tags        =   relationship('Tag', secondary=tags, 
                        backref = backref('images', lazy='dynamic'))
    comments    =   relationship('Comment', backref='image', lazy='dynamic')
    
    def __repr__(self):
        str_created_at = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return "<Image (uuid='%s', likes='%d', created_at=%s)>" % (self.uuid, self.likes, str_created_at)

class Tag(Base):
    
    __tablename__ = 'tags'
    
    id      =   Column(Integer, primary_key=True)
    name    =   Column(String(255), unique=True, nullable=False)
    
    def __repr__(self):
        return "<Tag (name='%s')>" % (self.name)

class Comment(Base):
    
    __tablename__ = 'comments'
    
    id          =   Column(Integer, primary_key=True)
    text        =   Column(String(2000))
    image_id    =   Column(Integer, ForeignKey('images.id'))
    
    def __repr__(self):
        return "<Comment (text='%s')>" % (self.text)
```

### Connecting and Creating the Schema ###

First of all we need to create the engine, which is used to connect to the database. This example uses SQLite3, which
should already be included in your Python installation.

```python
from sqlalchemy import create_engine

engine = create_engine('sqlite:///:memory:', echo=True)
```

A call to the metadata of the ``Base`` class then generates the Schema:

```
Base.metadata.create_all(engine)
```

Since we have set ``echo=True`` for the engine, we can see the generated SQL:

```sql
CREATE TABLE tags (
        id INTEGER NOT NULL,
        name VARCHAR(255) NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (name)
)

COMMIT

CREATE TABLE images (
        id INTEGER NOT NULL,
        uuid VARCHAR(36) NOT NULL,
        likes INTEGER,
        created_at DATETIME,
        PRIMARY KEY (id),
        UNIQUE (uuid)
)

COMMIT

CREATE TABLE tag_image (
        tag_id INTEGER,
        image_id INTEGER,
        FOREIGN KEY(tag_id) REFERENCES tags (id),
        FOREIGN KEY(image_id) REFERENCES images (id)
)

COMMIT

CREATE TABLE comments (
        id INTEGER NOT NULL,
        text VARCHAR(2000),
        image_id INTEGER,
        PRIMARY KEY (id),
        FOREIGN KEY(image_id) REFERENCES images (id)
)
COMMIT
```

### Sessions ###

A [Session] is a Python class, which handles the conversation with the database for us. It implements the [Unit of Work] pattern
for synchronizing changes to the database. Basically it tracks all records you add or modify. We can acquire a Session class with 
the [sessionmaker], which simplifies the configuration, since we only bind our database engine to it:

```python
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
```

And now whenever we want to talk to the database, we can create a new [Session]:

```python
session = Session()
```

[Session]: http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#module-sqlalchemy.orm.session
[Unit of Work]: http://martinfowler.com/eaaCatalog/unitOfWork.html
[sessionmaker]: http://docs.sqlalchemy.org/en/rel_0_8/orm/session.html#sqlalchemy.orm.session.sessionmaker


### Insert ###

First of all, we'll create some data:

```python
tag_cool = Tag(name='cool')
tag_car = Tag(name='car')
tag_animal = Tag(name='animal')

comment_rhino = Comment(text='Rhinoceros, often abbreviated as rhino, is a group of five extant species of odd-toed ungulates in the family Rhinocerotidae.')

image_car = Image(uuid='uuid_car', \
    tags=[tag_car, tag_cool], \
    created_at=(datetime.utcnow() - timedelta(days=1)))

image_another_car = Image(uuid='uuid_anothercar', \
    tags=[tag_car])
    
image_rhino = Image(uuid='uuid_rhino', \
    tags=[tag_animal], \
    comments=[comment_rhino])
```

And then we can get a new session object, add the records and commit the work:

```python
session = Session()

session.add(tag_cool)
session.add(tag_car)
session.add(tag_animal)

session.add(comment_rhino)

session.add(image_car)
session.add(image_another_car)
session.add(image_rhino)

session.commit()
```

The generated SQL appears in the command prompt:

```sql
BEGIN

INSERT INTO tags (name) VALUES (?)
('cool',)

INSERT INTO tags (name) VALUES (?)
('car',)

INSERT INTO tags (name) VALUES (?)
('animal',)

INSERT INTO images (uuid, likes, created_at) VALUES (?, ?, ?)
('uuid_car', 0, '2014-12-20 19:16:19.822000')

INSERT INTO images (uuid, likes, created_at) VALUES (?, ?, ?)
('uuid_anothercar', 0, '2014-12-21 19:16:19.828000')

INSERT INTO images (uuid, likes, created_at) VALUES (?, ?, ?)
('uuid_rhino', 0, '2014-12-21 19:16:19.829000')

INSERT INTO tag_image (tag_id, image_id) VALUES (?, ?)
((2, 1), (1, 1), (3, 3), (2, 2))

INSERT INTO comments (text, image_id) VALUES (?, ?)
('Rhinoceros, often abbreviated as rhino, is a group of five extant species of odd-toed ungulates in the family Rhinocerotidae.', 3)

COMMIT
```

### Update ###

Updating a record is easy... Imagine someone upvoted an image, and we get UUID:

```python
# Find the image with the given uuid:
image_to_update = session.query(Image).filter(Image.uuid == 'uuid_rhino').first()
# Increase the number of upvotes:
image_to_update.likes = image_to_update.likes + 1
# And commit the work:
session.commit()
```

[SQLAlchemy] translates this to SQL as:

```sql
SELECT images.id AS images_id, images.uuid AS images_uuid, images.likes AS images_likes, images.created_at AS images_created_at
FROM images
WHERE images.uuid = ?
LIMIT ? OFFSET ?
('uuid_rhino', 1, 0)

UPDATE images SET likes=? WHERE images.id = ?
(1, 3)

COMMIT
```

### Delete ###

Deleting an entity is as easy as calling delete on the session object:

```python
session.delete(image_rhino)
```

In the following SQL we can see that the comments of an image do not get deleted once the image is deleted. We can also see, 
that orphaned tags are not deleted, see [this stackoverflow post](http://stackoverflow.com/a/9264556/513875) for the very 
detailed reason.

```sql

SELECT images.id AS images_id, images.uuid AS images_uuid, images.likes AS images_likes, images.created_at AS images_created_at
FROM images
WHERE images.id = ?
(3,)

SELECT comments.id AS comments_id, comments.text AS comments_text, comments.image_id AS comments_image_id
FROM comments
WHERE ? = comments.image_id
(3,)

sqlalchemy.engine.base.Engine SELECT tags.id AS tags_id, tags.name AS tags_name 
FROM tags, tag_image
WHERE ? = tag_image.image_id AND tags.id = tag_image.tag_id
(3,)

DELETE FROM tag_image WHERE tag_image.tag_id = ? AND tag_image.image_id = ?
(3, 3)

UPDATE comments SET image_id=? WHERE comments.id = ?
(None, 1)

DELETE FROM images WHERE images.id = ?
(3,)

COMMIT
(1,)
```

It is up to you to decide wether this is an acceptable situation for your application or not. If you want to prevent the foreign key from 
being set to null, then declare the column as not nullable (``Column(Integer, ForeignKey('images.id'), nullable=False)``. A delete to 
an image will then fail with an ``IntegrityError``.

If you want the comments to be deleted, when the parent image is deleted, then add a ``cascade = "all,delete"`` to the relationship declaration:

```python
comments = relationship('Comment', cascade = "all,delete", backref='image', lazy='dynamic')
```

I know there are [cascaded deletes and updates](http://en.wikipedia.org/wiki/Foreign_key#CASCADE) in a lot of databases, but my SQLite version 
doesn't seem to respect them.

### Queries ###

If you are familiar with SQL, then writing queries with [SQLAlchemy] is easy for you. Here are some queries
you can fire against the database of this article.

```python
# Get a list of tags:
for name in session.query(Tag.name).order_by(Tag.name):
    print name

# How many tags do we have?
session.query(Tag).count()

# Get all images created yesterday:
session.query(Image) \
    .filter(Image.created_at < datetime.utcnow().date()) \
    .all()
   
# Get all images, that belong to the tag 'car' or 'animal', using a subselect:
session.query(Image) \
    .filter(Image.tags.any(Tag.name.in_(['car', 'animal']))) \
    .all()

# This can also be expressed with a join:
session.query(Image) \
    .join(Tag, Image.tags) \
    .filter(Tag.name.in_(['car', 'animal'])) \
    .all()

# Play around with functions:
from sqlalchemy.sql import func, desc

max_date = session.query(func.max(Image.created_at))
session.query(Image).filter(Image.created_at == max_date).first()

# Get a list of tags with the number of images:
q = session.query(Tag, func.count(Tag.name)) \
    .outerjoin(Image, Tag.images) \
    .group_by(Tag.name) \
    .order_by(desc(func.count(Tag.name))) \
    .all()

for tag, count in q:
    print 'Tag "%s" has %d images.' % (tag.name, count) 

# Get images created in the last two hours and zero likes so far:
session.query(Image) \
    .join(Tag, Image.tags) \
    .filter(Image.created_at > (datetime.utcnow() - timedelta(hours=2))) \
    .filter(Image.likes == 0) \
    .all()
```

## Conclusion ##

[SQLAlchemy] is fun to work with. Defining a schema is dead simple and the query language feels like writing native SQL. In the next article 
we are going to see how [Flask] uses [SQLAlchemy] and write a small Web service with it.

## Appendix ##

### Model ###

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from datetime import datetime, timedelta
from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

tags = Table('tag_image', Base.metadata,
    Column('tag_id', Integer, ForeignKey('tags.id')),
    Column('image_id', Integer, ForeignKey('images.id'))
)
 
class Image(Base):
    
    __tablename__ = 'images'
    
    id          =   Column(Integer, primary_key=True)
    uuid        =   Column(String(36), unique=True, nullable=False)
    likes       =   Column(Integer, default=0)
    created_at  =   Column(DateTime, default=datetime.utcnow)
    tags        =   relationship('Tag', secondary=tags, 
                        backref = backref('images', lazy='dynamic'))
    comments    =   relationship('Comment', backref='image', lazy='dynamic')
    
    def __repr__(self):
        str_created_at = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return "<Image (uuid='%s', likes='%d', created_at=%s)>" % (self.uuid, self.likes, str_created_at)

class Tag(Base):
    
    __tablename__ = 'tags'
    
    id      =   Column(Integer, primary_key=True)
    name    =   Column(String(255), unique=True, nullable=False)
    
    def __repr__(self):
        return "<Tag (name='%s')>" % (self.name)

class Comment(Base):
    
    __tablename__ = 'comments'
    
    id          =   Column(Integer, primary_key=True)
    text        =   Column(String(2000))
    image_id    =   Column(Integer, ForeignKey('images.id'))
    
    def __repr__(self):
        return "<Comment (text='%s')>" % (self.text)
```

### Data ###

```python
#----------------------------
# Turn Foreign Key Constraints ON for
# each connection.
#----------------------------

from sqlalchemy.engine import Engine
from sqlalchemy import event

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

#----------------------------
# Create the engine
#----------------------------

from sqlalchemy import create_engine
engine = create_engine('sqlite:///:memory:', echo=True)

#----------------------------
# Create the Schema
#----------------------------

Base.metadata.create_all(engine)

#----------------------------
# Create the Session class 
#----------------------------

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)

#----------------------------
# Populate the database 
#----------------------------

tag_cool = Tag(name='cool')
tag_car = Tag(name='car')
tag_animal = Tag(name='animal')

comment_rhino = Comment(text='Rhinoceros, often abbreviated as rhino, is a group of five extant species of odd-toed ungulates in the family Rhinocerotidae.')

image_car = Image(uuid='uuid_car', \
    tags=[tag_car, tag_cool], \
    created_at=(datetime.utcnow() - timedelta(days=1)))

image_another_car = Image(uuid='uuid_anothercar', \
    tags=[tag_car])
    
image_rhino = Image(uuid='uuid_rhino', \
    tags=[tag_animal], \
    comments=[comment_rhino])

# Create a new Session and add the images:
session = Session()

session.add(tag_cool)
session.add(tag_car)
session.add(tag_animal)

session.add(comment_rhino)

session.add(image_car)
session.add(image_another_car)
session.add(image_rhino)

# Commit the changes:
session.commit()

#----------------------------
# Update a Record
#----------------------------

image_to_update = session.query(Image).filter(Image.uuid == 'uuid_rhino').first()
image_to_update.likes = image_to_update.likes + 1
session.commit()

#----------------------------
# Query the database
#
# List of common filter: 
#
#   *http://docs.sqlalchemy.org/en/rel_0_9/orm/tutorial.html#common-filter-operators
#
#----------------------------

# Get a list of tags:
for name in session.query(Tag.name).order_by(Tag.name):
    print name

# How many tags do we have?
session.query(Tag).count()

# Get all images created yesterday:
session.query(Image) \
    .filter(Image.created_at < datetime.utcnow().date()) \
    .all()
   
# Get all images, that belong to the tag 'car' or 'animal', using a subselect:
session.query(Image) \
    .filter(Image.tags.any(Tag.name.in_(['car', 'animal']))) \
    .all()

# This can also be expressed with a join:
session.query(Image) \
    .join(Tag, Image.tags) \
    .filter(Tag.name.in_(['car', 'animal'])) \
    .all()

# Play around with functions:
from sqlalchemy.sql import func, desc

max_date = session.query(func.max(Image.created_at))
session.query(Image).filter(Image.created_at == max_date).first()

# Get a list of tags with the number of images:
q = session.query(Tag, func.count(Tag.name)) \
    .outerjoin(Image, Tag.images) \
    .group_by(Tag.name) \
    .order_by(desc(func.count(Tag.name))) \
    .all()

for tag, count in q:
    print 'Tag "%s" has %d images.' % (tag.name, count) 

# Get images created in the last two hours and zero likes so far:
session.query(Image) \
    .join(Tag, Image.tags) \
    .filter(Image.created_at > (datetime.utcnow() - timedelta(hours=2))) \
    .filter(Image.likes == 0) \
    .all()
```