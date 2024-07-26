title: Providing Multitenancy with Spring Boot and PostgreSQL Row Level Security (Revisited)
date: 2024-07-26 12:15
tags: java, spring
category: java
slug: spring_boot_multitenancy
author: Philipp Wagner
summary: This article shows a revisited implementation of Multitenancy with Spring Boot and PostgreSQL RLS.

A few years ago I have written on implementing Multitenancy using PostgreSQL Row Level Security features:

* [https://www.bytefish.de/blog/spring_boot_multitenancy_using_rls.html](https://www.bytefish.de/blog/spring_boot_multitenancy_using_rls.html)

The article was and still is well received, so it's a good idea to revisit it.

All code can be found in a Git repository at:

* [https://github.com/bytefish/SpringBootMultitenancyUsingRowLevelSecurity](https://github.com/bytefish/SpringBootMultitenancyUsingRowLevelSecurity)

## Table of contents ##

[TOC]

## What's the Problem ##

In the previous implementation, the tenant identifier was passed to the PostgreSQL database using 
a session variable. It was then used in the Row Level Security Policies like this:

```sql
CREATE POLICY tenant_isolation_policy ON sample.customer
    USING (tenant_name = current_setting('app.current_tenant')::VARCHAR);
```

But what happens, if we are using pooled connections? There's a real chance, that we are accidentally 
leaking the `app.current_user` setting across calls. We should find a more foolproof way for this!

## What we are going to build ##

Instead of using the `current_setting`, why not simply create a user for each tenant and 
use the built-in `current_user`? For the connections we are simply creating two separate 
connection pools in the Spring Boot application, so there's no chance of getting it 
wrong.

We start by creating our modified Row Level Security Policies, which are now based on the `current_user`:

```sql
CREATE POLICY tenant_customer_isolation_policy ON multitenant.customer
    USING (tenant_name = current_user);

CREATE POLICY tenant_address_isolation_policy ON multitenant.address
    USING (tenant_name = current_user);

CREATE POLICY tenant_customer_address_isolation_policy ON multitenant.customer_address
    USING (tenant_name = current_user);
```

We are then creating a new role for both tenants:

```sql
---------------------------
-- Create the tenants   --
---------------------------
IF NOT EXISTS (
  SELECT FROM pg_catalog.pg_roles
  WHERE  rolname = 'tenant_a') THEN

    CREATE ROLE tenant_a LOGIN PASSWORD 'tenant_a';

END IF;

IF NOT EXISTS (
  SELECT FROM pg_catalog.pg_roles
  WHERE  rolname = 'tenant_b') THEN

    CREATE ROLE tenant_b LOGIN PASSWORD 'tenant_b';

END IF;
```

The `AbstractRoutingDataSource` to determine the DataSource Tenant Key is now simply returning the current tenant name:

```java
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.datasource;

import de.bytefish.multitenancy.core.ThreadLocalStorage;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;

public class TenantAwareRoutingSource extends AbstractRoutingDataSource {

    @Override
    protected Object determineCurrentLookupKey() {
        return ThreadLocalStorage.getTenantName();
    }
}
```

And what's left is creating a `DataSource` for `tenant_a` and `tenant_b` in the `SpringApplication` entry point.

```java
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy;

// ...

@SpringBootApplication
@EnableAsync
@EnableTransactionManagement
public class SampleSpringApplication {

	public static void main(String[] args) {
		SpringApplication.run(SampleSpringApplication.class, args);
	}


	@Bean
	public DataSource dataSource() {

		AbstractRoutingDataSource dataSource = new TenantAwareRoutingSource();

		Map<Object,Object> targetDataSources = new HashMap<>();

		targetDataSources.put("tenant_a", tenantA());
		targetDataSources.put("tenant_b", tenantB());

		dataSource.setTargetDataSources(targetDataSources);

		dataSource.afterPropertiesSet();

		return dataSource;
	}

	public DataSource tenantA() {

		HikariDataSource dataSource = new HikariDataSource();

		dataSource.setInitializationFailTimeout(0);
		dataSource.setMaximumPoolSize(5);
		dataSource.setDataSourceClassName("org.postgresql.ds.PGSimpleDataSource");
		dataSource.addDataSourceProperty("url", "jdbc:postgresql://127.0.0.1:5432/sampledb");
		dataSource.addDataSourceProperty("user", "tenant_a");
		dataSource.addDataSourceProperty("password", "tenant_a");

		return dataSource;
	}

	public DataSource tenantB() {

		HikariDataSource dataSource = new HikariDataSource();

		dataSource.setInitializationFailTimeout(0);
		dataSource.setMaximumPoolSize(5);
		dataSource.setDataSourceClassName("org.postgresql.ds.PGSimpleDataSource");
		dataSource.addDataSourceProperty("url", "jdbc:postgresql://127.0.0.1:5432/sampledb");
		dataSource.addDataSourceProperty("user", "tenant_b");
		dataSource.addDataSourceProperty("password", "tenant_b");

		return dataSource;
	}
}
```

## Does it work? ##

Of course it does!

We start by inserting sample data for both tenants:

```sql
----------------------------------------------
-- Create the Sample Data for Tenant A      --
----------------------------------------------
INSERT INTO multitenant.customer(customer_id, first_name, last_name, tenant_name) 
    VALUES 
        (1, 'Philipp', 'Wagner', 'tenant_a')        
    ON CONFLICT DO NOTHING;

INSERT INTO multitenant.address(address_id, name, street, postalcode, city, country, tenant_name) 
    VALUES 
        (1, 'Philipp Wagner', 'Fakestreet 1', '12345', 'Faketown', 'Germany', 'tenant_a')        
    ON CONFLICT DO NOTHING;

INSERT INTO multitenant.customer_address(customer_id, address_id, tenant_name) 
    VALUES 
        (1, 1, 'tenant_a')        
    ON CONFLICT DO NOTHING;

----------------------------------------------
-- Create the Sample Data for Tenant B      --
----------------------------------------------
INSERT INTO multitenant.customer(customer_id, first_name, last_name, tenant_name) 
    VALUES 
        (2, 'John', 'Wick', 'tenant_b')        
    ON CONFLICT DO NOTHING;

INSERT INTO multitenant.address(address_id, name, street, postalcode, city, country, tenant_name) 
    VALUES 
        (2, 'John Wick', 'Fakestreet 55', '00000', 'Fakecity', 'USA', 'tenant_b')        
    ON CONFLICT DO NOTHING;

INSERT INTO multitenant.customer_address(customer_id, address_id, tenant_name) 
    VALUES 
        (2, 2, 'tenant_b')        
    ON CONFLICT DO NOTHING;
```

And we can see, that `tenant_a` only has access to `Philipp Wagner`:

```
curl -H "X-TenantID: tenant_a" -X GET http://localhost:8080/customers
[{"id":1,"firstName":"Philipp","lastName":"Wagner","addresses":[{"id":1,"name":"Philipp Wagner","street":"Fakestreet 1","postalcode":"12345","city":"Faketown","country":"Germany"}]}]
```

And `tenant_b` only has access to `John Wick`:

```
curl -H "X-TenantID: tenant_b" -X GET http://localhost:8080/customers
[{"id":2,"firstName":"John","lastName":"Wick","addresses":[{"id":2,"name":"John Wick","street":"Fakestreet 55","postalcode":"00000","city":"Fakecity","country":"USA"}]}]
```

## Conclusion ##

And that's it! We have successfully removed all traces of a session variable and prevent leaking 
the tenant identifier accross connections. I cannot see any obvious downsides using this approach
and I think it's a very lean implementation.