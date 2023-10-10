title: Anomaly Detection with SQL and R
date: 2017-11-18 09:03
tags: r, statistics
category: statistics
slug: anomaly_detection_with_r
author: Philipp Wagner
summary: This article shows how to do Anomaly Detection with R.

[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd
[AnomalyDetection]: https://github.com/twitter/AnomalyDetection

I am currently writing a blog post on Column Store Indices with SQL Server 2016. In the upcoming article 
I will show how to query and evaluate a large dataset with SQL Server and how to use Row Store and Column 
Store Indices for speeding up queries.

You can see the work in progress here:

* [https://github.com/bytefish/WeatherDataColumnStore/](https://github.com/bytefish/WeatherDataColumnStore/)

## About the Dataset ##

The dataset is the [Quality Controlled Local Climatological Data (QCLCD)] for 2014 and 2015. It contains hourly weather 
measurements for more than 1,600 US Weather Stations. It is a great dataset to learn about data processing and data 
visualization:

> The Quality Controlled Local Climatological Data (QCLCD) consist of hourly, daily, and monthly summaries for approximately 
> 1,600 U.S. locations. Daily Summary forms are not available for all stations. Data are available beginning January 1, 2005 
> and continue to the present. Please note, there may be a 48-hour lag in the availability of the most recent data.

The data is available as CSV files at:

* [http://www.ncdc.noaa.gov/orders/qclcd/](http://www.ncdc.noaa.gov/orders/qclcd/)

## Anomaly Detection ##

Now real life data is never perfect and the weather data is no exception. Devices can break. Sensors can fail and report wrong 
values. Networks can be down. 

So in real datasets you often have to deal with missing measurements and other anomalies. And this is what this post is about: Anomaly Detection.

> In data mining, anomaly detection (also outlier detection) is the identification of items, events or observations which do not 
> conform to an expected pattern or other items in a dataset. Typically the anomalous items will translate to some kind of problem 
> such as bank fraud, a structural defect, medical problems or errors in a text. 
> 
> Anomalies are also referred to as outliers, novelties, noise, deviations and exceptions. ([Wikipedia](https://en.wikipedia.org/wiki/Anomaly_detection))

## The Anomaly: The coldest day in Texas ##

In the process of writing the blog post I wanted to make up some interesting queries. 

As an example I wanted to determine the coldest day in Texas, which translates to the following SQL Query:

```sql
DECLARE @StateName NVARCHAR(255)  = 'TX';

WITH StationsInState AS (
	SELECT [WBAN], [Name], [State], [Location], [Latitude], [Longitude]
	FROM [LocalWeatherDatabase].[sample].[Station]
	WHERE State = @StateName
)
SELECT TOP 1 s.*, d.Timestamp, d.Temperature
FROM StationsInState s
	INNER JOIN [sample].[LocalWeatherData] d ON s.WBAN = d.WBAN
WHERE Temperature IS NOT NULL
ORDER BY Temperature ASC
```

Surprisingly the SQL Query returns ``-43 °C`` for Port Isabel on the 15th September of 2015:

```
WBAN   Name           State       Location                      Latitude    Longitude    Timestamp                      Temperature
12957  PORT ISABEL    TX	      PORT ISABEL-CAMERON CO APT    26.16583    -97.34583    2015-09-15 02:53:00.0000000    -43.3
```

``-43 °C`` on a September day in Texas looks suspiciously like an outlier. This is most probably a measurement error.

## Visualizing the Temperature with R ##

[infuser]: https://github.com/Bart6114/infuser
[RODBC]: https://cran.r-project.org/web/packages/RODBC/index.html
[ggplot2]: http://ggplot2.org/

I have been doing quite a lot of data mining in a previous life. So all this makes a good excuse to work with R again.

> R is an open source programming language and software environment for statistical computing and graphics that is supported 
> by the R Foundation for Statistical Computing. The R language is widely used among statisticians and data miners for 
> developing statistical software and data analysis. ([Wikipedia](https://en.wikipedia.org/wiki/R_(programming_language)))

And before digging deeper it is useful to get an overview about the temperature in September 2015 for the Station ``12957``. 

### The Plan ###

The basic idea is to write an SQL query for selecting the weather data, use [RODBC] for connecting to the database, 
[infuser] for building the query and [ggplot2] for plotting the timeseries. The basic plot will show what the data 
in question looks like.

### SQL Query Template ###

I am only interested in the temperature for a full hour, so I am removing the minute part of the timestamp. There 
are probably multiple measurements in an hour, so the second Common Table Expression (``DistinctSeries``) is grouping the 
measurements by hour and calculates the average temperature for each full hour:

```sql
WITH BoundedTimeSeries as (
	SELECT dateadd(hour, datediff(hour, 0, Timestamp), 0) as Timestamp, Temperature
	FROM [sample].[LocalWeatherData] weatherData
	WHERE WBAN = '{{wban}}' AND Timestamp BETWEEN '{{start_date}}' and '{{end_date}}'
),
DistinctSeries as (
	SELECT Timestamp, AVG(Temperature) as Temperature
	FROM BoundedTimeSeries b
	GROUP BY Timestamp
)
SELECT d.Timestamp as timestamp, d.Temperature as temperature
FROM DistinctSeries d
WHERE Temperature is not null
ORDER BY Timestamp ASC
```

### Plotting the Temperature in September 2015 ###

The SQL query can now be used to query the temperature for a given weather station (``wban``) and a time range (``start_date`` and ``end_date``):

```r
library(RODBC)
library(dplyr)
library(infuser)
library(readr)
library(magrittr)
library(ggplot2)

# Connection String for the SQL Server Instance:
connectionString <- "Driver=SQL Server;Server=.;Database=LocalWeatherDatabase;Trusted_Connection=Yes"

# Connect to the Database:
connection <- odbcDriverConnect(connectionString)

# Read the SQL Query from an external file and infuse the variables. Keeps the Script clean:
query <- read_file("D:\\github\\WeatherDataColumnStore\\WeatherDataColumnStore\\R\\anomaly\\query.sql") %>% infuse(wban = "12957", start_date="2015-09-01 00:00:00.000", end_date="2015-09-30  23:59:59.997", simple_character = TRUE) 

# Query the Database: 
ts_temp <- sqlQuery(connection, query)

# Close ODBC Connection:
odbcClose(connection)

temperature_september <- ggplot(ts_temp, aes(timestamp, temperature)) + 
    geom_line(na.rm=TRUE) +  
	geom_smooth(size = 1, se=FALSE) +
    ggtitle("Temperature September 2015") +
    xlab("Timestamp") + 
	ylab("Temperature (C)") + 
    theme_bw() +
    theme(plot.title = element_text(hjust = 0.5))

temperature_september
```

And looking at the plot, we can see that the temperature really is an outlier (click for full size):

<a href="/static/images/blog/anomaly_detection_with_r/temperature_september_2015.png">
	<img src="/static/images/blog/anomaly_detection_with_r/temperature_september_2015.png" alt="September 2015 Temperature" />
</a>

## Anomaly Detection with the Twitter AnomalyDetection library ##

[AnomalyDetection]: https://github.com/twitter/AnomalyDetection

All this is interesting, but how could we detect such outliers automatically? 

I decided to use the [AnomalyDetection] library built by Twitter:

* [https://github.com/twitter/AnomalyDetection](https://github.com/twitter/AnomalyDetection)

It is described as:

> AnomalyDetection is an open-source R package to detect anomalies which is robust, from a statistical standpoint, in the presence 
> of seasonality and an underlying trend. The AnomalyDetection package can be used in wide variety of contexts. For example, detecting 
> anomalies in system metrics after a new software release, user engagement post an A/B test, or for problems in econometrics, 
> financial engineering, political and social sciences.

The [AnomalyDetection] library can be installed from the R Console with:

```r
install.packages("devtools")
devtools::install_github("twitter/AnomalyDetection")
library(AnomalyDetection)
```

### Finding the Anomalies in the Weather Data ###

With the SQL Query defined above and [RODBC] it is easy to query all data from 2014 and 2015.
 
The data in ``ts_temp`` is bound to the full hour of a measurement, but the timeseries still contains missing values! 

So in order to find the timestamps with missing values, I am first defining a dense time series ``ts_dense``. It includes all timestamps, 
that we expect the measurements at. Then by left joining the dense series and the bounded series on the timestamp, we are creating a new 
timeseries ``ts_merged``. ``ts_merged`` is now a dense timeseries, where timestamps with missing values have an ``NA`` value.

These measurements have to be interpolated for the anomaly detection. In the example I am simply using the ``zoo`` library for interpolation.

And finally the ``AnomalyDetectionVec`` function can be executed with the interpolated values and a period of ``8760``, which represents the hours in a year:

```r
library(RODBC)
library(dplyr)
library(infuser)
library(readr)
library(magrittr)
library(ggplot2)
library(zoo)
library(AnomalyDetection)

# Connection String for the SQL Server Instance:
connectionString <- "Driver=SQL Server;Server=.;Database=LocalWeatherDatabase;Trusted_Connection=Yes"

# Connect to the Database:
connection <- odbcDriverConnect(connectionString)

# Read the SQL Query from an external file and infuse the variables. Keeps the Script clean:
query <- read_file("D:\\github\\WeatherDataColumnStore\\WeatherDataColumnStore\\R\\anomaly\\query.sql") %>% infuse(wban = "12957", start_date="2014-01-01 00:00:00.000", end_date="2016-07-01 23:59:59.997", simple_character = TRUE) 

# Query the Database: 
ts_temp <- sqlQuery(connection, query)

# Close ODBC Connection:
odbcClose(connection)

# Build a dense timeseries with all expected timestamps:
ts_dense <- data.frame(timestamp=seq(as.POSIXct("2014-01-01"), as.POSIXct("2015-12-31"), by="hour"))

# Build the Dense series by left joining both series:
ts_merged <- left_join(ts_dense, ts_temp, by = c("timestamp" = "timestamp"))

# Use zoo to interpolate missing values:
ts_merged$interpolated_temperature <- na.approx(ts_merged$temperature)

# Detect Anomalies:
res = AnomalyDetectionVec(ts_merged$interpolated_temperature, direction='both', period=8760, plot=TRUE)

# Display the Anomalies:
res$anoms

# Plot the Anomalies:
res$plot
```

### Results ###

We can see, that the [AnomalyDetection] library has indeed identified the anomalies.

From the R Console we run:

```
> res$plot
``` 

<a href="/static/images/blog/anomaly_detection_with_r/anomalies.png">
	<img src="/static/images/blog/anomaly_detection_with_r/anomalies_thumb.png" alt="Anomalies for 2015" />
</a>

And we can see, that only the extreme outliers are identified:

```
> res$anoms
   index     anoms
1  29137 -38.05000
2  29138 -41.10000
3  29139 -41.07917
4  29140 -41.05833
5  29141 -41.03750
6  29142 -41.01667
7  29143 -40.99583
8  29144 -40.97500
9  29145 -40.95417
10 29146 -40.93333
11 29147 -40.91250
12 29148 -40.89167
13 29149 -40.87083
14 29150 -40.85000
15 29151 -40.82917
16 29152 -40.80833
17 29153 -40.78750
18 29154 -40.76667
19 29155 -40.74583
20 29156 -40.72500
21 29157 -40.70417
22 29158 -40.68333
23 29159 -40.66250
24 29160 -40.64167
25 29161 -40.62083
26 29162 -40.60000
27 29163 -41.10000
28 29164 -43.30000
29 29165 -41.70000
```