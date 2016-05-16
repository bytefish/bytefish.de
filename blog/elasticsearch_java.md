title: Working with Elasticsearch in Java
date: 2016-05-16 12:55
tags: java, elasticsearch
category: java
slug: elasticsearch_java
author: Philipp Wagner
summary: This article shows how to work with Elasticsearch in Java.

In this article I am going to show you how to work with [Elasticsearch] in Java.

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://github.com/bytefish/JavaElasticSearchExperiment](https://github.com/bytefish/JavaElasticSearchExperiment)

## What we are going to build ##

The idea is to store the hourly weather data of 1,600 U.S. locations in an [Elasticsearch] database and visualize it with [Kibana].

The final result will visualize the average temperature in March 2015 on a tile map:

<a href="/static/images/blog/elasticsearch_net/kibana.jpg">
	<img src="/static/images/blog/elasticsearch_net/thumbs/kibana_thumb.jpg" alt="Kibana Map Weather Visualization" />
</a>

## ElasticSearchClient ##

Working with Elasticsearch Java API turned out to be a little complicated, that's why I wrote the ``ElasticSearchClient``. 

The ``ElasticSearchClient`` makes it possible to:

* Define Mappings with a Fluent API.
* Create an Index by name, if the Index doesn't exist yet.
* Create the Mapping with the PUT Mapping API.
* Bulk Insert a given ``Stream`` of data.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.client;

import elastic.client.bulk.configuration.BulkProcessorConfiguration;
import elastic.mapping.IObjectMapping;
import elastic.utils.ElasticSearchUtils;
import org.elasticsearch.action.bulk.BulkProcessor;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.client.Client;
import utils.JsonUtilities;

import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.stream.Stream;

public class ElasticSearchClient<TEntity> implements AutoCloseable {

    private final Client client;
    private final String indexName;
    private final IObjectMapping mapping;
    private final BulkProcessor bulkProcessor;

    public ElasticSearchClient(final Client client, final String indexName, final IObjectMapping mapping, final BulkProcessorConfiguration bulkProcessorConfiguration) {
        this.client = client;
        this.indexName = indexName;
        this.mapping = mapping;
        this.bulkProcessor = bulkProcessorConfiguration.build(client);
    }

    public void createIndex() {
        if(!ElasticSearchUtils.indexExist(client, indexName).isExists()) {
            ElasticSearchUtils.createIndex(client, indexName);
        }
    }

    public void createMapping() {
        if(ElasticSearchUtils.indexExist(client, indexName).isExists()) {
            ElasticSearchUtils.putMapping(client, indexName, mapping);
        }
    }

    public void index(TEntity entity) {
        index(Arrays.asList(entity));

        bulkProcessor.flush();
    }

    public void index(List<TEntity> entities) {
        index(entities.stream());
    }

    public void index(Stream<TEntity> entities) {
        entities
                .map(x -> JsonUtilities.convertJsonToBytes(x))
                .filter(x -> x.isPresent())
                .map(x -> createIndexRequest(x.get()))
                .forEach(bulkProcessor::add);
    }

    private IndexRequest createIndexRequest(byte[] messageBytes) {
        return client.prepareIndex()
                .setId(UUID.randomUUID().toString())
                .setIndex(indexName)
                .setType(mapping.getIndexType())
                .setSource(messageBytes)
                .request();
    }

    @Override
    public void close() throws Exception {
        // If we ever need to close opened resources, it would go here ...
    }
}
```


### Elasticsearch Mapping ###

So how does it work?

One of the most complicated parts of Elasticsearch with Java was working with the Elasticsearch [Mapping].

Elasticsearch is not a schema-less database. If you index a document without explicitly defining a document mapping, then Elasticsearch 
makes a best guess about your data and infers the mapping based on the document data, see the excellent [Elasticsearch Definitive guide] 
for more informations.

Sometimes you need to have more control over the data types and the mapping. Sometimes a property needs to be nested and included in the 
parent object. Sometimes you have a date field with a weird format, that should still be mapped to an Elasticsearch date type and not to a 
string value.

Citing the Elasticsearch documentation on [Mapping]:

> Mapping is the process of defining how a document, and the fields it contains, are stored and indexed. For instance, use mappings to define:
> 
> * which string fields should be treated as full text fields.
> * which fields contain numbers, dates, or geolocations.
> * whether the values of all fields in the document should be indexed into the catch-all _all field.
> * the format of date values.
> * custom rules to control the mapping for dynamically added fields.

#### IObjectMapping ####

First of all we are defining an interface ``IObjectMapping``. This interface has two methods for getting the index type and the mapping. The mapping is 
returned as an ``XContentBuilder``, so you can choose the format to serialize to. By using and ``XContentBuilder`` you can also do further work on the 
mapping. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.mapping;

import org.elasticsearch.common.xcontent.XContentBuilder;

public interface IObjectMapping {

    XContentBuilder getMapping();

    String getIndexType();

}
```

#### AbstractMap ####

First of all we are writing a base class for the mapping, called ``AbstractMap``. This base class handles building JSON mapping from an 
``RootObjectMapper`` (from Elasticsearch) and creating the ``XContentBuilder`` from the defined mapping. Implementations of this abstract 
class need to implement two methods for configuring the actual mapping and define the settings for the index creation.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.mapping;

import elastic.exceptions.GetMappingFailedException;
import org.elasticsearch.Version;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.common.xcontent.ToXContent;
import org.elasticsearch.common.xcontent.XContentBuilder;
import org.elasticsearch.common.xcontent.json.JsonXContent;
import org.elasticsearch.index.mapper.ContentPath;
import org.elasticsearch.index.mapper.Mapper;
import org.elasticsearch.index.mapper.Mapping;
import org.elasticsearch.index.mapper.MetadataFieldMapper;
import org.elasticsearch.index.mapper.object.RootObjectMapper;

import java.io.IOException;

public abstract class AbstractMap implements IObjectMapping {

    private final String indexType;
    private final String version;

    public AbstractMap(String indexType, String version) {
        this.indexType = indexType;
        this.version = version;
    }

    public XContentBuilder getMapping() {
        try {
            return internalGetMapping();
        } catch(Exception e) {
            throw new GetMappingFailedException(indexType, e);
        }
    }

    public String getIndexType() {
        return indexType;
    }

    public XContentBuilder internalGetMapping() throws IOException {

        // Configure the RootObjectMapper:
        RootObjectMapper.Builder rootObjectMapperBuilder = getRootObjectBuilder();

        // Populate the Settings:
        Settings.Builder settingsBuilder = getSettingsBuilder();

        // Build the Mapping:
        Mapping mapping = new Mapping(
                Version.fromString(version),
                rootObjectMapperBuilder.build(new Mapper.BuilderContext(settingsBuilder.build(), new ContentPath())),
                new MetadataFieldMapper[] {},
                new Mapping.SourceTransform[] {},
                null);

        // Turn it into JsonXContent:
        return mapping.toXContent(JsonXContent.contentBuilder().startObject(), ToXContent.EMPTY_PARAMS);
    }

    private Settings.Builder getSettingsBuilder() {
        Settings.Builder settingsBuilder = Settings.builder();

        configure(settingsBuilder);

        return settingsBuilder;
    }

    private RootObjectMapper.Builder getRootObjectBuilder() {
        RootObjectMapper.Builder rootObjectMapperBuilder = new RootObjectMapper.Builder(indexType);

        configure(rootObjectMapperBuilder);

        return rootObjectMapperBuilder;
    }

    protected abstract void configure(RootObjectMapper.Builder builder);

    protected abstract void configure(Settings.Builder builder);
}
```

#### LocalWeatherDataMapper ####

Now implementing the mapping for a document is easy. 

You extend your mapping from the ``AbstractMap`` base class and implement the two methods ``configure(RootObjectMapper.Builder builder)`` 
and ``configure(Settings.Builder builder)``, which are used for defining the field mapping and Settings for the index creation.

You can see, that the ``RootObjectMapper`` has a Fluent API, that makes it very easy to read and write the actual mapping. The various 
field mappers from Elasticsearch allow you to access all options for a given data type. This is much safer, than defining the mappings 
in JSON.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.mapping;

import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.mapper.core.DateFieldMapper;
import org.elasticsearch.index.mapper.core.FloatFieldMapper;
import org.elasticsearch.index.mapper.core.StringFieldMapper;
import org.elasticsearch.index.mapper.geo.GeoPointFieldMapper;
import org.elasticsearch.index.mapper.object.ObjectMapper;
import org.elasticsearch.index.mapper.object.RootObjectMapper;

public class LocalWeatherDataMapper extends AbstractMap {

    private static final String INDEX_TYPE = "document";

    public LocalWeatherDataMapper() {
        super(INDEX_TYPE, "1.0.0");
    }

    @Override
    protected void configure(RootObjectMapper.Builder builder) {
        builder
                .add(new DateFieldMapper.Builder("dateTime"))
                .add(new FloatFieldMapper.Builder("temperature"))
                .add(new FloatFieldMapper.Builder("windSpeed"))
                .add(new FloatFieldMapper.Builder("stationPressure"))
                .add(new StringFieldMapper.Builder("skyCondition"))
                .add(new ObjectMapper.Builder("station")
                        .add(new StringFieldMapper.Builder("wban"))
                        .add(new StringFieldMapper.Builder("name"))
                        .add(new StringFieldMapper.Builder("state"))
                        .add(new StringFieldMapper.Builder("location"))
                        .add(new GeoPointFieldMapper.Builder("coordinates")
                                .enableLatLon(true)
                                .enableGeoHash(false))
                        .nested(ObjectMapper.Nested.newNested(true, false)));
    }

    @Override
    protected void configure(Settings.Builder builder) {
        builder
                .put(IndexMetaData.SETTING_VERSION_CREATED, 1)
                .put(IndexMetaData.SETTING_CREATION_DATE, System.currentTimeMillis());
    }
}
```

### PUT Mapping API ###

The [PUT mapping API] allows you to add new type to an existing index  or new fields to an existing type. 

We have already defined the ``IObjectMapping`` interface above, which will be used to create the mapping for an index. Then we 
can write a small class ``ElasticSearchUtils``, that wraps the call to the [PUT Mapping API]. The ``putMapping`` method takes 
the Elasticsearch client to be used, the index to add the mapping to and the ``IObjectMapping`` itself.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.utils;

import elastic.exceptions.CreateIndexFailedException;
import elastic.exceptions.IndicesExistsFailedException;
import elastic.exceptions.PutMappingFailedException;
import elastic.mapping.IObjectMapping;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.elasticsearch.action.admin.indices.mapping.put.PutMappingRequest;
import org.elasticsearch.action.admin.indices.mapping.put.PutMappingResponse;
import org.elasticsearch.client.Client;

import java.io.IOException;

public class ElasticSearchUtils {

    private static final Logger log = LogManager.getLogger(ElasticSearchUtils.class);

    public static PutMappingResponse putMapping(Client client, String indexName, IObjectMapping mapping) {
        try {
            return internalPutMapping(client, indexName, mapping);
        } catch(Exception e) {
            if(log.isErrorEnabled()) {
                log.error("Error Creating Index", e);
            }
            throw new PutMappingFailedException(indexName, e);
        }
    }

