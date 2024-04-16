title: Using Testcontainers in .NET
date: 2024-04-17 06:52
tags: postgres, dotnet, docker, testcontainers
category: dotnet
slug: testcontainers_dotnet
author: Philipp Wagner
summary: This article shows how to use Testcontainers in .NET.

[gitclub-dotnet]: https://github.com/bytefish/gitclub-dotnet

In [gitclub-dotnet] I need a few services to run for the integration tests. In this article we will take a look at Testcontainers for .NET, which is ...

> [...] a library to support tests with throwaway instances of Docker containers for all compatible .NET Standard versions. The library is built on top of the .NET Docker remote API and provides a lightweight implementation to support your test environment in all circumstances.

All code can be found in a Git repository at:

* [https://github.com/bytefish/gitclub-dotnet](https://github.com/bytefish/gitclub-dotnet)


## Using Testcontainers with MSTest ##

In the [gitclub-dotnet] we have already written a `docker-compose.yaml` file, which is responsible for spinning up a Postgres instance and OpenFGA containers.  

```yaml
version: '3.8'

networks:
  openfga:

services:
  postgres:
    image: postgres:16
    container_name: postgres
    networks:
      - openfga
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - "./postgres/postgres.conf:/usr/local/etc/postgres/postgres.conf"
      - ../sql/openfga.sql:/docker-entrypoint-initdb.d/1-openfga.sql
      - ../sql/gitclub.sql:/docker-entrypoint-initdb.d/2-gitclub.sql
      - ../sql/gitclub-versioning.sql:/docker-entrypoint-initdb.d/3-gitclub-versioning.sql
      - ../sql/gitclub-notifications.sql:/docker-entrypoint-initdb.d/4-gitclub-notifications.sql
      - ../sql/gitclub-replication.sql:/docker-entrypoint-initdb.d/5-gitclub-replication.sql
      - ../sql/gitclub-tests.sql:/docker-entrypoint-initdb.d/6-gitclub-tests.sql
      - ../sql/gitclub-data.sql:/docker-entrypoint-initdb.d/7-gitclub-data.sql
    command: "postgres -c config_file=/usr/local/etc/postgres/postgres.conf"
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 5s
      timeout: 5s
      retries: 5
      
  migrate:
    depends_on:
      postgres:
        condition: service_healthy
    image: openfga/openfga:latest
    container_name: migrate
    command: migrate
    environment:
      - OPENFGA_DATASTORE_ENGINE=postgres
      - OPENFGA_DATASTORE_URI=postgres://postgres:password@postgres:5432/postgres?sslmode=disable&search_path=openfga
    networks:
      - openfga
      
  openfga:
    depends_on:
      migrate:
        condition: service_completed_successfully
    image: openfga/openfga:latest
    container_name: openfga
    environment:
      - OPENFGA_DATASTORE_ENGINE=postgres
      - OPENFGA_DATASTORE_URI=postgres://postgres:password@postgres:5432/postgres?sslmode=disable&search_path=openfga
      - OPENFGA_LOG_FORMAT=json
    command: run
    networks:
      - openfga
    ports:
      # Needed for the http server
      - "8080:8080"
      # Needed for the grpc server (if used)
      - "8081:8081"
      # Needed for the playground (Do not enable in prod!)
      - "3000:3000"
    healthcheck:
      test: ['CMD', '/usr/local/bin/grpc_health_probe', '-addr=openfga:8081']
      interval: 5s
      timeout: 30s
      retries: 3
      
  gitclub-fga-model-docker:
    depends_on:
      openfga:
        condition: service_healthy
    image: openfga/cli:latest
    container_name: gitclub-fga-model
    networks:
      - openfga
    volumes:
      - ../fga/gitclub.fga.yaml:/gitclub.fga.yaml
      - ../fga/gitclub-model.fga:/gitclub-model.fga
      - ../fga/gitclub-tuples.yaml:/gitclub-tuples.yaml
    command: store import --api-url http://openfga:8080 --file /gitclub.fga.yaml --store-id ${FGA_STORE_ID}
```

We now start the Testcontainers implementation by adding all files required by the Docker containers as a Link in our Solution. This has the nice side-effect, that you can use the files for both, the `docker-compose.yaml` and the Testcontainers.

Make sure to always copy the files to the output directory.

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <!-- ... -->
  
  <ItemGroup>
    <Folder Include="Resources\docker\" />
    <Folder Include="Resources\fga\" />
    <Folder Include="Resources\sql\" />
  </ItemGroup>

  <ItemGroup>
    <None Include="..\..\docker\postgres\postgres.conf" Link="Resources\docker\postgres.conf">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\fga\gitclub-model.fga" Link="Resources\fga\gitclub-model.fga">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\fga\gitclub-tuples.yaml" Link="Resources\fga\gitclub-tuples.yaml">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\fga\gitclub.fga.yaml" Link="Resources\fga\gitclub.fga.yaml">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\gitclub-data.sql" Link="Resources\sql\gitclub-data.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\gitclub-notifications.sql" Link="Resources\sql\gitclub-notifications.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\gitclub-replication.sql" Link="Resources\sql\gitclub-replication.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\gitclub-tests.sql" Link="Resources\sql\gitclub-tests.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\gitclub-versioning.sql" Link="Resources\sql\gitclub-versioning.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\gitclub.sql" Link="Resources\sql\gitclub.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
    <None Include="..\..\sql\openfga.sql" Link="Resources\sql\openfga.sql">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
  </ItemGroup>

  <!-- ... -->

</Project>
```

We can then create a class `DockerContainers`, which is basically a one to one translation from the `docker-compose.yaml` to the Testcontainers syntax.

Please note, that it only needs to be `static`, because of the MSTest lifecycle, which requires `static` methods for class and assembly level test initialization.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Configurations;
using DotNet.Testcontainers.Containers;
using DotNet.Testcontainers.Networks;

namespace GitClub.Tests
{
    public static class DockerContainers
    {
        public static INetwork OpenFgaNetwork = new NetworkBuilder()
            .WithName("openfga")
            .WithDriver(NetworkDriver.Bridge)
            .Build();

        public static IContainer PostgresContainer = new ContainerBuilder()
            .WithName("postgres")
            .WithImage("postgres:16")
            .WithNetwork(OpenFgaNetwork)
            .WithPortBinding(hostPort: 5432, containerPort: 5432)
            // Mount Postgres Configuration and SQL Scripts 
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/docker/postgres.conf"), "/usr/local/etc/postgres/postgres.conf")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/openfga.sql"), "/docker-entrypoint-initdb.d/1-openfga.sql")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/gitclub.sql"), "/docker-entrypoint-initdb.d/2-gitclub.sql")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/gitclub-versioning.sql"), "/docker-entrypoint-initdb.d/3-gitclub-versioning.sql")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/gitclub-notifications.sql"), "/docker-entrypoint-initdb.d/4-gitclub-notifications.sql")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/gitclub-replication.sql"), "/docker-entrypoint-initdb.d/5-gitclub-replication.sql")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/gitclub-tests.sql"), "/docker-entrypoint-initdb.d/6-gitclub-tests.sql")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/sql/gitclub-data.sql"), "/docker-entrypoint-initdb.d/7-gitclub-data.sql")
            // Set Username and Password
            .WithEnvironment(new Dictionary<string, string>
            {
                    {"POSTGRES_USER", "postgres" },
                    {"POSTGRES_PASSWORD", "password" },
            })
            // Start Postgres with the given postgres.conf.
            .WithCommand([
                "postgres",
                "-c",
                "config_file=/usr/local/etc/postgres/postgres.conf"
            ])
            // Wait until the Port is exposed.
            .WithWaitStrategy(Wait
                .ForUnixContainer()
                .UntilPortIsAvailable(5432))
            .Build();

        public static IContainer OpenFgaMigrateContainer = new ContainerBuilder()
            .WithName("openfga-migration")
            .WithImage("openfga/openfga:latest")
            .DependsOn(PostgresContainer)
            .WithNetwork(OpenFgaNetwork)
            .WithEnvironment(new Dictionary<string, string>
            {
                {"OPENFGA_DATASTORE_ENGINE", "postgres" },
                {"OPENFGA_DATASTORE_URI", "postgres://postgres:password@postgres:5432/postgres?sslmode=disable&search_path=openfga" }
            })
            .WithCommand("migrate")
            .Build();

        public static IContainer OpenFgaServerContainer = new ContainerBuilder()
            .WithName("openfga-server")
            .WithImage("openfga/openfga:latest")
            .DependsOn(OpenFgaMigrateContainer)
            .WithNetwork(OpenFgaNetwork)
            .WithCommand("run")
            .WithPortBinding(hostPort: 8080, containerPort: 8080)
            .WithPortBinding(hostPort: 8081, containerPort: 8081)
            .WithPortBinding(hostPort: 3000, containerPort: 3000)
            .WithEnvironment(new Dictionary<string, string>
            {
                {"OPENFGA_DATASTORE_ENGINE", "postgres" },
                {"OPENFGA_DATASTORE_URI", "postgres://postgres:password@postgres:5432/postgres?sslmode=disable&search_path=openfga" }
            })
            .WithWaitStrategy(Wait
                .ForUnixContainer()
                .UntilMessageIsLogged("HTTP server listening on '0.0.0.0:8080'.."))
            .Build();

        public static IContainer OpenFgaModelContainer = new ContainerBuilder()
            .WithName("openfga-model")
            .WithImage("openfga/cli:latest")
            .DependsOn(OpenFgaServerContainer)
            .WithNetwork(OpenFgaNetwork)
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/fga/gitclub.fga.yaml"), "/gitclub.fga.yaml")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/fga/gitclub-model.fga"), "/gitclub-model.fga")
            .WithBindMount(Path.Combine(Directory.GetCurrentDirectory(), "Resources/fga/gitclub-tuples.yaml"), "/gitclub-tuples.yaml")
            .WithCommand([
                "store",
                "import",
                "--api-url", "http://openfga-server:8080",
                "--file", "/gitclub.fga.yaml",
                "--store-id", "01HP82R96XEJX1Q9YWA9XRQ4PM"
            ])
            .Build();

        public static async Task StartAllContainersAsync()
        {
            await PostgresContainer.StartAsync();
            await OpenFgaMigrateContainer.StartAsync();
            await OpenFgaServerContainer.StartAsync();
            await OpenFgaModelContainer.StartAsync();
        }

        public static async Task StopAllContainersAsync()
        {
            await PostgresContainer.StopAsync();
            await OpenFgaMigrateContainer.StopAsync();
            await OpenFgaServerContainer.StopAsync();
            await OpenFgaModelContainer.StopAsync();
        }
    }
}
```

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace GitClub.Tests
{
    [TestClass]
    public abstract class IntegrationTestBase
    {
        // ...
        
        [AssemblyInitialize]
        public static async Task AssemblyInitializeAsync(TestContext context)
        {
            await DockerContainers.StartAllContainersAsync();
        }

        [AssemblyCleanup]
        public static async Task AssemblyCleanupAsync()
        {
            await DockerContainers.StopAllContainersAsync();
        }

        // ...
    }
}
```

## Conclusion ##

And that's it. You will now see the Containers spinning up for the tests, so there's no need for manually running a `docker-compose` before executing the tests.

To get a more reliable container initialization sequence, you'll probably need better Wait Strategy, which is described in the Testcontainers documentation at:

* [https://dotnet.testcontainers.org/api/wait_strategies/](https://dotnet.testcontainers.org/api/wait_strategies/)

Enjoy your integration tests!