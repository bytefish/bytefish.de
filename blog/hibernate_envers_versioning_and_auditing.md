title: Versioning and Auditing with Hibernate Envers
date: 2017-10-17 10:53
tags: java, hibernate, envers, spring
category: java
slug: hibernate_envers_versioning_and_auditing
author: Philipp Wagner
summary: This article shows how to provide Versioning and Auditing with Hibernate Envers.

[Hibernate Envers]: http://hibernate.org/orm/envers/)

In this post I will show you how to provide versioning and auditing with [Hibernate Envers].

It was quite hard to get everything right with [Hibernate Envers], so I am sharing a sample application at:

* [https://github.com/bytefish/VersioningWithEnvers](https://github.com/bytefish/VersioningWithEnvers)

This article explains the concepts behind the application.

## Database ##

I am using PostgreSQL for this example.

### Creating the Database ###

First of all create the user ``philipp`` for connecting to the database:

```
PS C:\Users\philipp> psql -U postgres
psql (9.4.1)
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
```

Then we can create the database ``sampledb`` and set the owner to ``philipp``:

```
postgres=# CREATE DATABASE sampledb
postgres-#   WITH OWNER philipp;
CREATE DATABASE
```

### Creating the Schema and Tables ###

The GitHub sample has a Batch Script (Windows users) and a Shell Script (Mac / Linux Users) to create the schemas and tables:

* [VersioningWithEnvers/sql](https://github.com/bytefish/VersioningWithEnvers/tree/master/VersioningWithEnvers/sql)

You simply need to exectute the script and enter the database name ``sampledb`` and the user credentials.

If you prefer to create the database manually, then the next sections will show the schema and table definitions.

#### Schema ####

```sql
IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'sample') THEN

    CREATE SCHEMA sample;

END IF;
```

#### Tables ####

There are three tables in the Schema:

* ``sample.customer``
    * The Customer Data, which is the current data.
* ``sample.customer_aud``
    * The audited customer table, which includes the log of changes to the data.
* ``sample.revinfo``
    * Holds the current revision number and the revision timestamp.

```sql
IF NOT EXISTS (
    SELECT 1 
    FROM information_schema.tables 
    WHERE  table_schema = 'sample' 
    AND table_name = 'customer'
) THEN

CREATE TABLE sample.customer
(
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    created_by VARCHAR(255),
    created_at TIMESTAMP,
    last_modified_by VARCHAR(255),
    last_modified_at TIMESTAMP
);

END IF;

IF NOT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE  table_schema = 'sample'
    AND table_name = 'customer_aud'
) THEN

CREATE TABLE sample.customer_aud
(
    customer_id SERIAL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    created_by VARCHAR(255),
    created_at TIMESTAMP,
    last_modified_by VARCHAR(255),
    last_modified_at TIMESTAMP,
    rev integer NOT NULL,
    revtype smallint
);

END IF;

IF NOT EXISTS (
	SELECT 1
	FROM information_schema.tables
	WHERE  table_schema = 'sample'
	AND table_name = 'revinfo'
) THEN

CREATE TABLE sample.revinfo
(
    revision_number integer NOT NULL,
    revision_timestamp bigint,
    CONSTRAINT revinfo_pkey PRIMARY KEY (revision_number)
);

END IF;
```

#### Sequences ####

Hibernate Envers needs a ``SEQUENCE`` named ``hibernate_sequence`` to increase the revision number 
for versioned entities. This sequence can be created with the ``CREATE SEQUENCE`` SQL Statement.

```sql
IF NOT EXISTS (
    SELECT 0 FROM pg_class where relname = 'hibernate_sequence'
) THEN

CREATE SEQUENCE hibernate_sequence  INCREMENT 1  MINVALUE 1
  MAXVALUE 9223372036854775807
  START 1
  CACHE 1;

END IF;
```

## The Spring Boot Application ##

### Project Structure ###

It's useful to take a look at the project structure first:

<a href="/static/images/blog/hibernate_envers_versioning_and_auditing/project_structure.jpg">
	<img class="mediacenter" src="/static/images/blog/hibernate_envers_versioning_and_auditing/project_structure.jpg" alt="Project Overview" />
</a>

The purpose of the various classes:

* ``audit``
    * ``model``
        * ``CustomRevisionEntity``
            * The base class for Revision Entities with the revision number and revision timestamp.
        * ``SampleRevisionEntity``
            * The Revision Entity for the application, which defines the mapping to the ``sample.revinfo`` table.
    * ``query``
        * ``AuditQueryResult``
            * A container for the Results of an Audit Query. It holds the audited entity data, the revision and the revision type.
        * ``AuditQueryResultUtils``
            * The ``AuditQuery`` results of Hibernate Envers are simply ``Object[]``, which makes it hard to work with in the application. This class provides methods to convert between the untyped ``Object[]`` and turns it into a strongly typed ``AuditQueryResult``.
        * ``AuditQueryUtils``
            * An ``AuditQuery`` returns a List of untyped ``Object[]``. This class provides a utility method to turn the untyped ``AuditQuery`` result list into a strongly typed list of ``AuditQueryResult``.
    * ``ThreadLocalStorageAuditorAware``
        * This class is necessary to provide the information, which user added / modified / deleted data. It implements ``AuditorAware`` interface.
* ``exceptions``
    * ``MissingUsernameException``
        * The application needs to be given a Username for being able to audit data. This exception is thrown, if no Username was given to the application. 
* ``model``
    * ``Customer``
        * The Customer data.
    * ``CustomerHistory``
        * The Customer History, which basically maps to the audited ``Customer`` table (``sample.customer_aud``).
* ``repositories``
    * ``audit``
        * ``ICustomerHistoryRepository``
            * The interface for accessing the auditioned customer table, and getting the audition and versioned data.
        * ``CustomerHistoryRepository``
            * The implementation of the ``ICustomerHistoryRepository``
    * * ``ICustomerRepository``
        * The ``ICustomerRepository`` for adding, modifying and deleting Customers.
* ``web``
    * ``configuration``
        * ``JerseyConfig``
            * Registers the Jersey components for the application.
    * ``converter``
        * ``Converters``
            * Converts between the Domain Model and the Data Transfer Objects.
    * ``errors``
        * ``ServiceError``
            * A JSON Representation of a service error, which will be sent to the client in case of an Exception.
    * ``exceptions``
        * ``GeneralExceptionMapper``
            * An Exception handler, that handles uncaught exceptions thrown up to the Web layer. It returns the message to the user and does not send the stack trace to the user.
    * ``filters``
        * ``UserNameFilter``
            * Extracts the Username information from the incoming HTTP Request, which is given in the HTTP Header ``X-Username``.
    * ``model``
        * ``CustomerDto``
            * The Data Transfer Object for the Customer.
        * ``CustomerHistoryDto``
            * The Data Transfer Object for the Customer History.
        * ``RevisionTypeDto``
            * The Data Transfer Object for the Revision Type.
    * ``resources``
        * ``CustomerHistoryResource``
            * The resource for accessing the auditioned and versioned customer data.
        * ``CustomerResource``
            * The resource for adding, modifying and deleting customers.
* ``SampleJerseyApplication``
    * The Spring Boot application, that plugs everything together and configures the JPA components.
    
### Auditing ###

#### Revision Entities ####

Hibernate Envers needs a Revision Entity, which maps to the revision table in the database. This is where Hibernate Envers 
writes the revision information to. I want to provide generic methods for working with Hibernate Envers, so I will define 
a base class ``CustomRevisionEntity``.

This class simply provides the Revision Number (maps to ``revision_number`` in the database) and the Revision Timestamp 
(maps to ``revision_timestamp``). The framework needs to know, that the class provides database mappings. That's why 
we need to add a ``MappedSuperclass`` annotation.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.audit.model;

import org.hibernate.envers.RevisionNumber;
import org.hibernate.envers.RevisionTimestamp;

import javax.persistence.*;
import java.io.Serializable;
import java.text.DateFormat;
import java.util.Date;

@MappedSuperclass
public class CustomRevisionEntity implements Serializable {

    private static final long serialVersionUID = 8530213963961662300L;

    @Id
    @RevisionNumber
    @GeneratedValue
    @Column(name = "revision_number")
    private int revisionNumber;

    @RevisionTimestamp

    @Column(name = "revision_timestamp")
    private long revisionTimestamp;

    public CustomRevisionEntity() {
    }

    public int getRevisionNumber() {
        return this.revisionNumber;
    }

    @Transient
    public Date getRevisionDate() {
        return new Date(this.revisionTimestamp);
    }

    public boolean equals(Object o) {
        if (this == o) {
            return true;
        } else if (!(o instanceof CustomRevisionEntity)) {
            return false;
        } else {
            CustomRevisionEntity that = (CustomRevisionEntity) o;
            return this.revisionNumber == that.revisionNumber && this.revisionTimestamp == that.revisionTimestamp;
        }
    }

    public int hashCode() {
        int result = this.revisionNumber;
        result = 31 * result + (int) (this.revisionTimestamp ^ this.revisionTimestamp >>> 32);
        return result;
    }

    public String toString() {
        return "CustomRevisionEntity(revisionNumber = " + this.revisionNumber + ", revisionDate = " + DateFormat.getDateTimeInstance().format(this.getRevisionDate()) + ")";
    }
}
```

Now that the base class is defined, we can define the Revision Entity for our application. This Entity 
maps to the ``sample.revinfo`` table of the database.

```java
package de.bytefish.envers.audit.model;

import org.hibernate.envers.RevisionEntity;

import javax.persistence.Entity;
import javax.persistence.Table;
import java.text.DateFormat;

@Entity
@RevisionEntity
@Table(schema = "sample", name = "revinfo")
public class SampleRevisionEntity extends CustomRevisionEntity {

    public SampleRevisionEntity() {
    }

    public String toString() {
        return "SampleRevisionEntity(revisionNumber = " + getRevisionNumber() + ", revisionDate = " + DateFormat.getDateTimeInstance().format(this.getRevisionDate()) + ")";
    }
}
```

#### AuditQuery Utilities ####

Hibernate Envers uses an ``AuditQuery`` to query audited tables. Hibernate Envers is very flexible, so the results of an 
``AuditQuery`` results have to be quite generic. The Result List of an ``AuditQuery`` simply is an untyped ``List``, which is almost 
impossible to work with nicely. 

That's why I define a class ``AuditQueryResult``, that provides strongly typed access to the versioned entity, the revision and the 
RevisionType:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.audit.query;

import de.bytefish.envers.audit.model.CustomRevisionEntity;
import org.hibernate.envers.RevisionType;

public class AuditQueryResult<T> {

    private final T entity;
    private final CustomRevisionEntity revision;
    private final RevisionType type;

    public AuditQueryResult(T entity, CustomRevisionEntity revision, RevisionType type) {
        this.entity = entity;
        this.revision = revision;
        this.type = type;
    }

    public T getEntity() {
        return entity;
    }

    public CustomRevisionEntity getRevision() {
        return revision;
    }

    public RevisionType getType() {
        return type;
    }
}
```

The application has to map between the ``Object[]`` of the ``AuditQuery`` and our ``AuditQueryResult``. This is done in the 
``AuditQueryResultUtils`` class, which safely converts between both representations:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.audit.query;

import de.bytefish.envers.audit.model.CustomRevisionEntity;
import org.hibernate.envers.RevisionType;

public class AuditQueryResultUtils {

    private AuditQueryResultUtils() {}

    public static <TTargetType> AuditQueryResult<TTargetType> getAuditQueryResult(Object[] item, Class<TTargetType> type) {

        // Early exit, if no item given:
        if(item == null) {
            return null;
        }

        // Early exit, if there is not enough data:
        if(item.length < 3) {
            return null;
        }

        // Cast item[0] to the Entity:
        TTargetType entity = null;
        if(type.isInstance(item[0])) {
            entity = type.cast(item[0]);
        }

        // Then get the Revision Entity:
        CustomRevisionEntity revision = null;
        if(item[1] instanceof CustomRevisionEntity) {
            revision = (CustomRevisionEntity) item[1];
        }

        // Then get the Revision Type:
        RevisionType revisionType = null;
        if(item[2] instanceof RevisionType) {
            revisionType = (RevisionType) item[2];
        }

        // Build the Query Result:
        return new AuditQueryResult<TTargetType>(entity, revision, revisionType);
    }
}
```

And what's left is mapping the list of ``Object[]`` into a list of ``AuditQueryResult``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.audit.query;

import org.hibernate.envers.query.AuditQuery;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class AuditQueryUtils {

    private AuditQueryUtils() {
    }

    public static <TTargetType> List<AuditQueryResult<TTargetType>> getAuditQueryResults(AuditQuery query, Class<TTargetType> targetType) {

        List<?> results = query.getResultList();

        if (results == null) {
            return new ArrayList<>();
        }

        // The AuditReader returns a List of Object[], where the indices are:
        //
        // 0 - The queried entity
        // 1 - The revision entity
        // 2 - The Revision Type
        //
        // We cast it into something useful for a safe access:
        return results.stream()
                // Only use Object[] results:
                .filter(x -> x instanceof Object[])
                // Then convert to Object[]:
                .map(x -> (Object[]) x)
                // Transform into the AuditQueryResult:
                .map(x -> AuditQueryResultUtils.getAuditQueryResult(x, targetType))
                // And collect the Results into a List:
                .collect(Collectors.toList());
    }
}
```

#### Determining the Current Auditor ####

Somehow Hibernate Envers needs to know which user has added, modified or deleted data. Hibernate Envers requires you to 
implement the ``AuditorAware`` interface for providing the username at runtime. The implementation in the sample 
application is the ``ThreadLocalStorageAuditorAware``.

I am using the ``RequestContextHolder`` to transport the Username information through the application. It is a Web application 
and all actions happen inside the Request Scope. So I think the ``RequestContextHolder`` is an appropiate place to store the 
user data in.

However you can easily switch to your own implementation by implementing the ``AuditorAware`` interface.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.audit;

import org.springframework.data.domain.AuditorAware;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;

import static org.springframework.web.context.request.RequestAttributes.SCOPE_REQUEST;

@Component
public class ThreadLocalStorageAuditorAware implements AuditorAware<String> {

    @Override
    public String getCurrentAuditor() {
        return (String) RequestContextHolder
                .currentRequestAttributes()
                .getAttribute("Username", SCOPE_REQUEST);
    }

}
```

### Domain ###

#### Domain Model ####

The ``Customer`` entity models the customer managed by the sample application. The entity only has a few properties to keep the example simple.

There are a few things to note here:

* The Entity needs to be annotated with the ``@Audited`` annotation.
* The Entity needs to be annotated with the ``@EntityListeners`` attribute, so the events are registered.
* The Entity has properties and annotations to write:
    * The creator of the data (``@CreatedBy``)
    * The creation date (``@CreatedAt``)
    * The user that modified the data (``@LastModifiedBy``)
    * The modification date (``@LastModifiedDate``)

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.model;

import org.hibernate.envers.Audited;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import javax.persistence.*;
import java.util.Date;

@Entity
@Audited
@EntityListeners({AuditingEntityListener.class})
@Table(schema = "sample", name = "customer")
public class Customer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "customer_id")
    private Long id;

    @Column(name = "first_name")
    private String firstName;

    @Column(name = "last_name")
    private String lastName;

    @CreatedBy
    @Column(name = "created_by")
    private String createdBy;

    @CreatedDate
    @Column(name = "created_at")
    private Date createdAt;

    @LastModifiedBy
    @Column(name = "last_modified_by")
    private String lastModifiedBy;

    @LastModifiedDate
    @Column(name = "last_modified_at")
    private Date lastModifiedAt;

    protected Customer() {}

    public Customer(Long id, String firstName, String lastName) {
        this.id = id;
        this.firstName = firstName;
        this.lastName = lastName;
    }

    public Long getId() {
        return id;
    }

    public String getFirstName() {
        return firstName;
    }

    public String getLastName() {
        return lastName;
    }
}
```

The Auditing Table ``sample.customer_aud`` contains the customer entity data of the revision, the revision entity and 
the revision type. The ``CustomerHistory`` class models this domain entity, by wrapping all this data. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.model;

import org.hibernate.envers.RevisionType;

public class CustomerHistory {

    private final Customer customer;
    private final Number revision;
    private final RevisionType revisionType;

    public CustomerHistory(Customer customer, Number revision, RevisionType revisionType) {
        this.customer = customer;
        this.revision = revision;
        this.revisionType = revisionType;
    }

    public Customer getCustomer() {
        return customer;
    }

    public Number getRevision() {
        return revision;
    }

    public RevisionType getRevisionType() {
        return revisionType;
    }
}
```

#### Repositories ####

Adding CRUD functionality is simple with Spring Boot, which provides a so called ``CrudRepository``. You simply extend from the 
``CrudRepository`` interface and Spring automatically provides all CRUD functionality for your entity.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.repositories;

import de.bytefish.envers.model.Customer;
import org.springframework.data.repository.CrudRepository;

public interface ICustomerRepository extends CrudRepository<Customer, Long> {
}
```

The ``ICustomerHistoryRepository`` interface returns a List of ``CustomerHistory``, which is the auditioning and version history for 
the ``Customer`` table.


```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.repositories.audit;

import de.bytefish.envers.model.CustomerHistory;

import java.util.List;

public interface ICustomerHistoryRepository {

    List<CustomerHistory> listCustomerRevisions(Long stationId);

}
```

The implementation uses the Hibernate Envers ``AuditReader`` to create an ``AuditQuery``. The results are mapped into 
an ``AuditQueryResult`` using the ``AuditQueryUtils`` we defined at the very beginning of the tutorial.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.repositories.audit;

import de.bytefish.envers.audit.query.AuditQueryResult;
import de.bytefish.envers.audit.query.AuditQueryUtils;
import de.bytefish.envers.model.Customer;
import de.bytefish.envers.model.CustomerHistory;
import org.hibernate.envers.AuditReader;
import org.hibernate.envers.AuditReaderFactory;
import org.hibernate.envers.query.AuditEntity;
import org.hibernate.envers.query.AuditQuery;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;
import java.util.List;
import java.util.stream.Collectors;

@Component
public class CustomerHistoryRepository implements ICustomerHistoryRepository {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional(readOnly = true)
    public List<CustomerHistory> listCustomerRevisions(Long customerId) {

        // Create the Audit Reader. It uses the EntityManager, which will be opened when
        // starting the new Transation and closed when the Transaction finishes.
        AuditReader auditReader = AuditReaderFactory.get(entityManager);

        // Create the Query:
        AuditQuery auditQuery = auditReader.createQuery()
                .forRevisionsOfEntity(Customer.class, false, true)
                .add(AuditEntity.id().eq(customerId));

        // We don't operate on the untyped Results, but cast them into a List of AuditQueryResult:
        return AuditQueryUtils.getAuditQueryResults(auditQuery, Customer.class).stream()
                // Turn into the CustomerHistory Domain Object:
                .map(x -> getCustomerHistory(x))
                // And collect the Results:
                .collect(Collectors.toList());
    }

    private static CustomerHistory getCustomerHistory(AuditQueryResult<Customer> auditQueryResult) {
        return new CustomerHistory(
                auditQueryResult.getEntity(),
                auditQueryResult.getRevision().getRevisionNumber(),
                auditQueryResult.getType()
        );
    }

}
```

### The Web Layer ###

#### Reading the Username ####

There are several ways to extract a username from an incoming request (Basic Authentication, Tokens, ...). In the example the 
Webservice client passes the username with a HTTP Header named ``X-Username``. With Jersey you can implement a 
``ContainerRequestFilter`` to intercept an incoming request and extract data from it.

The ``UserNameFilter`` reads the ``X-Username`` header and stores the name in the ``RequestContextHolder``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.filters;


import de.bytefish.envers.exceptions.MissingUsernameException;
import org.hibernate.Session;
import org.springframework.web.context.request.RequestContextHolder;

import javax.ws.rs.container.ContainerRequestContext;
import javax.ws.rs.container.ContainerRequestFilter;
import javax.ws.rs.core.MultivaluedMap;
import javax.ws.rs.ext.Provider;
import java.io.IOException;

import static org.springframework.web.context.request.RequestAttributes.SCOPE_REQUEST;

@Provider
public class UserNameFilter implements ContainerRequestFilter {

    Session session;

    @Override
    public void filter(ContainerRequestContext ctx) throws IOException {

        MultivaluedMap<String, String> headers = ctx.getHeaders();

        if(headers == null) {
            handleError(ctx);
        }

        if(!headers.containsKey("X-Username")) {
            handleError(ctx);
        }

        String username = headers.getFirst("X-Username");

        if(username == null) {
            handleError(ctx);
        }

        // Set the Username in the current Request Scope:
        RequestContextHolder
                .currentRequestAttributes()
                .setAttribute("Username", username, SCOPE_REQUEST);
    }

    public void handleError(ContainerRequestContext ctx) {
        throw new MissingUsernameException("Request is missing a Username");
    }
}
```

Auditing the application without a Username is not possible. So if a Username is missing, we need to throw an exception.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.exceptions;

public class MissingUsernameException extends RuntimeException {

    public MissingUsernameException() {
    }

    public MissingUsernameException(String message) {
        super(message);
    }

    public MissingUsernameException(String message, Throwable cause) {
        super(message, cause);
    }

}
```

Spring Boot will return the Stacktrace of an Exception by default. But returning the entire Stacktrace to the User is never 
a good idea. It can leak details, that should be better kept out of sight. That's why we are implementing the Jersey 
``ExceptionMapper``, which handles the most generic ``Exception``.

It creates a ``ServiceError`` and assigns the HTTP Status Code 400 (Bad Request) to the response:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.exceptions;

import de.bytefish.envers.web.errors.ServiceError;
import javax.ws.rs.core.Response;
import javax.ws.rs.ext.ExceptionMapper;

public class GeneralExceptionMapper implements ExceptionMapper<Exception> {

    @Override
    public Response toResponse(Exception e) {
        return Response
                .status(400)
                .entity(new ServiceError(e.getMessage()))
                .build();
    }

}
```

The ``ServiceError`` is a simple Data Transfer Object, which only has a message:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.errors;

import com.fasterxml.jackson.annotation.JsonProperty;

public class ServiceError {

    private final String message;

    public ServiceError(String message) {
        this.message = message;
    }

    @JsonProperty("message")
    public String getMessage() {
        return message;
    }
}
```

#### Data Transfer Objects and Converters ####

You should always separate your Web Layer from the Domain Layer. The Web layer should only care about receiving and sending 
Data Transfer Objects to the consumer. It should know how to convert between the Data Transfer Object and the Domain model, 
so it can use the Domain repositories.

The ``CustomerDto`` Data Transfer Object uses Jackson annotations to provide the JSON mapping.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;

import javax.persistence.Column;
import java.util.Date;

public class CustomerDto {

    private final Long id;

    private final String firstName;

    private final String lastName;

    @JsonCreator
    public CustomerDto(@JsonProperty("id") Long id, @JsonProperty("firstName") String firstName, @JsonProperty("lastName") String lastName) {
        this.id = id;
        this.firstName = firstName;
        this.lastName = lastName;
    }

    @JsonProperty("id")
    public Long getId() {
        return id;
    }

    @JsonProperty("firstName")
    public String getFirstName() {
        return firstName;
    }

    @JsonProperty("lastName")
    public String getLastName() {
        return lastName;
    }
}
```

You don't want to return ``0``, ``1`` or ``2`` as revision type of the auditioned entity. The ``RevisionTypeDto`` is an 
enum with Jackson ``@JsonProperties`` annotations for the ``ADD``, ``MOD`` and ``DEL`` operations:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum RevisionTypeDto {

    @JsonProperty("add")
    ADD,

    @JsonProperty("mod")
    MOD,

    @JsonProperty("del")
    DEL
}
```

And the ``CustomerHistoryDto`` now wraps the ``CustomerDto``, the revision number and revision type:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class CustomerHistoryDto {

    private final CustomerDto customer;
    private final Long revision;
    private final RevisionTypeDto type;

    public CustomerHistoryDto(CustomerDto customer, Long revision, RevisionTypeDto type) {
        this.customer = customer;
        this.revision = revision;
        this.type = type;
    }

    @JsonProperty("customer")
    public CustomerDto getCustomer() {
        return customer;
    }

    @JsonProperty("revision")
    public Long getRevision() {
        return revision;
    }

    @JsonProperty("type")
    public RevisionTypeDto getType() {
        return type;
    }
}
```

The ``Converters`` class provides all methods necessary to convert between the Domain Transfer Objects and the Domain model:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.converter;

import de.bytefish.envers.model.Customer;
import de.bytefish.envers.model.CustomerHistory;
import de.bytefish.envers.web.model.CustomerDto;
import de.bytefish.envers.web.model.CustomerHistoryDto;
import de.bytefish.envers.web.model.RevisionTypeDto;
import org.hibernate.envers.RevisionType;

public class Converters {

    public static CustomerDto convert(Customer source) {

        if(source == null) {
            return null;
        }

        return new CustomerDto(source.getId(), source.getFirstName(), source.getLastName());
    }

    public static Customer convert(CustomerDto source) {

        if(source == null) {
            return null;
        }

        return new Customer(source.getId(), source.getFirstName(), source.getLastName());
    }

    public static RevisionTypeDto convert(RevisionType source) {

        if(source == null) {
            return null;
        }

        switch (source) {
            case ADD:
                return RevisionTypeDto.ADD;
            case MOD:
                return RevisionTypeDto.MOD;
            case DEL:
                return RevisionTypeDto.DEL;
            default:
                throw new IllegalArgumentException("source");
        }
    }

    public static CustomerHistoryDto convert(CustomerHistory source) {

        if(source == null) {
            return null;
        }

        CustomerDto customerDto = convert(source.getCustomer());
        Long revision = source.getRevision().longValue();
        RevisionTypeDto revisionTypeDto = convert(source.getRevisionType());

        return new CustomerHistoryDto(customerDto, revision, revisionTypeDto);
    }
}
```



#### Resources ####

Implementing the RESTful Webservice with Jersey is now easy. It basically boils down to injecting the correct 
repository and use the ``Converters`` class to map between entity representations:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.resources;

import de.bytefish.envers.model.Customer;
import de.bytefish.envers.repositories.ICustomerRepository;
import de.bytefish.envers.web.converter.Converters;
import de.bytefish.envers.web.model.CustomerDto;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.security.RolesAllowed;
import javax.ws.rs.*;
import javax.ws.rs.core.MediaType;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Component
@Path("/customers")
public class CustomerResource {

    private final ICustomerRepository repository;

    @Autowired
    public CustomerResource(ICustomerRepository repository) {
        this.repository = repository;
    }

    @GET
    @Produces(MediaType.APPLICATION_JSON)
    public List<CustomerDto> getAll() {
        // Return the DTO List:
        return StreamSupport.stream(repository.findAll().spliterator(), false)
                .map(Converters::convert)
                .collect(Collectors.toList());
    }

    @GET
    @Path("{id}")
    @Produces(MediaType.APPLICATION_JSON)
    public CustomerDto get(@PathParam("id") long id) {
        Customer customer = repository.findOne(id);

        // Return the DTO:
        return Converters.convert(customer);
    }

    @POST
    @Produces(MediaType.APPLICATION_JSON)
    public CustomerDto post(CustomerDto customer) {
        // Convert to the Domain Object:
        Customer source = Converters.convert(customer);

        // Store the Entity:
        Customer result = repository.save(source);

        // Return the DTO:
        return Converters.convert(result);
    }

    @DELETE
    @Path("{id}")
    @Produces(MediaType.APPLICATION_JSON)
    public void delete(@PathParam("id") long id) {
        repository.delete(id);
    }
}
```

The history of a Customer can be queried at the ``/history/customer/{id}`` endpoint. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.resources;


import de.bytefish.envers.model.CustomerHistory;
import de.bytefish.envers.repositories.audit.ICustomerHistoryRepository;
import de.bytefish.envers.web.converter.Converters;
import de.bytefish.envers.web.model.CustomerHistoryDto;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;
import java.util.List;
import java.util.stream.Collectors;

@Component
@Path("/history")
public class CustomerHistoryResource {

    private final ICustomerHistoryRepository repository;

    @Autowired
    public CustomerHistoryResource(ICustomerHistoryRepository repository) {
        this.repository = repository;
    }

    @GET
    @Path("customer/{id}")
    @Produces(MediaType.APPLICATION_JSON)
    public List<CustomerHistoryDto> getHistory(@PathParam("id") Long id) {
        // Get History:
        List<CustomerHistory> history = repository.listCustomerRevisions(id);

        // Return the DTO List:
        return history.stream()
                .map(Converters::convert)
                .collect(Collectors.toList());
    }
}

```

#### Configuration ####

Finally the Filters, Resources and Exception handlers need to be registered. This is done by extending the ``JerseyConfig`` class. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.envers.web.configuration;

import de.bytefish.envers.web.exceptions.GeneralExceptionMapper;
import de.bytefish.envers.web.filters.UserNameFilter;
import de.bytefish.envers.web.resources.CustomerHistoryResource;
import de.bytefish.envers.web.resources.CustomerResource;
import org.glassfish.jersey.server.ResourceConfig;
import org.springframework.stereotype.Component;

/**
 * Jersey Configuration (Resources, Modules, Filters, ...)
 */
@Component
public class JerseyConfig extends ResourceConfig {

    public JerseyConfig() {

        // Register the Filters:
        register(UserNameFilter.class);

        // Register the Resources:
        register(CustomerResource.class);
        register(CustomerHistoryResource.class);

        // Register Exception Handlers:
        register(GeneralExceptionMapper.class);


        // Uncomment to disable WADL Generation:
        //property("jersey.config.server.wadl.disableWadl", true);

        // Uncomment to add Request Tracing:
        //property("jersey.config.server.tracing.type", "ALL");
        //property("jersey.config.server.tracing.threshold", "TRACE");
    }
}
```

### Plugging it together with Spring Boot ###

What's left is plugging everything together for the Spring Boot application. 

There are a few things to note:

* The ``SpringBootApplication`` needs to be annotated with the ``@EnableJpaAuditing`` annotation
* The following custom properties have to be set:
    * ``spring.jpa.properties.org.hibernate.envers.store_data_at_delete``
        * Save the audited entity on delete.
    * ``spring.jpa.hibernate.ddl-auto``
        * Prevent Hibernate from making any changes to the DDL Schema.

All other dependencies are automatically wired up by Spring Boot:
        
```java
package de.bytefish.envers;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.support.SpringBootServletInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.Properties;

@SpringBootApplication
@EnableJpaAuditing
@EnableTransactionManagement
public class SampleJerseyApplication extends SpringBootServletInitializer {

	public static void main(String[] args) {
		new SampleJerseyApplication()
				.configure(new SpringApplicationBuilder(SampleJerseyApplication.class))
				.properties(getDefaultProperties())
				.run(args);
	}


	@Bean
	public DataSource dataSource() {

		HikariDataSource dataSource = new HikariDataSource();

		dataSource.setInitializationFailTimeout(0);
		dataSource.setMaximumPoolSize(5);
		dataSource.setDataSourceClassName("org.postgresql.ds.PGSimpleDataSource");
		dataSource.addDataSourceProperty("url", "jdbc:postgresql://127.0.0.1:5432/sampledb");
		dataSource.addDataSourceProperty("user", "philipp");
		dataSource.addDataSourceProperty("password", "test_pwd");

		return dataSource;
	}

	private static Properties getDefaultProperties() {

		Properties defaultProperties = new Properties();

		// Set sane Spring Hibernate properties:
		defaultProperties.put("spring.jpa.show-sql", "true");
		defaultProperties.put("spring.jpa.hibernate.naming.physical-strategy", "org.hibernate.boot.model.naming.PhysicalNamingStrategyStandardImpl");
		defaultProperties.put("spring.datasource.initialize", "false");

		// Store Values on Delete:
		defaultProperties.put("spring.jpa.properties.org.hibernate.envers.store_data_at_delete", "true");

		// Prevent JPA from trying to Auto Detect the Database:
		defaultProperties.put("spring.jpa.database", "postgresql");

		// Prevent Hibernate from Automatic Changes to the DDL Schema:
		defaultProperties.put("spring.jpa.hibernate.ddl-auto", "none");

		return defaultProperties;
	}

}
```

## Example ##


We start by inserting a new Customer into the database. We are using the Username ``Philipp``, which is passed in the ``X-Username`` header:

```
> curl -H "X-Username: Philipp" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Philipp\", \"lastName\" : \"Wagner\"}"  http://localhost:8080/customers

{"id":26,"firstName":"Philipp","lastName":"Wagner"}
```

Now we can query the ``history`` resource for the customer. At the moment there is only one revision of type ``add``:

```
> curl -H "X-Username: Philipp" -X GET http://localhost:8080/history/customer/26

[{"customer":{"id":26,"firstName":"Philipp","lastName":"Wagner"},"revision":37,"type":"add"}]
```

Now let's change the last name from ``Wagner`` to ``Mustermann``:

```
> curl -H "X-Username: Philipp" -H "Content-Type: application/json" -X POST -d "{\"id\" : 26, \"firstName\" : \"Philipp\", \"lastName\" : \"Mustermann\"}"  http://localhost:8080/customers

{"id":26,"firstName":"Philipp","lastName":"Mustermann"}
```

And in the history we will now see a new revision ``38`` with the type ``mod`` in the history, which shows the modifications:

```
> curl -H "X-Username: Philipp" -X GET http://localhost:8080/history/customer/26

[{"customer":{"id":26,"firstName":"Philipp","lastName":"Wagner"},"revision":37,"type":"add"},{"customer":{"id":26,"firstName":"Philipp","lastName":"Mustermann"},"revision":38,"type":"mod"}]
```

And if we finally delete the Customer:

```
> curl -H "X-Username: Philipp" -X DELETE http://localhost:8080/customers/26
```

Then we will see a new revision ``42`` with the type ``del`` in the results:

```
> curl -H "X-Username: Philipp" -X GET http://localhost:8080/history/customer/26

[{"customer":{"id":26,"firstName":"Philipp","lastName":"Wagner"},"revision":37,"type":"add"},{"customer":{"id":26,"firstName":"Philipp","lastName":"Mustermann"},"revision":38,"type":"mod"},{"customer":{"id":26,"firstName":"Philipp","lastName":"Mustermann"},"revision":42,"type":"del"}]
```

## Conclusion ##

Hibernate Envers makes it really easy to audit databases tables. It was quite a fight to configure and wire up everything correctly and 
understanding how the ``AuditReader`` works. But with this sample application it should be easier to add versioning and auditing 
to your application. 