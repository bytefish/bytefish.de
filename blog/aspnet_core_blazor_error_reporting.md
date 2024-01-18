title: ASP.NET Core Blazor Error Handling and Error Documentation
date: 2024-01-18 13:15
tags: blazor, dotnet
category: dotnet
slug: aspnet_core_blazor_error_reporting
author: Philipp Wagner
summary: This article shows how to display and handle errors with Blazor.

In my last post I have shown how to provide consistent error handling within an ASP.NET Core OData 
application, and we have seen how to display localized messages in the Blazor Web Assembly client. 

This is great!

But imagine for a second you are using your software and you hit a bug. It's frustrating! It's even more 
frustrating if you don't know what the error means. Am I at fault? Did I use a wrong input format? Has 
someone given me an invalid link? Do I lack permissions to access the data?

In this article we will see how to give the user additional feedback and help to understand errors.

At the end of the article we will have a flexible way to provide error messages with a link to additional 
information about possible error reasons. The documentation is written in Markdown:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_blazor_error_reporting/login-error-with-help.jpg">
        <img src="/static/images/blog/aspnet_core_blazor_error_reporting/login-error-with-help.jpg" alt="Login Screen with Error Message and Help Link">
    </a>
</div>

The code has been taken from the Git Repository at:

* [https://github.com/bytefish/OpenFgaExperiments](https://github.com/bytefish/OpenFgaExperiments)

## Table of contents ##

[TOC]

## ASP.NET Core Implementation ##

So the most obvious solution for me is to write the error documentation in Markdown, put it in the 
`wwwroot` of the Blazor application and use a Markdown processor like `Markdig` to convert it down to 
HTML. Sanitized HTML will then be used in the Blazor Component.

That said, I personally don't think, that Markdown is well suited for complex software documentation. I 
have previously worked with professional help authoring tools to provide single source publishing, and 
Markdown wouldn't be the right tool for the job.

Anyways... Let's use Markdown!

### Markdown Content for Error Codes ###

I start by creating a new folder `/docs/errors` in the `wwwroot` directory. For each of the available 
error codes in the application I put a Markdown file there, like `ApiError_Auth_000001.md`:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_blazor_error_reporting/solution-markdown-files.jpg">
        <img src="/static/images/blog/aspnet_core_blazor_error_reporting/solution-markdown-files.jpg" alt="Markdown Files for Each Error Code">
    </a>
</div>

The content should be some kind of help page for a user, so they know about possible problems. It's not 
very creative, what I came up with here, but you get the point.

```markdown
# Authentication Failure (ApiError_Auth_000001)

The Authentication has failed. This indicates a problem to log in to the application, which 
may be due to an invalid combination of a username and password, or the account is not permitted 
to log in.

Please try to contact the support, if the problem persists.

## Description

Add a longer description here, so a user knows what to do ...

## Example

Add Examples here ...
```

### A Blazor Component for rendering Markdown Content ###

The Fluent UI documentation has a nice example for a Markdown component at:

* [https://www.fluentui-blazor.net/Lab/MarkdownSection](https://www.fluentui-blazor.net/Lab/MarkdownSection.)

It goes like this.

The `MarkdownSection.razor` component inherits the `FluentComponentBase` and just uses the `HtmlContent` defined in the Code-Behind:

```razor
@namespace RebacExperiments.Blazor.Components

@inherits FluentComponentBase

@HtmlContent
```

In the `MarkdownSection.razor.cs` file, we can then convert from Markdown to HTML. The sanitized HTML is stored 
in a `MarkupString`, which the Razor Component binds to:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Markdig;
using Microsoft.AspNetCore.Components;
using Microsoft.FluentUI.AspNetCore.Components;
using RebacExperiments.Blazor.Infrastructure;

namespace RebacExperiments.Blazor.Components
{
    /// <summary>
    /// This is based on https://www.fluentui-blazor.net/Lab/MarkdownSection.
    /// </summary>
    public partial class MarkdownSection : FluentComponentBase
    {
        private string? _content;
        private bool _raiseContentConverted;

        [Inject]
        private IStaticAssetService StaticAssetService { get; set; } = default!;

        /// <summary>
        /// Gets or sets asset to read the Markdown from.
        /// </summary>
        [Parameter]
        public required string FromAsset { get; set; }

        /// <summary>
        /// Raised, when the Content has been converted.
        /// </summary>
        [Parameter]
        public EventCallback OnContentConverted { get; set; }

        /// <summary>
        /// Sanitized HTML Content.
        /// </summary>
        public MarkupString HtmlContent { get; private set; }

        public string? InternalContent
        {
            get => _content;
            set
            {
                _content = value;

                HtmlContent = ConvertToMarkupString(_content);

                if (OnContentConverted.HasDelegate)
                {
                    OnContentConverted.InvokeAsync();
                }

                _raiseContentConverted = true;

                StateHasChanged();
            }
        }

        protected override async Task OnInitializedAsync()
        {
            InternalContent = await StaticAssetService.GetAsync(FromAsset);

            if (_raiseContentConverted)
            {
                _raiseContentConverted = false;

                if (OnContentConverted.HasDelegate)
                {
                    await OnContentConverted.InvokeAsync();
                }
            }
        }

        private static MarkupString ConvertToMarkupString(string? value)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                // Convert markdown string to HTML
                string? html = Markdown.ToHtml(value, new MarkdownPipelineBuilder().UseAdvancedExtensions().Build());

                // Return sanitized HTML as a MarkupString that Blazor can render
                return new MarkupString(html);
            }

            return new MarkupString();
        }
    }
}
```

The `IStaticAssetService` is an implementation by the Fluent UI team at:

* [.../examples/Demo/Shared/Infrastructure/HttpBasedStaticAssetService.cs](https://github.com/microsoft/fluentui-blazor/blob/7b92a81d45f5370c00ddfc91e6deb5e3beb4f491/examples/Demo/Shared/Infrastructure/HttpBasedStaticAssetService.cs)

### An Error Details Page using the MarkdownSection ###

All that now needs to be done is to pass an `ErrorCode` for the Route and use the `<MarkdownSection>`, which is 
going to load the Markdown content and render it.

```razor
@page "/Help/Errors/{ErrorCode}"

@using RebacExperiments.Blazor.Components

@namespace RebacExperiments.Blazor.Pages

@inject ApplicationErrorTranslator ApplicationErrorTranslator
<style>
    p {
        max-width: 700px;  
    }
</style>

    @if (!string.IsNullOrWhiteSpace(_assetUrl))
    {
        <MarkdownSection FromAsset=@_assetUrl />
    }
    else
    {
        <p>Loading Error Information ...</p>
    }
```

In the Code-Behind we can see, that all it does is to build the `AssetUrl`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Components;

namespace RebacExperiments.Blazor.Pages
{
    public partial class ErrorDetail
    {
        /// <summary>
        /// Gets or sets the Error Code to view information for.
        /// </summary>
        [Parameter]
        public string? ErrorCode { get; set; }

        private string? _assetUrl;

        protected override void OnParametersSet()
        {
            if(ErrorCode != null)
            {
                _assetUrl = $"/docs/errors/{ErrorCode}.md";
            }            
        }
    }
}
```

You can now navigate to an Address like `/Help/Errors/ApiError_Auth_000001` and you will see beautiful Markdown being rendered:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_blazor_error_reporting/error-details-page.jpg">
        <img src="/static/images/blog/aspnet_core_blazor_error_reporting/error-details-page.jpg" alt="Details Page example">
    </a>
</div>

### Extracting Error Information of an Exception ###

