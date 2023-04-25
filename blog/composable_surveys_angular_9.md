title: Composable Surveys with Angular 9
date: 2020-03-01 16:22
tags: angular, typescript, javascript
category: angular
slug: composable_surveys_angular_9
author: Philipp Wagner
summary: Building Surveys with Angular 9

I have built so many survey and questionnaire applications in my life, that I basically stopped counting.

Most of the systems were built in a way, that you have a schema defining the elements and the forms are 
dynamically rendered based on it. The schema defined the question types (single choice, multiple choice, 
text fields, ...), valid values and maybe some conditional displaying of elements.

What sounds appealing first... often breaks in reality.

## What's the problem? ##

No one wants to use boring surveys, people want:

* A great layout system
* Auto-Completes
* Accessibility
* Internationalization (i18n)
* Custom Validators
* Custom CSS
* Easy Backend Integration
* Push Messages 
* ... basically everything

And no matter how hard you try to satisfy everyones requirements, the abstraction you come 
up with will break. The only thing you could do for questionnaires and surveys is defining 
a good way to reuse components.

### And what about Google Forms and Microsoft Forms? ###

Google Forms and Microsoft Forms are two great tools to build surveys and questionnaires. And while 
I hate the "Not Invented Here" syndrome with a passion, these applications try to do everything for 
not being integrated easily.

Both services do not offer a RESTful API for querying the results, and what's suggested in the docs 
looks fragile to put it nicely. No I don't want to use Google AppScript to get results, nor do I want 
to use Microsoft Flow pipelines for something simple as getting survey results.

## What we are going to build ##

I want a system, that makes it easy to compose components for building surveys. I don't want to use a 
fixed model, but rather have dumb components holding their form data. In the following section you will 
see how I would implement it with Angular 9:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/composable_surveys_angular_9/survey.png">
        <img src="/static/images/blog/composable_surveys_angular_9/survey.png" alt="The final Survey application">
    </a>
</div>

You can play with the result here:

