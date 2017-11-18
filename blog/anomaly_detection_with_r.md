title: Anomaly Detection with SQL and R
date: 2017-11-18 09:03
tags: r, statistics
category: statistics
slug: anomaly_detection_with_r
author: Philipp Wagner
summary: This article shows how to do Anomaly Detection with R.

[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd
[AnomalyDetection]: https://github.com/twitter/AnomalyDetection

I am currently working on a blog post for Column Store Indices with SQL Server 2016. In the upcoming article 
I will show how to query and evaluate a large datasets with SQL Server and how to use Row Store and Column 
Store Indices to speed up the performance.

You can see the work in progress here:

* [https://github.com/bytefish/WeatherDataColumnStore/](https://github.com/bytefish/WeatherDataColumnStore/)

In this post I want to show how to do Anomaly Detection using SQL and R:

> In data mining, anomaly detection (also outlier detection) is the identification of items, events or observations which do not 
> conform to an expected pattern or other items in a dataset. Typically the anomalous items will translate to some kind of problem 
> such as bank fraud, a structural defect, medical problems or errors in a text. 
> 
> Anomalies are also referred to as outliers, novelties, noise, deviations and exceptions.

## Dataset ##

The dataset is the [Quality Controlled Local Climatological Data (QCLCD)] for 2014 and 2015: 

> Quality Controlled Local Climatological Data (QCLCD) consist of hourly, daily, and monthly summaries for approximately 
> 1,600 U.S. locations. Daily Summary forms are not available for all stations. Data are available beginning January 1, 2005 
> and continue to the present. Please note, there may be a 48-hour lag in the availability of the most recent data.

The data is available as CSV files at:

* [http://www.ncdc.noaa.gov/orders/qclcd/](http://www.ncdc.noaa.gov/orders/qclcd/)

## Anomaly in the Data ##

In the process of writing the blog post I wanted to make up interesting queries. So as an example I wanted to determine the 
coldest place in Texas, which translates to the following SQL Query. I hope it is understandable without knowing the SQL Schema 
in detail:

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

Surprisingly the SQL Query returns ``-43 °C`` on the 15th September of 2015:

```
WBAN   Name           State       Location                      Latitude    Longitude    Timestamp                      Temperature
12957  PORT ISABEL    TX	      PORT ISABEL-CAMERON CO APT    26.16583    -97.34583    2015-09-15 02:53:00.0000000    -43.3
```

``-43 °C`` in Texas in September looks suspiciously like an outlier. It is most probably a measurement error.

## Visualizing the Temperature ##

[infuser]: https://github.com/Bart6114/infuser
[RODBC]: https://cran.r-project.org/web/packages/RODBC/index.html
[ggplot2]: http://ggplot2.org/

First of all I want to get an overview about the temperature in September 2015 for the Station ``12957``. 

The basic idea is to use an SQL query for selecting the relevant data, [RODBC] for connecting to the database, 
[infuser] for building the query and [ggplot2] for plotting the timeseries.

### SQL Query Template ###

So first of all I am building an SQL Query with template variables, which will be populated by the [infuser] library:

I am only interested in the average temperature for a given hour, so I am removing the minute part of the timestamp. There 
are probably multiple measurements in an hour, so in the second Common Table Expression (``DistinctSeries``) I am calculating 
the average temperature for an hour:

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

The SQL query can now be used to query the temperature for a given weather station (``wban``) and time range (``start_date`` and ``end_date``):

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

## Anomaly Detection with Twitters AnomalyDetection ##

[AnomalyDetection]: https://github.com/twitter/AnomalyDetection

So how could we detect such outliers automatically? I decided to use the [AnomalyDetection] library built by Twitter:

* [https://github.com/twitter/AnomalyDetection](https://github.com/twitter/AnomalyDetection)

It is described as:

> AnomalyDetection is an open-source R package to detect anomalies which is robust, from a statistical standpoint, in the presence 
> of seasonality and an underlying trend. The AnomalyDetection package can be used in wide variety of contexts. For example, detecting 
> anomalies in system metrics after a new software release, user engagement post an A/B test, or for problems in econometrics, 
> financial engineering, political and social sciences.

You can install the [AnomalyDetection] library from the R Console with:

```r
install.packages("devtools")
devtools::install_github("twitter/AnomalyDetection")
library(AnomalyDetection)
```

### Using Twitters AnomalyDetection ###

First of all we are gathering all data from the years 2014 and 2015 from the SQL Server using ``RODBC`` again. The data (``ts_bounded``) is bound to 
hourly measurements, but it still may have some missing data. So the next thing we do is to build a dense series (``ts_dense``) with the timestamps, 
that we expect a measurement at. Now by left joining the dense series and the bounded series we are getting a dense series (``ts_merged``), where 
missing timestamps have an ``NA`` value.

These ``NA`` values are the missing measurements, that have to be interpolated for the anomaly detection. I am using the ``zoo`` library to interpolate those values.

Finally the ``AnomalyDetectionVec`` can be executed with the interpolated timeseries and a period of ``8760`` (the hours in a year):

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

And we can see, that the [AnomalyDetection] library has indeed identified the anomalies.

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