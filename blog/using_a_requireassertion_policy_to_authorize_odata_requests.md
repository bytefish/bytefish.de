title: Using a RequireAssertion Policy to Authorize OData Requests
date: 2025-01-18 19:13
tags: csharp, dotnet, odata
category: odata
slug: using_requireassertion_policy_to_authorize_odata_requests
author: Philipp Wagner
summary: Refactoring the ODataAuthorization library to use a RequireAssertion Policy.

`ODataAuthorization` is a library for implementing authorization on OData-enabled endpoints. It 
was originally written by Microsoft and I have ported it to ASP.NET Core OData a few years ago:

* [https://github.com/bytefish/ODataAuthorization](https://github.com/bytefish/ODataAuthorization)

## The Problem ##

When I've initially ported the library I wanted to change as little as possible. So the library 
is now a mix of `AuthorizationHandler`, `AuthorizationFilter`, `AuthorizationRequirement` and so 
on... 

It works *somehow*, but I don't understand the code. That's a problem, because I am the maintainer. 🫣

This needs to be fixed.

## The Solution ##

There must be a simpler way to integrate the OData Authorization into ASP.NET Core. So I've read through 
Microsofts documentation and saw a `RequireAssertion` method on an `AuthorizationPolicyBuilder`, which is 
described as:

> There may be situations in which fulfilling a policy is simple to express in code. It's possible to supply a 
> `Func<AuthorizationHandlerContext, bool>` when configuring a policy with the `RequireAssertion` policy 
> builder.

Now that... sounds about right?

## Implementing it ##

### Thinking about the Extension Methods ###

So what should the new ODataAuthorization API look like?

I think of something along the lines of this:

```csharp
var builder = WebApplication.CreateBuilder(args);

// ...

builder.Services.AddAuthorization(options =>
{
    options.AddODataAuthorizationPolicy();
});

// ...

var app = builder.Build();

// ...

app
    .MapControllers()
    .RequireODataAuthorization();
```

This means we will add an extension method on the `AuthorizationOptions` to add the `RequireAssertion` policy, 
and an extension method on the `IEndpointConventionBuilder` (which `MapControllers` returns) to require 
authorization on all OData-enabled endpoints.

### Implementing the Extension Methods ###

We start with a `static` class `ODataAuthorizationPolicies`, which is going to hold the `RequireAssertion` 
policy and the related extension methods. We start by adding two constants for the default policy name and 
the default scope name.

```csharp
public static class ODataAuthorizationPolicies
{
    public static class Constants
    {
        /// <summary>
        /// Gets the Default Policy Name.
        /// </summary>
        public const string DefaultPolicyName = "OData";

        /// <summary>
        /// Gets the Default Scope Claim Type.
        /// </summary>
        public const string DefaultScopeClaimType = "Scope";
    }
}
```

Next we add the `RequireODataAuthorization` extension to require endpoints authorizing OData requests.

```
public static class ODataAuthorizationPolicies
{
    // ...
        
    /// <summary>
    /// Require OData Authorization for all OData-enabled Endpoints. 
    /// </summary>
    /// <typeparam name="TBuilder">Type of the <see cref="IEndpointConventionBuilder"/></typeparam>
    /// <param name="builder">The <see cref="IEndpointConventionBuilder"/></param>
    /// <param name="policyName">The Policy name</param>
    /// <returns>A <typeparamref name="TBuilder"/> with OData authorization enabled</returns>
    public static TBuilder RequireODataAuthorization<TBuilder>(this TBuilder builder, string policyName = Constants.DefaultPolicyName)
        where TBuilder : IEndpointConventionBuilder
    {
        builder.RequireAuthorization(policyName);

        return builder;
    }

    
    // ...
}
```

And finally we'll add the `AuthorizationOptions#AddODataAuthorizationPolicy` extension method to add the `RequireAssertion` 
Policy. I was surprised to see how simple it is. I've left the `ODataModelPermissionsExtractor` out, because it's only 
partially interesting to the article.

```csharp
/// <summary>
/// Adds the OData Authorization Policy applied to all OData-enabled Endpoints.
/// </summary>
/// <param name="options"><see cref="AuthorizationOptions"> to be configured</param>
/// <param name="policyName">The Policy Name, which defaults to <see cref="Constants.DefaultPolicyName"/></param>
/// <param name="getUserScopes">Resolver for the User Scopes, uses <see cref="Constants.DefaultScopeClaimType"/>, if <see cref="null"/> is passed</param>
public static void AddODataAuthorizationPolicy(this AuthorizationOptions options, string policyName = Constants.DefaultPolicyName, Func<ClaimsPrincipal, IEnumerable<string>>? getUserScopes = null)
{
    // Set the Resolver for Permissions, if none was given
    if (getUserScopes == null)
    {
        getUserScopes = (user) => user
            .FindAll(Constants.DefaultScopeClaimType)
            .Select(claim => claim.Value);
    }

    options.AddPolicy(policyName, policyBuilder =>
    {
        policyBuilder.RequireAssertion((ctx) =>
        {
            var resource = ctx.Resource;

            // We can only work on a HttpContext or we are out
            if (resource is not HttpContext httpContext)
            {
                return false;
            }

            // Get all Scopes for the User
            var scopes = getUserScopes(httpContext.User);

            // Check Users Scopes against the OData Route
            bool isAccessAllowed = IsAccessAllowed(httpContext, scopes);

            return isAccessAllowed;
        });
    });
}

/// <summary>
/// Checks if the Access to the requested Resource is allowed based on the Scopes.
/// </summary>
/// <param name="httpContext">The <see cref="HttpContext"/> for the OData Route</param>
/// <param name="scopes">List of Scopes to check against the Model Permissions</param>
/// <returns></returns>
public static bool IsAccessAllowed(HttpContext httpContext, IEnumerable<string> scopes)
{
    // Get the OData Feature to access the parsed OData components
    var odataFeature = httpContext.ODataFeature();

    // We should ignore Non-OData Routes
    if (odataFeature == null || odataFeature.Path == null)
    {
        return true;
    }

    // Get the EDM Model associated with the Request
    IEdmModel model = httpContext.Request.GetModel();

    if (model == null)
    {
        return false;
    }

    // At this point in the Middleware the SelectExpandClause hasn't been evaluated yet (https://github.com/OData/WebApiAuthorization/issues/4),
    // but it's needed to provide securing the $expand-statements, so that you can't request expanded data without the required Scope Permissions.
    ParseSelectExpandClause(httpContext, model, odataFeature);

    // Extract the Required Permissions for the Request using the ODataModelPermissionsExtractor
    var permissions = ODataModelPermissionsExtractor.ExtractPermissionsForRequest(model, httpContext.Request.Method, odataFeature.Path, odataFeature.SelectExpandClause);

    // Finally evaluate the Scopes
    bool allowsScope = permissions.AllowsScopes(scopes);

    return allowsScope;
}
```

## Conclusion ##

And that's it! It's working great, and I am now way more confident with the code.