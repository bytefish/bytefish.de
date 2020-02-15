title: Visualizing the COVID-19 dataset using Microsoft Excel 3D Maps
date: 2020-02-15 14:29
tags: csv, dotnet, csharp, datamining
category: covid-19
slug: covid_19_excel
author: Philipp Wagner
summary: Visualizing the COVID-19 dataset using Microsoft Excel 3D Maps

In my last post on [COVID-19] I have shown how to write the [John Hopkins University] dataset 
to a SQL Server database:

* [https://bytefish.de/blog/parsing_covid_19_data/](https://bytefish.de/blog/parsing_covid_19_data/)

This post shows how visualize the data using the 3D Map feature of Microsoft Excel.

## Visualizing the COVID-19 data using Excel ##

So it all starts with getting the data into an Excel Sheet. From the Ribbon Bar you select ...

* **Data -> Get Data -> From Database -> From SQL Server Database**

... like this.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/01_Excel_Get_SqlServer_Data.png">
        <img src="/static/images/blog/covid_19_excel/01_Excel_Get_SqlServer_Data.png">
    </a>
</div>

In the Dialog Box you then enter the Server and Database. We have used the database name 
**SampleDatabase** in my article on writing the dataset to the SQL Server.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/02_Enter_SqlServer_Connection_Details.png">
        <img src="/static/images/blog/covid_19_excel/02_Enter_SqlServer_Connection_Details.png">
    </a>
</div>

If you have successfully entered the connection details, then select the ``sample.Observation`` 
table and click the **Load** Button.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/03_Select_And_Load_Table.png">
        <img src="/static/images/blog/covid_19_excel/03_Select_And_Load_Table.png">
    </a>
</div>

Excel will then load the dataset into a new Sheet it calls **Sheet2** initially. The right hand 
pane will show you the number of rows loaded, and errors if any.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/04_Loaded_Data_In_Sheet2.png">
        <img src="/static/images/blog/covid_19_excel/04_Loaded_Data_In_Sheet2.png">
    </a>
</div>

Now from the Ribbon Bar you create a 3D Map by navigating to ...

* **Insert -> 3D Map -> Open 3D Maps**

... like this.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/05_Create_3D_Map.png">
        <img src="/static/images/blog/covid_19_excel/05_Create_3D_Map.png">
    </a>
</div>

Microsoft Excel will now automatically load the data from the Sheet into the 3D Map. On the 
right pane you can see, that it already correctly mapped the columns **Country**, **Lat**, 
**Lon** and **Province**. And some data points are already displayed in the map.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/06_Initial_3D_Map.png">
        <img src="/static/images/blog/covid_19_excel/06_Initial_3D_Map.png">
    </a>
</div>

Now let's configure the 3D Map to make use of the data! 

1. In the Ribbon Bar I first select **Flat Map** to get a 2D projection of the world.
2. In the **Data** section of **Layer 1** I change the visualization to Bubbles.
3. In the **Size** section of **Layer 1** I am adding **Deaths (Maximum)**, **Recovered (Maximum)** and **Confirmed (Maximum)**.
4. In the **Time** section I am configuring to use the **Timestamp** column.
5. In the **Layer Options** I am adjusting the color scales, so it better matches colors of official pages.

Once I am done, I am finally configuring the Tooltip to show useful data.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/07_Configured_Map.png">
        <img src="/static/images/blog/covid_19_excel/07_Configured_Map.png">
    </a>
</div>

If you now press **Play Tour** from the Ribbon Bar you can see how the distribution behaves over time. 

### Building a Heat Map ###

In the final example, I am changing the visualization to a Heat Map. Using the filters section I am exluding the 
Hubei province, else it will dominate the visualization. As Value for the Heat Map I have selected the Number of 
Confirmed Cases.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/covid_19_excel/08_Heatmap_Confirmed_Excluding_Hubei.png">
        <img src="/static/images/blog/covid_19_excel/08_Heatmap_Confirmed_Excluding_Hubei.png">
    </a>
</div>

Using a Heat Map we can quickly identify the currently most impacted regions.

## Conclusion ##

Microsoft Excel makes it easy to build simple visualizations of the [COVID-19] dataset, without putting 
any energy into programming or data shaping. You can jump through any point in time using the 3D Map time 
slicer and run a tour, to see how the distribution evolves.

[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[John Hopkins University]: [https://systems.jhu.edu/]
[COVID-19]: https://en.wikipedia.org/wiki/2019-nCoV_acute_respiratory_disease