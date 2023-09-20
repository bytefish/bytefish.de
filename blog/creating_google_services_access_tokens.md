title: Creating OAuth 2.0 Tokens for Firebase Services
date: 2018-05-11 10:08
tags: dotnet, csharp, 
category: dotnet
slug: creating_google_services_access_tokens
author: Philipp Wagner
summary: This article shows how to create Access Tokens for the Firebase Services.

I have recently updated [FcmSharp] to use the Firebase HTTP v1 API. The Firebase APIs require you to authorize requests 
using short-lived OAuth 2.0 tokens. The official documents have examples for JavaScript, Python and Java, but there was 
no simple .NET example. So I am going to share how I did it.

The Google documentation writes in [Authorize Send Requests]:

> Every Firebase project has a default service account. You can use this account to call Firebase server APIs from your 
> app server or trusted environment. If you use a different service account, make sure it has Editor or Owner permissions.
> 
> To authenticate the service account and authorize it to access Firebase services, you must generate a private key file 
> in JSON format and use this key to retrieve a short-lived OAuth 2.0 token. Once you have a valid token, you can add it 
> in your server requests as required by the various Firebase services such as Remote Config or FCM.
> 
> To generate a private key file for your service account:
> 
> 1. In the Firebase console, open **Settings > [Service Accounts](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk)**.
> 2. Click **Generate New Private Key**, and confirm by clicking **Generate Key**.
> 3. Securely store the JSON file containing the key. You'll need it to complete the next step.

## Reading the Credentials ##

```csharp
private static string ReadCredentialsFromFile(string fileName)
{
    if (fileName == null)
    {
        throw new ArgumentNullException("fileName");
    }

    if (!File.Exists(fileName))
    {
        throw new Exception(string.Format("Could not Read Credentials. (Reason = File Does Not Exist, FileName = '{0}')", fileName));
    }

    string credentials = File.ReadAllText(fileName);

    if (string.IsNullOrWhiteSpace(credentials))
    {
        throw new Exception(string.Format("Could not Read Credentials. (Reason = File Is Empty, FileName = '{0}')", fileName));
    }

    return credentials;
}
```

## Creating the OAuth 2.0 Access Token ##

```csharp
public class FcmHttpClient : IFcmHttpClient
{
    public FcmHttpClient()
        : this(new ConfigurableHttpClient(new ConfigurableMessageHandler(new HttpClientHandler())))
    {
    }

    public FcmHttpClient(ConfigurableHttpClient client) 
    {
        if (client == null)
        {
            throw new ArgumentNullException("client");
        }
        
        this.client = client;
    }

    public async Task<string> CreateAccessTokenAsync(string credentials, CancellationToken cancellationToken)
    {
        
        var credential = GoogleCredential.FromJson(credentials)    
            // We need the Messaging Scope:
            .CreateScoped("https://www.googleapis.com/auth/firebase.messaging")
            // Cast to the ServiceAccountCredential:
            .UnderlyingCredential as ServiceAccountCredential;
        
        if (credential == null)
        {
            throw new Exception("Error creating Access Token for Authorizing Request");
        }

        // Initialize with the Configurable Client:
        credential.Initialize(client);

        // Execute the Request:
        var accessToken = await credential.GetAccessTokenForRequestAsync(cancellationToken: cancellationToken);

        if (accessToken == null)
        {
            throw new Exception("Empty Access Token for Authorizing Request");
        }

        return accessToken;
    }
    
    // ...
}
```

[FcmSharp]: https://codeberg.org/bytefish/FcmSharp
[Authorize Send Requests]: https://firebase.google.com/docs/cloud-messaging/auth-server