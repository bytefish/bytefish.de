title: ASP.NET Core OData 8 and Relationship-based Access Control 
date: 2023-10-25 22:49
tags: aspnetcore, dotnet, odata
category: dotnet
slug: aspnetcore_rebac_odata
author: Philipp Wagner
summary: This article shows a way to add Relationship-based Access Control to an ASP.NET Core OData application.

In my previous article we have seen how to implement Relationship-based Access Control with ASP.NET 
Core, EntityFramework Core and Microsoft SQL Server. At the end of the article we had a RESTful API, 
that supported and authorized CRUD operations on entities:

* [https://www.bytefish.de/blog/aspnetcore_rebac.html](https://www.bytefish.de/blog/aspnetcore_rebac.html)

In this article we will extend the Task Management Application to use ASP.NET Core OData, and see how 
to combine Relationship-based Access Control with an ASP.NET Core OData application.

All code in this article can be found at:

* [https://github.com/bytefish/ODataRebacExperiments](https://github.com/bytefish/ODataRebacExperiments)

## Table of contents ##

[TOC]

## The Problem ##

I think ASP.NET Core OData is a great technology. It has a good integration with ASP.NET Core and plays 
very well with EntityFramework Core. Just a few lines of code and boom... you have a CRUD API, that supports 
paging, sorting, filtering and even aggregations.

But how do you authorize access to the data? You don't want to open up your *entire database* for everyone 
to see. A Role-based approach, that I have previously experimented with, falls flat because it can restrict 
access to Entity Sets and Navigation Properties... but it isn't fine-grained enough to work per Entity.

So in real life, Role-based permissions for OData are not fine-grained enough and you need to come up with 
an idea to authorize access to the data. A `User` should be allowed to query for a list of *their* `UserTask` 
entities only.

And that's where Relationship-based Access Control comes in!

## What we are going to build ##

In the previous article an ASP.NET Core Backend for a Task Management Application has been developed. It basically 
consisted of a `User`, the `User` could be assigned to an `Organization` or a `Team`. `UserTask` entities can be 
assigned to `Users`, `Teams` or `Organizations`.

By using a `ListObjects API` we have been able to get the list of `Objects` a given `Subject` (for example a `User`) 
is related to. By using the `Check API` we have been able to check, if a `User` is authorized to access an `Object`. 

We are going to add a Swagger Page for testing the final API Endpoints:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnetcore_rebac_odata/swagger_endpoints.jpg">
        <img src="/static/images/blog/aspnetcore_rebac_odata/swagger_endpoints.jpg" alt="Final Swagger Endpoints">
    </a>
</div>

## ReBAC with ASP.NET Core OData 8 ##

We start by adding the NuGet Package `Microsoft.AspNetCore.OData` to our project:

```xml
<PackageReference Include="Microsoft.AspNetCore.OData" Version="8.2.3" />
```

### Adding the Entity Data Model (EDM) ###

It starts *Entity Data Model (EDM)*, which is ...

>  [...] the abstract data model that is used to describe the data exposed by an OData service. An OData Metadata Document 
> is a representation of a service's data model exposed for client consumption.

The `ApplicationEdmModel` is a static class, that returns the `IEdmModel` used by the ASP.NET Core OData framework. As 
of now it only contains the `UserTask`, the `UserTaskStatusEnum` and `UserTaskPriorityEnum`. If you want to expose 
`Organizations`, `Teams` and so on, you need to add them here. 

For Authentication we also add two Unbound Actions `SignInUser` and `SignOutUser` to the Entity Data Model.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Edm;
using Microsoft.OData.ModelBuilder;
using RebacExperiments.Server.Api.Models;

namespace RebacExperiments.Server.Api.Infrastructure.OData
{
    public static class ApplicationEdmModel
    {
        public static IEdmModel GetEdmModel()
        {
            var modelBuilder = new ODataConventionModelBuilder();

            modelBuilder.Namespace = "TaskManagementService";

            modelBuilder.EntitySet<UserTask>("UserTasks");
            
            modelBuilder.EnumType<UserTaskStatusEnum>();
            modelBuilder.EnumType<UserTaskPriorityEnum>();

            // Authentication
            RegisterSignInUserAction(modelBuilder);
            RegisterSignOutUserAction(modelBuilder);

            // Send as Lower Camel Case Properties, so the JSON looks better:
            modelBuilder.EnableLowerCamelCase();

            return modelBuilder.GetEdmModel();
        }

        private static void RegisterSignInUserAction(ODataConventionModelBuilder modelBuilder)
        {
            var signInUserAction = modelBuilder.Action("SignInUser");

            signInUserAction.HasDescription().HasDescription("SignInUser");

            signInUserAction.Parameter<string>("username").Required();
            signInUserAction.Parameter<string>("password").Required();
            signInUserAction.Parameter<bool>("rememberMe").Required();
        }

        private static void RegisterSignOutUserAction(ODataConventionModelBuilder modelBuilder)
        {
            var signOutUserAction = modelBuilder.Action("SignOutUser");

            signOutUserAction.HasDescription().HasDescription("SignOutUser");
        }
    }
}
```

### Enabling the OData Features for ASP.NET Core ###

We can then add the OData feature to the `Program.cs`, so that the requests sent are routed correctly using an `/odata` route prefix.

```csharp
// ...

builder.Services
    .AddControllers()
    // Register OData Routes:
    .AddOData((options) =>
    {
        options.AddRouteComponents(routePrefix: "odata", model: ApplicationEdmModel.GetEdmModel(), configureServices: svcs =>
        {
            svcs.AddSingleton<ODataBatchHandler>(new DefaultODataBatchHandler());
        });

        // Do not enable $expand
        options.Select().OrderBy().Filter().SetMaxTop(250).Count();
    });
```

Please note, that we are **not enabling**  the `$expand` feature explicitly. As of now ASP.NET Core OData 8 would query 
the expanded table without applying our authorization measures, that's for a later iteration. Keep it in mind.

### OData Error Handling ###

ASP.NET Core OData 8 comes with a set of `ActionResults`, that we can return to a user, such as a `UnauthorizedODataResult`, 
`NotFoundODataResult`, ... the ASP.NET Core OData framework uses these special results to add some metadata to them. The 
only `ActionResult`, that's missing for our application is a `ForbiddenODataResult`, so we add it as:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Infrastructure.OData
{
    /// <summary>
    /// Represents a result that when executed will produce a Unauthorized (401) response.
    /// </summary>
    /// <remarks>This result creates an <see cref="ODataError"/> with status code: 401.</remarks>
    public class ForbiddenODataResult : ForbidResult, IODataErrorResult
    {
        /// <summary>
        /// OData Error.
        /// </summary>
        public ODataError Error { get; }

        /// <summary>
        /// Initializes a new instance of the class.
        /// </summary>
        /// <param name="message">Error Message</param>
        public ForbiddenODataResult(string message)
        {
            if (message == null)
            {
                ArgumentNullException.ThrowIfNull("message");
            }

            Error = new ODataError
            {
                Message = message,
                ErrorCode = StatusCodes.Status403Forbidden.ToString()
            };
        }

        /// <summary>
        /// Initializes a new instance of the class.
        /// </summary>
        /// <param name="odataError">OData Error.</param>
        public ForbiddenODataResult(ODataError odataError)
        {
            Error = odataError;
        }

        /// <inheritdoc/>
        public async override Task ExecuteResultAsync(ActionContext context)
        {
            ObjectResult objectResult = new ObjectResult(Error)
            {
                StatusCode = StatusCodes.Status403Forbidden
            };

            await objectResult.ExecuteResultAsync(context).ConfigureAwait(false);
        }
    }
}
```

The previous article converted an `Exception` to a `ProblemDetails` DTO, which is a *RFC 7807*-conform 
representation of errors in HTTP APIs. But the OData specification comes with its own `ODataError`, so 
we add an `ApplicationErrorHandler` to convert an `Exception`to an `ODataError`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

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

        public ActionResult HandleInvalidModelState(HttpContext httpContext, ModelStateDictionary modelStateDictionary)
        {
            _logger.TraceMethodEntry();

            ODataError error = new ODataError()
            {
                ErrorCode = ErrorCodes.ValidationFailed,
                Message = "One or more validation errors occured",
                Details = GetODataErrorDetails(modelStateDictionary),

            };

            // If there was an exception, use this as ODataInnerError
            if (TryGetFirstException(modelStateDictionary, out var exception))
            {
                AddInnerError(httpContext, error, exception);
            }

            return new BadRequestObjectResult(error);
        }

        private bool TryGetFirstException(ModelStateDictionary modelStateDictionary, [NotNullWhen(true)] out Exception? e)
        {
            _logger.TraceMethodEntry();
        
            e = null;

            foreach (var modelStateEntry in modelStateDictionary)
            {
                foreach (var modelError in modelStateEntry.Value.Errors)
                {
                    if (modelError.Exception != null)
                    {
                        e = modelError.Exception;

                        return true;
                    }
                }
            }

            return false;
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

                    var odataErrorDetail = new ODataErrorDetail
                    {
                        ErrorCode = ErrorCodes.ValidationFailed,
                        Message = modelError.ErrorMessage,
                        Target = modelStateEntry.Key,
                    };

                    result.Add(odataErrorDetail);
                }
            }

            return result;
        }

        public ActionResult HandleException(HttpContext httpContext, Exception exception)
        {
            _logger.TraceMethodEntry();

            _logger.LogError(exception, "Call to '{RequestPath}' failed due to an Exception", httpContext.Request.Path);

            return exception switch
            {
                AuthenticationFailedException e => HandleAuthenticationException(httpContext, e),
                EntityConcurrencyException e => HandleEntityConcurrencyException(httpContext, e),
                EntityNotFoundException e => HandleEntityNotFoundException(httpContext, e),
                EntityUnauthorizedAccessException e => HandleEntityUnauthorizedException(httpContext, e),
                Exception e => HandleSystemException(httpContext, e)
            };
        }

        private ActionResult HandleAuthenticationException(HttpContext httpContext, AuthenticationFailedException e)
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

        private ActionResult HandleEntityConcurrencyException(HttpContext httpContext, EntityConcurrencyException e)
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

        private ActionResult HandleEntityNotFoundException(HttpContext httpContext, EntityNotFoundException e)
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

        private ActionResult HandleEntityUnauthorizedException(HttpContext httpContext, EntityUnauthorizedAccessException e)
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

        private ActionResult HandleSystemException(HttpContext httpContext, Exception e)
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

        private void AddInnerError(HttpContext httpContext, ODataError error, Exception e)
        {
            _logger.TraceMethodEntry();

            error.InnerError = new ODataInnerError();

            error.InnerError.Properties["trace-id"] = new ODataPrimitiveValue(httpContext.TraceIdentifier);

            if (_options.IncludeExceptionDetails)
            {
                error.InnerError.Message = e.Message;
                error.InnerError.StackTrace = e.StackTrace;
                error.InnerError.TypeName = e.GetType().Name;
            }
        }
    }
}
```

And in the `Program.cs` we are registering the error handler as:

```csharp
// ...

