title: Blazor WebAssembly with Cookie Authentication
date: 2024-01-11 11:46
tags: blazor, dotnet
category: dotnet
slug: blazor_wasm_cookie_authentication
author: Philipp Wagner
summary: This article shows how to use Cookie Authentication with Blazor WebAssembly. 

[Consistent Error Handling with NancyFx]: https://www.bytefish.de/blog/consistent_error_handling_with_nancy.html

In this article we are going to look at one of the most important, yet underrated, aspects of any 
customer-facing software: Error Handling and Error Messages. I am working on an ASP.NET Core OData 
application and want something similar to the Microsoft Graph API Error Handling.

Let's see how to do it!

## OData Error Model ##

Our Errors should be modeled after the Microsoft Graph API, which is an OData API. So there are two things to note: The 
ASP.NET Core OData implementation already includes a similar `ODataError` model and the Microsoft Graph API documentation 
somewhat applies to our application as well.

You can find the 

* [https://learn.microsoft.com/de-de/dotnet/api/microsoft.odata.odataerror](https://learn.microsoft.com/de-de/dotnet/api/microsoft.odata.odataerror)

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

## Error Codes ##

By all means, you should use application-specific error codes. It's going to help debugging issues from 
users and creates satisfied users. It helps your support team to quickly narrow down possible error 
reasons. If you achieve a globally unique error code, then users could also search the documentation for them 
or search for the error codes online, which might reduce issue reports to your support team.

As a developer and consumer of an API, you'll need error codes to localize messages for users. You could also 
localize error messages in the backend, but I didn't have good experience with it and the OData specification 
also argue against it. Your milage may vary, though.

I would start with a static class `ErrorCodes` to hold error codes, that the OData API can return. I don't 
want the Error Codes as an enumeration, because I want to be more flexible. What if the error codes come from 
different sources, think Stored Procedures?

In the example application, all Error Codes have the Scheme `ApiError_{Category}_{ErrorNumber}`. Here are some 
errors I came up with, you could come up with more errors in your application.

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

## How to communicate failure with ASP.NET Core? ##

[Result Types]: 

Now, how do you communicate errors and failure within your application? Do you throw Exceptions? Do you 
return error codes and pray the caller handles them accordingly? Do you try to come up with something 
like [Result Types] to force the caller handling errors? 

[Result Types] are something that's often advocated in the Functional Programming community:

> In functional programming, a result type is a monadic type holding a returned value or an error 
> code. They provide an elegant way of handling errors, without resorting to exception handling; when 
> a function that may fail returns a result type, the programmer is forced to consider success or 
> failure paths, before getting access to the expected result; this eliminates the possibility of 
> an erroneous programmer assumption.

My personal opinion here is a very pragmatic one. 

.NET is a Runtime, that uses Exceptions for communicating failure. You try to access a file, that does 
not exist? Boom, a `FileNotFoundException` in your face! So even if you introduce [Result Types], the 
.NET Runtime may throw at any point... and you suddenly need to deal with two error paradigms.

To quote Eirik Tsarpalis, you're better off using Exceptions:

* [https://eiriktsarpalis.wordpress.com/2017/02/19/youre-better-off-using-exceptions/](https://eiriktsarpalis.wordpress.com/2017/02/19/youre-better-off-using-exceptions/)

### Defining an Exception Hiearchy ###

In the application all exceptions derive from an `ApplicationErrorException`. It should at least transport 
an `ErrorCode` and an `ErrorMessage`. 

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

        protected ApplicationErrorException(string? message, Exception? innerException)
            : base(message, innerException)
        {
        }
    }
}
```

We can then derive from the `ApplicationErrorException` and define specialized Exceptions describing the error 
and (probably) containing additional information. An `AuthenticationFailedException` shouldn't give too much 
hints, so it looks like this.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using RebacExperiments.Server.Api.Infrastructure.Errors;

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    public class AuthenticationFailedException : ApplicationErrorException
    {
        /// <summary>
        /// Gets or sets an ErrorCode.
        /// </summary>
        public override string ErrorCode => ErrorCodes.AuthenticationFailed;

        /// <summary>
        /// Gets or sets an ErrorMessage.
        /// </summary>
        public override string ErrorMessage => $"AuthenticationFailed";

        /// <summary>
        /// Creates a new <see cref="EntityNotFoundException"/>.
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
includes additional information, like the `EntityName` and `EntityId`. This might be useful to debug errors, it's 
up to discussion, if a user needs to see this information however.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using RebacExperiments.Server.Api.Infrastructure.Errors;

namespace RebacExperiments.Server.Api.Infrastructure.Exceptions
{
    public class EntityNotFoundException : ApplicationErrorException
    {
        /// <summary>
        /// Gets or sets an error code.
        /// </summary>
        public override string ErrorCode => ErrorCodes.EntityNotFound;

        /// <summary>
        /// Gets or sets an error code.
        /// </summary>
        public override string ErrorMessage => $"EntityNotFound (Entity = {EntityName}, EntityID = {EntityId})";

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

### Handling Failure and building the ODataError Response Model ###

The ASP.NET Core OData framework already provides an `IODataErrorResult`, which looks like this:

```csharp
//-----------------------------------------------------------------------------
// <copyright file="IODataErrorResult.cs" company=".NET Foundation">
//      Copyright (c) .NET Foundation and Contributors. All rights reserved. 
//      See License.txt in the project root for license information.
// </copyright>
//------------------------------------------------------------------------------

