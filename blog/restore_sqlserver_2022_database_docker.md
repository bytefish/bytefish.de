title: Restoring a SQL Server Database Backup using Docker
date: 2024-04-18 15:46
tags: sqlserver, docker
category: docker
slug: restore_sqlserver_2022_database_docker
author: Philipp Wagner
summary: This article shows how to restore a database backup using Docker.

[WideWorldImporters]: https://github.com/bytefish/WideWorldImporters

I am currently updating several of my GitHub projects to use Docker, so it's easier for users to get started. The [WideWorldImporters] 
project requires a SQL Server 2022 database and we'll need to restore Microsofts WideWorldImporters OLTP Database to it:

* [https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is](https://docs.microsoft.com/en-us/sql/samples/wide-world-importers-what-is)

This should have been a very straightforward process, but the `sqlcmd` coming with the SQL Server 2022 Docker image apparently 
hangs when restoring a database. So we also need to download the latest set of `mssql-tools` when building the image. Maybe this 
article saves a poor soul some minutes.

All code can be found in a Git repository at:

* [https://github.com/bytefish/WideWorldImporters](https://github.com/bytefish/WideWorldImporters)


## Creating the SQL Server 2022 Docker Image ##

We put the T-SQL Code to restore the database into a file `restore.sql`:

```sql
RESTORE DATABASE WideWorldImporters
    FROM DISK = "/tmp/backup/WideWorldImporters-Full.bak"
    WITH 
        MOVE "WWI_Primary" TO "/var/opt/mssql/data/WideWorldImporters.mdf",
        MOVE "WWI_Userdata" TO "/var/opt/mssql/data/WideWorldImporters_UserData.ndf",
        MOVE "WWI_Log" TO "/var/opt/mssql/data/WideWorldImporters.ldf", MOVE "WWI_InMemory_Data_1"
    TO 
        "/var/opt/mssql/data/WideWorldImporters_InMemory_Data_1"

GO
```

After the database has been restored, we'll add a user `wwi` with the `db_datareader` 
and `db_datawriter` roles assigned. In a file `users.sql` we add: 

```sql
USE [WideWorldImporters]
GO

CREATE LOGIN wwi WITH PASSWORD = N'340$Uuxwp7Mcxo7Khy'
GO

CREATE USER wwi FOR LOGIN wwi
GO

EXEC sp_addrolemember N'db_datareader', N'wwi'
GO

EXEC sp_addrolemember N'db_datawriter', N'wwi'
GO
```

These two files should be executed once the SQL Server is ready, so we put it into a shell script `create-db.sh`. Instead 
of complex logic, I just wait 30 seconds for the SQL Server to finish initialization:

```bash
#!/bin/bash

# Wait for SQL Server to complete
sleep 30s

# Run the setup script to create the DB and the schema in the DB
/opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P $MSSQL_SA_PASSWORD -d master -i restore.sql
/opt/mssql-tools18/bin/sqlcmd -S localhost -C -U sa -P $MSSQL_SA_PASSWORD -d master -i users.sql
```

In the `entrypoint.sh`, which is the Entrypoint for the Docker image, we then run the `create-db.sh` script in the background and spin up the SQL Server using the `sqlservr` executable:

```bash
#!/bin/bash

# Start the script to restore the DB and user
/tmp/backup/create-db.sh &

/opt/mssql/bin/sqlservr
```

Now we can write the `Dockerfile`, which installs the latest `mssql-tools18` (including `sqlcmd`) and copies 
the scripts to the Docker image. Finally our `entrypoint.sh` is set as the Entrypoint, so it starts with the 
container.

```sh
FROM mcr.microsoft.com/mssql/server:2022-latest

WORKDIR /tmp/backup

# Install Packages, because built-in sqlcmd has a bug ...
USER root

RUN apt-get update \
    && ACCEPT_EULA=Y apt-get install mssql-tools18 unixodbc-dev -y \
    && wget -q  https://github.com/Microsoft/sql-server-samples/releases/download/wide-world-importers-v1.0/WideWorldImporters-Full.bak
    
COPY restore.sql .
COPY users.sql .
COPY create-db.sh .
COPY entrypoint.sh .

ENTRYPOINT ["/bin/bash", "/tmp/backup/entrypoint.sh"]
```

```yaml
version: '3.8'

networks:
  wwi:
    driver: bridge

services:
  db:
    container_name: wwi-sqlserver2022
    build:
      context: ./db/
      dockerfile: Dockerfile
    networks:
      - wwi
    ports:
      - "1533:1433"
    healthcheck:
      test: /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$$MSSQL_SA_PASSWORD" -C -Q "SELECT 1" || exit 1
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 10s
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "StrongPassword@"
```

## Conclusion ##

And that's it! Running a `docker-compose up` will now build a Docker image with an SQL Server 2022 and the WideWorldImporters Backup restored.