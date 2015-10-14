title: Benchmarking TinyCsvParser
date: 2015-09-19 10:54
tags: c#, csv, tinycsvparser
category: c#
slug: tinycsvparser_benchmark
author: Philipp Wagner
summary: This article benchmarks TinyCsvParser on a large file.

[FluentValidation]: https://github.com/JeremySkinner/FluentValidation
[CsvHelper]: https://github.com/JoshClose/CsvHelper
[FileHelpers]: http://www.filehelpers.net
[TinyCsvParser]: https://github.com/bytefish/TinyCsvParser
[NUnit]: http://www.nunit.org
[MIT License]: https://opensource.org/licenses/MIT

[TinyCsvParser] is an easy to use, easy to extend and high-performing library for parsing CSV files.

In my last post I have described how to use [TinyCsvParser] and [FluentValidation] on a tiny dataset. In 
real life you often end up with huge CSV files in the order of hundred Megabytes or even Gigabytes.

In this post I want to show how you to parse large CSV files with [TinyCsvParser] and process them in 
parallel. You will see how fast it is compared to other popular libraries for CSV parsing. This post is 
not meant to discredit the [FileHelpers] or [CsvHelper] projects. Both are great open source projects 
and they provide much more functionality than [TinyCsvParser].

## Dataset ##

In this post we are parsing a real life dataset. It's the local weather data in March 2015 gathered by 
all weather stations in the USA. You can obtain the data  ``QCLCD201503.zip`` from:
 