builder.Services.AddSingleton<ApplicationErrorHandler>();

// ...
```

We can see how to use the `ApplicationErrorHandler` in the `UserTask` controller. If you have 
read the previous article, you'll notice no differences in error handling compared to the Non-OData 
`Controller`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class UserTasksController : ODataController
    {
        private readonly ILogger<UserTasksController> _logger;
        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public UserTasksController(ILogger<UserTasksController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> GetUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromODataUri(Name = "key")] int key, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                var userTask = await userTaskService.GetUserTaskByIdAsync(context, key, User.GetUserId(), cancellationToken);

                return Ok(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
        
        // ...
    }
}
```

### OData Query Composition using ODataQueryOptions for UserTasks ###

ASP.NET Core OData 8 parses an incoming OData URI to `ODataQueryOptions`, that can be used to 
perform query composition. So in the `UserTaskService` we start by adding a `QueryUserTasks` 
method, that will return the `IQueryable` with the source data:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Services
{
    public class UserTaskService : IUserTaskService
    {
        private readonly ILogger<UserTaskService> _logger;

        public UserTaskService(ILogger<UserTaskService> logger)
        {
            _logger = logger;
        }

        // ...

        public IQueryable<UserTask> QueryUserTasks(ApplicationDbContext context, int currentUserId)
        {
            _logger.TraceMethodEntry();

            return context.ListUserObjects<UserTask>(currentUserId, new[] { Relations.Viewer, Relations.Owner });
        }
    }
}
```

And in the `UserTasksController` we can then use it like this:

```
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

