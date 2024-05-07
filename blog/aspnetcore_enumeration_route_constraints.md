title: Using Enumerations in ASP.NET Core Routes
date: 2024-05-07 12:12
tags: aspnet, aspnetcore, dotnet
category: dotnet
slug: aspnetcore_enumeration_route_constraints
author: Philipp Wagner
summary: This article shows how to use Enumerations in ASP.NET Core Routes.

[gitclub-dotnet]: https://github.com/bytefish/gitclub-dotnet

In [gitclub-dotnet] I wanted to use enumerations in routes. This can easily be 
done by implementing an `IRouteConstraint`. So let's do it!

All code can be found in a Git repository at:

* [https://github.com/bytefish/gitclub-dotnet](https://github.com/bytefish/gitclub-dotnet)

## Implementing the EnumRouteConstraint ##

We start by implementing a `IRouteConstraint`, which will be used for matching incoming routes.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace GitClub.Infrastructure.Mvc
{
    public class EnumRouteConstraint<TEnum> : IRouteConstraint
        where TEnum : struct
    {
        public bool Match(HttpContext? httpContext, IRouter? route, string routeKey, RouteValueDictionary values, RouteDirection routeDirection)
        {
            var matchingValue = values[routeKey]?.ToString();

            return Enum.TryParse(matchingValue, true, out TEnum _);
        }
    }
}
```

We then need to configure the `RouteOptions` for ASP.NET MVC like this:

```csharp
// Route Constraints
builder.Services.Configure<RouteOptions>(options =>
{
    options.ConstraintMap.Add("TeamRoleEnum", typeof(EnumRouteConstraint<TeamRoleEnum>));
    options.ConstraintMap.Add("OrganizationRoleEnum", typeof(EnumRouteConstraint<OrganizationRoleEnum>));
    options.ConstraintMap.Add("RepositoryRoleEnum", typeof(EnumRouteConstraint<RepositoryRoleEnum>));
});
```

## Using the EnumRouteConstraint ##

And we can then use the Route Constraint like this:

```csharp
﻿// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace GitClub.Controllers
{
    [Route("[controller]")]
    public class OrganizationsController : ControllerBase
    {
        // ...
        
        [HttpPut("{organizationId}/organization-roles/users/{userId}/{role:OrganizationRoleEnum}")]
        public async Task<IActionResult> AddUserOrganizationRole(
            [FromServices] OrganizationService organizationService,
            [FromServices] CurrentUser currentUser,
            [FromRoute(Name = "organizationId")] int organizationId,
            [FromRoute(Name = "userId")] int userId,
            [FromRoute(Name = "role")] OrganizationRoleEnum role,
            CancellationToken cancellationToken)
        {
            _logger.TraceMethodEntry();
            
            // ...        
        }
        
        // ...
    }
}
```

And that's it!