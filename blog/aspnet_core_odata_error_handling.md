title: Consistent Error Hanling in an ASP.NET Core OData and Blazor Application
date: 2024-01-16 10:04
tags: odata, blazor, dotnet
category: dotnet
slug: aspnet_core_odata_error_handling
author: Philipp Wagner
summary: This article shows how to add Consistent Error Handling to an ASP.NET Core OData Service and use it in a Blazor Application.

In this article we are going to look at one of the most important, yet underrated, aspects of any application: Error 
Handling and Error Messages. I am working on an ASP.NET Core OData application and want something similar to the 
Microsoft Graph API Error Handling.

Let's see how to do it!

At the end of the article we will have a flexible approach to Error Handling in our ASP.NET Core OData application 
and will be able to localize the results in the Blazor Frontend, so they show up like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_error_handling/localized_error_message.jpg">
        <img src="/static/images/blog/aspnet_core_odata_error_handling/localized_error_message.jpg" alt="Final Swagger Endpoints">
    </a>
</div>

The code has been taken from the Git Repository at:

* [https://github.com/bytefish/OpenFgaExperiments](https://github.com/bytefish/OpenFgaExperiments)

## OData Error Model ##

[Microsoft Graph REST API Guidelines]: https://github.com/microsoft/api-guidelines/blob/vNext/graph/GuidelinesGraph.md
[OData JSON Format]: https://docs.oasis-open.org/odata/odata-json-format/v4.01/odata-json-format-v4.01.html

Our errors should be modeled after the Microsoft Graph API. The Microsoft Graph API follows the [Microsoft Graph REST API Guidelines], which defines the Error handling here:

* [https://github.com/microsoft/api-guidelines/blob/vNext/graph/GuidelinesGraph.md#error-handling](https://github.com/microsoft/api-guidelines/blob/vNext/graph/GuidelinesGraph.md#error-handling)

This, as far as I can see, is the OData Error response model as defined in the [OData JSON Format] specification:

* [https://docs.oasis-open.org/odata/odata-json-format/v4.01/odata-json-format-v4.01.html#_Toc38457792](https://docs.oasis-open.org/odata/odata-json-format/v4.01/odata-json-format-v4.01.html#_Toc38457792)

So the ASP.NET Core OData implementation already includes a similar `ODataError` model, and all of the Microsoft Graph API documentation 
on Error handling somewhat applies to our OData applications as well. Great!

### HTTP status codes ###

The following table lists and describes the HTTP status codes that can be returned by the API.

<table>
    <thead>
        <th>Status code</th><th>Status message</th><th>Description</th></thead>
    <tbody>
        <tr><td>400</td><td>Bad Request</td><td>Can't process the request because it's malformed or incorrect.</td></tr>
        <tr><td>401</td><td>Unauthorized</td><td>Required authentication information is either missing or not valid for the resource.</td></tr>
        <tr><td>402</td><td>Payment Required</td><td>The payment requirements for the API haven't been met.</td></tr>
        <tr><td>403</td><td>Forbidden</td><td>Access is denied to the requested resource. The user might not have enough permission or might not have a required license.</td></tr>
        <tr><td>404</td><td>Not Found</td><td>The requested resource doesn’t exist.</td></tr>
        <tr><td>405</td><td>Method Not Allowed</td><td>	The HTTP method in the request isn't allowed on the resource.</td></tr>
        <tr><td>406</td><td>Not Acceptable</td><td>This service doesn’t support the format requested in the Accept header.</td></tr>
        <tr><td>409</td><td>Conflict</td><td>The current state conflicts with what the request expects. For example, the specified parent folder might not exist.</td></tr>
        <tr><td>410</td><td>Gone</td><td>The requested resource is no longer available at the server.</td></tr>
        <tr><td>411</td><td>Length Required</td><td>A Content-Length header is required on the request.</td></tr>
        <tr><td>412</td><td>Precondition Failed</td><td>A precondition provided in the request (such as an if-match header) doesn't match the resource's current state.</td></tr>
        <tr><td>413</td><td>Request Entity Too Large</td><td>The request size exceeds the maximum limit.</td></tr>
        <tr><td>415</td><td>Unsupported Media Type</td><td>	The content type of the request is a format that isn't supported by the service.</td></tr>
        <tr><td>416</td><td>Requested Range Not Satisfiable</td><td>The specified byte range is invalid or unavailable.</td></tr>
        <tr><td>422</td><td>Unprocessable Entity</td><td>Can't process the request because it is semantically incorrect.</td></tr>
        <tr><td>423</td><td>Locked</td><td>The resource that is being accessed is locked.</td></tr>
        <tr><td>429</td><td>Too Many Requests</td><td>Client application has been throttled and shouldn't attempt to repeat the request until an amount of time has elapsed.</td></tr>
        <tr><td>500</td><td>Internal Server Error</td><td>There was an internal server error while processing the request.</td></tr>
        <tr><td>501</td><td>Not Implemented</td><td>The requested feature isn’t implemented.</td></tr>
        <tr><td>503</td><td>Service Unavailable</td><td>The service is temporarily unavailable for maintenance or is overloaded. You may repeat the request after a delay, the length of which may be specified in a Retry-After header.</td></tr>
        <tr><td>504</td><td>Gateway Timeout</td><td>The server, while acting as a proxy, didn't receive a timely response from the upstream server it needed to access in attempting to complete the request.</td></tr>
        <tr><td>507</td><td>Insufficient Storage</td><td>The maximum storage quota has been reached.</td></tr>
        <tr><td>509</td><td>Bandwidth Limit Exceeded</td><td>Your app has been throttled for exceeding the maximum bandwidth cap. Your app can retry the request again after more time has elapsed.</td></tr>
    </tbody>
</table>

The error response is a single JSON object that contains a single property named `error`. This object includes all the details of 
the error. You can use the information returned here instead of or in addition to the HTTP status code. The following is an 
example of a full JSON error body.

```json
{
  "error": {
    "code": "ApiError_Auth_000001",
    "message": "Authentication failed.",
    "innerError": {
      "trace-id": "a-trace-id-guid",
    }
  }
}
```

### Error resource type ###

The error resource is returned whenever an error occurs in the processing of a request.

The error resource is composed of a single resource with the following format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "innererror": { 
      "code": "string"
    },
    "details": []
  }
}
```

The following table describe the semantics of the error resource type.

<table>
    <thead>
        <th>Property name</th><th>Value</th><th>Description</th></thead>
    <tbody>		
        <tr>
            <td>code</td>
            <td>string</td>
            <td>
                <div style="max-width: 300px">
                    <p>An error code string for the error that occurred.</p>
                    <p>A machine-readable value that you can take a dependency on in your code.</p>
                </div>
            </td>
        </tr>
        <tr>
            <td>message</td>
            <td>string</td>
            <td>
                <div style="max-width: 300px">
                    <p>A developer ready message about the error that occurred. This shouldn't be displayed to the user directly.</p>
                    <p>A human-readable value that describes the error condition. Don't take any dependency on the content of this value in your code.</p>
                    <p>At the root, it contains an error message intended for the developer to read. Error messages aren't localized and shouldn't be displayed directly to the user. When handling errors, your code shouldn't take any dependency on the message property values because they can change at any time, and they often contain dynamic information specific to the failed request. You should only code against error codes returned in code properties.</p>
                </div>
            </td>
        </tr>
        <tr>
            <td>innererror</td>
            <td>error object</td>
            <td>
                <div style="max-width: 300px">
                    <p>Optional. An additional error object that might be more specific than the top-level error.</p>
                    <p>Might recursively contain more innererror objects with additional, more specific error codes properties. When handling an error, apps should loop through all the nested error codes that are available and use the most detailed one that they understand.</p>
               </div>
           </td>
        </tr>
        <tr>
            <td>details</td>
            <td>error object</td>
            <td>
                <div style="max-width: 300px">
                    <p>Optional. A list of additional error objects that might provide a breakdown of multiple errors encountered while processing the request.</p>
                    <p>An array of error objects that have the same JSON format as the top-level error object. In the case of a request that is composed of multiple operations, such as a bulk or batch operation, it might be necessary to return an independent error for each operation. In this case, the details list is populated with these individual errors.</p>
                </div>
            </td>
        </tr>
    </tbody>
</table>

## ASP.NET Core Implementation ##

There's a lot to research, when it comes to Error Handling in ASP.NET Core.

There are `ProblemDetails`, an `IProblemDetailsService`, `ProblemDetailsFactory`, `InvalidModelStateResponseFactory`, 
`IProblemDetailsWriter`, `IExceptionFilter`, `IAsyncExceptionFilter`, `IExceptionHandler`, `ExeptionHandlerMiddleware`, 
`IExceptionHandlerFeature`, `StatusCodePages`, `StatusCodePagesWithReExecute`, ... and the list goes on.

Let's go!

### Error Codes ###

By all means, you should use application-specific error codes. It's going to help debugging issues from users and 
creates satisfied users. It helps your support team to quickly narrow down possible error reasons. If you achieve a 
globally unique error code, then users could also search the documentation or the internet for them, thus 
reducing pressure on your second level support.

As a Front end developer and consumer of an API, you'll need error codes to localize error messages for users. You could 
also localize error messages in the backend, but I didn't have good experience with it and the OData specification also 
argue against it. Your milage may vary, though.

So we start our journey with a static class `ErrorCodes` to hold error codes, which the OData API can return. I don't 
want the Error Codes as an `enum`, because it needs to be more flexible. Think of separate modules, or some Stored 
Procedure coughing up errors.

In the example application, all Error Codes have the Scheme `ApiError_{Category}_{ErrorNumber}`, you could come up 
with your own. Here are some errors I came up with, you could come up with more errors in your application.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Error Codes used in the Application.
    /// </summary>
    public static class ErrorCodes
    {
        /// <summary>
        /// Internal Server Error.
        /// </summary>
        public const string InternalServerError = "ApiError_System_000001";

        /// <summary>
        /// BadRequest.
        /// </summary>
        public const string BadRequest = "ApiError_System_000002";

        /// <summary>
        /// Validation Error.
        /// </summary>
        public const string ValidationFailed = "ApiError_Validation_000001";

        /// <summary>
        /// General Authentication Error.
        /// </summary>
        public const string AuthenticationFailed = "ApiError_Auth_000001";

        /// <summary>
        /// Entity has not been found.
        /// </summary>
        public const string EntityNotFound = "ApiError_Entity_000001";

        /// <summary>
        /// Access to Entity has been unauthorized.
        /// </summary>
        public const string EntityUnauthorized = "ApiError_Entity_000002";

        /// <summary>
        /// Entity has been modified concurrently.
        /// </summary>
        public const string EntityConcurrencyFailure = "ApiError_Entity_000003";
    }
}
```

### Defining an Exception Hiearchy ###

I am going to use Exceptions to signal failure within the Business Logic, so I am defining an Exception hierarchy.

In the application all exceptions derive from an `ApplicationErrorException`. The `ApplicationErrorException` transports an 
`ErrorCode`, an `ErrorMessage` and a `HttpStatusCode` (this one makes things easier). Specialized `ApplicationErrorExceptions` 
are probably containing more information, but that's the contract all application errors agree on.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    /// <summary>
    /// Base Exception for the Application.
    /// </summary>
    public abstract class ApplicationErrorException : Exception
    {
        /// <summary>
        /// Gets the Error Code.
        /// </summary>
        public abstract string ErrorCode { get; }

        /// <summary>
        /// Gets the Error Message.
        /// </summary>
        public abstract string ErrorMessage { get; }
        
        /// <summary>
        /// Gets the HttpStatusCode.
        /// </summary>
        public abstract int HttpStatusCode { get; }
        
        protected ApplicationErrorException(string? message, Exception? innerException)
            : base(message, innerException)
        {
        }
    }
}
```

Think of a situation, where a user wants to sign in to our system. In our Service we might throw something like 
an `AuthenticationFailedException`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using RebacExperiments.Server.Api.Infrastructure.Errors;

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    public class AuthenticationFailedException : ApplicationErrorException
    {
        /// <inheritdoc/>
        public override string ErrorCode => ErrorCodes.AuthenticationFailed;

        /// <inheritdoc/>
        public override string ErrorMessage => $"AuthenticationFailed";

        /// <inheritdoc/>
        public override int HttpStatusCode => StatusCodes.Status401Unauthorized;

        /// <summary>
        /// Creates a new <see cref="AuthenticationFailedException"/>.
        /// </summary>
        /// <param name="message">Error Message</param>
        /// <param name="innerException">Reference to the Inner Exception</param>
        public AuthenticationFailedException(string? message = null, Exception? innerException = null)
            : base(message, innerException)
        {
        }
    }
}
```

