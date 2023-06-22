title: Inovking a RESTful API with Powershell
date: 2023-06-22 12:22
tags: powershell, odata
category: powershell
slug: powershell_invoking_rest_apis
author: Philipp Wagner
summary: This article shows how to secure an ASP.NET Core OData API using the ODataAuthorization library.

[ODataAuthorization]: https://github.com/bytefish/ODataAuthorization/

In this article we will take a look at invoking a RESTful API with Powershell. We are 
going to use the `Invoke-RestMethod` cmdlet and learn about its parameters. Maybe it's 
useful to someone to get going quickly.

## The Problem ##

There was a bug in the [ODataAuthorization] library, and instead of using 
Postman I thought it would be nice to learn a little Powershell and execute 
requests using a Script.

So basically, I want to make a HTTP Post Request to obtain a Json Web Token 
(JWT) from an Auth Endpoint and execute some HTTP GET requests to OData-enabled 
endpoints.

## The Solution ##

PowerShell comes with the built-in `Invoke-RestMethod` cmdlet to call RESTful APIs:

* [https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-restmethod?view=powershell-7.3](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-restmethod?view=powershell-7.3)

The idea for each request is to basically define the parameters for `Invoke-RestMethod` like this:

```powershell
$authRequestParameters = @{
    Method = "POST"
    Uri = "some-url"
    Body = ($someBodyForPost | ConvertTo-Json) 
    ContentType = "application/json"
    # More Parameters here ...
}
```

The request to a given `$AuthUrl` is going to return a JSON 
object, where the `token` property contains the bearer token, 
that we'll need to send in the `Authorization` header.

```powershell
$AuthEmail = "..."
$AuthPassword = "..."
# More variables ...

$authRequestBody = @{
    Email = $AuthEmail
    Password = $AuthPassword
    RequestedScopes = $RequestedScopes
}

$authRequestParameters = @{
    Method = "POST"
    Uri = $AuthUrl
    Body = ($authRequestBody | ConvertTo-Json) 
    ContentType = "application/json"
}

# Invoke the Rest API
$authRequestResponse = Invoke-RestMethod @authRequestParameters

# Extract JWT from the JSON Response 
$authToken = $authRequestResponse.token

# The Auth Header needs to be sent for any additional OData request
$authHeader = @{
    Authorization = "Bearer $authToken"
}
```

The `$authHeader` can then be passed as the `Headers` Parameter to `Invoke-RestMethod`. You 
can also set a variable name, that `Invoke-RestMethod` should write the parameter to 
(`$statusCode` in the example).

```powershell
Write-Host "[REQ]"
Write-Host "[REQ] OData Request"
Write-Host "[REQ]"
Write-Host "[REQ]   Description:    $Description"
Write-Host "[REQ]   URL:            $Endpoint"
Write-Host "[REQ]   Scopes:         $RequestedScopes"
Write-Host "[REQ]"

$odataRequestParameters = @{
    Method = "GET"
    Uri = $Endpoint
    Headers = $authHeader
    StatusCodeVariable = 'statusCode'
}

try {
    
    $oDataResponse = Invoke-RestMethod @odataRequestParameters
    $oDataResponseValue = $oDataResponse.value | ConvertTo-Json
    
    Write-Host "[RES]    HTTP Status:    $statusCode"  -ForegroundColor Green
    Write-Host "[RES]    Body:           $oDataResponseValue"  -ForegroundColor Green
} catch {
    Write-Host "[ERR] Request failed with StatusCode:" $_.Exception.Response.StatusCode.value__ -ForegroundColor Red
}
```

We will then put all logic for querying the OData Endpoints into a function 
`Send-ODataRequest`, which can then be called with sample OData Requests. We 
end up with the following Powershell Script:

```powershell
<#
.SYNOPSIS
    Example Script for restricting Navigation Properties using the 
    ODataAuthorization library.
.DESCRIPTION
    This script obtains a valid token and proceeds to perform requests to
    the API.
.NOTES
    File Name      : ODataQueries.ps1
    Author         : Philipp Wagner
    Prerequisite   : PowerShell
    Copyright 2023 - MIT License
#>

function Send-ODataRequest {
    param (
        [Parameter(Mandatory)]
        [string]$AuthUrl,

        [Parameter(Mandatory)]
        [string]$AuthEmail,

        [Parameter(Mandatory)]
        [string]$AuthPassword,

        [Parameter(Mandatory)]
        [string]$Description,

        [Parameter(Mandatory)]
        [string]$Endpoint,
        
        [Parameter(Mandatory)]
        [string]$RequestedScopes
    )
        
    # Perform /Auth/login to obtain the JWT with Requested Scopes
    $authRequestBody = @{
        Email = $AuthEmail
        Password = $AuthPassword
        RequestedScopes = $RequestedScopes
    }

    $authRequestParameters = @{
        Method = "POST"
        Uri = $AuthUrl
        Body = ($authRequestBody | ConvertTo-Json) 
        ContentType = "application/json"
    }

    # Invoke the Rest API
    $authRequestResponse = Invoke-RestMethod @authRequestParameters

    # Extract JWT from the JSON Response 
    $authToken = $authRequestResponse.token

    # The Auth Header needs to be sent for any additional OData request
    $authHeader = @{
        Authorization = "Bearer $authToken"
    }

    Write-Host "[REQ]"
    Write-Host "[REQ] OData Request"
    Write-Host "[REQ]"
    Write-Host "[REQ]   Description:    $Description"
    Write-Host "[REQ]   URL:            $Endpoint"
    Write-Host "[REQ]   Scopes:         $RequestedScopes"
    Write-Host "[REQ]"

    $odataRequestParameters = @{
        Method = "GET"
        Uri = $Endpoint
        Headers = $authHeader
        StatusCodeVariable = 'statusCode'
    }

    try {
        
        $oDataResponse = Invoke-RestMethod @odataRequestParameters
        $oDataResponseValue = $oDataResponse.value | ConvertTo-Json
        
        Write-Host "[RES]    HTTP Status:    $statusCode"  -ForegroundColor Green
        Write-Host "[RES]    Body:           $oDataResponseValue"  -ForegroundColor Green
    } catch {
        Write-Host "[ERR] Request failed with StatusCode:" $_.Exception.Response.StatusCode.value__ -ForegroundColor Red
    }
}

$authUrl = "http://localhost:5124/Auth/login"
$authEmail = "admin@admin.com"
$authPassword = "123456"

$requests = 
    @{
        AuthUrl = $authUrl
        AuthEmail = $authEmail 
        AuthPassword = $authPassword 
        Description = "Get all Products without 'Address' expanded"
        Endpoint = "http://localhost:5124/odata/Products" 
        RequestedScopes = "Products.Read Products.ReadByKey"
    },    
    @{
        AuthUrl = $authUrl
        AuthEmail = $authEmail 
        AuthPassword = $authPassword 
        Description = "Get all Products with 'Address' expanded. Missing Scope: 'Products.ReadAddress'"
        Endpoint = "http://localhost:5124/odata/Products?`$expand=Address" 
        RequestedScopes = "Products.Read Products.ReadByKey"
    },
    @{
        AuthUrl = $authUrl
        AuthEmail = $authEmail 
        AuthPassword = $authPassword 
        Description = "Get all Products with 'Address' expanded. Valid Required Scopes."
        Endpoint = "http://localhost:5124/odata/Products?`$expand=Address" 
        RequestedScopes = "Products.Read Products.ReadByKey Products.ReadAddress"
    }

foreach ( $request in $requests )
{
    Send-ODataRequest @request
}
```

And we end up with the following output:

```
PS C:\Users\philipp\source\repos\bytefish\ODataAuthorization\samples\JwtAuthenticationExample\PowershellScripts> .\ODataQueries.ps1
[REQ]
[REQ] OData Request
[REQ]
[REQ]   Description:    Get all Products without 'Address' expanded
[REQ]   URL:            http://localhost:5124/odata/Products
[REQ]   Scopes:         Products.Read Products.ReadByKey
[REQ]
[RES]    HTTP Status:    200
[RES]    Body:           [
  {
    "Id": 1,
    "Name": "Macbook M1",
    "Price": 3000,
    "AddressId": 1
  },
  {
    "Id": 2,
    "Name": "Macbook M2",
    "Price": 3500,
    "AddressId": 1
  },
  {
    "Id": 3,
    "Name": "iPhone 14",
    "Price": 1400,
    "AddressId": 1
  }
]
[REQ]
[REQ] OData Request
[REQ]
[REQ]   Description:    Get all Products with 'Address' expanded. Missing Scope: 'Products.ReadAddress'
[REQ]   URL:            http://localhost:5124/odata/Products?$expand=Address
[REQ]   Scopes:         Products.Read Products.ReadByKey
[REQ]
[ERR] Request failed with StatusCode: 403
[REQ]
[REQ] OData Request
[REQ]
[REQ]   Description:    Get all Products with 'Address' expanded. Valid Required Scopes.
[REQ]   URL:            http://localhost:5124/odata/Products?$expand=Address
[REQ]   Scopes:         Products.Read Products.ReadByKey Products.ReadAddress
[REQ]
[RES]    HTTP Status:    200
[RES]    Body:           [
  {
    "Id": 1,
    "Name": "Macbook M1",
    "Price": 3000,
    "AddressId": 1,
    "Address": {
      "Id": 1,
      "Country": "USA",
      "City": "California"
    }
  },
  {
    "Id": 2,
    "Name": "Macbook M2",
    "Price": 3500,
    "AddressId": 1,
    "Address": {
      "Id": 1,
      "Country": "USA",
      "City": "California"
    }
  },
  {
    "Id": 3,
    "Name": "iPhone 14",
    "Price": 1400,
    "AddressId": 1,
    "Address": {
      "Id": 1,
      "Country": "USA",
      "City": "California"
    }
  }
]
```