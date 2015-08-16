title: File Uploads with Nancy
date: 2015-08-16 14:00
tags: c#, nancy
category: c#
slug: file_upload_nancy
author: Philipp Wagner
summary: This article describes how to do file uploads with Nancy, a framework for HTTP based services on .NET and Mono.

[Nancy]: https://github.com/NancyFx/Nancy
[HTML5 reference]: http://www.w3.org/TR/html5/forms.html#multipart/form-data-encoding-algorithm
[module]: https://github.com/NancyFx/Nancy/wiki/Exploring-the-nancy-module

This post shows how to implement file uploads with [Nancy], which is "... a lightweight, low-ceremony, framework for building HTTP based services on .Net and Mono".

The file upload will be sent as a HTTP POST request with ``multipart/form-data`` ([HTML5 reference]) content. A request should also include some metadata like a title, description and tags.

## Application Settings ##

So where to start the example? 

First of all we define an interface to obtain application-wide settings. It only holds the upload directory in this example, but you could easily imagine additional settings for a sophisticated application.

```csharp
namespace FileUploadSample.Infrastructure.Settings
{
    public interface IApplicationSettings
    {
        string FileUploadDirectory { get; }
    }
}
```

In this example we can safely hardcode the settings. You should load the configuration from a database or external configuration in a real project.

```csharp
namespace FileUploadSample.Infrastructure.Settings
{
    /// <summary>
    /// Should not be hardcoded in reality.
    /// </summary>
    public class ApplicationSettings : IApplicationSettings
    {
        public string FileUploadDirectory
        {
            get { return "uploads"; }
        }
    }
}
```

## Upload Handler ##