Something like failing to find an `Entity` in the application may lead to an `EntityNotFoundException`, which also 
includes additional information, like the `EntityName` and `EntityId`. This might not be immediately useful to the 
user, but it might make it easier for support to identify errors.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using RebacExperiments.Server.Api.Infrastructure.Errors;

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    public class EntityNotFoundException : ApplicationErrorException
    {
        /// <inheritdoc/>
        public override string ErrorCode => ErrorCodes.EntityNotFound;

        /// <inheritdoc/>
        public override string ErrorMessage => $"EntityNotFound (Entity = {EntityName}, EntityID = {EntityId})";

        /// <inheritdoc/>
        public override int HttpStatusCode => StatusCodes.Status404NotFound;

        /// <summary>
        /// Gets or sets the Entity Name.
        /// </summary>
        public required string EntityName { get; set; }

        /// <summary>
        /// Gets or sets the EntityId.
        /// </summary>
        public required int EntityId { get; set; }

        /// <summary>
        /// Creates a new <see cref="EntityNotFoundException"/>.
        /// </summary>
        /// <param name="message">Error Message</param>
        /// <param name="innerException">Reference to the Inner Exception</param>
        public EntityNotFoundException(string? message = null, Exception? innerException = null)
            : base(message, innerException)
        {
        }
    }
}
```

Now it's tempting to throw Exceptions all the way up to an `IExceptionHandler`, but we should avoid bubbling up exceptions in 
the ASP.NET Core pipeline, as David Fowler states ...

> Exceptions are extremely expensive, even more expensive than usual when they are in the ASP.NET Core pipeline which is fully 
> asynchronous and nested (we're looking at ways to make this cheaper but it's still very expensive). In fact, there are teams 
> with high scale services that see performance problems with exceptions and are trying to avoid them happening. There's 
> no way we'd do #47020.

So we should use the `IExceptionHandler` only for that, exceptional situations we cannot recover from. We should instead try to 
catch `Exceptions` thrown in our services, directly where they happen, and translate them into something useful... instead of 
sending them up the ASP.NET Core pipeline.

Let's take a look at the `MeController` used in the application, which returns the information about the current user. We 
basically wrap everything in the Action in a `try-catch` block, so the Exception doesn't bubble up to the ASP.NET Core 
Pipeline.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class MeController : ODataController
    {
        private readonly ILogger<UsersController> _logger;


        public MeController(ILogger<UsersController> logger)
        {
            _logger = logger;
        }

        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> Get([FromServices] IUserService userService, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();
            
            try
            {
                if (!ModelState.IsValid)
                {
                    throw new InvalidModelStateException
                    {
                        ModelStateDictionary = ModelState
                    };
                }

                // Get the User ID extracted by the Authentication Middleware:
                var meUserId = User.GetUserId();

                var user = await userService.GetUserByIdAsync(meUserId, meUserId, cancellationToken);

                return Ok(user);
            } 
            catch (Exception ex)
            {
                // What to do?
            }
        }
    }
}
```

