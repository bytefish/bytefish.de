title: JSON Deserialization with TypeScript
date: 2023-03-27 08:33
tags: typescript, json
category: typescript
slug: json_deserizaltion_with_typescript
author: Philipp Wagner
summary: This article shows how to deserialize JSON with TypeScript.

If you have ever worked with JSON in an Angular application, you know that you cannot 
trust the deserialized results. JavaScript doesn't have Reflection, JSON doesn't have 
a data type for a `Date` and so... so `JSON.parse` doesn't know that you want the 
incoming `string` value `"2018-07-15T05:35:03.000Z"` converted to a `Date`.

Great!

Say you have defined an interface `Order` as:

```typescript 
export interface Order {
    orderId?: number;
    orderNumber?: string;
    pickupDateTime?: Date
}
```

And you call your Angular `HttpClient` with the generic `HttpClient#get<T>` overload: 

```typescript
this.httpClient
    .get<Order>(url, ...)
    .pipe(
        map((response: Order) => {
            // Work with the Response ...
        })
    );
```

Your Webservice responds with a totally valid JSON `Order` as:

```json
{ 
    "orderId": 1,
    "orderNumber": "8472-423-14",
    "pickupDateTime":"2018-07-15T05:35:03.000Z"
}
```

And with a simple test, we can see, that the returned `pickupDateTime` is actually a `string` and not a `Date`:

```typescript
describe('JSON.parse', () => {

    it('Should not parse string as Date', () => {
        
        // prepare
        const json = `
        { 
            "orderId": 1,
            "orderNumber": "8472-423-14",
            "pickupDateTime":"2018-07-15T05:35:03.000Z"
        }`;

        // act
        const verifyResult = JSON.parse(json) as Order;

        // verify
        const isTypeOfString = typeof verifyResult.pickupDateTime === "string";
        const isInstanceOfDate = verifyResult.pickupDateTime instanceof Date;
        
        deepStrictEqual(isTypeOfString, true);
        deepStrictEqual(isInstanceOfDate, false);
    }); 
    
});
```

In this example we will take a look at different ways to get the correct results for our deserialized JSON. 

All code can be found in a GitHub repository at:

* [https://github.com/bytefish/TypeScriptExperiments](https://github.com/bytefish/TypeScriptExperiments)

## Solutions ##

### Manual Conversion ###

The most obvious way to convert JSON data is to reflect by hand, and manually handroll the 
deserialization. While this involves a lot of typing, though I am pretty sure most of it can 
be generated. 

It involves the least amount of *magic* and it doesn't involve any TypeScript cleverness. Absolutely 
everyone in a team understands this conversion and that should never be underestimated. I want to go 
on holiday and know all people get along just fine.

So what I would do is to basically ship a `Converters` class, which contains converters for all 
classes involved. Problem solved. And if the class gets huge you could break it down into an 
`OrderConverter`, `CustomerConverter` and so on...

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

    public static convertDateArray(data: any) : Date[] | undefined {
        return Array.isArray(data) ? data.map(item => new Date(item)) : undefined;
    }
}
```

### Deserialization using Decorators ###

So JavaScript removes the types at runtime and there is no Reflection. Then how on earth does 
Angular provide all this Dependency Injection voodoo? By using Decorators! You have probably 
come across a decorator like `@Component` in your Angular development?

So the idea is to provide a set of decorators like `@JsonProperty`, `@JsonType`, ... to decorate 
classes and deserialize the JSON into the correct types. It will look like this:

```typescript
export class Order {

    @JsonProperty("orderId")
    orderId?: number;

    @JsonProperty("orderNumber")
    orderNumber?: string;

    @JsonProperty("pickupDateTime")
    @JsonType(Date)
    pickupDateTime?: Date;
}
```

And with a simple test, we will see the correct types on our deserialized object:

```typescript
describe('deserialize', () => {

    it('Decorated Order should parse Date', () => {
        // prepare        
        const json = `
        { 
            "orderId": 1,
            "orderNumber": "8472-423-14",
            "pickupDateTime":"2018-07-15T05:35:03.000Z"
        }`;

        // act
        const verifyResult: Order = deserialize<Order>(json, Order);

        // verify
        const isTypeOfObject = typeof verifyResult.pickupDateTime === "object";
        const isInstanceOfDate = verifyResult.pickupDateTime instanceof Date;
        
        deepStrictEqual(isTypeOfObject, true);
        deepStrictEqual(isInstanceOfDate, true);
    }); 
});
```

That enables us a bit more type-safety, when deserializing incoming JSON data.

We start by enabling the secret sauce `tsconfig.json` of our project:

```json
{
  "compilerOptions": {
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true
  }
}
```

What's happening under the hood is, that TypeScript generates two helper functions `__decorate` 
and `__metadata` when it translates to JavaScript:

```javascript
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") 
        return Reflect.metadata(k, v);
};
```

Now assume we have added decorators to our class, like this:

```typescript
export class Order {

