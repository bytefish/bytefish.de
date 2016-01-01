title: Using a Tokenizer in TinyCsvParser
date: 2016-01-01 10:14
tags: c#, csv
category: c#, tinycsvparser
slug: tinycsvparser_tokenizer
author: Philipp Wagner
summary: This article shows how to implement and use a Tokenizer in TinyCsvParser.

[MIT License]: https://opensource.org/licenses/MIT
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser

I have been working on [TinyCsvParser] lately, which is a library to parse CSV data in an easy and fun 
way, while offering high performance (probably the fastest CSV reader around) and a very clean API.

## Why a CSV Parser library? ##

It may be confusing or even amusing to readers of this blog, that I spend so much time writing a 
library for CSV parsing. But I have been tearing my hair apart at work, when trying to grok CSV 
parsing code.

CSV parsing can lead to code monsters in real life, that will eat your precious lifetime and pose 
a threat to your application. After all, you are importing data into your system. Your data must 
be valid or you (or your team) are going to have fun correcting the data manually, which is expensive 
and frustrating.

And believe me. An interface for reading CSV data is going to become important in an application, 
especially when a team is short on time. It is just some CSV data, right? How complicated can it 
be? Oh, well. 

If you have ever felt the same pain as I did, you probably know, that CSV files are abused for a lot 
of things in reality. They can be complicated beasts and sometimes even contain malformed data. 
Often enough you don't have any control of the format. No blaming here, even your client may have no 
control over the CSV data format. 

Oh, what about File Encodings? Oh, what about date formats? Oh, what about culture-specific nuber 
formats? Oh Oh Oh...

A consistent approach for parsing CSV data in your application is important or you will get 
into severe problems maintaining an application. Let's agree, that enough hair was torn apart by 
developers reading custom hand-rolled CSV parsing code.

TinyCsvParser will help you to provide a consistent way for reading your CSV data. It is highly 
extendable to provide maximum flexibility, while maintaining a high performance. I hope it makes 
your life easier and brings you some joy, when working with CSV files.

## Updates ##

[TinyCsvParser] now contains a proper documentation and it is extensively unit tested. The unit tests 
uncovered some bugs lingering in the library and the code coverage is approaching 100%. I cannot stress 
enough how important tests are in modern software development.

## Developing a Feature: Tokenizer ##

### Problem Description ###

I was approached with an interesting problem lately. A users CSV file contained lines, where the column 
delimiter was also present in the actual data. This lead to problems with [TinyCsvParser] 1.0, so a new 
feature had to be implemented: a ``Tokenizer``.

Imagine we get CSV data, that looks like this:

```
FirstNameLastName;BirthDate
"Philipp,Wagner",1986/05/12
""Max,Mustermann",2014/01/01
```

A simple ``string.Split`` with a comma as column delimiter can lead to wrong data. This is definitely 
a realistic scenario, so thanks for reporting and let's see how the problem can be solved.

### Approaching the Problem ###

First of all we have to accept the fact, that there is no possible standard how CSV files are described. 
There is no schema, so every file you get may look different. You probably agree, that this rules out a 
single strategy to tokenize a given file.

Once you have accepted this fact it becomes obvious, that a user has to be enabled to apply different 
strategies for tokenizing a line. 

### Implementing the Feature ###

So a tokenizer is responsible for splitting your CSV data into your column data. 

This can be expressed by defining an interface ``ITokenizer``.

```csharp
namespace TinyCsvParser.Tokenizer
{
    public interface ITokenizer
    {
        string[] Tokenize(string input);
    }
}
```

#### StringSplitTokenizer ####

For a simple CSV file it is sufficient to do a ``string.Split``. So we can implement a simple 
``StringSplitTokenizer``, that tokenizes the file using a given column delimiter.

```csharp
namespace TinyCsvParser.Tokenizer
{
    public class StringSplitTokenizer : ITokenizer
    {
        public readonly char[] FieldsSeparator;
        public readonly bool TrimLine;

        public StringSplitTokenizer(char[] fieldsSeparator, bool trimLine)
        {
            FieldsSeparator = fieldsSeparator;
            TrimLine = trimLine;
        }

        public string[] Tokenize(string input)
        {
            if(TrimLine) 
            {
                return input.Trim().Split(FieldsSeparator);
            }
            return input.Split(FieldsSeparator);
        }

        public override string ToString()
        {
            return string.Format("StringSplitTokenizer (FieldsSeparator = {0}, TrimLine = {1})", FieldsSeparator, TrimLine);
        }
    }
}
```

#### RegularExpressionTokenizer ####

For some files it is not sufficient to do a ``string.Split``. Some files may contain the column delimiter 
in a columns data, other files may have even more exotic requirements. One way to split data is to use 
a regular expression. 

There may be more, than only one regular expression, so a base class ``RegularExpressionTokenizer`` is useful.