See the `// What to do`? The question now is, how we will process these Exceptions.

### Handling Exceptions and building the ODataError Response Model ###

The `Microsoft.OData` library already provides an `ODataError`, and that's our error response model to return. It 
sounds like we need something to "translate an `Exception` into an `ODataError`", defining some kind of 
`IODataExceptionTranslator` feels like the right thing to do.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using RebacExperiments.Server.Api.Infrastructure.OData;

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// A Translator to convert from an <see cref="Exception"/> to an <see cref="ObjectODataErrorResult"/>.
    /// </summary>
    public interface IODataExceptionTranslator
    {
        /// <summary>
        /// Translates a given <see cref="Exception"/> into an <see cref="ObjectODataErrorResult"/>.
        /// </summary>
        /// <param name="exception">Exception to translate</param>
        /// <param name="includeExceptionDetails">A flag, if exception details should be included</param>
        /// <returns>The <see cref="ObjectODataErrorResult"/> for the <see cref="Exception"/></returns>
        ObjectODataErrorResult GetODataErrorResult(Exception exception, bool includeExceptionDetails);

        /// <summary>
        /// Gets or sets the Exception Type.
        /// </summary>
        Type ExceptionType { get; }
    }
}
``` 

The `ObjectODataErrorResult` is just a very simple `ActionResult`, because I found the built-in ASP.NET Core 
OData implementations are making too many assumptions, like the `ODataError` error code automatically being 
the HTTP Status Code.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.OData.Results;
using Microsoft.OData;

namespace RebacExperiments.Server.Api.Infrastructure.OData
{
    /// <summary>
    /// Represents a result that when executed will produce an <see cref="ActionResult"/>.
    /// </summary>
    /// <remarks>This result creates an <see cref="ODataError"/> response.</remarks>
    public class ObjectODataErrorResult : ActionResult, IODataErrorResult
    {
        /// <summary>
        /// OData error.
        /// </summary>
        public required ODataError Error { get; set; }

        /// <summary>
        /// Http Status Code.
        /// </summary>
        public required int HttpStatusCode { get; set; }

        /// <inheritdoc/>
        public async override Task ExecuteResultAsync(ActionContext context)
        {

            ObjectResult objectResult = new ObjectResult(Error)
            {
                StatusCode = HttpStatusCode
            };

            await objectResult.ExecuteResultAsync(context).ConfigureAwait(false);
        }
    }
}
```