//...

namespace RebacExperiments.Server.Api.Controllers
{
    public class UserTasksController : ODataController
    {
        private readonly ILogger<UserTasksController> _logger;
        private readonly ODataApplicationErrorHandler _applicationErrorHandler;

        public UserTasksController(ILogger<UserTasksController> logger, ODataApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }
        
        // ...
        
        [HttpGet]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public ActionResult GetUserTasks([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, ODataQueryOptions<UserTask> queryOptions, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                var queryable = userTaskService.QueryUserTasks(context, User.GetUserId());

                return Ok(queryOptions.ApplyTo(queryable));
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
        
        // ...
    }
}
```

## ODataControllers ##

### ODataController for Authentication ###

We need two Unboundend Actions `SignInUser` to sign-in a `User`, and `SignOutUser` to sign-out the `User`. It basically 
looks like the AuthenticationController from the previous article, only with the `CredentialsDto` removed and replacing 
it with `ODataActionParameters`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

//...

namespace RebacExperiments.Server.Api.Controllers
{
    public class AuthenticationController : ODataController
    {
        private readonly ILogger<AuthenticationController> _logger;

        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public AuthenticationController(ILogger<AuthenticationController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [HttpPost("odata/SignInUser")]
        public async Task<IActionResult> SignInUser([FromServices] ApplicationDbContext context, [FromServices] IUserService userService, [FromBody] ODataActionParameters parameters, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            string username = (string)parameters["username"];
            string password = (string)parameters["password"];
            bool rememberMe = (bool)parameters["rememberMe"];

            try
            {
                // Create ClaimsPrincipal from Database 
                var userClaims = await userService.GetClaimsAsync(
                    context: context,
                    username: username,
                    password: password,
                    cancellationToken: cancellationToken);

                // Create the ClaimsPrincipal
                var claimsIdentity = new ClaimsIdentity(userClaims, CookieAuthenticationDefaults.AuthenticationScheme);
                var claimsPrincipal = new ClaimsPrincipal(claimsIdentity);

                // It's a valid ClaimsPrincipal, sign in
                await HttpContext.SignInAsync(claimsPrincipal, new AuthenticationProperties { IsPersistent = rememberMe });

                return Ok();
            } 
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpPost("odata/SignOutUser")]
        public async Task<IActionResult> SignOutUser()
        {
            _logger.TraceMethodEntry();

            try
            {
                await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            } 
            catch(Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }

            return Ok();
        }
    }
}
```

### ODataController for UserTasks ###

We can then finish the `UserTasksController` to provide the CRUD methods.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Server.Api.Controllers
{
    public class UserTasksController : ODataController
    {
        private readonly ILogger<UserTasksController> _logger;
        private readonly ApplicationErrorHandler _applicationErrorHandler;

        public UserTasksController(ILogger<UserTasksController> logger, ApplicationErrorHandler applicationErrorHandler)
        {
            _logger = logger;
            _applicationErrorHandler = applicationErrorHandler;
        }

        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> GetUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromODataUri(Name = "key")] int key, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                var userTask = await userTaskService.GetUserTaskByIdAsync(context, key, User.GetUserId(), cancellationToken);

                return Ok(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpGet]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public ActionResult GetUserTasks([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, ODataQueryOptions<UserTask> queryOptions)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                var queryable = userTaskService.QueryUserTasks(context, User.GetUserId());

                return Ok(queryOptions.ApplyTo(queryable));
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpPost]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> PostUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromBody] UserTask userTask, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                await userTaskService.CreateUserTaskAsync(context, userTask, User.GetUserId(), cancellationToken);