```csharp
using System.Linq;
using System.Text.RegularExpressions;

namespace TinyCsvParser.Tokenizer.RegularExpressions
{
    public abstract class RegularExpressionTokenizer : ITokenizer
    {
        public abstract Regex Regexp { get; }
        
        public string[] Tokenize(string input)
        {
            return Regexp.Matches(input)
                .Cast<Match>()
                .Select(x => x.Value)
                .ToArray();
        }

        public override string ToString()
        {
            return string.Format("Regexp = {0}", Regexp);
        }
    }
}
```

#### QuotedStringTokenizer ####

And finally the problem of parsing quoted data can be solved by implementing a ``RegularExpressionTokenizer``. 
The ``QuotedStringTokenizer`` defines a regular expression, that prevents quoted data to be split.

```csharp
using System.Text.RegularExpressions;

namespace TinyCsvParser.Tokenizer.RegularExpressions
{
    public class QuotedStringTokenizer : RegularExpressionTokenizer
    {
        private Regex regexp;

        public override Regex Regexp
        {
            get { return regexp; }
        }

        public QuotedStringTokenizer(char columnDelimiter)
            : base()
        {
            BuildCompiledRegexp(columnDelimiter);
        }

        private void BuildCompiledRegexp(char columnDelimiter)
        {
            regexp = new Regex(GetPreparedRegexp(columnDelimiter), RegexOptions.Compiled);
        }

        private string GetPreparedRegexp(char columnDelimiter)
        {
            return string.Format("((?<=\")[^\"]*(?=\"({0}|$)+)|(?<={0}|^)[^{0}\"]*(?={0}|$))", columnDelimiter);
        }

        public override string ToString()
        {
            return string.Format("QuotedStringTokenizer({0})", base.ToString());
        }
    }
}
```

### Using a Tokenizer ###

Now imagine you are getting persons data with the following data:

```
FirstNameLastName;BirthDate
"Philipp,Wagner",1986/05/12
""Max,Mustermann",2014/01/01
```

The first name and the last name are using the same character as the column delimiter. So the file can't 
be tokenized by only splitting at the column delimiter. The ``QuotedStringTokenizer`` is needed, and it 
will be set in the ``CsvParserOptions``.

So the code looks like this.

```csharp
using NUnit.Framework;
using System;
using System.Linq;
using System.Text;
using TinyCsvParser.Mapping;
using TinyCsvParser.Tokenizer.RegularExpressions;

namespace TinyCsvParser.Test.Tokenizer
{
    [TestFixture]
    public class TokenizerExampleTest
    {
        private class Person
        {
            public string FirstNameWithLastName { get; set; }
            public DateTime BirthDate { get; set; }
        }

        private class CsvPersonMapping : CsvMapping<Person>
        {
            public CsvPersonMapping()
            {
                MapProperty(0, x => x.FirstNameWithLastName);
                MapProperty(1, x => x.BirthDate);
            }
        }

        [Test]
        public void QuotedStringTokenizerExampleTest()
        {
            CsvParserOptions csvParserOptions = new CsvParserOptions(true, new QuotedStringTokenizer(','));
            CsvReaderOptions csvReaderOptions = new CsvReaderOptions(new[] { Environment.NewLine });
            CsvPersonMapping csvMapper = new CsvPersonMapping();
            CsvParser<Person> csvParser = new CsvParser<Person>(csvParserOptions, csvMapper);

            var stringBuilder = new StringBuilder()
                .AppendLine("FirstNameLastName;BirthDate")
                .AppendLine("\"Philipp,Wagner\",1986/05/12")
                .AppendLine("\"Max,Mustermann\",2014/01/01");

            var result = csvParser
                .ReadFromString(csvReaderOptions, stringBuilder.ToString())
                .ToList();

            // Make sure we got 2 results:
            Assert.AreEqual(2, result.Count);

            // And all of them have been parsed correctly:
            Assert.IsTrue(result.All(x => x.IsValid));

            // Now check the values:
            Assert.AreEqual("Philipp,Wagner", result[0].Result.FirstNameWithLastName);

            Assert.AreEqual(1986, result[0].Result.BirthDate.Year);
            Assert.AreEqual(5, result[0].Result.BirthDate.Month);
            Assert.AreEqual(12, result[0].Result.BirthDate.Day);

            Assert.AreEqual("Max,Mustermann", result[1].Result.FirstNameWithLastName);

            Assert.AreEqual(2014, result[1].Result.BirthDate.Year);
            Assert.AreEqual(1, result[1].Result.BirthDate.Month);
            Assert.AreEqual(1, result[1].Result.BirthDate.Day);
        }
    }
}
```


## Conclusion ##

I hope you had fun reading this article. Working with a ``Tokenizer`` is a great way to split data into 
its column values. You have learnt how to implement and use your own ``Tokenizer``, if you are given a 
file with a very weird formatting.