Now let's implement it for some Exceptions. 

We'll start with the most generic one, that handles the `System.Exception`. This indicates, that something out of our control 
happened, such as EntityFramework Core coughing up Exceptions we don't know. There's not much we can do for the user here, it 
smells like an `InternalServerError`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Infrastructure.Errors.Translators
{
    public class DefaultErrorExceptionTranslator : IODataExceptionTranslator
    {
        private readonly ILogger<DefaultErrorExceptionTranslator> _logger;

        public DefaultErrorExceptionTranslator(ILogger<DefaultErrorExceptionTranslator> logger)
        {
            _logger = logger;
        }

        public Type ExceptionType => typeof(Exception);

        public ObjectODataErrorResult GetODataErrorResult(Exception exception, bool includeExceptionDetails)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.InternalServerError,
                Message = "An Internal Server Error occured"
            };

            // Create the Inner Error
            error.InnerError = new ODataInnerError();

            if (includeExceptionDetails)
            {
                error.InnerError.Message = exception.Message;
                error.InnerError.StackTrace = exception.StackTrace;
                error.InnerError.TypeName = exception.GetType().Name;
            }

            return new ObjectODataErrorResult
            {
                Error = error,
                HttpStatusCode = StatusCodes.Status500InternalServerError,
            };
        }
    }
}
```

But if we catch a `ApplicationErrorException` we can actually do something sensible with it. We have an `ErrorCode`, an 
`ErrorMessage` and a HTTP Status Code. If the environment is a Debug or Staging environment, we can also return the 
Stack Trace.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData;
using RebacExperiments.Server.Api.Infrastructure.Exceptions;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Infrastructure.OData;

namespace RebacExperiments.Server.Api.Infrastructure.Errors.Translators
{
    public class ApplicationErrorExceptionTranslator : IODataExceptionTranslator
    {
        private readonly ILogger<ApplicationErrorExceptionTranslator> _logger;

        public ApplicationErrorExceptionTranslator(ILogger<ApplicationErrorExceptionTranslator> logger)
        {
            _logger = logger;
        }

        /// <inheritdoc/>
        public ObjectODataErrorResult GetODataErrorResult(Exception exception, bool includeExceptionDetails)
        {
            _logger.TraceMethodEntry();

            var applicationErrorException = (ApplicationErrorException)exception;

            return InternalGetODataErrorResult(applicationErrorException, includeExceptionDetails);
        }

        private ObjectODataErrorResult InternalGetODataErrorResult(ApplicationErrorException exception, bool includeExceptionDetails)
        {
            var error = new ODataError
            {
                ErrorCode = exception.ErrorCode,
                Message = exception.ErrorMessage,
            };

            // Create the Inner Error
            error.InnerError = new ODataInnerError();

            if (includeExceptionDetails)
            {
                error.InnerError.Message = exception.Message;
                error.InnerError.StackTrace = exception.StackTrace;
                error.InnerError.TypeName = exception.GetType().Name;
            }

            return new ObjectODataErrorResult
            {
                Error = error,
                HttpStatusCode = exception.HttpStatusCode,
            };
        }

        /// <inheritdoc/>
        public Type ExceptionType => typeof(ApplicationErrorException);
    }
}
```

And finally there are cases, where specialized Exceptions like a `InvalidModelStateException` need to be handled. This exception 
is thrown for example, when the ASP.NET Core MVC does model binding or validation fails. This can be turned into something more 
useful, than just a code and a message.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc.ModelBinding;
using Microsoft.OData;
using RebacExperiments.Server.Api.Infrastructure.Exceptions;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Infrastructure.OData;

namespace RebacExperiments.Server.Api.Infrastructure.Errors.Translators
{
    public class InvalidModelStateExceptionTranslator : IODataExceptionTranslator
    {
        private readonly ILogger<InvalidModelStateExceptionTranslator> _logger;

        public InvalidModelStateExceptionTranslator(ILogger<InvalidModelStateExceptionTranslator> logger)
        {
            _logger = logger;
        }

        /// <inheritdoc/>
        public ObjectODataErrorResult GetODataErrorResult(Exception exception, bool includeExceptionDetails)
        {
            var invalidModelStateException = (InvalidModelStateException) exception;

            return InternalGetODataErrorResult(invalidModelStateException, includeExceptionDetails);
        }

        /// <inheritdoc/>
        public Type ExceptionType => typeof(InvalidModelStateException);

        private ObjectODataErrorResult InternalGetODataErrorResult(InvalidModelStateException exception, bool includeExceptionDetails)
        {
            _logger.TraceMethodEntry();

            if (exception.ModelStateDictionary.IsValid)
            {
                throw new InvalidOperationException("Could not create an error response from a valid ModelStateDictionary");
            }

            ODataError error = new ODataError()
            {
                ErrorCode = ErrorCodes.ValidationFailed,
                Message = "One or more validation errors occured",
                Details = GetODataErrorDetails(exception.ModelStateDictionary),
            };

            // Create the Inner Error
            error.InnerError = new ODataInnerError();

            if (includeExceptionDetails)
            {
                error.InnerError.Message = exception.Message;
                error.InnerError.StackTrace = exception.StackTrace;
                error.InnerError.TypeName = exception.GetType().Name;
            }

            // If we have something like a Deserialization issue, the ModelStateDictionary has
            // a lower-level Exception. We cannot do anything sensible with exceptions, so 
            // we add it to the InnerError.
            var firstException = GetFirstException(exception.ModelStateDictionary);

            if (firstException != null)
            {
                _logger.LogWarning(firstException, "The ModelState contains an Exception, which has caused the invalid state");

                error.InnerError.InnerError = new ODataInnerError
                {
                    Message = firstException.Message,
                    StackTrace = firstException.StackTrace,
                    TypeName = firstException.GetType().Name,
                };
            }

            return new ObjectODataErrorResult
            {
                HttpStatusCode = StatusCodes.Status400BadRequest,
                Error = error
            };
        }

