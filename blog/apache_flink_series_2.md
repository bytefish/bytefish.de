title: Building Applications with Apache Flink (Part 2): Writing a custom SourceFunction and Using the DataStream API
date: 2016-07-03 15:12
tags: java, flink, elasticsearch, postgresql
category: java
slug: apache_flink_example
author: Philipp Wagner
summary: This article shows how to work with Apache Flink.

In the previous article we have obtained a CSV dataset, analyzed it and built the neccessary tools for parsing it. A domain model 
was created, which will be used for the Stream processing. What's left is how to feed a [DataStream] with the actual CSV data, 
and this is where the [SourceFunction] fits in.

## What we are going to build ##

We are going to build a [SourceFunction], that uses the parsers from the previous article to read the CSV data. The ``LocalWeatherDataConverter`` is 
used to transform the CSV objects into the domain model, which is the emitted to the Apache Flink [SourceContext].

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://github.com/bytefish/FlinkExperiments](https://github.com/bytefish/FlinkExperiments)

## LocalWeatherDataSourceFunction ##

The ``LocalWeatherDataSourceFunction`` implements the [SourceFunction] interface, parses the CSV data from the previous and emits the measurements to the Apache Flink [SourceContext].

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sources.csv;

import csv.parser.Parsers;
import org.apache.flink.streaming.api.functions.source.SourceFunction;
import stream.sources.csv.converter.LocalWeatherDataConverter;

import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystems;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class LocalWeatherDataSourceFunction implements SourceFunction<model.LocalWeatherData> {

    private volatile boolean isRunning = true;

    private String stationFilePath;
    private String localWeatherDataFilePath;

    public LocalWeatherDataSourceFunction(String stationFilePath, String localWeatherDataFilePath) {
        this.stationFilePath = stationFilePath;
        this.localWeatherDataFilePath = localWeatherDataFilePath;
    }

    @Override
    public void run(SourceFunction.SourceContext<model.LocalWeatherData> sourceContext) throws Exception {

        // The Source needs to be Serializable, so we have to construct the Paths at this point:
        final Path csvStationPath = FileSystems.getDefault().getPath(stationFilePath);
        final Path csvLocalWeatherDataPath = FileSystems.getDefault().getPath(localWeatherDataFilePath);

        // Get the Stream of LocalWeatherData Elements in the CSV File:
        try(Stream<model.LocalWeatherData> stream = getLocalWeatherData(csvStationPath, csvLocalWeatherDataPath)) {

            // We need to get an iterator, since the SourceFunction has to break out of its main loop on cancellation:
            Iterator<model.LocalWeatherData> iterator = stream.iterator();

            // Make sure to cancel, when the Source function is canceled by an external event:
            while (isRunning && iterator.hasNext()) {
                sourceContext.collect(iterator.next());
            }
        }
    }

    @Override
    public void cancel() {
        isRunning = false;
    }

    private Stream<model.LocalWeatherData> getLocalWeatherData(Path csvStationPath, Path csvLocalWeatherDataPath) {

        // A map between the WBAN and Station for faster Lookups:
        final Map<String, csv.model.Station> stationMap = getStationMap(csvStationPath);

        // Turns the Stream of CSV data into the Elasticsearch representation:
        return getLocalWeatherData(csvLocalWeatherDataPath)
                // Only use Measurements with a Station:
                .filter(x -> stationMap.containsKey(x.getWban()))
                // And turn the Station and LocalWeatherData into the ElasticSearch representation:
                .map(x -> {
                    // First get the matching Station:
                    csv.model.Station station = stationMap.get(x.getWban());
                    // Convert to the Elastic Representation:
                    return LocalWeatherDataConverter.convert(x, station);
                });
    }

    private static Stream<csv.model.LocalWeatherData> getLocalWeatherData(Path path) {
        return Parsers.LocalWeatherDataParser().readFromFile(path, StandardCharsets.US_ASCII)
                .filter(x -> x.isValid())
                .map(x -> x.getResult());
    }

    private static Stream<csv.model.Station> getStations(Path path) {
        return Parsers.StationParser().readFromFile(path, StandardCharsets.US_ASCII)
                .filter(x -> x.isValid())
                .map(x -> x.getResult());
    }

    private Map<String, csv.model.Station> getStationMap(Path path) {
        try (Stream<csv.model.Station> stationStream = getStations(path)) {
            return stationStream
                    .collect(Collectors.toMap(csv.model.Station::getWban, x -> x));
        }
    }
}
```

## Conclusion ##

The next part of the series shows how to utilize the [SourceFunction] to serve a [DataStream].

[Apache Flink]: https://flink.apache.org/
[SourceFunction]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/functions/source/SourceFunction.html
[SourceContext]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/functions/source/SourceFunction.SourceContext.html
[DataStream]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/index.html
[KeyedStream]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/windows.html
[SourceFunction]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/#data-sources
[SinkFunction]: https://ci.apache.org/projects/flink/flink-docs-master/apis/streaming/#data-sinks