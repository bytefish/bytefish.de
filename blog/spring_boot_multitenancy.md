title: Providing Multitenancy with Spring Boot
date: 2020-04-26 21:38
tags: java, spring
category: java
slug: spring_boot_multitenancy
author: Philipp Wagner
summary: This article shows how to provide Multitenancy with Spring Boot.

In this post I will show you how to provide multitenancy in a Spring Boot application.

A Spring Boot WebFlux implementation can be found at:

* [https://www.bytefish.de/blog/spring_boot_multitenancy_webflux.html](https://www.bytefish.de/blog/spring_boot_multitenancy_webflux.html)

## What Is Multitenancy ##

As soon as your application has multiple customers you will need to implement some kind of multitenancy for your application. 

Microsoft [writes on multitenant applications]():

> A multitenant application is a shared resource that allows separate users, or "tenants," to view the application as 
> though it was their own. A typical scenario that lends itself to a multitenant application is one in which all users 
> of the application may wish to customize the user experience but otherwise have the same basic business requirements. 

The best introduction to multitenant applications I have found is written by Microsoft at:

* [https://docs.microsoft.com/en-us/azure/sql-database/sql-database-design-patterns-multi-tenancy-saas-applications](https://docs.microsoft.com/en-us/azure/sql-database/sql-database-design-patterns-multi-tenancy-saas-applications)

## Multitenant Models ##

There are several models to achieve multitenancy in an application:

1. Database per Tenant 
    * Each Tenant has its own database and is isolated from other tenants. 
2. Shared database, Separate Schema
    * All Tenants share a database, but have their own database schemas and their own tables. 
3. Shared Database, Shared Schema
    * All Tenants share a database and tables. Every table has a Column with the Tenant Identifier, that shows the owner of the row.

Think about it like this (taken from [StackExchange Software Engineering](https://softwareengineering.stackexchange.com/a/340533)):

1. Database per Tenant: Every Tenant has its own house.
2. Shared Database, Separate Schema: Every Tenant in the same building, but has its own apartment.
3. Shared Database, Shared Schema: Everyone is living in the same apartment and all stuff is marked with sticky-notes to show who owns it.

Every model is a trade-off between isolation and resource sharing, which is explained in detail at:

* [Microsoft: Popular multi-tenant data models](https://docs.microsoft.com/en-us/azure/sql-database/sql-database-design-patterns-multi-tenancy-saas-applications#popular-multi-tenant-data-models)

I personally always opt for the Database-per-Tenant approach, because it provides the greatest data isolation between Tenants and 
is by far the simplest model to implement.

## Spring Boot Example ##

The GitHub repository for this post can be found at:

* [https://github.com/bytefish/SpringBootMultiTenancy](https://github.com/bytefish/SpringBootMultiTenancy)

In this example we are going to develop a multitenant application to manage customers.

### The Request Flow ###

It is probably best to summarize the request flow at the start of the post, so you have an idea how things work together:

1. A HTTP Request flows in with a Header ``X-TenantID``, that contains a Tenant identifier.
2. The ``X-TenantID`` header value is extracted and Tenant Name is written into a ``ThreadLocal``.
3. An implementation of an ``AbstractRoutingDataSource`` uses the ``ThreadLocal`` to resolve a ``DataSource`` (based on a Tenant identifier).
4. The JPA EntityManager in the Spring Boot application then uses this ``DataSource`` to make queries to the Tenant-specific Database.
5. A HTTP Response is sent.
6. The Tenant identifier in the ``ThreadLocal`` is reset to prevent leaking data.

### Creating the Databases ###

First of all we need to create a database user and the tenant databases for this tutorial. I am going to use PostgreSQL for this 
example. We are going to have two tenants ``TenantOne`` with the database ``sampledb`` and a tenant ``TenantTwo`` with the 
datbase ``sampledb2``.

First of all create the user ``philipp`` for connecting to the databases:

```
PS C:\Users\philipp> psql -U postgres
psql (9.4.1)
postgres=# CREATE USER philipp WITH PASSWORD 'test_pwd';
CREATE ROLE
```

Then we can create the two tenant databases and set the owner to ``philipp``:

```
postgres=# CREATE DATABASE sampledb
postgres-#   WITH OWNER philipp;
CREATE DATABASE
postgres=#
postgres=# CREATE DATABASE sampledb2
postgres-#   WITH OWNER philipp;
CREATE DATABASE
```

### Creating the Schema and Tables ###

The GitHub sample has a Batch Script (Windows users) and a Shell Script (Mac / Linux Users) to create the schemas and tables:

* [SpringBootMultiTenancy/sql](https://github.com/bytefish/SpringBootMultiTenancy/tree/master/SpringBootMultiTenancy/sql)

You simply need to exectute the script and enter the database name and credentials details.

Execute the script for both tenant databases ``sampledb`` and ``sampledb2`` to setup the databases.

If however you prefer to do this manually, the next sections will show the schema and table definitions.

#### SQL Schema ####

```sql
IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'sample') THEN

    CREATE SCHEMA sample;

END IF;
```

#### SQL Table ####

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
	last_name VARCHAR(255) NOT NULL
);

END IF;
```

### Project Structure ###

It's useful to take a look at the Project structure first:

<a href="/static/images/blog/spring_boot_multitenancy/project_structure_spring_mvc.jpg">
	<img class="mediacenter" src="/static/images/blog/spring_boot_multitenancy/project_structure_spring_mvc.jpg" alt="Project Overview" />
</a>

The purpose of the various classes: 

* ``async``
    * ``AsyncConfig``
        * Provides a TaskExecutor decorated for TenantAware Processing.
    * ``TenantAwareTaskDecorator``
        * Adds a Spring Boot ``TaskDecorator``, that passes the TenantName to a Child Thread.
* ``core``
    * ``ThreadLocalStorage``
        * Stores the Tenant Identifier in a ``ThreadLocal``.
* ``model``
    * ``Customer``
        * The ``Customer`` entity, which will be managed in each Tenant Database.
* ``repositories``
    * ``ICustomerRepository``
        * A CRUD Repository to persist customers.
* ``routing``
    * ``config``
        * ``DatabaseConfiguration``
            * For dynamic Tenant Configuration
    * ``DynamicTenantAwareRoutingSource``
        * Periodically refreshes the DataSources to identify new or stale datasources
    * ``TenantAwareRoutingSource``
        * Uses the Tenant Identifier to identify the database of this tenant.
* ``web``
    * ``configuration``
        * ``WebMvcConfig``
            * Configures the Spring MVC interceptors.
    * ``controllers``
        * ``CustomerController``
            * Implements a REST Webservice for persisting and deleting Customers.
    * ``converter``
        * ``Converters``
            * Converts between the Domain Model and the Data Transfer Object.
    * ``interceptor``
        * ``TenantNameInterceptor``
            * Extracts the Tenant Identifier from an incoming request.

### Infrastructure ###

#### Storing Tenant Identifier ####

The ``ThreadLocalStorage`` class wraps a ``ThreadLocal`` to store the Tenant data in the current thread context.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.core;

public class ThreadLocalStorage {

    private static ThreadLocal<String> tenant = new ThreadLocal<>();

    public static void setTenantName(String tenantName) {
        tenant.set(tenantName);
    }

    public static String getTenantName() {
        return tenant.get();
    }

}
```

#### Implement the Routing ####

Spring Boot provides the ``AbstractRoutingDataSource`` for determining a data source at runtime. In the example 
the tenant name from the ``ThreadLocalStorage`` is used as the lookup key for routing. We will later see how it 
is used in the Spring Boot application.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.routing;

import de.bytefish.multitenancy.core.ThreadLocalStorage;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;

public class TenantAwareRoutingSource extends AbstractRoutingDataSource {

    @Override
    protected Object determineCurrentLookupKey() {
        return ThreadLocalStorage.getTenantName();
    }

}
```

### Domain Layer ###

#### The Customer Entity ####

The Customer Entity models the Customer entity.  We are using the annotations from the ``javax.persistence`` namespace to 
annotate the domain model and set the database columns. Hibernate plays nicely with these annotations.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.model;

import javax.persistence.*;

@Entity
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

#### The Customer Repository ####

Adding CRUD functionality is simple with Spring Boot, which provides a so called ``CrudRepository``. You simply extend from the 
``CrudRepository`` interface and Spring automatically provides all CRUD functionality for your entity.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.repositories;

import de.bytefish.multitenancy.model.Customer;
import org.springframework.data.repository.CrudRepository;

public interface ICustomerRepository extends CrudRepository<Customer, Long> {
}
```

### The Web Layer ###

#### Extracting the Tenant Information ####

There are several ways to extract the tenant identifier from an incoming request. The Webservice client will send a HTTP Header 
with the name ``X-TenantID`` in the example. In Spring MVC you can implement a ``HandlerInterceptorAdapter`` to intercept an 
incoming request and extract data from it.

The ``TenantNameInterceptor`` reads the ``X-TenantID`` header and stores its value in the ``ThreadLocalStorage``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.interceptors;

import de.bytefish.multitenancy.core.ThreadLocalStorage;
import org.springframework.web.servlet.handler.HandlerInterceptorAdapter;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TenantNameInterceptor extends HandlerInterceptorAdapter {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {

        // Implement your logic to extract the Tenant Name here. Another way would be to
        // parse a JWT and extract the Tenant Name from the Claims in the Token. In the
        // example code we are just extracting a Header value:
        String tenantName = request.getHeader("X-TenantID");

        // Always set the Tenant Name, so we avoid leaking Tenants between Threads even in the scenario, when no
        // Tenant is given. I do this because if somehow the afterCompletion Handler isn't called the Tenant Name
        // could still be persisted within the ThreadLocal:
        ThreadLocalStorage.setTenantName(tenantName);

        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {

        // After completing the request, make sure to erase the Tenant from the current Thread. It's
        // because Spring may reuse the Thread in the Thread Pool and you don't want to leak this
        // information:
        ThreadLocalStorage.setTenantName(null);
    }
}
```

#### Data Transfer Object and Converter ####

You should always separate your Web Layer from the Domain Layer. In an ideal world Web Layer should only care about receiving and 
sending Data Transfer Objects to the consumer. It should know how to convert between the Data Transfer Object and the Domain model, 
so it can use the Domain repositories.

The ``CustomerDto`` Data Transfer Object uses Jackson annotations to provide the JSON mapping.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

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

And the ``Converters`` class provides two methods to convert between the ``CustomerDto`` and the ``Customer`` model.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.converter;

import de.bytefish.multitenancy.model.Customer;
import de.bytefish.multitenancy.web.model.CustomerDto;

import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

public class Converters {

    private Converters() {

    }

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

    public static List<CustomerDto> convert(Iterable<Customer> customers) {
        return StreamSupport.stream(customers.spliterator(), false)
                .map(Converters::convert)
                .collect(Collectors.toList());
    }
}
```

#### Controller ####

Implementing the RESTful Webservice with Spring MVC requires us to implement a ``RestController``. We are using 
the ``ICustomerRepository`` for querying the database and using the ``Converters`` to convert between both 
representations. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.controllers;

import de.bytefish.multitenancy.model.Customer;
import de.bytefish.multitenancy.repositories.ICustomerRepository;
import de.bytefish.multitenancy.web.converter.Converters;
import de.bytefish.multitenancy.web.model.CustomerDto;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@RestController
public class CustomerController {

    private final ICustomerRepository repository;

    @Autowired
    public CustomerController(ICustomerRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/customers")
    public List<CustomerDto> getAll() {
        Iterable<Customer> customers = repository.findAll();

        return Converters.convert(customers);
    }

    @GetMapping("/customers/{id}")
    public CustomerDto get(@PathVariable("id") long id) {
        Customer customer = repository
                .findById(id)
                .orElse(null);

        return Converters.convert(customer);
    }

    @PostMapping("/customers")
    public CustomerDto post(@RequestBody CustomerDto customer) {
        // Convert to the Domain Object:
        Customer source = Converters.convert(customer);

        // Store the Entity:
        Customer result = repository.save(source);

        // Return the DTO:
        return Converters.convert(result);
    }

    @DeleteMapping("/customers/{id}")
    public void delete(@PathVariable("id") long id) {
        repository.deleteById(id);
    }

}
```

#### Configuration ####

To configure Spring MVC, we need to extend the ``WebMvcConfigurer`` and add the ``TenantNameInterceptor`` to the list of interceptors.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.configuration;

import de.bytefish.multitenancy.web.interceptors.TenantNameInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new TenantNameInterceptor());
    }

}
```

### Plugging it together ###

Finally it is time to plug everything together using Spring Boot. All we have to do is to define a ``Bean`` for the ``DataSource``, 
and use the ``TenantAwareRoutingSource`` for routing. If you want a dynamic routing, that refreshes Data Sources at runtime, please 
use the ``DynamicTenantAwareRoutingSource``. 

I have also added some sane properties for Spring JPA, so Spring doesn't try to automatically detect the database.

All other dependencies are automatically resolved by Spring Boot. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy;

import com.zaxxer.hikari.HikariDataSource;
import de.bytefish.multitenancy.routing.TenantAwareRoutingSource;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.HashMap;
import java.util.Map;

@SpringBootApplication
@EnableAsync
@EnableScheduling
@EnableTransactionManagement
public class SampleSpringApplication {

	public static void main(String[] args) {
		SpringApplication.run(SampleSpringApplication.class, args);
	}

	@Bean
	public DataSource dataSource() {

		AbstractRoutingDataSource dataSource = new TenantAwareRoutingSource();

		Map<Object,Object> targetDataSources = new HashMap<>();

		targetDataSources.put("TenantOne", tenantOne());
		targetDataSources.put("TenantTwo", tenantTwo());

		dataSource.setTargetDataSources(targetDataSources);

		dataSource.afterPropertiesSet();

		return dataSource;
	}

	public DataSource tenantOne() {

		HikariDataSource dataSource = new HikariDataSource();

		dataSource.setInitializationFailTimeout(0);
		dataSource.setMaximumPoolSize(5);
		dataSource.setDataSourceClassName("org.postgresql.ds.PGSimpleDataSource");
		dataSource.addDataSourceProperty("url", "jdbc:postgresql://127.0.0.1:5432/sampledb");
		dataSource.addDataSourceProperty("user", "philipp");
		dataSource.addDataSourceProperty("password", "test_pwd");

		return dataSource;
	}

	public DataSource tenantTwo() {

		HikariDataSource dataSource = new HikariDataSource();

		dataSource.setInitializationFailTimeout(0);
		dataSource.setMaximumPoolSize(5);
		dataSource.setDataSourceClassName("org.postgresql.ds.PGSimpleDataSource");
		dataSource.addDataSourceProperty("url", "jdbc:postgresql://127.0.0.1:5432/sampledb2");
		dataSource.addDataSourceProperty("user", "philipp");
		dataSource.addDataSourceProperty("password", "test_pwd");

		return dataSource;
	}
}
```

#### Getting Rid if Warning ####

Spring Boot introduces a lot of magic to make things work with minimal coding... and sometimes convention 
over configuration introduces headaches. When Spring Boot starts there is no Tenant set in the Thread, so 
we cannot use things like automatic detection of the database.

So I have added a Properties file ``application.properties`` to configure Spring:

```properties
# Get Rid of the OIV Warning:
spring.jpa.open-in-view=false
# Show the SQL Statements fired by JPA:
spring.jpa.show-sql=true
# Set sane Spring Hibernate properties:
spring.jpa.hibernate.naming.physical-strategy=org.hibernate.boot.model.naming.PhysicalNamingStrategyStandardImpl
# Prevent JPA from trying to Initialize...:
spring.jpa.database=postgresql
# ... and do not Auto-Detect the Database:
spring.datasource.initialize=false
# Prevent Hibernate from Automatic Changes to the DDL Schema:
spring.jpa.hibernate.ddl-auto=none
```

The same thing happens down in Hibernate internals, where it attempts to read Metadata to initialize JDBC 
settings. To prevent those connections, which we don't want to be done I have added a properties file 
``hibernate.properties`` which is automagically read by Hibernate:

```properties
hibernate.temp.use_jdbc_metadata_defaults=false
```

## Testing the Application ##

We start with inserting customers to the database of Tenant ``TenantOne``:

```
> curl -H "X-TenantID: TenantOne" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Philipp\", \"lastName\" : \"Wagner\"}"  http://localhost:8080/customers

{"id":1,"firstName":"Philipp","lastName":"Wagner"}

> curl -H "X-TenantID: TenantOne" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Max\", \"lastName\" : \"Mustermann\"}"  http://localhost:8080/customers

{"id":2,"firstName":"Max","lastName":"Mustermann"}
```

Getting a list of all customers for ``TenantOne`` will now return two customers:

```
> curl -H "X-TenantID: TenantOne" -X GET http://localhost:8080/customers

[{"id":1,"firstName":"Philipp","lastName":"Wagner"},{"id":2,"firstName":"Max","lastName":"Mustermann"}]
```

While requesting a list of all customers for ``TenantTwo`` returns an empty list:

```
> curl -H "X-TenantID: TenantTwo" -X GET http://localhost:8080/customers

[]
```

We can now insert a customer into the ``TenantTwo`` database:

```
> curl -H "X-TenantID: TenantTwo" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Hans\", \"lastName\" : \"Wurst\"}"  http://localhost:8080/customers

{"id":1,"firstName":"Hans","lastName":"Wurst"}
```

Querying the ``TenantOne`` database still returns the two customers:

```
> curl -H "X-TenantID: TenantOne" -X GET http://localhost:8080/customers

[{"id":1,"firstName":"Philipp","lastName":"Wagner"},{"id":2,"firstName":"Max","lastName":"Mustermann"}]
```

Querying the ``TenantTwo`` database will now return the inserted customer:

```
> curl -H "X-TenantID: TenantTwo" -X GET http://localhost:8080/customers

[{"id":1,"firstName":"Hans","lastName":"Wurst"}]
```

## Resolving the Tenant in Asynchronous Methods ##

There is a problem though with the ``ThreadLocal`` in the ``ThreadLocalStorage``: Asynchronous methods. 

Spring Boot has a very cool way for asynchronous processing, which is by simply using the ``@Async`` annotation. In the Spring Boot 
implementation a new or existing thread is likely to be spun up from the ``ThreadPoolTaskExecutor``, thus the Tenant Name in the 
``ThreadLocal`` will be empty. 

Let's fix this!

What we could do is to add a ``TaskDecorator`` to Spring Boots ``ThreadPoolTaskExecutor``, and pass in the Tenant Name from the Parent Thread:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.async;

import de.bytefish.multitenancy.core.ThreadLocalStorage;
import org.springframework.core.task.TaskDecorator;

public class TenantAwareTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        String tenantName = ThreadLocalStorage.getTenantName();
        return () -> {
            try {
                ThreadLocalStorage.setTenantName(tenantName);
                runnable.run();
            } finally {
                ThreadLocalStorage.setTenantName(null);
            }
        };
    }
}
```

And in the ``AsyncConfigurerSupport`` we could add the ``TenantAwareTaskDecorator`` to the ``ThreadPoolTaskExecutor``. This 
configuration will be loaded by Spring in the Startup phase:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.async;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.AsyncConfigurerSupport;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

@Configuration
public class AsyncConfig extends AsyncConfigurerSupport {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();

        executor.setCorePoolSize(7);
        executor.setMaxPoolSize(42);
        executor.setQueueCapacity(11);
        executor.setThreadNamePrefix("TenantAwareTaskExecutor-");
        executor.setTaskDecorator(new TenantAwareTaskDecorator());
        executor.initialize();

        return executor;
    }

}
```

To test it, let's add an asynchronous method ``findAllAsync`` to the ``ICustomerRepository``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.repositories;

import de.bytefish.multitenancy.model.Customer;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.CrudRepository;
import org.springframework.scheduling.annotation.Async;

import java.util.List;
import java.util.concurrent.CompletableFuture;

public interface ICustomerRepository extends CrudRepository<Customer, Long> {

    @Async
    @Query("select c from Customer c")
    CompletableFuture<List<Customer>> findAllAsync();

}
```

And add a new endpoint to the ``CustomerController``:

```java
// ...

@RestController
public class CustomerController {

    private final ICustomerRepository repository;

    @Autowired
    public CustomerController(ICustomerRepository repository) {
        this.repository = repository;
    }

    // ...
    
    @GetMapping("/async/customers")
    public List<CustomerDto> getAllAsync() throws ExecutionException, InterruptedException {
        CompletableFuture<List<Customer>> customers = repository.findAllAsync();

        // Return the DTO List:
        return StreamSupport.stream(customers.get().spliterator(), false)
                .map(Converters::convert)
                .collect(Collectors.toList());
    }
    
}
```

And let's use curl to test it. Does it work?

```
curl -H "X-TenantID: TenantOne" -X GET http://localhost:8080/async/customers
```

And surprise... it does work as intended:

```
[{"id":1,"firstName":"Philipp","lastName":"Wagner"},{"id":2,"firstName":"Max","lastName":"Mustermann"}]
```

## Conclusion ##

It's really easy to provide multitenancy with Spring Boot. Using the ``AbstractRoutingDataSource`` makes it possible to easily implement a Database-Per-Tenant approach for multitenancy. 