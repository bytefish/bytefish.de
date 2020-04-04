title: Cookie Authentication in ASP.NET Core
date: 2020-04-04 09:59
tags: dotnet, netcore
category: dotnet
slug: asp_net_core_cookie_auth
author: Philipp Wagner
summary: Cookie Authentication with ASP.NET Core.

Setting up an ASP.NET Core 3 application with Cookie Authentication and CSRF Tokens turned 
out to be harder than expected. So I thought it's useful to share some code, if anyone else 
gets stuck with it.

## Startup Class ##

It all starts with the ``Startup`` class. In it we configure the Header Name to use for CSRF 
Antiforgery token, configure the Application Cookie to throw a HTTP Status 401 instead of 
doing a redirect, persist the Machine Key to disk and setup the Identity Provider.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using System.Threading.Tasks;
using TinyQuestionnaire.Database;
using TinyQuestionnaire.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using System;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using System.IO;

namespace TinyQuestionnaire.WebS
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        public void ConfigureServices(IServiceCollection services)
        {
            // Add CORS:
            services.AddCors(options =>
            {
                options.AddPolicy("CorsPolicy", policyBuilder =>
                {
                    policyBuilder
                        .WithOrigins("http://localhost:9000")
                        .SetIsOriginAllowedToAllowWildcardSubdomains()
                        .AllowAnyMethod()
                        .AllowAnyHeader()
                        .AllowCredentials();
                    ;
                });
            });

            // Use the Options Module:
            services.AddOptions();

            // Register Application Specific Services here ...
            RegisterApplicationServices(services);

            // Add Database:
            services.AddDbContext<ApplicationDbContext>(options =>
            {
                var connectionString = Configuration.GetConnectionString("DefaultConnection");
                
                options.UseSqlServer(connectionString);
            });

            // Add Anti-Forgery, use Angulars default Header Name, see Angulars XSRF implementation 
            // at: https://github.com/angular/angular/blob/f8096d499324cf0961f092944bbaedd05364eea1/packages/common/http/src/module.ts#L96
            //
            services.AddAntiforgery(options =>
            {
                options.HeaderName = "X-XSRF-TOKEN";
            });

            // Cookies:
            services
                 .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
                 .AddCookie(options =>
                 {
                     options.SlidingExpiration = true;

                     options.Events.OnRedirectToLogin = cxt =>
                     {
                         cxt.Response.StatusCode = 401;

                         return Task.CompletedTask;
                     };

                     options.Events.OnRedirectToAccessDenied = cxt =>
                     {
                         cxt.Response.StatusCode = 403;

                         return Task.CompletedTask;
                     };

                     options.Events.OnRedirectToLogout = cxt => Task.CompletedTask;
                 });

            // Add Identity:
            services
                .AddIdentity<ApplicationUser, IdentityRole>()
                .AddEntityFrameworkStores<ApplicationDbContext>();

            services.Configure<IdentityOptions>(options =>
             {
                 // User Settings:
                 options.User.RequireUniqueEmail = true;

                 // Lockout settings:
                 options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(30);
                 options.Lockout.MaxFailedAccessAttempts = 5;
                 options.Lockout.AllowedForNewUsers = true;
             });

            // Use a fixed Machine Key, so the Machine Key isn't regenerated for each restart:
            services.AddDataProtection()
                .SetApplicationName("questionnaire-application")
                .PersistKeysToFileSystem(new DirectoryInfo(@"D:\data"));

            // Use Web Controllers:
            services.AddControllers();

            // We need this for Antiforgery to work:
            services.AddMvc();

            // This needs to be configured, so MVC doesn't send us to HTTP 302 Redirects:
            services.ConfigureApplicationCookie(options =>
            {
                options.Events.OnRedirectToAccessDenied = ctx =>
                {
                    ctx.Response.StatusCode = 403;

                    return Task.CompletedTask;
                };

                options.Events.OnRedirectToLogout = ctx =>
                {
                    ctx.Response.StatusCode = 401;

                    return Task.CompletedTask;
                };

                options.Events.OnRedirectToLogin = ctx =>
                {
                    ctx.Response.StatusCode = 401;

                    return Task.CompletedTask;
                };
            });

            services.Configure<CookiePolicyOptions>(options =>
            {
                options.CheckConsentNeeded = context => false;
                options.MinimumSameSitePolicy = SameSiteMode.Lax;
            });
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
        {
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }

            app.UseCors("CorsPolicy");
            app.UseDefaultFiles();
            app.UseStaticFiles();
            app.UseAuthentication();
            app.UseRouting();
            app.UseAuthorization();
            app.UseEndpoints(endpoints =>
            {
                endpoints.MapControllerRoute(
                    name: "default",
                    pattern: "{controller=Home}/{action=Index}/{id?}");

                endpoints.MapFallbackToController("Index", "Home");
            });

        }

        private void RegisterApplicationServices(IServiceCollection services)
        {
            // Application Services go here ...
        }
    }
}
```

The ``ApplicationUser`` in the example basically is just the ``IdentityUser`` provided by ASP.NET Core.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Identity;

namespace TinyQuestionnaire.Models
{
    public class ApplicationUser : IdentityUser
    {
    }
}
```