                return Created(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        [HttpPut]
        [HttpPatch]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> PatchUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromODataUri] int key, [FromBody] Delta<UserTask> delta, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                // Get the UserTask with the current values:
                var userTask = await userTaskService.GetUserTaskByIdAsync(context, key, User.GetUserId(), cancellationToken);

                // Patch the Values to it:
                delta.Patch(userTask);

                // Update the Values:
                await userTaskService.UpdateUserTaskAsync(context, userTask, User.GetUserId(), cancellationToken);

                return Updated(userTask);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }

        
        [HttpDelete]
        [Authorize(Policy = Policies.RequireUserRole)]
        [EnableRateLimiting(Policies.PerUserRatelimit)]
        public async Task<IActionResult> DeleteUserTask([FromServices] ApplicationDbContext context, [FromServices] IUserTaskService userTaskService, [FromODataUri(Name = "key")] int key, CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();

            if (!ModelState.IsValid)
            {
                return _applicationErrorHandler.HandleInvalidModelState(HttpContext, ModelState);
            }

            try
            {
                await userTaskService.DeleteUserTaskAsync(context, key, User.GetUserId(), cancellationToken);

                return StatusCode(StatusCodes.Status204NoContent);
            }
            catch (Exception ex)
            {
                return _applicationErrorHandler.HandleException(HttpContext, ex);
            }
        }
    }
}
```

And believe it or not... that's it basically!

## OData API Example using a .http File ##

We got everything in place. We can now start the application and use Swagger to query it. But Visual Studio 2022 
now comes with the "Endpoints Explorer" to execute HTTP Requests against HTTP endpoints. Though it's not fully-fledged 
yet, I think it'll improve with time and it already covers a lot of use cases.

You can find the Endpoints Explorer at:

* `View -> Other Windows -> Endpoints Explorer`

By clicking on `RebacExperiments.Server.Api.http` the HTTP script with the sample requests comes up.

### The Example Setup ###

We have got 2 Tasks:

* `task_152`: "Sign Document"
* `task 323`: "Call Back Philipp Wagner"

And we have got two users: 

* `user_philipp`: "Philipp Wagner"
* `user_max`: "Max Mustermann"

Both users are permitted to login, so they are allowed to query for data, given a permitted role and permissions.

There are two Organizations:

* Organization 1: "Organization #1"
* Organization 2: "Organization #2"

And 2 Roles:

* `role_user`: "User" (Allowed to Query for UserTasks)
* `role_admin`: "Administrator" (Allowed to Delete a UserTask)

The Relationships between the entities are the following:

```
The Relationship-Table is given below.

