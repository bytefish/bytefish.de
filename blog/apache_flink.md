title: Stream Data Processing with Apache Flink
date: 2016-06-10 20:11
tags: java, flink, elasticsearch
category: java
slug: stream_data_processing_flink
author: Philipp Wagner
summary: This article shows how to work with Apache Flink.

In this post I want to show you how to work with [Apache Flink].

> Apache Flink is an open source platform for distributed stream and batch data processing. Flink’s core 
> is a streaming dataflow engine that provides data distribution, communication, and fault tolerance for 
> distributed computations over data streams. Flink also builds batch processing on top of the streaming 
> engine, overlaying native iteration support, managed memory, and program optimization.

## What we are going to build ##

The idea is to use [Apache Flink] to process the stream of weather data measurements from 1,600 U.S. locations.

The processed data will be written into an [Elasticsearch] database.

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://codeberg.org/bytefish/FlinkExperiments](https://codeberg.org/bytefish/FlinkExperiments)

## Dataset ##

The data is the [Quality Controlled Local Climatological Data (QCLCD)]: 

> Quality Controlled Local Climatological Data (QCLCD) consist of hourly, daily, and monthly summaries for approximately 
> 1,600 U.S. locations. Daily Summary forms are not available for all stations. Data are available beginning January 1, 2005 
> and continue to the present. Please note, there may be a 48-hour lag in the availability of the most recent data.

The data is available as CSV files at:

* [http://www.ncdc.noaa.gov/orders/qclcd/](http://www.ncdc.noaa.gov/orders/qclcd/)

We are going to use the data from March 2015, which is located in the zipped file ``QCLCD201503.zip``.

## Dependencies ##

In the example I am going to use the latest ``1.1-SNAPSHOT`` of [Apache Flink]. 

That's why the Apache Development Snapshot Repository must be added to the projects ``POM`` file. 

```xml
<properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <flink.version>1.1-SNAPSHOT</flink.version>
</properties>

<repositories>
    <repository>
        <id>apache.snapshots</id>
        <name>Apache Development Snapshot Repository</name>
        <url>https://repository.apache.org/content/repositories/snapshots/</url>
        <releases>
            <enabled>false</enabled>
        </releases>
        <snapshots>
            <enabled>true</enabled>
        </snapshots>
    </repository>
</repositories>
```

Once the Snapshot repository is added, the Flink dependencies can be added to the POM file.

```xml
<dependencies>

    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-java</artifactId>
        <version>${flink.version}</version>
    </dependency>
    
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-streaming-java_2.10</artifactId>
        <version>${flink.version}</version>
    </dependency>
    
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-clients_2.10</artifactId>
        <version>${flink.version}</version>
    </dependency>

</dependencies>
```

## Generating Measurements with a SourceFunction ##

[SourceFunction]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/functions/source/SourceFunction.html
[SourceContext]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/functions/source/SourceFunction.SourceContext.html
[DataStream]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/datastream/DataStream.html

Apache Flink can ingest data from almost any source. In this example a custom [SourceFunction] is used to serve the Apache Flink [DataStream] API. 

In the example ``LocalWeatherDataSourceFunction`` the CSV data is read with [JTinyCsvParser] and mapped into the Elasticsearch data representation. Each ``LocalWeatherData`` element of the Stream is then emitted to the [SourceContext]. 

An implementation of the [SourceFunction] must react on the ``cancel`` notification, so the [SourceFunction] is designed accordingly.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sources;

import converter.LocalWeatherDataConverter;
import csv.parser.Parsers;
import elastic.model.LocalWeatherData;
import org.apache.flink.streaming.api.functions.source.SourceFunction;

import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystems;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class LocalWeatherDataSourceFunction implements SourceFunction<elastic.model.LocalWeatherData> {

    private volatile boolean isRunning = true;

    private String stationFilePath;
    private String localWeatherDataFilePath;

    public LocalWeatherDataSourceFunction(String stationFilePath, String localWeatherDataFilePath) {
        this.stationFilePath = stationFilePath;
        this.localWeatherDataFilePath = localWeatherDataFilePath;
    }

    @Override
    public void run(SourceFunction.SourceContext<elastic.model.LocalWeatherData> sourceContext) throws Exception {

        // The Source needs to be Serializable, so we have to construct the Paths at this point:
        final Path csvStationPath = FileSystems.getDefault().getPath(stationFilePath);
        final Path csvLocalWeatherDataPath = FileSystems.getDefault().getPath(localWeatherDataFilePath);

        // Get the Stream of LocalWeatherData Elements in the CSV File:
        try(Stream<elastic.model.LocalWeatherData> stream = getLocalWeatherData(csvStationPath, csvLocalWeatherDataPath)) {

            // We need to get an iterator, since the SourceFunction has to break out of its main loop on cancellation:
            Iterator<elastic.model.LocalWeatherData> iterator = stream.iterator();

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

    private Stream<elastic.model.LocalWeatherData> getLocalWeatherData(Path csvStationPath, Path csvLocalWeatherDataPath) {

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

## Persisting the Processed data with a RichSinkFunction ##

[RichSinkFunction]: https://ci.apache.org/projects/flink/flink-docs-master/api/java/org/apache/flink/streaming/api/functions/sink/RichSinkFunction.html

The output of a [DataStream] can be consumed with a [RichSinkFunction]. A [RichSinkFunction] is a function, which offers an additional ``open`` and ``close`` method. 

The example ``BaseElasticSearchSink`` wraps the ``ElasticSearchClient`` from the [ElasticUtils] library. 

Apache Flink serializes and distributes the [RichSinkFunction] to each of its workers. That's why the ``ElasticSearchClient`` is created inside of the [RichSinkFunction], because all of its members need to be Serializable.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sinks;

import de.bytefish.elasticutils.client.ElasticSearchClient;
import de.bytefish.elasticutils.client.IElasticSearchClient;
import de.bytefish.elasticutils.client.bulk.configuration.BulkProcessorConfiguration;
import de.bytefish.elasticutils.client.bulk.options.BulkProcessingOptions;
import de.bytefish.elasticutils.mapping.IElasticSearchMapping;
import de.bytefish.elasticutils.utils.ElasticSearchUtils;
import elastic.mapping.LocalWeatherDataMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.elasticsearch.client.Client;
import org.elasticsearch.client.transport.TransportClient;
import org.elasticsearch.cluster.node.DiscoveryNode;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.elasticsearch.indices.IndexAlreadyExistsException;

import java.net.InetAddress;
import java.util.List;
import java.util.concurrent.TimeUnit;

public abstract class BaseElasticSearchSink<TEntity> extends RichSinkFunction<TEntity> {

    private final String host;
    private final int port;
    private final int bulkSize;

    private IElasticSearchClient<TEntity> client;

    public BaseElasticSearchSink(String host, int port, int bulkSize) {
        this.host = host;
        this.port = port;
        this.bulkSize = bulkSize;

        this.client = null;
    }

    @Override
    public void invoke(TEntity entity) throws Exception {
        client.index(entity);
    }

    @Override
    public void open(Configuration parameters) throws Exception {

        // Create the Transport Client:
        TransportClient transportClient = createClient();

        // Create Index:
        createIndexAndMapping(transportClient);

        // Finally create the Client:
        BulkProcessingOptions options = BulkProcessingOptions.builder()
                .setBulkActions(bulkSize)
                .build();

        client = new ElasticSearchClient<>(transportClient, getIndexName(), new LocalWeatherDataMapper(), new BulkProcessorConfiguration(options));
    }

    @Override
    public void close() throws Exception {
        client.awaitClose(10, TimeUnit.SECONDS);
    }

    protected abstract String getIndexName();

    protected abstract IElasticSearchMapping getMapping();

    private TransportClient createClient() throws Exception {

        // Create a new Connection:
        TransportClient client = TransportClient.builder().build()
                .addTransportAddress(new InetSocketTransportAddress(InetAddress.getByName(host), port));

        // Ensure we have connected nodes:
        List<DiscoveryNode> nodes = client.connectedNodes();

        if (nodes.isEmpty()) {
            throw new RuntimeException("Client is not connected to any Elasticsearch nodes!");
        }

        return client;
    }

    private void createIndexAndMapping(Client client) {
        // Create the Index and Mappings before indexing the entities:
        try {
            createIndex(client, getIndexName());
            createMapping(client, getIndexName(), getMapping());
        } catch (IndexAlreadyExistsException e) {
            // No need to worry. Someone else has already initialized the Elasticsearch database...
        }
    }

    private void createIndex(Client client, String indexName) {
        if (!ElasticSearchUtils.indexExist(client, indexName).isExists()) {
            ElasticSearchUtils.createIndex(client, indexName);
        }
    }

    private void createMapping(Client client, String indexName, IElasticSearchMapping mapping) {
        if (ElasticSearchUtils.indexExist(client, indexName).isExists()) {
            ElasticSearchUtils.putMapping(client, indexName, mapping);
        }
    }
}
```

Now the implementation for the ``LocalWeatherData`` is easy.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sinks;

import de.bytefish.elasticutils.client.bulk.options.BulkProcessingOptions;
import de.bytefish.elasticutils.mapping.IElasticSearchMapping;

public class LocalWeatherDataElasticSearchSink extends BaseElasticSearchSink<elastic.model.LocalWeatherData> {

    public LocalWeatherDataElasticSearchSink(String host, int port, int bulkSize) {
        super(host, port, bulkSize);
    }

    @Override
    protected String getIndexName() {
        return "weather_data";
    }

    @Override
    protected IElasticSearchMapping getMapping() {
        return new elastic.mapping.LocalWeatherDataMapper();
    }

}
```

## Processing the Data with a DataStream ##

Now it's time to connect the pieces. I have commented the code thoroughly.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package app;

import org.apache.flink.api.common.functions.FilterFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.streaming.api.TimeCharacteristic;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.timestamps.AscendingTimestampExtractor;
import org.apache.flink.streaming.api.windowing.time.Time;
import stream.sinks.LocalWeatherDataElasticSearchSink;
import stream.sources.LocalWeatherDataSourceFunction;

import java.util.Date;
import java.util.concurrent.TimeUnit;

public class WeatherDataStreamingExample {

    public static void main(String[] args) throws Exception {

        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Use the Measurement Timestamp of the Event:
        env.setStreamTimeCharacteristic(TimeCharacteristic.EventTime);

        // Path to read the CSV data from:
        final String csvStationDataFilePath = "C:\\Users\\philipp\\Downloads\\csv\\201503station.txt";
        final String csvLocalWeatherDataFilePath = "C:\\Users\\philipp\\Downloads\\csv\\201503hourly.txt";

        // Add the CSV Data Source and assign the Measurement Timestamp:
        DataStream<elastic.model.LocalWeatherData> localWeatherDataDataStream = env
                .addSource(new LocalWeatherDataSourceFunction(csvStationDataFilePath, csvLocalWeatherDataFilePath))
                .assignTimestampsAndWatermarks(new AscendingTimestampExtractor<elastic.model.LocalWeatherData>() {
                    @Override
                    public long extractAscendingTimestamp(elastic.model.LocalWeatherData localWeatherData) {
                        Date measurementDate = localWeatherData.dateTime;

                        return measurementDate.getTime();
                    }
                });

        // Now Perform the Analysis for the daily maximum value on the Stream:
        DataStream<elastic.model.LocalWeatherData> dailyMaxTemperature = localWeatherDataDataStream
                // Filte for Non-Null Temperature Values, because we might have missing data:
                .filter(new FilterFunction<elastic.model.LocalWeatherData>() {
                    @Override
                    public boolean filter(elastic.model.LocalWeatherData localWeatherData) throws Exception {
                        return localWeatherData.temperature != null;
                    }
                })
                // Now create the keyed stream by the Station WBAN identifier:
                .keyBy(new KeySelector<elastic.model.LocalWeatherData, String>() {
                    @Override
                    public String getKey(elastic.model.LocalWeatherData localWeatherData) throws Exception {
                        return localWeatherData.station.wban;
                    }
                })
                // Create a Tumbling Window with the values of 1 day:
                .timeWindow(Time.of(1, TimeUnit.DAYS))
                // Use the max Temperature of the day:
                .max("temperature")
                // And perform an Identity map, because we want to write all values of this day to the Database:
                .map(new MapFunction<elastic.model.LocalWeatherData, elastic.model.LocalWeatherData>() {
                    @Override
                    public elastic.model.LocalWeatherData map(elastic.model.LocalWeatherData localWeatherData) throws Exception {
                        return localWeatherData;
                    }
                });

        // Add a new ElasticSearch Sink:
        dailyMaxTemperature.addSink(new LocalWeatherDataElasticSearchSink("127.0.0.1", 9300, 100));

        // Finally execute the Stream:
        env.execute("Max Temperature By Day example");
    }
}
```

## Resources ##

* [Building real-time dashboard applications with Apache Flink, Elasticsearch, and Kibana](https://www.elastic.co/blog/building-real-time-dashboard-applications-with-apache-flink-elasticsearch-and-kibana)


[Apache Flink]: https://flink.apache.org/
[Elasticsearch]: https://www.elastic.co
[ElasticUtils]: https://codeberg.org/bytefish/ElasticUtils
[JTinyCsvParser]: https://codeberg.org/bytefish/JTinyCsvParser
[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd