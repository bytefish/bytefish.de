title: Airline On-Time Performance
date: 2018-01-01 10:24
tags: csharp, sql, datamining
category: datamining
slug: airline_on_time_performance
author: Philipp Wagner
summary: This Article is an introduction for importing the Airline On-Time Performance Dataset into an SQL Server instance.

At the moment I am working myself into Data Mining, Reporting and Business Intelligence again. I want to learn it at a 
larger scale so I know about the pitfalls of various solutions. Because something that works on small datasets may fail 
horribly as soon as your system ingests large amounts of data.

The first step is to gather data to work with and import it into the Microsoft SQL Server. In this repository I am showing 
how to do it for the [Airline On-Time Performance Dataset], which contains more than 150 million flight statistic items to 
work with. 

The Repository for importing the [Airline On-Time Performance Dataset] into an SQL Server can be found at:

* [https://codeberg.org/bytefish/AirlineOnTimePerformance](https://codeberg.org/bytefish/AirlineOnTimePerformance)

## Dataset ##

The [Airline On-Time Performance Dataset] contains:

> [...] on-time arrival data for non-stop domestic flights by major air carriers, and provides such additional 
> items as departure and arrival delays, origin and destination airports, flight numbers, scheduled and actual departure 
> and arrival times, cancelled or diverted flights, taxi-out and taxi-in times, air time, and non-stop distance.

The [Airline On-Time Performance Dataset] spans a time range from October 1987 to November 2017, and it contains more than 
150 million rows of flight informations. It can be obtained as CSV files from the Bureau of Transportation Statistics Database, 
and requires you to download the data month by month. More conveniently the [Revolution Analytics dataset repository] contains 
a ZIP File with the CSV data from 1987 to 2012.

## Additional Information ##

* [Airline On-Time Performance Dataset](https://www.transtats.bts.gov/Tables.asp?DB_ID=120&DB_Name=Airline%20On-Time%20Performance%20Data&DB_Short_Name=On-Time)
* [Revolution Analytics dataset repository](https://packages.revolutionanalytics.com/datasets/AirOnTime87to12/)
* [Combine ScaleR and SparkR in HDInsight](https://docs.microsoft.com/en-us/azure/hdinsight/hdinsight-hadoop-r-scaler-sparkr)

[Revolution Analytics dataset repository]: https://packages.revolutionanalytics.com/datasets/AirOnTime87to12/
[TinyCsvParser]: https://codeberg.org/bytefish/TinyCsvParser
[Reactive Extensions]: https://github.com/Reactive-Extensions/Rx.NET
[Airline On-Time Performance Dataset]: https://www.transtats.bts.gov/Tables.asp?DB_ID=120&DB_Name=Airline%20On-Time%20Performance%20Data&DB_Short_Name=On-Time
