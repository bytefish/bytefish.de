title: Consistent Error Handling with Nancy
date: 2015-04-19 13:48
tags: csharp, nancy
category: csharp
slug: consistent_error_handling_with_nancy
author: Philipp Wagner

[NancyFx]: https://github.com/NancyFx/
[Nancy]: https://github.com/NancyFx/
[application pipelines]: https://github.com/NancyFx/Nancy/wiki/The-Application-Before,-After-and-OnError-pipelines

I am developing a RESTful Web service with [NancyFx] and it has been a pleasant experience so far. The [Nancy] framework is described 
as "... a lightweight, low-ceremony, framework for building HTTP based services on .Net and Mono". It comes with a great documentation 
and it's really fun to work with.

In this post I'll show you how to do consistent error handling with [Nancy]. A consistent approach to error handling is an important part 
of every sucessful RESTful Web service. You really don't want to return an exception to the client, because it will confuse users and even 
worse might leak implementation details.

You will learn how to extend [Nancy], so that all your exceptions are converted into JSON/XML errors:

```json
{
	"code":30,
	"details":"Invalid API Token."
}
```

You can find the full source code example in my git repository at:

* [https://github.com/bytefish/NancySamples/tree/master/ErrorHandling](https://github.com/bytefish/NancySamples/tree/master/ErrorHandling)

## Error Model ##

First of all the error model has to be defined. It's a RESTful API, so each error should also come with a useful Http Status Code.

The available error codes are given in the ``ServiceErrorCode`` enum.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public enum ServiceErrorCode
    {
        GeneralError = 0,
        NotFound = 10,
        InternalServerError = 20,
        InvalidToken = 30,
    }
}
```

Next we'll define the ``ServiceErrorModel`` class which contains the error code and details.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public class ServiceErrorModel
    {
        public ServiceErrorCode Code { get; set; }

        public string Details { get; set; }
    }
}
```

And finally we'll wrap the ``ServiceErrorModel`` in a ``HttpServiceError``, which simply adds the HTTP Status to the error.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public class HttpServiceError
    {
        public ServiceErrorModel ServiceErrorModel { get; set; }

        public HttpStatusCode HttpStatusCode { get; set; }
    }
} 
```

Now everything is in place to define the errors!

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public static class HttpServiceErrorDefinition
    {
        public static HttpServiceError NotFoundError = new HttpServiceError
        {
            HttpStatusCode = HttpStatusCode.NotFound,
            ServiceErrorModel = new ServiceErrorModel
            {
                Code = ServiceErrorCode.NotFound,
                Details = "The requested entity was not found."
            }
        };

        public static HttpServiceError GeneralError = new HttpServiceError
        {
            HttpStatusCode = HttpStatusCode.BadRequest,
            ServiceErrorModel = new ServiceErrorModel
            {
                Code = ServiceErrorCode.GeneralError,
                Details = "An error occured during processing the request."
            }
        };

        public static HttpServiceError InternalServerError = new HttpServiceError
        {
            HttpStatusCode = HttpStatusCode.InternalServerError,
            ServiceErrorModel = new ServiceErrorModel
            {
                Code = ServiceErrorCode.InternalServerError,
                Details = "There was an internal server error during processing the request."
            }
        };

        public static HttpServiceError InvalidTokenError = new HttpServiceError
        {
            HttpStatusCode = HttpStatusCode.BadRequest,
            ServiceErrorModel = new ServiceErrorModel
            {
                Code = ServiceErrorCode.InvalidToken,
                Details = "Invalid API Token."
            }
        };
    }
}
```

## Exceptions ##

In the previous chapter we have designed a basic error model and defined the available errors. So where do we use these errors?  

The idea is simple: We'll first define an interface ``IHasHttpServiceError``, which ensures a ``HttpServiceError`` is available and 
then implement the interface for a custom exception. And then anyone who catches the exception can inspect it for the error. That 
will be useful.