    private static PutMappingResponse internalPutMapping(Client client, String indexName, IObjectMapping mapping) throws IOException {

        final PutMappingRequest putMappingRequest = new PutMappingRequest(indexName)
                .type(mapping.getIndexType())
                .source(mapping.getMapping().string());

        final PutMappingResponse putMappingResponse = client
                .admin()
                .indices()
                .putMapping(putMappingRequest)
                .actionGet();

        if(log.isDebugEnabled()) {
            log.debug("PutMappingResponse: isAcknowledged {}", putMappingResponse.isAcknowledged());
        }

        return putMappingResponse;
    }
}
```

### Bulk Insert API ###

It's often not neccessary to store a document one by one. Often enough you have a high rate of incoming data, that could be batched 
and written to the database as a bulk insert. The official Elasticsearch page on [performance consideration] says:

> Always use the bulk api, which indexes multiple documents in one request, and experiment with the right number of documents to send 
> with each bulk request. The optimal size depends on many factors, but try to err in the direction of too few rather than too many documents. 
> Use concurrent bulk requests with client-side threads or separate asynchronous requests.

#### BulkProcessor ####

##### BulkProcessor.Listener #####

Sometimes you need to do additional work on the inserted data. You want to evaluate if the data was inserted correctly, see what time it took to 
insert the data or you need to handle specific errors occured during inserting the data. This can be done by implementing the 
``BulkProcessor.Listener`` interface, which makes it possible to perform actions before and after the bulk insert.
 
In the example application, we are only interested in logging the actions, which is implemented by the ``LoggingBulkProcessorListener``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.client.bulk.listener;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.elasticsearch.action.bulk.BulkProcessor;
import org.elasticsearch.action.bulk.BulkRequest;
import org.elasticsearch.action.bulk.BulkResponse;

public class LoggingBulkProcessorListener implements BulkProcessor.Listener {

    private static final Logger log = LogManager.getLogger(LoggingBulkProcessorListener.class);

    public LoggingBulkProcessorListener() {
    }

    @Override
    public void beforeBulk(long executionId, BulkRequest request) {
        if(log.isDebugEnabled()) {
            log.debug("ExecutionId = {}, Actions = {}, Estimated Size = {}", executionId, request.numberOfActions(), request.estimatedSizeInBytes());
        }
    }

    @Override
    public void afterBulk(long executionId, BulkRequest request, BulkResponse response) {
        if(log.isDebugEnabled()) {
            log.debug("ExecutionId = {}, Actions = {}, Estimated Size = {}", executionId, request.numberOfActions(), request.estimatedSizeInBytes());
        }
    }

    @Override
    public void afterBulk(long executionId, BulkRequest request, Throwable failure) {
        if(log.isErrorEnabled()) {
            log.error("ExecutionId = {}, Error = {}", executionId, failure);
        }
    }
}
```

##### BulkProcessorOptions and Builder #####

The ElasticSearch ``BulkProcessor`` needs to be configured with a set of parameters, like: 

* Number of Bulk Actions
* Number of Concurrent Requests
* Bulk Size to flush at

This configuration is passed into the ``ElasticSearchClient``, that's why a separate class for these options is created.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.client.bulk.options;

import org.elasticsearch.action.bulk.BackoffPolicy;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.unit.TimeValue;

public class BulkProcessingOptions {

    private String name;
    private int concurrentRequests;
    private int bulkActions;
    private ByteSizeValue bulkSize;
    private TimeValue flushInterval;
    private BackoffPolicy backoffPolicy;

    public BulkProcessingOptions(String name, int concurrentRequests, int bulkActions, ByteSizeValue bulkSize, TimeValue flushInterval, BackoffPolicy backoffPolicy) {
        this.name = name;
        this.concurrentRequests = concurrentRequests;
        this.bulkActions = bulkActions;
        this.bulkSize = bulkSize;
        this.flushInterval = flushInterval;
        this.backoffPolicy = backoffPolicy;
    }

    public String getName() {
        return name;
    }

    public int getConcurrentRequests() {
        return concurrentRequests;
    }

    public int getBulkActions() {
        return bulkActions;
    }

    public ByteSizeValue getBulkSize() {
        return bulkSize;
    }

    public TimeValue getFlushInterval() {
        return flushInterval;
    }

    public BackoffPolicy getBackoffPolicy() {
        return backoffPolicy;
    }

    public static BulkProcessingOptionsBuilder builder() {
        return new BulkProcessingOptionsBuilder();
    }
}
```

You don't want to instantiate the ``BulkProcessingOptions`` with its long parameter list by hand. You also don't want to research the default 
parameters from the Elasticsearch pages. 

That's why the ``BulkProcessingOptions`` are instantiated by the ``BulkProcessingOptionsBuilder``, that already has all the default values set.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.client.bulk.options;

import org.elasticsearch.action.bulk.BackoffPolicy;
import org.elasticsearch.common.unit.ByteSizeUnit;
import org.elasticsearch.common.unit.ByteSizeValue;
import org.elasticsearch.common.unit.TimeValue;

public class BulkProcessingOptionsBuilder {

    private String name;
    private int concurrentRequests = 1;
    private int bulkActions = 1000;
    private ByteSizeValue bulkSize = new ByteSizeValue(5, ByteSizeUnit.MB);
    private TimeValue flushInterval = null;
    private BackoffPolicy backoffPolicy = BackoffPolicy.exponentialBackoff();

    public BulkProcessingOptionsBuilder setName(String name) {
        this.name = name;
        return this;
    }

    public BulkProcessingOptionsBuilder setConcurrentRequests(int concurrentRequests) {
        this.concurrentRequests = concurrentRequests;
        return this;
    }

    public BulkProcessingOptionsBuilder setBulkActions(int bulkActions) {
        this.bulkActions = bulkActions;
        return this;
    }

    public BulkProcessingOptionsBuilder setBulkSize(ByteSizeValue bulkSize) {
        this.bulkSize = bulkSize;
        return this;
    }

    public BulkProcessingOptionsBuilder setFlushInterval(TimeValue flushInterval) {
        this.flushInterval = flushInterval;
        return this;
    }

    public BulkProcessingOptionsBuilder setBackoffPolicy(BackoffPolicy backoffPolicy) {
        this.backoffPolicy = backoffPolicy;
        return this;
    }

    public BulkProcessingOptions build() {
        return new BulkProcessingOptions(name, concurrentRequests, bulkActions, bulkSize, flushInterval, backoffPolicy);
    }
}
```

