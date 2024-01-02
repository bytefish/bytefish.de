title: Custom Form Validation with ASP.NET Core Blazor
date: 2024-01-02 12:49
tags: blazor, dotnet
category: dotnet
slug: custom_form_validation_blazor
author: Philipp Wagner
summary: This article discusses Form Validation in Blazor.

I am working myself into ASP.NET Core Blazor to better understand how its working and how I could 
use it to quickly build applications. One thing I need is a flexible approach to Form Validation, 
that doesn't lock me in on `DataAnnotations` and is somewhat more flexible.

The code has been taken from the Git Repository at:

* [https://github.com/bytefish/OpenFgaExperiments](https://github.com/bytefish/OpenFgaExperiments)

## Table of contents ##

[TOC]

## The Problem ##

[Kiota]: https://github.com/microsoft/kiota

The canonical example for Form Validation in Blazor uses the `DataAnnotationsValidator` component to reuse Data Annotations 
defined for a models properties. In the FluentUI Blazor demo, it looks like this.

```razor
page "/basicform-blazor-components"

<! -- ... -->

<EditForm Model="@starship" OnValidSubmit="@HandleValidSubmit">
    <DataAnnotationsValidator />
    <FluentValidationSummary />
    <!-- ... -->
</EditForm>
```

But I am using [Kiota] to generate an Api SDK from a given OData service. It works great, but the generated 
model doesn't come with `DataAnnotations`, such as `[Required]`. And while I am confident, you could "weave" 
them in using a `partial class`... there are many open questions, such as Localization from a Resource.

I want to start with a simpler approach to Form Validation and my initial idea is to provide a Validation 
function in the Code-Behind to Validate the Model of the `EditForm`. This should be a simple, yet flexible 
approach to validation. 

## Simple Form Validation ##

While we could reuse the existing .NET Validation infrastructure, such as a `ValidationContext` or a `ValidationResult`, these 
classes come with a lot of adjacent code we don't require. So a validation error in our application simply goes into a 
`ValidationError` record.

```csharp
/// <summary>
/// Validation Error for a Property
/// </summary>
public record ValidationError
{
    /// <summary>
    /// Gets or sets the PropertyName.
    /// </summary>
    public required string PropertyName { get; set; }

    /// <summary>
    /// Gets or sets the ErrorMessage.
    /// </summary>
    public required string ErrorMessage { get; set; }
}
```

We then provide our `SimpleValidator<TModel>` component, which takes two dependencies: The `EditContext` of the parent form, which 
is a `CascadingParameter` and our Validation function, which takes a `TModel` and returns an `IEnumerable<ValidationError>` after 
validation.

```csharp
/// <summary>
/// Provides a SimpleValidator, which takes a Validation function for the model to be validated.
/// </summary>
/// <typeparam name="TModel">Type of the Model in the <see cref="EditContext"/></typeparam>
public class SimpleValidator<TModel> : ComponentBase, IDisposable
{
    private IDisposable? _subscriptions;
    private EditContext? _originalEditContext;

    [CascadingParameter] EditContext? CurrentEditContext { get; set; }

    [Parameter]
    public Func<TModel?, IEnumerable<ValidationError>> ValidationFunc { get; set; } = null!;

    /// <inheritdoc />
    protected override void OnInitialized()
    {
        if (CurrentEditContext == null)
        {
            throw new InvalidOperationException($"{nameof(SimpleValidator<TModel>)} requires a cascading " +
                $"parameter of type {nameof(EditContext)}. For example, you can use {nameof(DataAnnotationsValidator)} " +
                $"inside an EditForm.");
        }

        _subscriptions = CurrentEditContext.EnableSimpleValidation(ValidationFunc);
        _originalEditContext = CurrentEditContext;
    }

    /// <inheritdoc />
    protected override void OnParametersSet()
    {
        if (CurrentEditContext != _originalEditContext)
        {
            // While we could support this, there's no known use case presently. Since InputBase doesn't support it,
            // it's more understandable to have the same restriction.
            throw new InvalidOperationException($"{GetType()} does not support changing the {nameof(EditContext)} dynamically.");
        }
    }

    /// <inheritdoc/>
    protected virtual void Dispose(bool disposing)
    {
    }

    void IDisposable.Dispose()
    {
        _subscriptions?.Dispose();
        _subscriptions = null;

        Dispose(disposing: true);
    }
}
```

You need to subscribe to the `EditContext#OnFieldChanged` and `EditContext#OnValidationRequested` event. We can then simply 
apply the Validation function and add the list of `ValidationError` to the `ValidationMessageStore` associated with 
the `EditContext`.

```csharp
public static class EditContextSimpleValidationExtensions
{
    /// <summary>
    /// Enables validation support for the <see cref="EditContext"/>.
    /// </summary>
    /// <param name="editContext">The <see cref="EditContext"/>.</param>
    /// <param name="validationFunc">Validation function to apply</param>
    /// <returns>A disposable object whose disposal will remove DataAnnotations validation support from the <see cref="EditContext"/>.</returns>
    public static IDisposable EnableSimpleValidation<TModel>(this EditContext editContext, Func<TModel?, IEnumerable<ValidationError>> validationFunc)
    {
        return new SimpleValidationEventSubscriptions<TModel>(editContext, validationFunc);
    }

    private sealed class SimpleValidationEventSubscriptions<TModel> : IDisposable
    {
        private readonly EditContext _editContext;
        private readonly Func<TModel?, IEnumerable<ValidationError>> _validationFunc;
        private readonly ValidationMessageStore _messages;

        public SimpleValidationEventSubscriptions(EditContext editContext, Func<TModel?, IEnumerable<ValidationError>> validationFunc)
        {
            _editContext = editContext ?? throw new ArgumentNullException(nameof(editContext));
            _validationFunc = validationFunc;
            _messages = new ValidationMessageStore(_editContext);

            _editContext.OnFieldChanged += OnFieldChanged;
            _editContext.OnValidationRequested += OnValidationRequested;
        }

        private void OnFieldChanged(object? sender, FieldChangedEventArgs eventArgs)
        {
            _messages.Clear();

            var validationErrors = _validationFunc((TModel) _editContext.Model);

            foreach (var validationError in validationErrors)
            {
                _messages.Add(_editContext.Field(validationError.PropertyName), validationError.ErrorMessage);
            }

            _editContext.NotifyValidationStateChanged();
        }

        private void OnValidationRequested(object? sender, ValidationRequestedEventArgs eventArgs)
        {
            _messages.Clear();

            var validationErrors = _validationFunc((TModel) _editContext.Model);

            foreach (var validationError in validationErrors)
            {
                _messages.Add(_editContext.Field(validationError.PropertyName), validationError.ErrorMessage);
            }

            _editContext.NotifyValidationStateChanged();
        }

        public void Dispose()
        {
            _messages.Clear();
            _editContext.OnFieldChanged -= OnFieldChanged;
            _editContext.OnValidationRequested -= OnValidationRequested;
            _editContext.NotifyValidationStateChanged();
        }
    }
}
```

And that's it!

## Using it ##

Inside an `EditForm` we can now simply use the `SimpleValidator` component and all that's required is passing the model type 
parameter (could probably be inferred) and the Validation function, like this:

```razor
<EditForm Model="@CurrentTaskItem" OnValidSubmit="@(async () => await HandleValidSubmitAsync())" FormName="task_item_edit" novalidate>
    <SimpleValidator TModel=TaskItem ValidationFunc="ValidateTaskItem" />
    <!-- ... -->
</EditForm>
```

Inside a more complicated form it might look like this:

```razor
@page "/TaskItem/Edit/{Id:int}"

@namespace RebacExperiments.Blazor.Pages

@using RebacExperiments.Blazor.Components
@using RebacExperiments.Blazor.Infrastructure
@using RebacExperiments.Blazor.Shared.Models;
@using RebacExperiments.Shared.ApiSdk;
@using RebacExperiments.Shared.ApiSdk.Models;

@inject ApiClient ApiClient

<EditForm Model="@CurrentTaskItem" OnValidSubmit="@(async () => await HandleValidSubmitAsync())" FormName="task_item_edit" novalidate>
    <SimpleValidator TModel=TaskItem ValidationFunc="ValidateTaskItem" />
    <FluentValidationSummary />
    
    <FluentStack Orientation="Orientation.Vertical">
        <! -- Fields... -->
     </FluentStack>
    
    <FluentStack Orientation="Orientation.Horizontal">
         <FluentButton Type="ButtonType.Submit" Appearance="Appearance.Accent">Save Changes</FluentButton>
         <FluentButton Appearance="Appearance.Accent">Discard Changes</FluentButton>
     </FluentStack>
     
 </EditForm>
```

In the Code Behind we have to implement the Validation function (`ValidateTaskItem` for the example). We also want to 
translate Error Messages, so we also inject an `IStringLocalizer<TResource>` into the class. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.AspNetCore.Components;
using Microsoft.Extensions.Localization;
using RebacExperiments.Blazor.Infrastructure;
using RebacExperiments.Blazor.Localization;
using RebacExperiments.Shared.ApiSdk.Models;

namespace RebacExperiments.Blazor.Pages
{
    public partial class TaskItemEdit
    {
        /// <summary>
        /// The ID of the TaskItem to display.
        /// </summary>
        [Parameter]
        public int Id { get; set; }

        /// <summary>
        /// Localizer to use for translating messages.
        /// </summary>
        [Inject]
        public IStringLocalizer<SharedResource> Loc { get; set; } = null!;
        
        // ...

        /// <summary>
        /// Validates a <see cref="TaskItem"/>.
        /// </summary>
        /// <param name="taskItem">TaskItem to validate</param>
        /// <returns>The list of validation errors for the EditContext model fields</returns>
        private IEnumerable<ValidationError> ValidateTaskItem(TaskItem taskItem)
        {
            if (string.IsNullOrWhiteSpace(taskItem.Title))
            {
                yield return new ValidationError 
                { 
                    PropertyName = nameof(taskItem.Title), 
                    ErrorMessage = Loc.GetString("Validation_IsRequired", nameof(taskItem.Title)) 
                };
            }
            
            if(string.IsNullOrWhiteSpace(taskItem.Description))
            {
                yield return new ValidationError
                {
                    PropertyName = nameof(taskItem.Description),
                    ErrorMessage = Loc.GetString("Validation_IsRequired", nameof(taskItem.Description))
                };
            }

            if (taskItem.TaskItemPriority == null)
            {
                yield return new ValidationError
                {
                    PropertyName = nameof(taskItem.TaskItemPriority),
                    ErrorMessage = Loc.GetString("Validation_IsRequired", nameof(taskItem.TaskItemPriority))
                };
            }
        }
    }
}
```

## Conclusion ##

And that's it! 

I think this is very simple, yet flexible way to provide Form Validation in Blazor. You could easily extract common validations and 
build your own abstractions on top, such as using `DataAnnotations`-based validation in the method or calling into a `FluentValidation` 
validator.

There is room for improvements, and I'd be happy to hear about your approach to validation.