You could easily write a large [module](https://github.com/NancyFx/Nancy/wiki/Exploring-the-nancy-module) to handle a file upload, but let's break everything down into useful parts.

The result of a file upload is an identifier. We don't use the given filename, so we don't override existing files.

```csharp
namespace FileUploadSample.Infrastructure.Upload
{
    public class FileUploadResult
    {
        public string Identifier { get; set; }
    }
}
```

Then we can define an interface for an upload handler. Uploading a file may perform some IO, so let's make it an asynchronous method.

```csharp
using System.IO;
using System.Threading.Tasks;

namespace FileUploadSample.Infrastructure.Upload
{
    public interface IFileUploadHandler
    {
        Task<FileUploadResult> HandleUpload(string fileName, Stream stream);
    }
}
```

In this example we only want to store to the local file system, you could imagine implementing a handler for different data sinks. The [IRootPathProvider](https://github.com/NancyFx/Nancy/blob/master/src/Nancy/IRootPathProvider.cs) is provided and registered by the Nancy Framework.

```csharp
using FileUploadSample.Infrastructure.Settings;
using Nancy;
using System;
using System.IO;
using System.Threading.Tasks;

namespace FileUploadSample.Infrastructure.Upload
{
    public class LocalStorageHandler : IFileUploadHandler
    {
        private readonly IApplicationSettings applicationSettings;
        private readonly IRootPathProvider rootPathProvider;

        public LocalStorageHandler(IApplicationSettings applicationSettings, IRootPathProvider rootPathProvider)
        {
            this.applicationSettings = applicationSettings;
            this.rootPathProvider = rootPathProvider;
        }

        public async Task<FileUploadResult> HandleUpload(string fileName, System.IO.Stream stream)
        {
            string uuid = GetFileName();
            string targetFile = GetTargetFile(uuid);

            using (FileStream destinationStream = File.Create(targetFile))
            {
                await stream.CopyToAsync(destinationStream);
            }

            return new FileUploadResult()
            {
                Identifier = uuid
            };
        }

        private string GetTargetFile(string fileName)
        {
            return Path.Combine(GetUploadDirectory(), fileName);
        }

        private string GetFileName()
        {
            return Guid.NewGuid().ToString();
        }

        private string GetUploadDirectory()
        {
            var uploadDirectory = Path.Combine(rootPathProvider.GetRootPath(), applicationSettings.FileUploadDirectory);

            if (!Directory.Exists(uploadDirectory))
            {
                Directory.CreateDirectory(uploadDirectory);
            }

            return uploadDirectory;
        }
    }
}
```

## Request ##

Working with the incoming data directly is totally fine for small projects, but for anything more complex you really want to model your incoming data as request objects.

```csharp
using Nancy;
using System.Collections.Generic;

namespace FileUploadSample.Requests
{
    public class FileUploadRequest
    {
        public string Title { get; set; }

        public string Description { get; set; }

        public IList<string> Tags { get; set; }

        public HttpFile File { get; set; }
    }
}
```

### Binding ###

So how to populate the request object for an incoming HTTP request? The automatic binding won't work here, but we can write a custom [IModelBinder](https://github.com/NancyFx/Nancy/blob/master/src/Nancy/ModelBinding/IModelBinder.cs) to bind the incoming data. 

For more details you should ready the Nancy wiki on [ModelBinding](https://github.com/NancyFx/Nancy/wiki/Model-binding).

```csharp
using System;
using System.Linq;
using System.Collections.Generic;
using Nancy;
using Nancy.ModelBinding;

namespace FileUploadSample.Requests.Binding
{
    /// <summary>
    /// Do not pollute the Module. Use a custom Model Binder to extract the binding part.
    /// </summary>
    public class FileUploadRequestBinder : IModelBinder
    {
        public object Bind(NancyContext context, Type modelType, object instance, BindingConfig configuration, params string[] blackList)
        {
            var fileUploadRequest = (instance as FileUploadRequest) ?? new FileUploadRequest();

            var form = context.Request.Form;

            fileUploadRequest.Tags = GetTags(form["tags"]);
            fileUploadRequest.Title = form["title"];
            fileUploadRequest.Description = form["description"];
            fileUploadRequest.File = GetFileByKey(context, "file");

            return fileUploadRequest;
        }

        private IList<string> GetTags(dynamic field)
        {
            try
            {
                var tags = (string)field;
                return tags.Split(new[] { "," }, StringSplitOptions.RemoveEmptyEntries);
            }
            catch
            {
                return new List<string>();
            }
        }

        private HttpFile GetFileByKey(NancyContext context, string key)
        {
            IEnumerable<HttpFile> files = context.Request.Files;
            if (files != null)
            {
                return files.FirstOrDefault(x => x.Key == key);
            }
            return null;
        }

        public bool CanBind(Type modelType)
        {
            return modelType == typeof(FileUploadRequest);
        }
    }
}
```

## Response ##

Any outgoing data should also be modeled as a response object . For now the upload response simply holds the file identifier.

```csharp
namespace FileUploadSample.Responses
{
    public class FileUploadResponse
    {
        public string Identifier { get; set; }
    }
}
```

## FileUploadModule ##

Now we can write a [NancyModule](https://github.com/NancyFx/Nancy/wiki/Exploring-the-nancy-module) to tie everything together. 

The upload handler is injected into the module by the dependency injection container. The model binder will resolve to the custom model binder automatically.

```csharp
using FileUploadSample.Infrastructure.Upload;
using FileUploadSample.Requests;
using FileUploadSample.Responses;
using Nancy;
using Nancy.ModelBinding;

namespace FileUploadSample.Modules
{
    public class FileUploadModule : NancyModule
    {
        private readonly IFileUploadHandler fileUploadHandler;

        public FileUploadModule(IFileUploadHandler fileUploadHandler)
            : base("/file")
        {
            this.fileUploadHandler = fileUploadHandler;

            Post["/upload", true] = async (x, ct) =>
            {
                var request = this.Bind<FileUploadRequest>();
                
                var uploadResult = await fileUploadHandler.HandleUpload(request.File.Name, request.File.Value);

                var response = new FileUploadResponse() { Identifier = uploadResult.Identifier };

                return Negotiate
                    .WithStatusCode(HttpStatusCode.OK)
                    .WithModel(response);
            };
        }
    }
}
```

## Nancy Bootstrapper ##

We are done! There is only one implementation for each interface, so the TinyIoC container will [automatically register](https://github.com/NancyFx/Nancy/wiki/Bootstrapper#using-autoregister) the implementations.

So the Bootstrapper doesn't need to be modified at all.

```csharp
using Nancy;

namespace FileUploadSample
{
    public class Bootstrapper : DefaultNancyBootstrapper
    {
	
    }
}
```

## Uploading a file with curl ##

[cURL](http://curl.haxx.se/) is a great tool for transferring data with URL syntax. So let's make a HTTP POST to the module!

```
curl --verbose 
  --form title="File Title"
  --form description="File Description"
  --form tags="Tag1,Tag2"
  --form file=@"C:\Users\philipp\image.png"
  http://localhost:8080/file/upload
```

And we should get a ``HTTP 200`` status code the response, which means everything went fine.

```
* Connected to localhost (::1) port 12008 (#0)
> POST /file/upload HTTP/1.1
> User-Agent: curl/7.36.0
> Host: localhost:12008
> Accept: */*
> Content-Length: 3524301
> Expect: 100-continue
> Content-Type: multipart/form-data; boundary=------------------------92208bd1dbc8e77e
>
< HTTP/1.1 100 Continue
< HTTP/1.1 200 OK
< Cache-Control: private
< Content-Type: application/json; charset=utf-8
< Vary: Accept
* Server Microsoft-IIS/10.0 is not blacklisted
< Server: Microsoft-IIS/10.0
< Link: </upload.xml>; rel="application/xml"
< X-AspNet-Version: 4.0.30319
< X-Powered-By: ASP.NET
< Date: Sun, 16 Aug 2015 11:44:26 GMT
< Content-Length: 53
<

{"Identifier":"fbe0f047-7c4e-44af-b269-f7631de795d1"}
```

## Conclusion ##

I really like how the model binding works in [Nancy], how the async support is integrated and the very clean approach to dependency injection.