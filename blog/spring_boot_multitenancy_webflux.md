title: Providing Multitenancy with Spring Boot WebFlux
date: 2021-11-20 14:48
tags: java, spring, webflux, reactive
category: java
slug: spring_boot_multitenancy_webflux
author: Philipp Wagner
summary: This article shows how to provide Multitenancy with Spring Boot WebFlux.

The article on Multitenancy with Spring Boot is rather outdated. These days high performance Java services are written with 
Spring Boot WebFlux, which is Spring Boot's reactive and non-blocking web application framework.

So I updated the code and also provide a Spring Boot WebFlux implementation at:

* [https://github.com/bytefish/SpringBootMultiTenancy_WebFlux](https://github.com/bytefish/SpringBootMultiTenancy_WebFlux)

The GitHub repository contains all SQL scripts necessary to create the database used in this article.

## Adding the Maven Dependencies ##

Let's start by adding the required dependencies for the project!

We'll need ``spring-boot-starter-webflux`` to provide the WebFlux framework. Providing non-blocking services requires us to 
go all-in on reactive and try not to block in the application. That's why we need to add ``r2dbc-postgresql`` as the Postgres 
R2DBC implementation to provide reactive programming with PostgreSQL. I am lazy and want to have Spring Boot implementing the 
CRUD repositories and everything for me, so we also take a dependency on ``spring-boot-starter-data-r2dbc``.

```java
<dependencies>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-webflux</artifactId>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-r2dbc</artifactId>
    </dependency>

    <dependency>
        <groupId>io.r2dbc</groupId>
        <artifactId>r2dbc-postgresql</artifactId>
    </dependency>

</dependencies>
```

That's it.

## Implementation ##

The application is used to create, read and update customers. So we start by defining the ``Customer`` domain model:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.model;


import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

@Table("sample.customer")
public class Customer {

    @Id
    @Column("customer_id")
    private Long id;

    @Column("first_name")
    private String firstName;

    @Column("last_name")
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

It's probably good to have some kind of separation of concerns, so we also define the ``CustomerDto`` counterpart:

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

Now we start the service implementation by enabling WebFlux using the ``@EnableWebFlux`` annotation and configure the framework:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.configuration;

import org.springframework.context.annotation.Configuration;
import org.springframework.http.codec.ServerCodecConfigurer;
import org.springframework.web.reactive.config.EnableWebFlux;
import org.springframework.web.reactive.config.WebFluxConfigurer;

@Configuration
@EnableWebFlux
class WebFluxConfiguration implements WebFluxConfigurer {

    @Override
    public void configureHttpMessageCodecs(ServerCodecConfigurer configurer) {
        configurer.defaultCodecs().enableLoggingRequestDetails(true);
    }
}

```

The idea is to pass the Tenant identifier to the Web service by using a HTTP header named ``X-TenantID``: 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.constants;

public class HeaderNames {

    public static final String TenantId = "X-TenantID";

}
```

A ``WebFilter`` will intercept the HTTP request to WebFlux, read the ``X-TenantID`` and put it in the ``ContextView`` so 
anyone participating in the request has access to the Tenant identifier:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.filters;

import de.bytefish.multitenancy.constants.ApplicationConstants;
import de.bytefish.multitenancy.web.constants.HeaderNames;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

@Component
public class TenantIdWebFilter implements WebFilter {

    @Override
    public Mono<Void> filter(ServerWebExchange serverWebExchange, WebFilterChain webFilterChain) {

        var headerValues = serverWebExchange.getRequest().getHeaders().get(HeaderNames.TenantId);

        if(headerValues == null || headerValues.size() == 0) {
            return webFilterChain.filter(serverWebExchange);
        }

        // Make a guess. Just get the first Key, if we have multiple Tenant Headers:
        String tenantKey = headerValues.get(0);

        return webFilterChain
                .filter(serverWebExchange)
                .contextWrite(ctx -> ctx.put(ApplicationConstants.TenantKey, tenantKey));
    }
}
```

The R2DBC API defines an ``AbstractRoutingConnectionFactory`` to resolve a ``ConnectionFactory`` based on a routing key determined by a call to the abstract method 
``AbstractRoutingConnectionFactory#determineCurrentLookupKey``. We also need to override ``AbstractRoutingConnectionFactory#getMetadata``, so no default data source 
needs to be specified: 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.routing;

import de.bytefish.multitenancy.constants.ApplicationConstants;
import io.r2dbc.spi.ConnectionFactoryMetadata;
import org.springframework.r2dbc.connection.lookup.AbstractRoutingConnectionFactory;
import reactor.core.publisher.Mono;

import static de.bytefish.multitenancy.utils.ReactorUtils.errorIfEmpty;

public class PostgresTenantConnectionFactory extends AbstractRoutingConnectionFactory {

    static final class PostgresqlConnectionFactoryMetadata implements ConnectionFactoryMetadata {

        static final PostgresqlConnectionFactoryMetadata INSTANCE = new PostgresqlConnectionFactoryMetadata();

        public static final String NAME = "PostgreSQL";

        private PostgresqlConnectionFactoryMetadata() {
        }

        @Override
        public String getName() {
            return NAME;
        }
    }

    @Override
    protected Mono<Object> determineCurrentLookupKey() {
        return Mono
                .deferContextual(Mono::just)
                .filter(it -> it.hasKey(ApplicationConstants.TenantKey))
                .map(it -> it.get(ApplicationConstants.TenantKey))
                .transform(m -> errorIfEmpty(m, () -> new RuntimeException(String.format("ContextView does not contain the Lookup Key '%s'", ApplicationConstants.TenantKey))));
    }

    @Override
    public ConnectionFactoryMetadata getMetadata() {
        // If we don't override this method, it will try to determine the Dialect from the default
        // ConnectionFactory. This is a problem, because you don't want a "Default ConnectionFactory"
        // when you cannot resolve the Tenant.
        //
        // That's why we explicitly return a fixed PostgresqlConnectionFactoryMetadata. This class
        // is also defined within the r2dbc library, but it isn't exposed to public.
        return PostgresqlConnectionFactoryMetadata.INSTANCE;
    }
}
```

Where does ``errorIfEmpty`` come from? We need to throw a useful exception, when no lookup key was found in context. I have found the following 
the ``errorIfEmpty`` method in the Spring Boot Reactor issue tracker:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.utils;

import reactor.core.publisher.Mono;
import java.util.function.Supplier;

public class ReactorUtils {

    // https://github.com/reactor/reactor-core/issues/917
    public static <R> Mono<R> errorIfEmpty(Mono<R> mono, Supplier<Throwable> throwableSupplier) {
        return mono.switchIfEmpty(Mono.defer(() -> Mono.error(throwableSupplier.get())));
    }
}
```

This ``PostgresTenantConnectionFactory`` is now configured in by extending the ``AbstractR2dbcConfiguration``. This is 
where we are adding the connections for each tenant. All this can also be externalized to a configuration of course, but 
for sake of simplicity we are doing it in code:

```
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.web.configuration;

import de.bytefish.multitenancy.routing.PostgresTenantConnectionFactory;
import io.r2dbc.postgresql.PostgresqlConnectionConfiguration;
import io.r2dbc.postgresql.PostgresqlConnectionFactory;
import io.r2dbc.spi.ConnectionFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.r2dbc.config.AbstractR2dbcConfiguration;
import org.springframework.data.r2dbc.repository.config.EnableR2dbcRepositories;
import org.springframework.r2dbc.connection.lookup.AbstractRoutingConnectionFactory;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import java.util.Map;

import static java.util.Map.entry;

@Configuration
@EnableTransactionManagement
@EnableR2dbcRepositories
public class MultitenantPostgresConfiguration extends AbstractR2dbcConfiguration {

    @Override
    @Bean
    public ConnectionFactory connectionFactory() {
        var connectionFactory = postgresConnectionFactory();

        connectionFactory.afterPropertiesSet();

        return connectionFactory;
    }

    private AbstractRoutingConnectionFactory postgresConnectionFactory() {
        var routingConnectionFactory = new PostgresTenantConnectionFactory();

        routingConnectionFactory.setLenientFallback(false);
        routingConnectionFactory.setTargetConnectionFactories(tenants());

        return routingConnectionFactory;
    }

    private Map<String, ConnectionFactory> tenants() {
        return Map.ofEntries(
                entry("TenantOne", tenantOne()),
                entry("TenantTwo", tenantTwo())
        );
    }

    private ConnectionFactory tenantOne() {
        return new PostgresqlConnectionFactory(PostgresqlConnectionConfiguration.builder()
                .host("localhost")
                .port(5432)
                .database("sampledb")
                .username("philipp")
                .password("test_pwd").build());
    }

    private ConnectionFactory tenantTwo() {
        return new PostgresqlConnectionFactory(PostgresqlConnectionConfiguration.builder()
                .host("localhost")
                .port(5432)
                .database("sampledb2")
                .username("philipp")
                .password("test_pwd").build());
    }
}
```

Using Spring Boot Data magic we can simply use a ``ReactiveCrudRepository`` to connect to the database and perform 
CRUD operations on it. We only need to define the ``ICustomerRepository`` interface for the entity:

```
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.repositories;

import de.bytefish.multitenancy.model.Customer;
import org.springframework.data.repository.reactive.ReactiveCrudRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ICustomerRepository extends ReactiveCrudRepository<Customer, Long> {
}
```

The ``ICustomerRepository`` in turn is injected into the ``CustomerController``, that implements the REST API endpoints:

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
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
public class CustomerController {

    private final ICustomerRepository customerRepository;

    @Autowired
    public CustomerController(ICustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    @GetMapping("/customers")
    public Flux<CustomerDto> getAll() {
        return customerRepository.findAll().map(Converters::convert);
    }

    @GetMapping("/customers/{id}")
    public Mono<CustomerDto> get(@PathVariable("id") long id) {
        return customerRepository.findById(id).map(Converters::convert);
    }

    @PostMapping("/customers")
    public Mono<CustomerDto> post(@RequestBody CustomerDto customer) {
        Customer source = Converters.convert(customer);

        return customerRepository
                .save(source)
                .map(Converters::convert);
    }

    @DeleteMapping("/customers/{id}")
    public Mono<Void> delete(@PathVariable("id") long id) {
        return customerRepository.deleteById(id);
    }
}
```

And finally the ``SpringBootApplication`` starter class responsible for booting the whole thing:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class SampleSpringApplication {

	public static void main(String[] args) {
		SpringApplication.run(SampleSpringApplication.class, args);
	}

}
```

## Does it work? ##

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
