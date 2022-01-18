title: Building a Date Picker with Timezone Support using Clarity and the Temporal API
date: 2022-01-18 20:34
tags: angular, typescript, javascript, clarity
category: angular
slug: clarity_zoned_date_time_picker
author: Philipp Wagner
summary: Building a DatePicker with Timezones in Angular.

In a personal project I wanted to learn how to work with the [Clarity Design System] in Angular, which ...

> [...] is a scalable, customizable, open source design system bolstered by the people that build with it, 
> the people we build it for, and the community that makes us who we are.

It comes with a rich set of Web Components and Angular Components and is actively maintained by VMware:

* [https://clarity.design](https://clarity.design)

[Clarity Design System]: https://clarity.design/

## What we are going to build ##

The most important and painful component in any enterprise project? A [Datagrid]. So much data is being stored 
and people **always** want to make sense of the data. Do you want to reinvent all this? There is so much to 
think of.

So while playing with the Clarity [Datagrid] I wanted to filter a date range and support Timezones. 

Here is a screenshot of the final implementation:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/clarity_zoned_date_time_picker/clarity_zoned_date_time_picker.png">
        <img src="/static/images/blog/clarity_zoned_date_time_picker/clarity_zoned_date_time_picker.png">
    </a>
</div>

I think it's a good excuse for learning about the upcoming JavaScript ``Temporal`` API.

[Datagrid]: https://clarity.design/angular-components/datagrid/

## Handling Time in JavaScript ##

Handling Dates in JavaScript is a mess, just like it's a mess in any other language. Dates are a complicated thing, just think 
of [Leap years], [Leap seconds}, [Daylight saving time], [Date formats], [Timezones], ... and what if you suddenly need to 
convert your Gregorian Calendar-based Date to the [Japanese Calendar]?

There's a reason libraries for handling temporal things exist... because it takes superpowers get it right.

At the moment, there is a proposal for ECMAScript, which 

* [https://github.com/tc39/proposal-temporal](https://github.com/tc39/proposal-temporal)

> Date has been a long-standing pain point in ECMAScript. This is a proposal for Temporal, a global Object that acts as a top-level namespace (like Math), 
> that brings a modern date/time API to the ECMAScript language. For a detailed look at some of the problems with Date, and the motivations for Temporal, 
> see: Fixing JavaScript Date.
>
> Temporal fixes these problems by:
> 
> * Providing easy-to-use APIs for date and time computations
> * First-class support for all time zones, including DST-safe arithmetic
> * Dealing only with objects representing fixed dates and times
> * Parsing a strictly specified string format
> * Supporting non-Gregorian calendars
>
> Temporal provides separate ECMAScript classes for date-only, time-only, and other scoped use cases. This makes code more readable and prevents bugs caused by incorrectly assuming 0, UTC, or the local time zone for values that are actually unknown.

[Leap years]: https://en.wikipedia.org/wiki/Leap_year
[Leap seconds]: https://en.wikipedia.org/wiki/Leap_second
[Daylight Saving Time]: https://en.wikipedia.org/wiki/Daylight_saving_time
[Date formats]: https://en.wikipedia.org/wiki/Date_format_by_country
[Timezones]: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
[Japanese Calendar]: https://en.wikipedia.org/wiki/Japanese_calendar

## Let's start - Polyfill and defining the Supported Timezones ##

We start by installing the ``Temporal`` Polyfill, which gives us access to a ``ZonedDateTime``:

```
npm install @js-temporal/polyfill
```

Next we are defining a very simple interface ``AppTimeZone``, which models a Timezone identifier and a text:

```typescript
export interface AppTimeZone {
    timeZone: string;
    text: string;
};
```

Next we define the default Timezone of the application:

```typescript
export const appTimeZone: string = "Europe/Berlin";
```

... and create a list of all the supported timezones and a description:

```typescript
export const appTimeZones: AppTimeZone[] = [
    { timeZone: "Etc/GMT+12", text: "(UTC-12:00) International Date Line West" },
    { timeZone: "Pacific/Midway", text: "(UTC-11:00) Midway Island, Samoa" },
    { timeZone: "Pacific/Honolulu", text: "(UTC-10:00) Hawaii" },
    { timeZone: "US/Alaska", text: "(UTC-09:00) Alaska" },
    { timeZone: "America/Los_Angeles", text: "(UTC-08:00) Pacific Time (US & Canada)" },
    { timeZone: "US/Arizona", text: "(UTC-07:00) Arizona" },
    { timeZone: "America/Managua", text: "(UTC-06:00) Central America" },
    { timeZone: "US/Central", text: "(UTC-06:00) Central Time (US & Canada)" },
    { timeZone: "America/Bogota", text: "(UTC-05:00) Bogota, Lima, Quito, Rio Branco" },
    { timeZone: "US/Eastern", text: "(UTC-05:00) Eastern Time (US & Canada)" },
    { timeZone: "Canada/Atlantic", text: "(UTC-04:00) Atlantic Time (Canada)" },
    { timeZone: "America/Argentina/Buenos_Aires", text: "(UTC-03:00) Buenos Aires, Georgetown" },
    { timeZone: "America/Noronha", text: "(UTC-02:00) Mid-Atlantic" },
    { timeZone: "Atlantic/Azores", text: "(UTC-01:00) Azores" },
    { timeZone: "Etc/Greenwich", text: "(UTC+00:00) Dublin, Edinburgh, Lisbon, London" },
    { timeZone: "Europe/Berlin", text: "(UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna" },
    { timeZone: "Europe/Helsinki", text: "(UTC+02:00) Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius" },
    { timeZone: "Europe/Moscow", text: "(UTC+03:00) Moscow, St. Petersburg, Volgograd" },
    { timeZone: "Asia/Tehran", text: "(UTC+03:30) Tehran" },
    { timeZone: "Asia/Yerevan", text: "(UTC+04:00) Yerevan" },
    { timeZone: "Asia/Kabul", text: "(UTC+04:30) Kabul" },
    { timeZone: "Asia/Yekaterinburg", text: "(UTC+05:00) Yekaterinburg" },
    { timeZone: "Asia/Karachi", text: "(UTC+05:00) Islamabad, Karachi, Tashkent" },
    { timeZone: "Asia/Calcutta", text: "(UTC+05:30) Chennai, Kolkata, Mumbai, New Delhi" },
    { timeZone: "Asia/Katmandu", text: "(UTC+05:45) Kathmandu" },
    { timeZone: "Asia/Dhaka", text: "(UTC+06:00) Astana, Dhaka" },
    { timeZone: "Asia/Rangoon", text: "(UTC+06:30) Yangon (Rangoon)" },
    { timeZone: "Asia/Bangkok", text: "(UTC+07:00) Bangkok, Hanoi, Jakarta" },
    { timeZone: "Asia/Hong_Kong", text: "(UTC+08:00) Beijing, Chongqing, Hong Kong, Urumqi" },
    { timeZone: "Asia/Seoul", text: "(UTC+09:00) Seoul" },
    { timeZone: "Australia/Adelaide", text: "(UTC+09:30) Adelaide" },
    { timeZone: "Australia/Canberra", text: "(UTC+10:00) Canberra, Melbourne, Sydney" },
    { timeZone: "Asia/Magadan", text: "(UTC+11:00) Magadan, Solomon Is., New Caledonia" },
    { timeZone: "Pacific/Auckland", text: "(UTC+12:00) Auckland, Wellington" },
    { timeZone: "Pacific/Tongatapu", text: "(UTC+13:00) Nuku'alofa" },
];
```

It's also useful to know, if a given Timezone is supported by both, the application and the library itself. So 
let's define a function for this:

```typescript
export function isTimeZoneSupported(appTimeZones: AppTimeZone[], timeZone: string): boolean {

    const isInTzDatabase = (timeZone: string) => {
        try {
            Temporal.TimeZone.from(timeZone);

            return true;
        } catch {
            return false;
        }
    };

    const isInAppTimeZones = (timeZone: string) => {
        return appTimeZones.some(appTimeZone => {
            return appTimeZone.timeZone == timeZone;
        });
    };

    return isInTzDatabase(timeZone) && isInAppTimeZones(timeZone);
}
```

## Configuring the ZonedDatePicker - the ZonedDatePickerConfiguration ###

What is the default timezone, if no initial ``ZonedDateTime`` has been passed to the component? Which Timezones can a user select? So we start 
by defining an interface ``ZonedDatePickerConfiguration``, that will model the configuration for the DateTime Picker:

```typescript
export interface ZonedDatePickerConfiguration {
    labels: {
        labelDate: string,
        labelTime: string,
        labelTimeZone: string
    },
    defaultTimeZone: string,
    supportedTimeZones: AppTimeZone[],
};
```

And the ``DefaultZonedDatePickerConfiguration`` holds sane default values:

```typescript
export class DefaultZonedDatePickerConfiguration implements ZonedDatePickerConfiguration {
    labels = { 
        labelDate: "Date",
        labelTime: "Time",
        labelTimeZone: "Timezone"
    };
    defaultTimeZone: string = appTimeZone;
    supportedTimeZones: AppTimeZone[] = appTimeZones;
};
```

## Implementing the ZonedDatePicker - the ZonedDatePickerComponent ##

The Angular component uses the Clarity WebComponents. So we first install the ``@cds/core`` package, to we get access to all Clarity Web Components:

```
npm install @cds/core
```

In the ``app.module.ts`` we are importing the required Web Components for our Angular component:

```typescript
// CDS WebComponents: 
import '@cds/core/date/register.js';
import '@cds/core/time/register.js';
import '@cds/core/input/register.js';
import '@cds/core/select/register.js';
```

And in a ``zoned-date-time-picker.component.ts`` we can finally implement the component:

```typescript
import { Component, EventEmitter, Input, OnInit, Output } from "@angular/core";
import { Temporal } from '@js-temporal/polyfill';
import { DefaultZonedDatePickerConfiguration, isTimeZoneSupported, ZonedDatePickerConfiguration } from "src/app/data/app-timezones";

@Component({
    selector: 'app-date-picker',
    template: `
        <div cds-layout="vertical gap:lg">
            <cds-input-group layout="vertical" control-width="shrink">
                <cds-date>
                    <label>{{zonedDateTimePickerConfiguration.labels.labelDate}}</label>
                    <input type="date" [value]="dateString" (change)="onDateChange($event)" [disabled]="disabled" />
                </cds-date>
                <cds-time>
                    <label>{{zonedDateTimePickerConfiguration.labels.labelTime}}</label>
                    <input [disabled]="disabled" type="time" [value]="timeString" (change)="onTimeChange($event)" />
                </cds-time>
                <cds-select>
                    <label>{{zonedDateTimePickerConfiguration.labels.labelTimeZone}}</label>
                    <select [(ngModel)]="timeZone" (change)="onTimeZoneChange($event)">
                        <option *ngFor="let tz of zonedDateTimePickerConfiguration.supportedTimeZones" [value]="tz.timeZone">{{tz.text}}</option>
                    </select>
                </cds-select>
            </cds-input-group>
        </div> 
    `
})
export class ZonedDateTimePickerComponent implements OnInit {

    // Binds to the CDS Core Component:
    dateString: string | null = null;
    timeString: string | null = null;
    timeZone: string | null = null;

    @Input()
    zonedDateTimePickerConfiguration: ZonedDatePickerConfiguration = new DefaultZonedDatePickerConfiguration();

    @Input()
    zonedDateTime: Temporal.ZonedDateTime | string | null = null;

    @Input()
    disabled: boolean = false;

    @Output()
    zonedDateTimeChange: EventEmitter<Temporal.ZonedDateTime> = new EventEmitter();

    constructor() {
        this.timeZone = this.zonedDateTimePickerConfiguration.defaultTimeZone;
    }

    ngOnInit(): void {
        if (this.zonedDateTime != null) {
            // First convert into a Zoned Date Time ...
            const zonedDateTime = Temporal.ZonedDateTime.from(this.zonedDateTime);

            // ... then extract the Plain Date and Plain Time ...
            this.dateString = zonedDateTime.toPlainDate().toString();
            this.timeString = zonedDateTime.toPlainTime().toString({ smallestUnit: 'minute'});
            
            // ... and finally set the TimeZone in a safe way.
            this.setZonedDateTimeSafe(zonedDateTime);
        }
    }

    setZonedDateTimeSafe(zonedDateTime: Temporal.ZonedDateTime) {

        // Make sure we operate on a valid default TimeZone ...
        if(!isTimeZoneSupported(this.zonedDateTimePickerConfiguration.supportedTimeZones, this.zonedDateTimePickerConfiguration.defaultTimeZone)) {
            throw new Error(`The default TimeZone '${this.zonedDateTimePickerConfiguration.defaultTimeZone}' is not supported.`)
        }

        const timeZone = zonedDateTime.timeZone;

        if (!timeZone) {
            this.timeZone = this.zonedDateTimePickerConfiguration.defaultTimeZone;
            return;
        }

        // There are no complex TimeZone Mapping involved in the Picker. So if the TimeZone is not supported, 
        // we just recalculate the given ZonedDateTime to the default TimeZone:
        if (!timeZone.id || !isTimeZoneSupported(this.zonedDateTimePickerConfiguration.supportedTimeZones, timeZone.id)) {

            this.timeZone = this.zonedDateTimePickerConfiguration.defaultTimeZone;
            this.zonedDateTime = zonedDateTime.withTimeZone(this.zonedDateTimePickerConfiguration.defaultTimeZone);

            this.zonedDateTimeChange.emit(this.zonedDateTime);

            return;
        }

        // At the point we are safe to set the TimeZone:
        this.timeZone = timeZone.id;
    }

    onDateChange(event: any) {
        this.dateString = event.target.value;
        this.setDateTime();
    }

    onTimeChange(event: any) {
        this.timeString = event.target.value;
        this.setDateTime();
    }

    onTimeZoneChange(event: any) {
        this.timeZone = event.target.value;
        this.setDateTime();
    }

    setDateTime() {

        if (this.isValidDateString(this.dateString) && this.isValidTimeString(this.timeString) && this.timeZone != null) {

            const zonedDateTime = Temporal.PlainDateTime.from(this.dateString!)
                .withPlainTime(this.timeString!)
                .toZonedDateTime(this.timeZone);

            this.zonedDateTimeChange.emit(zonedDateTime);
        }
    }

    isValidDateString(value: string | null) {
        if(value == null) {
            return false;
        }

        try {
            Temporal.PlainDate.from(value);
            return true;
        } catch {
            return false;
        }
    }

    isValidTimeString(value: string | null) {
        if(value == null) {
            return false;
        }

        try {
            Temporal.PlainTime.from(value);
            return true;
        } catch {
            return false;
        }
    }
}
```

In your application you can now use the ``<app-date-picker>`` selector to bind a ``ZonedDateTime``:

```html
<app-date-picker [(zonedDateTime)]="endDate"></app-date-picker>
```

## Conclusion ##

And that's it.

I wanted to learn more about Clarity and learn about the upcoming Temporal API of JavaScript. It was only a 
few lines to implement a DatePicker, that also supports Timezones. It is far from perfect, given it's short 
list of supported time zones.

But I hope it gives you an idea, if you plan to tackle something similar.

I am sure most of this can be recreated with other libraries for handling Dates. 