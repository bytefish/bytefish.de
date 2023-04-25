title: Using XML Maps for exporting XML Data from Excel
date: 2020-01-25 14:31
tags: excel, microsoft, dotnet, xml
category: excel
slug: excel_xml_export
author: Philipp Wagner
summary: Using XML Maps for exporting XML Data from Excel.

A large part of the world is built on Microsoft Excel and CSV files. And knowing how to 
extract and parse these formats probably saves you a lot of time and headaches.

In this post I will show how to use the XML Mapping functionality to export data from Microsoft Excel.

All code is available in a GitHub repository at:

* [https://github.com/bytefish/ExcelInteropSample](https://github.com/bytefish/ExcelInteropSample)

## Why XML Maps? ##

Now there are many, many ways to extract data from Microsoft Excel.

You could use an [OleDB Connection to query worksheets], populate a ``DataTable`` and then map to your 
data model. It sounds appealing, but chances are you'll find yourself knee-deep in [trying to stop Excel 
from guessing Data Types] and spend hours experimenting with Registry keys and researching connection 
strings.

You could export your data to CSV first and use a CSV Parser to read the data. But what about culture 
specific formats in Excel? What about encodings gone wrong? What about systems with non-default column 
delimiters? What about newlines in the header row? How can we make sure cells have the correct data 
type? Is anything validated? Oh dear.

I think XML Maps are a simple way to avoid most of this and it's something I seldomly see examples for.

Let's change this.

## Defining XML Maps ##

Imagine we have the following Excel Sheet with a list of people:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/excel_xml_export/sample_sheet.png">
        <img src="/static/images/blog/excel_xml_export/sample_sheet.png" alt="Sample Excel Sheet, that's going to be exported">
    </a>
</div>

Each person has a first name, a last name, a birth date and an income.

So I start by defining a XSD Schema describing what the exported XML data looks like. 

```xml
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">

  <!-- Define the Entity Type -->
  <xsd:complexType name="ExcelInteropDataRow">
    <xsd:sequence minOccurs="0">
      <xsd:element minOccurs="0" nillable="true" type="xsd:string" name="FirstName" form="unqualified"/>
      <xsd:element minOccurs="0" nillable="true" type="xsd:string" name="LastName" form="unqualified"/>
      <xsd:element minOccurs="0" nillable="true" type="xsd:date" name="BirthDate" form="unqualified"/>
      <xsd:element minOccurs="0" nillable="true" type="xsd:decimal" name="Income" form="unqualified"/>
    </xsd:sequence>
  </xsd:complexType>

  <!-- Model as a List of Entities -->
  <xsd:element nillable="true" name="ExcelInteropData">
    <xsd:complexType>
      <xsd:sequence minOccurs="0" maxOccurs="unbounded">
        <xsd:element name="Entities" type="ExcelInteropDataRow" form="unqualified" />
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>

</xsd:schema>
```

Next I open the **Developer** Tab in Excel, click **Source** to show the XML Mappings and click 
on *Add ...* to add the above Schema. You can see, that the Elements of the Schema appear in the 
XML Source pane.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/excel_xml_export/add_xml_schema.png">
        <img src="/static/images/blog/excel_xml_export/add_xml_schema.png" alt="Creating the XML Mapping for the Sheet data">
    </a>
</div>

Now select the *Entities* node and drag it on the *First Name* column. This will map all following 
columns to the XML element in the order given in the Schema. See why I wrote the Schema exactely 
like in the Excel Sheet?

And that's it for the Excel-side! Let's go to the C\# application.

## .NET ##

Having an XSD makes it easy to generate matching C\# classes using ``xsd.exe``. I always tend to write 
small Batch scripts for this kind of jobs, so it's you can change the path to the executable:

```batch
@echo off

SET XSD_EXECUTABLE="C:\Program Files (x86)\Microsoft SDKs\Windows\v8.1A\bin\NETFX 4.5.1 Tools\xsd.exe"

%XSD_EXECUTABLE% "Schemas/ExcelInteropSample.xsd" /classes /namespace:ExcelInteropSample.Contracts.Generated /o:"Generated" 
```

Executing this script leaves us with the generated contracts:

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/excel_xml_export/generated_contracts.png">
        <img src="/static/images/blog/excel_xml_export/generated_contracts.png" alt="Generated Contracts for a given XSD file">
    </a>
</div>

Using the Excel Interop functionality from the ``Microsoft.Office.Interop.Excel`` namespace, we can easily 
write a C\# method to extract the XML data using the XML Map. The method should be probably be extended with 
passing the ``XmlMap`` index, the Sheet Name and so on:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Microsoft.Office.Interop.Excel;
using System;
using System.Runtime.InteropServices;

