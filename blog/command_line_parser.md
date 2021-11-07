title: Parsing Command Line Arguments in .NET
date: 2021-10-17 21:03
tags: dotnet, architecture
category: dotnet
slug: command_line_parser
author: Philipp Wagner
summary: On Building a simple .NET CLI Parser

I recently had to parse the command line arguments of the ``dotnet`` executable to read some option 
values. I think something like this should come out of the box in the .NET ecosystem. And apparently 
there has been a lot of work on it:

* [https://github.com/dotnet/command-line-api](https://github.com/dotnet/command-line-api)

But what is actually used in the .NET ecosystem? It's custom Command Line Parsers all along the way: 

* [https://github.com/search?q=org%3Adotnet+CommandLineParser&type=code](https://github.com/search?q=org%3Adotnet+CommandLineParser&type=code)

No blaming here. It's different projects, different requirements and there is no one-size-fits-all for a CLI probably.

But as an application developer it's often worth to take an additional dependency like [CommandLineParser], if you 
are writing your own CLI application. Because what often starts with a simple CLI quickly grows into Commands, 
Sub-Commands, Arguments, Options, ... something you don't want to implement yourself.

But for something as simple as getting some options and their values? There is way too much ceremony involved 
in [CommandLineParser] and alike. No I don't want your Fluent APIs, no I don't want to create an option class 
and use your attributes.

Let's build something simple.

## Implementation ##

An Option can either be given by a Long Name (``--something``), a Short Name (``-s``) or it's a plain symbol.

```csharp
public enum OptionTypeEnum
{
    /// <summary>
    /// A Long Name for an Option, e.g. --opt.
    /// </summary>
    LongName,

    /// <summary>
    /// A Short Name for an Option, e.g. -o.
    /// </summary>
    ShortName,

    /// <summary>
    /// A Symbol, that is neither a switch, nor an argument.
    /// </summary>
    Symbol
}
```

As for the ``ComandLineOption``, it's just the Name, Value and Type.

```csharp
/// <summary>
/// An option passed by a Command Line application.
/// </summary>
public class CommandLineOption
{
    /// <summary>
    /// The Name of the Option.
    /// </summary>
    public string Name { get; set; }

    /// <summary>
    /// The Value associated with this Option.
    /// </summary>
    public string Value { get; set; }

    /// <summary>
    /// The Type of this Option.
    /// </summary>
    public OptionTypeEnum OptionType { get; set; }
}
```

And the ``CommandLineParser`` now simply iterates over the arguments and parses them.

```csharp
/// <summary>
/// A simple parser to parse Command Line Arguments.
/// </summary>
public static class CommandLineParser
{
    public static IList<CommandLineOption> ParseOptions(string[] arguments)
    {
        // Holds the Results:
        var results = new List<CommandLineOption>();

        CommandLineOption lastOption = null;

        foreach (string argument in arguments)
        {
            // What should we do here? Go to the next one:
            if (string.IsNullOrWhiteSpace(argument))
            {
                continue;
            }

            // We have found a Long-Name option:
            if (argument.StartsWith("--", StringComparison.Ordinal))
            {
                // The previous argument was an option, too. Let's give it back:
                if (lastOption != null)
                {
                    results.Add(lastOption);
                }

                lastOption = new CommandLineOption
                {
                    OptionType = OptionTypeEnum.LongName,
                    Name = argument.Substring(2)
                };
            }
            // We have found a Short-Name option:
            else if (argument.StartsWith("-", StringComparison.Ordinal))
            {
                // The previous argument was an option, too. Let's give it back:
                if (lastOption != null)
                {
                    results.Add(lastOption);
                }

                lastOption = new CommandLineOption
                {
                    OptionType = OptionTypeEnum.ShortName,
                    Name = argument.Substring(1)
                };
            }
            // We have found a symbol:
            else if (lastOption == null)
            {
                results.Add(new CommandLineOption
                {
                    OptionType = OptionTypeEnum.Symbol,
                    Name = argument
                });
            }
            // And finally this is a value:
            else
            {
                // Set the Value and return this option:
                lastOption.Value = argument;

                results.Add(lastOption);

                // And reset it, because we do not expect multiple parameters:
                lastOption = null;
            }
        }

        if(lastOption != null)
        {
            results.Add(lastOption);
        }

        return results;
    }
}
```

And that's it!

### Tests ###

And here are the unit tests, that show how to use the ``CommandLineParser``.

```csharp
[TestFixture]
public class CommandLineParserTests
{
    [Test]
    public void ParseValidCommandLineTest()
    {
        // Parse: --noargs --scan 1 --connectionString "val"
        var result = CommandLineParser
            .ParseOptions(new[] { "--noargs", "--scan", "1", "--connectionString", "\"val\"" })
            .ToArray();

        Assert.AreEqual(3, result.Length);

        Assert.AreEqual("noargs", result[0].Name);
        Assert.AreEqual(OptionTypeEnum.LongName, result[0].OptionType);
        Assert.AreEqual(null, result[0].Value);

        Assert.AreEqual("scan", result[1].Name);
        Assert.AreEqual(OptionTypeEnum.LongName, result[1].OptionType);
        Assert.AreEqual("1", result[1].Value);

        Assert.AreEqual("connectionString", result[2].Name);
        Assert.AreEqual(OptionTypeEnum.LongName, result[2].OptionType);
        Assert.AreEqual("\"val\"", result[2].Value);
    }

    [Test]
    public void ParseValidCommandLineWithLongShortAndSymbolTest()
    {
        // Parse: sym --noargs -s 1 sym -empty
        var result = CommandLineParser
            .ParseOptions(new[] { "sym", "--noargs", "-s", "1", "sym", "-empty" })
            .ToArray();

        Assert.AreEqual(5, result.Length);

        Assert.AreEqual("sym", result[0].Name);
        Assert.AreEqual(OptionTypeEnum.Symbol, result[0].OptionType);
        Assert.AreEqual(null, result[0].Value);

        Assert.AreEqual("noargs", result[1].Name);
        Assert.AreEqual(OptionTypeEnum.LongName, result[1].OptionType);
        Assert.AreEqual(null, result[1].Value);

        Assert.AreEqual("s", result[2].Name);
        Assert.AreEqual(OptionTypeEnum.ShortName, result[2].OptionType);
        Assert.AreEqual("1", result[2].Value);

        Assert.AreEqual("sym", result[3].Name);
        Assert.AreEqual(OptionTypeEnum.Symbol, result[3].OptionType);
        Assert.AreEqual(null, result[3].Value);

        Assert.AreEqual("empty", result[4].Name);
        Assert.AreEqual(OptionTypeEnum.ShortName, result[4].OptionType);
        Assert.AreEqual(null, result[4].Value);
    }

    [Test]
    public void ParseCommandLineDotNetCoreExecutableTest()
    {
        // Parse: dotnet ef migrations script --output all_scripts.sql --idempotent
        var result = CommandLineParser
            .ParseOptions(new[] { "dotnet", "ef", "migrations", "script", "--output", "all_scripts.sql", "--idempotent" })
            .ToArray();

        Assert.AreEqual(6, result.Length);

        Assert.AreEqual("dotnet", result[0].Name);
        Assert.AreEqual(OptionTypeEnum.Symbol, result[0].OptionType);

        Assert.AreEqual("ef", result[1].Name);
        Assert.AreEqual(OptionTypeEnum.Symbol, result[1].OptionType);

        Assert.AreEqual("migrations", result[2].Name);
        Assert.AreEqual(OptionTypeEnum.Symbol, result[2].OptionType);

        Assert.AreEqual("script", result[3].Name);
        Assert.AreEqual(OptionTypeEnum.Symbol, result[3].OptionType);

        Assert.AreEqual("output", result[4].Name);
        Assert.AreEqual(OptionTypeEnum.LongName, result[4].OptionType);
        Assert.AreEqual("all_scripts.sql", result[4].Value);

        Assert.AreEqual("idempotent", result[5].Name);
        Assert.AreEqual(OptionTypeEnum.LongName, result[5].OptionType);
        Assert.AreEqual(null, result[5].Value);
    }
}
```

## Conclusion ##

And that's a simple Options Parser, that only covers the 10% CLI functionality I need.

I guess sharing is better, than to silo the code. Maybe it's useful for you?

[CommandLineParser]: https://github.com/commandlineparser/commandline