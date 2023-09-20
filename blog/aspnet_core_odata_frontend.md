title: Building an Angular Frontend for an ASP.NET Core OData Application
date: 2022-08-27 11:34
tags: angular, aspnetcore, csharp, odata
category: csharp
slug: aspnet_core_odata_frontend
author: Philipp Wagner
summary: This article shows how to build a Frontend application with Angular, that works with an ASP.NET Core OData Backend.

In the last article I have shown how to build a Backend for WideWorldImporters database using ASP.NET Core OData and EntityFramework Core:

* [https://www.bytefish.de/blog/aspnet_core_odata_example.html](https://www.bytefish.de/blog/aspnet_core_odata_example.html)

In this article we are taking the next step and build a Frontend for displaying the data in a Datagrid.

All code can be found at:

* [https://codeberg.org/bytefish/WideWorldImporters](https://codeberg.org/bytefish/WideWorldImporters)

## Table of contents ##

[TOC]

## What we are going to build ##

"I just want to show some data in a table and filter it. Why is all this so, so complicated?", 
said everyone trying to quickly expose a dataset with an Angular application. It doesn't have 
to be this way.

The Frontend is an Angular application to query the OData endpoints. We are going to use Angular components of the Clarity 
Design system, because Clarity takes a Desktop-first approach and has a very nice Datagrid, that's easy to extend:

* [https://clarity.design/](https://clarity.design/)

The final application will look like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/00_WWI_App.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/00_WWI_App.jpg" alt="The final Angular application">
    </a>
</div>

## Application Basics ##

### Application Translations ###

You should start your applications with translations. Translations are everywhere in your application, just think of 
menu items, column headers, ... you are going to need them basically everywhere. And modern applications should also take 
good care of a11y, because some people depend on screenreaders and additional information.

#### Providing translations for the application ####

I want type-safety for the translations. In my opinion there is nothing worse, than operating on strings and suddenly have placeholders popping 
up in the UI, because you mistyped some identifier... or even worse embarassing key names show up. So I will simply use an approach I have seen 
in Clarity and define a class called ``AppCommonStrings``, that provides type-safe access to all translations in the application.

That has the following advantadges:

* Locales need to implement the ``AppCommonStrings`` interface.
    * TypeScript ensures, that you have defined all your keys for all locales.
* Templates using the ``TranslationService`` can access the Translations by property with type-safety.
    * TypeScript ensures, that you are accessing valid properties and fails on mistyped properties.

You will instantiate the ``TranslationService`` in an Angular module, so it gets initialized with the correct locale.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Inject, Injectable, LOCALE_ID } from "@angular/core";
import { AppCommonStrings, defaultCommonStrings, germanCommonStrings } from "../data/app-common-strings";

/** */
@Injectable({
    providedIn: 'root',
  })
  export class TranslationService {

    /**
     * Holds the Translations available for the application. This could also 
     * be provided using dependency injection.
     */
    translations: Map<string, AppCommonStrings> = new Map([
        [ 'en', defaultCommonStrings ],
        [ 'de', germanCommonStrings ],
    ]);

    /**
     * Constructs a ``TranslationService`` with a given locale.
     * 
     * @param locale - Application locale
     */
    constructor(@Inject(LOCALE_ID) locale: string) {
        this.set(locale);
    }

    /**
     * Sets the translations for the given locale.
     * 
     * @param locale - Locale to use
     */
    public set(locale: string) {
        var translations = this.get(locale);

        this.localize(translations);
    }

    /**
     * Gets the translations for a given locale.
     * 
     * @param locale 
     * @returns 
     */
    private get(locale: string) : AppCommonStrings {
        return this.translations.has(locale) ? this.translations.get(locale)! : defaultCommonStrings;
    }
    
    private _strings = defaultCommonStrings;
  
    /**
     * Allows you to pass in new overrides for localization
     */
    localize(overrides: Partial<AppCommonStrings>) {
      this._strings = { ...this._strings, ...overrides };
    }
  
    /**
     * Access to all of the keys as strings
     */
    get keys(): Readonly<AppCommonStrings> {
      return this._strings;
    }
  
    /**
     * Parse a string with a set of tokens to replace
     */
    parse(source: string, tokens: { [key: string]: string } = {}) {
      const names = Object.keys(tokens);
      let output = source;
      if (names.length) {
        names.forEach(name => {
          output = output.replace(`{${name}}`, tokens[name]);
        });
      }
      return output;
    }
}
```

#### Providing translations for Clarity controls ####

Clarity uses the same simple approach, that I like a lot, because it's so transparent and not magic. The framework wants you to configure the translations 
in the ``ClrCommonStringsService`` for every language you want to support. 

I will just inject the current Locale using Angular ``LOCALE_ID`` injection token, and then set the ``ClrCommonStrings`` for all locales, that contain 
the required translations. The translations are given in the file ``app/data/clr-common-strings.ts``, it's just some static data that gets imported.


```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Inject, Injectable, LOCALE_ID } from "@angular/core";
import { ClrCommonStrings, ClrCommonStringsService, commonStringsDefault } from "@clr/angular";
import { germanLocale } from "../data/clr-common-strings";

/**
 * The ``CommonStringService`` is used to initialize the Clarity ``ClrCommonStringsService`` with the 
 * values of a given Locale, which is injected by Angulars Dependency Injection framework as a Injection 
 * Token.
 * 
 * @public
 */
@Injectable({
    providedIn: `root`
})
export class CommonStringsService {

    /**
     * The available Clarity component translations.
     */
    translations: Map<string, ClrCommonStrings> = new Map([
        ['en', commonStringsDefault],
        ['de', germanLocale],
    ]);

    /**
     * Initializes the ``CommonStringsService``.
     * 
     * @param locale - Application locale
     * @param clrCommonStringsService - Clarity ``ClrCommonStringsService`` for control translations
     */
    constructor(@Inject(LOCALE_ID) locale: string, private clrCommonStringsService: ClrCommonStringsService) {
        this.set(locale);
    }

    /**
     * Sets the Locale and updates the wrapped ``ClrCommonStringsService``.
     * 
     * @param locale - Application locale
     */
    public set(locale: string) {
        this.clrCommonStringsService.localize(this.get(locale));
    }

    /**
     * Gets the ``ClrCommonStrings`` for a given locale.
     * 
     * @param locale - Application Locale
     * @returns The ``ClrCommonStrings`` for a given locale
     */
    private get(locale: string): ClrCommonStrings {
        return this.translations.has(locale) ? this.translations.get(locale)! : commonStringsDefault;
    }
}
```

### Application Menus ###

Your users are going to navigate your application by using menus. It's a good next step in your 
application development to think about menus. Do you want a side menu, a header menu or something 
like a drop down menu?

#### Starting with... translations again ####

We start the implementation for the menu by defining the translations in the ``AppCommonStrings``, this is done for 
the sidemenu items, the header items and the dropdown items. Please feel totally free to come up with your own 
approach to modelling the translations.


```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

/**
 * All Resource strings available in the application.
 */
export interface AppCommonStrings {
  sidemenu: {
        home: string,
        tables: string,
        cities: string,
        countries: string,
        customers: string,
    },
    header: {
        title: string,
        navigation: {
            customers: string,
        }
    },
    dropdown: {
        title: string,
        profile: string,
    }
};
```

And the translations for English are given by defining a dictionary ``defaultCommonStrings``, that implements 
the ``AppCommonStrings`` and ensure we translated everything.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

export const defaultCommonStrings: AppCommonStrings = {
  header: {
        title: "Wide World Importers",
        navigation: {
            customers: "Customers"
        }
    },
    // Side Menu:
    sidemenu: {
        home: "Home",
        tables: "Tables",
        cities: "Cities",
        countries: "Countries",
        customers: "Customers",
    },
    // Dropdown Menu:
    dropdown: {
        title: "Settings",
        profile: "Profile"
    }
};
```

#### Modelling the Menu Items ####

Next we define the menu items in the application. Each item can have children, so we are able to build 
a hierarchy of menu sections and menu items. They should be the same for all kinds of menus in our 
application.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

/**
 * A menu item in the application, which can be an item in the side-menu, an 
 * item in the header or an item in drop-down.
 */
export interface MenuItem {
    
    /**
     * A unique Id.
     */
    id: string;

    /**
     * Is the Menu Item active?
     */
    active?: boolean;

    /**
     * An Icon.
     */
    icon?: string | null;

    /**
     * The Name.
     */
    name: string;

    /**
     * The description.
     */
    description: string;

    /**
     * Accessibility.
     */
    ariaLabel: string;

    /**
     * The Router URL.
     */
    url?: string;

    /**
     * The Children.
     */
    children?: MenuItem[];
}
```

#### Defining the actual Menu structure ####

And we define the actual menu contents in a class ``data/app-menu-items.ts``, where each method also takes a dependency on the 
``TranslationService`` for translating all menu item texts.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { MenuItem } from "../models/menu-item";
import { TranslationService } from "../services/translation.service";

/**
 * Builds the Header menu items.
 * 
 * @param translations - Translations to apply for the Header items.
 * @returns The Header menu items.
 */
 export function dropDownItems(translations: TranslationService): Array<MenuItem> {
    return [
        {
            id: "profile",
            name: translations.keys.dropdown.profile,
            description: translations.keys.dropdown.profile,
            ariaLabel: translations.keys.dropdown.profile,
            url: "/profile"
        },
    ];
};

/**
 * Builds the Header menu items.
 * 
 * @param translations - Translations to apply for the Header items.
 * @returns The Header menu items.
 */
 export function headerMenuItems(translations: TranslationService): Array<MenuItem> {
    return [
        {
            id: "customers",
            name: translations.keys.header.navigation.customers,
            description: translations.keys.header.navigation.customers,
            ariaLabel: translations.keys.header.navigation.customers,
            url: "/tables/customers"
        },
    ];
};

/**
 * Builds the Sidebar menu items.
 * 
 * @param translations - Translations to apply for the Menu Items.
 * @returns The Sidebar menu items.
 */
export function sidebarMenuItems(translations: TranslationService): Array<MenuItem> {
    return [
        {
            id: "home",
            name: translations.keys.sidemenu.home,
            description: translations.keys.sidemenu.home,
            ariaLabel: translations.keys.sidemenu.home,
            icon: "home",
            url: "/home"
        }
    ];
};
```

#### Providing menus to other components ####

Although we load our translations in a static way, you could also load them from other data sources. So we can define a 
small abstraction ``MenuService`` for providing the menu:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Injectable } from "@angular/core";
import { Observable, of } from "rxjs";
import { dropDownItems as dropDownMenuItems, headerMenuItems, sidebarMenuItems } from "../data/app-menu-items";
import { MenuItem } from "../models/menu-item";
import { TranslationService } from "./translation.service";

/**
 * Provides all Menu-related functionality.
 */
@Injectable({
    providedIn: `root`
})
export class MenuService {

    /**
     * Builds a new ``MenuService``.
     * 
     * @param translationService - Translations to apply.
     */
    constructor(private translationService: TranslationService) { }

    /**
     * Generates an ``Observable<MenuItem>`` for the page header.
     * 
     * @returns An ``Observable<MenuItem>`` with the available items.
     */
    public header(): Observable<MenuItem[]> {
        const menuItems = headerMenuItems(this.translationService);
        
        return of<MenuItem[]>(menuItems);
    }

    /**
     * Generates an ``Observable<MenuItem>`` for the page header dropdown.
     * 
     * @returns An ``Observable<MenuItem>`` with the available items.
     */
     public dropdown(): Observable<MenuItem[]> {

        const menuItems: Array<MenuItem> =  dropDownMenuItems(this.translationService);
        
        return of<MenuItem[]>(menuItems);
    }

    /**
     * Generates an ``Observable<MenuItem>`` for the side bar.
     * 
     * @returns An ``Observable<MenuItem>`` with the available items.
     */
     public sidenav(): Observable<MenuItem[]> {
        
        const menuItems = sidebarMenuItems(this.translationService);

        return of<MenuItem[]>(menuItems);
    }
}
```

### Application Container  ###

The application should be a *desktop-first* application. We want a side menu, that allows us to have a menu in a classic 
tree structure. Sorry, no Hamburgers here! To allow fast access of important data, you want to have a header menu, that 
contains a few links only. And finally you want a Drop Down in the Header for things like Settings.

The ``AppComponent`` is the entry point for the application. It defines the frame, which all other components will 
be rendered into. It takes a dependency on the ``TranslationService``, so the translations are initialized once 
the application loads.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Component, OnInit } from '@angular/core';
import { Observable, of } from 'rxjs';
import { MenuItem } from './models/menu-item';
import { MenuService } from './services/menu.service';
import { TranslationService } from './services/translation.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {

  sidenavMenu$: Observable<MenuItem[]> = of([]);
  headerMenu$: Observable<MenuItem[] >= of([]);
  dropdownMenu$: Observable<MenuItem[]> = of([]);

  constructor(public menuItemService: MenuService, public translations: TranslationService) {
  }

  ngOnInit(): void {
    this.sidenavMenu$ = this.menuItemService.sidenav();
    this.headerMenu$ = this.menuItemService.header();
    this.dropdownMenu$ = this.menuItemService.dropdown();
  }

  getChildren(menuItem: MenuItem): MenuItem[] | undefined {
    return menuItem.children;
  }
}
```