using Microsoft.OData;

namespace Microsoft.AspNetCore.OData.Results
{
    /// <summary>
    /// Provide the interface for the details of a given OData error result.
    /// </summary>
    public interface IODataErrorResult
    {
        /// <summary>
        /// OData error.
        /// </summary>
        ODataError Error { get; }
    }
}
```

It defines several `IODataErrorResult` implementations like a `ConflictODataResult`, `NotFoundODataResult`, which 
basically adds a HTTP Status Code and writes the `ODataError` to the response message. What we will do is to turn 
the Exceptions into an `IODataErrorResult`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.ModelBinding;
using Microsoft.AspNetCore.OData.Results;
using Microsoft.Extensions.Options;
using Microsoft.OData;
using RebacExperiments.Server.Api.Infrastructure.Exceptions;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Infrastructure.OData;
using System.Net;

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Handles errors returned by the application.
    /// </summary>
    public class ApplicationErrorHandler
    {
        private readonly ILogger<ApplicationErrorHandler> _logger;

        private readonly ApplicationErrorHandlerOptions _options;

        public ApplicationErrorHandler(ILogger<ApplicationErrorHandler> logger, IOptions<ApplicationErrorHandlerOptions> options)
        {
            _logger = logger;
            _options = options.Value;
        }

        #region Exception Handling

        public ActionResult HandleException(HttpContext httpContext, Exception exception)
        {
            _logger.TraceMethodEntry();

            _logger.LogError(exception, "Call to '{RequestPath}' failed due to an Exception", httpContext.Request.Path);

            return exception switch
            {
                // Authentication
                AuthenticationFailedException e => HandleAuthenticationException(httpContext, e),
                // Entities
                EntityConcurrencyException e => HandleEntityConcurrencyException(httpContext, e),
                EntityNotFoundException e => HandleEntityNotFoundException(httpContext, e),
                EntityUnauthorizedAccessException e => HandleEntityUnauthorizedException(httpContext, e),
                // Rate Limiting
                RateLimitException e => HandleRateLimitException(httpContext, e),
                // Global Handler
                Exception e => HandleSystemException(httpContext, e)
            };
        }

        private UnauthorizedODataResult HandleAuthenticationException(HttpContext httpContext, AuthenticationFailedException e)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.AuthenticationFailed,
                Message = e.ErrorMessage,
            };

            AddInnerError(httpContext, error, e);

            return new UnauthorizedODataResult(error);
        }

        private ConflictODataResult HandleEntityConcurrencyException(HttpContext httpContext, EntityConcurrencyException e)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = e.ErrorCode,
                Message = e.ErrorMessage,
            };

            AddInnerError(httpContext, error, e);

            return new ConflictODataResult(error);
        }

        private NotFoundODataResult HandleEntityNotFoundException(HttpContext httpContext, EntityNotFoundException e)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = e.ErrorCode,
                Message = e.ErrorMessage,
            };

            AddInnerError(httpContext, error, e);

            return new NotFoundODataResult(error);
        }

        private ForbiddenODataResult HandleEntityUnauthorizedException(HttpContext httpContext, EntityUnauthorizedAccessException e)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = e.ErrorCode,
                Message = e.ErrorMessage,
            };

            AddInnerError(httpContext, error, e);

            return new ForbiddenODataResult(error);
        }
        
        private ObjectResult HandleRateLimitException(HttpContext httpContext, RateLimitException e)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.TooManyRequests,
                Message = "Too many requests. The Rate Limit for the user has been exceeded"
            };

            AddInnerError(httpContext, error, e);

            return new ObjectResult(error)
            {
                StatusCode = (int)HttpStatusCode.TooManyRequests,
            };
        }

        private ObjectResult HandleSystemException(HttpContext httpContext, Exception e)
        {
            _logger.TraceMethodEntry();

            var error = new ODataError
            {
                ErrorCode = ErrorCodes.InternalServerError,
                Message = "An Internal Server Error occured"
            };

            AddInnerError(httpContext, error, e);

            return new ObjectResult(error)
            {
                StatusCode = (int)HttpStatusCode.InternalServerError,
            };
        }

        #endregion Exception Handling

        #region Debug Information

        private void AddInnerError(HttpContext httpContext, ODataError error, Exception? e)
        {
            _logger.TraceMethodEntry();

            error.InnerError = new ODataInnerError();

            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(httpContext.TraceIdentifier);

            if (e != null && _options.IncludeExceptionDetails)
            {
                error.InnerError.Message = e.Message;
                error.InnerError.StackTrace = e.StackTrace;
                error.InnerError.TypeName = e.GetType().Name;
            }
        }

        #endregion Debug Information
    }
}
```

