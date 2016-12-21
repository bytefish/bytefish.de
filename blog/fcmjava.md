title: Firebase Cloud Messaging (FCM) with Java
date: 2016-11-19 09:01
tags: java, fcmjava, fcm
category: java
slug: fcmjava
author: Philipp Wagner
summary: This article shows how to work with Firebase Cloud Messaging in Java.

Some time ago I needed a simple way to send Push Messages with Firebase Cloud Messaging (FCM), so I 
wrote [FcmJava]:

* [https://github.com/bytefish/FcmJava](https://github.com/bytefish/FcmJava)

[FcmJava] implements the entire [Firebase Cloud Messaging HTTP Protocol] and supports:

* Downstream HTTP Messages
* Notification Payloads
* Topic Messages
* Device Group Messages

Firebase Cloud Messaging (FCM) is basically the successor to Google Cloud Messaging, so it was easy to port my .NET library to Java. 

## Maven Dependencies ##

You can add the following dependencies to your pom.xml to include [FcmJava] in your project.

```xml
<dependency>
  <groupId>de.bytefish.fcmjava</groupId>
  <artifactId>fcmjava-core</artifactId>
  <version>0.6</version>
</dependency>

<dependency>
  <groupId>de.bytefish.fcmjava</groupId>
  <artifactId>fcmjava-client</artifactId>
  <version>0.6</version>
</dependency>
```

## Quickstart ##

The Quickstart shows you how to work with [FcmJava] and with Firebase Cloud Messaging for an Android application.

The Android application is taken from Googles GitHub repository for the [Firebase Quickstart with Android]:

* [https://github.com/firebase/quickstart-android/tree/master/messaging](https://github.com/firebase/quickstart-android/tree/master/messaging)

The example server application uses [FcmJava] to send a Push data message to the ``news`` Topic. I have implemented the ``FileContentBasedSettings`` class to read the API token from a file.

### FcmClient ###

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.fcmjava.integration;

import com.fasterxml.jackson.annotation.JsonProperty;
import de.bytefish.fcmjava.client.FcmClient;
import de.bytefish.fcmjava.constants.Constants;
import de.bytefish.fcmjava.http.options.IFcmClientSettings;
import de.bytefish.fcmjava.model.options.FcmMessageOptions;
import de.bytefish.fcmjava.model.topics.Topic;
import de.bytefish.fcmjava.requests.topic.TopicUnicastMessage;
import org.junit.Ignore;
import org.junit.Test;

import java.nio.charset.Charset;
import java.time.Duration;

public class FcmClientIntegrationTest {

    private class PersonData {

        private final String firstName;
        private final String lastName;

        public PersonData(String firstName, String lastName) {
            this.firstName = firstName;
            this.lastName = lastName;
        }

        @JsonProperty("firstName")
        public String getFirstName() {
            return firstName;
        }

        @JsonProperty("lastName")
        public String getLastName() {
            return lastName;
        }
    }

    @Test
    @Ignore("This is an Integration Test using system properties to contact the FCM Server")
    public void SendTopicMessageTest() throws Exception {

        // Creates the Client using the default settings location, which is System.getProperty("user.home") + "/.fcmjava/fcmjava.properties":
        FcmClient client = new FcmClient();

        // Message Options:
        FcmMessageOptions options = FcmMessageOptions.builder()
                .setTimeToLive(Duration.ofHours(1))
                .build();

        // Send a Message:
        client.send(new TopicUnicastMessage(options, new Topic("news"), new PersonData("Philipp", "Wagner")));
    }
}
```

### API Key ###

By default the FCM API Key is read from an external ``.properties`` file called ``fcmjava.properties`` 
to ensure the API Key secret does not reside in code or leaks into the public. The default location of 
the ``fcmjava.properties`` is ``System.getProperty("user.home") + "/.fcmjava/fcmjava.properties"``.

The file has to contain the FCM API Endpoint and the API Key:

```properties
fcm.api.url=https://fcm.googleapis.com/fcm/send
fcm.api.key=<YOUR_API_KEY_HERE>
```

If the properties are available in the default location you can simply instantiate the ``FcmClient``as seen in the example.

You can use the ``PropertiesBasedSettings`` class to read the Properties and pass them into the ``FcmClient``, if the Properties path differs from the default path:

1. ``PropertiesBasedSettings.createFromDefault()``
    * Uses the default file location of ``System.getProperty("user.home") + "/.fcmjava/fcmjava.properties"`` to read the properties. This is the recommended way of reading your API Key.
2. ``PropertiesBasedSettings.createFromFile(Path path, Charset charset)``
    * Uses a custom file location to read the settings from.
3. ``PropertiesBasedSettings.createFromSystemProperties()``
    * Uses the System Properties to initialize the settings.

### Android Client ###

I have decided to clone the messaging quickstart sample of Google, which is available at:

* [https://github.com/firebase/quickstart-android/tree/master/messaging](https://github.com/firebase/quickstart-android/tree/master/messaging)

Now first subscribe to the ``news`` topic, then execute the above [FcmJava] application. 

The Android app will now receive a message with the sent data included:

```
09-17 21:10:45.250 10882-11300/com.google.firebase.quickstart.fcm D/MyFirebaseMsgService: From: /topics/news
09-17 21:10:45.251 10882-11300/com.google.firebase.quickstart.fcm D/MyFirebaseMsgService: Message data payload: {lastName=Wagner, firstName=Philipp}
```

## Additional Resources ##

I have written an example Weather Warning Application using FcmJava.

The Android Application can be found at:

* [https://github.com/bytefish/WeatherWarningApp](https://github.com/bytefish/WeatherWarningApp)

The server-side using [FcmJava] can be found at:

* [https://github.com/bytefish/FcmJava/...](https://github.com/bytefish/FcmJava/blob/master/FcmJava/fcmjava-client/src/test/java/de/bytefish/fcmjava/integration/WeatherWarningIntegrationTest.java)

[FcmJava]: https://github.com/bytefish/FcmJava
[Firebase Quickstart with Android]: https://github.com/firebase/quickstart-android/tree/master/messaging
[Firebase Cloud Messaging (FCM) API]: https://firebase.google.com
[Firebase Cloud Messaging HTTP Protocol]: https://firebase.google.com/docs/cloud-messaging/http-server-ref