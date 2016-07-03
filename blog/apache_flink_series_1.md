title: Building Applications with Apache Flink (Part 1): Dataset, Data Preparation and Modelling the Problem
date: 2016-06-19 14:27
tags: java, flink, elasticsearch, postgresql
category: java
slug: apache_flink_example
author: Philipp Wagner
summary: This article shows how to work with Apache Flink.

In this series of articles we are building an application, that processes the hourly weather measurements of more than 1,600 
weather stations with Apache Flink. The articles will show how to write custom Source functions for generating data and is 
going to implement custom Sink functions for PostgreSQL and Elasticsearch.

## Source Code ##

You can find the full source code for the example in my git repository at:

* [https://github.com/bytefish/FlinkExperiments](https://github.com/bytefish/FlinkExperiments)

## Dataset ##

The data is the [Quality Controlled Local Climatological Data (QCLCD)]: 

> Quality Controlled Local Climatological Data (QCLCD) consist of hourly, daily, and monthly summaries for approximately 
> 1,600 U.S. locations. Daily Summary forms are not available for all stations. Data are available beginning January 1, 2005 
> and continue to the present. Please note, there may be a 48-hour lag in the availability of the most recent data.

The data is available as CSV files at:

* [http://www.ncdc.noaa.gov/orders/qclcd/](http://www.ncdc.noaa.gov/orders/qclcd/)

We are going to use the data from March 2015, which is located in the zipped file ``QCLCD201503.zip``.

## Analyzing the Data ##

The first step when processing data is to analyze the data, so we can model the problem in the application.

The weather data measurements are given as CSV files contained in the file ``201503hourly.txt``. The list of corresponding weather stations 
is given in the file ``201503station.txt``. The weather stations are identified by their WBAN number, which is an abbreviation for 
*W*eather-*B*ureau-*A*rmy-*N*avy.

The local weather data in ``201503hourly.txt`` has more than 30 columns, such as the WBAN Identifier (Column 1), time of measurement 
(Columns 2, 3), Sky Condition (Column 5), Air Temperature (Column 13), Wind Speed (Column 25) and Pressure level (Column 31). The column 
delimiter is a Comma character (``,``). 

The data of the weather stations is given in the ``201503station.txt`` file. It has 14 columns, such as the WBAN identifier (Column 1), 
a Name (Column 7) and most importantly the GPS position. The GPS position is given in latitude (Column 10) and longitude (Column 11). 
The measurements in the ``201503hourly.txt`` are given in local time, so we also need to take the stations timezone into account, which 
is given in the column 15. The column delimiter is a pipe symbol (``|``).

Missing data is indicated by an ``M``.

## Building the Domain Model ##

It's time to design the domain model, we want to work with. This domain model is going to be used throughout the application. The domain model 
should not include any persistence related details, such as foreign keys or framework-specific attributes. Do not pollute your domain model, 
always try to keep the concern separated.

In the example we need a class for a measurement (``LocalWeatherData``), a class for a station (``Station``) and a class for the GPS data (``GeoLocation``). 

We are designing the domain model as POJOs (Plain Old Java Objects), so they can be easily serialized and deserialized. 

### GeoLocation ###

The ``GeoLocation`` holds the latitude and longitude. 

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package model;

public class GeoLocation {

    private double lat;

    private double lon;

    public GeoLocation(){

    }

    public GeoLocation(double lat, double lon) {
        this.lat = lat;
        this.lon = lon;
    }

    public void setLat(double lat) {
        this.lat = lat;
    }

    public void setLon(double lon) {
        this.lon = lon;
    }

    public double getLat() {
        return lat;
    }

    public double getLon() {
        return lon;
    }
}
```

### Station ###

Each ``Station`` has an assigned ``GeoLocation``. We also keep track of its timezone, so we 

```
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package model;

public class Station {

    private String wban;

    private String name;

    private String state;

    private String location;

    private Integer timeZone;

    private GeoLocation geoLocation;

    public Station() {

    }

    public Station(String wban, String name, String state, String location, Integer timeZone, GeoLocation geoLocation) {
        this.wban = wban;
        this.name = name;
        this.state = state;
        this.location = location;
        this.timeZone = timeZone;
        this.geoLocation = geoLocation;
    }

    public void setWban(String wban) {
        this.wban = wban;
    }

    public void setName(String name) {
        this.name = name;
    }

    public void setState(String state) {
        this.state = state;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public void setTimeZone(Integer timeZone) {
        this.timeZone = timeZone;
    }

    public void setGeoLocation(GeoLocation geoLocation) {
        this.geoLocation = geoLocation;
    }

    public String getWban() {
        return wban;
    }

    public String getName() {
        return name;
    }

    public String getState() {
        return state;
    }

    public String getLocation() {
        return location;
    }

    public Integer getTimeZone() {
        return timeZone;
    }

    public GeoLocation getGeoLocation() {
        return geoLocation;
    }
}
```

### LocalWeatherData ###

Each ``LocalWeatherData`` measurement was generated by a ``Station``. We are interested in the time of measurements, temperature, wind speed, station pressure 
and sky condition. One could argue, that referencing the entire ``Station`` object is bad for performance and memory efficiency. But I have a huge dislike 
for premature optimization, so you should first focus on modelling the problem.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package model;

import java.time.LocalDate;
import java.time.LocalTime;

public class LocalWeatherData {

    private Station station;

    private LocalDate date;

    private LocalTime time;

    private Float temperature;

    private Float windSpeed;

    private Float stationPressure;

    private String skyCondition;

    public LocalWeatherData() {

    }

    public LocalWeatherData(Station station, LocalDate date, LocalTime time, Float temperature, Float windSpeed, Float stationPressure, String skyCondition) {
        this.station = station;
        this.date = date;
        this.time = time;
        this.temperature = temperature;
        this.windSpeed = windSpeed;
        this.stationPressure = stationPressure;
        this.skyCondition = skyCondition;
    }

    public void setStation(Station station) {
        this.station = station;
    }

    public void setDate(LocalDate date) {
        this.date = date;
    }

    public void setTime(LocalTime time) {
        this.time = time;
    }

    public void setTemperature(Float temperature) {
        this.temperature = temperature;
    }

    public void setWindSpeed(Float windSpeed) {
        this.windSpeed = windSpeed;
    }

    public void setStationPressure(Float stationPressure) {
        this.stationPressure = stationPressure;
    }

    public void setSkyCondition(String skyCondition) {
        this.skyCondition = skyCondition;
    }

    public Station getStation() {
        return station;
    }

    public LocalDate getDate() {
        return date;
    }

    public LocalTime getTime() {
        return time;
    }

    public Float getTemperature() {
        return temperature;
    }

    public Float getWindSpeed() {
        return windSpeed;
    }

    public Float getStationPressure() {
        return stationPressure;
    }

    public String getSkyCondition() {
        return skyCondition;
    }
}
```

## Parsing the CSV Data ##

### Model ###

The CSV data model is different from the application model. The CSV data model is a flat representation of the data.

#### LocalWeatherData ####



#### Station ####



### Mapper ###

#### LocalWeatherDataMapper ####

The measurement date is given in the format ``yyyyMMdd`` and the measurement time is given in the format ``HHmm``. That's why the 
``LocalDateConverter`` and ``LocalTimeConverter`` are instantiated with custom formats. 

The columns for temperature, wind speed and station pressure may include missing values indicated by a ``M``. That's why we need to map 
it with an ``IgnoreMissingValuesConverter``. The ``IgnoreMissingValuesConverter`` returns null, when it encounters the missing value sign 
instead of trying to parse the data.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.mapping;

import csv.converter.IgnoreMissingValuesConverter;
import csv.model.LocalWeatherData;
import de.bytefish.jtinycsvparser.builder.IObjectCreator;
import de.bytefish.jtinycsvparser.mapping.CsvMapping;
import de.bytefish.jtinycsvparser.typeconverter.FloatConverter;
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

        mapProperty(0, String.class, LocalWeatherData::setWban);
        mapProperty(1, LocalDate.class, LocalWeatherData::setDate, new LocalDateConverter(DateTimeFormatter.ofPattern("yyyyMMdd")));
        mapProperty(2, LocalTime.class, LocalWeatherData::setTime, new LocalTimeConverter(DateTimeFormatter.ofPattern("HHmm")));
        mapProperty(4, String.class, LocalWeatherData::setSkyCondition);
        mapProperty(12, Float.class, LocalWeatherData::setDryBulbCelsius, new IgnoreMissingValuesConverter<>(new FloatConverter(), "M"));
        mapProperty(24, Float.class, LocalWeatherData::setWindSpeed, new IgnoreMissingValuesConverter<>(new FloatConverter(), "M"));
        mapProperty(30, Float.class, LocalWeatherData::setStationPressure, new IgnoreMissingValuesConverter<>(new FloatConverter(), "M"));
    }
}
```

#### StationMapper ####

The ``StationMapper`` maps all of the 14 available columns. Again the Ground Height, Station Height and Barometer for some stations may be missing
in the data, so we also map them with an ``IgnoreMissingValuesConverter``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.mapping;

import csv.converter.IgnoreMissingValuesConverter;
import csv.model.Station;
import de.bytefish.jtinycsvparser.builder.IObjectCreator;
import de.bytefish.jtinycsvparser.mapping.CsvMapping;
import de.bytefish.jtinycsvparser.typeconverter.FloatConverter;
import de.bytefish.jtinycsvparser.typeconverter.IntegerConverter;

public class StationMapper extends CsvMapping<Station>
{
    public StationMapper(IObjectCreator creator)
    {
        super(creator);

        mapProperty(0, String.class, Station::setWban);
        mapProperty(1, String.class, Station::setWmo);
        mapProperty(2, String.class, Station::setCallSign);
        mapProperty(3, String.class, Station::setClimateDivisionCode);
        mapProperty(4, String.class, Station::setClimateDivisionStateCode);
        mapProperty(5, String.class, Station::setClimateDivisionStationCode);
        mapProperty(6, String.class, Station::setName);
        mapProperty(7, String.class, Station::setState);
        mapProperty(8, String.class, Station::setLocation);
        mapProperty(9, Float.class, Station::setLatitude);
        mapProperty(10, Float.class, Station::setLongitude);
        mapProperty(11, Integer.class, Station::setGroundHeight, new IgnoreMissingValuesConverter<>(new IntegerConverter()));
        mapProperty(12, Integer.class, Station::setStationHeight, new IgnoreMissingValuesConverter<>(new IntegerConverter()));
        mapProperty(13, Integer.class, Station::setBarometer, new IgnoreMissingValuesConverter<>(new IntegerConverter()));
        mapProperty(14, Integer.class, Station::setTimeZone);
    }
}
```

### Parser ###

A ``CsvParser`` defines how a CSV file is tokenized and mapped to a Java object. We are using a simple ``StringSplitTokenizer``, which splits a 
line at a given column delimiter. For the station file a pipe symbol ``|`` is used as a column delimiter. For the local weather data measurements 
a comma ``,`` is used as column delimiter.

Both ``CsvParser`` are set to ignore the header line.

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

## Mapping between CSV model and the Domain model ##

What's left is the mapping between the CSV model and the applications domain model. This is done by writing a simple converter, which takes the 
CSV representation of the data and returns the application model of the data. Such model mappings might look like a total overkill for this simple 
example, but it is the only way to not leak persistence details into your application.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package stream.sources.csv.converter;

import java.time.LocalDate;
import java.time.LocalTime;

public class LocalWeatherDataConverter {

    public static model.LocalWeatherData convert(csv.model.LocalWeatherData csvLocalWeatherData, csv.model.Station csvStation) {

        LocalDate date = csvLocalWeatherData.getDate();
        LocalTime time = csvLocalWeatherData.getTime();
        String skyCondition = csvLocalWeatherData.getSkyCondition();
        Float stationPressure = csvLocalWeatherData.getStationPressure();
        Float temperature = csvLocalWeatherData.getDryBulbCelsius();
        Float windSpeed = csvLocalWeatherData.getWindSpeed();

        // Convert the Station data:
        model.Station station = convert(csvStation);

        return new model.LocalWeatherData(station, date, time, temperature, windSpeed, stationPressure, skyCondition);
    }

    public static model.Station convert(csv.model.Station csvStation) {
        String wban = csvStation.getWban();
        String name = csvStation.getName();
        String state = csvStation.getState();
        String location = csvStation.getLocation();
        Integer timeZone = csvStation.getTimeZone();
        model.GeoLocation geoLocation = new model.GeoLocation(csvStation.getLatitude(), csvStation.getLongitude());

        return new model.Station(wban, name, state, location, timeZone, geoLocation);
    }

}
```

## Preparing the Data ##

If you analyze the data, you will notice, that the measurements are not sorted by the measurement timestamp. In order to simulate incoming weather data 
measurements as realistic as possible, we need to make sure the measurements are emitted with a monotonic increasing timestamp.

So we are going to write a small application, which sorts the CSV file by monotonically ascending measurement timestamps. The idea is to basically 
enumerate the entire dataset first, once it is enumerated the invalid lines are discarded. After the invalid lines have been discarded, we calculate 
the UTC timestamp of the measurement by taking the station zone offset into account. These coordinated timestamps (with their original index in file) 
are then sorted by the timestamp.

Finally this list of indices is used to sort the CSV file and write it into a new file ``201503hourly_sorted.txt``.

I have 16 GB RAM, so I can safely sort the entire dataset in memory. If the dataset becomes larger, this approach obviously does not scale.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package csv.sorting;

import csv.model.Station;
import csv.parser.Parsers;
import de.bytefish.jtinycsvparser.mapping.CsvMappingResult;
import org.apache.commons.lang3.tuple.ImmutablePair;

import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class PrepareWeatherData {

    public static void main(String[] args) throws Exception {

        // Path to read the CSV data from:
        final Path csvStationDataFilePath = FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv\\201503station.txt");
        final Path csvLocalWeatherDataUnsortedFilePath = FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv\\201503hourly.txt");
        final Path csvLocalWeatherDataSortedFilePath = FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv\\201503hourly_sorted.txt");

        // A map between the WBAN and Station for faster Lookups:
        final Map<String, Station> stationMap = getStationMap(csvStationDataFilePath);

        // Holds the List of Sorted DateTimes (including ZoneOffset):
        List<Integer> indices = new ArrayList<>();

        // Comparator for sorting the File:
        Comparator<OffsetDateTime> byMeasurementTime = (e1, e2) -> e1.compareTo(e2);

        // Get the sorted indices from the stream of LocalWeatherData Elements:
        try (Stream<CsvMappingResult<csv.model.LocalWeatherData>> stream = getLocalWeatherData(csvLocalWeatherDataUnsortedFilePath)) {

            // Holds the current line index, when processing the input Stream:
            AtomicInteger currentIndex = new AtomicInteger(1);

            // We want to get a list of indices, which sorts the CSV file by measurement time:
            indices = stream
                    // Skip the CSV Header:
                    .skip(1)
                    // Start by enumerating ALL mapping results:
                    .map(x -> new ImmutablePair<>(currentIndex.getAndAdd(1), x))
                    // Then only take those lines, that are actually valid:
                    .filter(x -> x.getRight().isValid())
                    // Now take the parsed entity from the CsvMappingResult:
                    .map(x -> new ImmutablePair<>(x.getLeft(), x.getRight().getResult()))
                    // Take only those measurements, that are also available in the list of stations:
                    .filter(x -> stationMap.containsKey(x.getRight().getWban()))
                    // Get the OffsetDateTime from the LocalWeatherData, which includes the ZoneOffset of the Station:
                    .map(x -> {
                        // Get the matching station:
                        csv.model.Station station = stationMap.get(x.getRight().getWban());
                        // Calculate the OffsetDateTime from the given measurement:
                        OffsetDateTime measurementTime = OffsetDateTime.of(x.getRight().getDate(), x.getRight().getTime(), ZoneOffset.ofHours(station.getTimeZone()));
                        // Build the Immutable pair with the Index again:
                        return new ImmutablePair<>(x.getLeft(), measurementTime);
                    })
                    // Now sort the Measurements by their Timestamp:
                    .sorted((x, y) -> byMeasurementTime.compare(x.getRight(), y.getRight()))
                    // Take only the Index:
                    .map(x -> x.getLeft())
                    // And turn it into a List:
                    .collect(Collectors.toList());
        }

        // Now sort the File by Line Number:
        writeSortedFileByIndices(csvLocalWeatherDataUnsortedFilePath, indices, csvLocalWeatherDataSortedFilePath);
    }

    private static void writeSortedFileByIndices(Path csvFileIn, List<Integer> indices, Path csvFileOut) {
        try {
            List<String> csvDataList = new ArrayList<>();

            // This is sorting for the dumb (like me). Read the entire CSV file, skipping the first line:
            try (Stream<String> lines = Files.lines(csvFileIn, StandardCharsets.US_ASCII).skip(1))
            {
                csvDataList = lines.collect(Collectors.toList());
            }
            // Now write the sorted file:
            try(BufferedWriter writer = Files.newBufferedWriter(csvFileOut)) {
                for (Integer index : indices) {
                    writer.write(csvDataList.get(index));
                    writer.newLine();
                }
            }
        } catch(Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static Stream<CsvMappingResult<csv.model.LocalWeatherData>> getLocalWeatherData(Path path) {
        return Parsers.LocalWeatherDataParser().readFromFile(path, StandardCharsets.US_ASCII);
    }

    private static Stream<csv.model.Station> getStations(Path path) {
        return Parsers.StationParser().readFromFile(path, StandardCharsets.US_ASCII)
                .filter(x -> x.isValid())
                .map(x -> x.getResult());
    }

    private static Map<String, csv.model.Station> getStationMap(Path path) {
        try (Stream<csv.model.Station> stationStream = getStations(path)) {
            return stationStream
                    .collect(Collectors.toMap(csv.model.Station::getWban, x -> x));
        }
    }
}
```

## Conclusion ##

In this part of the series we have analyzed the CSV data, wrote the neccessary classes to parse the files and 
preprocessed it.  We have defined the domain model, that we are going to work with and wrote a converter between 
the CSV data and the domain model.

The next part of the series shows how to write a source function for emitting the local weather data events to Apache Flink.

[Apache Flink]: https://flink.apache.org/
[Elasticsearch]: https://www.elastic.co
[ElasticUtils]: https://github.com/bytefish/ElasticUtils
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser
[Quality Controlled Local Climatological Data (QCLCD)]: https://www.ncdc.noaa.gov/data-access/land-based-station-data/land-based-datasets/quality-controlled-local-climatological-data-qclcd