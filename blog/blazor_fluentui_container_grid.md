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

### Adding a 12-Column CSS Grid ###


In the `app.css` we are adding a simple 12-Column Grid Layout. The idea is 
to help us building responsive layouts in a quicker way without needing to 
include additional libraries.

```css
.row {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    grid-gap: 20px;
}

.col-xs-12 {
    grid-column: span 12
}

.col-xs-11 {
    grid-column: span 11;
}

.col-xs-10 {
    grid-column: span 10
}

.col-xs-9 {
    grid-column: span 9
}

.col-xs-8 {
    grid-column: span 8
}

.col-xs-7 {
    grid-column: span 7
}

.col-xs-6 {
    grid-column: span 6
}

.col-xs-5 {
    grid-column: span 5
}

.col-xs-4 {
    grid-column: span 4
}

.col-xs-3 {
    grid-column: span 3
}

.col-xs-2 {
    grid-column: span 2
}

.col-xs-1 {
    grid-column: span 1
}

@media (min-width: 576px) {
    .col-sm-12 {
        grid-column: span 12
    }

    .col-sm-11 {
        grid-column: span 11;
    }

    .col-sm-10 {
        grid-column: span 10
    }

    .col-sm-9 {
        grid-column: span 9
    }

    .col-sm-8 {
        grid-column: span 8
    }

    .col-sm-7 {
        grid-column: span 7
    }

    .col-sm-6 {
        grid-column: span 6
    }

    .col-sm-5 {
        grid-column: span 5
    }

    .col-sm-4 {
        grid-column: span 4
    }

    .col-sm-3 {
        grid-column: span 3
    }

    .col-sm-2 {
        grid-column: span 2
    }

    .col-sm-1 {
        grid-column: span 1
    }
}

@media (min-width: 768px) {
    .col-md-12 {
        grid-column: span 12
    }

    .col-md-11 {
        grid-column: span 11;
    }

    .col-md-10 {
        grid-column: span 10
    }

    .col-md-9 {
        grid-column: span 9
    }

    .col-md-8 {
        grid-column: span 8
    }

    .col-md-7 {
        grid-column: span 7
    }

    .col-md-6 {
        grid-column: span 6
    }

    .col-md-5 {
        grid-column: span 5
    }

    .col-md-4 {
        grid-column: span 4
    }

    .col-md-3 {
        grid-column: span 3
    }

    .col-md-2 {
        grid-column: span 2
    }

    .col-md-1 {
        grid-column: span 1
    }
}

@media (min-width: 992px) {
    .col-lg-12 {
        grid-column: span 12
    }

    .col-lg-11 {
        grid-column: span 11;
    }

    .col-lg-10 {
        grid-column: span 10
    }

    .col-lg-9 {
        grid-column: span 9
    }

    .col-lg-8 {
        grid-column: span 8
    }

    .col-lg-7 {
        grid-column: span 7
    }

    .col-lg-6 {
        grid-column: span 6
    }

    .col-lg-5 {
        grid-column: span 5
    }

    .col-lg-4 {
        grid-column: span 4
    }

    .col-lg-3 {
        grid-column: span 3
    }

    .col-lg-2 {
        grid-column: span 2
    }

    .col-lg-1 {
        grid-column: span 1
    }
}

@media (min-width: 1200px) {
    .col-xl-12 {
        grid-column: span 12
    }

    .col-xl-11 {
        grid-column: span 11;
    }

    .col-xl-10 {
        grid-column: span 10
    }

    .col-xl-9 {
        grid-column: span 9
    }

    .col-xl-8 {
        grid-column: span 8
    }

    .col-xl-7 {
        grid-column: span 7
    }

    .col-xl-6 {
        grid-column: span 6
    }

    .col-xl-5 {
        grid-column: span 5
    }

    .col-xl-4 {
        grid-column: span 4
    }

    .col-xl-3 {
        grid-column: span 3
    }

    .col-xl-2 {
        grid-column: span 2
    }

    .col-xl-1 {
        grid-column: span 1
   }
}


@media (min-width: 1400px) {
    .col-xxl-12 {
        grid-column: span 12
    }

    .col-xxl-11 {
        grid-column: span 11;
    }

    .col-xxl-10 {
        grid-column: span 10
    }

    .col-xxl-9 {
        grid-column: span 9
    }

    .col-xxl-8 {
        grid-column: span 8
    }

    .col-xxl-7 {
        grid-column: span 7
    }

    .col-xxl-6 {
        grid-column: span 6
    }

    .col-xxl-5 {
        grid-column: span 5
    }

    .col-xxl-4 {
        grid-column: span 4
    }

    .col-xxl-3 {
        grid-column: span 3
    }

    .col-xxl-2 {
        grid-column: span 2
    }

    .col-xxl-1 {
        grid-column: span 1
    }
}
```


## Adding a Blazor Grid component ##

What really helps when starting out with web applications is a 12-Grid column layout. No matter how 
hard I try, I still have problems centering a `div`, so don't get me started with `flex` and so on.

Let's just reuse the 12-Column Grid Layout and provide two wrappers `FluentGridRow` and `FluentGridColumn`.

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
        .AddClass(Class)
        .Build();

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

@code {

}
```