        private Exception? GetFirstException(ModelStateDictionary modelStateDictionary)
        {
            _logger.TraceMethodEntry();

            foreach (var modelStateEntry in modelStateDictionary)
            {
                foreach (var modelError in modelStateEntry.Value.Errors)
                {
                    if (modelError.Exception != null)
                    {
                        return modelError.Exception;
                    }
                }
            }

            return null;
        }

        private List<ODataErrorDetail> GetODataErrorDetails(ModelStateDictionary modelStateDictionary)
        {
            _logger.TraceMethodEntry();

            var result = new List<ODataErrorDetail>();

            foreach (var modelStateEntry in modelStateDictionary)
            {
                foreach (var modelError in modelStateEntry.Value.Errors)
                {
                    // We cannot make anything sensible for the caller here. We log it, but then go on 
                    // as if nothing has happened. Alternative is to populate a chain of ODataInnerError 
                    // or abuse the ODataErrorDetails...
                    if (modelError.Exception != null)
                    {
                        continue;
                    }

                    // A ModelStateDictionary has nothing like an "ErrorCode" and it's not 
                    // possible with existing infrastructure to get an "ErrorCode" here. So 
                    // we set a generic one.
                    var errorCode = ErrorCodes.ValidationFailed;

                    var odataErrorDetail = new ODataErrorDetail
                    {
                        ErrorCode = errorCode,
                        Message = modelError.ErrorMessage,
                        Target = modelStateEntry.Key,
                    };

                    result.Add(odataErrorDetail);
                }
            }

            return result;
        }
    }
}
```

Then we are adding our `IODataExceptionTranslators` to the `IServiceCollection` in the Applications Startup:

```csharp
// Add Exception Handling
builder.Services.AddSingleton<IODataExceptionTranslator, DefaultErrorExceptionTranslator>();
builder.Services.AddSingleton<IODataExceptionTranslator, ApplicationErrorExceptionTranslator>();
builder.Services.AddSingleton<IODataExceptionTranslator, InvalidModelStateExceptionTranslator>();
```

And finally, we need to add some metadata to the `ODataError` like a `trace-id`, before returning it. This is going to enable us 
to correlate messages of users with exceptions in the logs. We also need a way to resolve the correct `IODataExceptionTranslator` 
for the Exception being thrown, so let's put all this into something I called an `ExceptionToODataErrorMapper`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Handles errors returned by the application.
    /// </summary>
    public class ExceptionToODataErrorMapper
    {
        private readonly ILogger<ExceptionToODataErrorMapper> _logger;

        private readonly ExceptionToODataErrorMapperOptions _options;
        private readonly Dictionary<Type, IODataExceptionTranslator> _translators;

        public ExceptionToODataErrorMapper(ILogger<ExceptionToODataErrorMapper> logger, IOptions<ExceptionToODataErrorMapperOptions> options, IEnumerable<IODataExceptionTranslator> translators)
        {
            _logger = logger;
            _options = options.Value;
            _translators = translators.ToDictionary(x => x.ExceptionType, x => x);
        }

        public ObjectODataErrorResult CreateODataErrorResult(HttpContext httpContext, Exception exception)
        {
            _logger.TraceMethodEntry();

            _logger.LogError(exception, "Call to '{RequestPath}' failed due to an Exception", httpContext.Request.Path);

            // Get the best matching translator for the exception ...
            var translator = GetTranslator(exception);

            // ... translate it to the Result ...
            var error = translator.GetODataErrorResult(exception, _options.IncludeExceptionDetails);

            // ... add error metadata, such as a Trace ID, ...
            AddMetadata(httpContext, error);

            // ... and return it.
            return error;
        }

        private void AddMetadata(HttpContext httpContext, ObjectODataErrorResult result)
        {
            if(result.Error.InnerError == null)
            {
                result.Error.InnerError = new ODataInnerError();
            }

            result.Error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(httpContext.TraceIdentifier);
        }

        private IODataExceptionTranslator GetTranslator(Exception e)
        {
            if (e is ApplicationErrorException)
            {
                if (_translators.TryGetValue(e.GetType(), out var translator))
                {
                    return translator;
                }

                return _translators[typeof(ApplicationErrorException)];
            }

            return _translators[typeof(Exception)];
        }
    }
}
```

To prevent leaking something like a Stacktrace to our users, we need some `ExceptionToODataErrorMapperOptions` to configure it.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Options for the <see cref="ExceptionToODataErrorMapper"/>.
    /// </summary>
    public class ExceptionToODataErrorMapperOptions
    {
        /// <summary>
        /// Gets or sets the option to include the Exception Details in the response.
        /// </summary>
        public bool IncludeExceptionDetails { get; set; } = false;
    }
}
```

And add it to the Application Services.

```csharp
// Add Exception Handling

// ...

builder.Services.Configure<ODataErrorMapperOptions>(o =>
{
    o.IncludeExceptionDetails = builder.Environment.IsDevelopment() || builder.Environment.IsStaging();
});