ObjectKey           |  ObjectNamespace  |   ObjectRelation  |   SubjectKey          |   SubjectNamespace    |   SubjectRelation
--------------------|-------------------|-------------------|-----------------------|-----------------------|-------------------
:task_323  :        |   UserTask        |       viewer      |   :organization_1:    |       Organization    |   member
:task_152  :        |   UserTask        |       viewer      |   :organization_1:    |       Organization    |   member
:task_152  :        |   UserTask        |       viewer      |   :organization_2:    |       Organization    |   member
:organization_1:    |   Organization    |       member      |   :user_philipp:      |       User            |   NULL
:organization_2:    |   Organization    |       member      |   :user_max:          |       User            |   NULL
:role_user:         |   Role            |       member      |   :user_philipp:      |       User            |   NULL
:role_admin:        |   Role            |       member      |   :user_philipp:      |       User            |   NULL
:role_user:         |   Role            |       member      |   :user_max:          |       User            |   NULL
:task_323:          |   UserTask        |       owner       |   :user_2:            |       User            |   member
```

We can draw the following conclusions here: A `member` of `organization_1` is `viewer` of `task_152` and `task_323`. A `member` 
of `organization_2` is a `viewer` of `task_152` only. `user_philipp` is member of `organization_1`, so the user is able to see 
both tasks as `viewer`. `user_max` is member of `organization_2`, so he is a `viewer` of `task_152` only. `user_philipp` has the 
`User` and `Administrator` roles assigned, so he can create, query and delete a `UserTask`. `user_max` only has the `User` role 
assigned, so he is not authorized to delete a `UserTask`. Finally `user_philipp` is also the `owner` of `task_323` so he is 
permitted to update the data of the `UserTask`.

### HTTP Endpoints Explorer Script ###

We start by defining the Host Address:

```
@RebacExperiments.Server.Api_HostAddress = https://localhost:5000/odata
```

Then we signin `philipp@bytefish.de` using the `SignInUser` Action:

```
### Sign In "philipp@bytefish.de"

POST {{RebacExperiments.Server.Api_HostAddress}}/SignInUser
Content-Type: application/json