* [https://bytefish.de/static/apps/tiny-questionnaire](https://bytefish.de/static/apps/tiny-questionnaire)

As always all code can be found in a Github repository at:

* [https://github.com/bytefish/TinyQuestionnaire](https://github.com/bytefish/TinyQuestionnaire)

## The Implementation ##

Now let's see how to implement it!

### AppModule ###

The ``AppModule`` is where it all starts. 

We are going to declare three components we are going to write in this article:

* ``AddressComponent``
    * Provides the elements for Address data
* ``ContactComponent``
    * Provides the elements for Contact data
* ``SymptomComponent``
    * Provides the elements to capture symptoms
* ``HealthQuestionnaireComponent``
    * Uses all components to build a Questionnaire Wizard

The ``AppModule`` also includes a lot of Angular Material modules for high quality UI elements:

```typescript
import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms'

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

import { FlexLayoutModule } from '@angular/flex-layout';

import {MatInputModule} from '@angular/material/input';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatSelectModule} from '@angular/material/select';
import {MatCardModule} from '@angular/material/card';
import { MatDatepickerModule} from '@angular/material/datepicker'
import { MatStepperModule} from '@angular/material/stepper'
import { MatMomentDateModule } from '@angular/material-moment-adapter';
import { MatButtonModule } from '@angular/material/button';

import { ContactComponent } from './components/contact/contact.component';
import { AddressComponent } from './components/address/address.component';
import { SymptomComponent } from './components/symptom/symptom.component';
import { HealthQuestionnaireComponent } from './questionnaires/health/health-questionnaire.component';

@NgModule({
  declarations: [
    AppComponent,
    ContactComponent, 
    AddressComponent,  
    SymptomComponent,
    HealthQuestionnaireComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    FlexLayoutModule, 
    MatInputModule, 
    MatSelectModule,
    MatCardModule,
    MatDatepickerModule,
    MatMomentDateModule,
    MatAutocompleteModule,
    MatStepperModule,
    MatButtonModule
    
  ],
  providers: [ ],
  bootstrap: [AppComponent]
})
export class AppModule { }
```


### AddressComponent ###

The ``address.component.ts`` only provides an ``@Input()`` for the name of the ``NgModelGroup``:


```typescript
import { Component, OnInit, Input, SkipSelf } from '@angular/core';
import { ControlContainer, NgForm } from '@angular/forms';

@Component({
  selector: 'app-address',
  templateUrl: './address.component.html',
  styleUrls: ['./address.component.css'],
  viewProviders: [{
    provide: ControlContainer,
    useFactory: (container: ControlContainer) => container,
    deps: [[new SkipSelf(), ControlContainer]],
  }]
})
export class AddressComponent {

  @Input() modelGroupName: string;

}
```

And the template then uses the ``modelGroupName`` and Angular Material components for the elements:

```html
<div ngModelGroup="{{modelGroupName}}">

    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">
        <mat-form-field fxFlex="100">
            <input matInput placeholder="Street" name="street" ngModel i18n-placeholder required>
        </mat-form-field>
    </div>

    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">
        <mat-form-field fxFlex="20">
            <input matInput placeholder="ZIP Code" name="zip" ngModel i18n-placeholder required>
        </mat-form-field>
        <mat-form-field fxFlex="45">
            <input matInput placeholder="City" name="city" ngModel i18n-placeholder required>
        </mat-form-field>
        <mat-form-field fxFlex="30">
            <input matInput placeholder="Country" name="country" ngModel i18n-placeholder>
        </mat-form-field>
    </div>
</div>
```

### ContactComponent ##

The ``contact.component.ts`` only provides an ``@Input()`` for the NgModelGroup:

```typescript
import { Component, Input, SkipSelf } from '@angular/core';
import { ControlContainer } from '@angular/forms';

@Component({
  selector: 'app-contact',
  templateUrl: './contact.component.html',
  styleUrls: ['./contact.component.css'],
  viewProviders: [{
    provide: ControlContainer,
    useFactory: (container: ControlContainer) => container,
    deps: [[new SkipSelf(), ControlContainer]],
  }]
})
export class ContactComponent {
  
  @Input() modelGroupName: string;

}
```

And the template then uses the ``modelGroupName`` and Angular Material components for the elements. You can see, 
that the ``ContactComponent`` template also includes the ``<app-address>`` selector to include address data in the 
contact model:

```html
<div ngModelGroup="{{modelGroupName}}">

    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">
        <mat-form-field fxFlex="45">
            <input matInput placeholder="First Name" name="firstName" ngModel i18n-placeholder>
        </mat-form-field>
        <mat-form-field fxFlex="45">
            <input matInput placeholder="Last Name" name="lastName" required ngModel i18n-placeholder>
        </mat-form-field>
    </div>

    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">

        <mat-form-field fxFlex="20">
            <mat-label i18n>Gender</mat-label>
                <mat-select required>
                    <mat-option value="Female" i18n>Female</mat-option>
                    <mat-option value="Male" i18n>Male</mat-option>
              <mat-option value="Non-Binary" i18n>Non-Binary</mat-option>
            </mat-select>
          </mat-form-field>

        <mat-form-field fxFlex="20">
            <input matInput [matDatepicker]="picker" placeholder="Birth Date" name="birthDate" ngModel i18n-placeholder required>
            <mat-datepicker-toggle matSuffix [for]="picker"></mat-datepicker-toggle>
            <mat-datepicker #picker></mat-datepicker>
        </mat-form-field>

    </div>

    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">

        <mat-form-field fxFlex="50">
            <input matInput placeholder="Phone Number 1" name="phone1" ngModel i18n-placeholder>
        </mat-form-field>

        <mat-form-field fxFlex="50">
            <input matInput placeholder="Phone Number 2" name="phone2" ngModel i18n-placeholder>
        </mat-form-field>

        <mat-form-field fxFlex="50">
            <input matInput placeholder="Phone Number 3" name="phone3" ngModel i18n-placeholder>
        </mat-form-field>

    </div>

    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">
        <mat-form-field fxFlex="50">
            <input matInput placeholder="E-Mail Address 1" name="eMail1" ngModel i18n-placeholder>
        </mat-form-field>
        <mat-form-field fxFlex="50">
            <input matInput placeholder="E-Mail Address 2" name="eMail2" ngModel i18n-placeholder>
        </mat-form-field>
    </div>

    <app-address modelGroupName="address"></app-address> 
</div>
```

### SymptomsComponent ###

The ``SymptomsComponent`` is a little more "complicated". There are various symptoms a person can have, 
like fever, a cough or shortness of breath. The ``selectedItems`` variable holds these values and the 
``selectedUnit`` holds the Unit someone has measured the Fever with (Celsius or Fahrenheit):

```typescript
import { Component, SkipSelf, Input } from '@angular/core';
import { ControlContainer, NgForm } from '@angular/forms';

@Component({
  selector: 'app-symptom',
  templateUrl: './symptom.component.html',
  styleUrls: ['./symptom.component.css'],
  viewProviders: [{
    provide: ControlContainer,
    useFactory: (container: ControlContainer) => container,
    deps: [[new SkipSelf(), ControlContainer]],
  }]
})
export class SymptomComponent {

  @Input() modelGroupName: string;

  selectedItems: Array<string> = [];
  selectedUnit: string = 'celsius';

  handleSelection(selectedItems: Array<string>): void {
    this.selectedItems = selectedItems;
  }
}
```

In the template we are now dynamically displaying elements based on the symptom someone has chosen. For the 
temperature we display a required field for entering the measured temperature. For the "other" option, we 
are displaying a ``textarea`` to add a short description:

```html
<div ngModelGroup="{{modelGroupName}}">
    <div fxLayout="row" fxLayout.lt-sm="column" fxLayoutGap="20px">
        <mat-form-field fxFlex="100">
            <mat-label i18n>Symptoms</mat-label>
                <mat-select multiple name="symptom" (selectionChange)="handleSelection($event.value)" ngModel>
                    <mat-option value="fever" i18n>Fever</mat-option>
                    <mat-option value="cough" i18n>Cough</mat-option>
                    <mat-option value="shortnessOfBreath" i18n>Shortness of breath</mat-option>
                    <mat-option value="breathingDifficulties" i18n>Breathing difficulties</mat-option>
                    <mat-option value="other" i18n>Other</mat-option>
            </mat-select>
          </mat-form-field>
    </div>

    <div fxLayout="row" *ngIf="selectedItems.includes('fever')" fxLayout.lt-sm="column" fxLayoutGap="0px" >
            <mat-form-field fxFlex="10">
                <mat-select [(ngModel)]="selectedUnit" name="unit">
                  <mat-option value="celsius">&#176;C</mat-option>
                  <mat-option value="fahrenheit">&#176;F</mat-option>
             </mat-select>
            </mat-form-field>

            <mat-form-field fxFlex="30">
                <input matInput type="number" placeholder="Temperature" name="temperature" required ngModel>
            </mat-form-field>
    </div>

    <div fxLayout="row" *ngIf="selectedItems.includes('other')" fxLayout.lt-sm="column" fxLayoutGap="0px" >
        <mat-form-field fxFlex="100">
            <mat-label>Other</mat-label>
            <textarea name="other" matInput #message rows="5" maxlength="2500" placeholder="Please describe your symptoms ..." required ngModel></textarea>
            <mat-hint align="start"><strong>Please describe your symptoms.</strong> </mat-hint>
            <mat-hint align="end">{{message.value.length}} / 2500</mat-hint>
          </mat-form-field>
    </div>

</div>
```

### HealthQuestionnaireComponent ###

Finally we can put the components into a ``mat-horizontal-stepper`` to build a wizard a user has to follow. To prevent 
the form from being submitted on Enter or Shift + Enter, we capture the ``(ngSubmit)`` event and just return without 
actually doing anything.

If someone clicks the Submit Button on the last wizard page, we want to log the JSON to the console:

```typescript
import { Component } from '@angular/core';
import { NgForm } from '@angular/forms';

@Component({
  selector: 'app-health-questionnaire',
  templateUrl: './health-questionnaire.component.html',
  styleUrls: ['./health-questionnaire.component.css']
})
export class HealthQuestionnaireComponent {

  onSubmit(form: NgForm): void {
    return;
  }

  onClick(form: NgForm): void {
    const json = JSON.stringify(form.value);

    console.log(json);
  }
}
```

And now the ``mat-horizontal-stepper``. Each ``mat-step`` also defines a ``ngModelGroup``, so we can 
validate it and prevent stepping through the wizard with missing data:

```html
<mat-card class="example-card">
  <mat-card-header>
    <mat-card-title>Health Questionnaire</mat-card-title>
    <mat-card-subtitle>This is a sample questionnaire for Health Evaluation</mat-card-subtitle>
  </mat-card-header>
  <mat-card-content>
    <form (ngSubmit)="onSubmit(f)" #f="ngForm" novalidate>
      <mat-horizontal-stepper linear>
        <mat-step #personal="ngModelGroup" ngModelGroup="personal" [completed]="personal.valid">
          <ng-template matStepLabel>Personal</ng-template>
          <app-contact modelGroupName="contact"></app-contact>
        </mat-step>
        <mat-step #health="ngModelGroup" ngModelGroup="health" [completed]="health.valid">
          <ng-template matStepLabel>Health</ng-template>
          <app-symptom modelGroupName="symptoms"></app-symptom>
        </mat-step>
        <mat-step>
          <ng-template matStepLabel>Done</ng-template>
          <p>Thanks for using the survey!</p>
          <div>
            <button mat-raised-button type="button" (click)="onClick(f)" color="primary">Submit Data</button>
          </div>
        </mat-step>
      </mat-horizontal-stepper>
    </form>
    <pre>{{ f.value | json }}</pre>
  </mat-card-content>
</mat-card>
```

## Conclusion ##

And that's it. You now have a simple approach to building surveys. Are there shortcomings of this approach? Of course, 
there are! How do we pass data between the pages? Why don't we bind to a fixed model? How do we add our own validators?

I don't know yet, how far such an approach is going to take me, but it feels like a lightweight way to build surveys.

## License ##

The code is released under terms of the [MIT License].

[MIT License]: https://opensource.org/licenses/MIT