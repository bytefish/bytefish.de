title: Token Authentication with Nancy and Owin
date: 2015-08-29 15:33
tags: csharp, nancy
category: csharp
slug: token_authentication_owin_nancy
author: Philipp Wagner
summary: This article describes how to implement Token-based authentication with Nancy.

[Nancy]: https://github.com/NancyFx/Nancy
[NPoco]: https://github.com/schotime/NPoco
[OWIN]: http://owin.org
[HTML5 reference]: http://www.w3.org/TR/html5/forms.html#multipart/form-data-encoding-algorithm
[PostgreSQL]: http://www.postgresql.org
[NHibernate]: http://nhibernate.info
[Entity Framework]: http://www.asp.net/entity-framework

[TOC]

## Introduction ##

This post shows how to implement Token-based authentication with [OWIN] and [Nancy]. I will show you how to implement a custom claim-based authentication system, that you can adapt to your needs. 

I have always struggled with how to start a project. This is a full-blown example on how to implement such a project with open source applications and libraries.

The source code is released under MIT license:

* [https://github.com/bytefish/NancyOwinExample](https://github.com/bytefish/NancyOwinExample)

You can find the SQL scripts used in this article at:

* [https://github.com/bytefish/NancyOwinExample/tree/master/TokenAuthentication/Database](https://github.com/bytefish/NancyOwinExample/tree/master/TokenAuthentication/Database)

### OWIN, Token-authentication, Claims, ...? ###

Before starting a project you should always get the terminology right and understand what you are going to build. I thought about writing a thorough introduction for 
each topic, but I found myself copying Stackoverflow posts, Microsoft documentation and other peoples blogs. So I think it's better to link these posts and focus on 
using and implementing the mentioned concepts.

Every client facing API should be secured, which turns out to be a tough problem for a RESTful API. One way to provide authenticated access to an API is using a Token-based authentication scheme.

> The general concept behind a token-based authentication system is simple. Allow users to enter their username and password in order to obtain a token which allows them 
> to fetch a specific resource - without using their username and password. Once their token has been obtained, the user can offer the token - which offers access to a 
> specific resource for a time period - to the remote site. ([Source](http://www.w3.org/2001/sw/Europe/events/foaf-galway/papers/fp/token_based_authentication/))

The tokens in this article will be generated according to the OAuth 2.0 specification: [http://tools.ietf.org/html/rfc6749](http://tools.ietf.org/html/rfc6749).

Once authenticated requests to the API can be made, we have to determine if a user has the permission to access a given method. One way is to use claim-based authentication, which 
is available in the ``System.Security.Claims`` namespace of the .NET Framework.

Starting with .NET 4.5 the Windows Identity Foundation got fully integrated into the .NET Framework as ``System.Security.Claims``. Using these components in a 
web applications is really a piece of cake with Microsoft OWIN components, which we are going to use in this article. There is a nice blog post by Daniel Roth 
about [using claims with the new OWIN security components](http://blogs.msdn.com/b/webdev/archive/2014/02/21/using-claims-in-your-web-app-is-easier-with-the-new-owin-security-components.aspx).

> When you build claims-aware applications, the user identity is represented in your application as a set of claims. One claim could be the users name, 
> another might be an e-mail address. The idea is that an external identity system is configured to give your application everything it needs to know about 
> the user with each request she makes, along with cryptographic assurance that the identity data you receive comes from a trusted source.
>
> Under this model, single sign-on is much easier to achieve, and your application is no longer responsible for the following:
>
> * Authenticating users.
> * Storing user accounts and passwords.
> * Calling to enterprise directories to look up user identity details.
> * Integrating with identity systems from other platforms or companies.
>
> Under this model, your application makes identity-related decisions based on claims supplied by the system that authenticated your user. This could be anything 
> from simple application personalization with the users first name, to authorizing the user to access higher valued features and resources in your application.

So what is OWIN? Microsoft has noticed, that Ruby on Rails and [Node.js](https://nodejs.org) got a lot of (deserved) attention in web programming. 
I think Microsoft wants to create an open source community around the .NET stack and specified OWIN to enable writing modular components for the web. Prior to OWIN all 
ASP.NET application were more or less bound to the IIS and took a hard dependency on System.Web assembly.

Microsoft explains OWIN as:

> Open Web Interface for .NET (OWIN) defines an abstraction between .NET web servers and web applications. By decoupling the web server from the application, 
> OWIN makes it easier to create middleware for .NET web development. Also, OWIN makes it easier to port web applications to other hosts for example, 
> self-hosting in a Windows service or other process.

That's it.

## Preparing the Database ##

A claim-based identity model is based around the notion of a user with its associated claims. So where do we store the authentication credentials and claims? I 
like working with relational databases, because SQL makes it really easy to work with data. Database transactions and constraints ensure data integrity, which 
is a must for any serious business application.

This post uses [PostgreSQL] as the database backend, which is freely available at [http://www.postgresql.org](http://www.postgresql.org).

### User and Database ###

[pgAdmin]: http://www.pgadmin.org/

First of all we need to create the ``sampledb`` database and a user ``philipp`` (or any name you want). You can do this by connecting to your local 
PostgreSQL instance as the default user *postgres* (or any other user with administrative rights) and create a new user and database.

```
PS C:\Users\philipp> psql -U postgres
psql (9.4.1)
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
postgres=# CREATE DATABASE sampledb
postgres-#   WITH OWNER philipp;
CREATE DATABASE
```

You could also use [pgAdmin] for this task, if you are uncomfortable with using a terminal.

## The Database Schema ##

### Schema ###

I am using schemas to keep my database clean and so should you. A database schema logically groups the objects such as tables, views, 
stored procedures, ... and makes it possible to assign user permissions to the schema. In this example the ``auth`` schema is going 
to contain all tables for the user and permission management.

```
DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN

    CREATE SCHEMA auth;

END IF;

END;
$$;
```

### Tables ###

[plaintext]: https://en.wikipedia.org/wiki/Plaintext
[junction table]: https://en.wikipedia.org/wiki/Junction_table

Now it's time to define the tables and relations for the authentication. In this example there are only two entities: a *User* and a *Claim*. Let's take a look at 
the relation between both: A user can have many claims and a claim can be associated with many users. That's a many-to-many relation, so an additional 
[junction table] is needed.

It's important to note, that you should **never store [plaintext] passwords in a database**. Your database could be hacked and you may cause serious 
damage by exposing all passwords in plaintext. The best way to protect the passwords is to employ salted password hashing. So the user table is going 
to have a field for the password hash, and a field for the salt used to create the hash.

```
DO $$
BEGIN

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'auth' 
	AND table_name = 'user'
) THEN

CREATE TABLE auth.user
(
	user_id SERIAL PRIMARY KEY,
	name VARCHAR(255) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	password_salt VARCHAR(255) NOT NULL
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'auth' 
	AND table_name = 'claim'
) THEN

CREATE TABLE auth.claim
(
	claim_id SERIAL PRIMARY KEY,
	type VARCHAR(255) NOT NULL,
	value VARCHAR(255) NOT NULL
);

END IF;

IF NOT EXISTS (
	SELECT 1 
	FROM information_schema.tables 
	WHERE  table_schema = 'auth' 
	AND table_name = 'user_claim'
) THEN

CREATE TABLE auth.user_claim
(
	user_claim_id SERIAL PRIMARY KEY,
	user_id INTEGER NOT NULL,
	claim_id INTEGER NOT NULL
);

END IF;

END;
$$;
```

### Foreign Keys and Unique Constraints ###

And what is a relational database without referential integrity? Let's add some keys and constraints!

```
DO $$
BEGIN

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_claim_userid_fkey') THEN
	ALTER TABLE auth.user_claim
		ADD CONSTRAINT user_claim_userid_fkey
		FOREIGN KEY (user_id) REFERENCES auth.user(user_id);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_claim_claimid_fkey') THEN
	ALTER TABLE auth.user_claim
		ADD CONSTRAINT user_claim_claimid_fkey
		FOREIGN KEY (claim_id) REFERENCES auth.claim(claim_id);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_user_name') THEN
	ALTER TABLE auth.user
		ADD CONSTRAINT uk_user_name
		UNIQUE (name);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_claim_type') THEN
	ALTER TABLE auth.claim
		ADD CONSTRAINT uk_claim_type
		UNIQUE (type);
END IF;

IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uk_user_claim') THEN
	ALTER TABLE auth.user_claim
		ADD CONSTRAINT uk_user_claim
		UNIQUE (user_id, claim_id);
END IF;

END;
$$;
```

### Security ###

And finally we should employ a little security to revoke all access from public eyes.

```
DO $$
BEGIN

REVOKE ALL ON auth.user FROM public;

END;
$$;
```

### Data ###

And finally the claims have to be added to the database.

```
DO $$
BEGIN

IF NOT EXISTS (
	SELECT 1 
	FROM auth.claim 
	WHERE type = 'urn:sample:admin') THEN

INSERT INTO auth.claim(type, value) VALUES('urn:sample:admin', 'true');

END IF;

END
$$;
```

### Creating a Deployment Script ###

[Batch]: http://en.wikipedia.org/wiki/Batch_file

You could copy and paste the above scripts for this tutorial. This is totally OK for small applications, but it won't scale for any real project. 
Believe me, you need to automate the task of creating and migrating a database as early as possible in your project.

I am working in a Windows environment right now, so I have used a [Batch] file to automate the database setup. There is no magic going on, I am just 
setting the path to ``psql`` and use the ``PGPASSWORD`` environment variable to pass the password to the command line.

```bat
@echo off

:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

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

1>%STDOUT% 2>%STDERR% (

	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 01_Schemas/schema_auth.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 02_Tables/tables_auth.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 03_Keys/keys_auth.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 05_Security/security_auth.sql -L %LOGFILE%
	%PGSQL_EXECUTABLE% -h %HostName% -p %PortNumber% -d %DatabaseName% -U %UserName% < 06_Data/data_auth.sql -L %LOGFILE%
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

Deploying the database is now just a matter of running the [Batch] file. By default all messages will be logged to ``stdout.log``, all error messages 
will be logged to ``stderr.log`` and the PostgreSQL logs will be written to ``query_output.log``.

## Database Access with NPoco ##

This article uses [NPoco] to access the database from .NET. We need to install the ``Npgsql`` driver, because [PostgreSQL] is used. ``log4net`` is added to provide the logging.

You can install the packages with NuGet.

```
Install-Package NPoco
Install-Package Npgsql
Install-Package log4net
```

### Connection Strings ###

A connection string is needed to connect to the database. We are using an object oriented language, so we don't pass the plain string around. The 
connection string contains an additional provider name, which is used to specify the driver for the database access.

```csharp
namespace TokenAuthentication.Infrastructure.Database
{
    public class ConnectionStringSettings
    {
        public string ConnectionString { get; set; }
        
        public string ProviderName { get; set; }
    }
}
```

### ConnectionStringProvider ###

The connection string for the application could be resolved from various sources, so let's define an interface first.

```csharp
namespace TokenAuthentication.Infrastructure.Database
{
    public interface IConnectionStringProvider
    {
        ConnectionStringSettings GetConnectionString();
    }
}
```

In this example we are going to resolve the connection string from the ``App.config``. We are simply looking for a connection string named ``ApplicationConnectionString``.

```csharp
namespace TokenAuthentication.Infrastructure.Database
{
    public class ConnectionStringProvider : IConnectionStringProvider
    {
        public ConnectionStringSettings GetConnectionString()
        {
            if (ConfigurationManager.ConnectionStrings["ApplicationConnectionString"] != null)
            {
                var connectionString = ConfigurationManager.ConnectionStrings["ApplicationConnectionString"];

                return new ConnectionStringSettings
                {
                    ConnectionString = connectionString.ConnectionString,
                    ProviderName = connectionString.ProviderName
                };
            }

            throw new InvalidOperationException("ConnectionString with Name ApplicationConnectionString was not found");
        }
    }
}
```

So what's left is to define the ``ApplicationConnectionString`` and the ``Npgsql`` Database Provider in the ``configuration`` section of the app config. 

```xml
<configuration>
   
  <!-- ... -->

  <!-- Database Providers -->
  <system.data>
    <DbProviderFactories>
      <add name="Npgsql Data Provider" invariant="Npgsql" support="FF" description=".Net Framework Data Provider for Postgresql Server" type="Npgsql.NpgsqlFactory, Npgsql" />
    </DbProviderFactories>
  </system.data>

  <!-- Connection Strings -->
  <connectionStrings>
    <add name="ApplicationConnectionString" connectionString="Server=127.0.0.1;Port=5432;Database=sampledb;User Id=philipp;Password=test_pwd;" providerName="Npgsql" />
  </connectionStrings>

</configuration>
```

### Entities ###

Now the ``User`` and ``Claim`` tables from the database need to be mapped to objects in the application. The first step of the data access is to define objects, that map directly 
to the columns of the database. That means we don't have to provide exotic mappings at this point, like NHibernate or Entity Framework require you to define.

All entities should have a Primary Key, which will be ensured by having an abstract base class ``Entity``.

```csharp
namespace TokenAuthentication.Infrastructure.Database.Entities
{
    public abstract class Entity
    {
        public int Id { get; set; }

        public override string ToString()
        {
            return string.Format("Id: {0}", Id);
        }
    }
}
```

Now we have to define the entities for the ``User``, ``Claim`` and ``UserClaim`` junction table. 

```csharp
namespace TokenAuthentication.Infrastructure.Database.Entities
{
    public class User : Entity
    {
        public string Name { get; set; }
        
        public string PasswordHash { get; set; }

        public string PasswordSalt { get; set; }

        public override string ToString()
        {
            return string.Format("User ({0}, Name: {1}, PasswordHash: {2}, PasswordSalt: {3})", base.ToString(), Name, PasswordHash, PasswordSalt);
        }
    }
}
```

Do not put these classes in a single file, but separate them into their own files.

```csharp
namespace TokenAuthentication.Infrastructure.Database.Entities
{
    public class Claim : Entity
    {
        public string Type { get; set; }

        public string Value { get; set; }

        public override string ToString()
        {
            return string.Format("Claim ({0}, Type: {1}, Value: {2}", base.ToString(), Type, Value);
        }
    }
}
```

The ``UserClaims`` class finally represents the mentioned [junction table].

```csharp
namespace TokenAuthentication.Infrastructure.Database.Entities
{
    public class UserClaims : Entity
    {
        public string UserId { get; set; }

        public string ClaimId { get; set; }
        
        public override string ToString()
        {
            return string.Format("UserClaim ({0}, UserId: {1}, ClaimId: {2})", base.ToString(), UserId, ClaimId);
        }
    }
}
```

I am overriding the ``ToString`` method, because I really, really, really want to have a nice representation of the objects when logging. It makes tracing problems so much easier.

### Fluent Mapping ###

Somehow [NPoco] has to perform the actual mapping when querying data. This is done by implementing the ``IMap`` interface for each type. I am not a huge fan of XML configurations or trusting conventions,
so I am going to use the [Fluent Mapping API](https://github.com/schotime/NPoco/wiki/Fluent-mappings-including-conventional) of NPoco for this.

```csharp
using NPoco.FluentMappings;
using TokenAuthentication.Infrastructure.Database.Entities;

namespace TokenAuthentication.Infrastructure.Database.Mapping
{
    public class UserMapping : Map<User>
    {
        public UserMapping()
        {
            PrimaryKey(p => p.Id, autoIncrement: true)
                .TableName("auth.user")
                .Columns(x =>
                {
                    x.Column(p => p.Id).WithName("user_id");
                    x.Column(p => p.Name).WithName("name");
                    x.Column(p => p.PasswordHash).WithName("password_hash");
                    x.Column(p => p.PasswordSalt).WithName("password_salt");
                });
        }
    }
}
```

Do the same for the ``Claim`` entity.

```csharp
using NPoco.FluentMappings;
using TokenAuthentication.Infrastructure.Database.Entities;

namespace TokenAuthentication.Infrastructure.Database.Mapping
{
    public class ClaimMapping : Map<Claim>
    {
        public ClaimMapping()
        {
            PrimaryKey(p => p.Id, autoIncrement: true)
                .TableName("auth.claim")
                .Columns(x =>
                {
                    x.Column(p => p.Id).WithName("claim_id");
                    x.Column(p => p.Type).WithName("type");
                    x.Column(p => p.Value).WithName("value");
                });
        }
    }
}
```

And do the same for the [junction table] between both.

```csharp
using NPoco.FluentMappings;
using TokenAuthentication.Infrastructure.Database.Entities;

namespace TokenAuthentication.Infrastructure.Database.Mapping
{
    public class UserClaimsMapping : Map<UserClaims>
    {
        public UserClaimsMapping()
        {
            PrimaryKey(p => p.Id, autoIncrement: true)
                .TableName("auth.user_claim")
                .Columns(x =>
                {
                    x.Column(p => p.Id).WithName("user_claim_id");
                    x.Column(p => p.UserId).WithName("user_id");
                    x.Column(p => p.ClaimId).WithName("claim_id");
                });
        }
    }
}
```

### A MappingProvider ###

These mappings need to be provided to a ``DatabaseFactory`` at a later point. We are defining a simple ``IMappingProvider`` interface, which makes it possible to define 
different strategies of providing the mapping classes. Again I could imagine various strategies to locate the mappings, like scanning through assemblies or reading from 
an external file.

```csharp
using NPoco.FluentMappings;

namespace TokenAuthentication.Infrastructure.Database
{
    public interface IMappingProvider
    {
        IMap[] GetMappings();
    }
}
```

For this example we can safely hardcode the ``IMap`` implementations. In a complex project you should come up with something more dynamic and extendable.

```csharp
using NPoco.FluentMappings;
using TokenAuthentication.Infrastructure.Database.Mapping;

namespace TokenAuthentication.Infrastructure.Database
{
    public class MappingProvider : IMappingProvider
    {
        public IMap[] GetMappings()
        {
            return new IMap[] { new UserMapping(), new ClaimMapping(), new UserClaimsMapping() };
        }
    }
}
```

### Logging Database Queries ###

The most important aspect of an application is logging. Every developer knows, that applications crash. And when they crash, you want to know what happened. [NPoco] makes 
it easy to log the all executed queries and errors. You simply extend from the NPoco ``Database`` and override the methods you are interested in.

```csharp
using log4net;
using System.Data;
using System.Reflection;

namespace TokenAuthentication.Infrastructure.Database
{
    public class LoggingDatabase : NPoco.Database
    {
        private static readonly ILog log = LogManager.GetLogger(MethodBase.GetCurrentMethod().DeclaringType);

        public LoggingDatabase(ConnectionStringSettings connectionString) 
            : base(connectionString.ConnectionString, connectionString.ProviderName) { }

        protected override void OnExecutingCommand(IDbCommand cmd)
        {
            if (log.IsDebugEnabled)
            {
                log.Debug(FormatCommand(cmd));
            }
        }

        protected override void OnException(System.Exception exception)
        {
            if (log.IsErrorEnabled)
            {
                log.Error(exception);
            }
        }
    }
}
```

### Configuring log4net ###

The application is using log4net for logging. But where are the logs written to? We didn't define a log appender yet, so they are written nowhere at the moment. log4net provides a large 
set of log appenders, you can find an exhaustive list of example configurations at [https://logging.apache.org/log4net/release/config-examples.html](https://logging.apache.org/log4net/release/config-examples.html).

Configuring log4net is easy. In the ``AssemblyInfo.cs`` of our project we have to configure log4net to use the Xml configuration and watch for changes to the file.

```csharp
// Configure log4net by XML and make sure we are watching for changes!
[assembly: log4net.Config.XmlConfigurator(Watch = true)]
```

Then we edit the ``App.config`` to set the appSettings for log4net. The appSetting values are a convention used in log4net and you can find them in the documentation of log4net. We don't want to 
write the log4net configuration directly in the App.config, but use an external ``log4net.config`` file. This is where the log appenders are going to be defined.

```xml
  <!-- Logging -->
  <appSettings>
    <add key="log4net.Config" value="log4net.config" />
    <add key="log4net.Config.Watch" value="True" />
  </appSettings>
```

Finall we can define the log appenders in the ``log4net.config`` file. In this example a RollingFileAppender with a maximum file size of ``10 MB`` and a maximum number of 
``10`` backups is used. You probably need to adjust the file path for your local system. The ``log4net.config`` is the place to define the appenders and format and so on.

```xml
<?xml version="1.0" encoding="utf-8" ?>
<configuration>
  <configSections>
    <section name="log4net" type="log4net.Config.Log4NetConfigurationSectionHandler, log4net" />
  </configSections>
  <log4net>
    <appender name="RollingFileAppender" type="log4net.Appender.RollingFileAppender">
      <file value="D:\logs\log.txt" />
      <appendToFile value="true" />
      <rollingStyle value="Size" />
      <maxSizeRollBackups value="10" />
      <maximumFileSize value="10MB" />
      <staticLogFileName value="true" />
      <layout type="log4net.Layout.PatternLayout">
        <conversionPattern value="%date [%thread] %-5level %logger - %message%newline" />
      </layout>
    </appender>
    <root>
      <level value="DEBUG" />
      <appender-ref ref="RollingFileAppender" />
    </root>
  </log4net>
</configuration>
```

### Database Factory ###

It is time to plug everything together and create the ``DatabaseFactory``, which is used to get fresh NPoco ``IDatabase`` objects.

Again we define an interface, so we could switch the ``DatabaseFactory`` if we ever need to.

```csharp
using NPoco;

namespace TokenAuthentication.Infrastructure.Database
{
    public interface IDatabaseFactory
    {
        IDatabase GetDatabase();
    }
}
```

See how we pass the ``IConnectionStringProvider`` and the ``IMappingProvider`` into the factory? These providers could easily be replaced with 
your own implementations and you don't have to change anything in the ``DatabaseFactory``. Dependency Injection at its best!

```csharp
using NPoco;
using NPoco.FluentMappings;

namespace TokenAuthentication.Infrastructure.Database
{
    public class DatabaseFactory : IDatabaseFactory
    {
        private NPoco.DatabaseFactory databaseFactory;

        public DatabaseFactory(IConnectionStringProvider connectionStringProvider, IMappingProvider mappingProvider)
        {   
            DatabaseFactoryConfigOptions options = new DatabaseFactoryConfigOptions();

            var connectionString = connectionStringProvider.GetConnectionString();
            var mappings = mappingProvider.GetMappings();

            options.Database = () => new LoggingDatabase(connectionString);
            options.PocoDataFactory = FluentMappingConfiguration.Configure(mappings);

            databaseFactory = new NPoco.DatabaseFactory(options);
        }
        
        public IDatabase GetDatabase()
        {
            return databaseFactory.GetDatabase();
        }
    }
}
```

And that's it for the Database access for now!

### Conclusion ###

I really like how simple it was to get started with [NPoco]. It's a very lightweight approach to data access, compared to a full-blown ORM 
like [NHibernate] or [Entity Framework]. I am not saying NHibernate or Entity Framework are bad. They remove the burden to write a lot of 
boilerplate code and get you started just as quick.

[Adam](https://github.com/schotime) you did a great job! I really enjoyed working with [NPoco].

## Implementing Token-authentication with Nancy and OWIN ##

So much code and we haven't dealt with the actual Claims or Token authentication yet. What have we done so far? We have set up the PostgreSQL database 
to store the User and Claims data. We have built the base classes to access the database. Now we want to look at how to self-host a [Nancy] application 
on an [OWIN] stack. 

Then we'll see how to secure the API with claim-based Token-authentication.

### Using OWIN to a Self-Host an app ###

[OWIN Startup Class Detection]: http://www.asp.net/aspnet/overview/owin-and-katana/owin-startup-class-detection

How would I approach such a task? I would start with getting the self-hosted server up and running. The self-hosted server is located in 
``Microsoft.Owin.Hosting`` and we can host it with a simple command line application. In a real project you would opt for a full-blown IIS 
or a Windows Service. 

```csharp
using Microsoft.Owin.Hosting;
using System;

namespace TokenAuthentication
{
    public class Program
    {
        static void Main(string[] args)
        {
            const string url = "http://localhost:8080";

            using (WebApp.Start<Startup>(url))
            {
                Console.WriteLine("Server running on {0}", url);
                Console.ReadLine();
            }
        }
    }
}
```

So what's this ``Startup`` class used for the ``WebApp``? 

The startup class is a class, which is used to configure the components of the OWIN application pipeline. It's where we plug the middleware into the 
OWIN pipeline. How does the class get invoked at all? The Katana Runtime is Microsofts OWIN implementation and tries to determine the Startup class with 
several strategies, see the official page on [OWIN Startup Class Detection].  We are going to rely on the Naming Convention described in the documentation.

The Startup class has to provide a public method with the signature ``void Configuration(IAppBuilder app)`` to be detected and that's it.

```csharp
using Owin;

namespace TokenAuthentication
{
    public class Startup
    {
        public void Configuration(IAppBuilder app)
        {

        }
    }
}
```

You can now start the server, although it hasn't much functionality at the moment. Let's see how to plug Nancy into our application pipeline!

### Plugging Nancy into the OWIN Pipeline ###

[Nancy] has first-class support for OWIN and provides an extension method for integrating it into the OWIN pipeline.

First of all we have to install the OWIN extensions points of Nancy.

```
Install-Package Nancy.Owin
```

Now the ``UseNancy`` extension method on the ``IAppBuilder`` interface is used to hook it into the pipeline. Please read up the very detailed 
wiki page on [hosting Nancy with OWIN](https://github.com/NancyFx/Nancy/wiki/Hosting-nancy-with-owin) for additional configurations.

```csharp
using Owin;

namespace TokenAuthentication
{
    public class Startup
    {
        public void Configuration(IAppBuilder app)
        {
            app.UseNancy();
        }
    }
}
```

Let's add a new Folder ``Modules`` to the project and create a new NancyModule.

```csharp
using Nancy;

namespace TokenAuthentication.Modules
{
    public class HelloWorldModule : NancyModule
    {
        public HelloWorldModule()
        {
            Get["/"] = _ =>
            {
                return "Hello World";
            };   
        }
    }
}
```

Start the server and visit ``http://localhost:8080``. You should now be greeted with a Hello World:

<img src="/static/images/blog/nancy_owin/owin_nancy_hello_world.png" alt="A Nancy module saying Hello World" />

Congratulations!

### Application settings ###

The endpoints for Nancy modules and the endpoint for token generation should be separated. The Nancy modules will be located at the ``/api`` path and 
tokens will be obtained from the ``/token`` endpoint. We don't want to use magic strings in our application, so let's define an interface to obtain 
application-wide settings.

```csharp
namespace TokenAuthentication.Services
{
    /// <summary>
    /// Defines Application-wide Settings.
    /// </summary>
    public interface IApplicationSettings
    {
        /// <summary>
        /// Base Path for the Nancy Modules.
        /// </summary>
        string NancyBasePath { get; }

        /// <summary>
        /// Base Path for the Token.
        /// </summary>
        string TokenEndpointBasePath { get; }

        /// <summary>
        /// Size of the salts for Password generation.
        /// </summary>
        int SaltSize { get; }
    }
}
```

In this example we can safely hardcode the settings. You should load the configuration from a database or external configuration in a real project.

```csharp
namespace TokenAuthentication.Services
{
    public class ApplicationSettings : IApplicationSettings
    {
        public string NancyBasePath
        {
            get { return "/api"; }
        }

        public string TokenEndpointBasePath
        {
            get { return "/token"; }
        }

        public int SaltSize
        {
            get { return 13; }
        }
    }
}
```

### Configuring the Nancy Endpoint ###

These endpoints now have to be configured in the Startup class. I am adding a Dependency Injection container, because it is going to make our life a little easier. Did you 
ever hear about Dependency Injection? It's basically giving an object its instance variables, rather than instantiating them inside the class. This is a very useful technique 
to write testable and maintainable code.

```csharp
using Nancy.TinyIoc;
using Owin;
using TokenAuthentication.Services;

namespace TokenAuthentication
{
    public class Startup
    {
        public void Configuration(IAppBuilder app)
        {
            TinyIoCContainer container = new TinyIoCContainer();

            // Register Dependencies:
            RegisterDependencies(container);

            // Initialize Nancy:
            SetupNancy(app, container);
        }

        private void RegisterDependencies(TinyIoCContainer container)
        {
            container.Register<IApplicationSettings, ApplicationSettings>();
        }

        private void SetupNancy(IAppBuilder app, TinyIoCContainer container)
        {
            var settings = container.Resolve<IApplicationSettings>();

            app.Map(settings.NancyBasePath, siteBuilder => siteBuilder.UseNancy());
        }
    }
}
```

Visiting ``http://localhost:8080/api`` will now greet you with a Hello World. The Endpoint has been successfully mapped.

[TinyIoC](https://github.com/NancyFx/Nancy/blob/master/src/Nancy/TinyIoc/TinyIoC.cs) is the Dependency Injection container used by the Nancy framework, and it provides basic Dependency 
Injection functionality. I like to use it for small projects, where I am not willed to fight with [Spring.NET](http://springframework.net/), [Ninject](http://www.ninject.org/) and so on. 
If you have wondered how an IoC container works, you probably want to read a great post by [Mat McLoughlin](http://mat-mcloughlin.net) on 
[building a basic IoC container](http://mat-mcloughlin.net/2013/08/15/a-basic-example-of-an-ioc-container/).

## User Management ##

### Password Hashing ###

We need to hash the passwords in the application, so we define an interface to hash values. The reason is simple: You probably want to switch the 
Hash algorithm without changing anything else in code.

```csharp
namespace TokenAuthentication.Services
{
    public interface IHashProvider
    {
        byte[] ComputeHash(byte[] data);
    }
}
```

The default implementation uses [SHA512](https://en.wikipedia.org/wiki/SHA-2) to hash the given data.


```csharp
using System.Security.Cryptography;

namespace TokenAuthentication.Services
{
    public class HashProvider : IHashProvider
    {
        public byte[] ComputeHash(byte[] data)
        {
            using (var sha512 = SHA512.Create())
            {
                return sha512.ComputeHash(data);
            }
        }
    }
}
```

#### Crypto Service ####

To do the actual hashing of values we are defining an ``ICryptoService`` that generates and computes hashes.

```csharp
namespace TokenAuthentication.Services
{
    public interface ICryptoService
    {
        void CreateHash(byte[] data, out byte[] hash, out byte[] salt);

        byte[] ComputeHash(byte[] data, byte[] salt);
    }
}
```

The default implementation creates a random salt and takes a HashProvider as dependency.

```csharp
using System.Security.Cryptography;

namespace TokenAuthentication.Services
{
    public class CryptoService : ICryptoService
    {
        private readonly IApplicationSettings settings;
        private readonly IHashProvider hashProvider;

        public CryptoService(IApplicationSettings settings, IHashProvider hashProvider)
        {
            this.settings = settings;
            this.hashProvider = hashProvider;
        }

        public void CreateHash(byte[] data, out byte[] hash, out byte[] salt)
        {
            salt = CreateSalt();
            hash = ComputeHash(data, salt);
        }

        public byte[] ComputeHash(byte[] data, byte[] salt)
        {
            byte[] saltedData = Concatenate(data, salt);
            byte[] hashBytes = hashProvider.ComputeHash(saltedData);

            return hashBytes;
        }

        private byte[] CreateSalt()
        {
            byte[] randomBytes = new byte[settings.SaltSize];
            using (var randomGenerator = new RNGCryptoServiceProvider())
            {
                randomGenerator.GetBytes(randomBytes);
                return randomBytes;
            }
        }

        private byte[] Concatenate(byte[] a, byte[] b)
        {
            byte[] result = new byte[a.Length + b.Length];

            System.Buffer.BlockCopy(a, 0, result, 0, a.Length);
            System.Buffer.BlockCopy(b, 0, result, a.Length, b.Length);

            return result;
        }
    }
}
```

You have seen, that we are storing the hashes as strings in the database. Defining two extension methods make it easier for us to work with strings instead of byte arrays.

```csharp
using System;
using System.Text;

namespace TokenAuthentication.Services
{
    public static class CryptoServiceExtensions
    {
        public static void CreateHash(this ICryptoService cryptoService, string data, out string hash, out string salt)
        {
            byte[] hashBytes;
            byte[] saltBytes;
            byte[] dataBytes = Encoding.UTF8.GetBytes(data);

            cryptoService.CreateHash(dataBytes, out hashBytes, out saltBytes);

            hash = Convert.ToBase64String(hashBytes);
            salt = Convert.ToBase64String(saltBytes);
        }

        public static string ComputeHash(this ICryptoService cryptoService, string data, string salt)
        {
            byte[] dataBytes = Encoding.UTF8.GetBytes(data);
            byte[] saltBytes = Convert.FromBase64String(salt);

            byte[] hashBytes = cryptoService.ComputeHash(dataBytes, saltBytes);

            return Convert.ToBase64String(hashBytes);
        }
    }
}
```

### UserIdentity ###

The user model in this application isn't rich, so it only has a Name the Claims associated with the Identity.

```csharp
using System.Collections.Generic;

namespace TokenAuthentication.Model
{
    /// <summary>
    /// Represents a UserIdentity with a Users Name and Claims.
    /// </summary>
    public class UserIdentity
    {
        public int Id {get; set; }

        public string Name { get; set; }

        public IList<ClaimIdentity> Claims { get; set; }
    }
}
```

And the claims simply consist of a type and value.

```csharp
namespace TokenAuthentication.Model
{
    /// <summary>
    /// Represents a Claim with a Type and a Value.
    /// </summary>
    public class ClaimIdentity
    {
        public int Id { get; set; }

        public string Type { get; set; }
        
        public string Value { get; set; }
    }
}
```

### Authentication Service ###

By now we have finished the database access and implemented the hashing of passwords. Now we can define the service to perform the actual user authentication.

The Authenticatication service is going to access the database, and it is probably not the only service to do so. Let's create a base class, that holds a ``DatabaseFactory``.

```csharp
using TokenAuthentication.Infrastructure.Database;

namespace TokenAuthentication.Services
{
    public abstract class BaseService 
    {
        protected readonly IDatabaseFactory DatabaseFactory;

        protected BaseService(IDatabaseFactory databaseFactory)
        {
            DatabaseFactory = databaseFactory;
        }
    }
}
```

Now we define the interface for the authentication service, which takes user credentials and returns the UserIdentity.

```csharp
using TokenAuthentication.Infrastructure.Authentication;
using TokenAuthentication.Model;

namespace TokenAuthentication.Services
{
    public interface IAuthenticationService
    {
        bool TryAuthentifcate(Credentials request, out UserIdentity identity);
    }
}
```

Our implementation accesses the database and builds the ``UserIdentity`` for the given user name.

```csharp
using TokenAuthentication.Infrastructure.Authentication;
using TokenAuthentication.Infrastructure.Database;
using TokenAuthentication.Infrastructure.Database.Entities;
using TokenAuthentication.Model;
using Nancy.Security;
using NPoco;
using System.Collections.Generic;
using System.Linq;

namespace TokenAuthentication.Services
{
    /// <summary>
    /// Simple Database-based Authentification Service. 
    /// </summary>
    public class AuthenticationService : BaseService, IAuthenticationService
    {
        private readonly ICryptoService cryptoService;

        public AuthenticationService(IDatabaseFactory databaseFactory, ICryptoService cryptoService)
            : base(databaseFactory)
        {
            this.cryptoService = cryptoService;
        }

        public bool TryAuthentifcate(Credentials credentials, out Model.UserIdentity identity)
        {
            identity = null;

            using (var database = DatabaseFactory.GetDatabase())
            {
                User user = database.Query<User>().FirstOrDefault(x => x.Name == credentials.UserName);

                // Check if there is a User:
                if (user == null)
                {
                    return false;
                }

                // Make sure the Hashed Passwords match:
                if (user.PasswordHash != cryptoService.ComputeHash(credentials.Password, user.PasswordSalt))
                {
                    return false;
                }

                // We got a User, now obtain his claims from DB:
                IList<Claim> claims = database.Fetch<Claim>(@"
                                select c.*
                                from auth.user u 
                                    inner join auth.user_claim uc on u.user_id = uc.user_id
                                    inner join auth.claim c on uc.claim_id = c.claim_id
                                where u.user_id = @0", user.Id);
                
                // And return the UserIdentity:
                identity = Convert(user, claims);
                
                return true;
            }
        }

        /// <summary>
        /// Converts between Model and DB Entity.
        /// </summary>
        UserIdentity Convert(User user, IList<Claim> claims)
        {
            if (user == null)
            {
                return null;
            }
            return new UserIdentity()
            {
                Id = user.Id,
                Name = user.Name,
                Claims = Convert(claims)
            };
        }

        /// <summary>
        /// Converts between Model and DB Entity.
        /// </summary>
        IList<ClaimIdentity> Convert(IList<Claim> entities)
        {
            if (entities == null)
            {
                return null;
            }
            return entities.Select(x => Convert(x)).ToList();
        }

        /// <summary>
        /// Converts between Model and DB Entity.
        /// </summary>
        ClaimIdentity Convert(Claim entity)
        {
            return new ClaimIdentity()
            {
                Id = entity.Id,
                Type = entity.Type,
                Value = entity.Value
            };
        }
    }
}
```

### Registration Service ###

What's left is how to register a User. We build a very simple user registration service, so the registration request contains of a user name and password only.

```csharp
namespace TokenAuthentication.Requests
{
    public class RegisterUserRequest
    {
        public string UserName { get; set; }
        public string Password { get; set; }
    }
}
```

The Service has only a ``Register`` method.

```csharp
using TokenAuthentication.Requests;

namespace TokenAuthentication.Services
{
    public interface IRegistrationService
    {
        void Register(RegisterUserRequest register);
    }
}
```

The default database implementation creates a new User in the database and doesn't assign any claims.

```csharp
using TokenAuthentication.Infrastructure.Database;
using TokenAuthentication.Infrastructure.Database.Entities;
using TokenAuthentication.Requests;

namespace TokenAuthentication.Services
{
    /// <summary>
    /// An Authentication Service to authenticate incoming requests.
    /// </summary>
    public class RegistrationService : BaseService, IRegistrationService
    {
        private readonly ICryptoService cryptoService;

        public RegistrationService(IDatabaseFactory databaseFactory, ICryptoService cryptoService)
            : base(databaseFactory)
        {
            this.cryptoService = cryptoService;
        }

        public void Register(RegisterUserRequest register)
        {
            using (var database = DatabaseFactory.GetDatabase())
            {
                // Let's do this in a transaction, so we cannot register two users
                // with the same name. Seems to be a useful requirement.
                using (var tran = database.GetTransaction())
                {
                    string hashBase64;
                    string saltBase64;

                    cryptoService.CreateHash(register.Password, out hashBase64, out saltBase64);

                    User user = new User()
                    {
                        Name = register.UserName,
                        PasswordHash = hashBase64,
                        PasswordSalt = saltBase64
                    };

                    database.Insert(user);

                    tran.Complete();
                }
            }
        }
    }
}
```

#### Registration Module with Nancy ####

We create a new module, that uses the registration service. The built-in model binding of Nancy makes it easy to consume the request.

```csharp
using TokenAuthentication.Requests;
using TokenAuthentication.Services;
using Nancy;
using Nancy.ModelBinding;

namespace TokenAuthentication.Modules
{
    public class RegistrationModule : NancyModule
    {
        public RegistrationModule(IRegistrationService registrationService)
        {
            Post["/register"] = x =>
            {
                var request = this.Bind<RegisterUserRequest>();

                registrationService.Register(request);

                return Negotiate.WithStatusCode(HttpStatusCode.OK);
            };
        }
    }
}
```


## Implementing the OAuthAuthorizationServerProvider ##

Now we are implementing an ``OAuthAuthorizationServerProvider`` to use the custom authentication service we have built.

```csharp
using Microsoft.Owin.Security.OAuth;
using System.Security.Claims;
using System.Threading.Tasks;
using TokenAuthentication.Model;
using TokenAuthentication.Services;

namespace TokenAuthentication.Infrastructure.Authentication
{
    public class SimpleAuthorizationServerProvider : OAuthAuthorizationServerProvider
    {
        private readonly IAuthenticationService authService;

        public SimpleAuthorizationServerProvider(IAuthenticationService authService)
        {
            this.authService = authService;
        }

        public override Task ValidateClientAuthentication(OAuthValidateClientAuthenticationContext context)
        {
            context.Validated();

            return base.ValidateClientAuthentication(context);
        }

        public override Task GrantResourceOwnerCredentials(OAuthGrantResourceOwnerCredentialsContext context)
        { 
            if (!CredentialsAvailable(context))
            {
                context.SetError("invalid_grant", "User or password is missing.");

                return base.GrantResourceOwnerCredentials(context);
            }

            Credentials credentials = GetCredentials(context);

            UserIdentity userIdentity;
            if (authService.TryAuthentifcate(credentials, out userIdentity))
            {
                var oAuthIdentity = new ClaimsIdentity(context.Options.AuthenticationType);

                oAuthIdentity.AddClaim(new Claim(ClaimTypes.Name, userIdentity.Name));

                // Add Claims from DB:
                foreach (var claim in userIdentity.Claims)
                {
                    oAuthIdentity.AddClaim(new Claim(claim.Type, claim.Value));
                }

                context.Validated(oAuthIdentity);

                return base.GrantResourceOwnerCredentials(context);
            }
            else
            {
                context.SetError("invalid_grant", "Invalid credentials.");
                return base.GrantResourceOwnerCredentials(context);
            }
        }

        private bool CredentialsAvailable(OAuthGrantResourceOwnerCredentialsContext context)
        {
            if (string.IsNullOrWhiteSpace(context.UserName))
            {
                return false;
            }
            if (string.IsNullOrWhiteSpace(context.Password))
            {
                return false;
            }
            return true;
        }

        private Credentials GetCredentials(OAuthGrantResourceOwnerCredentialsContext context)
        {
            return new Credentials()
            {
                UserName = context.UserName,
                Password = context.Password
            };
        }
    }
}
```

The bearer token can be passed to the application in the request header or as a query parameter. Sometimes the bearer token cannot be passed through a header 
(SignalR, I am looking at you!), so we should look in different places for a token. I am using an implementation from 
[a stackoverflow post](http://stackoverflow.com/questions/22989209/web-api-owin-signalr-authorization) to inspect an incoming request.

```csharp
using Microsoft.Owin;
using Microsoft.Owin.Security.OAuth;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace TokenAuthentication.Infrastructure.Authentication
{
    /// <summary>
    /// We can't use Authorization Headers for a Websocket-scenario with SignalR. This only works in the long-polling scenario.
    /// 
    /// Instead we'll look for the Bearer Token in multiple locations:
    /// 
    ///     http://stackoverflow.com/questions/22989209/web-api-owin-signalr-authorization
    ///     
    /// </summary>
    public class OAuthTokenProvider : OAuthBearerAuthenticationProvider
    {
        private const string AuthHeader = "Authorization";

        private readonly List<Func<IOwinRequest, string>> locations;
        private readonly Regex bearerRegex = new Regex("((B|b)earer\\s)");
        
        /// <summary>
        /// By Default the Token will be searched for on the "Authorization" header.
        /// <para> pass additional getters that might return a token string</para>
        /// </summary>
        /// <param name="locations"></param>
        public OAuthTokenProvider(params Func<IOwinRequest, string>[] locations)
        {
            this.locations = locations.ToList();
            this.locations.Add(x => x.Headers.Get(AuthHeader));
        }

        public override Task RequestToken(OAuthRequestTokenContext context)
        {
            var getter = locations.FirstOrDefault(x => !String.IsNullOrWhiteSpace(x(context.Request)));
            if (getter != null)
            {
                var tokenStr = getter(context.Request);
                context.Token = bearerRegex.Replace(tokenStr, "").Trim();
            }
            return Task.FromResult<object>(null);
        }
    }
}
```

And now let's rewrite the Startup class to setup the authentication server.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Owin;
using Microsoft.Owin.Security.OAuth;
using Nancy.TinyIoc;
using Owin;
using System;
using TokenAuthentication.Infrastructure.Authentication;
using TokenAuthentication.Infrastructure.Database;
using TokenAuthentication.Services;

namespace TokenAuthentication
{
    public class Startup
    {
        public void Configuration(IAppBuilder app)
        {
            TinyIoCContainer container = new TinyIoCContainer();

            // Register Dependencies:
            RegisterDependencies(container);

            // Initialize Authentication:
            SetupAuth(app, container);

            // Initialize Nancy:
            SetupNancy(app, container);

        }

        private void RegisterDependencies(TinyIoCContainer container)
        {
            // Make some Registrations:
            container.Register<IMappingProvider, MappingProvider>();
            container.Register<IConnectionStringProvider, ConnectionStringProvider>();
            container.Register<IDatabaseFactory, DatabaseFactory>().AsSingleton();
            container.Register<IApplicationSettings, ApplicationSettings>();
            container.Register<ICryptoService, CryptoService>();
            container.Register<IRegistrationService, RegistrationService>();
            container.Register<IHashProvider, HashProvider>();
            container.Register<IAuthenticationService, AuthenticationService>();
        }

        private void SetupAuth(IAppBuilder app, TinyIoCContainer container)
        {
            var settings = container.Resolve<IApplicationSettings>();

            // Use default options:
            app.UseOAuthBearerAuthentication(new OAuthBearerAuthenticationOptions()
            {
                Provider = new OAuthTokenProvider(
                    req => req.Query.Get("bearer_token"),
                    req => req.Query.Get("access_token"),
                    req => req.Query.Get("token"),
                    req => req.Headers.Get("X-Token"))
            });

            // Register a Token-based Authentication for the App:            
            app.UseOAuthAuthorizationServer(new OAuthAuthorizationServerOptions
            {
                AllowInsecureHttp = true, // you should use this for debugging only
                TokenEndpointPath = new PathString(settings.TokenEndpointBasePath),
                AccessTokenExpireTimeSpan = TimeSpan.FromHours(8),
                Provider = new SimpleAuthorizationServerProvider(container.Resolve<IAuthenticationService>()),
            });
        }

        private void SetupNancy(IAppBuilder app, TinyIoCContainer container)
        {
            var settings = container.Resolve<IApplicationSettings>();

            app.Map(settings.NancyBasePath, siteBuilder => siteBuilder.UseNancy());
        }
    }
}
```

## Securing Nancy Modules ##

### ClaimsPrincipal Extensions ###

First of all we are defining two extension methods on the ``ClaimsPrincipal`` to make our life easy. 

```csharp
using System;
using System.Security.Claims;

namespace TokenAuthentication.Infrastructure.Authentication
{
    public static class PrincipalExtensions
    {
        public static bool HasClaim(this ClaimsPrincipal principal, string type)
        {
            if (principal == null)
            {
                return false;
            }
            return !String.IsNullOrEmpty(principal.GetClaimValue(type));
        }

        public static string GetClaimValue(this ClaimsPrincipal principal, string type)
        {
            Claim claim = principal.FindFirst(type);

            return claim != null ? claim.Value : null;
        }
    }
}
```

### ClaimsPrincipal in Nancy ###

The next step is to get the ``ClaimsPrincipal`` from the OWIN request context. An implementation for this is already available in the ``Nancy.MSOwinSecurity`` package, 
which can easily be installed with NuGet.

```csharp
Install-Package Nancy.MSOwinSecurity
```

Then we can create a ``SecureModule``, which makes it possible to get the ``ClaimsPrincipal`` by using the ``GetMSOwinUser`` property from the context.

```csharp
using Nancy;
using Nancy.Security;
using System.Security.Claims;

namespace TokenAuthentication.Infrastructure.Nancy
{
    public abstract class SecureModule : NancyModule
    {
        public SecureModule()
            : base()
        {
        }

        public SecureModule(string modulePath)
            : base(modulePath)
        {
        }

        protected ClaimsPrincipal Principal
        {
            get { return this.Context.GetMSOwinUser(); }
        }

        protected bool IsAuthenticated
        {
            get
            {
                if (Principal == null)
                {
                    return false;
                }
                if (Principal.Identity == null)
                {
                    return false;
                }
                return Principal.Identity.IsAuthenticated;
            }
        }
    }
}
```

### Authentication for Nancy Modules ###

The claims we want to check have to defined somewhere. I opted for defining them as constants in a static class.

```csharp
namespace TokenAuthentication.Infrastructure.Authentication
{
    public static class SampleClaimTypes
    {
        public const string Admin = "urn:sample:admin";
    }
}
```

And then we can secure the Hello World module to allow access for authenticated users only.

```csharp
using Nancy;
using TokenAuthentication.Infrastructure.Authentication;
using TokenAuthentication.Infrastructure.Nancy;

namespace TokenAuthentication.Modules
{
    public class HelloWorldModule : SecureModule
    {
        public HelloWorldModule()
        {
            Get["/admin"] = _ =>
            {
                if (!this.Principal.HasClaim(SampleClaimTypes.Admin))
                {
                    return HttpStatusCode.Forbidden;
                }

                return "Hello Admin!";
            };

            Get["/"] = _ =>
            {
                if (!IsAuthenticated)
                {
                    return HttpStatusCode.Forbidden;
                }

                return "Hello User!";
            };   
        }
    }
}
``` 

## Demo ##

[cURL](http://curl.haxx.se/) is a great tool for working with HTTP requests.

### User Registeration  ###

Store the following content to a file called ``user_password.json``.

```
{
  "username" : "philipp_wagner",
  "password" : "test_pwd"
}
```

And then we can register the user at the server.

```
curl --verbose -H "Content-Type: application/json" --data @user_password.json http://localhost:8080/api/register
```

### Obtaining Tokens ###

We have registered a user at the web service, so now we can obtain a token to make authenticated requests.

```
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=password" -d "username=philipp_wagner" -d "password=test_pwd" http://localhost:8080/token
```

And the ``token`` endpoint returns the generated token:

```
< HTTP/1.1 200 OK
< Cache-Control: no-cache
< Pragma: no-cache
< Content-Length: 495
< Content-Type: application/json;charset=UTF-8
< Expires: -1
* Server Microsoft-HTTPAPI/2.0 is not blacklisted
< Server: Microsoft-HTTPAPI/2.0
< Date: Sat, 29 Aug 2015 13:16:06 GMT
<
{"access_token":"AQAAANCMnd8BFdERjHoAwE_Cl-sBAAAAI7O4UaGSa063cCfCsbk32AAAAAACAAA
AAAAQZgAAAAEAACAAAABoUeoi5FHKTEkkH2H0skU7-WQV-c1RaLppQBb69on6kgAAAAAOgAAAAAIAACA
AAADeUE498RjGyTNZyN_srtj6e-6CPruSeltuHonouECsJ3AAAABoGO-INRh3liV_btaDgDwAceK3J_N
2x0VQbkZHkSzmDh88tfBkZcz7Fn5gqYLEQ5HVdbRMYDKXvuwCS8ctbyJN_qXv0EaKnPN6ASLavuzuvi9
yL59f5C-f2pvcOQ91WcfNJd9ZtV230UossdukSuvOQAAAAHeheBv7ZUQAlAsmCElNFsnkrTNTq30og1a
4iL9jKd62CQXSdsJqc2w1YYg7ls3uWeeMntIF-hUJq58QWQmqFSc","token_type":"bearer","exp
ires_in":28799}
```

Cool!

### Authenticated Requests ###

Sending a request without an access token leads to a HTTP Status Code ``403`` (Forbidden).

```
curl -v http://localhost:8080/api

< HTTP/1.1 403 Forbidden
```

If we pass the Access Token in the header, we will be greeted with a ``Hello User!``.

```
curl -v -H "Authorization: Bearer <Obtained Token>" http://localhost:8080/api

< HTTP/1.1 200 OK
< Content-Type: text/html
< Date: Sat, 29 Aug 2015 13:23:13 GMT
<
Hello User!
```

### Assigning Claims (Admin Claim) ###

First of all, we need to assign the registered user to the ``Admin`` claim. We can use a SQL query for this:

```
insert into auth.user_claim(user_id, claim_id) values (
    (
        select user_id 
        from auth.user
        where name='philipp_wagner'
    ),
    (
        select claim_id
        from auth.claim
        where type='urn:sample:admin'
    )
);
```

When the claim is added to a user, a fresh token has to be obtained. The above cURL Request can be used. 
The new token will contain the claim with the Admin type. If the Access Token is passed to the ``/admin`` 
endpoint, we will be greeted with a ``Hello Admin!``.

```
curl -v -H "Authorization: Bearer <Obtained Token>" http://localhost:8080/api/admin

< HTTP/1.1 200 OK
< Content-Type: text/html
< Date: Sat, 29 Aug 2015 13:23:13 GMT
<
Hello Admin!
```

## Conclusion ##

And that's it! Once you get over the initial problems with OWIN, it is really nice to work with. It was easy to integrate Nancy into the OWIN Pipeline 
and secure the Nancy modules with the ClaimsPrincipal. I hope sharing this code is useful and saves some time.