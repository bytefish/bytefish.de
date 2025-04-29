title: Building Custom Filter Controls in WpfDataGridFilter
date: 2025-04-29 12:34
tags: csharp, dotnet, wpf
category: wpf
slug: wpfdatagridfilter_custom_filters
author: Philipp Wagner
summary: Implementing a Custom Control for filtering Spatial Data using WpfDataGridFilter.

[WpfDataGridFilter]: https://github.com/bytefish/WpfDataGridFilter
[WideWorldImporters]: https://github.com/bytefish/WideWorldImporters

In this example we'll take a look at writing a custom Filter for [WpfDataGridFilter], which is a small library 
to simplify sever-side filtering in a WPF application. We will see how to use it for the [WideWorldImporters] 
backend, which is my current playground to base tutorials on.

All code can be found in a Git repository at:

* [https://github.com/bytefish/WideWorldImporters](https://github.com/bytefish/WideWorldImporters)

## What we are going to build ##

The [WpfDataGridFilter] library comes with few Filtering Controls built-in, such as Filters for `String`, 
`Integer` or `DateTime` properties. But what, if we need to filter some special type not provided 
built-in? 

We are going to write our own, of course!

The WideWorldImporters uses the `Microsoft.Spatial` library to define spatial types. In previous 
articles I have shown how to use these types in a Backend, when confronted with EntityFramework 
Core.

In this article we are going to take a look at providing a filter control to filter the WideWorldImporters 
database the Delivery Location of a `Customer`. The Property `Customer.DeliveryLocation` has been generated 
as a `GeographyPoint`:

```csharp
public partial class Customer : global::Microsoft.OData.Client.BaseEntityType, global::System.ComponentModel.INotifyPropertyChanged
{
    // ...
    
    public virtual Microsoft.Spatial.GeographyPoint DeliveryLocation
    {
        get
        {
            return this._DeliveryLocation;
        }
        set
        {
            this.OnDeliveryLocationChanging(value);
            this._DeliveryLocation = value;
            this.OnDeliveryLocationChanged();
            this.OnPropertyChanged("deliveryLocation");
        }
    }
    
    // ...
}
```

The final result is a Custom Control, which is shown in the Column Filter Popup:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/wpfdatagridfilter_custom_filters/wwi-custom-geo-filter.jpg">
        <img src="/static/images/blog/wpfdatagridfilter_custom_filters/wwi-custom-geo-filter.jpg" alt="WPF OData Example">
    </a>
</div>

## Getting it up and running ##

It's useful to actually *see*, what we are going to build. It also sets you up for local development.

### Running the Backend ###

You start by cloning the WideWorldImporters Git repository:

```
git clone https://github.com/bytefish/WideWorldImporters.git
```

Then start the Backend and SQL Server 2022 by using Docker:

```
docker compose --profile backend up
```

The Backend consists of two services: 

* SQL Server 2022 Database
    * Restores and provides the WideWorldImporters database.
* ASP.NET Core Backend
    * Exposes OData Endpoints for querying the data.

The Backend exposes the ASP.NET Core endpoints using the following URL:

* https://localhost:5000

And that's it for the Backend.

### Running the WPF Application ###

You can use `dotnet run` to start the WPF application, by running:

```
dotnet run --project .\src\WideWorldImporters.Desktop.Client\WideWorldImporters.Desktop.Client.csproj
```

That's it. Congratulations! You will now see the WPF application, where you can see the 
sorting, pagination and filtering for the WPF DataGrid in action.

## Implementation ##

Let's take a look at how a Custom Filter for Spatial Types is built.

### Defining Constants for our Filter Controls ###

Our Spatial have something to do with Geography, so I start by adding a class `GeographyFilter`, which 
is goint to hold all 

```csharp
public static class GeographyFilter
{
    // TODO
}
```

In [WpfDataGridFilter] all Filter Controls are resolved by a `FilterType`. We want to Filter for Distance to a 
given `GeographyPoint`, so let's add the FilterType:

```csharp
public static class GeographyFilter
{
    // Filter Type
    public static FilterType GeoDistanceFilterType = new FilterType { Name = "GeoDistanceFilter" };
}
```

The library comes with a set of `FilterOperator`, say a `IsNull` or `IsNotNull`. But we don't have Filter 
Operators for Distances, let's add them:

```csharp
public static class GeographyFilter
{
    // Filter Type
    public static FilterType GeoDistanceFilterType = new FilterType { Name = "GeoDistanceFilter" };

    // Filter Operators
    public static class FilterOperators
    {
        public static FilterOperator DistanceLessThan = new FilterOperator { Name = nameof(DistanceLessThan) };
        public static FilterOperator DistanceLessEqualThan = new FilterOperator { Name = nameof(DistanceLessEqualThan) };
        public static FilterOperator DistanceGreaterThan = new FilterOperator { Name = nameof(DistanceGreaterThan) };
        public static FilterOperator DistanceGreaterEqualThan = new FilterOperator { Name = nameof(DistanceGreaterEqualThan) };
    }
}
```

But what about displaying the Operators in a UI? 

We need to add translations, which is done by the `Translations<T>` class of the [WpfDataGridFilter] library.

```csharp
public static class GeographyFilter
{
    // Filter Type
    public static FilterType GeoDistanceFilterType = new FilterType { Name = "GeoDistanceFilter" };

    // Filter Operators
    public static class FilterOperators
    {
        public static FilterOperator DistanceLessThan = new FilterOperator { Name = nameof(DistanceLessThan) };
        public static FilterOperator DistanceLessEqualThan = new FilterOperator { Name = nameof(DistanceLessEqualThan) };
        public static FilterOperator DistanceGreaterThan = new FilterOperator { Name = nameof(DistanceGreaterThan) };
        public static FilterOperator DistanceGreaterEqualThan = new FilterOperator { Name = nameof(DistanceGreaterEqualThan) };
    }
    
    // Translations
    public static class Translations
    {
        public static List<Translation<FilterOperator>> FilterOperatorTranslations =
        [
            new Translation<FilterOperator>() { Value = FilterOperators.DistanceLessThan, Text = "Distance Less Than"},
            new Translation<FilterOperator>() { Value = FilterOperators.DistanceLessEqualThan, Text = "Distance Less Equal Than"},
            new Translation<FilterOperator>() { Value = FilterOperators.DistanceGreaterThan, Text = "Distance Greater Than"},
            new Translation<FilterOperator>() { Value = FilterOperators.DistanceGreaterEqualThan, Text = "Distance Greater Equal Than"},
        ];
    }
}
```


### Adding a Custom FilterDescriptor ###

Filters in the library are always a `FilterDescriptor`, so let's add one for the Geo Distance we are calculating:

```csharp
/// <summary>
/// The FilterDescriptor for Geography Distances.
/// </summary>
public record GeoDistanceFilterDescriptor : FilterDescriptor
{
    public override FilterType FilterType => GeographyFilter.GeoDistanceFilterType;

    /// <summary>
    /// Gets or sets the Latitude.
    /// </summary>
    public double? Latitude { get; set; }

    /// <summary>
    /// Gets or sets the Longitude.
    /// </summary>
    public double? Longitude { get; set; }

    /// <summary>
    /// Gets or sets the Distance.
    /// </summary>
    public double? Distance { get; set; }
}
```

### Adding an IFilterTranslator ###

We are going to use `WpfDataGridFilter.DynamicLinq` for filtering on an `IQueryable<T>`. This means, we'll also 
need to convert the `FilterDescriptor` into a Predicate, given the `FilterOperator` and Properties of the 
`FilterDescriptor`. 

Dynamic LINQ doesn't allow you to "just use" any C# function you want, due to sane security reasons. So we'll 
add a custom `ParsingConfig`, that allows to use the Custom `Distance` function for the 
`Microsoft.Spatial.Point`.

```csharp
// ...

namespace WideWorldImporters.Desktop.Client.Controls
{
    /// <summary>
    /// Used to apply the Geo Distance Queries on an <see cref="IQueryable{T}">.
    /// </summary>
    public class GeoDistanceFilterTranslator : IFilterTranslator
    {
        public FilterType FilterType => GeographyFilter.GeoDistanceFilterType;

        private readonly ParsingConfig _parsingConfig;

        public GeoDistanceFilterTranslator()
        {
            _parsingConfig = GetParsingConfig();
        }

        public IQueryable<TEntity> Convert<TEntity>(IQueryable<TEntity> source, FilterDescriptor filterDescriptor)
        {
            if (filterDescriptor is not GeoDistanceFilterDescriptor f)
            {
                return source;
            }

            // Convert to a Microsoft Spatial Point, we could use in an OData Query
            GeographyPoint point = GeographyPoint.Create(f.Latitude ?? 0, f.Longitude ?? 0);
            
            switch (f.FilterOperator)
            {
                case var _ when f.FilterOperator == GeographyFilter.FilterOperators.DistanceLessThan:
                    return source.Where(_parsingConfig, $"(GeographyOperationsExtensions.Distance({f.PropertyName}, @0) lt @1)", point, f.Distance);
                case var _ when f.FilterOperator == GeographyFilter.FilterOperators.DistanceLessThan:
                    return source.Where(_parsingConfig, $"({f.PropertyName}.Distance{f.PropertyName}, (@0) le @1)", point, f.Distance);
                case var _ when f.FilterOperator == GeographyFilter.FilterOperators.DistanceLessThan:
                    return source.Where(_parsingConfig, $"({f.PropertyName}.Distance({f.PropertyName}, @0) gt @1)", point, f.Distance);
                case var _ when f.FilterOperator == GeographyFilter.FilterOperators.DistanceLessThan:
                    return source.Where(_parsingConfig, $"({f.PropertyName}.Distance({f.PropertyName}, @0) gt @1)", point, f.Distance);
                default:
                    throw new InvalidOperationException($"The Filter Operator '{f.FilterOperator.Name}' is not supported");
            }
        }

        public ParsingConfig GetParsingConfig()
        {
            ParsingConfig parsingConfigWithSpatial = new ParsingConfig();

            parsingConfigWithSpatial.CustomTypeProvider = new DefaultDynamicLinqCustomTypeProvider(parsingConfigWithSpatial, [typeof(GeographyOperationsExtensions)], false);

            return parsingConfigWithSpatial;

        }
    }
}
```

### Adding the FilterControl ###

```xml
<ResourceDictionary
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    xmlns:controls="clr-namespace:WideWorldImporters.Desktop.Client.Controls">

    <Style TargetType="{x:Type controls:GeoDistanceFilterControl}">
        <Setter Property="Template">
            <Setter.Value>
                <ControlTemplate TargetType="{x:Type controls:GeoDistanceFilterControl}">
                    <Grid>
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition Width="150"/>
                            <ColumnDefinition Width="Auto"/>
                        </Grid.ColumnDefinitions>
                        <Grid.RowDefinitions>
                            <RowDefinition Height="40" />
                            <RowDefinition Height="40" />
                            <RowDefinition Height="40" />
                            <RowDefinition Height="40" />
                            <RowDefinition Height="40" />
                            <RowDefinition Height="*" />
                        </Grid.RowDefinitions>

                        <TextBlock Grid.Row="0" Grid.Column="0" Style="{DynamicResource FilterLabelStyle}">Filter Operator:</TextBlock>

                        <ComboBox x:Name="PART_FilterOperators"
                                  Grid.Row="0" Grid.Column="1"
                                  Style="{DynamicResource FilterComboBoxStyle}" />

                        <TextBlock Grid.Row="1" Grid.Column="0" Style="{DynamicResource FilterLabelStyle}">Latitude:</TextBlock>

                        <TextBox x:Name="PART_LatitudeTextBox"
                                 Grid.Row="1" Grid.Column="1"
                                 Style="{DynamicResource FilterTextBoxStyle}"/>

                        <TextBlock Grid.Row="2" Grid.Column="0" Style="{DynamicResource FilterLabelStyle}">Longitude:</TextBlock>

                        <TextBox x:Name="PART_LongitudeTextBox"
                            Grid.Row="2" Grid.Column="1"
                            Style="{DynamicResource FilterTextBoxStyle}" />

                        <TextBlock Grid.Row="3" Grid.Column="0" Style="{DynamicResource FilterLabelStyle}">Distance (in Meters):</TextBlock>

                        <TextBox x:Name="PART_DistanceTextBox"
                            Grid.Row="3" Grid.Column="1"
                            Style="{DynamicResource FilterTextBoxStyle}" />

                        <StackPanel Grid.Row="4" Grid.Column="0" Grid.ColumnSpan="2" Orientation="Horizontal" HorizontalAlignment="Right">
                            <Button x:Name="PART_ResetButton" 
                                    Style="{DynamicResource FilterButtonStyle}" />
                            <Button x:Name="PART_ApplyButton" 
                                    Style="{DynamicResource FilterButtonStyle}" />
                        </StackPanel>
                    </Grid>
                </ControlTemplate>
            </Setter.Value>
        </Setter>
    </Style>
</ResourceDictionary>
```

And in the Code-Behind we'll derive from a `BaseFilterControl<TFilterDescriptor>` to implement the Filter. 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Windows.Controls;
using WpfDataGridFilter.Models;
using WpfDataGridFilter.Translations;
using WpfDataGridFilter.Controls;

namespace WideWorldImporters.Desktop.Client.Controls
{
    public class GeoDistanceFilterControl : BaseFilterControl<GeoDistanceFilterDescriptor>
    {
        public static FilterType GeoDistanceFilterType = new FilterType { Name = "GeoDistanceFilter" };

        /// <summary>
        /// Supported Filters for this Filter Control.
        /// </summary>
        public static readonly List<FilterOperator> SupportedFilterOperators =
        [
            GeographyFilter.FilterOperators.DistanceLessThan,
            GeographyFilter.FilterOperators.DistanceLessEqualThan,
            GeographyFilter.FilterOperators.DistanceGreaterThan,
            GeographyFilter.FilterOperators.DistanceGreaterEqualThan,
        ];

        #region Controls 

        ComboBox? FilterOperatorsComboBox;
        TextBox? LatitudeTextBox;
        TextBox? LongitudeTextBox;
        TextBox? DistanceTextBox;

        #endregion Controls

        public override string PropertyName { get; set; } = string.Empty;

        public List<Translation<FilterOperator>> FilterOperators { get; private set; } = [];

        public override void OnApplyTemplate()
        {
            base.OnApplyTemplate();

            FilterOperatorsComboBox = GetTemplateChild("PART_FilterOperators") as ComboBox;
            LatitudeTextBox = GetTemplateChild("PART_LatitudeTextBox") as TextBox;
            LongitudeTextBox = GetTemplateChild("PART_LongitudeTextBox") as TextBox;
            DistanceTextBox = GetTemplateChild("PART_DistanceTextBox") as TextBox;

            // Translations for the Control
            FilterOperators = GetFilterOperatorTranslations(Translations, SupportedFilterOperators);

            if (FilterOperatorsComboBox != null)
            {
                FilterOperatorsComboBox.DisplayMemberPath = nameof(Translation<FilterOperator>.Text);
                FilterOperatorsComboBox.SelectedValuePath = nameof(Translation<FilterOperator>.Value);
                FilterOperatorsComboBox.ItemsSource = FilterOperators;
            }

            if (DataGridState != null)
            {
                OnDataGridStateChanged();
            }
        }

        protected override void OnDataGridStateChanged()
        {
            GeoDistanceFilterDescriptor filterDescriptor = GetFilterDescriptor(DataGridState, PropertyName);

            if (FilterOperatorsComboBox != null)
            {
                FilterOperatorsComboBox.SelectedValue = filterDescriptor.FilterOperator;
            }

            if (LatitudeTextBox != null)
            {
                LatitudeTextBox.Text = filterDescriptor.Latitude?.ToString();
            }

            if (LongitudeTextBox != null)
            {
                LongitudeTextBox.Text = filterDescriptor.Longitude?.ToString();
            }
        }

        protected override void OnApplyFilter()
        {
            // Nothing to do...
        }

        protected override void OnResetFilter()
        {
            // Nothing to do...
        }

        protected override GeoDistanceFilterDescriptor GetDefaultFilterDescriptor()
        {
            return new GeoDistanceFilterDescriptor
            {
                PropertyName = PropertyName,
                FilterOperator = FilterOperator.None,
            };
        }

        protected override FilterDescriptor GetFilterDescriptor()
        {
            return new GeoDistanceFilterDescriptor
            {
                PropertyName = PropertyName,
                FilterOperator = GetCurrentFilterOperator(),
                Latitude = GetDoubleValue(LatitudeTextBox?.Text),
                Longitude = GetDoubleValue(LongitudeTextBox?.Text),
                Distance = GetDoubleValue(DistanceTextBox?.Text),
            };
        }

        private double? GetDoubleValue(string? value)
        {
            if (!double.TryParse(value, out double result))
            {
                return null;
            }

            return result;
        }

        private FilterOperator GetCurrentFilterOperator()
        {
            if (FilterOperatorsComboBox == null)
            {
                return FilterOperator.None;
            }

            if (FilterOperatorsComboBox.SelectedValue == null)
            {
                return FilterOperator.None;
            }

            FilterOperator currentFilterOperator = (FilterOperator)FilterOperatorsComboBox.SelectedValue;

            return currentFilterOperator;
        }

        protected override List<Translation<FilterOperator>> GetAdditionalTranslations()
        {
            return GeographyFilter.Translations.FilterOperatorTranslations;
        }
    }
}
```

### Connecting all things in the ViewModel ###

Filter Controls are created by an `IFilterControlProvider` by the [WpfDataGridFilter] library. The `WpfDataGridFilter.DynamicLinq` 
plugin resolves the `IFilterTranslator` by using a `IFilterTranslatorProvider`. So we add a Method `MainWindowViewModel#GetCustomProviders()`, 
that creates the two providers.

```csharp
public partial class MainWindowViewModel : ObservableObject
{
    [ObservableProperty]
    private IFilterControlProvider _filterControlProvider;

    [ObservableProperty]
    private IFilterTranslatorProvider _filterTranslatorProvider;

    // ...

    public MainWindowViewModel(DataGridState dataGridState)
    {
        // ...
        
        // Create a Custom Filter Provider, which is able to resolve 
        (FilterControlProvider, FilterTranslatorProvider) = GetCustomProviders();

        // ...
    }
    
    public static (IFilterControlProvider, IFilterTranslatorProvider)  GetCustomProviders()
    {
        // Build default Providers
        (FilterControlProvider filterControlProvider, FilterTranslatorProvider filterTranslatorProvider) = 
            (new FilterControlProvider(), new FilterTranslatorProvider());

        // Register custom hooks
        filterControlProvider
            .AddOrReplace(GeographyFilter.GeoDistanceFilterType, () => new GeoDistanceFilterControl());

        filterTranslatorProvider
            .AddOrReplace(new GeoDistanceFilterTranslator());

        return (filterControlProvider, filterTranslatorProvider);
    }
}
```

In the `MainWindow.xaml` we pass the custom `IFilterControlProvider` to the `FilterableColumnHeader` by using the `FilterControlProvider` property:

```xml
<Window x:Name="MainWindowRoot">
    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="*" />
            <RowDefinition Height="Auto" />
        </Grid.RowDefinitions>
        <DataGrid ItemsSource="{Binding ViewModel.Customers}" AutoGenerateColumns="False" CanUserSortColumns="False" MinColumnWidth="150">
            <DataGrid.Columns>
                <DataGridTextColumn Binding="{Binding DeliveryLocation, Converter={StaticResource GeographyPointConverter}}">
                    <DataGridTextColumn.HeaderTemplate>
                        <DataTemplate>
                            <wpfdatagridfilter:FilterableColumnHeader DataGridState="..." FilterControlProvider="{Binding ViewModel.FilterControlProvider, ElementName=MainWindowRoot}" ... />
                        </DataTemplate>
                    </DataGridTextColumn.HeaderTemplate>
                </DataGridTextColumn>
            </DataGrid.Columns>
        </DataGrid>
    </Grid>
</Window>
```

What's left is passing the custom `FilterTranslatorProvider` to the `WpfDataGridFilter.DynamicLinq` libraries `IQueryable#ApplyDataGridState` 
extension method. 

```csharp
public partial class MainWindowViewModel : ObservableObject
{
    // ...
    
    public async Task RefreshAsync()
    {
        // ...

        DataServiceQuery<Customer> dataServiceQuery = (DataServiceQuery<Customer>)Container.Customers
            .IncludeCount()
            .Expand(x => x.LastEditedByNavigation)
            .ApplyDataGridState(DataGridState, FilterTranslatorProvider);
            
        // ...
    }
```

And we are done!

## Conclusion ##

I think we're off to a good start, because we are able to add our custom Filter Controls. 

As of now the API requires quite a lot in-depth knowledge about the library. The XAML Styling should also 
be *a lot simpler* and not require us to use the exact `PART` names to apply the Button actions.

Anyways. It's important to **start with something**, instead of starting with nothing.