First of all the interface.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public interface IHasHttpServiceError
    {
        HttpServiceError HttpServiceError { get; }
    }
}
```

Next we'll just derive from a ``System.Exception`` and implement the ``IHasHttpServiceError`` interface. You can find more exceptions in the GitHub 
project, so you probably want to take a look at the other exceptions too. All exception follow the same pattern as used for the 
``GeneralServiceErrorException``.

```csharp
namespace RestSample.Server.Infrastructure.Exceptions
{
    public class GeneralServiceErrorException : Exception, IHasHttpServiceError
    {
        public GeneralServiceErrorException()
            : base() { }

        public GeneralServiceErrorException(string message)
            : base(message) { }

        public GeneralServiceErrorException(string message, Exception innerException)
            : base(message, innerException) { }

        public HttpServiceError HttpServiceError { get { return HttpServiceErrorDefinition.GeneralError; } }
    }
}
```

We can now throw this exception at any point in our code and extract the ``HttpServiceError`` from it. If an exception doesn't implement the ``IHasHttpServiceError`` 
interface, we should still return a service error. Let's write a simple method to do that.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public static class HttpServiceErrorUtilities
    {
        public static HttpServiceError ExtractFromException(Exception exception, HttpServiceError defaultValue)
        {
            HttpServiceError result = defaultValue;

            if (exception != null)
            {
                IHasHttpServiceError exceptionWithServiceError = exception as IHasHttpServiceError;

                if (exceptionWithServiceError != null)
                {
                    result = exceptionWithServiceError.HttpServiceError;
                }
            }

            return result;
        }
    }
}
```

### A Custom Error Handler for the OnError Pipeline ###

So how can we use all this with [Nancy]? The idea is simple: We'll hook a custom error handler into the [application pipelines] and intercept all errors. The [Nancy] documentation states:

> The OnError interceptor enables you to execute code whenever an exception occurs in any of the routes that are being invoked. It gives you access to the NancyContext and the exception that took place.

So whenever an exception is thrown we'll intercept the error and:

1. Extract the ``HttpServiceError`` from the Exception (with the ``ExtractFromException`` defined above).
2. Negotiate the Response and set the ``ServiceErrorModel`` and HTTP Status code.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public static class CustomErrorHandler
    {
        private static readonly ILog log = LogManager.GetLogger(MethodBase.GetCurrentMethod().DeclaringType);

        public static void Enable(IPipelines pipelines, IResponseNegotiator responseNegotiator)
        {
            if (pipelines == null)
            {
                throw new ArgumentNullException("pipelines");
            }

            if (responseNegotiator == null)
            {
                throw new ArgumentNullException("responseNegotiator");
            }

            pipelines.OnError += (context, exception) => HandleException(context, exception, responseNegotiator);
        }

        private static void LogException(NancyContext context, Exception exception)
        {
            if (log.IsErrorEnabled)
            {
                log.ErrorFormat("An exception occured during processing a request. (Exception={0}).", exception);
            }
        }

        private static Response HandleException(NancyContext context, Exception exception, IResponseNegotiator responseNegotiator)
        {
            LogException(context, exception);

            return CreateNegotiatedResponse(context, responseNegotiator, exception);
        }

        private static Response CreateNegotiatedResponse(NancyContext context, IResponseNegotiator responseNegotiator, Exception exception)
        {
            HttpServiceError httpServiceError = HttpServiceErrorUtilities.ExtractFromException(exception, HttpServiceErrorDefinition.GeneralError);

            Negotiator negotiator = new Negotiator(context)
                .WithStatusCode(httpServiceError.HttpStatusCode)
                .WithModel(httpServiceError.ServiceErrorModel);

            return responseNegotiator.NegotiateResponse(negotiator, context);
        }
    }
}
```

### Implementing StatusCodeHandlers ###

Nancy is very safe by default and implements various ``IStatusCodeHandler`` by default. But we want to return our own error codes for the 404 (Not Found) and 
500 (Internal Server Error) HTTP Status codes as well, so we'll implement our own ``IStatusCodeHandler``. See how we pass a ``IResponseNegotiator`` into the 
handler? Nancys IoC-container automatically injects it for us, so we can also negotiate the format of the response.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public class StatusCodeHandler404 : IStatusCodeHandler
    {
        private IResponseNegotiator responseNegotiator;

        public StatusCodeHandler404(IResponseNegotiator responseNegotiator)
        {
            this.responseNegotiator = responseNegotiator;
        }

        public bool HandlesStatusCode(HttpStatusCode statusCode, NancyContext context)
        {
            return statusCode == HttpStatusCode.NotFound;
        }

        public void Handle(HttpStatusCode statusCode, NancyContext context)
        {
            context.NegotiationContext = new NegotiationContext();

            Negotiator negotiator = new Negotiator(context)
                .WithStatusCode(HttpServiceErrorDefinition.NotFoundError.HttpStatusCode)
                .WithModel(HttpServiceErrorDefinition.NotFoundError.ServiceErrorModel);
                        
            context.Response = responseNegotiator.NegotiateResponse(negotiator, context);
        }
    }
}
```

