title: Migrating a library to .NET Core
date: 2016-07-24 9:53
tags: csharp, dotnetcore
category: csharp
slug: migrating_a_library_to_dotnetcore
author: Philipp Wagner
summary: This article shows how to migrate an existing .NET library to .NET Core.

Microsoft released .NET Core 1.0 and I want to port some of my .NET libraries to [.NET Core]. This article describes how to 
migrate the existing library [TinyCsvParser] to [.NET Core] and shows the changes necessary to make it work.

## Visual Studio 2015 RC3, .NET Core Tools ##

The best way to start with .NET Core in Windows is to use [Visual Studio] and the addition [.NET Core 1.0 Tools]:

* [Visual Studio 2015 Update 3*]
* [.NET Core 1.0 for Visual Studio]

I had the problem, that the Setup [.NET Core 1.0 for Visual Studio] due to an errorneous Visual Studio version check. 

You can skip the version check by running the Setup with the ``SKIP_VSU_CHECK`` parameter:

```
DotNetCore.1.0.0-VS2015Tools.Preview2.exe SKIP_VSU_CHECK=1
```

## The .xproj / .project.json Situation ##

One of the key goals of [.NET Core] was to build a platform, which allows to develop applications with Windows, Mac and Linux. 
MSBuild wasn't Open Source at the time and so Microsoft has developed a new build system. The current build system is based 
.xproj / project.json files.

So the first step for migrating to the current [.NET Core] version is to migrate the .csproj projects into the new format. I have 
decided to have projects for both .csproj / MSBuild and .xproj / project.json, so you can still use Visual Studio 2013 and your 
existing MSBuild environment to build the library. 

Please keep in mind, that Microsoft has recently decided to step back from .xproj / project.json and intends to move back to a 
.csproj / MSBuild build system (see the Microsoft announcement on [Changes to Project.json]). I really, really hope, that some 
of the very nice features of project.json survive the change.

### global.json ###

The [global.json] file specifies what folders the build system should search, when resolving dependencies. 

[TinyCsvParser] currently consists of two projects named ``TinyCsvParser``, which is the library and ``TinyCsvParser.Test``, 
which is is the test project. Both the projects need to be defined in the [global.json] file, so the [.NET Core] Tooling can 
correctly resolve both.

The final [global.json] looks like this:

```json
{
    "projects": [ "TinyCsvParser", "TinyCsvParser.Test" ]
}
```

### project.json ###

The projects in [.NET Core] are specified in a [project.json] file. The [project.json] file specifies how the project should 
be built, it includes the dependencies and specifies the frameworks it works with. 

## Migrating the TinyCsvParser Project ##

### project.json ###

The [project.json] build system has the nice feature, that I can directly build a package.

In the ``frameworks`` section of the file the target .NET frameworks are specified. At the moment I target 
.NET 4.5 and .NET Core 1.0. See the [.NET Platform Standard] for most recent informations on the .NET platform 
and informations like Target Framework monikers.

[.NET Core] is intended to be a very modular system, so we also need to include dependencies on the [NETStandard.Library] and 
[System.Linq.Parallel], which will be resolved from NuGet when building the project. 

In the ``scripts`` section, we can define various pre-build and post-build events. In the ``postCompile`` event I have instructed 
the build system to pack a NuGet Packages and store it in the current Configuration folder (e.g. Debug / Release). This is a great 
feature and makes it very simple to distribute the library.

```json
{
  "version": "1.4.0",
  "title": "TinyCsvParser",
  "description": "An easy to use and high-performance library for CSV parsing.",
  "copyright": "Copyright 2016 Philipp Wagner",
  "authors": [
    "Philipp Wagner"
  ],

  "packOptions": {
    "owners": [
      "Philipp Wagner"
    ],
    "authors": [
      "Philipp Wagner"
    ],
    "tags": [ "csv", "csv parser" ],
    "requireLicenseAcceptance": false,
    "projectUrl": "https://github.com/bytefish/TinyCsvParser",
    "summary": "An easy to use and high-performance library for CSV parsing.",
    "licenseUrl": "https://opensource.org/licenses/MIT",
    "repository": {
      "type": "git",
      "url": "git://github.com/bytefish/TinyCsvParser"
    }
  },


  "frameworks": {
    "net45": {},
    "netstandard1.6": {
      "dependencies": {
        "NETStandard.Library": "1.6.0",
        "System.Linq.Parallel": "4.0.0"
      },
      "imports": "dnxcore50"
    }
  },

  "scripts": {
    "postcompile": [
      "dotnet pack --no-build --configuration %compile:Configuration%"
    ]
  }
}
```