And in the template we are defining the website layout, with a header and side navigation. We are using the 
``MenuService`` to generate the menu items and the ``TranslationService`` to translate all other labels. All 
child components go into the ``<router-outlet>``.

```html
<div class="main-container">
    <header class="header header-6">
        <div class="branding">
          <cds-icon shape="world" size="md"></cds-icon>
            <a href="javascript://" class="nav-link">
              <span class="title">{{translations.keys.header.title}}</span>
            </a>
          </div>
          <div class="header-nav">
              <ng-container *ngIf="headerMenu$ | async as headerMenuItems">
                <a *ngFor="let headerMenuItem of headerMenuItems" class="nav-link nav-text" [routerLink]="headerMenuItem.url">{{headerMenuItem.name}}</a>
              </ng-container>
          </div>
          <div class="header-actions">
            <clr-dropdown [clrCloseMenuOnItemClick]="false">
                <button clrDropdownTrigger class="me-1" aria-label="Dropdown">
                    <cds-icon shape="cog" class="me-1" size="md"></cds-icon>         
                    <cds-icon shape="angle"  direction="down"></cds-icon>
                </button>
                <clr-dropdown-menu *clrIfOpen clrPosition="bottom-right" >
                  <label class="dropdown-header" aria-hidden="true">{{translations.keys.dropdown.title}}</label>
                  <ng-container *ngIf="dropdownMenu$ | async as dropdownMenu">
                    <div *ngFor="let dropdownMenuItem of dropdownMenu" [attr.aria-label]="dropdownMenuItem.ariaLabel" clrDropdownItem>{{dropdownMenuItem.name}}</div>
                    </ng-container>
                </clr-dropdown-menu>
              </clr-dropdown>
          </div>
    </header>
    <div class="content-container">
        <nav class="sidenav m-2">
            <section *ngIf="sidenavMenu$ | async as sidenavMenuItems" class="sidenav-content">
              <clr-tree>
                <clr-tree-node [clrExpanded]="true" *clrRecursiveFor="let sidenavMenuItem of sidenavMenuItems;getChildren: getChildren">
                  <a class="clr-treenode-link" [routerLink]="sidenavMenuItem.url" routerLinkActive="active" >{{sidenavMenuItem.name}}</a>
                </clr-tree-node>
              </clr-tree>

            </section>
        </nav>
        <div class="content-area">
            <router-outlet></router-outlet>
        </div>
    </div>
</div>
```

## Integrating OData into the Application ##

### Modelling OData Responses in TypeScript ###

We start the OData integration by defining what an OData response looks like and how it is constructed from the Angular 
``HttpResponse``. We will create a file ``models/odata-response.ts`` with the following content:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpResponse } from "@angular/common/http";

/**
 * Base class for all OData Responses.
 */
export abstract class ODataResponse {

    /**
     * The HTTP Status Code, such as ``200`` (OK) or ``404`` (Not Found).
     */
    public readonly status: number;

    /**
     * The Response Headers.
     */
    public readonly headers: Array<[string, string | null]>;

    /**
     * The ``Map<string, any>``, that holds the OData Metadata.
     */
    public readonly metadata: Map<string, any>;

    /**
     * Initialized common data for all ``ODataResponse`` implementations, such as 
     * status, headers and metadata.
     * 
     * @param response - Response returned by the Webservice
     */
    constructor(response: HttpResponse<any>) {
        this.status = response.status;
        this.headers = response.headers.keys().map(k => [k, response.headers.get(k)])
        this.metadata = this.getMetadata(response.body);
    }

    /**
     * Builds up the OData Metadata, which are basically all keys prefixed with ``@odata``.
     * 
     * @param data - The untyped response body
     * @returns A map of Metadata
     */
    private getMetadata(data: any): Map<string, any> {
        const metadata = new Map<string, any>();
        Object.keys(data)
            .filter((key) => key.startsWith("@odata"))
            .forEach((key) => metadata.set(key.replace("@odata.", ""), data[key]));
        return metadata;
    }
};

/**
 * An OData response containing a single entity, such as a lookup by ID.
 */
export class ODataEntityResponse<T> extends ODataResponse {

    /**
     * An entity of type ``T`` or ``null``, if the response didn't return data.
     */
    public readonly entity: T | null;

    /**
     * Constructs a new ``ODataEntityResponse`` by parsing the response body.
     * 
     * @param response - The HTTP Response.
     */
    constructor(response: HttpResponse<any>) {
        super(response);

        this.entity = this.getEntity(response.body);
    }