And in the ``ApplicationDbContext`` we are also adding a Administrator user:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using System;
using TinyQuestionnaire.Models;

namespace TinyQuestionnaire.Database
{
    public class ApplicationDbContext : IdentityDbContext<ApplicationUser>
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            // The Password Hash is precalculated, so even if your code leaks, at least your "admin" 
            // password is a little more secure:
            builder
                .Entity<ApplicationUser>()
                .HasData(new ApplicationUser 
                {
                    Id = "a18be9c0-aa65-4af8-bd17-00bd9344e575",
                    UserName = "admin",
                    NormalizedUserName = "admin".ToUpper(),
                    Email = "my_email@bytefish.de",
                    NormalizedEmail = "my_email@bytefish.de".ToUpper(),
                    AccessFailedCount = 0,
                    EmailConfirmed = true,
                    LockoutEnabled = false,
                    PasswordHash = "AQAAAAEAACcQAAAAEBz0QR2SEkJYXvs1HmIzoVE39gQ43cWu456jOimDUoHsCur60yIIygBc/M+sxxEzFw==", // Equals "SuperSecurePassword" ...
                    SecurityStamp = Guid.NewGuid().ToString("D")
                });
        }   
    }
}
```

## Serving the SPA ##

There are a million ways to serve a SPA with ASP.NET Core. But we also have to secure the Login page with a CSRF token. So whenever I am serving 
the Angular SPA for an unauthenticated user I am also appending a CSRF Token to the ``HttpContext``, that is expected on the Server-side:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System.IO;

namespace TinyQuestionnaire.WebS.Controllers
{
    public class HomeController : Controller
    {
        private readonly IWebHostEnvironment environment;
        private readonly IAntiforgery antiforgery;

        public HomeController(IWebHostEnvironment environment, IAntiforgery antiforgery)
        {
            this.environment = environment;
            this.antiforgery = antiforgery;
        }

        [AllowAnonymous]
        public IActionResult Index()
        {
            // Whenever we serve the Angular application, we also serve the CSRF Tokens. There are a million ways to do this, 
            // I think it is best placed here... but I might be wrong anyway:
            if (!User.Identity.IsAuthenticated)
            {
                AppendCsrfToken();
            }

            return PhysicalFile(Path.Combine(environment.ContentRootPath, environment.WebRootPath, "index.html"), "text/html");
        }

        private void AppendCsrfToken()
        {
            var tokens = antiforgery.GetAndStoreTokens(Response.HttpContext);

            Response.Cookies.Append("XSRF-TOKEN", tokens.RequestToken, new CookieOptions() { HttpOnly = false });
        }
    }
}
```

## Authentication Controller ##

