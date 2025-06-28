title: flink-jam: Detect Traffic Congestion Patterns in Apache Flink
date: 2025-06-28 10:05
tags: osm, gis, flink
category: sql
slug: flink_jam_2
author: Philipp Wagner
summary: This post is the second article on flink-jam.

## Table of contents ##

[TOC]

## What we are going to build ##

In the last article we have been importing Open Street Map (OSM) data into a PostGIS database, then 
we've extracted the road and traffic light data available for the data. The queries are quite 
efficient by now, so we can query it in a millisecond range.

All code can be found in a Git repository at:

* [https://github.com/bytefish/flink-jam/tree/main](https://github.com/bytefish/flink-jam/tree/main)

In this article we are going to implement a Traffic Congestion Detection using the OSM data, Apache Flink 
and a generated mock dataset. We will see how to transform events, query the database, using the CEP for 
detecting patterns in data and generate warnings.

## Modelling the Road Traffic Data ##

We start by creating a `RawTrafficEvent`, which models the data a single vehicle sends to our service. As 
you can see it contains a `timestamp` the  event was recorded at, a `vehicleId` as a unique identifier of 
the vehicle, the position given as `latitude` and `longitude`, and finally the `speed`.

```java
package de.bytefish.flinkjam.models;

/**
 * Represents a raw real-time traffic event from a vehicle, before any enrichment.
 */
public class RawTrafficEvent implements java.io.Serializable {

    public long timestamp;
    public String vehicleId;
    public double latitude;
    public double longitude;
    public double speed;

    public RawTrafficEvent() {
    }

    public RawTrafficEvent(long timestamp, String vehicleId, double latitude, double longitude, double speed) {
        this.timestamp = timestamp;
        this.vehicleId = vehicleId;
        this.latitude = latitude;
        this.longitude = longitude;
        this.speed = speed;
    }

    // Getters
    public long getTimestamp() {
        return timestamp;
    }

    public String getVehicleId() {
        return vehicleId;
    }

    public double getLatitude() {
        return latitude;
    }

    public double getLongitude() {
        return longitude;
    }

    public double getSpeed() {
        return speed;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    public void setVehicleId(String vehicleId) {
        this.vehicleId = vehicleId;
    }

    public void setLatitude(double latitude) {
        this.latitude = latitude;
    }

    public void setLongitude(double longitude) {
        this.longitude = longitude;
    }

    public void setSpeed(double speed) {
        this.speed = speed;
    }

    @Override
    public String toString() {
        return "RawTrafficEvent{" +
                "timestamp=" + timestamp +
                ", vehicleId='" + vehicleId + '\'' +
                ", lat=" + latitude +
                ", lon=" + longitude +
                ", speed=" + speed +
                '}';
    }
}
```

The idea is to now enrich the data with the road and traffic light information, that we have 
extracted in a previous version. I intially thought about sending the road and traffic light 
information along with the `RawEventData`.

And if you are Apple Maps or Google Maps you are controlling their devices and are based on 
most recent maps. So I guess they *can* send along this information reliably and highly 
simplfy the entire pipeline.

Since we are not Apple or Google, we need to enrich the Event with the road information for 
the given GPS position in a `RoadEnrichedTrafficEvent`.

```java
package de.bytefish.flinkjam.models;

/**
 * Represents a traffic event enriched with road segment data.
 */
public class RoadEnrichedTrafficEvent implements java.io.Serializable  {
    public long timestamp;
    public String vehicleId;
    public double latitude;
    public double longitude;
    public double speed;
    public String roadSegmentId;
    public int speedLimitKmh;
    public String roadType;

    public RoadEnrichedTrafficEvent() {
    }

    public RoadEnrichedTrafficEvent(RawTrafficEvent rawEvent, String roadSegmentId, int speedLimitKmh, String roadType) {
        this.timestamp = rawEvent.timestamp;
        this.vehicleId = rawEvent.vehicleId;
        this.latitude = rawEvent.latitude;
        this.longitude = rawEvent.longitude;
        this.speed = rawEvent.speed;
        this.roadSegmentId = roadSegmentId;
        this.speedLimitKmh = speedLimitKmh;
        this.roadType = roadType;
    }

    // Getters (needed for Flink's POJO detection and keying)
    public long getTimestamp() {
        return timestamp;
    }

    public String getVehicleId() {
        return vehicleId;
    }

    public String getRoadSegmentId() {
        return roadSegmentId;
    }

    public double getSpeed() {
        return speed;
    }

    public double getLatitude() {
        return latitude;
    }

    public double getLongitude() {
        return longitude;
    }

    public int getSpeedLimitKmh() {
        return speedLimitKmh;
    }

    public String getRoadType() {
        return roadType;
    }

    @Override
    public String toString() {
        return "RoadEnrichedTrafficEvent{" +
                "timestamp=" + timestamp +
                ", vehicleId='" + vehicleId + '\'' +
                ", latitude=" + latitude +
                ", longitude=" + longitude +
                ", speed=" + speed +
                ", roadSegmentId='" + roadSegmentId + '\'' +
                ", speedLimitKmh=" + speedLimitKmh +
                ", roadType='" + roadType + '\'' +
                '}';
    }
}
```

It's not useful to generate Traffic Warnings if a car is standing at a traffic light in 
a city. So we need to take our traffic light data into account and enrich the event with 
traffic lights in a `FullyEnrichedTrafficEvent`.

```java
package de.bytefish.flinkjam.models;

import java.util.List;
import java.util.Objects;

/**
 * Represents a fully enriched traffic event, including road segment and nearby traffic light data.
 * This is the event used for CEP.
 */
public class FullyEnrichedTrafficEvent implements java.io.Serializable {

    public long timestamp;
    public String vehicleId;
    public double latitude;
    public double longitude;
    public double speed;
    public String roadSegmentId;
    public int speedLimitKmh;
    public String roadType;
    public List<TrafficLightInfo> nearbyTrafficLights; // List of nearby traffic lights

    public FullyEnrichedTrafficEvent() {
    }

    public FullyEnrichedTrafficEvent(RoadEnrichedTrafficEvent roadEvent, List<TrafficLightInfo> nearbyTrafficLights) {
        this.timestamp = roadEvent.timestamp;
        this.vehicleId = roadEvent.vehicleId;
        this.latitude = roadEvent.latitude;
        this.longitude = roadEvent.longitude;
        this.speed = roadEvent.speed;
        this.roadSegmentId = roadEvent.roadSegmentId;
        this.speedLimitKmh = roadEvent.speedLimitKmh;
        this.roadType = roadEvent.roadType;
        this.nearbyTrafficLights = nearbyTrafficLights;
    }

    // Getters
    public long getTimestamp() {
        return timestamp;
    }

    public String getVehicleId() {
        return vehicleId;
    }

    public String getRoadSegmentId() {
        return roadSegmentId;
    }

    public double getSpeed() {
        return speed;
    }

    public double getLatitude() {
        return latitude;
    }

    public double getLongitude() {
        return longitude;
    }

    public int getSpeedLimitKmh() {
        return speedLimitKmh;
    }

    public String getRoadType() {
        return roadType;
    }

    public List<TrafficLightInfo> getNearbyTrafficLights() {
        return nearbyTrafficLights;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        FullyEnrichedTrafficEvent that = (FullyEnrichedTrafficEvent) o;
        return timestamp == that.timestamp &&
                Double.compare(that.speed, speed) == 0 &&
                Double.compare(that.latitude, latitude) == 0 &&
                Double.compare(that.longitude, longitude) == 0 &&
                speedLimitKmh == that.speedLimitKmh &&
                Objects.equals(vehicleId, that.vehicleId) &&
                Objects.equals(roadSegmentId, that.roadSegmentId) &&
                Objects.equals(roadType, that.roadType) &&
                Objects.equals(nearbyTrafficLights, that.nearbyTrafficLights);
    }

    @Override
    public int hashCode() {
        return Objects.hash(timestamp, vehicleId, latitude, longitude, speed, roadSegmentId, speedLimitKmh, roadType, nearbyTrafficLights);
    }

    @Override
    public String toString() {
        return "FullyEnrichedTrafficEvent{" +
                "timestamp=" + timestamp +
                ", vehicleId='" + vehicleId + '\'' +
                ", latitude=" + latitude +
                ", longitude=" + longitude +
                ", speed=" + speed +
                ", roadSegmentId='" + roadSegmentId + '\'' +
                ", speedLimitKmh=" + speedLimitKmh +
                ", roadType='" + roadType + '\'' +
                ", nearbyTrafficLights=" + nearbyTrafficLights +
                '}';
    }
}
```

## Using a RichAsyncFunction to query PostGIS ##

Apache Flink uses a so called `RichAsyncFunction` to asynchronously load data from external data sources. We 
start by writing a `AsyncRoadSegmentLookupFunction` to load the road segments off of our PostGIS database, the 
SQL query has been written and optimized in the previous article.

A little complexity is introduced by using `HikariCP` as the data source, because we want efficient Connection 
Pooling, instead of having the costly task of opening and closing database connections for each and every query.

```java
package de.bytefish.flinkjam.lookup;

// ...

/**
 * An Asynchronous Lookup Function for enriching RawTrafficEvents with the road_segment data.
 */
public class AsyncRoadSegmentLookupFunction extends RichAsyncFunction<RawTrafficEvent, RoadEnrichedTrafficEvent> {

    private transient ExecutorService executorService;
    private transient HikariDataSource dataSource; // HikariCP DataSource

    private String dbUrl;
    private String dbUser;
    private String dbPassword;
    private double lookupRadiusMeters;

    private static final String LOOKUP_SQL =
            "SELECT\n" +
                    "    osm_id, \n" +
                    "    osm_type,\n" +
                    "    road_type,\n" +
                    "    speed_limit_kmh,\n" +
                    "    name,\n" +
                    "    geom <-> ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography as distance\n" +
                    "FROM\n" +
                    "    road_segments\n" +
                    "WHERE \n" +
                    "    ST_DWithin(geom, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, ?)\n" +
                    "ORDER BY \n" +
                    "    distance asc \n" +
                    "LIMIT 1;";

    public AsyncRoadSegmentLookupFunction(String dbUrl, String dbUser, String dbPassword, double lookupRadiusMeters) {
        this.dbUrl = dbUrl;
        this.dbUser = dbUser;
        this.dbPassword = dbPassword;
        this.lookupRadiusMeters = lookupRadiusMeters;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);

        // Initialize HikariCP connection pool
        HikariConfig config = new HikariConfig();

        config.setJdbcUrl(dbUrl);
        config.setUsername(dbUser);
        config.setPassword(dbPassword);
        config.addDataSourceProperty("cachePrepStmts", "true");
        config.addDataSourceProperty("prepStmtCacheSize", "250");
        config.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");
        config.setMinimumIdle(5); // Minimum idle connections
        config.setMaximumPoolSize(20); // Maximum total connections (tune this based on DB capacity)
        config.setConnectionTimeout(5000); // 5 seconds connection timeout
        config.setIdleTimeout(300000); // 5 minutes idle timeout
        config.setMaxLifetime(1800000); // 30 minutes max connection lifetime

        // Adjust the thread pool size for the AsyncFunction to match or exceed HikariCP's pool size
        // A higher number of threads allows more concurrent async DB calls.
        executorService = Executors.newFixedThreadPool(config.getMaximumPoolSize() * 2);

        dataSource = new HikariDataSource(config);
    }

    @Override
    public void close() throws Exception {
        super.close();

        if (executorService != null) {
            executorService.shutdown();
            executorService.awaitTermination(5, TimeUnit.SECONDS); // Wait for threads to finish
        }

        if (dataSource != null) {
            dataSource.close(); // Close the connection pool
        }
    }

    @Override
    public void asyncInvoke(RawTrafficEvent input, ResultFuture<RoadEnrichedTrafficEvent> resultFuture) throws Exception {
        executorService.submit(() -> {
            RoadEnrichedTrafficEvent outputEvent = null;
            try (Connection connection = dataSource.getConnection()) {
                try (PreparedStatement statement = connection.prepareStatement(LOOKUP_SQL)) {

                    statement.setDouble(1, input.longitude);
                    statement.setDouble(2, input.latitude);
                    statement.setDouble(3, input.longitude);
                    statement.setDouble(4, input.latitude);
                    statement.setDouble(5, lookupRadiusMeters);

                    try (ResultSet rs = statement.executeQuery()) {
                        if (rs.next()) {
                            String roadSegmentId = rs.getString("osm_id");
                            String roadType = rs.getString("road_type");
                            int speedLimit = rs.getInt("speed_limit_kmh");
                            outputEvent = new RoadEnrichedTrafficEvent(input, roadSegmentId, speedLimit, roadType);
                        } else {
                            // Important: Complete the future even if no segment is found
                            System.out.println("No road segment found for " + input.latitude + ", " + input.longitude + " - " + input.vehicleId);
                            outputEvent = new RoadEnrichedTrafficEvent(input, null, 0, "Unknown");
                        }
                    }
                }
                resultFuture.complete(Collections.singleton(outputEvent));
            } catch (Exception e) { // Catch any exception during lookup (e.g., SQLException)
                System.err.println("Error during async road segment lookup for event " + input.vehicleId + ": " + e.getMessage());
                resultFuture.completeExceptionally(e); // Ensure future is completed exceptionally
            }
        });
    }
}
```

We'll do the same for loading nearby traffic lights in the `AsyncTrafficLightLookupFunction` function. We load 
multiple traffic lights in a given radius, in case our vehicles are congested at an intersection.

```java
package de.bytefish.flinkjam.lookup;

// ...

public class AsyncTrafficLightLookupFunction extends RichAsyncFunction<RoadEnrichedTrafficEvent, FullyEnrichedTrafficEvent> {

    private transient ExecutorService executorService;
    private transient HikariDataSource dataSource; // HikariCP DataSource

    private String dbUrl;
    private String dbUser;
    private String dbPassword;
    private double lookupRadiusMeters;

    private static final String LOOKUP_SQL =
            "SELECT osm_id, name, ST_Y(geom) AS latitude, ST_X(geom) AS longitude, is_pedestrian_crossing_light, " +
                    "ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography) AS distance_meters " +
                    "FROM traffic_lights " +
                    "WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography, ?) " + // ? = radius in meters
                    "ORDER BY distance_meters " +
                    "LIMIT 3;"; // Limit to top N closest lights

    public AsyncTrafficLightLookupFunction(String dbUrl, String dbUser, String dbPassword, double lookupRadiusMeters) {
        this.dbUrl = dbUrl;
        this.dbUser = dbUser;
        this.dbPassword = dbPassword;
        this.lookupRadiusMeters = lookupRadiusMeters;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        // Initialize HikariCP connection pool
        HikariConfig config = new HikariConfig();

        config.setJdbcUrl(dbUrl);
        config.setUsername(dbUser);
        config.setPassword(dbPassword);
        config.addDataSourceProperty("cachePrepStmts", "true");
        config.addDataSourceProperty("prepStmtCacheSize", "250");
        config.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");
        config.setMinimumIdle(5); // Minimum idle connections
        config.setMaximumPoolSize(20); // Maximum total connections (tune this based on DB capacity)
        config.setConnectionTimeout(5000); // 5 seconds connection timeout
        config.setIdleTimeout(300000); // 5 minutes idle timeout
        config.setMaxLifetime(1800000); // 30 minutes max connection lifetime

        // Adjust the thread pool size for the AsyncFunction to match or exceed HikariCP's pool size
        // A higher number of threads allows more concurrent async DB calls.
        executorService = Executors.newFixedThreadPool(config.getMaximumPoolSize() * 2);

        dataSource = new HikariDataSource(config);
    }

    @Override
    public void close() throws Exception {
        super.close();

        if (executorService != null) {
            executorService.shutdown();
            executorService.awaitTermination(5, TimeUnit.SECONDS); // Wait for threads to finish
        }

        if (dataSource != null) {
            dataSource.close(); // Close the connection pool
        }
    }

    @Override
    public void asyncInvoke(RoadEnrichedTrafficEvent input, ResultFuture<FullyEnrichedTrafficEvent> resultFuture) throws Exception {
        executorService.submit(() -> {
            List<TrafficLightInfo> nearbyTrafficLights = new ArrayList<>();
            // Open connection within the submitted task to ensure thread safety
            try (Connection connection = dataSource.getConnection()) {
                try (PreparedStatement statement = connection.prepareStatement(LOOKUP_SQL)) {
                    statement.setDouble(1, input.longitude); // For ST_MakePoint
                    statement.setDouble(2, input.latitude);  // For ST_MakePoint
                    statement.setDouble(3, input.longitude); // For ST_DWithin
                    statement.setDouble(4, input.latitude);  // For ST_DWithin
                    statement.setDouble(5, lookupRadiusMeters); // Radius in meters

                    try (ResultSet rs = statement.executeQuery()) {
                        while (rs.next()) {
                            long id = rs.getLong("osm_id");
                            String name = rs.getString("name");
                            double lat = rs.getDouble("latitude");
                            double lon = rs.getDouble("longitude");
                            boolean isPedestrian = rs.getBoolean("is_pedestrian_crossing_light");
                            double distance = rs.getDouble("distance_meters");

                            nearbyTrafficLights.add(new TrafficLightInfo(id, name, lat, lon, isPedestrian, distance));
                        }
                    }
                }
                FullyEnrichedTrafficEvent outputEvent = new FullyEnrichedTrafficEvent(input, nearbyTrafficLights);
                resultFuture.complete(Collections.singleton(outputEvent));
            } catch (Exception e) {
                System.err.println("SQL Error during async traffic light lookup for event " + input.vehicleId + ": " + e.getMessage());
                resultFuture.completeExceptionally(e);
            }
        });
    }
}
```

## Simulating Traffic Congestion Patterns ##

By using Google Maps I have extracted the GPS position and simulated various congestion patters. The events 
are published in a one second interval, so you can see them coming in and see patterns building up.

```java
package de.bytefish.flinkjam.sources;

// ...

/**
 * A custom Flink SourceFunction to continuously generate simulated RawTrafficEvents.
 * This will prevent the Flink job from terminating due to source exhaustion.
 */
public class RawTrafficEventSource implements SourceFunction<RawTrafficEvent> {
    private volatile boolean isRunning = true;

    public List<RawTrafficEvent> simulatedEvents;

    public long currentBaseTimestamp;

    public RawTrafficEventSource() {
        // Initialize the base simulated events once
        simulatedEvents = new ArrayList<>();

        // Populate initial simulated events
        currentBaseTimestamp = System.currentTimeMillis();

        // Simulate normal traffic on A1 initially
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp, "Car001", 52.194443, 7.797556, 90));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp, "Car002", 52.194512, 7.797632, 95));

        // Simulate Light Slowdown on A1 (Exit FMO Airport) (e.g., speed below 70%, 3+ events, 2+ unique vehicles)
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 5000, "Car001", 52.115703, 7.702582, 65));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 10000, "Car002", 52.115849, 7.702784, 60));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 15000, "Car003", 52.115611, 7.702527, 68));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 20000, "Car001", 52.116178, 7.703204, 62));

        // Simulate Sustained Slowdown on A1 (e.g., speed below 50%, 5+ events, 3+ unique vehicles)
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 25000, "Car008", 52.041431, 7.607906, 45));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 30000, "Car009", 52.041487, 7.607935, 40));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 35000, "Car010", 52.041200, 7.607768, 42));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 40000, "Car008", 52.041744, 7.608094, 35));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 45000, "Car009", 52.041499, 7.608008, 38));

        // Simulate Traffic Jam (e.g., speed below 10 km/h, 7+ events, 5+ unique vehicles)
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 50000, "TruckX", 52.006419, 7.575624, 8));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 53000, "CarY", 52.006460, 7.575661, 5));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 56000, "BusZ", 52.006511, 7.575714, 3));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 59000, "MotoA", 52.006555, 7.575762, 1));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 62000, "VanB", 52.006612, 7.575814, 7));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 65000, "TruckX", 52.006687, 7.575893, 2));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 68000, "CarY", 52.006760, 7.575959, 4));

        // Simulate a scenario that's just a long red light (high density, low speed, but expected)
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 78000, "CarD", 51.966097, 7.623803, 2));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 81000, "CarE", 51.966113, 7.623785, 0));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 84000, "CarF", 51.966138, 7.623783, 1));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 87000, "CarG", 51.966162, 7.623780, 0));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 90000, "CarH", 51.966184, 7.623771, 3));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 93000, "CarI", 51.966092, 7.623775, 0));
        simulatedEvents.add(new RawTrafficEvent(currentBaseTimestamp + 96000, "CarJ", 51.966217, 7.623759, 2));
    }

    @Override
    public void run(SourceContext<RawTrafficEvent> ctx) throws Exception {
        int eventIndex = 0;
        // Define a delay between each event emission to simulate real-time data
        long delayBetweenEventsMillis = 1000; // 1 second between events

        while (isRunning) {
            if (eventIndex >= simulatedEvents.size()) {
                // Loop back to the beginning of the simulated data
                eventIndex = 0;
                // Optionally adjust timestamps for the next loop to keep them increasing
                currentBaseTimestamp = System.currentTimeMillis();
            }

            RawTrafficEvent originalEvent = simulatedEvents.get(eventIndex);

            // Create a new event to update its timestamp
            RawTrafficEvent eventToSend = new RawTrafficEvent(
                    currentBaseTimestamp + (originalEvent.timestamp - simulatedEvents.get(0).timestamp),
                    originalEvent.vehicleId,
                    originalEvent.latitude,
                    originalEvent.longitude,
                    originalEvent.speed
            );

            ctx.collect(eventToSend);

            eventIndex++;

            try {
                Thread.sleep(delayBetweenEventsMillis);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                isRunning = false; // Stop if interrupted
                System.err.println("RawTrafficEventSource interrupted during sleep.");
            }
        }
    }

    @Override
    public void cancel() {
        isRunning = false;
    }
}
```

## Congestion Warnings ##

We are going to use the Apache Flink CEP to generate `CongestionWarnings`. This `CongestionWarning` is going to be the 
same for every Traffic Event, such as `Traffic Jam`, `Sustained Slowdown`, ... It also includes the related traffic 
lights in case we have encountered a Traffic Jam, that's related to an intersection.

```java
package de.bytefish.flinkjam.models;

import java.util.List;

/**
 * Represents a detected congestion warning.
 */
public class CongestionWarning implements java.io.Serializable  {
    public long timestamp;
    public String warningType;
    public String roadSegmentId;
    public double currentAverageSpeed;
    public int speedLimit;
    public String details;
    public List<TrafficLightInfo> relatedTrafficLights; // Can include lights related to the congestion
    public int affectedUniqueVehiclesCount;

    public CongestionWarning() {
    }

    public CongestionWarning(long timestamp, String roadSegmentId, String warningType, double currentAverageSpeed, int speedLimit, String details, List<TrafficLightInfo> relatedTrafficLights, int affectedUniqueVehiclesCount) {
        this.timestamp = timestamp;
        this.roadSegmentId = roadSegmentId;
        this.warningType = warningType;
        this.currentAverageSpeed = currentAverageSpeed;
        this.speedLimit = speedLimit;
        this.details = details;
        this.relatedTrafficLights = relatedTrafficLights;
        this.affectedUniqueVehiclesCount = affectedUniqueVehiclesCount;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public String getWarningType() {
        return warningType;
    }

    public String getRoadSegmentId() {
        return roadSegmentId;
    }

    public double getCurrentAverageSpeed() {
        return currentAverageSpeed;
    }

    public int getSpeedLimit() {
        return speedLimit;
    }

    public String getDetails() {
        return details;
    }

    public List<TrafficLightInfo> getRelatedTrafficLights() {
        return relatedTrafficLights;
    }

    public int getAffectedUniqueVehiclesCount() {
        return affectedUniqueVehiclesCount;
    }

    @Override
    public String toString() {
        return "!!! CONGESTION ALERT !!! " +
                "Timestamp=" + timestamp +
                ", RoadSegmentId='" + roadSegmentId + '\'' +
                ", Type='" + warningType + '\'' +
                ", AvgSpeed=" + String.format("%.2f", currentAverageSpeed) + " km/h" +
                ", SpeedLimit=" + speedLimit + " km/h" +
                ", Details='" + details + '\'' +
                ", UniqueVehicles=" + affectedUniqueVehiclesCount +
                ", RelatedLights=" + relatedTrafficLights;
    }
}
```

## Building the Apache Flink Pipeline ##

I usually don't want my articles to just be "dumping code to the article". So I have long thought about how to 
show iteratively building a pipeline. But it's too long, so the code has been commented a lot instead.

It basically starts with a `TrafficCongestionConfig`, which is going to hold a configuration for congestion 
patterns. All patterns are somewhat similar, so it's not useful to break them up into a dozens of 
configurations.

We then start streaming the data with our previously defined `RawTrafficEventSource` and enrich the 
`RawTrafficEvent` using the `AsyncRoadSegmentLookupFunction` and `AsyncTrafficLightLookupFunction`.

Once we have built the `FullyEnrichedTrafficEvent`, we apply the various congestion patterns on them, 
that are using the `TrafficCongestionConfig` to define relative and absolute thresholds. In Apache Flink 
a `PatternProcessFunction` is then used to convert the matched pattern into a `CongestionWarning`.

This generates the `CongestionWarnings` just fine. It's generating them so fine, that way too many 
warnings are generated. And it's logical: Think how the patterns are applied: It matches the 
Patterns for every incoming event, thus each of them matches.

And what about a Traffic Jam, that slowly fades out? We don't want to generate the events in a very 
rapid succession, because with a "Stop-And-Go" you would quickly alternate like... "Traffic Jam", 
"Sustained Slowdown", "Traffic Jam", "Sustained Slowdown". People watching such a map probably go 
crazy. 

So we also need to debounce the patterns introducing both an "Warning Event Hierarchy" and a debounce 
period, that avoids generating millions of events, while traffic is fading out. All this happens in 
the `WarningDebouncerFunction`.

```java
package de.bytefish.flinkjam;

// ...

public class TrafficCongestionWarningSystem {

    private static final String DB_URL = "jdbc:postgresql://localhost:5432/flinkjam";
    private static final String DB_USER = "postgis";
    private static final String DB_PASSWORD = "postgis";

    /**
     * A Configuration used in Traffic Congestions Patterns.
     */
    public static class TrafficCongestionConfig implements Serializable { // Implement Serializable
        public int minEvents;
        public  double speedThresholdFactor; // Speed < factor of speed limit
        public  long windowMillis; // Changed to long for serializability
        public  int minUniqueVehicles;
        public int trafficLightNearbyRadiusInMeters;
        public double absoluteSpeedThresholdKmh; // Absolute speed < this value

        public TrafficCongestionConfig(int minEvents, double speedThresholdFactor, double absoluteSpeedThresholdKmh, Duration window, int minUniqueVehicles, int trafficLightNearbyRadiusInMeters) {
            this.minEvents = minEvents;
            this.speedThresholdFactor = speedThresholdFactor;
            this.absoluteSpeedThresholdKmh = absoluteSpeedThresholdKmh;
            this.windowMillis = window.toMillis(); // Store as milliseconds
            this.minUniqueVehicles = minUniqueVehicles;
            this.trafficLightNearbyRadiusInMeters = trafficLightNearbyRadiusInMeters;

        }

        public int getMinEvents() {
            return minEvents;
        }

        public double getSpeedThresholdFactor() {
            return speedThresholdFactor;
        }

        public long getWindowMillis() {
            return windowMillis;
        }

        public int getMinUniqueVehicles() {
            return minUniqueVehicles;
        }

        public int getTrafficLightNearbyRadiusInMeters() {
            return trafficLightNearbyRadiusInMeters;
        }

        public double getAbsoluteSpeedThresholdKmh() {
            return absoluteSpeedThresholdKmh;
        }
    }

    public static void main(String[] args) throws Exception {
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        env.setParallelism(1);

        // We define a WatermarkStrategy for all event streams. forBoundedOutOfOrderness is a common choice for
        // real-time applications, allowing for some events to arrive out of order. We allow 5 seconds
        // out-of-orderness.
        WatermarkStrategy<RawTrafficEvent> rawEventWmStrategy = WatermarkStrategy
                .<RawTrafficEvent>forBoundedOutOfOrderness(Duration.ofSeconds(5))
                .withTimestampAssigner((event, recordTimestamp) -> event.timestamp);

        // The simulation should include the following types: Normal Traffic, Light Slowdown, Sustained Slowdown,
        // Traffic Jam, Red Light Phase.  We don't have access to a real data source, so we generate our own
        // traffic events and feed them to Apache Flink using a SourceFunction<>.
        DataStream<RawTrafficEvent> rawTrafficEvents = env.addSource(new RawTrafficEventSource())
                .assignTimestampsAndWatermarks(rawEventWmStrategy); // Apply watermark strategy

        // Now we need to enrich the raw events with the road segment data, so we get the speed limit and road_segment,
        // the possible congestion is on. This is done using the RichAsyncFunction, with 10m as the Lookup Function
        // for Road Segments.
        DataStream<RoadEnrichedTrafficEvent> roadEnrichedEvents = AsyncDataStream.unorderedWait(
                rawTrafficEvents,
                new AsyncRoadSegmentLookupFunction(DB_URL, DB_USER, DB_PASSWORD, 10),
                5000, TimeUnit.MILLISECONDS, 100
        ).filter(event -> event.roadSegmentId != null);

        roadEnrichedEvents.print("Road Enriched Event");

        // Next is enriching the events with the TrafficLightInformation. This needs to be done, because we don't
        // want to generate dozens of false positives, if cars are in a red light phase. If we don't take traffic
        // lights into consideration, each red light phase would generate an event.
        DataStream<FullyEnrichedTrafficEvent> fullyEnrichedEvents = AsyncDataStream.unorderedWait(
                roadEnrichedEvents,
                new AsyncTrafficLightLookupFunction(DB_URL, DB_USER, DB_PASSWORD, 20),
                500, TimeUnit.MILLISECONDS, 100 // Increased timeout to 15 seconds
        );

        fullyEnrichedEvents.print("Fully Enriched Event");

        // Watermark Strategy for FullyEnrichedTrafficEvents
        WatermarkStrategy<FullyEnrichedTrafficEvent> fullyEnrichedEventWmStrategy = WatermarkStrategy
                .<FullyEnrichedTrafficEvent>forBoundedOutOfOrderness(Duration.ofSeconds(5)) // Allow 5 seconds out-of-orderness
                .withTimestampAssigner((event, recordTimestamp) -> event.getTimestamp());

        DataStream<FullyEnrichedTrafficEvent> trafficEventsForCEP = fullyEnrichedEvents
                .assignTimestampsAndWatermarks(fullyEnrichedEventWmStrategy) // Apply watermark strategy after enrichment
                .filter(event -> event.roadSegmentId != null); // Ensure only valid road segments go to CEP

        // Key the stream by road segment ID to detect patterns per road segment
        DataStream<FullyEnrichedTrafficEvent> keyedTrafficEvents = trafficEventsForCEP
                .keyBy(FullyEnrichedTrafficEvent::getRoadSegmentId);

        // Pattern 1: Light Slowdown
        TrafficCongestionConfig lightSlowdownConfig = new TrafficCongestionConfig(3, 0.7, 0, Duration.ofSeconds(60), 2, 50);

        Pattern<FullyEnrichedTrafficEvent, ?> lightSlowdownPattern = Pattern.<FullyEnrichedTrafficEvent>begin("lightSlowEvent")
                .where(new IterativeCondition<FullyEnrichedTrafficEvent>() {
                    @Override
                    public boolean filter(FullyEnrichedTrafficEvent event, Context<FullyEnrichedTrafficEvent> ctx) throws Exception {
                        return event.getSpeed() < (event.getSpeedLimitKmh() * lightSlowdownConfig.speedThresholdFactor);
                    }
                })
                .timesOrMore(lightSlowdownConfig.minEvents)
                .greedy()
                .within(Duration.ofMillis(lightSlowdownConfig.windowMillis));

        DataStream<CongestionWarning> lightSlowdownWarnings = CEP.pattern(keyedTrafficEvents, lightSlowdownPattern).process(
                new CongestionPatternProcessFunction("Light Slowdown", lightSlowdownConfig.speedThresholdFactor, 0.0, lightSlowdownConfig.minUniqueVehicles, lightSlowdownConfig.getTrafficLightNearbyRadiusInMeters()));

        // Pattern 2: Sustained Slowdown (more severe than Light Slowdown)
        TrafficCongestionConfig sustainedSlowdownConfig = new TrafficCongestionConfig(5, 0.5, 0, Duration.ofSeconds(60), 3, 30);

        Pattern<FullyEnrichedTrafficEvent, ?> sustainedSlowdownPattern = Pattern.<FullyEnrichedTrafficEvent>begin("sustainedSlowEvent")
                .where(new IterativeCondition<>() {
                    @Override
                    public boolean filter(FullyEnrichedTrafficEvent event, Context<FullyEnrichedTrafficEvent> ctx) throws Exception {
                        return event.getSpeed() < (event.getSpeedLimitKmh() * sustainedSlowdownConfig.speedThresholdFactor);
                    }
                })
                .timesOrMore(sustainedSlowdownConfig.minEvents)
                .greedy()
                .within(Duration.ofMillis(sustainedSlowdownConfig.windowMillis));

        DataStream<CongestionWarning> sustainedSlowdownWarnings = CEP
                .pattern(keyedTrafficEvents, sustainedSlowdownPattern)
                .process(new CongestionPatternProcessFunction("Sustained Slowdown", sustainedSlowdownConfig.speedThresholdFactor, 0.0, sustainedSlowdownConfig.minUniqueVehicles, sustainedSlowdownConfig.getTrafficLightNearbyRadiusInMeters()));

        // Pattern 3: Traffic Jam (most severe, near-stop)
        TrafficCongestionConfig trafficJamConfig = new TrafficCongestionConfig(7, 0, 10, Duration.ofSeconds(60), 5, 30);

        Pattern<FullyEnrichedTrafficEvent, ?> trafficJamPattern = Pattern.<FullyEnrichedTrafficEvent>begin("trafficJamEvent")
                .where(new IterativeCondition<FullyEnrichedTrafficEvent>() {
                    @Override
                    public boolean filter(FullyEnrichedTrafficEvent event, Context<FullyEnrichedTrafficEvent> ctx) throws Exception {
                        return event.getSpeed() < trafficJamConfig.absoluteSpeedThresholdKmh; // Absolute low speed
                    }
                })
                .timesOrMore(trafficJamConfig.minEvents)
                .greedy()
                .within(Duration.ofMillis(trafficJamConfig.windowMillis));

        DataStream<CongestionWarning> trafficJamWarnings = CEP.pattern(keyedTrafficEvents, trafficJamPattern).process(
                new CongestionPatternProcessFunction("Traffic Jam", 0.0, trafficJamConfig.absoluteSpeedThresholdKmh, trafficJamConfig.minUniqueVehicles, trafficJamConfig.trafficLightNearbyRadiusInMeters));

        DataStream<CongestionWarning> allWarnings = lightSlowdownWarnings
                .union(sustainedSlowdownWarnings)
                .union(trafficJamWarnings);

        // Apply debouncing to the combined warnings stream with severity awareness
        long debouncePeriodMs = Duration.ofSeconds(60).toMillis();

        DataStream<CongestionWarning> debouncedWarnings = allWarnings
                .keyBy(CongestionWarning::getRoadSegmentId)
                .process(new WarningDebouncerFunction(debouncePeriodMs));

        debouncedWarnings.print("DEBOUNCED CONGESTION WARNING");

        env.execute("flink-jam: Traffic Congestion Warning System");
    }
}
```

## Debouncing Warnings using a KeyedProcessFunction ##

In order to debounce the warning events in the stream, we need to store the last warning generated 
by the system. The last event is going to be stored for a keyed stream, that's why we don't need to 
introduce additional fields.

```java
package de.bytefish.flinkjam.models;

import java.io.Serializable;

/**
 * Stores metadata about the last warning issued for a road segment.
 */
public class LastWarningMetadata implements Serializable {
    public long timestamp;
    public String warningType;
    public int severity; // Numerical severity

    public LastWarningMetadata() {}

    public LastWarningMetadata(long timestamp, String warningType, int severity) {
        this.timestamp = timestamp;
        this.warningType = warningType;
        this.severity = severity;
    }

    @Override
    public String toString() {
        return "LastWarningMetadata{" +
                "timestamp=" + timestamp +
                ", warningType='" + warningType + '\'' +
                ", severity=" + severity +
                '}';
    }
}
```

For debouncing events we are using a `KeyedProcessFunction`, that debounces the events. It emits 
a warning, if the current warnings severity is higher than the previous once or if we exceeded the 
debounce period.

```java
package de.bytefish.flinkjam.cep;

// ...

/**
 * We need to debounce the events, so we don't generate too many warnings. Imagine you
 * have a traffic jam and the cars slowly fade out. You probably don't want to send
 * events, when traffic clears up.
 */
public class WarningDebouncerFunction extends KeyedProcessFunction<String, CongestionWarning, CongestionWarning> {

    private final long debouncePeriodMillis;
    private transient ValueState<LastWarningMetadata> lastWarningMetadataState;
    private transient Map<String, Integer> severityMap; // Maps warning type strings to integers

    public WarningDebouncerFunction(long debouncePeriodMillis) {
        this.debouncePeriodMillis = debouncePeriodMillis;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);

        lastWarningMetadataState = getRuntimeContext().getState(
                new ValueStateDescriptor<>("lastWarningMetadata", TypeInformation.of(LastWarningMetadata.class))
        );

        // Initialize severity mapping
        severityMap = new HashMap<>();
        severityMap.put("Light Slowdown", 1);
        severityMap.put("Sustained Slowdown", 2);
        severityMap.put("Traffic Jam (Queue at Light)", 3);
        severityMap.put("Traffic Jam", 4); // Highest severity
    }

    // Helper to get severity from a warning type string
    private int getSeverity(String warningType) {
        return severityMap.getOrDefault(warningType, 0); // Default to 0 for unknown types (lowest)
    }

    @Override
    public void processElement(
            CongestionWarning warning,
            Context ctx,
            Collector<CongestionWarning> out) throws Exception {

        LastWarningMetadata lastMetadata = lastWarningMetadataState.value();
        long currentTime = warning.timestamp;
        int incomingSeverity = getSeverity(warning.warningType);

        if (lastMetadata == null) {
            // No previous warning for this segment, emit immediately
            out.collect(warning);
            lastWarningMetadataState.update(new LastWarningMetadata(currentTime, warning.warningType, incomingSeverity));
        } else {
            int lastSeverity = lastMetadata.severity;
            long timeSinceLastWarning = currentTime - lastMetadata.timestamp;

            if (incomingSeverity > lastSeverity) {
                // Always emit if the new warning is more severe
                System.out.println(String.format("Emitting %s warning for segment %s (Severity escalated from %s to %s).",
                        warning.warningType, warning.roadSegmentId, lastMetadata.warningType, warning.warningType));
                out.collect(warning);
                lastWarningMetadataState.update(new LastWarningMetadata(currentTime, warning.warningType, incomingSeverity));
            } else if (timeSinceLastWarning >= debouncePeriodMillis) {
                // Emit if the debounce period has passed, even if severity is same or lower
                System.out.println(String.format("Emitting %s warning for segment %s (Debounce period passed).",
                        warning.warningType, warning.roadSegmentId));
                out.collect(warning);
                lastWarningMetadataState.update(new LastWarningMetadata(currentTime, warning.warningType, incomingSeverity));
            } else {
                // Suppress if less severe or same severity and within debounce period
                System.out.println(String.format("Suppressing %s warning for road segment %s (last warning %d ms ago, severity %d <= %d).",
                        warning.warningType, warning.roadSegmentId, timeSinceLastWarning, incomingSeverity, lastSeverity));
            }
        }
    }
}
```

## Generating Warnings for the CEP Pattern Matches with a PatternProcessFunction ##

Now the final piece to the puzzle is the `PatternProcessFunction`, that finally processes the our matched 
patterns. It takes the List of `FullyEnrichedTrafficEvent` and applies the logic for generating the warnings 
based on our matches.

```java
package de.bytefish.flinkjam.cep;

// ...

import java.util.*;

public class CongestionPatternProcessFunction extends org.apache.flink.cep.functions.PatternProcessFunction<FullyEnrichedTrafficEvent, CongestionWarning> {

    private final String warningBaseType;
    private final double speedThresholdFactor; // Used for "Slowdown" types relative to speed limit
    private final double absoluteSpeedThresholdKmh; // Used for "Traffic Jam" types
    private final int minUniqueVehicles;
    private final double trafficLightRadius; // Radius used to consider lights "nearby"

    // Constructor for Light and Sustained Slowdown (using speedThresholdFactor)
    public CongestionPatternProcessFunction(String warningBaseType, double speedThresholdFactor, double absoluteSpeedThresholdKmh, int minUniqueVehicles, double trafficLightRadius) {
        this.warningBaseType = warningBaseType;
        this.speedThresholdFactor = speedThresholdFactor;
        this.absoluteSpeedThresholdKmh = absoluteSpeedThresholdKmh; // Will be 0.0 for slowdowns
        this.minUniqueVehicles = minUniqueVehicles;
        this.trafficLightRadius = trafficLightRadius;
    }

    @Override
    public void processMatch(Map<String, List<FullyEnrichedTrafficEvent>> match, Context ctx, Collector<CongestionWarning> out) throws Exception {

        // The matched events will be under the first key defined in the pattern (e.g., "firstSlowEvent")
        List<FullyEnrichedTrafficEvent> allMatchedEvents = null;

        // Iterate through the map to find the list of matched events.
        // The key used in `begin("patternName")` is what needs to be retrieved.
        // For simple patterns with a single `begin` event, iterating `values()` is sufficient.
        if (!match.isEmpty()) {
            allMatchedEvents = match.values().iterator().next(); // Get the list from the first (and likely only) key
        }

        if (allMatchedEvents == null || allMatchedEvents.isEmpty()) {
            return; // Should not happen if pattern is correctly defined, but good check
        }

        FullyEnrichedTrafficEvent firstEvent = allMatchedEvents.get(0);

        double totalSpeed = 0;

        Set<String> uniqueVehicles = new HashSet<>();

        Set<TrafficLightInfo> uniqueRelatedLights = new HashSet<>(); // Use Set for uniqueness

        for (FullyEnrichedTrafficEvent event : allMatchedEvents) {
            totalSpeed += event.getSpeed();
            uniqueVehicles.add(event.getVehicleId());
            if (event.getNearbyTrafficLights() != null) {
                uniqueRelatedLights.addAll(event.getNearbyTrafficLights());
            }
        }

        // Apply unique vehicle count filter
        if (uniqueVehicles.size() < minUniqueVehicles) {
            System.out.println(String.format("Skipping %s warning: Not enough unique vehicles (%d < %d) on road segment %s.",
                    warningBaseType, uniqueVehicles.size(), minUniqueVehicles, firstEvent.roadSegmentId));
            return;
        }

        double averageSpeed = totalSpeed / allMatchedEvents.size();

        // Check speed of the last event to prevent stale warnings
        FullyEnrichedTrafficEvent lastEvent = allMatchedEvents.get(allMatchedEvents.size() - 1);
        boolean lastEventStillSlowEnough = false;

        if (warningBaseType.equals("Traffic Jam")) {
            if (lastEvent.getSpeed() < absoluteSpeedThresholdKmh * 1.5) { // Allow some slight increase but still very slow
                lastEventStillSlowEnough = true;
            }
        } else {
            if (lastEvent.getSpeed() < (lastEvent.getSpeedLimitKmh() * (speedThresholdFactor + 0.15))) { // Allow slightly higher speed than threshold
                lastEventStillSlowEnough = true;
            }
        }

        if (!lastEventStillSlowEnough) {
            System.out.println(String.format("Skipping %s warning: Last event speed (%.2f km/h) indicates clearing traffic or transient slowdown on road segment %s.",
                    warningBaseType, lastEvent.getSpeed(), firstEvent.roadSegmentId));
            return;
        }

        String actualWarningType = warningBaseType;
        String details;

        // Use speedThresholdFactor (for relative) or absoluteSpeedThresholdKmh (for absolute)
        if (warningBaseType.equals("Traffic Jam")) {
            details = String.format("Severe congestion (Avg Speed: %.2f km/h, below %.1f km/h) detected on road segment %s (Type: %s). Involved vehicles: %d.",
                    averageSpeed, absoluteSpeedThresholdKmh, firstEvent.roadSegmentId, firstEvent.roadType, uniqueVehicles.size());
        } else {
            double thresholdSpeed = firstEvent.getSpeedLimitKmh() * speedThresholdFactor;
            details = String.format("Average speed (%.2f km/h) is below %.1f%% of speed limit (%.1f km/h vs %d km/h) on road segment %s (Type: %s). Involved vehicles: %d.",
                    averageSpeed, speedThresholdFactor * 100, thresholdSpeed, firstEvent.speedLimitKmh, firstEvent.roadSegmentId, firstEvent.roadType, uniqueVehicles.size());
        }

        // Traffic Light Consideration Logic
        if (!uniqueRelatedLights.isEmpty()) {
            boolean isNearTrafficLight = false;
            for (TrafficLightInfo light : uniqueRelatedLights) {
                if (light.distanceMeters <= trafficLightRadius) {
                    isNearTrafficLight = true;
                    break;
                }
            }

            if (isNearTrafficLight) {
                if (warningBaseType.equals("Traffic Jam")) {

                    // If it's a Traffic Jam and near a light, refine the type
                    actualWarningType = "Traffic Jam (Queue at Light)";
                    details = String.format("Severe congestion (Avg Speed: %.2f km/h) detected near traffic light(s) on segment %s. Possible queue at intersection. Involved vehicles: %d.",
                            averageSpeed, firstEvent.roadSegmentId, uniqueVehicles.size());
                } else if (warningBaseType.equals("Sustained Slowdown") || warningBaseType.equals("Light Slowdown")) {
                    // For slowdowns near a light, add a note
                    details += " (Near traffic light(s))";
                }
            } else {
                // If it's a Traffic Jam AND NOT near a light, it's a more serious general jam
                if (warningBaseType.equals("Traffic Jam")) {
                    details = String.format("Severe congestion (Avg Speed: %.2f km/h) detected on road segment %s. No immediate traffic light nearby. Potential incident/bottleneck. Involved vehicles: %d.",
                            averageSpeed, firstEvent.roadSegmentId, uniqueVehicles.size());
                }
            }
        }

        CongestionWarning warning = new CongestionWarning(
                ctx.timestamp(),
                firstEvent.roadSegmentId,
                actualWarningType,
                averageSpeed,
                firstEvent.speedLimitKmh,
                details,
                new ArrayList<>(uniqueRelatedLights), // Convert Set back to List for output
                uniqueVehicles.size()
        );
        out.collect(warning);
    }
}
```

## Running the Apache Flink Pipeline ##

Since Java 11 we need to explictly add the Java classes we need to use Reflection on. 

In the IntelliJ Run Configuration I am adding the CLI Parameters to the JVM options. I don't know 
if I need them all, but... yolo:

```
--add-opens java.base/java.lang=ALL-UNNAMED 
--add-opens java.base/java.io=ALL-UNNAMED 
--add-opens java.base/java.util=ALL-UNNAMED 
--add-opens java.base/java.base=ALL-UNNAMED
```

And when running the application, we can following the entire stream processing and see a warning generated for 
the light slowdown on the Autobahn A1, that we have defined in our simulated data:

```
Raw Traffic Event> RawTrafficEvent{timestamp=1751097526846, vehicleId='Car002', latitude=52.194512, longitude=7.797632, speed=95.0}
Road Enriched Event> RoadEnrichedTrafficEvent{timestamp=1751097526846, vehicleId='Car002', latitude=52.194512, longitude=7.797632, speed=95.0, roadSegmentId='326809667', speedLimitKmh=130, roadType='Autobahn'}
Fully Enriched Event> FullyEnrichedTrafficEvent{timestamp=1751097526846, vehicleId='Car002', latitude=52.194512, longitude=7.797632, speed=95.0, roadSegmentId='326809667', speedLimitKmh=130, roadType='Autobahn', nearbyTrafficLights=[]}

Raw Traffic Event> RawTrafficEvent{timestamp=1751097531846, vehicleId='Car001', latitude=52.115703, longitude=7.702582, speed=65.0}
Road Enriched Event> RoadEnrichedTrafficEvent{timestamp=1751097531846, vehicleId='Car001', latitude=52.115703, longitude=7.702582, speed=65.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn'}
Fully Enriched Event> FullyEnrichedTrafficEvent{timestamp=1751097531846, vehicleId='Car001', latitude=52.115703, longitude=7.702582, speed=65.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn', nearbyTrafficLights=[]}

Raw Traffic Event> RawTrafficEvent{timestamp=1751097536846, vehicleId='Car002', latitude=52.115849, longitude=7.702784, speed=60.0}
Road Enriched Event> RoadEnrichedTrafficEvent{timestamp=1751097536846, vehicleId='Car002', latitude=52.115849, longitude=7.702784, speed=60.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn'}
Fully Enriched Event> FullyEnrichedTrafficEvent{timestamp=1751097536846, vehicleId='Car002', latitude=52.115849, longitude=7.702784, speed=60.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn', nearbyTrafficLights=[]}

Raw Traffic Event> RawTrafficEvent{timestamp=1751097541846, vehicleId='Car003', latitude=52.115611, longitude=7.702527, speed=68.0}
Road Enriched Event> RoadEnrichedTrafficEvent{timestamp=1751097541846, vehicleId='Car003', latitude=52.115611, longitude=7.702527, speed=68.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn'}
Fully Enriched Event> FullyEnrichedTrafficEvent{timestamp=1751097541846, vehicleId='Car003', latitude=52.115611, longitude=7.702527, speed=68.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn', nearbyTrafficLights=[]}

Raw Traffic Event> RawTrafficEvent{timestamp=1751097546846, vehicleId='Car001', latitude=52.116178, longitude=7.703204, speed=62.0}
Road Enriched Event> RoadEnrichedTrafficEvent{timestamp=1751097546846, vehicleId='Car001', latitude=52.116178, longitude=7.703204, speed=62.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn'}
Fully Enriched Event> FullyEnrichedTrafficEvent{timestamp=1751097546846, vehicleId='Car001', latitude=52.116178, longitude=7.703204, speed=62.0, roadSegmentId='25995891', speedLimitKmh=130, roadType='Autobahn', nearbyTrafficLights=[]}

Raw Traffic Event> RawTrafficEvent{timestamp=1751097551846, vehicleId='Car008', latitude=52.041431, longitude=7.607906, speed=45.0}
Road Enriched Event> RoadEnrichedTrafficEvent{timestamp=1751097551846, vehicleId='Car008', latitude=52.041431, longitude=7.607906, speed=45.0, roadSegmentId='26305583', speedLimitKmh=130, roadType='Autobahn'}
Fully Enriched Event> FullyEnrichedTrafficEvent{timestamp=1751097551846, vehicleId='Car008', latitude=52.041431, longitude=7.607906, speed=45.0, roadSegmentId='26305583', speedLimitKmh=130, roadType='Autobahn', nearbyTrafficLights=[]}

DEBOUNCED CONGESTION WARNING> !!! CONGESTION ALERT !!! Timestamp=1751097541846, RoadSegmentId='25995891', Type='Light Slowdown', AvgSpeed=64,33 km/h, SpeedLimit=130 km/h, Details='Average speed (64,33 km/h) is below 70,0% of speed limit (91,0 km/h vs 130 km/h) on road segment 25995891 (Type: Autobahn). Involved vehicles: 3.', UniqueVehicles=3, RelatedLights=[]
```

## Conclusion ##

And that's it! We now have a nice playground for exploring other ideas.

Let's see what we could build upon it!