    /**
     * Returns the entity of type ``T`` or ``null``.
     * 
     * @param data - The untyped response body
     * @returns Entity of type ``T``
     */
    private getEntity(data: any): T{

        let entity = {} as T;
        
        Object.keys(data)
            .filter((key) => !key.startsWith("@odata"))
            .forEach((key) => entity[key as keyof T] = data[key]);

        return entity;
    }
}

/**
 * Returns an entities array of type ``T``.
 */
export class ODataEntitiesResponse<T> extends ODataResponse {

    public readonly entities: T[];

    /**
     * Constructs a new ``ODataEntityResponse`` by parsing the response body.
     * 
     * @param response - The HTTP Response.
     */
     constructor(response: HttpResponse<any>) {
        super(response);

        this.entities = this.getEntities(response.body);
    }

    /**
     * Returns an array entities of type ``T`` returned by the OData-enabled endpoint.
     * 
     * @param data - The untyped response body
     * @returns Array of type ``T`` elements
     */
    private  getEntities(data: any): T[] {
        const keys = Object.keys(data).filter((key) => !key.startsWith("@odata"));
        if (keys.length === 1 && keys[0] === "value") {
            return (data.value as T[]);
        }
        return [];
    }
}
```

### ODataService: Enable components to run OData queries ###

Now that we know the shape of our response, we can define an ``ODataService`` to query the API for a single entity or an array of entities:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { map, Observable } from "rxjs";
import { ODataEntitiesResponse, ODataEntityResponse } from "../models/odata-response";

/**
 * The ``ODataService`` provides functionality to query an OData-enabled 
 * endpoint and parse the HTTP response to a type-safe entity and its 
 * metadata.
 */
@Injectable({
    providedIn: `root`
})
export class ODataService {

    /**
     * Constructs an ``ODataService``.
     * 
     * @param httpClient - The ``HttpClient`` to be used for queries.
     */
    constructor(private httpClient: HttpClient) {
    }

    /**
     * Queries a OData-enabled enpoint for a single entity of type ``T``. The 
     * response also contains all metadata of the response data.
     *
     * @typeParam T - Type of the entity
     * @param url - URL for an OData-enabled enpoint
     * @returns Response containing metadata and entity
     */
    getEntity<T>(url: string): Observable<ODataEntityResponse<T>> {
        return this.httpClient
            .get<any>(url, { observe: 'response' } )
            .pipe(map(response => new ODataEntityResponse<T>(response)));
    }

    /**
     * Queries a OData-enabled enpoint for a entities of type ``T``. The response also 
     * contains all metadata of the response data.
     *
     * @typeParam T - Type of the entity
     * @param url - URL for an OData-enabled enpoint
     * @returns Response containing metadata and entities
     */
     getEntities<T>(url: string): Observable<ODataEntitiesResponse<T>> {
        return this.httpClient
            .get<any>(url, { observe: 'response' } )
            .pipe(map(response => new ODataEntitiesResponse<T>(response)));
    }
}
```

And that's it already for the mapping the OData queries. There is no fancy builder to abstract away the ``$expand`` and ``$select`` 
query parameters. Writing them by hand for your use cases makes absolutely everything much easier, implementation-wise... a little 
bit of code duplication is better than an expensive abstraction!

### Implementing a Filter API  ###

We will use a the Clarity Datagrid to expose data from OData-endpoints and to allow filtering:

* [https://clarity.design/documentation/datagrid/structure](https://clarity.design/documentation/datagrid/structure)

So the "Filter API" will be built in a way, that's compatible with the Clarity Datagrid. 

The idea is, that you have Filters of various types (``Numeric``, ``String``, ``Date``, ``Boolean``, ...) and 
Filter operators (``StartsWith``, ``EndsWith``, ...). A ``ColumnFilter`` will be implemented by a custom Clarity 
Datagrid filter as described in:

* [https://clarity.design/documentation/datagrid/custom-filtering](https://clarity.design/documentation/datagrid/custom-filtering)

That way we can get the state of the Datagrid (``ClrDatagridStateInterface<T>``) and the columns will return their OData representations.

#### Filter Types ####

All Filters in our application should use a specific type, such as being a filter for numerics, for dates or booleans. We describe 
these in an enumeration ``FilterType``.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

/**
 * Each Filter has a Type.
 */
export enum FilterType {
    NumericFilter = "numericFilter",
    StringFilter = "stringFilter",
    DateFilter = "dateFilter",
    BooleanFilter = "booleanFilter",
};
```

#### Filter Operators ####

All Filters share a common set of Operators. Something like ``IsNull`` applies for strings, dates or numeric values. We 
define the entire set of available operators in an enumeration ``FilterOperator``.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

/**
 * All Filters share a common set of FilterOperators, such as "Greater Than"...
 */
export enum FilterOperator {
    None = "none",
    Before = "before",
    After = "after",
    IsEqualTo = "isEqualTo",
    IsNotEqualTo = "isNotEqualTo",
    Contains = "contains",
    NotContains = "notContains",
    StartsWith = "startsWith",
    EndsWith = "endsWith",
    IsNull = "isNull",
    IsNotNull = "isNotNull",
    IsEmpty = "isEmpty",
    IsNotEmpty = "isNotEmpty",
    IsGreaterThanOrEqualTo = "isGreaterThanOrEqualTo",
    IsGreaterThan = "isGreaterThan",
    IsLessThanOrEqualTo = "isLessThanOrEqualTo",
    IsLessThan = "isLessThan",
    BetweenInclusive = "betweenInclusive",
    BetweenExclusive = "betweenExclusive",
    Yes = "yes",
    No = "no",
    All = "all"
};
```

#### Column Filters ####

A columns in a Datagrid can have a filter. This Filter is applied on a field and has a filter operator, such as 
``IsNull`` or ``StartsWith``. A column filter maybe applied and needs to know how to reset itself to an initial 
state.

The method ``ColumnFilter#toODataFilter`` returns the OData Filter, that's needed to construct OData queries.

```
/**
 * A Column Filter is applied to a field and knows 
 */
export interface ColumnFilter {

    /**
     * Field to apply the Filter on.
     */
    field: string;

    /**
     * Filter operator, such as "IsNull", "StartsWith", ...
     */
    filterOperator: FilterOperator;

    /**
     * Applies the Filter.
     */
    applyFilter(): void;

    /**
     * Resets the Filter.
     */
    resetFilter(): void;

    /**
     * Returns the OData Filter.
     */
    toODataFilter(): ODataFilter;
}
```

#### ODataFilter for OData queries ####

An ``ODataFilter`` is used to translate the current Filter into an OData query string. It is basically the 
same interface like a ``ColumnFilter``, so I suspect they could be merged. But I am not sure, so I leave them 
as separate models.

By using the ``ODataFilter#toODataString`` method an ``ODataFilter`` can be translated into an OData query string.

```typescript
/**
 * Every OData Filter is applied to a field and provides a way to serialize itself into the OData Format.
 */
export interface ODataFilter {

    /**
     * Field to apply the Filter on.
     */
    field: string;

    /**
     * The Filter operator, such as "IsNull", "StartsWith", ...
     */
    operator: FilterOperator;

    /**
     * Serializes the ODataFilter as a string.
     */
    toODataString(): string | null;
};
```

One of its implementation is an ``ODataStringFilter``:

```typescript
/**
 * OData Filter on a String field.
 */
export class ODataStringFilter implements ODataFilter {

    /**
     * Field to apply the Filter on.
     */
    field: string;
    
    /**
     * Operator to filter for.
     */
    operator: FilterOperator;

    /**
     * The Value to filter.
     */
    value: string | null;

    /**
     * Constructs a new ``StringFilter``.
     * 
     * @param field - Field to apply the Filter on.
     * @param operator - Operator to filter for, such as "IsNull", "StartsWith", ...
     * @param value - The Value to filter for.
     */
    constructor(field: string, operator: FilterOperator, value: string | null) {
        this.field = field;
        this.operator = operator;
        this.value = value;
    }

    /**
     * Converts this Filter to an OData string.
     * 
     * @returns OData filter string for the field.
     */
    toODataString(): string | null {

        if (this.operator == FilterOperator.None) {
            return null;
        }
   
        switch (this.operator) {
            case FilterOperator.IsNull:
                return `${this.field} eq null`;
            case FilterOperator.IsNotNull:
                return `${this.field} ne null`;
            case FilterOperator.IsEqualTo:
                return `${this.field}  eq '${this.value}'`;
            case FilterOperator.IsNotEqualTo:
                return `${this.field} neq '${this.value}'`;
            case FilterOperator.IsEmpty:
                return `(${this.field} eq null) or (${this.field} eq '')`
            case FilterOperator.IsNotEmpty:
                return `(${this.field} ne null) and (${this.field} ne '')`
            case FilterOperator.Contains:
                return `contains(${this.field}, '${this.value}')`;
            case FilterOperator.NotContains:
                return `indexof(${this.field}, '${this.value}') eq -1`;
            case FilterOperator.StartsWith:
                return `startswith(${this.field}, '${this.value}')`;
            case FilterOperator.EndsWith:
                return `endswith(${this.field}, '${this.value}')`;
            default:
                throw new Error(`${this.operator} is not supported`);
        }
    }
}
```

### Extending the Clarity Datagrid with OData Filters ###

We can then implement the Components to integrate our Filters into the Clarity Datagrid, such as a ``StringFilterComponent``. 

You can learn about custom filtering in Clarity at:

* [https://clarity.design/documentation/datagrid/custom-filtering](https://clarity.design/documentation/datagrid/custom-filtering)

To simplify implementation, we are only implementing it for Server-side Filtering. If you want to implement Client-side 
filtering, you need to implement the ``ClrDatagridFilterInterface#accepts(item: any)`` method to filter elements.

#### Implementing a Custom Filter ####

All custom filters for a Clarity Datagrid need to implement the ``ClrDatagridFilterInterface<T>`` interface. Our 
OData-enabled filters also need to implement the ``ColumnFilter`` of our very own "Filter API". 

Here is a ``StringFilter`` component, that can be used as a starting point. The repository implements more 
filters, such as for Numeric and Date Ranges.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { AfterViewInit, Component, Input } from "@angular/core";
import { ClrDatagridFilter, ClrDatagridFilterInterface, ClrPopoverEventsService } from "@clr/angular";
import { Subject } from "rxjs";
import { ODataFilter, FilterOperator, FilterType, ColumnFilter, ODataStringFilter } from "src/app/models/filter";
import { TranslationService } from "src/app/services/translation.service";

/**
 * A Filter for search string values.
 */
@Component({
    selector: 'app-string-filter',
    template: `
        <form clrForm clrLayout="horizontal"  clrLabelSize="4">
        <clr-select-container>
                <label>{{translations.keys.filters.numericFilter.labelOperator}}</label>
                <select clrSelect name="operators" [(ngModel)]="filterOperator">
                    <option *ngFor="let operator of filterOperators" [value]="operator">{{translations.keys.filterOperators[operator]}}</option>
                </select>
            </clr-select-container>
            <clr-input-container>
                <label>{{translations.keys.filters.numericFilter.labelValue}}</label>
                <input clrInput [placeholder]="translations.keys.filters.stringFilter.placeholder" name="input" [(ngModel)]="search" 
                    [disabled]="filterOperator === 'none' || filterOperator === 'isNull' || filterOperator === 'isNotNull' || filterOperator === 'isEmpty' || filterOperator === 'isNotEmpty'" />
            </clr-input-container>
            <div class="clr-row filter-actions">
                <div class="clr-col">
                    <button class="btn btn-primary btn-block" (click)="applyFilter()">{{translations.keys.filters.applyFilter}}</button>
                </div>
                <div class="clr-col">
                    <button class="btn btn-block" (click)="resetFilter()">{{translations.keys.filters.resetFilter}}</button>
                </div>
            </div>
        </form>
    `,
    styles: ['.filter-actions { margin-top: 1.2rem; }']
})
export class StringFilterComponent implements ClrDatagridFilterInterface<any>, ColumnFilter, AfterViewInit  {

    /**
     * Filter operators valid for the component.
     */
    readonly filterOperators: FilterOperator[] = [
        FilterOperator.None,
        FilterOperator.IsNull, 
        FilterOperator.IsNotNull, 
        FilterOperator.IsEmpty, 
        FilterOperator.IsNotEmpty, 
        FilterOperator.IsEqualTo, 
        FilterOperator.IsNotEqualTo, 
        FilterOperator.Contains, 
        FilterOperator.NotContains, 
        FilterOperator.StartsWith, 
        FilterOperator.EndsWith,
    ];

    /**
     * The name of the field, which has to match the model.
     */
    @Input()
    field!: string;
 
     /**
      * The Filter operator selected by the user.
      */
    @Input()
    filterOperator: FilterOperator = FilterOperator.None;
 

    /**
     * Search Value entered by the user.
     */
    @Input()
    search: string | null = null;

    /**
     * Required by the ``ClrDatagridFilterInterface`` so the Datagrid knows something has changed.
     */
    changes = new Subject<any>();

    /**
     * Creates a new ``StringFilterComponent``.
     * 
     * @param filterContainer - The Clarity Datagrid ``ClrDatagridFilter`` filter container to register to
     * @param translations - Translations to be used in the component.
     * @param clrPopoverEventsService - The popover service to control the behavior of the popout.
     */
    constructor(private filterContainer: ClrDatagridFilter, public translations: TranslationService, private clrPopoverEventsService: ClrPopoverEventsService) {
        filterContainer.setFilter(this);
    }

    /**
     * Applies the Filter.
     */
    applyFilter(): void {
        this.changes.next(null);
    }
    
    /**
     * Resets the Filter.
     */
    resetFilter(): void {
        this.filterOperator = FilterOperator.None;
        this.search = null;

        this.changes.next(null);
    }

    /**
     * Returns ``true`` if this Filter is enabled.
     * 
     * @returns ``true`` if the Filter is valid.
     */
    isActive(): boolean {
        return this.filterOperator !== FilterOperator.None;
    }

    /**
     * This method needs to be implemented for Client-side Filtering. We will do all 
     * filtering on Server-side and just pipe everything through here.
     * 
     * @param item - Item to Filter for
     * @returns At the moment this method only returns ``true``
     */
    accepts(item: any): boolean {
        return true;
    }
    
    /**
     * Turns this component into an ``ODataFilter``.
     * 
     * @returns The OData Filter for the component.
     */
    toODataFilter(): ODataFilter {
        return new ODataStringFilter(this.field, this.filterOperator, this.search);
    }

    /**
     * After the Component has been initialized we need to tell its ``ClrPopoverEventsService`` to 
     * not close, when the User has accidentally clicked outside the filter. And if the Filter has been 
     * initialized, we tell the Datagrid to refresh the filters.
     */
     ngAfterViewInit() {
		this.clrPopoverEventsService.outsideClickClose = false;

        if(this.filterOperator != FilterOperator.None) {
            this.applyFilter();
        }
	}
}
```

#### From Datagrid state to an OData Query ####

These filters can then be used to build an OData string for the current Datagrid's state. The class ``ODataUtils#asODataString`` 
takes the Datagrid state to set the ``$filter``, ``$sort``, ``$top``, ``$skip`` and ``$count`` query parameters. Optionally the 
``$select`` and ``$expand`` parameters can be added.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { HttpParams } from "@angular/common/http";
import { ClrDatagridStateInterface } from "@clr/angular";
import { ColumnFilter, ODataFilter } from "../models/filter";
import { HttpQueryParamType } from "../types/type-utils";
import { StringUtils } from "./string-utils";

/**
 * Utilities for working with OData Data Sources.
  */
export class ODataUtils {

    /**
     * Serializes a ``ClrDatagridStateInterface`` into an OData query with filters,
     * pagination and sort parameters. The result will also include a $count to get 
     * the total result set size.
     *
     * @param endpoint - OData-enabled endpoint we are querying.
     * @param state - The State of the DataGrid.
     * @param params - Addition $select and $expand parameters.
     * @returns OData query with Sorting, Filters and Pagination. 
     */
     public static asODataString(endpoint: string, state: ClrDatagridStateInterface, params: Partial<{ $select?: string, $expand?: string }>): string {

        const httpQueryParameters: HttpQueryParamType = {
            ...this.getSelectParameter(params.$select),
            ...this.getExpandParameter(params.$expand),
            ...this.toODataFilterStatements(state),
            ...this.getPaginationParameters(state),
            ...this.getSortParameters(state),
            ...{ "$count": true }
        };

        const httpParameters: HttpParams = new HttpParams().appendAll(httpQueryParameters);

        if (StringUtils.isNullOrWhitespace(httpParameters.toString())) {
            return endpoint;
        }

        return `${endpoint}?${httpParameters.toString()}`;
    }

    /**
     * Returns the $select part of the OData query.
     *
     * @param select - The raw select string.
     * @returns The OData $select statement.
     */
    private static getSelectParameter(select?: string): HttpQueryParamType {

        if(!select) {
            return {};
        }

        return { "$select": select };
    }

     /**
     * Returns the $select part of the OData query.
     *
     * @param select - The raw select string.
     * @returns The OData $select statement.
     */
         private static getExpandParameter(expand?: string): HttpQueryParamType {
            if(!expand) {
                return {};
            }
    
            return { "$expand": expand };
        }

    /**
     * Serializes the filters of a ``ClrDatagridStateInterface`` into a ``HttpQueryParamType``, containing 
     * the ``$filter`` statements of an OData query.
     *
     * @param clrDataGridState - The state of the DataGrid.
     * @returns The OData $filter parameters.
     */
    private static toODataFilterStatements(clrDataGridState: ClrDatagridStateInterface): HttpQueryParamType {

        // Get all OData Filters from the Grid:
        const filters: ODataFilter[] = ODataUtils.castToODataFilters(clrDataGridState);

        // Serialize the to OData strings:
        const serializedFilters = ODataUtils.serializeAllFilters(filters);

        if (!serializedFilters) {
            return {};
        }

        return {
            "$filter": serializedFilters
        };
    }

    /**
     * Gets the ``ODataFilter[]`` from the ``ClrDatagridStateInterface#filter`` property.
     *
     * @param clrDataGridState - An array of ``ODataFilter``.
     * @returns The OData $filter value.
     */
    private static castToODataFilters(clrDataGridState: ClrDatagridStateInterface): ODataFilter[] {

        if (!clrDataGridState.filters) {
            return [];
        }

        return clrDataGridState.filters
            .filter(filter => (filter as ColumnFilter).toODataFilter) // Typescript has no "instanceof", so use some duck typing...
            .map(filterProvider => filterProvider.toODataFilter());
    }

    /**
     * Serializes all $filter statement generated by a given array of ``ODataFilter``.
     *
     * @param filters - An array of ``ODataFilter``.
     * @returns The OData $filter value.
     */
    private static serializeAllFilters(filters: ODataFilter[]): string {
        // Serialize the Filters:
        return filters
            // Format as OData string:
            .map((filter) => filter.toODataString())
            // There may be empty OData-strings:
            .filter(filter => !StringUtils.isNullOrWhitespace(filter))
            // Wrap it in parentheses, so concatenating filters doesn't lead to problems:
            .map((filter) => `(${filter})`)
            // Concat all Filters with AND:
            .join(' and ');
    }

    /**
     * Returns the optional OData $sort parameter.
     *
     * @param clrDataGridState - The state of the Data Grid.
     * @returns The OData $orderby statement.
     */
    private static getSortParameters(clrDataGridFilter: ClrDatagridStateInterface): HttpQueryParamType {

        if (!clrDataGridFilter.sort) {
            return {};
        }

        const by: string = clrDataGridFilter.sort.by.toString();

        if (StringUtils.isNullOrWhitespace(by)) {
            return {};
        }

        const result: HttpQueryParamType = {};

        if (clrDataGridFilter.sort.reverse) {
            result["$orderby"] = `${by} desc`;
        } else {
            result["$orderby"] = `${by}`;
        }

        return result;
    }

    /**
     * Gets the optional Pagination parameters ``$top`` and ``$skip``.
     *
     * @param clrDataGridState - The state of the Data Grid.
     * @returns The OData ``$top`` and ``$skip`` statements.
     */
    private static getPaginationParameters(clrDataGridFilter: ClrDatagridStateInterface): HttpQueryParamType {

        const page = clrDataGridFilter.page;

        if (!page) {
            return {};
        }

        const result: HttpQueryParamType = {};

        if (page.size) {
            result["$top"] = page.size;
        }

        if (page.current && page.size) {
            result["$skip"] = (page.current - 1) * page.size;
        }

        return result;
    }
}
```

And that's it for filtering!

## Querying the WideWorldImporters Backend ##

With all the infrastructure code in place, we can finally, finally query the data. 

As an example I will show how to query for cities and also include values of expanded entities: 

* ``stateProvince``
    * Information about the city's state. 
* ``lastEditedByNavigation`` 
    * Person that was modifying the city.

### Generating the WideWorldImporters TypeScript model ###

If you want some kind of rapid application development, then you don't want to type your entity data model by 
hand. And why should you do that? In the last article we have already built an OpenAPI document, that describes 
the schema of the data.

So I start by downloading *NSwagStudio* from:

* [https://github.com/RicoSuter/NSwag/wiki/NSwagStudio](https://github.com/RicoSuter/NSwag/wiki/NSwagStudio)

On the starting page I set the path to the OpenAPI Document (``http://localhost:5000/odata/$swagger``) and configure it like this:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/09_NSwagStudio_TypeScript.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/09_NSwagStudio_TypeScript.jpg" alt="Generating TypeScript contracts with NSwagStudio">
    </a>
</div>

And then we can see how it generates all these beautiful TypeScript classes:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/10_NSwagStudio_TypeScript_Results.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/10_NSwagStudio_TypeScript_Results.jpg" alt="The TypeScript interfaces generated by NSwagStudio">
    </a>
</div>

I'll just copy and paste these to the Frontend into a class ``app/models/entities.ts``. 👍

### Displaying the Customer data ###

The component code is very concise and basically boils down to getting a ``ClrDatagridStateInterface``, then 
using the ``ODataUtils`` and finally using the ``ODataService`` to query the WideWorldImporters backend. To 
translate column names a ``TranslationService`` gets injected to the component.

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { Component } from '@angular/core';
import { ClrDatagridStateInterface } from '@clr/angular';
import { ODataEntitiesResponse } from 'src/app/models/odata-response';
import { City } from 'src/app/models/entities';
import { ODataService } from 'src/app/services/odata-service';
import { TranslationService } from 'src/app/services/translation.service';
import { ODataUtils } from 'src/app/utils/odata-utils';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-cities-table',
  templateUrl: 'app-cities-table.component.html',
})
export class CitiesTableComponent {

  loading: boolean = true;
  filterOpen: boolean = false;
  tableData: ODataEntitiesResponse<City> | null;

  constructor(public odataService: ODataService, public translations: TranslationService) {
    this.tableData = null;
  }

  refresh(state: ClrDatagridStateInterface) {
    
    const query = ODataUtils.asODataString(`${environment.baseUrl}/Cities`, state, { $expand: "stateProvince, lastEditedByNavigation" });

    this.loading = true;

    this.odataService.getEntities<City>(query)
      .subscribe(res => {
        this.tableData = res;
        this.loading = false;
      });
  }
}
```

In the corresponding template we are adding the data grid and add our filters to each of the columns. You can see, 
that for example ``lastEditedBy`` in the filter maps to ``lastEditedByNavigation/fullName`` property of a related 
entity.

```html
<clr-datagrid  (clrDgRefresh)="refresh($event)" [clrDgLoading]="loading">
    <clr-dg-column [clrDgField]="'cityId'">
        <clr-dg-filter>
            <app-string-filter field="cityId"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.cityId }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'cityName'">
        <clr-dg-filter>
            <app-string-filter field="cityName"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.cityName }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'stateProvince'">
        <clr-dg-filter>
            <app-string-filter field="stateProvince/stateProvinceName"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.stateProvince }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'latestRecordedPopulation'">
        <clr-dg-filter>
            <app-numeric-filter field="latestRecordedPopulation"></app-numeric-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.cities.latestRecordedPopulation }}
    </clr-dg-column>
    <clr-dg-column [clrDgField]="'lastEditedBy'">
        <clr-dg-filter>
            <app-string-filter field="lastEditedByNavigation/fullName"></app-string-filter>
        </clr-dg-filter>
        {{ translations.keys.tables.countries.lastEditedBy}}
    </clr-dg-column>
    <!-- Row Binding -->
    <clr-dg-row *ngFor="let city of tableData?.entities">
        <clr-dg-cell>{{city.cityId}}</clr-dg-cell>
        <clr-dg-cell>{{city.cityName}}</clr-dg-cell>
        <clr-dg-cell>{{city.stateProvince?.stateProvinceName}}</clr-dg-cell>
        <clr-dg-cell>{{city.latestRecordedPopulation}}</clr-dg-cell>
        <clr-dg-cell>{{city.lastEditedByNavigation?.fullName}}</clr-dg-cell>
    </clr-dg-row>
    <!-- Footer -->
    <clr-dg-footer>
        <clr-dg-pagination #pagination [clrDgPageSize]="10"
            [clrDgTotalItems]="tableData?.metadata?.get('count')">
            <clr-dg-page-size [clrPageSizeOptions]="[10,20,50,100]">{{ translations.keys.core.datagrid.pagination.items_per_page }}</clr-dg-page-size>
            {{pagination.firstItem + 1}} - {{pagination.lastItem + 1}} {{ translations.keys.core.datagrid.pagination.of }} {{pagination.totalItems}}  {{ translations.keys.core.datagrid.pagination.items }}
        </clr-dg-pagination>
    </clr-dg-footer>
