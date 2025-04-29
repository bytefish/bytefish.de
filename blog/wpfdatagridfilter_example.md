title: An Example on using WpfDataGridFilter in an OData Service
date: 2025-04-26 23:26
tags: csharp, dotnet, wpf
category: wpf
slug: wpfdatagridfilter_example
author: Philipp Wagner
summary: Implementing a Library for Server-side Pagination, Sorting and Filtering with a WPF DataGrid.

[WpfDataGridFilter]: https://github.com/bytefish/WpfDataGridFilter
[WideWorldImporters]: https://github.com/bytefish/WideWorldImporters

In this example we'll take a look at [WpfDataGridFilter], which is a small library to simplify 
sever-side filtering in a WPF application. We will see how to use it for the [WideWorldImporters] 
backend, which is my current playground to base tutorials on.

All code can be found in a Git repository at:

* [https://github.com/bytefish/WideWorldImporters](https://github.com/bytefish/WideWorldImporters)

## What we are going to build ##

We are going to build a small WPF application, that shows the list of Customers available in the 
WideWorldImporters database, and allow you to filter through data exposed by an OData Service 
using the [WpfDataGridFilter] library.

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/wpfdatagridfilter_example/wwi-wpf-app.jpg">
        <img src="/static/images/blog/wpfdatagridfilter_example/wwi-wpf-app.jpg" alt="WPF OData Example">
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

Let's take a look at how the application is built.

### Generate the OData Client using the OData Connected Services 2022+ Extension ###

We start by installing the OData Connected Services 2022+ Visual Studio Extension:

* [https://marketplace.visualstudio.com/items?itemName=marketplace.ODataConnectedService2022](https://marketplace.visualstudio.com/items?itemName=marketplace.ODataConnectedService2022)

Now right click on the Project and navigate to `Add -> Connected Service`:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/wpfdatagridfilter_example/wwi-add-service-reference.jpg">
        <img src="/static/images/blog/wpfdatagridfilter_example/wwi-add-service-reference.jpg" alt="WPF OData Example Add Connected Service">
    </a>
</div>

Adding the Service Reference requires us to point to the OData endpoint, which is `https://localhost:5000/odata` in our example:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/wpfdatagridfilter_example/wwi-add-service-reference-configure-endpoint.jpg">
        <img src="/static/images/blog/wpfdatagridfilter_example/wwi-add-service-reference-configure-endpoint.jpg" alt="WPF OData Example Configure Endpoints">
    </a>
</div>

There's nothing we'll need to configure, because we want to include all classes exposed by the OData Service. Just click on 
the `Finish` button. The extension now generates a Service Client and all model classes:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/wpfdatagridfilter_example/wwi-add-service-reference-generated-service-client.jpg">
        <img src="/static/images/blog/wpfdatagridfilter_example/wwi-add-service-reference-generated-service-client.jpg" alt="WPF OData Generated Service Client">
    </a>
</div>

We now have a fully functional client to query our OData endpoints.

### Adding the WpfDataGridFilter NuGet packages ###

Let's get to the reason I am writing this article for: [WpfDataGridFilter].

We'll need to add the `WpfDataGridFilter` NuGet package, which contains the WPF Controls we are going to use in our application:

```
dotnet package add WpfDataGridFilter
```

The `WpfDataGridFilter.DynamicLinq` package is used, so our filtering can be applied to an `IQueryable`: 

```
dotnet package add WpfDataGridFilter.DynamicLinq
```

### Building the basic MVVM Setup using the Community Toolkit ###

We want to develop a MVVM application, and the CommunityToolkit simplified building MVVM applications 
a lot. We add it by running:

```
dotnet package add CommunityToolkit.Mvvm
```

The `MainWindowViewModel` for the application then derives from an `ObservableObject` and provides 
methods being executed, when the View is loaded or unloaded. This is useful to register or unregister 
Event Handlers:

```csharp
// ...

namespace WideWorldImporters.Desktop.Client.ViewModels;

public partial class MainWindowViewModel : ObservableObject
{
    public void OnLoaded()
    {
        // Run Code when the View has been loaded ...
    }

    public void OnUnloaded()
    {
        // Run Code when the View is being unloaded ...
    }
}
```

In the Code-Behind we are instantiating the ViewModel with an empty `DataGridState` and implement two 
Event Handlers to be used for the Loaded and Unloaded Events.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using WideWorldImporters.Desktop.Client.ViewModels;
using WpfDataGridFilter;

namespace WideWorldImporters.Desktop.Client;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : Window
{
    public MainWindowViewModel ViewModel { get; set; }

    public MainWindow()
    {
        ViewModel = new MainWindowViewModel(new DataGridState([]));
        DataContext = this;

        InitializeComponent();
    }

    private void Window_Loaded(object sender, RoutedEventArgs e)
    {
        ViewModel.OnLoaded();
    }

    private void Window_Unloaded(object sender, RoutedEventArgs e)
    {
        ViewModel.OnUnloaded();
    }
}
```

### Building the ViewModel (Getting the Data) ###

I think it's hard to describe the iterative process, when connecting the View and ViewModel. I often have a vague idea of 
what to show in the UI and then start on the `ViewModel` side, to get a *feeling* for loading the data. Let's see how to 
do it for the [WpfDataGridFilter] example.

You need to understand the notion of the `DataGridState`, that comes with the library. The `DataGridState` basically holds 
the filters, the sort column, and the number of elements to skip and take (for pagination). The `DataGridState` fires a 
`DataGridStateChangedEvent`, whenever its state has been changed, so all subscribers can react on it (to reload data 
for example).

The most important part is the `MainWindowViewModel#RefreshAsync` method. It uses the `DataGridState#ApplyDataGridState` extension 
methods on the `DataServiceQuery`, created by the generated OData Client. The method is available in the `WpfDataGridFilter.DynamicLinq` 
package:

```csharp
// ...

DataServiceQuery<Customer> dataServiceQuery = (DataServiceQuery<Customer>)Container.Customers
    .IncludeCount()
    .Expand(x => x.LastEditedByNavigation)
    .ApplyDataGridState(DataGridState);

// ...
```

You can also see, that I am including the total count, so we can populate the paginator accordingly. We want to 
query the name of the person, who last edited the entity. So we expand the required Navigation Property to load 
the related data.

And yes, that's enough to get the data and apply the filters. The rest is some infrastructure code for adding the 
pagination and making it a little more robust, if requested data exceeds the bounds.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.OData.Client;
using System.Collections.ObjectModel;
using WideWorldImportersService;
using WpfDataGridFilter;
using WpfDataGridFilter.DynamicLinq;

namespace WideWorldImporters.Desktop.Client.ViewModels;

public partial class MainWindowViewModel : ObservableObject
{
    [ObservableProperty]
    private ObservableCollection<Customer> _customers;

    [ObservableProperty]
    private DataGridState _dataGridState;

    [ObservableProperty]
    public int _currentPage = 1;

    public int LastPage => ((TotalItemCount - 1) / PageSize) + 1;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(LastPage))]
    private int _totalItemCount;

    [ObservableProperty]
    private List<int> _pageSizes = new() { 10, 25, 50, 100, 250 };

    private int _pageSize = 25;

    public int PageSize
    {
        get => _pageSize;
        set
        {
            if (SetProperty(ref _pageSize, value))
            {
                // We could also calculate the page, that contains 
                // the current element, but it's better to just set 
                // it to 1 I think.
                CurrentPage = 1;

                // The Last Page has changed, so we can update the 
                // UI. The Last Page is also used to determine the 
                // bounds.
                OnPropertyChanged(nameof(LastPage));

                // Update the Page.
                SetSkipTop();
            }
        }
    }

    public IRelayCommand FirstPageCommand { get; }

    public IRelayCommand PreviousPageCommand { get; }

    public IRelayCommand NextPageCommand { get; }

    public IRelayCommand LastPageCommand { get; }

    public IAsyncRelayCommand RefreshDataCommand { get; }

    public Container Container;

    public void OnLoaded()
    {
        DataGridState.DataGridStateChanged += DataGridState_DataGridStateChanged;

        SetSkipTop();
    }

    public void OnUnloaded()
    {
        DataGridState.DataGridStateChanged -= DataGridState_DataGridStateChanged;
    }

    private void DataGridState_DataGridStateChanged(object? sender, DataGridStateChangedEventArgs e)
    {
        RefreshDataCommand.Execute(null);
    }

    public MainWindowViewModel(DataGridState dataGridState)
    {
        // Creates a new WideWorldImporters Container to query the Service
        Container = new Container(new Uri("https://localhost:5000/odata"));
        
        // Holds the DataGridState for the Displayed DataGrid
        DataGridState = dataGridState;
        
        // Customers
        Customers = new ObservableCollection<Customer>([]);

        FirstPageCommand = new RelayCommand(() =>
        {
            CurrentPage = 1;
            SetSkipTop();
        },
        () => CurrentPage != 1);

        PreviousPageCommand = new RelayCommand(() =>
        {
            CurrentPage = CurrentPage - 1;
            SetSkipTop();
        },
        () => CurrentPage > 1);

        NextPageCommand = new RelayCommand(() =>
        {
            CurrentPage = CurrentPage + 1;
            SetSkipTop();
        },
        () => CurrentPage < LastPage);

        LastPageCommand = new RelayCommand(() =>
        {
            CurrentPage = LastPage;
            SetSkipTop();
        },
        () => CurrentPage != LastPage);

        RefreshDataCommand = new AsyncRelayCommand(
            execute: () => RefreshAsync(),
            canExecute: () => true);
    }

    public void SetSkipTop()
    {
        DataGridState.SetSkipTop((CurrentPage - 1) * PageSize, PageSize);
    }

    public async Task RefreshAsync()
    {
        // If there's no Page Size, we don't need to load anything.
        if (PageSize == 0)
        {
            return;
        }

        DataServiceQuery<Customer> dataServiceQuery = (DataServiceQuery<Customer>)Container.Customers
            .IncludeCount()
            .Expand(x => x.LastEditedByNavigation)
            .ApplyDataGridState(DataGridState);

        // Gets the Response and Data, as can be seen in the Query, we are also including the Count, so we don't run 
        // dozens of queries. We could also try to use the pagination functions of OData I guess.
        QueryOperationResponse<Customer> response = (QueryOperationResponse<Customer>)await dataServiceQuery.ExecuteAsync();

        // Get the Total Count, so we can update the First and Last Page.
        TotalItemCount = (int) response.Count;

        // If our current page is beyond the last Page, we'll need to rerequest data. It often means, that we didn't receive 
        // any data yet, so it shouldn't be too expensive to re-request everything again.
        if (CurrentPage > 0 && CurrentPage > LastPage)
        {
            // If the number of items has reduced such that the current page index is no longer valid, move
            // automatically to the final valid page index and trigger a further data load.
            CurrentPage = LastPage;

            SetSkipTop();

            return;
        }

        // Notify all Event Handlers, so we can enable or disable the 
        FirstPageCommand.NotifyCanExecuteChanged();
        PreviousPageCommand.NotifyCanExecuteChanged();
        NextPageCommand.NotifyCanExecuteChanged();
        LastPageCommand.NotifyCanExecuteChanged();

        IEnumerable<Customer> filteredResult = await dataServiceQuery.ExecuteAsync();

        Customers = new ObservableCollection<Customer>(filteredResult);
    }
}
```

### Adding the WpfDataGridFilter Styles to your WPF application ###

In the `App.xaml` you start by adding the `WpfDataGridFilter` styles to your application. I have tried my best to make 
the components as configurable as possible, so it should be easy to adjust the styles to your needs:

```xml
<Application>
    <Application.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ResourceDictionary Source="pack://application:,,,/WpfDataGridFilter;component/WpfDataGridFilter.xaml" />
                <ResourceDictionary Source="pack://application:,,,/WpfDataGridFilter;component/Theme/Light.xaml" />
            </ResourceDictionary.MergedDictionaries>
        </ResourceDictionary>
    </Application.Resources>
