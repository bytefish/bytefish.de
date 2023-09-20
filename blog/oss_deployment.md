title: Releasing Java libraries to the Central Repository
date: 2016-02-15 16:16
tags: java, ossrh
category: java
slug: oss_deployment
author: Philipp Wagner
summary: This article describes how to release Java libraries to the OSSRH.

[MIT License]: https://opensource.org/licenses/MIT
[NuGet]: http://www.nuget.org
[OSSRH]: http://central.sonatype.org
[Central Repository]: http://central.sonatype.org

As an open source developer I want to share my work and make utilizing the libraries as easy as possible. It 
is often not sufficient to share the sources to GitHub, because users may not be willed to build the binaries 
by themselves or they have to keep track of dependencies.

.NET has [NuGet] as a package repository and Java offers the [Central Repository] to publish open source libraries. 
The release process to [NuGet] is a very simple one: just register an account and push your package. It was a little 
harder to release my small libraries to the [Central Repository] without going all in on Maven.

Here is a small description of the necessary steps for manually releasing a library to the Central Repository using 
the Sonatype OSS Repository Hosting (OSSRH).

## Prerequisites for Deployment ##

### Initial Setup ###

The initial repository for a new project has to be approved, which requires human interaction ([Explanation](http://central.sonatype.org/articles/2014/Feb/27/why-the-wait/)). Basically you 
only have to register in the Sonatype JIRA and issue a new Project ticket. You have to choose a Group ID, describe your project and wait for your request to be approved. 

* [Create your JIRA account](https://issues.sonatype.org/secure/Signup!default.jspa)
* [Create a New Project ticket](https://issues.sonatype.org/secure/CreateIssue.jspa?issuetype=21&pid=10134)

### Deployment Requirements ###

[Requirements]: http://central.sonatype.org/pages/requirements.html

It is not sufficient to simply upload a JAR to the [OSSRH]. There is a list of [Requirements] for publishing to the Central Repository, that will be 
checked when uploading an artifact. The Requirements are:

* Supply Javadoc and Sources
* Sign Files with GPG/PGP
* Sufficient Metadata

### Create and Upload Signing Key ##

The packages need to be signed with PGP/GPG and come with an ``.asc`` file containing the signature. The first step in the signature process is to create a 
Signarure key, which can be done with the following command (or a UI of course!):

```
gpg --gen-key
```

The Central Repository then requires you to upload the signature key to the keyserver. A kind warning first: If you publish your key to a public keyserver, your 
associated mail address is going to be visible to everyone. Keyservers are possibly harvested by spammers for mail addresses, so you either need to have trust 
in your spam filters or you better create a mail address specific to the signature part. 

The upload to a Keyserver can be done with the following command (or a UI of course!):

```
gpg --keyserver pool.sks-keyservers.net --send-keys <your KEYID>
```

For a more detailed writeup I suggest to read the Sonatype documentation on [Working with PGP Signatures](http://central.sonatype.org/pages/working-with-pgp-signatures.html).

## Project Object Model (POM) ##

The next step is to create the Project Object Model (POM) for your project. A POM file is used by Maven to build a Java project and it also contains the projects 
metadata (Project Name, Authors, Licenses, Dependencies, ...). The full list of required tags can be found at the Central Repository guide on [Requirements].

Here is the POM file for my [PgBulkInsert](https://codeberg.org/bytefish/PgBulkInsert) project:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">

    <modelVersion>4.0.0</modelVersion>

    <!-- Basic Project Information -->
    <groupId>de.bytefish</groupId>
    <artifactId>pgbulkinsert</artifactId>
    <version>0.4</version>
    <packaging>jar</packaging>
    <name>pgbulkinsert</name>
    <description>PgBulkInsert is a Java 1.8 library for Bulk Inserts with PostgreSQL.</description>
    <url>http://www.github.com/bytefish/PgBulkInsert</url>

    <!-- Define the License -->
    <licenses>
        <license>
            <name>MIT License</name>
            <url>https://opensource.org/licenses/MIT</url>
        </license>
    </licenses>
    <scm>
        <url>https://codeberg.org/bytefish/PgBulkInsert</url>
        <connection>scm:git:git://github.com/bytefish/PgBulkInsert.git</connection>
        <developerConnection>scm:git:git@github.com:bytefish/PgBulkInsert.git</developerConnection>
    </scm>
    <!-- Developers -->
    <developers>
        <developer>
            <email>bytefish@gmx.de</email>
            <name>Philipp Wagner</name>
            <url>https://www.bytefish.de</url>
            <id>bytefish</id>
        </developer>
    </developers>

    <!-- Dependencies -->
    <dependencies>
    <dependency>
        <groupId>org.postgresql</groupId>
        <artifactId>postgresql</artifactId>
        <version>9.4-1206-jdbc42</version>
    </dependency>
    </dependencies>

</project>
```

## Manual Staging Bundle Creation ##

[Manual Staging Bundle Creation and Deployment]: http://central.sonatype.org/pages/manual-staging-bundle-creation-and-deployment.html

The Central Repository documentation has a page on [Manual Staging Bundle Creation and Deployment], which describes how to bundle 
a Java library for deploying it to the Central Repository. I have turned the described steps into a small Batch script, that 
automatically creates the bundle to upload.

The script basically looks up and bundles two files:

1. The JAR file ``artifacts/VERSION/FILENAME-VERSION.jar``, where artifact directory, filename and version are set in the Batch script.
2. The POM file at ``artifacts/VERSION/pom.xml``, which has to be created in the artifacts directory.

Make sure, these two files are present in the ``artifacts`` directory. And in order to successfully deploy the bundle to the Central Repository, 
you have to make sure, that the version of the Bundle filename and version in the POM file match.

The Central Repository deployment process requires to also bundle the javadoc and sources for the library. I don't have included them in 
my bundles and have included empty JAR files for both. If your library should include javadoc and sources, you have to modify the script 
accordingly.

```batch
:: Copyright (c) Philipp Wagner. All rights reserved.
:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

@echo off

echo ---------------------------------------------------
echo - Bundling Artifacts for Manual Repository Upload -
echo ---------------------------------------------------

:: Define the Executables, so we don't have to rely on pathes:
set JAR_EXECUTABLE="C:\Program Files\Java\jdk1.8.0_71\bin\jar.exe"
set GPG_EXECUTABLE="C:\Program Files (x86)\GNU\GnuPG\pub\gpg.exe"

:: Logs to be used:
set STDOUT=stdout.log
set STDERR=stderr.log

:: Version to build the bundle for:
set VERSION=0.4

:: Set the Target Bundle file:
set TARGET_BUNDLE=bundle\pgbulkinsert-bundle-%VERSION%.jar

:: Define the Artifacts to be signed. Simply use an absolute path here:
set ARTIFACTS_DIR=artifacts
set BASE_DIR=%ARTIFACTS_DIR%\%VERSION%

:: Set the Filename for artifacts to use:
set FILENAME=pgbulkinsert-%VERSION%

set JAR_FILE=%FILENAME%.jar
set JAR_SOURCES_FILE=%FILENAME%-sources.jar
set JAR_JAVADOC_FILE=%FILENAME%-javadoc.jar

set POM_FILE=pom.xml

set JAR_FILE_ASC=%JAR_FILE%.asc
set POM_FILE_ASC=%POM_FILE%.asc
set JAR_SOURCES_FILE_ASC=%JAR_SOURCES_FILE%.asc
set JAR_JAVADOC_FILE_ASC=%JAR_JAVADOC_FILE%.asc

:: Ask for GPG Signing Passphrase:

set /p PASSPHRASE="Signing Passphrase: "

1>%STDOUT% 2>%STDERR% (
    
    :: Create Fake:
    %JAR_EXECUTABLE% -cf %BASE_DIR%\%JAR_SOURCES_FILE% -C %ARTIFACTS_DIR% README.txt
    %JAR_EXECUTABLE% -cf %BASE_DIR%\%JAR_JAVADOC_FILE% -C %ARTIFACTS_DIR% README.txt
    
    :: Sign JAR and POM Files:
    echo %PASSPHRASE%|%GPG_EXECUTABLE% --batch --yes --passphrase-fd 0  -b -a -s "%BASE_DIR%\%JAR_FILE%"  
    echo %PASSPHRASE%|%GPG_EXECUTABLE% --batch --yes --passphrase-fd 0  -b -a -s "%BASE_DIR%\%POM_FILE%"
    echo %PASSPHRASE%|%GPG_EXECUTABLE% --batch --yes --passphrase-fd 0  -b -a -s "%BASE_DIR%\%JAR_SOURCES_FILE%"
    echo %PASSPHRASE%|%GPG_EXECUTABLE% --batch --yes --passphrase-fd 0  -b -a -s "%BASE_DIR%\%JAR_JAVADOC_FILE%"

    :: Create the Bundle File for manual upload:
    %JAR_EXECUTABLE% -cf "%TARGET_BUNDLE%" -C "%BASE_DIR%" "%JAR_FILE%" -C "%BASE_DIR%" "%JAR_FILE_ASC%" -C "%BASE_DIR%" "%POM_FILE%" -C "%BASE_DIR%" "%POM_FILE_ASC%" -C "%BASE_DIR%" "%JAR_SOURCES_FILE%" -C "%BASE_DIR%" "%JAR_JAVADOC_FILE%" -C "%BASE_DIR%" "%JAR_SOURCES_FILE_ASC%" -C "%BASE_DIR%" "%JAR_JAVADOC_FILE_ASC%"
    
)

pause
```

When you have run the script, you can find the created bundle at ``bundle\FILENAME-%VERSION%.jar``, which can be configured with the variable ``TARGET_BUNDLE``.

## Artifact Bundle Upload ##

Once the bundle has been created, it can be uploaded manually by using the [Nexus Repository Manager](https://oss.sonatype.org/). 

1. Switch to the menu item ``Staging Upload`` and choose ``Upload Mode: Artifact Bundle``, then upload your Bundle.
2. Switch to ``Staging Repositories`` and select the Repository created by the Bundle upload.
2.1. Under the Tab ``Activity`` you can see if all Rules for a Release have passed.
3. If all rules have been passed, you can click on the ``Release`` button to release your Bundle to the Central Repository.