builder.Services.AddSingleton<ODataErrorMapper>();
```

We can then inject it to the Controller and handle the exceptions, where they are thrown.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class MeController : ODataController
    {
        private readonly ILogger<UsersController> _logger;

        private readonly ODataErrorMapper _odataErrorMapper;

        public MeController(ILogger<UsersController> logger, ODataErrorMapper odataErrorMapper)
        {
            _logger = logger;
            _odataErrorMapper = odataErrorMapper;
        }

        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> Get([FromServices] IUserService userService, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            try
            {
                // ...
            }
            catch (Exception exception)
            {
                return _odataErrorMapper.CreateODataErrorResult(HttpContext, exception);
            }
        }
    }
}
```

### Configuring ASP.NET Core Middlewares for the OData Error Response ###

In an ASP.NET Core application, there are many places things might go wrong. And these things may happen, before anything goes 
into out `Controller`. They happen in the Middleware, like what happens if we cannot resolve a Controller? We get a HTTP 
Status 404, but it's not in our nice error format.

This might not be much of a problem, but we should really have a consistent error model for all requests. If a Route 
cannot be resolved, it should also map to an error code an application can localize. Say, if we only use a HTTP Status 404 
for both, a missing route and missing entity... how can we turn this into a sensible error message?

So we need to add some Status Code mapping to our ASP.NET Core Pipeline.

```csharp
app.UseStatusCodePagesWithReExecute("/error/{0}");
```

In the `ErrorController` we can then handle these errors accordingly. The sad thing here is, that I have no idea, how 
to nicely format a negotiated `ODataError` there. As of now I accept, that we'll only return a JSON representation, 
because none of the OData MVC Output Formatters can be used.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.OData;
using RebacExperiments.Server.Api.Infrastructure.Errors;
using RebacExperiments.Server.Api.Infrastructure.Logging;

namespace RebacExperiments.Server.Api.Controllers
{
    public class ErrorController : ControllerBase
    {
        private readonly ILogger<ErrorController> _logger;

        private readonly ODataErrorMapper _odataErrorMapper;

        public ErrorController(ILogger<ErrorController> logger, ODataErrorMapper exceptionToODataErrorMapper)
        {
            _logger = logger;
            _odataErrorMapper = exceptionToODataErrorMapper;
        }
        
        // ...

        [Route("/error/401")]
        public IActionResult HandleHttpStatus401()
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.Unauthorized,
                Message = "Unauthorized"
            };

            error.InnerError = new ODataInnerError();
            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(HttpContext.TraceIdentifier);
     
            return new ContentResult
            {
                Content = error.ToString(),
                ContentType = "application/json",
                StatusCode = StatusCodes.Status401Unauthorized
            };
        }

        [Route("/error/404")]
        public IActionResult HandleHttpStatus404()
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.ResourceNotFound,
                Message = "ResourceNotFound"
            };
            
            error.InnerError = new ODataInnerError();
            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(HttpContext.TraceIdentifier);

            return new ContentResult 
            { 
                Content = error.ToString(), 
                ContentType = "application/json", 
                StatusCode = StatusCodes.Status404NotFound 
            };
        }

        [Route("/error/405")]
        public IActionResult HandleHttpStatus405()
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.MethodNotAllowed,
                Message = "MethodNotAllowed"
            };

            error.InnerError = new ODataInnerError();
            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(HttpContext.TraceIdentifier);

            return new ContentResult 
            { 
                Content = error.ToString(), 
                ContentType = "application/json",
                StatusCode = StatusCodes.Status405MethodNotAllowed
            };
        }

        [Route("/error/429")]
        public IActionResult HandleHttpStatus429()
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.TooManyRequests,
                Message = "TooManyRequests"
            };

            error.InnerError = new ODataInnerError();
            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(HttpContext.TraceIdentifier);

            return new ContentResult
            {
                Content = error.ToString(),
                ContentType = "application/json",
                StatusCode = StatusCodes.Status429TooManyRequests
            };
        }
    }
}
```

If we now hit a non existing route, we get the following error response. Note, the empty values are set by 
the `Microsoft.OData` implementation to provide backward-compatibility to their previous WCF 
implementations.

```json
{
    "error": {
        "code": "ApiError_Routing_000001",
        "message": "ResourceNotFound",
        "target": "",
        "details": {},
        "innererror": {
            "message": "",
            "type": "",
            "stacktrace": "",
            "innererror": {},
            "trace-id": "0HN0MDPKDBD80:00000003"
        }
    }
}
```

### Adding a Global Exception Handler for Uncaught Exceptions ###

There might be exceptions still bubbling up the stack, and we need to catch them. This is done by adding 
an Error Handler. You can use an `IExceptionHandler` or an `Exception Handla Lambda` function. But I think 
we can just reuse our `ErrorController` like this:

```csharp
app.UseExceptionHandler("/error");
```

And in the `ErrorController` we are reusing the `ODataErrorMapper` to convert the `Exception` into something sensible. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class ErrorController : ControllerBase
    {
        private readonly ILogger<ErrorController> _logger;

        private readonly ODataErrorMapper _odataErrorMapper;

        public ErrorController(ILogger<ErrorController> logger, ODataErrorMapper exceptionToODataErrorMapper)
        {
            _logger = logger;
            _odataErrorMapper = exceptionToODataErrorMapper;
        }

        [Route("/error")]
        public IActionResult HandleError()
        {
            _logger.TraceMethodEntry();

            var exceptionHandlerFeature = HttpContext.Features.Get<IExceptionHandlerFeature>()!;

            var error = _odataErrorMapper.CreateODataErrorResult(HttpContext, exceptionHandlerFeature.Error);

            return new ContentResult
            {
                Content = error.ToString(),
                ContentType = "application/json",
                StatusCode = StatusCodes.Status400BadRequest
            };
        }
        
        // ...
    }
}
```

Great!

### Conclusion ###

And that's it! I think we now have a consistent `ODataError` throughout our entire ASP.NET Core application. I am not proud 
of the non-negotiated errors happening within the Middleware. But I didn't find a "simple" way to negotiate the response, when 
all ASP.NET Core Odata `OutputFormatter` implementations require us to run on OData Routes. 

