title: Adding an AuthorizeFilter with a dynamic Policy to the ASP.NET Core MVC Pipeline
date: 2023-06-21 08:26
tags: aspnetcore, csharp, odata
category: csharp
slug: aspnet_core_adding_dynamic_filters
author: Philipp Wagner
summary: This article shows how to secure an ASP.NET Core OData API using the ODataAuthorization library.

[ODataAuthorization]: https://github.com/bytefish/ODataAuthorization/

In this article we will take a look at a bugfix for the [ODataAuthorization] library. I think 
it's worth sharing and making some code available, if someone comes here from Google.

## The Problem ##

There was recently a bug reported in the [ODataAuthorization] library, that made 
the Authorization failing for multiple requests:

* [https://github.com/bytefish/ODataAuthorization/issues/1](https://github.com/bytefish/ODataAuthorization/issues/1)

The [ODataAuthorization] library basically works like this... From an incoming 
`HttpRequest` the `IEdmModel` is resolved, then the permissions are resolved 
using an `ODataPath` (which is basically the parsed OData URL).

From these permissions an `AuthorizationPolicy` is built and put into an 
ASP.NET Core built-in `AuthorizeFilter`. This Filter has then been added 
to the controller like this:

```csharp
// Licensed under the MIT License.  See License.txt in the project root for license information.

// ...

namespace ODataAuthorization
{
    /// <summary>
    /// The OData authorization middleware
    /// </summary>
    public class ODataAuthorizationMiddleware
    {
        private static void ApplyRestrictions(IScopesEvaluator handler, HttpContext context)
        {
            var requirement = new ODataAuthorizationScopesRequirement(handler);

            var policy = new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser()
                .AddRequirements(requirement)
                .Build();

            // We use the AuthorizeFilter instead of relying on the built-in authorization middleware
            // because we cannot add new metadata to the endpoint in the middle of a request
            // and OData's current implementation of endpoint routing does not allow for
            // adding metadata to individual routes ahead of time
            var authFilter = new AuthorizeFilter(policy);

            var controllerActionDescriptor = context.GetEndpoint().Metadata.GetMetadata<ControllerActionDescriptor>();
            
            if(controllerActionDescriptor != null)
            {
                controllerActionDescriptor.FilterDescriptors?.Add(new FilterDescriptor(authFilter, 0));
            }
        }
    }
}
```

What the bug uncovered is, that a `Filter` is cached this way and only the cached 
filter is going to be used for all subsequent requests. I didn't find a way to 
invalidate the cache.

## The Solution ##

ASP.NET Core MVC comes with an `IFilterProvider`, which is ...

> A FilterItem provider. Implementations should update Results to make executable filters available.

So we basically shift the logic from the Middleware to an `IFilterProvider`, which 
allows us to dynamically provide a dynamically created `AuthorizeFilter`. By registering 
the `FilterItem` as not reusable, we can finally prevent it from being cached.

Here is the solution in its glory:


```csharp
// Licensed under the MIT License.  See License.txt in the project root for license information.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.Authorization;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.OData.Abstracts;
using Microsoft.AspNetCore.OData.Extensions;
using Microsoft.AspNetCore.OData.Query;
using Microsoft.OData.Edm;
using System;
using System.Linq;

namespace ODataAuthorization
{
    public class ODataAuthorizeFilterProvider : IFilterProvider
    {
        public int Order => 0;

        public void OnProvidersExecuted(FilterProviderContext context)
        {
            
        }

        public void OnProvidersExecuting(FilterProviderContext context)
        {
            // ...
            
            var permissions = model.ExtractPermissionsForRequest(httpContext.Request.Method, odataFeature.Path, odataFeature.SelectExpandClause);

            var requirement = new ODataAuthorizationScopesRequirement(permissions);

            var policy = new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser()
                .AddRequirements(requirement)
                .Build();

            var authFilter = new AuthorizeFilter(policy);

            var authFilterDescriptor = new FilterDescriptor(authFilter, FilterScope.Global);

            var authFilterItem = new FilterItem(authFilterDescriptor, authFilter)
            {
                IsReusable = false
            };

            context.Results.Add(authFilterItem);
        }
    }
}
```

And we need to add it to the Dependency Injection container:

```csharp
// ...

services.AddSingleton<IFilterProvider, ODataAuthorizeFilterProvider>();            
```