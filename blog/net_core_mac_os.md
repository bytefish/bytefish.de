title: Installing .NET Core on Mac OS X
date: 2016-07-19 21:46
tags: dotnet, mac
category: dotnet
slug: net_core_mac_os
author: Philipp Wagner
summary: This article shows how to install .NET Core on Mac OS X.

I have bought a MacBook lately and wanted to learn how to work with .NET Core. The first thing is installing the 
.NET Core libraries and tools of course, which is available from:

* [https://www.microsoft.com/net/core#macos](https://www.microsoft.com/net/core#macos)

.NET Core requires OpenSSL 1.0.0 or later, but Mac OS X currently defaults to OpenSSL 0.9.8. So we first download 
the sources for the latest stable OpenSSL release 1.0.2h:

* [https://www.openssl.org/source/](https://www.openssl.org/source/)

Next unpack the OpenSSL Sources:

```
tar xzf openssl-1.0.2h.tar
```

Then compile and install OpenSSL to ``/usr/local/ssl/macos-x86_64``:

```
./Configure darwin64-x86_64-cc shared enable-ec_nistp_64_gcc_128 no-ssl2 no-ssl3 no-comp --openssldir=/usr/local/ssl/macos-x86_64
make depend
sudo make install
```

Next we need to create symbolic links for the OpenSSL binaries and libraries in the ``/usr/local`` directory, or the 
.NET Core tools won't find them.

```
sudo ln -s /usr/local/ssl/macos-x86_64/bin/openssl /usr/local/bin/openssl
sudo ln -s /usr/local/ssl/macos-x86_64/lib/libssl.1.0.0.dylib /usr/local/lib/libssl.1.0.0.dylib
sudo ln -s /usr/local/ssl/macos-x86_64/lib/libcrypto.1.0.0.dylib /usr/local/lib/libcrypto.1.0.0.dylib
```

And that's it.

You can now start with .NET Core.

```
mkdir DotNetCoreSample
cd DotNetCoreSample
dotnet new
```