In the example we are using a password-based authentication. A user should also be able to set 
a "Remember Me" checkbox, so we are passing all information in the ``LoginDto``:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace TinyQuestionnaire.WebS.Contracts
{
    public class LoginDto
    {
        [JsonPropertyName("email")]
        public string Email { get; set; }

        [JsonPropertyName("password")]
        public string Password { get; set; }

        [JsonPropertyName("rememberMe")]
        public bool RememberMe { get; set; }
    }
}
```

The Authentication Cookie is HttpOnly on the Client-side, so there is no way to access it from JavaScript. So when 
a user is authenticating to the application we are also sending a ``UserDto``, that includes all the information a 
client application needs.

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Text.Json.Serialization;

namespace TinyQuestionnaire.WebS.Contracts
{
    public class UserDto
    {
        [JsonPropertyName("id")]
        public string Id { get; set; }
        
        [JsonPropertyName("username")]
        public string Username { get; set; }

        [JsonPropertyName("email")]
        public string Email { get; set; }

        [JsonPropertyName("role")]
        public string Role { get; set; }
        
    }
}
```

The ``AuthenticationController`` now provides the Endpoints to handle login and logout. 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;
using TinyQuestionnaire.Models;
using TinyQuestionnaire.WebS.Contracts;

namespace TinyQuestionnaire.WebS.Controllers
{
    [Route("api/auth")]
    public class AuthenticationController : Controller
    {
        private readonly UserManager<ApplicationUser> userManager;
        private readonly SignInManager<ApplicationUser> signInManager;
        private readonly IUserClaimsPrincipalFactory<ApplicationUser> principalFactory;
        private readonly IAntiforgery antiforgery;

        public AuthenticationController(UserManager<ApplicationUser> userManager, SignInManager<ApplicationUser> signInManager, IAntiforgery antiforgery, IUserClaimsPrincipalFactory<ApplicationUser> principalFactory)
        {
            this.signInManager = signInManager;
            this.userManager = userManager;
            this.antiforgery = antiforgery;
            this.principalFactory = principalFactory;
        }

        [AllowAnonymous]
        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginDto request)
        {
            if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
            {
                return BadRequest();
            }

            var user = await userManager.FindByEmailAsync(request.Email);

            if(user == null)
            {
                return BadRequest();
            }

            var result = await signInManager.PasswordSignInAsync(user.UserName, request.Password, isPersistent: request.RememberMe, lockoutOnFailure: true);

            if (result.Succeeded)
            {
                await UpdateCsrfTokensForUser(user);

                return Ok(new UserDto
                {
                    Id = user.Id,
                    Email = user.Email,
                    Username = user.UserName,
                    Role = "User"
                });
            }

            return Unauthorized();
        }

        [ValidateAntiForgeryToken]
        [HttpPost("logout")]
        public async Task<IActionResult> Logout()
        {
            await signInManager.SignOutAsync();

            return Ok();
        }

        private async Task UpdateCsrfTokensForUser(ApplicationUser user)
        {
            var principal = await principalFactory.CreateAsync(user);

            HttpContext.User = principal;

            var tokens = antiforgery.GetAndStoreTokens(Response.HttpContext);

            Response.Cookies.Append("XSRF-TOKEN", tokens.RequestToken, new CookieOptions() { HttpOnly = false });
        }
    }
}
```

## Conclusion ##

Now if you are using Angular sending the credentials is then as easy as setting ``withCredentials: true`` in the options for the ``HttpClient`` like this:

```typescript
const options = {
  withCredentials: true,
  headers: {'Content-Type': 'application/json'}
};

```

And here is how I used it in a component to make an authenticated request to a server endpoint:

```typescript
import { Component } from '@angular/core';
import { NgForm } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { environment } from 'src/environments/environment';
import { catchError, tap } from 'rxjs/operators';

@Component({
  selector: 'app-health-questionnaire',
  templateUrl: './health-questionnaire.component.html',
  styleUrls: ['./health-questionnaire.component.scss']
})
export class HealthQuestionnaireComponent {

  // ...

  onClick(form: NgForm): void {
    // Serialize the Questionnaire as JSON:
    const json = JSON.stringify(form.value);

    // Use the Cookie and send as Content-Type application/json:
    const options = {
      withCredentials: true,
      headers: {'Content-Type': 'application/json'}
    };

    // Now send the Results:
    this.httpClient
      .post(`${environment.apiUrl}/questionnaire/send`, json, options)
      .pipe(catchError((err, caught) => this.handleError(err, caught)))
      .subscribe(x => console.log("Sent successfully!"));
  }
  
  // ...
}
```

And that's it!