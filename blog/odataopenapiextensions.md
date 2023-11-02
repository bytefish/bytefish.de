title: Swagger UI for ASP.NET Core OData Services
date: 2023-11-01 12:17
tags: aspnetcore, dotnet, odata
category: dotnet
slug: odataopenapiextensions
author: Philipp Wagner
summary: This article shows how to add a Swagger Endpoint for ASP.NET Core OData Services.

If you are working on an ASP.NET Core OData application, you probably want to expose the OData Service using OpenAPI (Swagger). 

While ASP.NET Core OData comes with nothing built-in, an OpenAPI middleware was actually implemented at:

* [https://github.com/OData/AspNetCoreOData/tree/main/sample/ODataRoutingSample/OpenApi](https://github.com/OData/AspNetCoreOData/tree/main/sample/ODataRoutingSample/OpenApi)

I found myself copying the Middleware between many projects, so I think it may be useful to move it into a separate NuGet package and add it as a dependency. You can find the Git repository at:

* [https://github.com/bytefish/ODataOpenApiExtensions](https://github.com/bytefish/ODataOpenApiExtensions)

I have used it for my experiments and it builds a Swagger Page:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/odataopenapiextensions/swagger_endpoints.jpg">
        <img src="/static/images/blog/odataopenapiextensions/swagger_endpoints.jpg" alt="Final Swagger Endpoints">
    </a>
</div>

This work is based on the ASP.NET Core OData teams work and I don't take credit in it. 

## Installing ##

To install ODataOpenApiExtensions, run the following command in the Package Manager Console:

```
PM> Install-Package ODataOpenApiExtensions
```

## Basic Usage ##

The `ODataOpenApiMiddleware` can then be used like this:

```csharp
// ..

builder.Services.AddSwaggerGen();


// ...

var app = builder.Build();

// ...

if(app.Environment.IsDevelopment() || app.Environment.IsStaging())
{
    app.UseSwagger();
    app.UseODataOpenApi();
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("https://localhost:5000/odata/$openapi", "WideWorldImporters API");
    });
}

```

## License ##

```
AspNetCoreOData

Copyright (c) .NET Foundation and Contributors

Material in this repository is made available under the following terms:
  1. Code is licensed under the MIT license, reproduced below.
  2. Documentation is licensed under the Creative Commons Attribution 3.0 United States (Unported) License.
     The text of the license can be found here: http://creativecommons.org/licenses/by/3.0/legalcode

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, 
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is 
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial 
portions of the Software.

THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT 
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND 
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES 
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```