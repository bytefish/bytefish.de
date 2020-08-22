title: Enabling CORS for StaticFiles in ASP.NET Core  
date: 2020-08-22 10:37
tags: dotnet, aspnet
category: dotnet
slug: aspnetcore_static_files_cors
author: Philipp Wagner
summary: A note on CORS for the Static Files feature of ASP.NET Core.

ASP.NET Core is a great piece of technology and it's fun to develop with. At the moment I am working on 
a Tile Server in ASP.NET Core and I need to serve static files to a Vue.js application. The Vue.js 
development server is running on a different port. So what happens?

[Cross Origin Resource Sharing (CORS)]!

According to Microsoft CORS ...

* Is a W3C standard that allows a server to relax the same-origin policy.
* Is not a security feature, CORS relaxes security. An API is not safer by allowing CORS. For more information, see [How CORS works].
* Allows a server to explicitly allow some cross-origin requests while rejecting others.
* Is safer and more flexible than earlier techniques, such as JSONP.

ASP.NET Core provides a CORS Middleware, that handles all the dirty work of configuring and handling CORS, which can 
be easily added as a Service using the ``IServiceCollection#AddCors(...)`` extension and and integrated into the request 
``IApplicationBuilder#UseCors``.

## The Problem ##

But there is a little twist in ASP.NET Core. If you are using the Static Files feature with the ``IApplicationBuilder`` extension 
method ``UseStaticFiles(...)``, then no CORS strategy is applied. So while we are able to serve all requests to Controllers with 
CORS headers, all requests to static files from Vue.js with fail.

## The Solution ##

We can use the ``OnPrepareResponse`` to serve CORS headers, when configuring the Static Files Middleware. We are also injecting 
the ``ICorsService`` and ``ICorsPolicyProvider`` into the Statup ``Configure`` method. Then in the ``UseStaticFiles`` you can 
use the ``StaticFileOptions`` to add additional headers in the ``OnPrepareResponse`` method.

Here is the relevant snippet from the MapboxTileServer project.

```csharp
namespace MapboxTileServer
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // Add CORS:
            services.AddCors(options =>
            {
                options.AddPolicy("CorsPolicy", policyBuilder => policyBuilder
                        .WithOrigins("http://localhost:4200", "http://localhost:8080", "http://localhost:9000")
                        .SetIsOriginAllowedToAllowWildcardSubdomains()
                        .AllowAnyMethod()
                        .AllowAnyHeader()
                        .AllowCredentials());
            });
            
            // ...
        }
        
        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IWebHostEnvironment env, ICorsService corsService, ICorsPolicyProvider corsPolicyProvider)
        {

            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }

            app.UseCors("CorsPolicy");

            // To serve PBF Files, we need to allow unknown filetypes 
            // to be served by the Webserver:
            app.UseStaticFiles(new StaticFileOptions
            {
                ServeUnknownFileTypes = true,
                OnPrepareResponse = (ctx) =>
                {
                    var policy = corsPolicyProvider.GetPolicyAsync(ctx.Context, "CorsPolicy")
                        .ConfigureAwait(false)
                        .GetAwaiter().GetResult();

                    var corsResult = corsService.EvaluatePolicy(ctx.Context, policy);

                    corsService.ApplyResult(corsResult, ctx.Context.Response);
                }
            });
            
            // ...
        }
    }
}
```

[Cross Origin Resource Sharing (CORS)]: https://docs.microsoft.com/en-us/aspnet/core/security/cors?view=aspnetcore-3.1
[How CORS works]: https://docs.microsoft.com/en-us/aspnet/core/security/cors?view=aspnetcore-3.1#how-cors
[maputnik]: http://maputnik.github.io/
[OpenMapTiles]: https://openmaptiles.org/