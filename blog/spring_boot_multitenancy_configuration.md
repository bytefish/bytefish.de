title: Loading Tenants dynamically in a Multi-Tenant Spring Boot application
date: 2020-04-19 15:24
tags: java, spring, multitenant
category: java
slug: spring_boot_multitenancy_configuration
author: Philipp Wagner
summary: Loading Tenants dynamically in a Multi-Tenant Spring Boot Application.

When I am running out of ideas for projects I am taking a look at old projects and see what 
most people asked for. Some years ago I wrote an article on Multi-Tenant applications with 
Spring Boot, which was well received:

* [https://github.com/bytefish/SpringBootMultiTenancy/](https://github.com/bytefish/SpringBootMultiTenancy/)

I tried to keep the code as simple as possible back then, but there is something a lot of readers 
are asking for: "How on earth could I add tenants dynamically? I don't want to hardcode all this 
stuff!".

## What's the problem? ##

If we look at the entry point for the Spring Boot application, we can see how the Tenants are 
registered. The ``AbstractRoutingDataSource`` is created in code and the ``DataSource`` for the 
tenants are passed into it:

```java
package de.bytefish.multitenancy;

import com.zaxxer.hikari.HikariDataSource;
import de.bytefish.multitenancy.routing.TenantAwareRoutingSource;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.support.SpringBootServletInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

@SpringBootApplication
@EnableTransactionManagement
public class SampleJerseyApplication extends SpringBootServletInitializer {

	public static void main(String[] args) {
		new SampleJerseyApplication()
				.configure(new SpringApplicationBuilder(SampleJerseyApplication.class))
				.run(args);
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

## Adding Tenants Dynamically ##

To load tenants or change connection details, we should start with the loading the data we need 
at runtime. To keep things simple, I decided to store all Tenants and their Connection details 
in a JSON file.

The class is called ``DatabaseConfiguration`` and is going to hold the same connection details as 
the hardcoded solution:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.routing.config;


import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Objects;

public class DatabaseConfiguration {

    private final String tenant;
    private final String url;
    private final String user;
    private final String dataSourceClassName;
    private final String password;

    @JsonCreator(mode = JsonCreator.Mode.PROPERTIES)
    public DatabaseConfiguration(@JsonProperty("tenant") String tenant,
            @JsonProperty("url") String url,
            @JsonProperty("user") String user,
            @JsonProperty("dataSourceClassName") String dataSourceClassName,
            @JsonProperty("password") String password) {
        this.tenant = tenant;
        this.url = url;
        this.user = user;
        this.dataSourceClassName = dataSourceClassName;
        this.password = password;
    }

    @JsonProperty("tenant")
    public String getTenant() {
        return tenant;
    }

    @JsonProperty("url")
    public String getUrl() {
        return url;
    }

    @JsonProperty("user")
    public String getUser() {
        return user;
    }

    @JsonProperty("dataSourceClassName")
    public String getDataSourceClassName() {
        return dataSourceClassName;
    }

    @JsonProperty("password")
    public String getPassword() {
        return password;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        DatabaseConfiguration that = (DatabaseConfiguration) o;
        return Objects.equals(tenant, that.tenant) &&
                Objects.equals(url, that.url) &&
                Objects.equals(user, that.user) &&
                Objects.equals(dataSourceClassName, that.dataSourceClassName) &&
                Objects.equals(password, that.password);
    }

    @Override
    public int hashCode() {
        return Objects.hash(tenant, url, user, dataSourceClassName, password);
    }
}
```

The JSON now looks like this:

```json
[
  {
    "tenant" : "TenantOne",
    "dataSourceClassName": "org.postgresql.ds.PGSimpleDataSource",
    "url": "jdbc:postgresql://127.0.0.1:5432/sampledb",
    "user": "philipp",
    "password": "test_pwd"
  },
  {
    "tenant": "TenantTwo",
    "dataSourceClassName": "org.postgresql.ds.PGSimpleDataSource",
    "url": "jdbc:postgresql://127.0.0.1:5432/sampledb2",
    "user": "philipp",
    "password": "test_pwd"
  }
]
```

And believe it or not, we are almost done. 

## The DynamicTenantAwareRoutingSource ##

In the original article [Providing Multitenancy with Spring Boot] we extended for the ``AbstractRoutingDataSource`` 
and resolved the current Tenant by overriding the ``determineCurrentLookupKey()`` method. We are not going to 
change this.

To provide dynamic loading of tenants I am again extending the ``DynamicTenantAwareRoutingSource`` and use the 
``ThreadLocalStorage`` to resolve the current tenant. It's also neccessary to override the methods 
``determineTargetDataSource()`` and ``afterPropertiesSet()``.

The class basically:

1. Loads the ``DatabaseConfiguration`` from the JSON File.
2. Builds the ``HikariDataSource`` from the ``DatabaseConfiguration``.
3. Uses the Data Sources in the ``determineTargetDataSource()`` to determine the tenant database.

Now where does the dynamic stuff come in? I have added a method ``insertOrUpdateDataSources()``, which 
uses the Spring Boot ``@Scheduled`` annotation to be executed every 5 seconds. This method loads the 
``DatabaseConfiguration`` from JSON and compares it to the current Data Sources. 

If a Tenant is missing, it is added to the internal map, and if the configuration has changed for a Tenant 
the Connection Pool is shutdown and a new Connection Pool is added:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.routing;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zaxxer.hikari.HikariDataSource;
import de.bytefish.multitenancy.core.ThreadLocalStorage;
import de.bytefish.multitenancy.routing.config.DatabaseConfiguration;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.scheduling.annotation.Scheduled;

import javax.sql.DataSource;

import java.io.File;
import java.util.Arrays;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

public class DynamicTenantAwareRoutingSource extends AbstractRoutingDataSource {

    private final String filename;
    private final ObjectMapper objectMapper;
    private final Map<String, HikariDataSource> tenants;

    public DynamicTenantAwareRoutingSource(String filename) {
        this(filename, new ObjectMapper());
    }

    public DynamicTenantAwareRoutingSource(String filename, ObjectMapper objectMapper) {
        this.filename = filename;
        this.objectMapper = objectMapper;
        this.tenants = getDataSources();
    }

    @Override
    public void afterPropertiesSet() {
        // Nothing to do ..
    }

    @Override
    protected DataSource determineTargetDataSource() {
        String lookupKey = (String) determineCurrentLookupKey();

        // And finally return it:
        return tenants.get(lookupKey);
    }

    @Override
    protected Object determineCurrentLookupKey() {
        return ThreadLocalStorage.getTenantName();
    }

    private Map<String, HikariDataSource> getDataSources() {

        // Deserialize the JSON:
        DatabaseConfiguration[] configurations = getDatabaseConfigurations();

        // Now create a Lookup Table:
        return Arrays
                .stream(configurations)
                .collect(Collectors.toMap(x -> x.getTenant(), x -> buildDataSource(x)));
    }

    private DatabaseConfiguration[] getDatabaseConfigurations() {
        try {
            return objectMapper.readValue(new File(filename), DatabaseConfiguration[].class);
        } catch(Exception e) {
            throw new RuntimeException(e);
        }
    }

    private HikariDataSource buildDataSource(DatabaseConfiguration configuration) {
        HikariDataSource dataSource = new HikariDataSource();

        dataSource.setInitializationFailTimeout(0);
        dataSource.setMaximumPoolSize(5);
        dataSource.setDataSourceClassName(configuration.getDataSourceClassName());
        dataSource.addDataSourceProperty("url", configuration.getUrl());
        dataSource.addDataSourceProperty("user", configuration.getUser());
        dataSource.addDataSourceProperty("password", configuration.getPassword());

        return dataSource;
    }

    @Scheduled(fixedDelay = 5000L)
    public void insertOrUpdateDataSources() {

        DatabaseConfiguration[] configurations = getDatabaseConfigurations();

        for (DatabaseConfiguration configuration : configurations) {
            if (tenants.containsKey(configuration.getTenant())) {
                HikariDataSource dataSource = tenants.get(configuration.getTenant());
                // We only shutdown and reload, if the configuration has actually changed...
                if (!isCurrentConfiguration(dataSource, configuration)) {
                    // Make sure we close this DataSource first...
                    dataSource.close();
                    // ... and then insert a new DataSource:
                    tenants.put(configuration.getTenant(), buildDataSource(configuration));
                }
            } else {
                tenants.put(configuration.getTenant(), buildDataSource(configuration));
            }
        }
    }

    private boolean isCurrentConfiguration(HikariDataSource dataSource, DatabaseConfiguration configuration) {
        return Objects.equals(dataSource.getDataSourceProperties().getProperty("user"), configuration.getUser())
                && Objects.equals(dataSource.getDataSourceProperties().getProperty("url"), configuration.getUrl())
                && Objects.equals(dataSource.getDataSourceProperties().getProperty("password"), configuration.getPassword())
                && Objects.equals(dataSource.getDataSourceClassName(), configuration.getDataSourceClassName());
    }
}
```

What's left is to rewrite the ``SpringBootApplication`` to use the ``DynamicTenantAwareRoutingSource``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy;

import de.bytefish.multitenancy.routing.DynamicTenantAwareRoutingSource;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.support.SpringBootServletInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.Properties;

@SpringBootApplication
@EnableScheduling
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
		return new DynamicTenantAwareRoutingSource("D:\\tenants.json");
	}

	private static Properties getDefaultProperties() {

		Properties defaultProperties = new Properties();

		// Set sane Spring Hibernate properties:
		defaultProperties.put("spring.jpa.show-sql", "true");
		defaultProperties.put("spring.jpa.hibernate.naming.physical-strategy", "org.hibernate.boot.model.naming.PhysicalNamingStrategyStandardImpl");
		defaultProperties.put("spring.datasource.initialize", "false");

		// Prevent JPA from trying to Auto Detect the Database:
		defaultProperties.put("spring.jpa.database", "postgresql");

		// Prevent Hibernate from Automatic Changes to the DDL Schema:
		defaultProperties.put("spring.jpa.hibernate.ddl-auto", "none");

		return defaultProperties;
	}
}
```

And that's it!



[Providing Multitenancy with Spring Boot]: https://bytefish.de/blog/spring_boot_multitenancy/