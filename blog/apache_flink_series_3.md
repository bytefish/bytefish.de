title: Building Applications with Apache Flink (Part 3): Stream Processing with the DataStream API
date: 2016-07-03 16:38
tags: java, flink, elasticsearch, postgresql
category: java
slug: apache_flink_series_3
author: Philipp Wagner
summary: This article shows how to work with Apache Flink.

In the previous article we have written a [SourceFunction] to emit measurements from a CSV source file. In this article we are going to use the [SourceFunction] to serve a [DataStream]. 

## What we are going to build ##

You will see how to use the [DataStream] API for applying operators on the stream, so that for each station the maximum temperature for a day is identified.

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://github.com/bytefish/FlinkExperiments](https://github.com/bytefish/FlinkExperiments)

## DataStream API ##

The [DataStream] API of Apache Flink makes it possible to apply a various operations on a stream of incoming data.

The [Apache Flink] documentation describes a DataStream as:

> DataStream programs in Flink are regular programs that implement transformations on data streams (e.g., filtering, updating state, defining windows, aggregating). 
> The data streams are initially created from various sources (e.g., message queues, socket streams, files). Results are returned via sinks, which may for example 
> write the data to files, or to standard output (for example the command line terminal). Flink programs run in a variety of contexts, standalone, or embedded in 
> other programs. The execution can happen in a local JVM, or on clusters of many machines.

### Example Program: Maximum Air Temperature by station and day ###

In this example we are using the [SourceFunction] from the previous article to serve the [DataStream]. We are first setting the time characteristics of the 
[DataStream] to the EventTime, because each measurement carries the measurement timestamp. We are then building a [KeyedStream] over the [DataStream], which 
groups the incoming data by its station. And finally we use a non-overlapping tumbling window with 1 day length, from which the maximum temperature is used.

The results in this example are written to a Console, but in the next article you will learn how to write a custom [SinkFunction] to write the data 
into a PostgreSQL database for further data analysis.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package app;

import model.LocalWeatherData;
import org.apache.flink.api.common.functions.FilterFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.streaming.api.TimeCharacteristic;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.KeyedStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.timestamps.AscendingTimestampExtractor;
import org.apache.flink.streaming.api.windowing.time.Time;
import stream.sources.csv.LocalWeatherDataSourceFunction;
import utils.DateUtilities;

import stream.sources.csv.LocalWeatherDataSourceFunction;
import utils.DateUtilities;

public class WeatherDataStreamingExample {

    public static void main(String[] args) throws Exception {

        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Use the Measurement Timestamp of the Event:
        env.setStreamTimeCharacteristic(TimeCharacteristic.EventTime);

        // We are sequentially reading the historic data from a CSV file:
        env.setParallelism(1);

        // Path to read the CSV data from:
        final String csvStationDataFilePath = "C:\\Users\\philipp\\Downloads\\csv\\201503station.txt";
        final String csvLocalWeatherDataFilePath = "C:\\Users\\philipp\\Downloads\\csv\\201503hourly_sorted.txt";

        // Add the CSV Data Source and assign the Measurement Timestamp:
        DataStream<model.LocalWeatherData> localWeatherDataDataStream = env
                .addSource(new LocalWeatherDataSourceFunction(csvStationDataFilePath, csvLocalWeatherDataFilePath))
                .assignTimestampsAndWatermarks(new AscendingTimestampExtractor<LocalWeatherData>() {
                    @Override
                    public long extractAscendingTimestamp(LocalWeatherData localWeatherData) {
                        Date measurementTime = DateUtilities.from(localWeatherData.getDate(), localWeatherData.getTime(), ZoneOffset.ofHours(localWeatherData.getStation().getTimeZone()));

                        return measurementTime.getTime();
                    }
                });

        // First build a KeyedStream over the Data with LocalWeather:
        KeyedStream<LocalWeatherData, String> localWeatherDataByStation = localWeatherDataDataStream
                // Filte for Non-Null Temperature Values, because we might have missing data:
                .filter(new FilterFunction<LocalWeatherData>() {
                    @Override
                    public boolean filter(LocalWeatherData localWeatherData) throws Exception {
                        return localWeatherData.getTemperature() != null;
                    }
                })
                // Now create the keyed stream by the Station WBAN identifier:
                .keyBy(new KeySelector<LocalWeatherData, String>() {
                    @Override
                    public String getKey(LocalWeatherData localWeatherData) throws Exception {
                        return localWeatherData.getStation().getWban();
                    }
                });

        // Now take the Maximum Temperature per day from the KeyedStream:
        DataStream<LocalWeatherData> maxTemperaturePerDay =
                localWeatherDataByStation
                        // Use non-overlapping tumbling window with 1 day length:
                        .timeWindow(Time.days(1))
                        // And use the maximum temperature:
                        .maxBy("temperature");
						
        env.execute("Max Temperature By Day example");
    }
}
```

## Conclusion ##

In this part of the series you have seen how to use the [DataStream] API to analyze data from the custom [SourceFunction].

The next part of the series shows how to write a custom [SinkFunction] for writing the [DataStream] results into a PostgreSQL database.

[Apache Flink]: https://flink.apache.org/
[DataStream]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/index.html
[KeyedStream]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/windows.html
[SourceFunction]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/#data-sources
[SinkFunction]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/#data-sinks
[PgBulkInsert]: https://github.com/bytefish/PgBulkInsert