title: Spring Boot Multi-Tenant Applications: Preserving Tenant information in Asynchronous Methods
date: 2020-04-29 18:05
tags: java, spring
category: java
slug: spring_boot_multitenancy_async
author: Philipp Wagner
summary: This article shows how to preserve tenant 

In the past days I have revisited an old Spring Boot example for implementing Multi-Tenant applications. It 
got updated to the latest Spring Boot release, all packages have been updated and I updated it to use the 
Spring Boot ``@RestController`` implementation:

* [https://github.com/bytefish/SpringBootMultiTenancy](https://github.com/bytefish/SpringBootMultiTenancy)

## What's the Problem? ##

Spring Boot has a very cool way for asynchronous processing, which is by simply using the ``@Async`` annotation 
and call it a day. Somewhere deep down in the Spring Boot implementation a new or existing thread is likely to be 
spun up from its ``ThreadPoolTaskExecutor``.

In the existing implementation the Tenant identifier was provided by using a ``ThreadLocal``. This is a problem when 
using asynchronous methods, because child threads won't have access to the Tenant name anymore... the ``ThreadLocal`` 
will be empty. 

Let's fix this!

## Making the ThreadPoolTaskExecutor Tenant-aware ##

What we could do is to add a ``TaskDecorator`` to Spring Boots ``ThreadPoolTaskExecutor``, and pass in the Tenant Name from 
the parent thread like this:

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

And in the ``AsyncConfigurerSupport`` we could add the ``TenantAwareTaskDecorator`` to the ``ThreadPoolTaskExecutor``. 

This configuration will be loaded by Spring in the Startup phase:

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