</clr-datagrid>
```

And the result is a beautiful data grid, that allows us to sort, filter and paginate our hearts out:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/aspnet_core_odata_example/11_Cities_Table.jpg">
        <img src="/static/images/blog/aspnet_core_odata_example/11_Cities_Table.jpg" alt="Data Grid with Cities">
    </a>
</div>

The GitHub repository contains more tables, so you get a feeling on how to work with it.

## Final Plumbing Steps ##

A little bit of plumbing is necessary to setup the Routes and the Angular Dependency Injection container.

### Setting Angular Routes ###

In the ``app-routing.module.ts`` we are defining the routes for the application:

```typescript
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CitiesTableComponent } from './components/tables/cities-table/app-cities-table.component';
import { CountriesTableComponent } from './components/tables/countries-table/app-countries-table.component';
import { CustomersTableComponent } from './components/tables/customer-table/app-customer-table.component';


const routes: Routes = [
  { path: 'tables/cities', component: CitiesTableComponent },
  { path: 'tables/countries', component: CountriesTableComponent },
  { path: 'tables/customers', component: CustomersTableComponent },
  
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
```

### Angular Module ###

And in the ``app.module.ts`` we define the application roots dependency injection container.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import { CUSTOM_ELEMENTS_SCHEMA, LOCALE_ID, NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ClarityModule } from '@clr/angular';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { CommonModule, registerLocaleData } from '@angular/common';
import localeDe from '@angular/common/locales/de';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

// CDS Web Components: 
import '@cds/core/icon/register.js';
import '@cds/core/date/register.js';
import '@cds/core/time/register.js';
import '@cds/core/input/register.js';
import '@cds/core/select/register.js';

import { ClarityIcons, cloudIcon, cogIcon, homeIcon, arrowIcon } from '@cds/core/icon';

// Filters:
import { BooleanFilterComponent } from './components/filters/boolean-filter/boolean-filter.component';
import { DateRangeFilterComponent } from './components/filters/date-range-filter/date-range-filter.component';
import { StringFilterComponent } from './components/filters/string-filter/string-filter-component.component';
import { NumericFilterComponent } from './components/filters/numeric-filter/numeric-filter-component.component';

// Components:
import { ZonedDatePickerComponent } from './components/core/zoned-date-picker.component';
import { CountriesTableComponent } from './components/tables/countries-table/app-countries-table.component';
import { CitiesTableComponent } from './components/tables/cities-table/app-cities-table.component';
import { CustomersTableComponent } from './components/tables/customer-table/app-customer-table.component';

// Add Icons used in the Application:
ClarityIcons.addIcons(homeIcon, cogIcon, cloudIcon, arrowIcon);

registerLocaleData(localeDe);

@NgModule({
  declarations: [
    AppComponent,
    // Common
    ZonedDatePickerComponent,
    // Filter
    BooleanFilterComponent,
    DateRangeFilterComponent,
    StringFilterComponent,
    NumericFilterComponent,
    // Tables
    CitiesTableComponent,
    CountriesTableComponent,
    CustomersTableComponent
  ],
  imports: [
    // Angular
    AppRoutingModule,
    BrowserModule,
    BrowserAnimationsModule,
    CommonModule,
    FormsModule,
    HttpClientModule,
    // Clarity    
    ClarityModule,
  ],
  providers: [{ provide: LOCALE_ID, useValue: 'en' }],
  bootstrap: [AppComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule { }
```

And oh... That's it already!

## Conclusion ##

I think it was very easy to build an Angular application, that uses an OData-enabled Backend to provide access to 
the data. The Clarity Design components comes with a wide range of high-quality components and has a very versatile 
Datagrid, that's easy to extend.

All this leaves you with a good basis for your own adventure with Clarity and OData-enabled Backends.