But there are parts of ASP.NET Core, that do not throw Exceptions. An example is, if something like 
binding the request to a model fails, or the built-in validation fails. This is usually communicated 
by a `ModelStateDictionary`.

Let's add it to the `ApplicationErrorHandler`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.ModelBinding;
using Microsoft.AspNetCore.OData.Results;
using Microsoft.Extensions.Options;
using Microsoft.OData;
using RebacExperiments.Server.Api.Infrastructure.Exceptions;
using RebacExperiments.Server.Api.Infrastructure.Logging;
using RebacExperiments.Server.Api.Infrastructure.OData;
using System.Net;

namespace RebacExperiments.Server.Api.Infrastructure.Errors
{
    /// <summary>
    /// Handles errors returned by the application.
    /// </summary>
    public class ApplicationErrorHandler
    {
        private readonly ILogger<ApplicationErrorHandler> _logger;

        private readonly ApplicationErrorHandlerOptions _options;

        public ApplicationErrorHandler(ILogger<ApplicationErrorHandler> logger, IOptions<ApplicationErrorHandlerOptions> options)
        {
            _logger = logger;
            _options = options.Value;
        }

        #region ModelState Handling

        public ActionResult HandleInvalidModelState(HttpContext httpContext, ModelStateDictionary modelStateDictionary)
        {
            _logger.TraceMethodEntry();

            ODataError error = new ODataError()
            {
                ErrorCode = ErrorCodes.BadRequest,
                Message = "One or more validation errors occured",
                Details = GetODataErrorDetails(modelStateDictionary),
            };

            // If we have something like a Deserialization issue, the ModelStateDictionary has
            // a lower-level Exception. We cannot do anything sensible with exceptions, so 
            // we add them to the InnerError.
            var firstException = GetFirstException(modelStateDictionary);

            AddInnerError(httpContext, error, firstException);
            
            return new BadRequestObjectResult(error);
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

            // Validation Details
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
                        _logger.LogError(modelError.Exception, "Invalid ModelState due to an exception");

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

        #endregion ModelState Handling

        #region Debug Information

        private void AddInnerError(HttpContext httpContext, ODataError error, Exception? e)
        {
            _logger.TraceMethodEntry();

            error.InnerError = new ODataInnerError();

            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(httpContext.TraceIdentifier);

            if (e != null && _options.IncludeExceptionDetails)
            {
                error.InnerError.Message = e.Message;
                error.InnerError.StackTrace = e.StackTrace;
                error.InnerError.TypeName = e.GetType().Name;
            }
        }

        #endregion Debug Information
    }
}
```

Now we need to add the `ApplicationErrorHandler` Services. At the same time we configure it to include 
the Stack Trace, depending on the Environment we are currently running in:

```csharp
// Add Error Handler
builder.Services.Configure<ApplicationErrorHandlerOptions>(o =>
{
    o.IncludeExceptionDetails = builder.Environment.IsDevelopment() || builder.Environment.IsStaging();
});

builder.Services.AddSingleton<ApplicationErrorHandler>();
```

And how could we use the `ApplicationErrorHandler`? We inject it into the Controller and handle the errors 
explicitly. I think it's a very obvious implementation and easy to follow.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class TaskItemsController : ODataController
    {
        private readonly ILogger<TaskItemsController> _logger;
        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public TaskItemsController(ILogger<TaskItemsController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [HttpPut]
        [HttpPatch]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> PatchTaskItem([FromServices] ITaskItemService taskItemService, [FromODataUri] int key, [FromBody] Delta<TaskItem> delta, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                // Get the TaskItem with the current values:
                var taskItem = await taskItemService.GetTaskItemByIdAsync(key, User.GetUserId(), cancellationToken);

                // Patch the Values to it:
                delta.Patch(taskItem);

                // Update the Values:
                await taskItemService.UpdateTaskItemAsync(taskItem, User.GetUserId(), cancellationToken);

                return Updated(taskItem);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
    }
}
```

In the Business Logic, such as a the `TaskService` we can then throw the `ApplicationErrorException` implementations and 
we know, that it is handled for us and an `ODataError` is somehow returned to the client.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Services
{
    public class TaskItemService : ITaskItemService
    {
        private readonly ILogger<TaskItemService> _logger;

        private readonly ApplicationDbContext _applicationDbContext;
        private readonly IAclService _aclService;

        public TaskItemService(ILogger<TaskItemService> logger, ApplicationDbContext applicationDbContext, IAclService aclService)
        {
            _logger = logger;
            _applicationDbContext = applicationDbContext;
            _aclService = aclService;
        }
        
        // ...

        public async Task<TaskItem> UpdateTaskItemAsync(TaskItem TaskItem, int currentUserId, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            bool isAuthorized = await _aclService.CheckUserObjectAsync(currentUserId, TaskItem, Actions.CanWrite, cancellationToken);

            if (!isAuthorized)
            {
                throw new EntityUnauthorizedAccessException()
                {
                    EntityName = nameof(TaskItem),
                    EntityId = TaskItem.Id,
                    UserId = currentUserId,
                };
            }

            int rowsAffected = await _applicationDbContext.TaskItems
                .Where(t => t.Id == TaskItem.Id && t.RowVersion == TaskItem.RowVersion)
                .ExecuteUpdateAsync(setters => setters
                    // ...
                    .SetProperty(x => x.LastEditedBy, currentUserId), cancellationToken);

            if (rowsAffected == 0)
            {
                throw new EntityConcurrencyException()
                {
                    EntityName = nameof(TaskItem),
                    EntityId = TaskItem.Id,
                };
            }

            return TaskItem;
        }
        
        // ...
    }
}
```

### Configuring ASP.NET Core Middleware for the OData Error Response ###

In an ASP.NET Core application, there are many places things might go wrong. The Cookie Authentication wants to directly 
return a HTTP Status `401 (Unauthorized)` to the user, thus bypassing our Exceptions and Error Model. So there are certain 
extension points we might need to throw exceptions at.

For example in the `AuthenticationBuilder#AddCookie` extension method, we want to throw an `AuthenticationFailedException` 
for the `OnRedirectToLogin` event. You shouldn't care (maybe you should) where the exception is caught. At some point an 
Exception Handler catches it and converts it to our `ODataError` model accordingly:

```csharp
// Cookie Authentication
builder.Services
    .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        // ...
        options.Events.OnRedirectToLogin = (context) => throw new AuthenticationFailedException(); // Handle this in the middleware ...
    });
```

If we hit a Rate Limit for a user, we want to throw a `RateLimitException`. This Exception will then be turned into an 
`ODataError` with a HTTP Status Code `429 (TooManyRequests)`. It can be done like this:

```csharp
// Add the Rate Limiting
builder.Services.AddRateLimiter(options =>
{
    options.OnRejected = (ctx, cancellationToken) => throw new RateLimitException(); // Handle this in the middleware ...

    // ...
});
```

### Adding a Global Exception Handler for Uncaught Exceptions ###

We can define a Global Exception Handler by using the `WebApplication#UseExceptionHandler` extension method. This method basically 
catches everything that bubbled up all the way up. For OData we need to do some ASP.NET Core MVC `ActionContext` voodoo to make 
ASP.NET Core OData happy, but you should be able to adapt it to your needs:

```csharp
// We want all Exceptions to return an ODataError in the Response. So all Exceptions should be handled and run through
// this ExceptionHandler. This should only happen for things deep down in the ASP.NET Core stack, such as not resolving
// routes.
// 
// Anything else should run through the Controllers and the Error Handlers are going to work there.
//
app.UseExceptionHandler(options =>
{
    options.Run(async context =>
    {
        // Get the ExceptionHandlerFeature, so we get access to the original Exception
        var exceptionHandlerFeature = context.Features.GetRequiredFeature<IExceptionHandlerFeature>();
        
        // The ODataErrorHandler is required for adding an ODataError to all failed HTTP responses
        var odataErrorHandler = context.RequestServices.GetRequiredService<ApplicationErrorHandler>();

        // We can get the underlying Exception from the ExceptionHandlerFeature
        var exception = exceptionHandlerFeature.Error;

        // This isn't nice, because we probably shouldn't work with MVC types here. It would be better 
        // to rewrite the ApplicationErrorHandler to working with the HttpResponse.
        var actionContext = new ActionContext { HttpContext = context };

        var actionResult = odataErrorHandler.HandleException(context, exception);

        await actionResult
            .ExecuteResultAsync(actionContext)
            .ConfigureAwait(false);
    });
});
```

## Handling ASP.NET Core OData Errors in the Blazor Frontend ##

I think it's a waste of time to hand-write an Api SDK for an API. Again, we can do it somewhat like Microsoft.

The Microsoft Graph API is an OData API and it has thousands of endpoints. It's useful to understand how 
Microsoft themselves are generating their Microsoft Graph SDK. While it's literally impossible to know 
their exact stack, my best guess is, that it's the following two steps:

1. Convert the OData EDM Schema to an OpenAPI 3 Schema, using the `Microsoft.OpenApi.OData`.
2. Generate the Microsoft Graph SDK from the OpenAPI 3 Schema, using the Kiota CLI.

Kiota is available at:

* [https://aka.ms/kiota](https://aka.ms/kiota)

It's a command line tool for generating API Clients and is described as ...

> [...] a command line tool for generating an API client to call any OpenAPI-described API 
> you are interested in. The goal is to eliminate the need to take a dependency on a different 
> API SDK for every API that you need to call. Kiota API clients provide a strongly typed 
> experience with all the features you expect from a high quality API SDK, but without 
> having to learn a new library for every HTTP API.

What's relevant for us in this article is, that it automatically generates the `ODataError` model for us. In 
the generated files we can see our expected classes.


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

If you dig deep enough into the generated code, you will see, that it throws an Exception for failed 
HTTP Requests, such as a `401 (Unauthorized)`. It specifically throws an `ODataError` exception, which 
contains the `MainError` we want to inspect.

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

That also means: You should wrap all calls to the generated Kiota `ApiClient` inside a `try-catch` block. Blazor 
doesn't have a notion of a "Global Exception Handler", so bubbling up exceptions probably isn't useful. 

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