And we'll do the same for the 500 HTTP Status code.

```csharp
namespace RestSample.Server.Infrastructure.Web
{
    public class StatusCodeHandler500 : IStatusCodeHandler
    {
        private IResponseNegotiator responseNegotiator;

        public StatusCodeHandler500(IResponseNegotiator responseNegotiator)
        {
            this.responseNegotiator = responseNegotiator;
        }

        public bool HandlesStatusCode(HttpStatusCode statusCode, NancyContext context)
        {
            return statusCode == HttpStatusCode.InternalServerError;
        }

        public void Handle(HttpStatusCode statusCode, NancyContext context)
        {
            context.NegotiationContext = new NegotiationContext();

            Negotiator negotiator = new Negotiator(context)
                .WithStatusCode(HttpServiceErrorDefinition.InternalServerError.HttpStatusCode)
                .WithModel(HttpServiceErrorDefinition.InternalServerError.HttpStatusCode);

            context.Response = responseNegotiator.NegotiateResponse(negotiator, context);
        }
    }
}
```

### Wiring it up: Bootstrapper ###

[DefaultResponseNegotiator]: https://github.com/NancyFx/Nancy/blob/master/src/Nancy/Responses/Negotiation/DefaultResponseNegotiator.cs

It's time to finally wire up all the things!

The API should support JSON and XML only, so we'll override the ``InternalConfiguration`` of Nancy and use ``JsonProcessor`` and ``XmlProcessor``. We 
also don't want any of the default status code handlers, so we only add the ``StatusCodeHandler404`` and the ``StatusCodeHandler500``.

We'll configure the application pipeline to use the custom error handler by simply calling ``CustomErrorHandler.Enable``. The 
response negotiator is determined from the IoC container and defaults to the [DefaultResponseNegotiator].

```csharp
namespace RestSample.Server
{
    public class Bootstrapper : DefaultNancyBootstrapper
    {
        protected override NancyInternalConfiguration InternalConfiguration
        {
            get
            {
                return NancyInternalConfiguration.WithOverrides(config => {
                    config.StatusCodeHandlers = new[] { typeof(StatusCodeHandler404), typeof(StatusCodeHandler500) };
                    config.ResponseProcessors = new [] { typeof(JsonProcessor), typeof(XmlProcessor) };
                });
            }
        }

        protected override void RequestStartup(TinyIoCContainer container, IPipelines pipelines, NancyContext context)
        {
            CustomErrorHandler.Enable(pipelines, container.Resolve<IResponseNegotiator>());
        }
    }
}
```

We are done!

### Example Requests and Error Responses ###

[curl]: http://curl.haxx.se/

Let's see the error handling in action and define a module, that throws some errors! The endpoints will throw exceptions and we'll see if 
they get translated into the JSON and XML errors we have defined above.

```csharp
    public class IndexModule : NancyModule
    {
        public IndexModule()
        {
		    Get["token"] = parameters =>
            {
                throw new InvalidTokenErrorException("The User had an invalid token.");
            };
			
            Get["unhandled"] = parameters =>
            {
                throw new System.InvalidOperationException("An invalid operation exception.");
            };
        }
    }
```

