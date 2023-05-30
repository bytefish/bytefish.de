title: Getting started with Blazor and FluentUI 
date: 2023-05-30 13:36
tags: aspnetcore, csharp, blazor
category: blazor
slug: blazor_fluentui_container_grid
author: Philipp Wagner
summary: This article is an initial article on Blazor, which is a recent UI technology by Microsoft.

It's hard to keep up with the latest frontlines of the "UI Civil Wars", raging within Microsofts 
departments. Say, what UI framework are you going to bet your companies money on? Is it WinForms, 
WPF (†), UWP (†), WinUI 2.x (†), WinUI 3 (†?), Xamarin (†), Xamarin.Forms (†), MAUI, Blazor Server, 
Blazor WebAssembly, Blazor Hybrid or the upcoming Blazor United?

Or do you want to go the (very logical) "Microsoft Teams"-Team route in ditching all of them 
in favor of React? It's very unclear, what UI technology is going win within Microsoft and 
lives for years to come. 

This article is an initial article on Blazor, more are expected to be written. 

## What we are going to build ##

Blazor is one of the currently most hyped things by Microsoft. There are enthusiastic reviews by 
the core .NET staff, so let's take a look at it. I am planning to build a complete sample application 
for it, but let's start slowly.

I will take a look at Fluent UI for Blazor, which is available at:

* [https://www.fluentui-blazor.net/](https://www.fluentui-blazor.net/)

## Why FluentUI for Blazor? ##

I have decided to use FluentUI for Blazor, because it looks like the Windows 11 controls. So once 
you embed your Blazor application inside in a Desktop application, it (hopefully) looks familiar to 
users. 

And Fluent UI for Blazor lives inside the Microsoft's GitHub organization... that gives tiny bits of 
confidence.

## What's missing in Fluent UI for Blazor? ##

You can quickly get up to speed by using the FluentUI for Blazor Project templates:

* [https://www.fluentui-blazor.net/Templates](https://www.fluentui-blazor.net/Templates)

But when I tried to build an application I found some things to be missing, that I am used to in 
other UI Web frameworks, like Containers, a 12-column Grid and things like validation. Whyis it 
missing? 

Well, I understand the reasoning of the core developers for not providing these components and 
Layout items. The official FluentUI design guidelines have not specified them, so they are waiting 
for them to be finalized.

Let's see what we can do!

## Adding Blazor Components ##

### Adding the Bootstrap 5 CSS Grid ###

I start by downloading the latest Bootstrap 5 release over at:

* [https://getbootstrap.com/docs/5.3/getting-started/download/](https://getbootstrap.com/docs/5.3/getting-started/download/)

I copy the Bootstrap Grid CSS from `dist/css/bootstrap-grid.css` to my Blazor project at `css/grid.css` and include it 
in the `index.html`:

```
<!DOCTYPE html>
<html lang="en">

    <head>
        <!-- ... -->
        <link href="css/grid.css" rel="stylesheet" />
        <!-- ... -->
    </head>
    
    <!-- ... -->

</html>
```

In the `grid.css` I am renaming `.container` to `.fluent-container` incase the Project templates already have a `.container` specified.

## Containers ##

We start by adding a `MaxWidth` enumeration for the container size:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.ComponentModel;

namespace WideWorldImporters.Blazor.Web.Enums
{
    public enum MaxWidth
    {
        [Description("lg")]
        Large,
        [Description("md")]
        Medium,
        [Description("sm")]
        Small,
        [Description("xl")]
        ExtraLarge,
        [Description("xxl")]
        ExtraExtraLarge,
        [Description("xs")]
        ExtraSmall,
    }
}
```

And then use it in the `FluentContainer.razor` component:

```razor
@namespace WideWorldImporters.Blazor.Components
@using Microsoft.Fast.Components.FluentUI.Utilities
@using WideWorldImporters.Blazor.Web.Enums
@using WideWorldImporters.Blazor.Web.Extensions

@inherits FluentComponentBase
<div @ref=Element @attributes="AdditionalAttributes" class="@Classname" style="@Style">
    @ChildContent
</div>

@code {

    // Licensed under the MIT license. See LICENSE file in the project root for full license information.

    /// <summary>
    /// Child content to be rendered.
    /// </summary>
    [Parameter]
    public RenderFragment? ChildContent { get; set; }

    /// <summary>
    /// Builds the CSS class based on the given Parameters.
    /// </summary>
    public string? Classname => new CssBuilder()
        .AddClass("fluent-container")
        .AddClass($"fluent-container-{MaxWidth.ToDescriptionString()}", !Fixed)
        .AddClass($"fluent-container-fluid", Fluid)
        .AddClass(Class)
        .Build();

    /// <summary>
    /// Set the container as fluid container. It will set the width to 100% at all breakpoints.
    /// </summary>
    public bool Fluid { get; set; } = false;

    /// <summary>
    /// Set the max-width to match the min-width of the current breakpoint. This is useful if you'd prefer to design for a fixed set of sizes instead of trying to accommodate a fully fluid viewport. It's fluid by default.
    /// </summary>
    [Parameter]
    public bool Fixed { get; set; } = false;

    /// <summary>
    /// Determine the max-width of the container. The container width grows with the size of the screen. Set to false to disable maxWidth.
    /// </summary>
    [Parameter]
    public MaxWidth MaxWidth { get; set; } = MaxWidth.Large;

    protected override void OnInitialized()
    {
        base.OnInitialized();
    }
}
```

## 12-Column Grid ##

What really helps when starting out with web applications is a 12-Grid column layout. No matter how 
hard I try, I still have problems centering a `div`, so don't get me started with `flex` and so on.

Let's just reuse the Bootstrap Grid and provide two wrappers `FluentGridRow` and `FluentGridColumn`.

In the `FluentGridRow.razor` we are adding:

```razor
@using Microsoft.Fast.Components.FluentUI.Utilities;
@using WideWorldImporters.Blazor.Web.Enums;
@using WideWorldImporters.Blazor.Web.Extensions;

@inherits FluentComponentBase
<div @attributes="AdditionalAttributes" class="@Classname" style="@Style">
    @ChildContent
</div>

@code {
    // Licensed under the MIT license. See LICENSE file in the project root for full license information.

    /// <summary>
    /// Child content to be rendered.
    /// </summary>
    [Parameter]
    public RenderFragment? ChildContent { get; set; }

    /// <summary>
    /// Builds the CSS class based on the given Parameters.
    /// </summary>
    public string? Classname => new CssBuilder()
        .AddClass("row")
        .AddClass($"row-{Columns}", Columns != null)
        .AddClass(Class)
        .Build();

    /// <summary>
    /// Optional number of columns for the row.
    /// </summary>
    [Parameter]
    public int? Columns { get; set; }

    protected override void OnInitialized()
    {
        base.OnInitialized();
    }
}
```

And in the `FluentGridColumn.razor` we are adding the following markup:

```razor
@using Microsoft.Fast.Components.FluentUI.Utilities;
@using WideWorldImporters.Blazor.Web.Enums;
@using WideWorldImporters.Blazor.Web.Extensions;

@inherits FluentComponentBase
<div @attributes="AdditionalAttributes" class="@Classname" style="@Style">
    @ChildContent
</div>

@code {

    // Licensed under the MIT license. See LICENSE file in the project root for full license information.

    /// <summary>
    /// Builds the CSS class based on the given Parameters.
    /// </summary>
    public string? Classname => new CssBuilder()
        .AddClass("col", !HasSize)
        .AddClass($"col-xs-{xs.ToString()}", xs != 0)
        .AddClass($"col-sm-{sm.ToString()}", sm != 0)
        .AddClass($"col-md-{md.ToString()}", md != 0)
        .AddClass($"col-lg-{lg.ToString()}", lg != 0)
        .AddClass($"col-xl-{xl.ToString()}", xl != 0)
        .AddClass($"col-xxl-{xxl.ToString()}", xxl != 0)
        .AddClass(Class)
        .Build();

    /// <summary>
    /// Child content to be rendered.
    /// </summary>
    [Parameter]
    public RenderFragment? ChildContent { get; set; }

    /// <summary>
    /// Column width for "xs" screen size.
    /// </summary>
    [Parameter]
    public int xs { get; set; }

    /// <summary>
    /// Column width for "sm" screen size.
    /// </summary>
    [Parameter]
    public int sm { get; set; }

    /// <summary>
    /// Column width for "md" screen size.
    /// </summary>
    [Parameter]
    public int md { get; set; }

    /// <summary>
    /// Column width for "lg" screen size.
    /// </summary>
    [Parameter]
    public int lg { get; set; }

    /// <summary>
    /// Column width for "xl" screen size.
    /// </summary>
    [Parameter]
    public int xl { get; set; }

    /// <summary>
    /// Column width for "xxl" screen size.
    /// </summary>
    [Parameter]
    public int xxl { get; set; }

    /// <summary>
    /// Checks if any column size has been set.
    /// </summary>
    public bool HasSize => xs != 0 || sm != 0 || md != 0 || lg != 0 || xl != 0 || xxl != 0;

    protected override void OnInitialized()
    {
        base.OnInitialized();
    }
}
```

And that's it.

## Conclusion ##

We can now use the container and create a Grid-Layout using our components. It 
feels just like using Bootstrap Grid and... I like it:

```razor
@page "/gridlayoutexample"

@using Microsoft.Fast.Components.FluentUI.Utilities
@using WideWorldImporters.Blazor.Components
@using WideWorldImporters.Blazor.Web.Components
@using WideWorldImporters.Blazor.Web.Enums
@using WideWorldImporters.Blazor.Web.Extensions

<FluentContainer>
    <FluentGridRow>
        <FluentGridColumn md="12" xl="3">
            <p>Row 1, Column 1</p>
        </FluentGridColumn>
        <FluentGridColumn md="12" xl="3">
            <p>Row 1, Column 2</p>
        </FluentGridColumn>
        <FluentGridColumn md="12" xl="3">
            <p>Row 1, Column 3</p>
        </FluentGridColumn>
    </FluentGridRow>
    <FluentGridRow>
        <FluentGridColumn xs="12" md="6">
            <p>Row 2, Column 1</p>
        </FluentGridColumn>
        <FluentGridColumn xs="12" md="6">
            <p>Row 2, Column 2</p>
        </FluentGridColumn>
    </FluentGridRow>
</FluentContainer>

@code {

}
```