namespace ExcelInteropSample.Utils
{
    public static class ExcelUtils
    {
        public static bool TryExportXml(string xlsxFilePath, out string xmlData)
        {
            xmlData = string.Empty;

            Application xlApp = new Application();

            xlApp.Visible = false;

            Workbook xlBook = xlApp.Workbooks.Open(Filename: xlsxFilePath,
                UpdateLinks: Type.Missing,
                ReadOnly: true,
                Format: Type.Missing,
                Password: Type.Missing,
                WriteResPassword: Type.Missing,
                IgnoreReadOnlyRecommended: Type.Missing,
                Origin: Type.Missing,
                Delimiter: Type.Missing,
                Editable: Type.Missing,
                Notify: Type.Missing,
                Converter: Type.Missing,
                AddToMru: Type.Missing,
                Local: Type.Missing,
                CorruptLoad: Type.Missing);
            
            XlXmlExportResult exportXmlResult = xlBook.XmlMaps[1].ExportXml(out xmlData);

            xlBook.Close(Type.Missing, Type.Missing, Type.Missing);

            xlApp.Quit();

            // Cleanup:
            Marshal.FinalReleaseComObject(xlBook);
            Marshal.FinalReleaseComObject(xlApp);

            if (exportXmlResult.HasFlag(XlXmlExportResult.xlXmlExportValidationFailed))
            {
                return false;
            }

            return true;
        }
    }
}
```

This method enables us to write a line like this to export the XML based on the first defined ``XmlMap``:

```csharp
var success = ExcelUtils.TryExportXml(filename, out string xml);
```

The final step is to deserialize the XML data to the generated C\# classes. This can be done using the ``XmlSerializer``. 

Again I am writing a small method for the job:

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.IO;
using System.Xml.Serialization;

namespace ExcelInteropSample.Utils
{
    public static class XmlUtils
    {
        public static TEntityType Deserialize<TEntityType>(string xmlString)
        {
            XmlSerializer xmlSerializer = new XmlSerializer(typeof(TEntityType));

            using (StringReader stringReader = new StringReader(xmlString))
            {
                return (TEntityType)xmlSerializer.Deserialize(stringReader);
            }
        }
    }
}
```

And finally we can connect all things to read the XML data, deserialize it and operate on the strongly-typed entities: 

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using ExcelInteropSample.Contracts.Generated;
using ExcelInteropSample.Utils;
using System;
using System.Globalization;
using System.IO;

namespace ExcelInteropSample
{
    class Program
    {
        static void Main(string[] args)
        {
            // We copy the Workbook to the bin/Debug, so we first need to get the absolute Path Excel should load:
            var filename = Path.Combine(System.AppContext.BaseDirectory, @"Resources\SampleWorkbook.xlsx");

            // Then we get the XML Data as string using the first XmlMap[1]:
            var success = ExcelUtils.TryExportXml(filename, out string xml);

            if(!success)
            {
                Console.WriteLine($"Exporting '{filename}' to XML failed");
                Console.ReadLine();

                return;
            }

            // And then use the XmlSerialize to deserialize it:
            var data = XmlUtils.Deserialize<ExcelInteropData>(xml);

            // And now we can safely iterate over the data:
            foreach(var entity in data.Entities)
            {
                var culture = new CultureInfo("en-US");

                Console.WriteLine($"{entity.FirstName} {entity.LastName} was born on {entity.BirthDate?.ToString(culture.DateTimeFormat.ShortDatePattern)} and has an Income of {entity.Income?.ToString("C", culture)}");
            }

            Console.ReadLine();
        }
    }
}
```

## Conclusion ##

And that's it!

Does this method have its shortcomings? Oh yes, of course! What about repeating fields? Nested elements? What if 
I do not have Microsoft Excel on the server? What if I have no control over the incoming Excel sheets and can 
not apply an XML mapping? What if my data is huge and the XML string blows up?

But anyway.

I find XML Maps are a simple way to not deal with Excel guessing the types. And I am not getting headaches about 
encodings, culture, delimiters and all this. Generating the contracts and deserialization is a big plus for me, 
so I do not have to hand roll anything.

And on the bright side, I get some data validation for free.

[OleDB Connection to query worksheets]: https://stackoverflow.com/a/18984865/513875
[trying to stop Excel from guessing Data Types]: https://docs.microsoft.com/en-us/office/client-developer/access/desktop-database-reference/initializing-the-microsoft-excel-driver