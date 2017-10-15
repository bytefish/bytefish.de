title: Cross Origin Resource Sharing (CORS) with Jersey
date: 2017-09-17 09:00
tags: java, jersey
category: java
slug: cors_with_jersey
author: Philipp Wagner
summary: This article shows how to implement Cross Origin Resource Sharing (CORS) with Jersey.

[Jersey]: https://jersey.github.io/
[Spring Boot]: https://projects.spring.io/spring-boot/

[TOC]

## Introduction ##

I was recently writing a small Single Page Application (SPA) with JavaScript and used [Spring Boot] and [Jersey] for the Backend. 
It's really easy to get started with [Spring Boot], and with the [Jersey] starter package your RESTful Webservice is up and 
running within minutes. 

While [Jersey] provides a huge set of built-in features and a set of additional modules, it was lacking a module for CORS negotiation.

This post will show you an approach for implementing Cross Origin Resource Sharing (CORS) with [Jersey].

## What we are going to build ##

In the end you can attribute your endpoints with ``@CrossOrigin`` attribute to support CORS headers for the given endpoint.

A sample resource with a CORS-enabled endpoint could look like this:

```java
@Component
@Path("/sample")
public class SampleResource extends JerseyBaseResource {

    @GET
    @CrossOrigin
    @Path("{id}")
    @Produces(MediaType.APPLICATION_JSON)
    public SampleEntity get(@PathParam("id") long id) {
        return repository.findOne(id);
    }
}
```
## Implementation ##

### Headers ###

Cross Origin Resource Sharing (CORS) defines a set of HTTP headers used for negotiating shared resources. The first step in 
our implementation is to define the headers as constants. The headers can be looked up in the current specification for CORS:

* [https://fetch.spec.whatwg.org/#http-cors-protocol](https://fetch.spec.whatwg.org/#http-cors-protocol)

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jerseyexample.core.cors;

public class CrossOriginHeaders {

    public static final String ACCESS_CONTROL_REQUEST_METHOD_HEADER = "Access-Control-Request-Method";
    public static final String ACCESS_CONTROL_REQUEST_HEADERS_HEADER = "Access-Control-Request-Headers";

    public static final String ACCESS_CONTROL_ALLOW_ORIGIN = "Access-Control-Allow-Origin";

    public static final String ACCESS_CONTROL_ALLOW_CREDENTIALS = "Access-Control-Allow-Credentials";
    public static final String ACCESS_CONTROL_ALLOW_HEADERS = "Access-Control-Allow-Headers";
    public static final String ACCESS_CONTROL_ALLOW_METHODS = "Access-Control-Allow-Methods";
    public static final String ACCESS_CONTROL_EXPOSE_HEADERS = "Access-Control-Expose-Headers";

}
```

### CORS Configuration ###

We need to configure our application to tell the client, which origins are allowed, which headers are going to be served and 
which methods are allowed to query. The CORS specification defines a set of default headers, which should also be predefined 
in the application.

The ``Configuration`` class has a lot of parameters, so it will probably be complicated for a consumer to instantiate it with 
the correct set of headers defined in the CORS standard. That's why the ``Configuration`` also defines a builder pattern, 
that provides a Fluent API to configure the CORS Configuration.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jerseyexample.core.cors;

import de.bytefish.jerseyexample.core.utils.StringUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class CrossOriginConfiguration {

    private final String allowedOrigins;

    private final String allowedMethods;

    private final String allowedHeaders;

    private final String exposedHeaders;

    private final String allowCredentials;

    public CrossOriginConfiguration(String allowedOrigins, String allowedMethods, String allowedHeaders, String exposedHeaders, String allowCredentials) {
        this.allowedOrigins = allowedOrigins;
        this.allowedMethods = allowedMethods;
        this.allowedHeaders = allowedHeaders;
        this.exposedHeaders = exposedHeaders;
        this.allowCredentials = allowCredentials;
    }

    public String getAllowedOrigins() {
        return allowedOrigins;
    }

    public String getAllowedMethods() {
        return allowedMethods;
    }

    public String getAllowedHeaders() {
        return allowedHeaders;
    }

    public String getExposedHeaders() {
        return exposedHeaders;
    }

    public String getAllowCredentials() {
        return allowCredentials;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {

        private List<String> allowedOrigins = new ArrayList<>();
        private List<String> allowedMethods = new ArrayList<>();
        private List<String> allowedHeaders = new ArrayList<>();
        private List<String> exposedHeaders = new ArrayList<>();
        private String allowCredentials;

        public Builder() {
            // Set Default Values:
            allowedOrigins.addAll(Arrays.asList("*"));
            allowedMethods.addAll(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"));
            exposedHeaders.addAll(Arrays.asList("Cache-Control", "Content-Language", "Content-Type", "Expires", "Last-Modified", "Pragma"));
            allowCredentials = "true";
        }

        public Builder allowedOrigins(List<String> origins) {
            this.allowedOrigins = origins;

            return this;
        }

        public Builder allowedOrigin(String origin) {
            allowedOrigins.add(origin);

            return this;
        }

        public Builder allowedMethods(List<String> methods) {
            this.allowedMethods = methods;

            return this;
        }

        public Builder allowedMethod(String method) {
            this.allowedMethods.add(method);

            return this;
        }

        public Builder allowedHeaders(List<String> headers) {
            this.allowedHeaders = headers;

            return this;
        }

        public Builder allowedHeader(String header) {
            this.allowedHeaders.add(header);

            return this;
        }

        public Builder allowCredentials(boolean allowCredentials) {
            this.allowCredentials = allowCredentials ? "true" : "false";

            return this;
        }


        public Builder exposedHeaders(List<String> headers) {
            this.exposedHeaders = headers;

            return this;
        }

        public Builder exposedHeader(String header) {
            this.exposedHeaders.add(header);

            return this;
        }

        public CrossOriginConfiguration build() {
            return new CrossOriginConfiguration(
                    getCommaSeparatedString(allowedOrigins),
                    getCommaSeparatedString(allowedMethods),
                    getCommaSeparatedString(allowedHeaders),
                    getCommaSeparatedString(exposedHeaders),
                    allowCredentials
            );
        }

        private static String getCommaSeparatedString(List<String> source) {
            return StringUtils.getDelimitedString(source, ", ");
        }
    }

}
```

The ``StringUtils`` class contains a Helper method for splitting a String:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jerseyexample.core.utils;

import java.util.List;
import java.util.stream.Collectors;

public class StringUtils {

    private StringUtils() {

    }

    public static String getDelimitedString(List<String> source, String delimiter) {
        if(source == null) {
            return null;
        }

        return source.stream().collect(Collectors.joining(delimiter));
    }
}
```

### Handling Preflight Requests with a Base Resource ###

The CORS Standard defines something called "Preflight Requests": 

> This is effectively the user agent implementation of the check to see if the CORS protocol is understood. The so-called 
> CORS-preflight request. If successful it populates the CORS-preflight cache to minimize the number of these fetches.

So a Preflight Request asks for permissions to a resource before using it. It uses the ``OPTIONS`` HTTP method and contains 
the ``Access-Control-Request-Method`` and the ``Access-Control-Request-Headers``. 

I expected the ``Chrome`` browser to do a preflight request for every resource it wants to consume. So I wrote a base class all 
resources will derive from. It declares an catch-all endpoint on the option method and returns the global configuration. If you 
need a finer control over the resource permissions, you will need to do some additional work here.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jerseyexample.core.resources;

import de.bytefish.jerseyexample.core.cors.CrossOriginHeaders;
import de.bytefish.jerseyexample.core.cors.CrossOriginConfiguration;
import org.springframework.beans.factory.annotation.Autowired;

import javax.ws.rs.OPTIONS;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;

public abstract class JerseyBaseResource {

    @OPTIONS
    @Produces(MediaType.APPLICATION_JSON)
    public Response options() {
        return Response.ok()
                .header(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, crossOriginConfiguration.getAllowedOrigins())
                .header(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_HEADERS, crossOriginConfiguration.getAllowedHeaders())
                .header(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, crossOriginConfiguration.getAllowCredentials())
                .header(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_METHODS, crossOriginConfiguration.getAllowedMethods())
                .header(CrossOriginHeaders.ACCESS_CONTROL_EXPOSE_HEADERS, crossOriginConfiguration.getExposedHeaders())
                .build();
    }
}
```


### Annotations for supplying the CORS headers ###

#### Annotation ####

[Jersey] has a cool feature, which allows to annotate methods and bind the annotations to Plugins. In this case the plugin is going 
to be a ``ContainerResponseFilter``, which allows us to intercept the incoming requests and add additional headers to outgoing 
responses.

We call the Annotation ``CrossOrigin``, so the methods can be annotated with ``@CrossOrigin`` as seen above.

```java
package de.bytefish.jerseyexample.core.cors.annotations;

import javax.ws.rs.NameBinding;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@NameBinding
@Target({ ElementType.TYPE, ElementType.METHOD })
@Retention(RetentionPolicy.RUNTIME)
public @interface CrossOrigin {

}
```

#### Intercepting the Incoming Requests ####

We only want to add the CORS Headers to the requests, if it is not a Preflight Request. That's why we early exit, if it is an 
``OPTIONS`` request. Again: Some work will be neccessary for providing a fine-grained access to resources. This example provides 
a global configuration.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jerseyexample.core.filters.cors;

import de.bytefish.jerseyexample.core.cors.CrossOriginConfiguration;
import de.bytefish.jerseyexample.core.cors.CrossOriginHeaders;
import de.bytefish.jerseyexample.core.cors.annotations.CrossOrigin;
import de.bytefish.jerseyexample.core.filters.priorities.Priorities;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.annotation.Priority;
import javax.ws.rs.container.ContainerRequestContext;
import javax.ws.rs.container.ContainerResponseContext;
import javax.ws.rs.container.ContainerResponseFilter;
import javax.ws.rs.ext.Provider;
import java.io.IOException;

@Provider
@Priority(Priorities.CORS_RESPONSE)
@CrossOrigin
public class CrossOriginResponseFilter implements ContainerResponseFilter {

    private static final Logger log = LoggerFactory.getLogger(CrossOriginResponseFilter.class);

    private final CrossOriginConfiguration configuration;

    public CrossOriginResponseFilter(CrossOriginConfiguration configuration) {
        this.configuration = configuration;
    }

    @Override
    public void filter(ContainerRequestContext requestContext, ContainerResponseContext responseContext) throws IOException {
        if(!isPreflightRequest(requestContext)) {
            handleSimpleRequest(requestContext, responseContext);
        }
    }

    private boolean isPreflightRequest(ContainerRequestContext requestContext)
    {
        String method = requestContext.getMethod();

        // A Preflight Request uses the OPTIONS Method to Query Resources:
        if (!"OPTIONS".equalsIgnoreCase(method)) {
            return false;
        }

        // If no Access Control Request Header is given, we should not interpret this as a Preflight Request:
        if (!requestContext.getHeaders().containsKey(CrossOriginHeaders.ACCESS_CONTROL_REQUEST_METHOD_HEADER)) {
            return false;
        }

        // This is a Preflight Request:
        return true;
    }

     private void handleSimpleRequest(ContainerRequestContext requestContext, ContainerResponseContext responseContext) {
        responseContext.getHeaders().add(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, configuration.getAllowedOrigins());
        responseContext.getHeaders().add(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_HEADERS, configuration.getAllowedHeaders());
        responseContext.getHeaders().add(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_METHODS, configuration.getAllowedMethods());
        responseContext.getHeaders().add(CrossOriginHeaders.ACCESS_CONTROL_EXPOSE_HEADERS, configuration.getExposedHeaders());
        responseContext.getHeaders().add(CrossOriginHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, configuration.getAllowCredentials());
    }

}
```

#### Plugging it together in the Jersey Configuration ####

Finally we need to register the ``CrossOriginResponseFilter`` in the Jersey Configuration. At the Webserver startup Jersey evaluates 
the registrations and builds the Pipelines accordingly. The CORS Filter should always be the first Filter in the Pipeline.

```java
/**
 * Jersey Configuration (Resources, Modules, Filters, ...)
 */
@Component
public class JerseyConfig extends ResourceConfig {

    @Autowired
    public JerseyConfig(CrossOriginConfiguration crossOriginConfiguration) {

        // Register the CORS Filter as a Singleton first:
        register(new CrossOriginResponseFilter(crossOriginConfiguration), 1);
        
        // ...
    }       
}
```

## Spring Boot Configuration ##

You have seen, that I used the [Spring Boot] Annotation ``@Autowired`` to inject the Dependency into the Jersey Config. The 
``SpringBootServletInitializer`` is where the registrations are done and it is where we define the ``CrossOriginConfiguration`` 
to be used in the application.

As an example I have added a custom allowed and exposed header called ``X-MyCustomHeader``, which is easy to do with the 
Fluent API provided by the ``CrossOriginConfiguration`` class.

```java
package de.bytefish.jerseyexample;

import de.bytefish.jerseyexample.core.cors.CrossOriginConfiguration;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.support.SpringBootServletInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.web.cors.CorsConfiguration;

@SpringBootApplication
@ComponentScan({"de.bytefish.jerseyexample"})
public class SampleJerseyApplication extends SpringBootServletInitializer {

	public static void main(String[] args) {
		new SampleJerseyApplication()
				.configure(new SpringApplicationBuilder(SampleJerseyApplication.class))
				.run(args);
	}

	@Bean
	public CrossOriginConfiguration corsConfiguration() {
		return CrossOriginConfiguration.builder()
				.allowedHeader("X-MyCustomHeader")
				.exposedHeader("X-MyCustomHeader")
				.build();
	}
}
```

## Conclusion ##

[Nancy]: http://nancyfx.org/

It is really easy to extend the [Jersey] framework. Providing some kind of Aspect Oriented Programming by using Annotations 
is a great idea to provide Cross Cutting Concerns, such as Logging or as seen above Cross Origin Resource Sharing. 