##### BulkProcessorConfiguration ######

The ``BulkProcessorConfiguration`` is the class, that holds the listener and the options. It has a ``build`` method, that takes 
an Elasticsearch ``Client`` to build the final ``BulkProcessor``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.client.bulk.configuration;

import elastic.client.bulk.listener.LoggingBulkProcessorListener;
import elastic.client.bulk.options.BulkProcessingOptions;
import elastic.client.bulk.options.BulkProcessingOptionsBuilder;
import org.elasticsearch.action.bulk.BulkProcessor;
import org.elasticsearch.client.Client;

public class BulkProcessorConfiguration {

    private BulkProcessingOptions options = new BulkProcessingOptionsBuilder().build();
    private BulkProcessor.Listener listener = new LoggingBulkProcessorListener();

    public BulkProcessorConfiguration(BulkProcessingOptions options)
    {
        this(options, new LoggingBulkProcessorListener());
    }

    public BulkProcessorConfiguration(BulkProcessingOptions options, BulkProcessor.Listener listener) {
        this.options = options;
        this.listener = listener;
    }

    public BulkProcessingOptions getBulkProcessingOptions() {
        return options;
    }

    public BulkProcessor.Listener getBulkProcessorListener() {
        return listener;
    }

    public BulkProcessor build(final Client client) {
        return BulkProcessor.builder(client, listener)
                .setName(options.getName())
                .setConcurrentRequests(options.getConcurrentRequests())
                .setBulkActions(options.getBulkActions())
                .setBulkSize(options.getBulkSize())
                .setFlushInterval(options.getFlushInterval())
                .setBackoffPolicy(options.getBackoffPolicy())
                .build();
    }
}
```

### Indexing data using the Bulk API ###

#### JsonUtilities ####

We want to index JSON data from a given ``Stream`` of Java objects. These objects need to be serialized to JSON 
messages and transformed into a UTF8 byte array. The indexing should not fail, just because one of the entities 
cannot be serialized to JSON. 

You can imagine, that probably a number is too large to fit into the defined JSON data type. Or values set as 
required are missing for the serialization. That's why we are wrapping the call to the Jackson 
``ObjectMapper.writeValueAsBytes`` in a try/catch block and make the result optional.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.Optional;

public class JsonUtilities {

    private static final Logger logger = LogManager.getLogger(JsonUtilities.class);

    private static final ObjectMapper mapper = new ObjectMapper();

    public static <TEntity> Optional<byte[]> convertJsonToBytes(TEntity entity) {
        try {
            return Optional.empty().of(mapper.writeValueAsBytes(entity));
        } catch(Exception e) {
            if(logger.isErrorEnabled()) {
                logger.error(String.format("Failed to convert entity %s to JSON", entity), e);
            }
        }
        return Optional.empty();
    }
}
```

#### BulkProcessor Pipeline ####

Having wrapped the JSON serialization in a separate class, we can now write the indexing pipeline for the ``BulkProcessor``.

It basically works like this: 
* A ``Stream`` of Java objects is first turned into a ``Stream`` JSON messages. 
* Then the invalid JSON messages are filtered out.
* The ``Stream`` of valid JSON messages is turned into a ``Stream`` of ``IndexRequest``. 
* Each ``IndexRequest`` is added to the ``BulkProcessor``.

```java
public void index(Stream<TEntity> entities) {
	entities
			.map(x -> JsonUtilities.convertJsonToBytes(x))
			.filter(x -> x.isPresent())
			.map(x -> createIndexRequest(x.get()))
			.forEach(bulkProcessor::add);
}
```

What's left is creating the ``IndexRequest`` from the message. 

You can see, that we assign a unique identifier to each message, set the index name, the index type and set the JSON message as source.

```java
private IndexRequest createIndexRequest(byte[] messageBytes) {
	return client.prepareIndex()
			.setId(UUID.randomUUID().toString())
			.setIndex(indexName)
			.setType(mapping.getIndexType())
			.setSource(messageBytes)
			.request();
}
```

## The LocalWeatherData Application ##

I have always problems to start with a new technology. You seldomly find full examples in the internet, that you can experiment with.

So I have implemented and open sourced a sample application, that shows how to work with Elasticsearch in Java.

### Dataset ###

The data is the [Quality Controlled Local Climatological Data (QCLCD)]: 

> Quality Controlled Local Climatological Data (QCLCD) consist of hourly, daily, and monthly summaries for approximately 
> 1,600 U.S. locations. Daily Summary forms are not available for all stations. Data are available beginning January 1, 2005 
> and continue to the present. Please note, there may be a 48-hour lag in the availability of the most recent data.

The data is available as CSV files at:

* [http://www.ncdc.noaa.gov/orders/qclcd/](http://www.ncdc.noaa.gov/orders/qclcd/)

We are going to use the data from March 2015, which is located in the zipped file ``QCLCD201503.zip``.


### Parsing the CSV data ###

I am using my project [JTinyCsvParser] to parse the CSV data. 

#### Model ####

The first thing is to model the data we are interested in. The weather data is contained in the file ``201503hourly.txt`` and the list 
of available weather stations is given in the file ``201503station.txt``. The weather stations are identified by their ``WBAN`` number 
(*W*eather-*B*ureau-*A*rmy-*N*avy).

##### LocalWeatherData #####

The local weather data in ``201503hourly.txt`` has more than 30 columns, but we are only interested in the WBAN Identifier (Column 0), 
Time of measurement (Columns 1, 2), Sky Condition (Column 4), Air Temperature (Column 12), Wind Speed (Column 24) and Pressure (Column 30).

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.model;

import java.time.LocalDate;
import java.time.LocalTime;

public class LocalWeatherData {

    private String wban;

    private LocalDate date;

    private LocalTime time;

    private String skyCondition;

    private Float dryBulbCelsius;

    private Float windSpeed;

    private Float stationPressure;

    public LocalWeatherData() {

    }

	// Getters and Setters ...
	
}
```

##### Station #####

The Station data has only 14 properties, the model is going to contain all properties.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.model;

public class Station {

    private String wban;

    private String wmo;

    private String callSign;

    private String climateDivisionCode;

    private String climateDivisionStateCode;

    private String climateDivisionStationCode;

    private String name;

    private String state;

    private String location;

    private Float latitude;

    private Float longitude;

    private Integer groundHeight;

    private Integer stationHeight;

    private Integer barometer;

    private Integer timeZone;

    public Station() {
    }

	// Getters and Setters ...

}
```

#### Mapping ####

With [JTinyCsvParser] you have to define mapping between the column index and the property of the Java object. This is done 
by implementing the abstract base class ``CsvMapping`` for the objects.

##### LocalWeatherDataMapper ######

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.mapping;

import csv.converter.IgnoreMissingValuesConverter;
import csv.model.LocalWeatherData;
import de.bytefish.jtinycsvparser.builder.IObjectCreator;
import de.bytefish.jtinycsvparser.mapping.CsvMapping;
import de.bytefish.jtinycsvparser.typeconverter.LocalDateConverter;
import de.bytefish.jtinycsvparser.typeconverter.LocalTimeConverter;

import java.time.LocalDate;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

public class LocalWeatherDataMapper extends CsvMapping<LocalWeatherData>
{
    public LocalWeatherDataMapper(IObjectCreator creator)
    {
        super(creator);

        MapProperty(0, String.class, LocalWeatherData::setWban);
        MapProperty(1, LocalDate.class, LocalWeatherData::setDate, new LocalDateConverter(DateTimeFormatter.ofPattern("yyyyMMdd")));
        MapProperty(2, LocalTime.class, LocalWeatherData::setTime, new LocalTimeConverter(DateTimeFormatter.ofPattern("HHmm")));
        MapProperty(4, String.class, LocalWeatherData::setSkyCondition);
        MapProperty(12, Float.class, LocalWeatherData::setDryBulbCelsius, new IgnoreMissingValuesConverter("M"));
        MapProperty(24, Float.class, LocalWeatherData::setWindSpeed, new IgnoreMissingValuesConverter("M"));
        MapProperty(30, Float.class, LocalWeatherData::setStationPressure, new IgnoreMissingValuesConverter("M"));
    }
}
```

##### StationMapper #####

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.mapping;

import csv.model.Station;
import de.bytefish.jtinycsvparser.builder.IObjectCreator;
import de.bytefish.jtinycsvparser.mapping.CsvMapping;

public class StationMapper extends CsvMapping<Station>
{
    public StationMapper(IObjectCreator creator)
    {
        super(creator);

        MapProperty(0, String.class, Station::setWban);
        MapProperty(1, String.class, Station::setWmo);
        MapProperty(2, String.class, Station::setCallSign);
        MapProperty(3, String.class, Station::setClimateDivisionCode);
        MapProperty(4, String.class, Station::setClimateDivisionStateCode);
        MapProperty(5, String.class, Station::setClimateDivisionStationCode);
        MapProperty(6, String.class, Station::setName);
        MapProperty(7, String.class, Station::setState);
        MapProperty(8, String.class, Station::setLocation);
        MapProperty(9, Float.class, Station::setLatitude);
        MapProperty(10, Float.class, Station::setLongitude);
        MapProperty(11, Integer.class, Station::setGroundHeight);
        MapProperty(12, Integer.class, Station::setStationHeight);
        MapProperty(13, Integer.class, Station::setBarometer);
        MapProperty(14, Integer.class, Station::setTimeZone);
    }
}
```

#### Converter ####

If you look at the CSV file you will see, that it has missing values. You don't want to discard the entire line, just because of a 
missing value. Probably these values are optional? The missing values in the CSV files are identified by an ``M`` (apparently for **m**issing). 

These values cannot be converted into an ``Float`` as defined in the mapping. That's why a custom converter ``IgnoreMissingValuesConverter`` for 
the columns is implemented, which is done by deriving from a ``ITypeConverter`` from [JTinyCsvParser].

##### IgnoreMissingValuesConverter #####

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.converter;

import de.bytefish.jtinycsvparser.typeconverter.ITypeConverter;
import utils.StringUtils;

import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class IgnoreMissingValuesConverter implements ITypeConverter<Float> {

    private List<String> missingValueRepresentation;

    public IgnoreMissingValuesConverter(String... missingValueRepresentation) {
        this(Arrays.asList(missingValueRepresentation));
    }

    public IgnoreMissingValuesConverter(List<String> missingValueRepresentation) {
        this.missingValueRepresentation = missingValueRepresentation;
    }

    @Override
    public Float convert(final String s) {

        if(StringUtils.isNullOrWhiteSpace(s)) {
            return null;
        }

        boolean isMissingValue = missingValueRepresentation
                .stream()
                .anyMatch(x -> x.equals(s));

        if(isMissingValue) {
            return null;
        }

        return Float.parseFloat(s);
    }

    @Override
    public Type getTargetType() {
        return Float.class;
    }
}
```

#### Parsers ####

The CSV file is parsed with a ``CsvParser`` from [JTinyCsvParser]. The ``CsvParser`` defines how to tokenize a line of CSV data 
and how to instantiate the result objects. I am defining a class ``Parsers``, that creates ``CsvParser`` instances for the CSV 
Station and the LocalWeatherData file.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.parser;

import csv.mapping.LocalWeatherDataMapper;
import csv.mapping.StationMapper;
import csv.model.LocalWeatherData;
import csv.model.Station;
import de.bytefish.jtinycsvparser.CsvParser;
import de.bytefish.jtinycsvparser.CsvParserOptions;
import de.bytefish.jtinycsvparser.tokenizer.StringSplitTokenizer;

public class Parsers {

    public static CsvParser<Station> StationParser() {

        return new CsvParser<>(new CsvParserOptions(true, new StringSplitTokenizer("\\|", true)), new StationMapper(() -> new Station()));
    }

    public static CsvParser<LocalWeatherData> LocalWeatherDataParser()
    {
        return new CsvParser<>(new CsvParserOptions(true, new StringSplitTokenizer(",", true)), new LocalWeatherDataMapper(() -> new LocalWeatherData()));
    }

}
```

## Elasticsearch ##

If you are working with [Elasticsearch] the data needs to modeled different to a Relational Database. Instead of modelling relations between data in separate files, you need to 
store all data neccessary for a query in a document. The Elasticsearch documentation states on [Handling Relationships](https://www.elastic.co/guide/en/elasticsearch/guide/current/relations.html):

> Elasticsearch, like most NoSQL databases, treats the world as though it were flat. An index is a flat collection of independent documents. 
> A single document should contain all of the information that is required to decide whether it matches a search request.

So the Elasticsearch mindset is to denormalize the data as much as possible, because the inverted index is built over the documents and only this allows efficient queries.

#### Model ####

We also need to define how the property names are serialized in the JSON document. This is done by annotating a property with the Jackson ``JsonProperty`` annotation.

##### GeoLocation #####

If you want to define a property in your data as an Elasticsearch ``GeoPoint`` type, it needs to have at least the latitude or longitude with the property 
names ``lat`` and ``lon``.

This can easily be implemented with a custom class, that we call ``GeoLocation``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public class GeoLocation {

    @JsonProperty("lat")
    public double lat;

    @JsonProperty("lon")
    public double lon;

    public GeoLocation() {}

    public GeoLocation(double lat, double lon) {
        this.lat = lat;
        this.lon = lon;
    }
}
```

##### Station #####

The station has the same properties like the CSV file. It has the GPS informations of the station in a ``GeoLocation`` property.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.elasticsearch.common.geo.GeoPoint;

public class Station {

    @JsonProperty("wban")
    public String wban;

    @JsonProperty("name")
    public String name;

    @JsonProperty("state")
    public String state;

    @JsonProperty("location")
    public String location;

    @JsonProperty("coordinates")
    public GeoLocation geoLocation;

}
```

##### LocalWeatherData #####

The ``LocalWeatherData`` contains the actual temperature, wind speed, pressure and so on. It also contains the ``Station``, 
that generated the measurements.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Date;

public class LocalWeatherData {

    @JsonProperty("station")
    public Station station;

    @JsonProperty("dateTime")
    public Date dateTime;

    @JsonProperty("temperature")
    public Float temperature;

    @JsonProperty("windSpeed")
    public Float windSpeed;

    @JsonProperty("stationPressure")
    public Float stationPressure;

    @JsonProperty("skyCondition")
    public String skyCondition;
}
```

#### Mapping ####

Now the Elasticsearch mapping needs to be defined. This is done by implementing an ``IObjectMapping`` as explained above.

The ``AbstractMap`` base class can be used to simplify the mapping creation.

##### LocalWeatherDataMapper #####

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package elastic.mapping;

import org.elasticsearch.cluster.metadata.IndexMetaData;
import org.elasticsearch.common.settings.Settings;
import org.elasticsearch.index.mapper.core.DateFieldMapper;
import org.elasticsearch.index.mapper.core.FloatFieldMapper;
import org.elasticsearch.index.mapper.core.StringFieldMapper;
import org.elasticsearch.index.mapper.geo.GeoPointFieldMapper;
import org.elasticsearch.index.mapper.object.ObjectMapper;
import org.elasticsearch.index.mapper.object.RootObjectMapper;

public class LocalWeatherDataMapper extends AbstractMap {

    private static final String INDEX_TYPE = "document";

    public LocalWeatherDataMapper() {
        super(INDEX_TYPE, "1.0.0");
    }

    @Override
    protected void configure(RootObjectMapper.Builder builder) {
        builder
                .add(new DateFieldMapper.Builder("dateTime"))
                .add(new FloatFieldMapper.Builder("temperature"))
                .add(new FloatFieldMapper.Builder("windSpeed"))
                .add(new FloatFieldMapper.Builder("stationPressure"))
                .add(new StringFieldMapper.Builder("skyCondition"))
                .add(new ObjectMapper.Builder("station")
                        .add(new StringFieldMapper.Builder("wban"))
                        .add(new StringFieldMapper.Builder("name"))
                        .add(new StringFieldMapper.Builder("state"))
                        .add(new StringFieldMapper.Builder("location"))
                        .add(new GeoPointFieldMapper.Builder("coordinates")
                                .enableLatLon(true)
                                .enableGeoHash(false))
                        .nested(ObjectMapper.Nested.newNested(true, false)));
    }

    @Override
    protected void configure(Settings.Builder builder) {
        builder
                .put(IndexMetaData.SETTING_VERSION_CREATED, 1)
                .put(IndexMetaData.SETTING_CREATION_DATE, System.currentTimeMillis());
    }
}
```

### Converting between the CSV and Elasticsearch model ###

What's left is converting between the CSV data and the object-oriented JSON document. 

This is done by implementing a ``LocalWeatherDataConverter`` class, that takes the flat CSV ``Station`` and ``LocalWeatherData`` 
and builds the hierachial Elasticsearch model.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package converter;


import elastic.model.GeoLocation;
import elastic.model.Station;
import org.elasticsearch.common.geo.GeoPoint;
import utils.DateUtilities;

import java.sql.Date;
import java.time.ZoneId;
import java.time.ZoneOffset;

public class LocalWeatherDataConverter {

    public static elastic.model.LocalWeatherData convert(csv.model.LocalWeatherData csvLocalWeatherData, csv.model.Station csvStation) {

        elastic.model.LocalWeatherData elasticLocalWeatherData = new elastic.model.LocalWeatherData();

        elasticLocalWeatherData.dateTime = DateUtilities.from(csvLocalWeatherData.getDate(), csvLocalWeatherData.getTime(), ZoneOffset.ofHours(csvStation.getTimeZone()));
        elasticLocalWeatherData.skyCondition = csvLocalWeatherData.getSkyCondition();
        elasticLocalWeatherData.stationPressure = csvLocalWeatherData.getStationPressure();
        elasticLocalWeatherData.temperature = csvLocalWeatherData.getDryBulbCelsius();
        elasticLocalWeatherData.windSpeed = csvLocalWeatherData.getWindSpeed();

        // Convert the Station data:
        elasticLocalWeatherData.station = convert(csvStation);

        return elasticLocalWeatherData;
    }

    public static elastic.model.Station convert(csv.model.Station csvStation) {
        elastic.model.Station elasticStation = new elastic.model.Station();

        elasticStation.wban = csvStation.getWban();
        elasticStation.name = csvStation.getName();
        elasticStation.state = csvStation.getState();
        elasticStation.location = csvStation.getLocation();
        elasticStation.geoLocation = new GeoLocation(csvStation.getLatitude(), csvStation.getLongitude());

        return elasticStation;
    }
}
```

### Integration Test ###

And finally it is time to connect the parts into an integration test. You can see how to instantiate the Elasticsearch Mapping, 
how to configure the ``BulkProcessor``, how to wrap the original Elasticsearch ``Client`` in our own client. Then the Index is 
created, the mapping is put into Elasticsearch and the ``Stream`` of data is indexed.

The ``Stream`` is created by using the ``CsvParser`` instances and converting the flat representation into the Elasticsearch 
representation. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import converter.LocalWeatherDataConverter;
import csv.parser.Parsers;
import elastic.client.ElasticSearchClient;
import elastic.client.bulk.configuration.BulkProcessorConfiguration;
import elastic.client.bulk.options.BulkProcessingOptions;
import elastic.mapping.IObjectMapping;
import org.elasticsearch.client.transport.TransportClient;
import org.elasticsearch.common.transport.InetSocketTransportAddress;
import org.junit.Ignore;
import org.junit.Test;

import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystems;
import java.nio.file.Path;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Ignore("Integration Test")
public class IntegrationTest {

    @Test
    public void bulkProcessingTest() throws Exception {

        // Describes how to build the Index:
        IObjectMapping mapping = new elastic.mapping.LocalWeatherDataMapper();

        // Bulk Options for the Wrapped Client:
        BulkProcessorConfiguration bulkConfiguration = new BulkProcessorConfiguration(BulkProcessingOptions.builder()
                .setBulkActions(100)
                .build());

        // Create a new Client with default options:
        try (TransportClient transportClient = TransportClient.builder().build()) {

            transportClient.addTransportAddress(new InetSocketTransportAddress(InetAddress.getByName("127.0.0.1"), 9300));

            // Now wrap the Elastic client in our bulk processing client:
            try (ElasticSearchClient<elastic.model.LocalWeatherData> client = new ElasticSearchClient<>(transportClient, "weather_data", mapping, bulkConfiguration)) {

                // Create the Index:
                client.createIndex();

                // Create the Mapping:
                client.createMapping();

                // And now process the data stream:
                try (Stream<elastic.model.LocalWeatherData> weatherDataStream = getData()) {
                    client.index(weatherDataStream);
                }
            }
        }
    }

    private static Stream<elastic.model.LocalWeatherData> getData() {

        // Data to read from:
        Path stationFilePath = FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503station.txt");
        Path weatherDataFilePath = FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503hourly.txt");

        try (Stream<csv.model.Station> stationStream = getStations(stationFilePath)) {

            // Get a Map of Stations for faster Lookup:
            Map<String, csv.model.Station> stationMap = stationStream
                    .collect(Collectors.toMap(csv.model.Station::getWban, x -> x));

            // Now read the LocalWeatherData from CSV:
            return getLocalWeatherData(weatherDataFilePath)
                    .filter(x -> stationMap.containsKey(x.getWban()))
                    .map(x -> {
                        // Get the matching Station:
                        csv.model.Station station = stationMap.get(x.getWban());
                        // Convert to the Elastic Representation:
                        return LocalWeatherDataConverter.convert(x, station);
                    });
        }
    }

    private static Stream<csv.model.Station> getStations(Path path) {
        return Parsers.StationParser().readFromFile(path, StandardCharsets.US_ASCII)
                .filter(x -> x.isValid())
                .map(x -> x.getResult());
    }


    private static Stream<csv.model.LocalWeatherData> getLocalWeatherData(Path path) {
        return Parsers.LocalWeatherDataParser().readFromFile(path, StandardCharsets.US_ASCII)
                .filter(x -> x.isValid())
                .map(x -> x.getResult());

    }
}
```

## Visualizing the Data with Kibana ##

[Kibana] is a front-end to visualize the indexed data stored in an [Elasticsearch] database. It's possible to create various graphs (line charts, pie charts, tilemaps, ...) and combine the 
created visualizations into custom dashboards. [Kibana] also updates the dashboard as soon as new data is indexed in Elasticsearch, which is a really cool feature to show your customers.

In the following example I want to show how to create a Tile Map, that shows the Average temperature of March 2015.

### Starting Kibana ###

After starting the [Kibana] you can access the front-end using a browser and visiting:

```
http://localhost:5601
```

### 1. Configure the Index Pattern ###

In the example application the created index was called ``weather_data``. To visualize this index with [Kibana], an index pattern must be configured.

You are going to the *Settings* tab and set the *Index name or pattern* to ``weather_data``:

<a href="/static/images/blog/elasticsearch_java/01_create_tilemap_configure_index_pattern.jpg">
	<img src="/static/images/blog/elasticsearch_java/01_create_tilemap_configure_index_pattern.jpg" alt="Creating the Initial Index Pattern" />
</a>

### 2. Inspecting the Index Pattern ###

<a href="/static/images/blog/elasticsearch_java/02_create_tilemap_weather_data_mapping.jpg">
	<img src="/static/images/blog/elasticsearch_java/02_create_tilemap_weather_data_mapping.jpg" alt="Inspecting the Weather Data Index Pattern" />
</a>

### 3. Create the Tile Map Visualization ###

<a href="/static/images/blog/elasticsearch_java/03_create_tilemap_create_tilemap_visualization.jpg">
	<img src="/static/images/blog/elasticsearch_java/03_create_tilemap_create_tilemap_visualization.jpg" alt="Create Tile Map Visualization Step 1" />
</a>

### 4. Create the Visualization from a New Search ###

We haven't stored any searches over the index yet, so the tile map needs to be created from a new search:

<a href="/static/images/blog/elasticsearch_java/04_create_tilemap_new_search.jpg">
	<img src="/static/images/blog/elasticsearch_java/04_create_tilemap_new_search.jpg" alt="Create New Search for the Tile Map" />
</a>

### 5. Choosing the Geocordinates for the Tile Map markers ###

The indexed data contains the GPS coordinates of each station. We are going to choose these GPS positions as *Geo Coordinates*:

<a href="/static/images/blog/elasticsearch_java/05_create_tilemap_geo_coordinates.jpg">
	<img src="/static/images/blog/elasticsearch_java/05_create_tilemap_geo_coordinates.jpg" alt="Choose Geo Coordinates from the Index" />
</a>

### 6. Inspecting the Geo Coordinates ###

There is only one *Geo Position* property in the index. Kibana should automatically choose this property, but you should inspect to 
see if the correct values has been determined:

<a href="/static/images/blog/elasticsearch_java/06_create_tilemap_geo_coordinates_set.jpg">
	<img src="/static/images/blog/elasticsearch_java/06_create_tilemap_geo_coordinates_set.jpg" alt="Inspecting the Geocordinates" />
</a>


### 7. Adding the Average Temperature Value ###

We want to visualize the Average Temperature, add a new value. *Aggregation* must be set to ``Average`` and *Field* must be set to ``temperature``:

<a href="/static/images/blog/elasticsearch_java/07_create_tilemap_adding_temperature_value.jpg">
	<img src="/static/images/blog/elasticsearch_java/07_create_tilemap_adding_temperature_value.jpg" alt="Adding Value: Average Temperature" />
</a>

### 8. Adjusting the Interval ###

You don't see values yet. This is because of the search interval [Kibana] defaults to. The indexed data is from March 2015, but Kibana visualize only 
the latest 15 Minutes by default. You need to set the interval to a larger time interval, by adjusting it in the upper right corner of the Kibana 
front-end.

I have highlighted it with a red marker in the following screenshot:

<a href="/static/images/blog/elasticsearch_java/08_create_tilemap_adjust_interval.jpg">
	<img src="/static/images/blog/elasticsearch_java/08_create_tilemap_adjust_interval.jpg" alt="Inspecting the Weather Data Index Pattern" />
</a>

### Final Visualization ###

And now you can enjoy the final visualization of the Average temperature in March 2015:

<a href="/static/images/blog/elasticsearch_net/kibana.jpg">
	<img src="/static/images/blog/elasticsearch_net/thumbs/kibana_thumb.jpg" alt="Kibana Map Weather Visualization" />
</a>

## Conclusion ##

Getting started with [Elasticsearch] in Java was harder, compared to the .NET version. It should be much easier to create a mapping programmatically 
with the official Elasticsearch client. On the other hand, I found the source code of [Elasticsearch] highly readable and it wasn't hard to implement 
a simpler client by myself.

[Kibana] is a nice front-end for quickly visualizing data, especially the Tile Map is an amazing feature.

I hope you had fun reading this article, and it gave you some insight on how to work with Elasticsearch in Java.


[elastic]: https://www.elastic.co/
[Kibana]: https://www.elastic.co/products/kibana
[performance consideration]: https://www.elastic.co/blog/performance-considerations-elasticsearch-indexing
[Elasticsearch Definitive guide]: https://www.elastic.co/guide/en/elasticsearch/guide/current/mapping-intro.html#core-fields
[Mapping]: https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping.html
[PUT Mapping API]: https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-put-mapping.html
[Elasticsearch Reference]: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
[MIT License]: https://opensource.org/licenses/MIT
[Apache Lucene]: https://lucene.apache.org/
[Elasticsearch]: https://www.elastic.co/products/elasticsearch
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser/
[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd
[Query DSL]: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
[Introducing the Query Language]: https://www.elastic.co/guide/en/elasticsearch/reference/current/_introducing_the_query_language.html