### Conditional Compilation for the Reflection API ###

There were slight changes to the Reflection API in [.NET Core]. An additional call to the ``GetTypeInfo`` method is necessary 
to access the property informations of a type. I want the library to have a single code base, so I have used a preprocessor 
directive to allow conditional compilation. 

I target the .NET Standard 1.6 framework with the library, so the ``#if`` directive looks like this:

```csharp
public static bool IsEnum(Type type)
{
#if NETSTANDARD1_6
    return typeof(Enum).GetTypeInfo().IsAssignableFrom(type);
#else 
    return typeof(Enum).IsAssignableFrom(type);
#endif
}
```

## Migrating the TinyCsvParser.Test Project ##

### project.json ###

The [NUnit] Folks have done an amazing job and provide full support for [.NET Core 1.0]. In the [project.json] for the project 
we simply need to set the ``testRunner`` to ``nunit`` and include the necessary [NUnit] dependencies. We reference the 
``TinyCsvParser`` as a project dependency.

```json
{
  "version": "0.0.0",

  "testRunner": "nunit",
  "dependencies": {
    "dotnet-test-nunit": "3.4.0-beta-1",
    "NUnit": "3.4.0",
    "TinyCsvParser": {
      "target": "project"
    }
  },
  "frameworks": {
    "netcoreapp1.0": {
      "imports": [
        "netcoreapp1.0",
        "portable-net45+win8"
      ],
      "dependencies": {
        "Microsoft.NETCore.App": {
          "version": "1.0.0",
          "type": "platform"
        }
      },
      "buildOptions": {
        "define": [ "NETCOREAPP" ]
      }
    }
  }
}
```

### Conditional Compilation ###

One of the Unit Tests used the ``AppDomain`` to obtain the current working directory, and write a file to disk. The ``AppDomain`` is 
not available in [.NET Core] for various valid reasons, but it can be replaced with the ``AppContext``. So for the [.NET Core] build 
the ``buildOptions`` have been used to define a preprocessor symbol for conditional compilation.

The ``NETCOREAPP`` symbol can now be used in the unit test to obtain the current base directory either from the ``AppContext`` or the 
``AppDomain``, depending on the target framework.

```csharp
#if NETCOREAPP
            var basePath = AppContext.BaseDirectory;
#else 
            var basePath = AppDomain.CurrentDomain.BaseDirectory;
#endif
```

## Conclusion ##

And that's it! 

The library is now built for .NET 45 and .NET Core, and the NuGet package is automatically created in a post-build event. Only minimal 
changes had to be made to build the library against the [.NET Core] framework. All unit tests went green on first run, and even the 
NUnit Test Runner in Visual Studio worked without problems.

So migrating an existing project to .NET Core was really easy. Microsoft is currently making hard changes to the .NET ecosystem. And to 
me it's natural, that a lot of things are still in flux. It was fun to work the [project.json] based build system and the [.NET Core] 
integration in [Visual Studio] is great.

[.NET Platform Standard]: https://github.com/dotnet/corefx/blob/master/Documentation/architecture/net-platform-standard.md
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[Changes to Project.json]: https://blogs.msdn.microsoft.com/dotnet/2016/05/23/changes-to-project-json/
[project.json]: https://docs.microsoft.com/en-us/dotnet/articles/core/tools/project-json
[global.json]: https://docs.microsoft.com/en-us/dotnet/articles/core/tools/global-json
[NUnit]: http://www.nunit.org
[Visual Studio]: https://www.visualstudio.com/news/releasenotes/vs2015-update3-vs
[Visual Studio 2015 Update 3*]: https://www.visualstudio.com/news/releasenotes/vs2015-update3-vs
[.NET Core 1.0 for Visual Studio]: https://go.microsoft.com/fwlink/?LinkId=817245
[.NET Core 1.0]: https://go.microsoft.com/fwlink/?LinkId=817245
[.NET Core]: https://go.microsoft.com/fwlink/?LinkId=817245