    @JsonProperty("orderId")
    orderId?: number;

    @JsonProperty("orderNumber")
    orderNumber?: string;

    @JsonProperty("pickupDateTime")
    @JsonType(Date)
    pickupDateTime?: Date;
    
}

```

Then `tsc` will generate the following JavaScript:

```javascript
var Order = exports.Order = /** @class */ (function () {
    function Order() {
    }
    __decorate([
        (0, deserializer_1.JsonProperty)("orderId"),
        __metadata("design:type", Number)
    ], Order.prototype, "orderId", void 0);
    __decorate([
        (0, deserializer_1.JsonProperty)("orderNumber"),
        __metadata("design:type", String)
    ], Order.prototype, "orderNumber", void 0);
    __decorate([
        (0, deserializer_1.JsonProperty)("pickupDateTime"),
        (0, deserializer_1.JsonType)(Date),
        __metadata("design:type", Date)
    ], Order.prototype, "pickupDateTime", void 0);
    return Order;
}());
```

I won't go into details here, but we can see, that `__decorate` and `__metadata` use the 
Reflect API polyfill. The Reflect API internally creates `WeakMap` to store the Metadata 
and uses the Object itself as the key.

Now with the Reflect API magic explained, let's implement the JSON deserializer. The deserializer 
example is based on the great `typeserializer` library by Dan Revah, which is available at:

* [https://github.com/danrevah/typeserializer/](https://github.com/danrevah/typeserializer/)

So all credit goes to him. It's such a clever and great implementation.

We start by adding the `reflect-metadata` polyfill, because the Reflect API isn't an official standard:

```typescript
import 'reflect-metadata';
```

Metadata can only be attached to objects and we are working in JavaScript, so we need helper methods 
to know at runtime, if a given value is defined and is an object:

```typescript
// Helpers
export function isObject(val: any) {
    return typeof val === 'object' && val !== null && !Array.isArray(val);
}

export function isUndefined(val: any) {
    return typeof val === 'undefined';
}
```

We can then add a `createDecorator` method to create a Decorator function, that we can 
then use to decorate properties and classes.

```typescript
// Creates a Decorator
export function createDecorator(name: string, keySymbol: Symbol, value: any) {
    return function <T extends Object>(target: T, key: keyof T) {
        const obj = Reflect.getMetadata(keySymbol, target) || {};

        if (!isUndefined(obj[key])) {
            throw new Error(
                `Cannot apply @${name} decorator twice on property '${String(key)}' of class '${(target as any).constructor.name}'.`
            );
        }

        Reflect.defineMetadata(keySymbol, { ...obj, ...{ [key]: value } }, target);
    };
}
```

Next we define the set of `Symbol`, that serve as the keys for the metadata:

```typescript
export const JsonPropertySymbol = Symbol('JsonProperty');
export const JsonTypeSymbol = Symbol('JsonType');
export const JsonConverterSymbol = Symbol('JsonConverter');
```

Next we create the set of decorator functions, that we can apply using the special `@` syntax we 
have enabled in the `tsconfig.json`:

```typescript
// Decorators
export function JsonProperty(name: string) {
    return createDecorator("JsonProperty", JsonPropertySymbol, name);
}

export function JsonType(type: any) {
    return createDecorator("JsonType", JsonTypeSymbol, type);
}

export function JsonConverter<T>(fn: (value: any, obj: any) => T) {
    return createDecorator("JsonConverter", JsonConverterSymbol, fn);
}
```

Then we can implement a `deserialize` method, that takes a JSON string and class type. We 
need a class type, so we can access the Metadata. Remember: The Reflect API stores all Metadata 
using an `Object` as key.

By using `Reflect.getMetadata` on the target instance we can reflect the Metadata associated and then 
map the JSON object accordingly.

```typescript
// Deserializer
export function deserialize<T>(json: string, classType: any): any {
    return transform(toObject(json), classType);
}

