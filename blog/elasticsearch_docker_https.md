title: Elasticsearch: Enabling HTTPS for Local Development in Docker
date: 2024-06-21 10:56
tags: elasticsearch, docker
category: elasticsearch
slug: elasticsearch_docker_https
author: Philipp Wagner
summary: This article shows how to enable HTTPS for Elasticsearch in Docker.

This is just a quick writeup on how to enable HTTPS for Elasticsearch, when 
running in a Docker container. It has taken me too much time to piece this 
together, so maybe it helps someone trying to do the same.

All code can be found in a Git repository at:

* [https://github.com/bytefish/ElasticsearchCodeSearch](https://github.com/bytefish/ElasticsearchCodeSearch)

## Configuring HTTPS for Elasticsearch ##

To secure the HTTPS communication with Elasticsearch we need to generate a certificate 
first. The easiest way to do this is to use the `elasticsearch-certutil` command line 
tool.

We start by creating a Certificate Authority (CA):

```powershell
elasticsearch-certutil ca --silent --pem -out ./elastic-cert/ca.zip
```

In the `docker/elasticsearch/elastic-cert` we will now find a `ca.zip` and unzip it.

Next we create a `instances.yml`file for the local Elasticsearch instance `es01`:

```yaml
instances:
  - name: es01
    dns:
      - es01
      - localhost
    ip:
        - 127.0.0.1
```

We can then pass the `instances.yml` to the `elasticsearch-certutil` command line tool and 
create a certificate using our previously generated CA certificate:

```powershell
elasticsearch-certutil cert --silent --pem -out ./certs.zip --in ./instances.yml --ca-cert ./elastic-cert/ca/ca.crt --ca-key ./elastic-cert/ca/ca.key
```

In an `.env` file we are defining the Environment variables as:

```
ELASTIC_HOSTNAME=es01
ELASTIC_USERNAME=elastic
ELASTIC_PASSWORD=secret
ELASTIC_PORT=9200
ELASTIC_SECURITY=true
ELASTIC_SCHEME=https
ELASTIC_VERSION=8.14.1
```

In the `docker-compose.yml` we then configure `elasticsearch` with our generated certificates as:

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:${ELASTIC_VERSION:-8.14.1}
    container_name: ${ELASTIC_HOSTNAME:-es01}
    hostname: ${ELASTIC_HOSTNAME:-es01}
    restart: ${RESTART_MODE:-unless-stopped}
    healthcheck:
      test: ["CMD-SHELL", "curl --user ${ELASTIC_USER:-elastic}:${ELASTIC_PASSWORD:-secret} --silent --fail https://localhost:9200/_cluster/health -k || exit 1" ]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    env_file:
      - ./.env
    environment:
      - node.name=es01
      - discovery.type=single-node
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD:-secret}
      - xpack.security.enabled=${ELASTIC_SECURITY:-true}
      - xpack.security.http.ssl.enabled=true
      - xpack.security.http.ssl.verification_mode=none
      - xpack.security.http.ssl.key=/usr/share/elasticsearch/config/cert/es01.key
      - xpack.security.http.ssl.certificate=/usr/share/elasticsearch/config/cert/es01.crt
      - xpack.security.http.ssl.certificate_authorities=/usr/share/elasticsearch/config/cert/ca/ca.crt
      - xpack.security.transport.ssl.enabled=${ELASTIC_SECURITY:-true}
      - xpack.security.transport.ssl.verification_mode=none
      - xpack.security.transport.ssl.certificate_authorities=/usr/share/elasticsearch/config/cert/ca/ca.crt
      - xpack.security.transport.ssl.certificate=/usr/share/elasticsearch/config/cert/es01.crt
      - xpack.security.transport.ssl.key=/usr/share/elasticsearch/config/cert/es01.key
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - ./elasticsearch/elastic-data:/usr/share/elasticsearch/data
      - ./elasticsearch/elastic-cert:/usr/share/elasticsearch/config/cert
    ports:
      - "9200:9200"
      - "9300:9300"
```

We can now verify, if Elasticsearch starts correctly by using `curl`:

```Powershell
C:\Users\philipp>curl -k https://127.0.0.1:9200  -u elastic:secret
{
  "name" : "es01",
  "cluster_name" : "docker-cluster",
  "cluster_uuid" : "2pvSQcC-Tnu-cbQuc1AONw",
  "version" : {
    "number" : "8.14.1",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "93a57a1a76f556d8aee6a90d1a95b06187501310",
    "build_date" : "2024-06-10T23:35:17.114581191Z",
    "build_snapshot" : false,
    "lucene_version" : "9.10.0",
    "minimum_wire_compatibility_version" : "7.17.0",
    "minimum_index_compatibility_version" : "7.0.0"
  },
  "tagline" : "You Know, for Search"
}
```

And finally we calculate the Certificate Fingerprint using:

```powershell
openssl.exe x509 -fingerprint -sha256 -in .\es01.crt
```

And get our Certificate Fingerprint as:

```
31a63ffca5275df7ea7d6fc7e92b42cfa774a0feed7d7fa8488c5e46ea9ade3f
```

And that's it.

In the .NET application I can then create the `ElasticsearchClient` like this:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace ElasticsearchCodeSearch.Shared.Elasticsearch
{
    public class ElasticCodeSearchClient
    {
    
        // ...
    
        public virtual ElasticsearchClient CreateClient(ElasticCodeSearchOptions options)
        {
            var settings = new ElasticsearchClientSettings(new Uri(options.Uri))
                .CertificateFingerprint(options.CertificateFingerprint)
                .Authentication(new BasicAuthentication(options.Username, options.Password));

            return new ElasticsearchClient(settings);
        }
        
        // ...
    }
}
```