## Handling ASP.NET Core OData Errors in the Blazor Frontend ##

### Generating the Api SDK ###

I think it's a waste of time to hand-write an Api SDK for a RESTful API. 

The Microsoft Graph API is an OData API and it has thousands of endpoints. It's useful to understand how Microsoft themselves are 
generating their Microsoft Graph SDK. While it's literally impossible to know their exact stack, I can make an educated guess from 
the GitHub Issues raised in Kiota:

1. Convert the OData CSDL to an OpenAPI 3 Schema, using `Microsoft.OpenApi.OData`.
2. Generate the Microsoft Graph SDK from the OpenAPI 3 Schema, using the Kiota CLI.

So in our Backend we add an Endpoint `odata/openapi.json`, that converts from CSDL to OpenAPI 3.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    /// <summary>
    /// This Controller exposes an Endpoint for the OpenAPI Schema, which will be generated from an <see cref="IEdmModel"/>.
    /// </summary>
    public class OpenApiController : ControllerBase
    {
        private readonly ILogger<AuthenticationController> _logger;

        private readonly ODataErrorMapper _odataErrorMapper;

        public OpenApiController(ILogger<AuthenticationController> logger, ODataErrorMapper odataErrorMapper)
        {
            _logger = logger;
            _odataErrorMapper = odataErrorMapper;
        }

        [HttpGet("odata/openapi.json")]
        public IActionResult GetOpenApiJson()
        {
            _logger.TraceMethodEntry();

            try
            {
                var edmModel = ApplicationEdmModel.GetEdmModel();

                var openApiSettings = new OpenApiConvertSettings
                {
                    ServiceRoot = new("https://localhost:5000"),
                    PathPrefix = "odata",
                    EnableKeyAsSegment = true,
                };

                var openApiDocument = edmModel.ConvertToOpenApi(openApiSettings);

                var openApiDocumentAsJson = openApiDocument.SerializeAsJson(OpenApiSpecVersion.OpenApi3_0);

                return Content(openApiDocumentAsJson, "application/json");
            }
            catch (Exception exception)
            {
                return _odataErrorMapper.CreateODataErrorResult(HttpContext, exception);
            }
        }
    }
}
```

If we are running in Debug mode, we can use it to render a Swagger page.

```csharp
if (app.Environment.IsDevelopment() || app.Environment.IsStaging())
{
    app.UseSwagger();
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("https://localhost:5000/odata/openapi.json", "TaskManagement Service");
    });
}
```

We can then use Kiota to generate the C\# client from the OpenAPI Schema at `/odata/openapi.json`.

Kiota is available at:

* [https://aka.ms/kiota](https://aka.ms/kiota)

It's a command line tool for generating API Clients and is described as ...

> [...] a command line tool for generating an API client to call any OpenAPI-described API 
> you are interested in. The goal is to eliminate the need to take a dependency on a different 
> API SDK for every API that you need to call. Kiota API clients provide a strongly typed 
> experience with all the features you expect from a high quality API SDK, but without 
> having to learn a new library for every HTTP API.

By using a simple Powershell Script `makeSdk.ps1`, we can generate the C\# client.

```powershell
<# Licensed under the MIT license. See LICENSE file in the project root for full license information.#>

# Kiota Executable
$kiota_exe="kiota"

# Parameters for the Code Generator
$param_openapi_schema="https://localhost:5000/odata/openapi.json"
$param_language="csharp"
$param_namespace="RebacExperiments.Shared.ApiSdk"
$param_log_level="Trace"
$param_out_dir="${PSScriptRoot}/src/Shared/RebacExperiments.Shared.ApiSdk"

# Construct the "kiota generate" Command
$cmd="${kiota_exe} generate --openapi ${param_openapi_schema} --language ${param_language} --namespace-name ${param_namespace} --log-level ${param_log_level} --output ${param_out_dir}"

# Run the the "kiota generate" Command
Invoke-Expression $cmd
```

After executing the Script it generates the `ODataError` model for us. In the generated files we can see our expected classes.

```
PS C:\Users\philipp\source\repos\bytefish\ODataRebacExperiments\src\Shared\RebacExperiments.Shared.ApiSdk> tree /f
Folder PATH listing for volume OS
Volume serial number is 1274-2B9B
C:.
│   ApiClient.cs
│   kiota-lock.json
│   RebacExperiments.Shared.ApiSdk.csproj
│
├───Models
│   └───ODataErrors
│           ErrorDetails.cs
│           InnerError.cs
│           MainError.cs
│           ODataError.cs
│
│ ...
```

Nice!

### Translating the ODataErrors ###

If you dig deep enough into the generated code, you will see, that it throws an Exception for failed HTTP Requests, such as a `401 (Unauthorized)`. It 
specifically throws an `ODataError` exception, which contains the `MainError` we want to inspect.

```csharp
// <auto-generated/>

// ...

namespace RebacExperiments.Shared.ApiSdk.Models.ODataErrors {
    public class ODataError : ApiException, IAdditionalDataHolder, IParsable {
        /// <summary>Stores additional data not described in the OpenAPI description found when deserializing. Can be used for serialization as well.</summary>
        public IDictionary<string, object> AdditionalData { get; set; }
        /// <summary>The error property</summary>
        public MainError Error { get; set; }
        /// <summary>The primary error message.</summary>
        public override string Message { get => base.Message; }
        /// <summary>
        /// Instantiates a new ODataError and sets the default values.
        /// </summary>
        public ODataError() {
            AdditionalData = new Dictionary<string, object>();
        }
        