{
  "username": "philipp@bytefish.de",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

And then we get all `UserTask` entities for the current user:

```
### Get all UserTasks for "philipp@bytefish.de"

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
```

The response is going to contain two entities:

```json
{
  "@odata.context": "https://localhost:5000/odata/$metadata#UserTasks",
  "value": [
    {
      "title": "Call Back",
      "description": "Call Back Philipp Wagner",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Low",
      "userTaskStatus": "NotStarted",
      "id": 152,
      "rowVersion": "AAAAAAAAB\u002Bw=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    },
    {
      "title": "Sign Document",
      "description": "You need to Sign a Document",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Normal",
      "userTaskStatus": "InProgress",
      "id": 323,
      "rowVersion": "AAAAAAAAB\u002B0=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    }
  ]
}
```

We can then introduce some OData Goodies and say we want only `1` entity, the results should be 
ordered by the `id` property and the response should contain the total number of entities the user 
is authorized to acces.

```
### Get the first task and return the total count of Entities visible to "philipp@bytefish.de"

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks?$top=1&$orderby=id&$count=true
```

The result is going to contain the `@odata.count` property and have `1` task only.

```
{
  "@odata.context": "https://localhost:5000/odata/$metadata#UserTasks",
  "@odata.count": 2,
  "value": [
    {
      "title": "Call Back",
      "description": "Call Back Philipp Wagner",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Low",
      "userTaskStatus": "NotStarted",
      "id": 152,
      "rowVersion": "AAAAAAAAB\u002Bw=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    }
  ]
}
```

We can then sign in as `max@mustermann.local`.

```
### Sign In as "max@mustermann.local"

POST {{RebacExperiments.Server.Api_HostAddress}}/SignInUser
Content-Type: application/json

{
  "username": "max@mustermann.local",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

If you try to get all `UserTask` entities of `max@mustermann.local`:

```
### Get all UserTasks for "max@mustermann.local"

GET {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
```

There will be `1` task only.

```json
{
  "@odata.context": "https://localhost:5000/odata/$metadata#UserTasks",
  "value": [
    {
      "title": "Call Back",
      "description": "Call Back Philipp Wagner",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Low",
      "userTaskStatus": "NotStarted",
      "id": 152,
      "rowVersion": "AAAAAAAAB\u002Bw=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    }
  ]
}
```

Now we'll create a new `UserTask` "API HTTP File Example":

```
### Create a new UserTask "API HTTP File Example" as "max@mustermann.local"

POST {{RebacExperiments.Server.Api_HostAddress}}/UserTasks
Content-Type: application/json

{
    "title": "API HTTP File Example",
    "description": "API HTTP File Example",
    "dueDateTime": null,
    "reminderDateTime": null,
    "completedDateTime": null,
    "assignedTo": null,
    "userTaskPriority": "Normal",
    "userTaskStatus": "NotStarted"
}
```

And we can see, that `max@mustermann.local` now sees both `UserTask` entities:

```json
{
  "@odata.context": "https://localhost:5000/odata/$metadata#UserTasks",
  "value": [
    {
      "title": "Call Back",
      "description": "Call Back Philipp Wagner",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Low",
      "userTaskStatus": "NotStarted",
      "id": 152,
      "rowVersion": "AAAAAAAAB\u002Bw=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    },
    {
      "title": "API HTTP File Example",
      "description": "API HTTP File Example",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Normal",
      "userTaskStatus": "NotStarted",
      "id": 38191,
      "rowVersion": "AAAAAAAACAY=",
      "lastEditedBy": 7,
      "validFrom": "2023-10-25T19:58:44.8007138\u002B02:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    }
  ]
}
```

If we sign in as `philipp@bytefish.de` again:

```
### Sign In "philipp@bytefish.de"

POST {{RebacExperiments.Server.Api_HostAddress}}/SignInUser
Content-Type: application/json

{
  "username": "philipp@bytefish.de",
  "password": "5!F25GbKwU3P",
  "rememberMe": true
}
```

We can see with a call to `/UserTasks`, that he doesn't see the new `UserTask` at all.

```json
{
  "@odata.context": "https://localhost:5000/odata/$metadata#UserTasks",
  "value": [
    {
      "title": "Call Back",
      "description": "Call Back Philipp Wagner",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Low",
      "userTaskStatus": "NotStarted",
      "id": 152,
      "rowVersion": "AAAAAAAAB\u002Bw=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    },
    {
      "title": "Sign Document",
      "description": "You need to Sign a Document",
      "dueDateTime": null,
      "reminderDateTime": null,
      "completedDateTime": null,
      "assignedTo": null,
      "userTaskPriority": "Normal",
      "userTaskStatus": "InProgress",
      "id": 323,
      "rowVersion": "AAAAAAAAB\u002B0=",
      "lastEditedBy": 1,
      "validFrom": "2013-01-01T00:00:00\u002B01:00",
      "validTo": "9999-12-31T23:59:59.9999999\u002B01:00"
    }
  ]
}
```

## Conclusion ##

That's it! We have successfully authorized the access to Entity Sets using a Relationship-based Access Control model. The Git Repository 
contains much more goodies and food for thought. The Project also comes with an OpenAPI integration so you can use the Swagger UI for 
testing.