</Application>
```

### Using the FilterableColumnHeader in your WPF application ###

And finally you can see how the `FilterableColumnHeader` is used for the DataGrids `HeaderTemplate`. Please note, 
that we had to reference the Window as the Binding Context, so it resolves to the ViewModel correctly.

```xml
<Window
    x:Class="WideWorldImporters.Desktop.Client.MainWindow"
    x:Name="MainWindowRoot"
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" 
    xmlns:wpfdatagridfilter="clr-namespace:WpfDataGridFilter.Controls;assembly=WpfDataGridFilter"
    Title="WPF OData Example"
    Width="1100"
    Height="650"
    d:DesignHeight="800"
    d:DesignWidth="1200"
    WindowStartupLocation="CenterScreen"
    mc:Ignorable="d"
    Loaded="Window_Loaded"
    Unloaded="Window_Unloaded">
    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="*" />
            <RowDefinition Height="Auto" />
        </Grid.RowDefinitions>
        <DataGrid ItemsSource="{Binding ViewModel.Customers}" AutoGenerateColumns="False" CanUserSortColumns="False" MinColumnWidth="150">
            <DataGrid.Columns>
                <DataGridTextColumn Binding="{Binding CustomerId}">
                    <DataGridTextColumn.HeaderTemplate>
                        <DataTemplate>
                            <wpfdatagridfilter:FilterableColumnHeader DataGridState="{Binding ViewModel.DataGridState, ElementName=MainWindowRoot}" HeaderText="CustomerId" PropertyName="CustomerId" Height="40" MinWidth="150" FilterType="IntNumericFilter"></wpfdatagridfilter:FilterableColumnHeader>
                        </DataTemplate>
                    </DataGridTextColumn.HeaderTemplate>
                </DataGridTextColumn>
                <DataGridTextColumn Binding="{Binding CustomerName}">
                    <DataGridTextColumn.HeaderTemplate>
                        <DataTemplate>
                            <wpfdatagridfilter:FilterableColumnHeader DataGridState="{Binding ViewModel.DataGridState, ElementName=MainWindowRoot}" HeaderText="CustomerName" PropertyName="CustomerName" Height="40" MinWidth="150" FilterType="StringFilter"></wpfdatagridfilter:FilterableColumnHeader>
                        </DataTemplate>
                    </DataGridTextColumn.HeaderTemplate>
                </DataGridTextColumn>
                <DataGridTextColumn Binding="{Binding LastEditedByNavigation.FullName}">
                    <DataGridTextColumn.HeaderTemplate>
                        <DataTemplate>
                            <wpfdatagridfilter:FilterableColumnHeader DataGridState="{Binding ViewModel.DataGridState, ElementName=MainWindowRoot}" HeaderText="LastEditedBy" PropertyName="LastEditedByNavigation.FullName" Height="40" MinWidth="150" FilterType="StringFilter"></wpfdatagridfilter:FilterableColumnHeader>
                        </DataTemplate>
                    </DataGridTextColumn.HeaderTemplate>
                </DataGridTextColumn>
            </DataGrid.Columns>
        </DataGrid>
        <Grid Grid.Row="1" Margin="10">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*" />
            </Grid.ColumnDefinitions>

            <wpfdatagridfilter:PaginationControl 
                Grid.Column="0"
                HorizontalAlignment="Center"
                SelectedPageSize="{Binding ViewModel.PageSize, Mode=TwoWay}"
                PageSizes="{Binding ViewModel.PageSizes}"
                CurrentPage="{Binding ViewModel.CurrentPage}"
                FirstPage="{Binding ViewModel.FirstPageCommand}"
                PreviousPage="{Binding ViewModel.PreviousPageCommand}"
                NextPage="{Binding ViewModel.NextPageCommand}"
                LastPage="{Binding ViewModel.LastPageCommand}" />

            <TextBlock Width="150" Grid.Column="0"  HorizontalAlignment="Right">
                <Run Text="Page" />
                <Run Text="{Binding ViewModel.CurrentPage, Mode=OneWay}" d:Text="0" />
                <Run Text="/" />
                <Run Text="{Binding ViewModel.LastPage, Mode=OneWay}" d:Text="0" />
                <LineBreak />
                <Run Text="Number of Elements:"></Run>
                <Run Text="{Binding ViewModel.TotalItemCount, Mode=OneWay}" d:Text="1020" />
            </TextBlock>
        </Grid>
    </Grid>
</Window>
```

## Conclusion ##

So, that's [WpfDataGridFilter]!

The library is still in early stages, but I am quite happy with the results. It's makes it 
super easy to query data from everything, that exposes an `IQueryable`. So everything also 
works with EntityFramework Core.