The easiest way to test the API is to use [curl] and call the endpoints. 

### token ###

The ``token`` endpoint throws a ``InvalidTokenErrorException``, which will be translated into a ``InvalidToken`` (Code: 30).

<pre>
PS C:\Users\philipp&gt; curl -i -H "Accept: application/json" -X GET http://localhost:12008/token.json

HTTP/1.1 400 Bad Request
Cache-Control: private
Content-Type: application/json; charset=utf-8
Vary: Accept
Server: Microsoft-IIS/8.0
X-AspNet-Version: 4.0.30319
X-SourceFiles: =?UTF-8?B?RDpcZ2l0aHViXG5hbmN5X3Jlc3RcUmVzdFNhbXBsZS5TZXJ2ZXJcdG9rZW4=?=
X-Powered-By: ASP.NET
Date: Sun, 19 Apr 2015 13:06:25 GMT
Content-Length: 42

{
	"code":30,
	"details":"Invalid API Token."
}
</pre>

And if we request XML data, the error response is negotiated:

<pre>
PS C:\Users\philipp&gt; curl -i -H "Accept: application/xml" -X GET http://localhost:12008/token.xml

HTTP/1.1 400 Bad Request
Cache-Control: private
Content-Type: application/xml
Vary: Accept
Server: Microsoft-IIS/8.0
X-AspNet-Version: 4.0.30319
X-SourceFiles: =?UTF-8?B?RDpcZ2l0aHViXG5hbmN5X3Jlc3RcUmVzdFNhbXBsZS5TZXJ2ZXJcdG9rZW4=?=
X-Powered-By: ASP.NET
Date: Sun, 19 Apr 2015 13:07:25 GMT
Content-Length: 233

&lt;?xml version="1.0"?&gt;
&lt;ServiceErrorModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"&gt;
  &lt;Code&gt;30&lt;/Code&gt;
  &lt;Details&gt;Invalid API Token.&lt;/Details&gt;
&lt;/ServiceErrorModel&gt;
</pre>

### unhandled ###

Any exception, that does not implement the ``IHasHttpServiceError`` is automatically turned into a ``GeneralError``.

<pre>
PS C:\Users\philipp&gt; curl -i -H "Accept: application/json" -X GET http://localhost:12008/unhandled

HTTP/1.1 400 Bad Request
Cache-Control: private
Content-Type: application/json; charset=utf-8
Vary: Accept
Server: Microsoft-IIS/8.0
X-AspNet-Version: 4.0.30319
X-SourceFiles: =?UTF-8?B?RDpcZ2l0aHViXG5hbmN5X3Jlc3RcUmVzdFNhbXBsZS5TZXJ2ZXJcdW5oYW5kbGVk?=
X-Powered-By: ASP.NET
Date: Sun, 19 Apr 2015 14:25:25 GMT
Content-Length: 70

{
	"code":0,
	"details":"An error occured during processing the request."
}
</pre>

And again the XML:

<pre>
PS C:\Users\philipp&gt; curl -i -H "Accept: application/xml" -X GET http://localhost:12008/unhandled

HTTP/1.1 400 Bad Request
Cache-Control: private
Content-Type: application/xml
Vary: Accept
Server: Microsoft-IIS/8.0
X-AspNet-Version: 4.0.30319
X-SourceFiles: =?UTF-8?B?RDpcZ2l0aHViXG5hbmN5X3Jlc3RcUmVzdFNhbXBsZS5TZXJ2ZXJcdW5oYW5kbGVk?=
X-Powered-By: ASP.NET
Date: Sun, 19 Apr 2015 14:26:39 GMT
Content-Length: 251

&lt;?xml version="1.0"?&gt;
&lt;ServiceErrorModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"&gt;
  &lt;Code&gt;0&lt;/Code&gt;
  &lt;Details&gt;An error occured during processing the request.&lt;/Details&gt;
&lt;/ServiceErrorModel&gt;
</pre>