// Transformers
export function transformArray(arr: any[], classType: any): any[] {
    return arr.map((elm: any) => (Array.isArray(elm) ? transformArray(elm, classType) : transform(elm, classType)));
}

export function transform(obj: any, classType: any) {

    // If the given value is not an object, we cannot reflect
    if (!isObject(obj)) {
        return obj;
    }

    // Create an instance, so we can reflect the Decorator metadata:
    const instance = new classType();

    // Reflects the Metadata associated with each property:
    const jsonPropertyMap = Reflect.getMetadata(JsonPropertySymbol, instance) || {};
    const jsonTypeMap = Reflect.getMetadata(JsonTypeSymbol, instance) || {};
    const jsonConverterMap = Reflect.getMetadata(JsonConverterSymbol, instance) || {};

    // Maps the Name to the Property
    const nameToPropertyMap = Object.keys(jsonPropertyMap)
        .reduce((accumulator: any, key: string) => ({ ...accumulator, [jsonPropertyMap[key]]: key }), {});

    Object.keys(obj).forEach((key: string) => {
        if (nameToPropertyMap.hasOwnProperty(key)) {
            instance[nameToPropertyMap[key]] = obj[key];
        } else {
            instance[key] = obj[key];
        }
        
        if (typeof jsonConverterMap[key] === 'function') {
            
            instance[key] = jsonConverterMap[key].call(null, instance[key], instance);
            return;
        }

        if (!jsonTypeMap.hasOwnProperty(key)) {
            return;
        }

        const type = jsonTypeMap[key];

        if (Array.isArray(type)) {
            instance[key] = transformArray(obj[key], type[0]);
        } else if (type === Date) {
            instance[key] = new Date(obj[key]);
        } else {
            instance[key] = transform(obj[key], type);
        }
    });

    return instance;
}

```

## Adding Unit Tests for both implementations ##

In the `deserializer.spec.ts` class, we are adding tests to ensure both approaches work correctly.

```typescript
import { describe, it, } from 'mocha';
import { Temporal } from "@js-temporal/polyfill";
import { deepStrictEqual } from "assert";

import { deserialize, isObject, JsonConverter, JsonProperty, JsonType, transform, transformArray } from './deserializer';

const fixtureChildOrder1 = `
    { 
        "orderId": 1,
        "orderNumber": "8472-423-14",
        "pickupDateTime":"2018-07-15T05:35:03.000Z"
    }`;

const fixtureChildOrder2 = `
    { 
        "orderId": 2,
        "orderNumber": "1341-7856-75189",
        "pickupDateTime":"2019-01-12T01:15:03.000Z"
    }`;

const fixtureCustomer = `
    {
        "customerId": 4,
        "customerName": "Northwind Toys",
        "orders": [
            ${fixtureChildOrder1},
            ${fixtureChildOrder2}
        ]
    }
`;

const fixturePlainDateExample = `
    {
        "shippingDate": "2012-01-01"
    }
`;

export class JsonConverterExample {

    @JsonProperty("shippingDate")
    @JsonConverter((val) => Temporal.PlainDate.from(val))
    shippingDate?: Temporal.PlainDate;

}

const fixtureDifferentNameExample = `
    {
        "myShippingDate": "2012-01-01"
    }
`;

export class JsonPropertyExample {

    @JsonProperty("myShippingDate")
    shippingDate?: string;
}

const fixtureODataEntityResponse = `
    {
        "@odata.context" : "http://localhost:5000/odata/#Customer",
        "@odata.count" : 2,
        "orderId": 2,
        "orderNumber": "1341-7856-75189",
        "pickupDateTime":"2019-01-12T01:15:03.000Z"
    }
`;

const fixtureODataEntitiesResponse = `
    {
        "@odata.context" : "http://localhost:5000/odata/#Customer",
        "@odata.count" : 2,
        "value" : [
            ${fixtureChildOrder1},
            ${fixtureChildOrder2} 
        ]
    }
`;

export class Order {

    @JsonProperty("orderId")
    orderId?: number;

    @JsonProperty("orderNumber")
    orderNumber?: string;

    @JsonProperty("pickupDateTime")
    @JsonType(Date)
    pickupDateTime?: Date;

}

