title: Using TinyCsvParser and FluentValidation
date: 2015-09-15 22:12
tags: c#, csv, fluent validation
category: c#
slug: fluent_validation
author: Philipp Wagner
summary: This article describes how to validate data with TinyCsvParser and FluentValidation.

[FluentValidation]: https://github.com/JeremySkinner/FluentValidation
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[NUnit]: http://www.nunit.org
[MIT License]: https://opensource.org/licenses/MIT

In my last post I have described [TinyCsvParser], which is an easy to extend, easy to use library for 
parsing CSV data. This post shows how to perform an additional validation on the CSV parse results with 
[FluentValidation].

[FluentValidation] is "... a small validation library for .NET that uses a fluent interface and lambda 
expressions for building validation rules". It's a great library, because it is open source, easy to 
extend and easy to use.

I think both libraries are fun to use and they are easy to combine.

## Example Scenario ##

Imagine a client sends us a CSV file with peoples data, that we need to import into our system. We don't 
want to have invalid data in our application, because it could lead to unexpected behavior and unexpected 
crashes. 

Real life data is never perfect. So what we get might look like this.

```
FirstName;LastName;BirthDate;EMailAddress
FirstNameA;LastNameA;1986/05/12;bytefish@gmx.de
FirstNameB;LastNameB;1988/01/01;Max@Mustermann.de
FirstNameC;LastNameC;2076/01/01;unknown@identity.de
FirstNameD;LastNameD;1912/01/01;invalid@mailaddress
;LastNameE;1900/01/01;unknown@identity.de
```

There are obviously invalid records in the data. One record has a wrong mail address, someone is born in 
the future and someone doesn't have a first name. This isn't a problem for tiny datasets, which could be 
fixed manually, but it's a problem for larger files.

### Installing the Packages ###

Create a class library project and install [TinyCsvParser], [FluentValidation] and [NUnit].

```
Install-Package TinyCsvParser
Install-Package FluentValidation
Install-Package NUnit
```

### Domain Model ###

First of all we are defining the domain model in the application. Create a new class ``Person``, that 
holds the first name, last name, mail address and birth date.

```csharp
public class Person
{
    public string FirstName { get; set; }

    public string LastName { get; set; }

    public string MailAddress { get; set; }

    public DateTime BirthDate { get; set; }

    public override string ToString()
    {
        return string.Format("Person (FirstName = {0}, LastName = {1}, MailAddress = {2}, BirthDate = {3})",
            FirstName, LastName, MailAddress, BirthDate.ToShortDateString());
    }
}
```

### CSV Mapping ###

Then we need to define how the CSV file and the domain model match. This is done by using a ``CsvMapping`` of 
the [TinyCsvParser] library. See how easy it is to write the mapping.

```csharp
public class CsvPersonMapping : CsvMapping<Person>
{
    public CsvPersonMapping()
    {
        MapProperty(0, x => x.FirstName);
        MapProperty(1, x => x.LastName);
        MapProperty(2, x => x.BirthDate);
        MapProperty(3, x => x.MailAddress);
    }
}
```

### Enter FluentValidation ###

The basic idea of [FluentValidation] is to define rules on each property of your domain model. You can 
chain multiple rules by using its Fluent interface, which makes it easy to understand the validation 
rules.

Every Validator in [FluentValidation] is an ``AbstractValidator``. The ``AbstractValidator`` has a method 
``RuleFor``, which takes an expression (the property) and exposes a Fluent interface.

```csharp
public class PersonValidator : AbstractValidator<Person>
{
    public PersonValidator()
    {
        
        RuleFor(x => x.FirstName)
            .NotEmpty()
            .Length(1, 255);

        RuleFor(x => x.LastName)
            .NotEmpty()
            .Length(1, 255);

        RuleFor(x => x.MailAddress)
            .NotEmpty()
            .Length(1, 255)
            .EmailAddress();

        RuleFor(x => x.BirthDate)
            .NotEmpty()
            .GreaterThan(new DateTime(1870, 1, 1, 0, 0, 0, DateTimeKind.Utc));
    }
}
```

### Combining TinyCsvParser and FluentValidation ###

[ParallelQuery]: https://msdn.microsoft.com/en-us/library/system.linq.parallelquery(v=vs.100).aspx

Now we want to read the CSV data and filter the invalid results. The ``CsvParser`` in [TinyCsvParser] 
returns a [ParallelQuery], which can be used to perform additional processing on the data. 

For the problem at hand, we are first instantiating a new ``PersonValidator``. Then we construct the 
``CsvParser``, read the CSV data and validate the records with the ``PersonValidator``. The last step 
is to filter for the valid records only.

Problem solved in a few lines of code!

```csharp
[Test]
public void CsvParseAndValidateTest()
{
    // Create the CSV Data. You could also read from file with TinyCsvParser:
    var csvData = new StringBuilder()
        .AppendLine("FirstName;LastName;BirthDate;EMailAddress")
        .AppendLine("FirstNameA;LastNameA;1986/05/12;bytefish@gmx.de")
        .AppendLine("FirstNameB;LastNameB;1988/01/01;Max@Mustermann.de")
        .AppendLine("FirstNameC;LastNameC;2099/01/01;unknown@identity.de")
        .AppendLine("FirstNameD;LastNameD;1753/01/01;invalid@mailaddress")
        .AppendLine(";LastNameE;1900/01/01;unknown@identity.de")
        .ToString();

    // Instantiate the Validator:
    var validator = new PersonValidator();

    // Create the CsvParser:
    CsvParserOptions csvParserOptions = new CsvParserOptions(true, new[] { ';' });
    CsvReaderOptions csvReaderOptions = new CsvReaderOptions(new[] { Environment.NewLine });
    CsvPersonMapping csvMapper = new CsvPersonMapping();
    CsvParser<Person> csvParser = new CsvParser<Person>(csvParserOptions, csvMapper);
    
    // LINQ to rescue:
    var results = csvParser
        .ReadFromString(csvReaderOptions, csvData)
        .Where(x => x.IsValid)
        .Select(x => new { Entity = x.Result, ValidationResult = validator.Validate(x.Result) }) 
        .Where(x => x.ValidationResult.IsValid)
        .ToList();

    Assert.AreEqual(2, results.Count);

    Assert.AreEqual("LastNameA", results[0].Entity.LastName);
    Assert.AreEqual("LastNameB", results[1].Entity.LastName);
}
```