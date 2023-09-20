title: Using T4 Templates for generating TypeScript 
date: 2023-03-28 12:26
tags: csharp, typescript, t4
category: csharp, typescript
slug: t4_templates_for_generating_typescript
author: Philipp Wagner
summary: In this article we will learn how to use T4 Templates to generate TypeScript code.

In the last article we have seen how to manually deserialize JSON with TypeScript. It's a lot 
of typing and I said it could easily be generated. So let's take a look how to generate TypeScript 
code from an OData EDM Model. 

Although this article uses an OData EDM model, it will also work just fine with an OpenAPI schema.

All code can be found in a GitHub repository at:

* [https://codeberg.org/bytefish/WideWorldImporters/blob/main/Backend/WideWorldImporters.ModelGenerator](https://codeberg.org/bytefish/WideWorldImporters/blob/main/Backend/WideWorldImporters.ModelGenerator)

## Table of contents ##

[TOC]

## What we are going to build ##

In the last article we have seen a `Customer` and `Order` model, that have been sent as 
a JSON payload by a fictional ASP.NET Core OData Service:

```typescript
export interface Customer {
    customerId?: number;
    customerName?: string;
    orders?: Order[];
}


export interface Order {
    orderId?: number;
    orderNumber?: string;
    pickupDateTime?: Date;
}
```

We have taken a look at deserializing the JSON data. And a simple `Converters` class with some 
static methods for converting from JSON to TypeScript objects looked like the best approach: 

```typescript
export class Converters {

    public static convertToCustomerArray(data: any): Customer[] | null {
        return Array.isArray(data) ? data.map(item => Converters.convertToCustomer(item)): undefined;
    }

    public static convertToCustomer(data: any): Customer | undefined {
        return data ? {
            customerId: data["customerId"],
            customerName: data["customerName"],
            orders: Converters.convertToOrderArray(data["orders"])
        } : undefined;
    }

    public static convertToOrderArray(data: any): Order[] | undefined {
        return Array.isArray(data) ? data.map(item => Converters.convertToOrder(item)) : undefined;
    }

    public static convertToOrder(data: any): Order | null {
        return data ? {
            orderId: data["orderId"],
            orderNumber: data["orderNumber"],
            pickupDateTime: data["pickupDateTime"] 
                ? new Date(data["pickupDateTime"]) : undefined
        } : undefined;
    }

}
```

## T4 Templates to Rescue ##

The idea is to use Runtime T4 Templates to generate the data. The T4 Template expects all 
Metadata about entities and their properties, because I don't want to reference the entire 
EDM Model:

```csharp
/// <summary>
/// Metadata for the Entity.
/// </summary>
public class EntityMetadata
{ 
    /// <summary>
    /// Gets or sets the Name.
    /// </summary>
    public string Name { get; set; }

    /// <summary>
    /// Gets or sets the Properties.
    /// </summary>
    public PropertyMetadata[] Properties { get; set; }
}

    /// <summary>
/// Holds all Property-related Metadata.
/// </summary>
public class PropertyMetadata
{
    /// <summary>
    /// Gets or sets the Name.
    /// </summary>
    public string Name { get; set; }

    /// <summary>
    /// Gets or sets the Type.
    /// </summary>
    public string Type { get; set; }

    /// <summary>
    /// Gets or sets the Nullability information.
    /// </summary>
    public bool IsNullable { get; set; }

    /// <summary>
    /// Gets or sets the Entity information.
    /// </summary>
    public bool IsEntity { get; set; }

    /// <summary>
    /// Gets or sets the Collection information.
    /// </summary>
    public bool IsCollection { get; set; }

    /// <summary>
    /// Gets or sets the Type of the array property.
    /// </summary>
    public string? ElementType { get; set; }

    /// <summary>
    /// Gets or sets the Information, if the array element is nullable.
    /// </summary>
    public bool? ElementIsNullable { get; set; }
}
```

What the C\# code does is to flatten the `IEdmModel` into the `EntityMetadata` objects and pass them 
into the T4 Template. This T4 Template is then invoked by running `TypeScriptCodeGen#TransformText()` 
on it.

```csharp
using Microsoft.OData.Edm;
using WideWorldImporters.Api.Models;

namespace WideWorldImporters.ModelGenerator // Note: actual namespace depends on the project name.
{
    internal class Program
    {
        static void Main(string[] args)
        {
            // Get the EDM Model used in the WideWorldImporters.Api project ...
            var edmModel = ApplicationEdmModel.GetEdmModel();

            // Create the TypeScript Code Generator with the EntityMetadata list ...
            var typeScriptCodeGenerator = new TypeScriptCodeGen()
            {
                EntityMetadatas = GetEntityMetadata(edmModel)
            };

            // Run the T4 Template to generate the TypeScript code ...
            var typeScriptCode = typeScriptCodeGenerator.TransformText();

            // ... and finall save it to disk:
            File.WriteAllText("entities.codegen.ts", typeScriptCode);
        }

        public static TypeScriptCodeGen.EntityMetadata[] GetEntityMetadata(IEdmModel model)
        {
            var edmEntityTypes = model.SchemaElements
                .OfType<IEdmEntityType>()
                .Cast<EdmEntityType>()
                .ToArray();

            return edmEntityTypes.Select(entity =>
            {
                // Resolve the Metadata for all Declared Properties
                var properties = entity.DeclaredProperties.Select(p => new TypeScriptCodeGen.PropertyMetadata
                {
                    Name = p.Name,
                    Type = GetTypeScriptType(p.Type),
                    IsNullable = p.Type.IsNullable,
                    IsEntity = p.Type.IsEntity(),
                    IsCollection = p.Type.IsCollection(),
                    ElementType = p.Type.IsCollection() ? GetTypeScriptType(p.Type.AsCollection().ElementType()) : null,
                    ElementIsNullable = p.Type.IsCollection() ? p.Type.AsCollection().ElementType().IsNullable : null,
                }).ToArray();

                return new TypeScriptCodeGen.EntityMetadata
                {
                    Name = entity.Name,
                    Properties = properties
                };
            }).ToArray();
        }

        private static string GetTypeScriptType(IEdmTypeReference edmTypeReference)
        {
            if (edmTypeReference.IsCollection())
            {
                return "[]";
            }
            else if (edmTypeReference.IsEntity())
            {
                return edmTypeReference.FullName().Split(".").Last();
            }
            else if (edmTypeReference.IsBinary() || edmTypeReference.IsSpatial() || edmTypeReference.IsGeometry() || edmTypeReference.IsGeography())
            {
                return "any";
            }
            else if (edmTypeReference.IsPrimitive())
            {
                return GetByPrimitiveType(edmTypeReference.AsPrimitive());
            }

            return string.Empty;
        }

        private static string GetByPrimitiveType(IEdmPrimitiveTypeReference edmPrimitiveTypeReference)
        {
            var edmPrimitiveKind = edmPrimitiveTypeReference.PrimitiveKind();

            switch (edmPrimitiveKind)
            {
                case EdmPrimitiveTypeKind.Binary:
                    return "string";
                case EdmPrimitiveTypeKind.Boolean:
                    return "boolean";
                case EdmPrimitiveTypeKind.SByte:
                case EdmPrimitiveTypeKind.Byte:
                case EdmPrimitiveTypeKind.Int16:
                case EdmPrimitiveTypeKind.Int32:
                case EdmPrimitiveTypeKind.Int64:
                case EdmPrimitiveTypeKind.Single:
                case EdmPrimitiveTypeKind.Double:
                case EdmPrimitiveTypeKind.Decimal:
                    return "number";
                case EdmPrimitiveTypeKind.String:
                    return "string";
                case EdmPrimitiveTypeKind.Date:
                case EdmPrimitiveTypeKind.DateTimeOffset:
                    return "Date";
                case EdmPrimitiveTypeKind.Guid:
                    return "string";
                case EdmPrimitiveTypeKind.Geography:
                case EdmPrimitiveTypeKind.GeographyCollection:
                case EdmPrimitiveTypeKind.GeographyPolygon:
                case EdmPrimitiveTypeKind.GeographyPoint:
                case EdmPrimitiveTypeKind.GeographyMultiPoint:
                case EdmPrimitiveTypeKind.GeographyLineString:
                case EdmPrimitiveTypeKind.GeographyMultiLineString:
                    return "string";
                default:
                    return "any";
            }
        }
    }
}
```

The T4 Template then iterates over the `EntityMetadata` array and recreates the TypeScript interfaces 
and the `Converter` class, that has been shown in the previous article. The TypeScript code can then 
be copy and pasted into an application, if the API has been updated.

```txt
//------------------------------------------------------------------------------
// <auto-generated>
//     This code was generated from a template.
//
//     Manual changes to this file may cause unexpected behavior in your application.
//     Manual changes to this file will be overwritten if the code is regenerated.
// </auto-generated>
//------------------------------------------------------------------------------
<#@ template language="C#" #>
<# 
foreach(var entityMetadata in EntityMetadatas) { 
#>
export interface <#= entityMetadata.Name #> {
<# 
    foreach(var propertyMetadata in entityMetadata.Properties) { 
#>
<#
        if(propertyMetadata.IsCollection) { 
#>
  <#= propertyMetadata.Name #>: Array<<#= propertyMetadata.ElementType #>> <#= propertyMetadata.IsNullable ? " | null" : "" #>;
<#
        } else { 
#>
  <#= propertyMetadata.Name #>?: <#= propertyMetadata.Type#><#= propertyMetadata.IsNullable ? " | null" : "" #>;
<#
        } 
#>
<#
    }
#>
}

<#
}

#>

export class Converters {
    
    public static convertDateArray(data: any) : Date[] | undefined {
        return Array.isArray(data) ? data.map(item => new Date(item)) : undefined;
    }

<# 
foreach(var entityMetadata in EntityMetadatas) { 
#>

    public static convertTo<#= entityMetadata.Name #>Array(data: any): <#= entityMetadata.Name #>[] | undefined {
        return Array.isArray(data) ? data.map(item => Converters.convertTo<#= entityMetadata.Name #>(item)) : undefined;
    }

    public static convertTo<#= entityMetadata.Name #>(data: any): <#= entityMetadata.Name #> | undefined {
        return data ? {
<#
    foreach(var propertyMetadata in entityMetadata.Properties) { 
#>
<#
        if(propertyMetadata.IsCollection) { 
#>
            <#= propertyMetadata.Name #>: Converters.convertTo<#= propertyMetadata.ElementType #>Array(data["<#= propertyMetadata.Name #>"]),
<#
        } else if(propertyMetadata.Type == "Date") { 
#>
            <#= propertyMetadata.Name #>: data["<#= propertyMetadata.Name #>"] ? new Date(data["<#= propertyMetadata.Name #>"]) : undefined,
<#
        } else  { 
#>
            <#= propertyMetadata.Name #>: data["<#= propertyMetadata.Name #>"],
<#
        }
#>
<#
    }
#>
        } : undefined;
    }
<#
    }
#>
}

<#+

    /// <summary>
    /// Metadata for the Entity.
    /// </summary>
    public class EntityMetadata
    { 
        /// <summary>
        /// Gets or sets the Name.
        /// </summary>
        public string Name { get; set; }

        /// <summary>
        /// Gets or sets the Properties.
        /// </summary>
        public PropertyMetadata[] Properties { get; set; }
    }

        /// <summary>
    /// Holds all Property-related Metadata.
    /// </summary>
    public class PropertyMetadata
    {
        /// <summary>
        /// Gets or sets the Name.
        /// </summary>
        public string Name { get; set; }

        /// <summary>
        /// Gets or sets the Type.
        /// </summary>
        public string Type { get; set; }

        /// <summary>
        /// Gets or sets the Nullability information.
        /// </summary>
        public bool IsNullable { get; set; }

        /// <summary>
        /// Gets or sets the Entity information.
        /// </summary>
        public bool IsEntity { get; set; }

        /// <summary>
        /// Gets or sets the Collection information.
        /// </summary>
        public bool IsCollection { get; set; }

        /// <summary>
        /// Gets or sets the Type of the array property.
        /// </summary>
        public string? ElementType { get; set; }

        /// <summary>
        /// Gets or sets the Information, if the array element is nullable.
        /// </summary>
        public bool? ElementIsNullable { get; set; }
    }

    // The Entity Metadata List, that we are generating interfaces and Converters for:
    public EntityMetadata[] EntityMetadatas { get; set; }
#>
```

## Result ##

The generated TypeScript code will look like this:

```typescript
//------------------------------------------------------------------------------
// <auto-generated>
//     This code was generated from a template.
//
//     Manual changes to this file may cause unexpected behavior in your application.
//     Manual changes to this file will be overwritten if the code is regenerated.
// </auto-generated>
//------------------------------------------------------------------------------

export interface BuyingGroup {
  buyingGroupId?: number;
  buyingGroupName?: string;
  lastEditedBy?: number;
  lastEditedByNavigation?: Person;
  customers: Array<Customer>  | null;
  specialDeals: Array<SpecialDeal>  | null;
}

export interface City {
  cityId?: number;
  cityName?: string;
  stateProvinceId?: number;
  latestRecordedPopulation?: number | null;
  lastEditedBy?: number;
  location?: any | null;
  lastEditedByNavigation?: Person;
  stateProvince?: StateProvince;
  customerDeliveryCities: Array<Customer>  | null;
  customerPostalCities: Array<Customer>  | null;
  supplierDeliveryCities: Array<Supplier>  | null;
  supplierPostalCities: Array<Supplier>  | null;
  systemParameterDeliveryCities: Array<SystemParameter>  | null;
  systemParameterPostalCities: Array<SystemParameter>  | null;
}

export interface ColdRoomTemperature {
  coldRoomTemperatureId?: number;
  coldRoomSensorNumber?: number;
  recordedWhen?: Date;
  temperature?: number;
}

// ...

export class Converters {
    
    public static convertDateArray(data: any) : Date[] | undefined {
        return Array.isArray(data) ? data.map(item => new Date(item)) : undefined;
    }


    public static convertToBuyingGroupArray(data: any): BuyingGroup[] | undefined {
        return Array.isArray(data) ? data.map(item => Converters.convertToBuyingGroup(item)) : undefined;
    }

    public static convertToBuyingGroup(data: any): BuyingGroup | undefined {
        return data ? {
            buyingGroupId: data["buyingGroupId"],
            buyingGroupName: data["buyingGroupName"],
            lastEditedBy: data["lastEditedBy"],
            lastEditedByNavigation: data["lastEditedByNavigation"],
            customers: Converters.convertToCustomerArray(data["customers"]),
            specialDeals: Converters.convertToSpecialDealArray(data["specialDeals"]),
        } : undefined;
    }

    public static convertToCityArray(data: any): City[] | undefined {
        return Array.isArray(data) ? data.map(item => Converters.convertToCity(item)) : undefined;
    }

    public static convertToCity(data: any): City | undefined {
        return data ? {
            cityId: data["cityId"],
            cityName: data["cityName"],
            stateProvinceId: data["stateProvinceId"],
            latestRecordedPopulation: data["latestRecordedPopulation"],
            lastEditedBy: data["lastEditedBy"],
            location: data["location"],
            lastEditedByNavigation: data["lastEditedByNavigation"],
            stateProvince: data["stateProvince"],
            customerDeliveryCities: Converters.convertToCustomerArray(data["customerDeliveryCities"]),
            customerPostalCities: Converters.convertToCustomerArray(data["customerPostalCities"]),
            supplierDeliveryCities: Converters.convertToSupplierArray(data["supplierDeliveryCities"]),
            supplierPostalCities: Converters.convertToSupplierArray(data["supplierPostalCities"]),
            systemParameterDeliveryCities: Converters.convertToSystemParameterArray(data["systemParameterDeliveryCities"]),
            systemParameterPostalCities: Converters.convertToSystemParameterArray(data["systemParameterPostalCities"]),
        } : undefined;
    }

    // ...
}
```

## Conclusion ##

T4 Templates are easily the most underrated tool in the .NET ecosystem. It has been really 
easy to use them for generating TypeScript models for OData services. No more fighting against 
external code generation tools.