export class Customer {

    @JsonProperty("orderId")
    customerId?: number;

    @JsonProperty("customerName")
    customerName?: string;

    @JsonProperty("orders")
    @JsonType([Order])
    orders?: Order[];
}

export class OrderWithoutDecorators {

    orderId?: number;

    orderNumber?: string;

    pickupDateTime?: Date;
}

describe('JSON.parse', () => {

    it('Should not parse string as Date', () => {
        
        // prepare
        const json = `
        { 
            "orderId": 1,
            "orderNumber": "8472-423-14",
            "pickupDateTime":"2018-07-15T05:35:03.000Z"
        }`;

        // act
        const verifyResult = JSON.parse(json) as Order;

        // verify
        const isTypeOfString = typeof verifyResult.pickupDateTime === "string";
        const isInstanceOfDate = verifyResult.pickupDateTime instanceof Date;
        

        deepStrictEqual(isTypeOfString, true);
        deepStrictEqual(isInstanceOfDate, false);
    }); 

});

describe('deserialize', () => {

    it('Decorated Order should parse Date', () => {
        // prepare        
        const json = `
        { 
            "orderId": 1,
            "orderNumber": "8472-423-14",
            "pickupDateTime":"2018-07-15T05:35:03.000Z"
        }`;

        // act
        const verifyResult: Order = deserialize<Order>(json, Order);

        // verify
        const isTypeOfObject = typeof verifyResult.pickupDateTime === "object";
        const isInstanceOfDate = verifyResult.pickupDateTime instanceof Date;
        
        deepStrictEqual(isTypeOfObject, true);
        deepStrictEqual(isInstanceOfDate, true);
    }); 


    it('Should convert Customer with manual conversion', () => {
        // prepare
        const data = JSON.parse(fixtureCustomer);

        // act
        const verifyResult: Customer = Converters.convertToCustomer(data);
        
        // verify
        const isTypeOfObject = typeof verifyResult.orders[0].pickupDateTime === "object";
        const isInstanceOfDate = verifyResult.orders[0].pickupDateTime instanceof Date;
        
        deepStrictEqual(isTypeOfObject, true);
        deepStrictEqual(isInstanceOfDate, true);

        deepStrictEqual(verifyResult.orders[0].pickupDateTime, new Date("2018-07-15T05:35:03.000Z"));
        deepStrictEqual(verifyResult.orders[1].pickupDateTime, new Date("2019-01-12T01:15:03.000Z"));
    }); 

    it('Should Convert Child Array and Dates', () => {
        // prepare
        // act
        const customer: Customer = deserialize(fixtureCustomer, Customer);
        
        // verify
        deepStrictEqual(customer.orders[0].pickupDateTime, new Date("2018-07-15T05:35:03.000Z"));
        deepStrictEqual(customer.orders[1].pickupDateTime, new Date("2019-01-12T01:15:03.000Z"));
    }); 

    it('Should Convert Plain Date', () => {
        // prepare
        // act
        const verifyResult: JsonConverterExample = deserialize(fixturePlainDateExample, JsonConverterExample);
        
        deepStrictEqual(verifyResult.shippingDate, Temporal.PlainDate.from("2012-01-01"));
    }); 

    it('Should Convert by Name', () => {
        // prepare
        //act
        const verifyResult: JsonConverterExample = deserialize(fixtureDifferentNameExample, JsonPropertyExample);

        // verify
        deepStrictEqual(verifyResult.shippingDate, "2012-01-01");
    }); 
    
    // ...
});
```

## Conclusion ##

I thought hard about, what's the best way in TypeScript to deserialize a given JSON object.

And I have to admit, that `@JsonProperty` and `@JsonType` decorators look great on the outside. They make the whole 
deserialization very clean. You could easily add decorators like `@JsonRequired` to require certain properties 
during deserialization, one can imagine `@JsonValidate` decorator to validate incoming data.

But with a manual conversion? I can just debug and step through the whole thing, and get the freedom to do whatever 
I want with the data. What would have been a `@JsonRequired` decorator will now be a function `Converters#require`, 
so what? 

I am working on an OData application, so I have access to all schema elements, their properties and types. That makes 
it possible to simply generate all TypeScript interfaces and required converter functions... no magic included and 
that's probably the way I would go.

What is your approach to JSON deserialization with TypeScript?