The `ApiClient` the application is using to perform requests throws an `ODataError`, if a request has failed. In the 
previous article, we have developed an `ApplicationErrorTranslator` to extract the Error information from a given 
`Exception`.

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

        public (string ErrorCode, string ErrorMessage) GetErrorMessage(Exception exception) 
        {
            return exception switch
            {
                ODataError e => (e.Error!.Code!, GetErrorMessageFromODataError(e)),
                Exception e => (LocalizationConstants.ClientError_UnexpectedError, GetErrorMessageFromException(e)),
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

### Showing the Errors in a FluentUI Message Bar ###

We can then use the Fluent UI `MessageBar` to display the error. We wrap the `MessageService` 


```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;
using Microsoft.FluentUI.AspNetCore.Components;
using RebacExperiments.Blazor.Localization;

namespace RebacExperiments.Blazor.Infrastructure
{
    public class ApplicationErrorMessageService
    {
        private readonly IStringLocalizer<SharedResource> _sharedLocalizer;
        private readonly ApplicationErrorTranslator _applicationErrorTranslator;
        private readonly IMessageService _messageService;
        private readonly NavigationManager _navigationManager;
        

        public ApplicationErrorMessageService(IStringLocalizer<SharedResource> sharedLocalizer, IMessageService messageService, NavigationManager navigationManager, ApplicationErrorTranslator applicationErrorTranslator)
        {
            _sharedLocalizer = sharedLocalizer;
            _navigationManager = navigationManager;
            _applicationErrorTranslator = applicationErrorTranslator;
            _messageService = messageService;
        }

        public void ShowErrorMessage(Exception exception, Action<MessageOptions>? configure = null)
        {
            (var errorCode, var errorMessage) = _applicationErrorTranslator.GetErrorMessage(exception);

            _messageService.ShowMessageBar(options =>
            {
                options.Section = App.MESSAGES_TOP;
                options.Intent = MessageIntent.Error;
                options.ClearAfterNavigation = false;
                options.Title = _sharedLocalizer["Message_Error_Title"];
                options.Body = errorMessage;
                options.Timestamp = DateTime.Now;
                options.Link = new ActionLink<Message>
                {
                    Text = _sharedLocalizer["Message_ShowHelp"],
                    OnClick = (message) =>
                    {
                        _navigationManager.NavigateTo($"Help/Errors/{errorCode}");

                        return Task.CompletedTask;
                    }
                };

                // If we need to customize it like using a different section or intent, we should
                // use the action passed to us ...
                if(configure != null )
                {
                    configure(options);
                }
            });
        }
    }
}
```

In the `Login` Page we will then add a `<FluentMessageBarProvider Section="@App.MESSAGES_TOP" />`, which basically is 
the placeholder, where Fluent UI displays the Messages.

```razor
@page "/Login"
@layout EmptyLayout

@using RebacExperiments.Shared.ApiSdk

@inject ApiClient ApiClient

@inject IStringLocalizer<SharedResource> Loc
@inject NavigationManager NavigationManager
@inject CustomAuthenticationStateProvider AuthStateProvider
@inject ApplicationErrorMessageService ApplicationErrorMessageService

<div class="container">
    <FluentCard Width="500px">
        <EditForm Model="@Input" OnValidSubmit="SignInUserAsync" FormName="login_form" novalidate>
            <FluentStack Orientation="Orientation.Vertical">
                <FluentGrid Spacing="3" Justify="JustifyContent.Center">
                    <!-- ... -->
                     <FluentGridItem xs="12">
                         <FluentMessageBarProvider Section="@App.MESSAGES_TOP" />
                     </FluentGridItem>
                 </FluentGrid>
             </FluentStack>
         </EditForm>
     </FluentCard>
 </div>
```

In the Code-Behind we can then put our code in a `try-catch` block, and handle the `Exception` where it is thrown.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace RebacExperiments.Blazor.Pages
{
    public partial class Login
    {
        /// <summary>
        /// Data Model for binding to the Form.
        /// </summary>
        private sealed class InputModel
        {
        /// <summary>
        /// Signs in the User to the Service using Cookie Authentication.
        /// </summary>
        /// <returns></returns>
        public async Task SignInUserAsync()
        {
            try
            {
                // ...
            }
            catch(Exception e)
            {
                ApplicationErrorMessageService.ShowErrorMessage(e);
            }
        }

```

### Adding an ErrorBoundary to the MainLayout ###

Sometimes you have an `Exception`, that bubbles up your component. To prevent crashing everything, we put an `ErrorBoundary` into the layout, 
so we catch it there... as some kind of "Global Error Handling".

```razor
<!-- ... -->
@inject ApplicationErrorMessageService ApplicationErrorMessageService

<!-- ... -->

<article id="article">
    <FluentMessageBarProvider Section="@App.MESSAGES_TOP" />
    <ErrorBoundary @ref="_errorBoundary">
        <ChildContent>
            <div>@Body</div>
        </ChildContent>
        <ErrorContent Context="exception">
            @{
                ApplicationErrorMessageService.ShowErrorMessage(exception);
            }
        </ErrorContent>
    </ErrorBoundary>
</article>

<!-- ... -->
```

### Providing a List of Errors ###

Sometimes a user wants to see the list of all errors available. Maybe they got an error message or need 
to research a problem, someone integrating the service has. A `FluentDataGrid` is a nice way to present 
the information.

```razor
@page "/Help/Errors"

@using RebacExperiments.Blazor.Components

@namespace RebacExperiments.Blazor.Pages

@inject NavigationManager NavigationManager
@inject IStringLocalizer<SharedResource> Loc

<FluentDataGrid Items="@Errors" ResizableColumns=true GridTemplateColumns="0.2fr 0.2fr 1fr 0.2fr" TGridItem="ErrorListItem">
    <PropertyColumn Property="@(c => c.Code)" Sortable="true" Align="Align.Start" />
    <PropertyColumn Property="@(c => c.Title)" Sortable="true" Align="Align.Start" />
    <PropertyColumn Property="@(c => c.Message)" Sortable="true" Align="Align.Start" />
    <TemplateColumn Title="Actions" Align="@Align.Start">
        <FluentButton OnClick="@(() => ShowDetails(context))">@Loc["DataGrid_Button_Details"]</FluentButton>
    </TemplateColumn>
</FluentDataGrid>
```

In the Code-Behind we are going to list all application errors manually. You could come up with less verbose ideas for, 
but hey, it's simple and it works good. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Components;

namespace RebacExperiments.Blazor.Pages
{
    public partial class ErrorDataGrid
    {
        public class ErrorListItem
        {
            public required string Code { get; set; }

            public required string Title { get; set; }

            public required string Message { get; set; }
        }

        private IQueryable<ErrorListItem> Errors = new List<ErrorListItem>().AsQueryable();

        protected override void OnInitialized()
        {
            Errors = new List<ErrorListItem>()
            {
                    new ErrorListItem { Code = "ClientError_UnexpectedError", Title = "Unexpected Error", Message = Loc["ClientError_UnexpectedError"] },
                    new ErrorListItem { Code = "ApiError_Auth_000001", Title = "Authentication Failure", Message = Loc["ApiError_Auth_000001"] },
                    new ErrorListItem { Code = "ApiError_Auth_000002", Title = "Missing Permissions", Message = Loc["ApiError_Auth_000002"]},
                    new ErrorListItem { Code = "ApiError_Auth_000003", Title = "Unauthorized Access", Message = Loc["ApiError_Auth_000003"] },
                    new ErrorListItem { Code = "ApiError_Entity_000001", Title = "Entity Not Found", Message = Loc["ApiError_Entity_000001"] },
                    new ErrorListItem { Code = "ApiError_Entity_000002", Title = "Entity Permissions Missing", Message = Loc["ApiError_Entity_000002"] },
                    new ErrorListItem { Code = "ApiError_Entity_000003", Title = "Concurrency Failure", Message = Loc["ApiError_Entity_000003"] },
                    new ErrorListItem { Code = "ApiError_RateLimit_000001", Title = "Too Many Requests", Message = Loc["ApiError_RateLimit_000001"] },
                    new ErrorListItem { Code = "ApiError_Routing_000001", Title = "Resource Not Found", Message = Loc["ApiError_Routing_000001"] },
                    new ErrorListItem { Code = "ApiError_Routing_000002", Title = "Method Not Allowed", Message = Loc["ApiError_Routing_000002"] },
                    new ErrorListItem { Code = "ApiError_System_000001", Title = "Internal Server Error", Message = Loc["ApiError_System_000001"] },
            }
            .AsQueryable();
        }

        private void ShowDetails(ErrorListItem errorListItem)
        {
            NavigationManager.NavigateTo($"/Help/Errors/{errorListItem.Code}");
        }
    }
}
```

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_blazor_error_reporting/error-list-page.jpg">
        <img src="/static/images/blog/aspnet_core_blazor_error_reporting/error-list-page.jpg" alt="List of Errors">
    </a>
</div>

## Conclusion ##

And that's it.

In this article we have seen how to render Markdown content in a Blazor application. It was used to provide 
help pages, that a user can navigate to when an Error is shown within the Client. The Errors can be handeled 
either directly in the component, or they are caught in an `ErrorBoundary` of the default layout.

I am not saying this is *the perfect way* to implement your Error handling with Blazor. But I think it works 
pretty well, because a simple `try-catch` is sufficient to display the errors in the User Interface. And any 
`Exception` that slips through, is still going to be caught in the last line of defense... the 
`ErrorBoundary`.