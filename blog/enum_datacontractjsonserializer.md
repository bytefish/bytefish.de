title: DataContractJsonSerializer: Serializing and Deserializing enum values by their name
date: 2015-03-27 20:54
tags: csharp
category: csharp
slug: enum_datacontractjsonserializer
author: Philipp Wagner

[NUnit]: http://www.nunit.org
[DataContractJsonSerializer]: https://msdn.microsoft.com/en-us/library/system.runtime.serialization.json.datacontractjsonserializer.aspx
[Json.NET]: http://www.newtonsoft.com/json

I am stuck in a project where I have to use the [DataContractJsonSerializer] coming with the .NET Framework. Serializing and Deserializing enum values by their name 
instead of their numerical value might not be obvious, so here is a simple example on how to do it.

First of all we'll define an ``interface`` for the Serializer.

```csharp
namespace JsonExample.Serialization
{
    public interface ISerializer
    {
        string Serialize<TEntity>(TEntity entity)  
            where TEntity : class, new();  

        TEntity Deserialize<TEntity>(string entity) 
            where TEntity : class, new();   
    }
}
```

Next we'll implement a sample Json Serializer using the [DataContractJsonSerializer].

```csharp
using System.IO;
using System.Runtime.Serialization.Json;
using System.Text;

namespace JsonExample.Serialization
{
    public class JsonSerializer : ISerializer
    {
        public string Serialize<TEntity>(TEntity entity) 
            where TEntity : class, new()
        {
            using (MemoryStream ms = new MemoryStream())
            {
                DataContractJsonSerializer ser = new DataContractJsonSerializer(typeof(TEntity));
                ser.WriteObject(ms, entity);
                return Encoding.UTF8.GetString(ms.ToArray());
            }
        }

        public TEntity Deserialize<TEntity>(string entity) 
            where TEntity : class, new()
        {
            DataContractJsonSerializer ser = new DataContractJsonSerializer(typeof(TEntity));
            using (MemoryStream stream = new MemoryStream(Encoding.UTF8.GetBytes(entity)))
            {
                return ser.ReadObject(stream) as TEntity;
            }
        }
    }
}
```

Next we define the ``enum``, which we want to serialize and deserialize to JSON.

```csharp
namespace JsonExample.Model
{
    public enum SampleEnum
    {
        FirstValue = 0,
        SecondValue
    }
}
```

And then we'll define the class, that uses the ``SampleEnum``. The trick is to use a string as a private property and override its getter and setter, so that:

* The getter returns the name of the ``enum`` value when serializing it.
* The setter parses the given enum name and sets the public property (``EnumVal`` in this example)

```csharp
using System;
using System.Runtime.Serialization;

namespace JsonExample.Model
{
    [DataContract]
    public class SampleClass
    {
        [DataMember(Name = "description", Order = 0)]
        public string Description { get; set; }

        public SampleEnum EnumVal { get; set; }

        [DataMember(Name = "enumVal", Order = 1)]
        private string EnumValString
        {
            get { return Enum.GetName(typeof(SampleEnum), this.EnumVal); }
            set { this.EnumVal = (SampleEnum)Enum.Parse(typeof(SampleEnum), value, true); }
        }
    }
}
```

And that's it basically. I am a big believer in Unit testing, so let's write a test to serialize and deserialize the sample class.

```csharp
using NUnit.Framework;
using JsonExample.Model;
using JsonExample.Serialization;

namespace JsonExample
{
    [TestFixture]
    public class JsonSerializationTest
    {
        private ISerializer jsonSerializer;

        [SetUp]
        public void SetUp()
        {
            jsonSerializer = new JsonSerializer();
        }

        [Test]
        public void SerializeEnumValueTest()
        {
            SampleClass sampleEntity = new SampleClass 
            {
                Description = "SerializeTest",
                EnumVal = SampleEnum.FirstValue
            };

            string expectedJsonData = "{\"description\":\"SerializeTest\",\"enumVal\":\"FirstValue\"}";
            string actualJsonData = jsonSerializer.Serialize<SampleClass>(sampleEntity);

            Assert.AreEqual(expectedJsonData, actualJsonData);
        }

        [Test]
        public void DeserializeEnumValueTest()
        {
            string jsonData = "{\"description\":\"DeserializeTest\",\"enumVal\":\"SecondValue\"}";

            SampleClass expectedSampleEntity = new SampleClass
            {
                Description = "DeserializeTest",
                EnumVal = SampleEnum.SecondValue
            };
            
            SampleClass actualSampleEntity = jsonSerializer.Deserialize<SampleClass>(jsonData);

            Assert.AreEqual(expectedSampleEntity.Description, actualSampleEntity.Description);
            Assert.AreEqual(expectedSampleEntity.EnumVal, actualSampleEntity.EnumVal);
        }
    }
}
```