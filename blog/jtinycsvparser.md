title: JTinyCsvParser
date: 2016-01-08 15:02
tags: csv, tinycsvparser, jtinycsvparser
category: csv, jtinycsvparser, java
slug: jtinycsvparser
author: Philipp Wagner
summary: This article introduces JTinyCsvParser, which is a Java 1.8 Framework for CSV parsing.

[MIT License]: https://opensource.org/licenses/MIT
[JTinyCsvParser]: https://github.com/bytefish/JTinyCsvParser
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[Parallel Streams]: https://docs.oracle.com/javase/tutorial/collections/streams/parallelism.html

I wanted to learn Java 1.8 and about its new Features: Lambda Functions and Streams. So I have ported [TinyCsvParser] over to Java and 
named it [JTinyCsvParser]. The library makes mapping between a CSV file and a Java class very easy and provides a nice Streaming API:

* [https://github.com/bytefish/JTinyCsvParser](https://github.com/bytefish/JTinyCsvParser)

It should be one of the fastest CSV Parsers in Java 1.8, although I didn't run benchmarks against any of the available solutions. The parser is able 
to read and map ``4.5`` **Million** lines in ``12`` seconds (and I didn't optimize anything yet). That means [JTinyCsvParser] for Java is as fast as 
[TinyCsvParser] for .NET.

This article is an introduction to [JTinyCsvParser], it includes a section on benchmarking the [JTinyCsvParser] and hopefully has some interesting content.

## Basic Usage ##

This is an example for the most common use of [JTinyCsvParser]. 

Imagine we have list of Persons in a CSV file ``persons.csv`` with their first name, last name and birthdate.

```
Philipp,Wagner,1986/05/12
Max,Musterman,2014/01/02
```

The corresponding domain model in our system might look like this.

```java
public class Person {

    private String firstName;
    private String lastName;
    private LocalDate BirthDate;

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public LocalDate getBirthDate() {
        return BirthDate;
    }

    public void setBirthDate(LocalDate birthDate) {
        BirthDate = birthDate;
    }
}
```

When using [JTinyCsvParser] you have to define the mapping between the CSV File and your domain model:

```java
public class PersonMapping extends CsvMapping<Person> {

    public PersonMapping(IObjectCreator creator) {
        super(creator);

        Map(0, String.class, Person::setFirstName);
        Map(1, String.class, Person::setLastName);
        Map(2, LocalDate.class, Person::setBirthDate);
    }
}
```

And then it can be used to read the Results. Please note, that the ``CsvParser`` returns a ``Stream``, so 
in this example they are turned into a list first.

```java
public class CsvParserTest {

    @Test
    public void testParse() throws Exception {
        CsvParserOptions options = new CsvParserOptions(false, ",");
        PersonMapping mapping = new PersonMapping(() -> new Person());

        CsvParser<Person> parser = new CsvParser<>(options, mapping);

        ArrayList<String> csvData = new ArrayList<>();

        // Simulate CSV Data:
        csvData.add("Philipp,Wagner,1986-05-12");
        csvData.add(""); // An empty line... Should be skipped.
        csvData.add("Max,Musterman,2000-01-07");

        List<CsvMappingResult<Person>> result =  parser.parse(csvData)
                .collect(Collectors.toList()); // turn it into a List!

        Assert.assertNotNull(result);

        Assert.assertEquals(2, result.size());

        // Get the first person:
        Person person0 = result.get(0).getResult();

        Assert.assertEquals("Philipp", person0.firstName);
        Assert.assertEquals("Wagner", person0.lastName);
        Assert.assertEquals(1986, person0.getBirthDate().getYear());
        Assert.assertEquals(5, person0.getBirthDate().getMonthValue());
        Assert.assertEquals(12, person0.getBirthDate().getDayOfMonth());

        // Get the second person:
        Person person1 = result.get(1).getResult();

        Assert.assertEquals("Max", person1.firstName);
        Assert.assertEquals("Musterman", person1.lastName);
        Assert.assertEquals(2000, person1.getBirthDate().getYear());
        Assert.assertEquals(1, person1.getBirthDate().getMonthValue());
        Assert.assertEquals(7, person1.getBirthDate().getDayOfMonth());
    }
}
```


## Benchmark ##

### Dataset ###

In this benchmark the local weather data in March 2015 gathered by all weather stations in the USA is parsed. 

You can obtain the data ``QCLCD201503.zip`` from:
 
* [http://www.ncdc.noaa.gov/orders/qclcd](http://www.ncdc.noaa.gov/orders/qclcd)

The File size is ``557 MB`` and it has ``4,496,262`` lines.

### Setup ###

#### Software ###

The Java Version used is ``1.8.0_66``.

```
C:\Users\philipp>java -version
java version "1.8.0_66"
Java(TM) SE Runtime Environment (build 1.8.0_66-b18)
Java HotSpot(TM) 64-Bit Server VM (build 25.66-b18, mixed mode)
```

#### Hardware ####

* Intel (R) Core (TM) i5-3450 
* Hitachi HDS721010CLA330 (1 TB Capacity, 32 MB Cache, 7200 RPM)
* 16 GB RAM 

### Measuring the Elapsed Time ###

Working with dates and timespans has always been **hell** in Java. 

Java 1.8 has finally introduced new classes like ``LocalDate``, ``LocalDateTime`` or ``Duration`` to work with time. Combined with lambda functions we can 
easily write a nice helper class ``MeasurementUtils``, that measures the elapsed time of a function.

You simply have to pass a description and an ``Action`` into the ``MeasurementUtils.MeasureElapsedTime`` method, and it will print out the elapsed time.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jtinycsvparser.utils;

import java.time.Duration;
import java.time.Instant;

public class MeasurementUtils {

    /**
     * Java 1.8 doesn't have a Consumer without parameters (why not?), so we
     * are defining a FunctionalInterface with a nullary function.
     *
     * I call it Action, so I am consistent with .NET.
     */
    @FunctionalInterface
    public interface Action {

        void invoke();

    }

    public static void MeasureElapsedTime(String description, Action action) {
        Duration duration = MeasureElapsedTime(action);
        System.out.println(String.format("[%s] %s", description, duration));
    }

    public static Duration MeasureElapsedTime(Action action) {
        Instant start = Instant.now();

        action.invoke();

        Instant end = Instant.now();

        return Duration.between(start, end);
    }
}
```

### Reading a File Sequentially ###

First we have to find out, if the CSV parsing is an I/O or CPU bound task. The lower bound of the CSV Parsing is obviously given by the time needed to read a text 
file, the actual CSV parsing and mapping cannot be any faster. I am using ``Files.lines`` to get a consume ``Stream<String>``, which is also used in [JTinyCsvParser] 
to read a file.

#### Benchmark Code ####

```java
@Test
public void testReadFromFile_SequentialRead() {

    MeasurementUtils.MeasureElapsedTime("LocalWeatherData_SequentialRead", () -> {

        // Read the file. Make sure to wrap it in a try, so the file handle gets disposed properly:
        try(Stream<String> stream = Files.lines(FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503hourly.txt"), StandardCharsets.UTF_8)) {

            List<String> result = stream
                    .collect(Collectors.toList()); // turn it into a List!

            // Make sure we got the correct amount of lines in the file:
            Assert.assertEquals(4496263, result.size());

        } catch(IOException e) {
            throw new RuntimeException(e);
        }
        
    });
}
``` 

Make sure to always close the Stream returned by ``Files.lines``, because it is not closed automatically!

#### Benchmark Result ####

```
[LocalWeatherData_SequentialRead] PT4.258S
```

Reading the CSV File takes something around ``4.3`` seconds. So the entire mapping from CSV to objects cannot be faster, than ``4.3`` seconds.

#### On Closing the Stream ####

Oh I do not really understand, why ``Files.lines`` has to be wrapped in a ``try(...)`` block to get closed. After all the method returns a 
``Stream<String>``... Why on earth can't the Stream be automatically disposed when the entire ``Stream`` has been consumed? That also 
means I have to impose the closing of the Stream returned by ``Files.lines`` on the user of [JTinyCsvParser]. 

This is **by no means obvious** (except through comments maybe), but there seems to be no way around in Java 1.8.

### JTinyCsvParser ###

In order to parse a CSV file into a strongly-typed object, you have to define the domain model in your application and a ``CsvMapping`` for the class.

#### Domain Model #####

```java
public class LocalWeatherData
{
    private String WBAN;

    private LocalDate Date;

    private String SkyCondition;

    public String getWBAN() {
        return WBAN;
    }

    public void setWBAN(String WBAN) {
        this.WBAN = WBAN;
    }

    public LocalDate getDate() {
        return Date;
    }

    public void setDate(LocalDate date) {
        Date = date;
    }

    public String getSkyCondition() {
        return SkyCondition;
    }

    public void setSkyCondition(String skyCondition) {
        SkyCondition = skyCondition;
    }
}
```

#### CsvMapping ####

We only want to map the columns ``WBAN`` (Column 0), ``Date`` (Column 1) and ``SkyCondition`` (Column 4) to the Domain Model, which is done by using the ``MapProperty`` function.

```java
public class LocalWeatherDataMapper extends CsvMapping<LocalWeatherData>
{
    public LocalWeatherDataMapper(IObjectCreator creator)
    {
        super(creator);

        MapProperty(0, String.class, LocalWeatherData::setWBAN);
        MapProperty(1, LocalDate.class, LocalWeatherData::setDate, new LocalDateConverter(DateTimeFormatter.ofPattern("yyyyMMdd")));
        MapProperty(4, String.class, LocalWeatherData::setSkyCondition);
    }
}
```

### Benchmarking JTinyCsvParser (Single Threaded) ###

#### Benchmark Code ####

```java
@Test
public void testReadFromFile_LocalWeatherData_Sequential() {

    // Not in parallel:
    CsvParserOptions options = new CsvParserOptions(true, ",", false);
    // The Mapping to employ:
    LocalWeatherDataMapper mapping = new LocalWeatherDataMapper(() -> new LocalWeatherData());
    // Construct the parser:
    CsvParser<LocalWeatherData> parser = new CsvParser<>(options, mapping);
    // Measure the Time using the MeasurementUtils:
    MeasurementUtils.MeasureElapsedTime("LocalWeatherData_Sequential_Parse", () -> {

        // Read the file. Make sure to wrap it in a try, so the file handle gets disposed properly:
        try(Stream<CsvMappingResult<LocalWeatherData>> stream = parser.readFromFile(FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503hourly.txt"), StandardCharsets.UTF_8)) {

                List<CsvMappingResult<LocalWeatherData>> result = stream
                        .filter(e -> e.isValid())
                        .collect(Collectors.toList()); // turn it into a List!

            Assert.assertEquals(4496262, result.size());
        }
    });
}
```

#### Benchmark Results ####

```
[LocalWeatherData_Sequential_Parse] PT19.252S
```

Parsing the entire file takes approximately 20 seconds. I think this is a reasonable speed and it is comparable to the [TinyCsvParser] performance for a Single Threaded run. 
A lot of stuff is going on in the parsing, especially Auto Boxing Values is a time-consuming task I guess. I didn't profile the entire library, so I cannot tell exactely where 
one could squeeze out the last CPU cycles.

### Benchmarking JTinyCsvParser (Parallel Streams, Without Bugfix) ###

Java 1.8 introduced Parallel Streams to simplify parallel computing in applications. 

You can basically we can turn every simple Stream into a Parallel Stream, by calling the ``parallel()`` method on it. One weird thing is, that I don't have any control over 
the degree of parallelism at this point. By default the number of processors is used for the default ForkJoinPool. But describing Parallel Streams in Java 1,.8 is out of scope 
for this article. 

There is a great write-up on parallel processing in Java using Streams by Marko Topolnik:

* [https://www.airpair.com/java/posts/parallel-processing-of-io-based-data-with-java-streams](https://www.airpair.com/java/posts/parallel-processing-of-io-based-data-with-java-streams)

#### Why using a Parallel Stream? ####

We have learnt, that the mapping to objects is largely CPU bound. It is a well-defined problem and by throwing some more cores at it, we should see a significantly improved performance. 

#### Benchmark Code ####

In order to process the data in parallel, you have to set the ``parallel`` parameter in the ``CsvParserOption``. 

```java
@Test
public void testReadFromFile_LocalWeatherData_Parallel() {

    // See the third constructor argument. It sets the Parallel processing to true!
    CsvParserOptions options = new CsvParserOptions(true, ",", true);
    // The Mapping to employ:
    LocalWeatherDataMapper mapping = new LocalWeatherDataMapper(() -> new LocalWeatherData());
    // Construct the parser:
    CsvParser<LocalWeatherData> parser = new CsvParser<>(options, mapping);
    // Measure the Time using the MeasurementUtils:
    MeasurementUtils.MeasureElapsedTime("LocalWeatherData_Parallel_Parse", () -> {

        // Read the file. Make sure to wrap it in a try, so the file handle gets disposed properly:
        try(Stream<CsvMappingResult<LocalWeatherData>> stream = parser.readFromFile(FileSystems.getDefault().getPath("C:\\Users\\philipp\\Downloads\\csv", "201503hourly.txt"), StandardCharsets.UTF_8)) {

            List<CsvMappingResult<LocalWeatherData>> result = stream
                    .filter(e -> e.isValid())
                    .collect(Collectors.toList()); // turn it into a List!

            Assert.assertEquals(4496262, result.size());

        }
    });
}
```

#### Benchmark Results ####

The results are not satisfying. Although all cores are utilized during processing the file, it actually leads to a slow-down.

```
[LocalWeatherData_Parallel_Parse] PT26.232S
```

Why is that?

Well in order to parallelize a task Java has to split the problem into sub problems somehow. This is done by using a ``Spliterator``, which basically means "splittable Iterator". 
The ``Spliterator`` has a method ``trySplit()``, that splits off a chunk of elements to be processed by the threads. I assume, that the estimation about the size of the data 
is not known ahead and that's why Java 1.8 initializes the estimated size with ``Long.MAX_VALUE`` (unknown size).

We can find the confirmation for it, if we take a look into the OpenJDK Bugtracker titled:

* [JDK-8072773 Files.lines needs a better splitting implementation for stream source](https://bugs.openjdk.java.net/browse/JDK-8072773)


### Benchmarking JTinyCsvParser (Parallel Streams, With Bugfix) ###

We have seen, that there is a bug in the ``Spliterator`` for ``Files.lines``, but the OpenJDK Bug ticket [JDK-8072773](https://bugs.openjdk.java.net/browse/JDK-8072773) also references a bug fix. 

When I backport the bugfix mentioned in [JDK-8072773](https://bugs.openjdk.java.net/browse/JDK-8072773) to Java 1.8, then the file is split correctly. The file is then parsed in `12` seconds.

```
[LocalWeatherData_Parallel_Parse] PT11.773S
```

But since the OpenJDK code is released under terms of the GPL v2 license, I cannot include the mentioned bugfix into [JTinyCsvParser] the parser.

## Conclusion ##

I have presented you [JTinyCsvParser], which is a small CSV Parser I have written. It provides a Streaming API, so the user can build custom processing pipelines.

In the end I have to admit, that Java 1.8 makes writing Java a little less painful. There are a lot of nice additions like Streams and lambda functions. But honestly I will 
never get warm with type erasure. Type Erasure is really a major pain to deal with, porting [JTinyCsvParser] over from .NET confirmed this to me. Anyway it was a good exercise 
to see what Java 1.8 offers and sharpen my skills... if I ever have to read a Java codebase.

I hope this article was a nice read and gave you some ideas how to use Java 1.8 to your own advance.