* [http://www.ncdc.noaa.gov/orders/qclcd](http://www.ncdc.noaa.gov/orders/qclcd)

The File size is ``557 MB`` and it has ``4,496,262`` lines.

## Benchmark Results ##

Without further explanation, here are the Benchmark results for parsing the dataset.

```
[TinyCsvParser (DegreeOfParallelism = 4, KeepOrder = True)] Elapsed Time = 00:00:10.48
[CsvHelper] Elapsed Time = 00:00:32.60
[FileHelpers] Crash
```

You can see, that [TinyCsvParser] is able to parse the file in ``10.5`` seconds only. Even if you don't 
process the data in parallel (``DegreeOfParallelism = 1``) it is still faster, than [CsvHelper]. The 
[FileHelpers] implementation crashed with an OutOfMemory Exception.

Here are the full benchmark results of [TinyCsvParser]. You can see, that increasing the number of threads 
helps when processing the data. Keeping the order doesn't have impact on the processing time, but it may 
lead to a much higher memory consumption. This may be a subject for a future article.

```
[TinyCsvParser (DegreeOfParallelism = 4, KeepOrder = True)] Elapsed Time = 00:00:10.48
[TinyCsvParser (DegreeOfParallelism = 3, KeepOrder = True)] Elapsed Time = 00:00:10.65
[TinyCsvParser (DegreeOfParallelism = 2, KeepOrder = True)] Elapsed Time = 00:00:12.26
[TinyCsvParser (DegreeOfParallelism = 1, KeepOrder = True)] Elapsed Time = 00:00:17.04
[TinyCsvParser (DegreeOfParallelism = 4, KeepOrder = False)] Elapsed Time = 00:00:10.50
[TinyCsvParser (DegreeOfParallelism = 3, KeepOrder = False)] Elapsed Time = 00:00:10.31
[TinyCsvParser (DegreeOfParallelism = 2, KeepOrder = False)] Elapsed Time = 00:00:11.71
[TinyCsvParser (DegreeOfParallelism = 1, KeepOrder = False)] Elapsed Time = 00:00:16.70
```

## Benchmark Code ##

The elapsed time of the import can be easily measured by using the ``System.Diagnostics.Stopwatch``.

```csharp
private void MeasureElapsedTime(string description, Action action)
{
    // Get the elapsed time as a TimeSpan value.
    TimeSpan ts = MeasureElapsedTime(action);

    // Format and display the TimeSpan value.
    string elapsedTime = String.Format("{0:00}:{1:00}:{2:00}.{3:00}",
        ts.Hours, ts.Minutes, ts.Seconds,
        ts.Milliseconds / 10);

    Console.WriteLine("[{0}] Elapsed Time = {1}", description, elapsedTime);
}

private TimeSpan MeasureElapsedTime(Action action)
{
    Stopwatch stopWatch = new Stopwatch();
    
    stopWatch.Start();
    action();
    stopWatch.Stop();

    return stopWatch.Elapsed;
}
```

### TinyCsvParser ###

[TinyCsvParser] can be installed with NuGet:

```
Install-Package TinyCsvParser
```

#### Code ####

```csharp
public class LocalWeatherData
{
    public string WBAN { get; set; }
    public DateTime Date { get; set; }
    public string SkyCondition { get; set; }
}

public class LocalWeatherDataMapper : CsvMapping<LocalWeatherData>
{
    public LocalWeatherDataMapper()
    {
        MapProperty(0, x => x.WBAN);
        MapProperty(1, x => x.Date).WithCustomConverter(new DateTimeConverter("yyyyMMdd"));
        MapProperty(4, x => x.SkyCondition);
    }
}

[Test]
public void TinyCsvParserBenchmark()
{
    bool[] keepOrder = new bool[] { true, false };
    int[] degreeOfParallelismList = new[] { 4, 3, 2, 1 };

    foreach (var order in keepOrder)
    {
        foreach (var degreeOfParallelism in degreeOfParallelismList)
        {
            CsvParserOptions csvParserOptions = new CsvParserOptions(true, new[] { ',' }, degreeOfParallelism, order);
            CsvReaderOptions csvReaderOptions = new CsvReaderOptions(new[] { Environment.NewLine });
            LocalWeatherDataMapper csvMapper = new LocalWeatherDataMapper();
            CsvParser<LocalWeatherData> csvParser = new CsvParser<LocalWeatherData>(csvParserOptions, csvMapper);

            MeasureElapsedTime(string.Format("TinyCsvParser (DegreeOfParallelism = {0}, KeepOrder = {1})", degreeOfParallelism, order),
                () =>
                {
                    var a = csvParser
                        .ReadFromFile(@"C:\Users\philipp\Downloads\csv\201503hourly.txt", Encoding.ASCII)
                        .ToList();
                });
        }
    }
}
```

### CsvHelper ###

[CsvHelper] can be installed with NuGet:

```
Install-Package CsvHelper
```

#### Code ####

```csharp
public class CustomDateConverter : CsvHelper.TypeConversion.DefaultTypeConverter
{
    private const string CustomDateFormat = @"yyyyMMdd";

    public override bool CanConvertFrom(Type type)
    {
        return typeof(String) == type;
    }

    public override bool CanConvertTo(Type type)
    {
        return typeof(DateTime) == type;
    }

    public override object ConvertFromString(CsvHelper.TypeConversion.TypeConverterOptions options, string text)
    {
        DateTime newDate = default(DateTime);

        try
        {
            newDate = DateTime.ParseExact(text, CustomDateFormat, CultureInfo.GetCultureInfo("en-US"));
        }
        catch (Exception ex)
        {
            Debug.WriteLine(String.Format(@"Error parsing date '{0}': {1}", text, ex.Message));
        }

        return newDate;
    }
}

public sealed class CsvHelperMapping : CsvHelper.Configuration.CsvClassMap<LocalWeatherData>
{
    public CsvHelperMapping()
    {
        Map(m => m.WBAN).Index(0);
        Map(m => m.Date).Index(1).TypeConverter<CustomDateConverter>();;
        Map(m => m.SkyCondition).Index(4);
    }
}

[Test]
public void CsvHelperBenchmark()
{
    MeasureElapsedTime("CsvHelper", () =>
       {
           using (TextReader reader = File.OpenText(@"C:\Users\philipp\Downloads\csv\201503hourly.txt"))
           {
               var csv = new CsvHelper.CsvReader(reader);
               csv.Configuration.RegisterClassMap<CsvHelperMapping>();
               csv.Configuration.Delimiter = ",";
               csv.Configuration.HasHeaderRecord = true;

               var usersFromCsv = csv.GetRecords<LocalWeatherData>().ToList();
           }
       });
}
```


### FileHelpers ###

[FileHelpers] can be installed with NuGet:

```
Install-Package FileHelpers
```

#### Code ####

Sadly I was not able to figure out, how to select only the three columns in the mapping. Probably I am 
mistaken here and you should feel free to comment below, if you have a different solution to parse the 
file without writing the whole amount of columns.

```csharp
[FileHelpers.IgnoreFirst(1)] 
[FileHelpers.DelimitedRecord(",")]
public class LocalWeatherDataFileHelper
{
    public string WBAN;

    [FileHelpers.FieldConverter(FileHelpers.ConverterKind.Date, "yyyyMMdd")]
    public DateTime Date;

    private string dummyFieldTime;

    private string dummyFieldStationType;

    public string SkyCondition;

    private string[] mDummyField;
}

[Test]
public void FileHelperBenchmark()
{
    var engine = new FileHelpers.FileHelperEngine<LocalWeatherDataFileHelper>();
    MeasureElapsedTime("FileHelper", () =>
    {
        var result = engine.ReadFile(@"C:\Users\philipp\Downloads\csv\201503hourly.txt", 900000);
    });
}
```

#### Additional Notes ####

I was not able to read the entire file, because [FileHelpers] apparently does not provide an API for 
streaming the result. So if you try to read the entire dataset with its ``FileHelperEngine<T>.ReadFile`` 
method, you are going to run out of memory (System.OutOfMemoryException). 

## Summary ##

[TinyCsvParser] is a really fast CSV parser and suited well for processing very large datasets.

Feel free to fork and contribute to the project!