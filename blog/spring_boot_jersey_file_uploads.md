title: Providing a File Upload API with Jersey
date: 2017-10-21 07:38
tags: java, jersey spring
category: java
slug: file_upload_api_jersey
author: Philipp Wagner
summary: This article shows how to provide File Uploads with Jersey.

Every RESTful API grows to the point it needs to support file uploads. Supporting file uploads with 
Jersey is rather simple and in this post I will show you how to do it. All my posts come with a GitHub 
project, and this post is no exception.

The GitHub repository for this post can be found at:

* [https://github.com/bytefish/JerseyFileUploadExample](https://github.com/bytefish/JerseyFileUploadExample)

## Dependencies ##

You need the ``jersey-media-multipart`` package to support HTTP multipart requests with Jersey. I am using 
Spring Boot for the example, so you will also need the ``spring-boot-starter-jersey`` depdendency. 

In the ``dependencies`` element of the POM file we add both dependencies:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-jersey</artifactId>
</dependency>

<dependency>
    <groupId>org.glassfish.jersey.media</groupId>
    <artifactId>jersey-media-multipart</artifactId>
    <version>2.25</version>
</dependency>
```

## Project Structure ##

It's useful to take a look at the project structure first:

<a href="/static/images/blog/spring_boot_jersey_file_uploads/project_structure.jpg">
	<img class="mediacenter" src="/static/images/blog/spring_boot_jersey_file_uploads/project_structure.jpg" alt="Project Overview" />
</a>

The purpose of the various classes:

* ``exceptions``
    * ``FileUploadException``
        * An exception, that will be thrown if a File Upload fails due to an error.
* ``handler``
    * ``IFileUploadHandler``
        * This interface needs to be implemented to handle incoming file upload requests.
    * ``LocalStorageHandler``
        * A default implementation of the ``IFileUploadHandler``, which writes a file to the local filesystem.
* ``model``
    * ``errors``
        * ``ServiceError``
            * An error containing an error code and error reason for failed uploads.
        * ``HttpServiceError``
            * Wraps a ``ServiceError`` and adds a HTTP Status Code, which will be sent back to the client.
    * ``files``
        * ``HttpFile``
            * Abstracts the incoming HTTP multipart file data into something more usable for business logic.
    * ``request``
        * ``FileUploadRequest``
            * Abstracts the incoming HTTP multipart *form* data and builds a Request with Metadata and a ``HttpFile``.
    * ``response``
        * ``FileUploadResponse``
            * The response data, that will be sent to the client.
* ``provider``
    * ``IRootPathProvider``
        * This interface needs to be implemented for defining the Servers root path.
    * ``RootPathProvider``
        * The default implementation of the ``IRootPathProvider``.
* ``web``
    * ``configuration``
        * ``JerseyConfiguration``
            * The Jersey configuration setting up the Jersey server.
    * ``exceptions``
        * ``FileUploadExceptionMapper``
            * Handles Exceptions on the highest level and turns them into a useful representation.
    * ``resource``
        * ``FileUploadResource``
            * Finally the resource implementing the File Upload API.
* ``SampleJerseyApplication``
    * Configures and starts the Server.

## Domain Model ##

### Errors ###

In most of my posts I stress how important errors are. It's because you need to provide a proper approach to errors as early 
as possible in your projects. It should be possible for a client to make sense of errors, so you don't have to investigate log 
files for every problem.

And more importantly, you don't want to leak Exception details to the client. Your Stacktrace may contain sensitive information 
and may reveal details about your architecture, that should be hidden. And I guess you don't want your exception messages to be 
sent into the wild.

#### ServiceError ####

An error sent to the client should contain a ``code`` and an error ``message``. Providing a specific error code makes it possible 
for a client to automatically evaluate the error response and take the right actions, such as notifying users to provide required 
data.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.model.errors;

import com.fasterxml.jackson.annotation.JsonProperty;

public class ServiceError {

    private final String code;
    private final String message;

    public ServiceError(String code, String message) {
        this.code = code;
        this.message = message;
    }

    @JsonProperty("code")
    public String getCode() {
        return code;
    }

    @JsonProperty("message")
    public String getMessage() {
        return message;
    }
}
```

#### HttpServiceError ####

The API will be a RESTful API, which defined HTTP Status Codes to indicate failure and success. There may be different types of 
errors, like a bad request (HTTP Status 400), invalid authentication credentials (HTTP Status 401). It should also be possible to 
send an Internal Server Error (HTTP Status 500) to the client, which says the error is on the Server side and cannot be fixed by 
the client.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.model.errors;

public class HttpServiceError {

    private final int httpStatusCode;

    private final ServiceError serviceError;

    public HttpServiceError(int httpStatusCode, ServiceError serviceError) {
        this.httpStatusCode = httpStatusCode;
        this.serviceError = serviceError;
    }

    public int getHttpStatusCode() {
        return httpStatusCode;
    }

    public ServiceError getServiceError() {
        return serviceError;
    }
}
```

#### FileUploadException ####

If a file can't be uploaded due to missing or invalid data, then the control flow will be exited by throwing an application. The 
``FileUploadException`` gets a ``ServiceError`` passed into and wraps it in a ``HttpServiceError``. If someone in the application 
thinks it's appropriate to handle the exception, then the method ``getHttpServiceError()`` returns the error reason.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.exceptions;

import de.bytefish.fileuploads.model.errors.HttpServiceError;
import de.bytefish.fileuploads.model.errors.ServiceError;

public class FileUploadException extends RuntimeException {

    private final HttpServiceError httpServiceError;

    public FileUploadException(ServiceError serviceError) {
        this.httpServiceError = createServiceError(serviceError);
    }

    public FileUploadException(ServiceError serviceError, String message) {
        super(message);

        this.httpServiceError = createServiceError(serviceError);
    }

    public FileUploadException(ServiceError serviceError, String message, Throwable cause) {
        super(message, cause);

        this.httpServiceError = createServiceError(serviceError);
    }

    public HttpServiceError getHttpServiceError() {
        return httpServiceError;
    }

    private static HttpServiceError createServiceError(ServiceError serviceError) {
        return new HttpServiceError(400, serviceError);
    }
}
```

#### FileUploadExceptionMapper ####

The best place to handle such an exception is in the web layer. Jersey provides a so called ``ExceptionMapper``, which 
makes it possible to handle specific exceptions. In the example the ``FileUploadException`` is handled and a response 
is generated, with the HTTP Status code and ``ServiceError`` extracted from the exception.

```java
package de.bytefish.fileuploads.web.exceptions;

import de.bytefish.fileuploads.exceptions.FileUploadException;
import de.bytefish.fileuploads.model.errors.HttpServiceError;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.ws.rs.core.Response;

public class FileUploadExceptionMapper implements javax.ws.rs.ext.ExceptionMapper<FileUploadException> {

    private static final Logger logger = LoggerFactory.getLogger(FileUploadExceptionMapper.class);

    @Override
    public Response toResponse(FileUploadException fileUploadException) {

        if(logger.isErrorEnabled()) {
            logger.error("An error occured", fileUploadException);
        }

        HttpServiceError httpServiceError = fileUploadException.getHttpServiceError();

        return Response
                .status(httpServiceError.getHttpStatusCode())
                .entity(httpServiceError.getServiceError())
                .build();
    }
}
```

### Abstracting the Multipart File Data ###

#### HttpFile ####

Even small applications can grow into larger systems. So you want to decouple your system as early as possible in a 
project. One of these abstractions should be turning the incoming HTTP multipart request into something more useful. 
Because you really don't want to fiddle around with a ``HttpServletRequest`` deep down in your business logic; nor 
should any other developer in your team do so.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.model.files;

import java.io.InputStream;
import java.util.Map;

public class HttpFile {

    private final String name;
    private final String submittedFileName;
    private final long size;
    private final Map<String, String> parameters;
    private final InputStream stream;

    public HttpFile(String name, String submittedFileName, long size, Map<String, String> parameters, InputStream stream) {
        this.name = name;
        this.submittedFileName = submittedFileName;
        this.size = size;
        this.parameters = parameters;
        this.stream = stream;
    }

    public String getName() {
        return name;
    }

    public String getSubmittedFileName() {
        return submittedFileName;
    }

    public long getSize() {
        return size;
    }

    public Map<String, String> getParameters() {
        return parameters;
    }

    public InputStream getStream() {
        return stream;
    }
}
```

#### FileUploadRequest ####

Every file upload may contain some metadata like a title or the description. This metadata shouldn't pollute the ``HttpFile``, so 
we wrap the ``HttpFile`` and add the Metadata in a ``FileUploadRequest``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.model.request;

import de.bytefish.fileuploads.model.files.HttpFile;

public class FileUploadRequest {

    private final String title;
    private final String description;
    private final HttpFile httpFile;

    public FileUploadRequest(String title, String description, HttpFile httpFile) {
        this.title = title;
        this.description = description;
        this.httpFile = httpFile;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public HttpFile getHttpFile() {
        return httpFile;
    }
}
```

#### FileUploadResponse ####

If you are storing a file on the server, then chances are good there are duplicate file names when using the original file name. 
These files shouldn't be overriden, so one way is to assign a unique identifier to the file, and pass it to the client. The client 
itself then knows, which file he has to request.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.model.response;

import com.fasterxml.jackson.annotation.JsonProperty;

public class FileUploadResponse {

    private final String identifier;

    public FileUploadResponse(String identifier) {
        this.identifier = identifier;
    }

    @JsonProperty("identifier")
    public String getIdentifier() {
        return identifier;
    }
}
```

### Handling the incoming data ###

#### Determining the Root Path of the Server ####

The user should be able to decide, where to write files and this is where the ``IRootPathProvider`` is necessary. An 
``IRootPathProvider`` is a simple interface, that just returns the root path to write the files to, if the implementation 
is using a local filesystem.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.provider;

public interface IRootPathProvider {

    String getRootPath();

}
```

The default implementation ``RootPathProvider`` requires the root path to be configured explicitly, when bootstrapping the server.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.provider;

public class RootPathProvider implements IRootPathProvider {

    private final String path;

    public RootPathProvider(String path) {
        this.path = path;
    }

    @Override
    public String getRootPath() {
        return path;
    }
}
```

#### FileUploadHandler ####

With a proper model in place, the abstraction for handling a ``FileUploadRequest`` becomes simple:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.handler;


import de.bytefish.fileuploads.model.request.FileUploadRequest;
import de.bytefish.fileuploads.model.response.FileUploadResponse;

public interface IFileUploadHandler {

    FileUploadResponse handle(FileUploadRequest request);

}
```

The default implementation writes to the local filesystem, that's why I called it a ``LocalStorageFileUploadHandler``. You 
can see, that the handler gets an ``IRootPathProvider`` injected, so you can easily configure the root path from the outside. 

The ``LocalStorageFileUploadHandler`` first evaluates, if a file is available in the request. If some assertions don't hold, 
the control flow will be stopped and a ``FileUploadException`` is thrown, with a ``ServiceError`` included.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.handler;

import de.bytefish.fileuploads.exceptions.FileUploadException;
import de.bytefish.fileuploads.model.files.HttpFile;
import de.bytefish.fileuploads.model.errors.ServiceError;
import de.bytefish.fileuploads.model.request.FileUploadRequest;
import de.bytefish.fileuploads.model.response.FileUploadResponse;
import de.bytefish.fileuploads.provider.IRootPathProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.UUID;

@Component
public class LocalStorageFileUploadHandler implements IFileUploadHandler {

    private final IRootPathProvider rootPathProvider;

    @Autowired
    public LocalStorageFileUploadHandler(IRootPathProvider rootPathProvider) {
        this.rootPathProvider = rootPathProvider;
    }

    @Override
    public FileUploadResponse handle(FileUploadRequest request) {

        // Early exit, if there is no Request:
        if(request == null) {
            throw new FileUploadException(new ServiceError("missingFile", "Missing File data"), String.format("Missing Parameter: request"));
        }

        // Get the HttpFile:
        HttpFile httpFile = request.getHttpFile();

        // Early exit, if the Request has no data assigned:
        if(httpFile == null) {
            throw new FileUploadException(new ServiceError("missingFile", "Missing File data"), String.format("Missing Parameter: request.httpFile"));
        }

        // We don't override existing files, create a new UUID File name:
        String targetFileName = UUID.randomUUID().toString();

        // Write it to Disk:
        internalWriteFile(httpFile.getStream(), targetFileName);

        return new FileUploadResponse(targetFileName);
    }

    private void internalWriteFile(InputStream stream, String fileName) {
        try {
            Files.copy(stream, Paths.get(rootPathProvider.getRootPath(), fileName));
        } catch(Exception e) {
            throw new FileUploadException(new ServiceError("storingFileError", "Error writing file"), String.format("Writing File '%s' failed", fileName), e);
        }
    }
}
```

### The Web Layer ###

#### Resource ####

The ``FileUploadResource`` now connects all the parts. It defines an endpoint, that consumes multipart form data and 
produces a JSON Response. The ``fileUpload(...)`` method uses the ``@FormDataParam`` annotation from the 
``jersey-media-multipart`` package to evaluate the incoming HTTP multipart form data request.

From the incoming request we first build the ``HttpFile``, the ``FileUploadRequest`` and then pass it into the 
configured ``IFileUploadHandler``. If the file was written successfully, then the ``FileUploadResponse`` with a 
unique file identifier is returned to the client.
 
```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads.web.resource;

import de.bytefish.fileuploads.handler.IFileUploadHandler;
import de.bytefish.fileuploads.model.files.HttpFile;
import de.bytefish.fileuploads.model.request.FileUploadRequest;
import de.bytefish.fileuploads.model.response.FileUploadResponse;
import org.glassfish.jersey.media.multipart.FormDataContentDisposition;
import org.glassfish.jersey.media.multipart.FormDataParam;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.ws.rs.Consumes;
import javax.ws.rs.POST;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import java.io.InputStream;


@Component
@Path("/files")
public class FileUploadResource  {

    private final IFileUploadHandler fileUploadHandler;

    @Autowired
    public FileUploadResource(IFileUploadHandler fileUploadHandler) {
        this.fileUploadHandler = fileUploadHandler;
    }

    @POST
    @Path("/upload")
    @Consumes(MediaType.MULTIPART_FORM_DATA)
    @Produces(MediaType.APPLICATION_JSON)
    public Response fileUpload(@FormDataParam("title") String title,
                               @FormDataParam("description") String description,
                               @FormDataParam("file") InputStream stream,
                               @FormDataParam("file") FormDataContentDisposition fileDetail) {

        // Create the HttpFile:
        HttpFile httpFile = new HttpFile(fileDetail.getName(), fileDetail.getFileName(), fileDetail.getSize(), fileDetail.getParameters(), stream);

        // Create the FileUploadRequest:
        FileUploadRequest fileUploadRequest = new FileUploadRequest(title, description, httpFile);

        // Handle the File Upload:
        FileUploadResponse result = fileUploadHandler.handle(fileUploadRequest);

        return Response
                .status(200)
                .entity(result)
                .build();
    }
}
```

#### Configuration ####

Almost done! In the ``JerseyConfig`` we need to enable the ``MultiPartFeature``, register the ``FileUploadResource`` and register 
the ``FileUploadExceptionMapper``.

```java
package de.bytefish.fileuploads.web.configuration;

import de.bytefish.fileuploads.web.exceptions.FileUploadExceptionMapper;
import de.bytefish.fileuploads.web.resource.FileUploadResource;
import org.glassfish.jersey.media.multipart.MultiPartFeature;
import org.glassfish.jersey.server.ResourceConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class JerseyConfig extends ResourceConfig {

    public JerseyConfig() {

        // Register the Resource:
        register(FileUploadResource.class);

        // Register the Feature for Multipart Uploads (File Upload):
        register(MultiPartFeature.class);

        // Register Exception Mappers for returning API Errors:
        register(FileUploadExceptionMapper.class);

        // Uncomment to disable WADL Generation:
        //property("jersey.config.server.wadl.disableWadl", true);

        // Uncomment to add Request Tracing:
        //property("jersey.config.server.tracing.type", "ALL");
        //property("jersey.config.server.tracing.threshold", "TRACE");
    }
}
```


### Spring Boot Application ###

Finally the ``SpringBootApplication`` can be defined, so the Spring container is configured and the Webserver is booted. So much 
dependencies, but this looks simple right? It's because the example only has one implementation for most of the dependencies, so 
Spring automatically resolves them.

The only dependency, that needs to be declared explicitly is the ``IRootPathProvider``. I have decided to write to a folder named ``out`` 
in the Webserver directory. You can adjust the path to your needs.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fileuploads;

import de.bytefish.fileuploads.provider.IRootPathProvider;
import de.bytefish.fileuploads.provider.RootPathProvider;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.support.SpringBootServletInitializer;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class SampleJerseyApplication extends SpringBootServletInitializer {

    public static void main(String[] args) {
        new SampleJerseyApplication()
                .configure(new SpringApplicationBuilder(SampleJerseyApplication.class))
                .run(args);
    }

    @Bean
    IRootPathProvider rootPathProvider() {
        return new RootPathProvider("./out");
    }
}
```

## Example ##

To upload a file you can use ``curl``. In the example I am uploading a file ``myfile.txt`` to the Webserver:

```
curl --verbose --form title="File Title" --form description="File Description" --form file=@"myfile.txt" http://localhost:8080/files/upload
```