        // ...
    }
}
```

That also means: You should wrap all calls to the generated Kiota `ApiClient` inside a `try-catch` block. Blazor doesn't have a notion of 
a "Global Exception Handler", so bubbling up exceptions probably isn't useful. Who is going to catch them? Your Error Boundary probably?

We can then write an `ApplicationErrorTranslator`, that takes an `ODataError` and converts it into a nicely 
localized error message. It uses an `IStringLocalizer<SharedResource>` to lookup the error code in a 
`SharedResource.resx` Resource file.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Extensions.Localization;
using RebacExperiments.Blazor.Localization;
using RebacExperiments.Shared.ApiSdk.Models.ODataErrors;
using System.Diagnostics.CodeAnalysis;

namespace RebacExperiments.Blazor.Infrastructure
{
    public class ApplicationErrorTranslator
    {
        private readonly IStringLocalizer<SharedResource> _sharedLocalizer;

        public ApplicationErrorTranslator(IStringLocalizer<SharedResource> sharedLocalizer) 
        { 
            _sharedLocalizer = sharedLocalizer;
        }

        public string GetErrorMessage(Exception exception) 
        {
            return exception switch
            {
                ODataError e => GetErrorMessageFromODataError(e),
                Exception e => GetErrorMessageFromException(e),
            };
        }

        private string GetErrorMessageFromODataError(ODataError error)
        {
            // Extract the ErrorCode from the OData MainError.
            string errorCode = error.Error!.Code!;

            // And get the Error Message by the Error Code.
            string errorCodeMessage = _sharedLocalizer[errorCode];

            // Format with Trace ID for correlating user error reports with logs.
            if(TryGetRequestTraceId(error.Error!, out string? traceId))
            {
                return $"{errorCodeMessage} (Error Code = '{errorCode}', TraceID = '{traceId}')";
            }

            return $"{errorCodeMessage} (Error Code = '{errorCode}')";
        }

        private string GetErrorMessageFromException(Exception e)
        {
            string errorMessage = _sharedLocalizer["ApplicationError_Exception"];

            return errorMessage;
        }

        private bool TryGetRequestTraceId(MainError mainError, [NotNullWhen(true)] out string? requestTraceId)
        {
            requestTraceId = null;

            if(mainError.Innererror == null)
            {
                return false;
            }

            var innerError = mainError.Innererror;

            if(!innerError.AdditionalData.ContainsKey("trace-id"))
            {
                return false;
            }

            requestTraceId = innerError.AdditionalData["trace-id"] as string;

            if(requestTraceId == null)
            {
                return false;
            }

            return true;
        }
    }
}
```

This can be used for example in a `Login` Razor Page, so we can display an `ErrorMessage`, if the OData Backend returns 
an error, such as a failed Authentication or Internal Server Errors. You start by injecting all dependencies in 
the `Login.razor` component.

```razor
<!-- ... -->

@inject ApiClient ApiClient
@inject ApplicationErrorTranslator ApplicationErrorTranslator
@inject IStringLocalizer<SharedResource> Loc
@inject NavigationManager NavigationManager

<div class="container">
    <FluentCard Width="500px">
        <EditForm Model="@Input" OnValidSubmit="SignInUserAsync" FormName="login_form" novalidate>
            <SimpleValidator TModel=InputModel ValidationFunc="ValidateInputModel" />
            <FluentValidationSummary />
            <FluentStack Orientation="Orientation.Vertical">
                <FluentGrid Spacing="3" Justify="JustifyContent.Center">
                    <FluentGridItem xs="12">
                        <h1>Login</h1>
                     </FluentGridItem>
                    <FluentGridItem xs="12">
                        <FluentTextField Name="login_eMail" Style="width: 100%" @bind-Value="Input.Email" Label=@Loc["Login_Email"] Required />
                         <FluentValidationMessage For="@(() => Input.Email)" />
                     </FluentGridItem>
                     <!-- ... -->
                     @if(!string.IsNullOrWhiteSpace(ErrorMessage)) {
                        <FluentGridItem xs="12">
                            <FluentMessageBar Style="width: 100%" Title="Error" Intent="@MessageIntent.Error" Type="MessageType.MessageBar">
                                @ErrorMessage
                            </FluentMessageBar>
                        </FluentGridItem>
                     }
                </FluentGrid>
            </FluentStack>
        </EditForm>
    </FluentCard>
</div>
```

And in the Code-Behind we can see how the `ApiClient` calls are wrapped in a `try-catch` block and the `ApplicationErrorTranslator` 
is used to convert the `Exception` into a more user-friendly error message.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Blazor.Pages
{
    public partial class Login
    {

        // ...

        /// <summary>
        /// Signs in the User to the Service using Cookie Authentication.
        /// </summary>
        /// <returns></returns>
        public async Task SignInUserAsync()
        {
            ErrorMessage = null;

            try
            {
                // Sign in the User, which sets the Auth Cookie ...
                await ApiClient.Odata.SignInUser.PostAsync(new SignInUserPostRequestBody
                {
                    Username = Input.Email,
                    Password = Input.Password,
                    RememberMe = true
                });

                // ... then get the User Profile ...
                var me = await ApiClient.Odata.Me.GetAsync();

                // ... then set the new User Profile ...
                await AuthStateProvider.SetCurrentUserAsync(me);

                // ... and navigate to the ReturnUrl.
                var navigationUrl = GetNavigationUrl();

                NavigationManager.NavigateTo(navigationUrl);
            }
            catch(Exception e)
            {
                ErrorMessage = ApplicationErrorTranslator.GetErrorMessage(e);
            }
        }
        
        // ...
    }
}
```

## Conclusion ##

And that's it! 

This application is now a fine blueprint to quickly build an ASP.NET Core Backend with consistent error handling and a 
nice way to quickly build API SDKs using Kiota. By using Blazor you don't have to switch between too many paradigms and 
gain some kind of "Rapid Application Development".

I am not saying all this in here is a perfect approach! But it is a very straight-forward one. And I think it can be 
well understood, without diving too deep into all the ASP.NET Core Error Handling infrastructure.

It might be interesting to see, how this can be built using the existing `ProblemDetails` infrastructure. I have the feeling, 
that an `IProblemDetailsWriter` might be sufficient, but... it turned out to be way too complicated for me.