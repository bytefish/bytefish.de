title: Building a Fulltext Search Engine with ASP.NET Core, Angular 9, Elasticsearch and Tesseract
date: 2020-05-22 13:59
tags: dotnet, elasticsearch, tesseract
category: elasticsearch
slug: fulltext_search_example
author: Philipp Wagner
summary: This article shows how to implement Full Text Search, Auto-Completion with ASP.NET Core, Angular and Elasticsearch

Every project grows to a point it needs to support a Fulltext Search. And once you reach the point 
you'll need to give estimates. But have you ever built such a thing? How do you extract data from 
PDF files? Microsoft Word? Microsoft Excel? Microsoft PowerPoint? RTF? JPEG Images?

In this article I will develop a simple Fulltext Search Frontend and Backend using ASP.NET Core, 
Angular 9, Elasticsearch, Tesseract and PostgreSQL. It is meant as a basis for quick prototyping 
and iterate on ideas.

You can find all code on 

* [https://github.com/bytefish/ElasticsearchFulltextExample](https://github.com/bytefish/ElasticsearchFulltextExample)

## What we are going to build ##

Let's take a look at what we will build.

Basically we need a way to send documents from a client to a server, so we will build a small 
dialog for uploading files and adding some metadata like keywords and a document title:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_fulltext_search/Frontend_AddDocument.png">
        <img src="/static/images/blog/elasticsearch_fulltext_search/Frontend_AddDocument.png">
    </a>
</div>

Once we uploaded a file, we want to know the status. Is the document indexed? Is it still scheduled for 
indexing? Or was there a Server failure, that needs to be reported? So we add a component to see the 
status for each document:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_fulltext_search/Frontend_DocumentStatus.png">
        <img src="/static/images/blog/elasticsearch_fulltext_search/Frontend_DocumentStatus.png">
    </a>
</div>

What's a modern search without getting suggestions? Suggestions can help users find interesting 
content or reduce typos. So we'll also add an Auto-Completion box:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_fulltext_search/Frontend_Auto_Completion.png">
        <img src="/static/images/blog/elasticsearch_fulltext_search/Frontend_Auto_Completion.png">
    </a>
</div>

And what are we building all this for? Exactely, for getting search results on the uploaded data. The 
final result will contain the highlighted results from the Elasticsearch server:

<div style="display:flex; align-items:center; justify-content:center;margin-bottom:15px;">
    <a href="/static/images/blog/elasticsearch_fulltext_search/Frontend_Search_Results.png">
        <img src="/static/images/blog/elasticsearch_fulltext_search/Frontend_Search_Results.png">
    </a>
</div>

## Frontend ##

The Frontend is written with Angular 9. And it should be obvious, that I am not a great UI designer or 
CSS wizard. Just take a look at my minimal website, and even that took me weeks to build!

That's why the project uses the Angular Material components:

* [https://material.angular.io/](https://material.angular.io/)

Also note, that I am not using ngrx or any Redux libraries in the code, just because it would 
overcomplicate things. It's all basic Angular. 

### Configuring the Environment ###

#### Adding Paths to the tsconfig.json ####

In the ``tsconfig.json`` ``compilerOptions`` I am adding ``paths``. So we can import components and services using 
``@app`` and ``@environments`` instead of having to use relative paths:

```json
{
  "compileOnSave": false,
  "compilerOptions": {
    "paths": {
      "@app/*": [
        "src/app/*"
      ],
      "@environments/*": [
        "src/environments/*"
      ]
    }
  },
```

#### Configuring the environment ####

Angular uses the ``environment.ts`` and ``environment.prod.ts`` to set environment settings for debug and 
prod targets. We only need to add a ``apiUrl`` key for now, which defines the Backend API endpoint. 

The ``environment.ts`` for debugging looks like this:

```typescript
export const environment = {
  production: false,
  apiUrl: "http://localhost:9000/api"
};
```

And the ``environment.prod.ts`` for the production builds looks like this:

```typescript
export const environment = {
  production: true,
  apiUrl: "http://localhost:9000/api"
};
```

### Defining the Data Model ###

I am going to keep it very simple for this application and put all data contracts in a global file 
I have called ``app.model.ts``. In a larger application you probably want to modularize your Angular 
application, but this is sufficient for now.

The interfaces ``SearchStateEnum``, ``SearchQuery``, ``SearchResults`` and ``SearchResult`` hold the 
Search results for a given query:

```typescript
export enum SearchStateEnum {
  Loading = "loading",
  Finished = "finished",
  Error = "error"
}

export interface SearchQuery {
  state: SearchStateEnum;
  data: SearchResults;
  error: string;
}

export interface SearchResults {
  query: string;
  results: SearchResult[];
}

export interface SearchResult {
  identifier: string;
  title: string;
  matches: string[];
  keywords: string[];
  url: string;
  type: string;
}
```

For the suggestions we define two interfaces ``SearchSuggestions`` and ``SearchSuggestion``:

```typescript
export interface SearchSuggestions {
  query: string;
  results: SearchSuggestion[];
}

export interface SearchSuggestion {
  text: string;
  highlight: string;
}
```

And a document in the index can have a status and general file informations... like a filename, 
a title and if OCR was requested on the document or not.

```typescript
export enum StatusEnum {
  None = "none",
  ScheduledIndex = "scheduledIndex",
  ScheduledDelete = "scheduledDelete",
  Indexed = "indexed",
  Failed = "failed",
  Deleted = "deleted"
}

export interface DocumentStatus {
  id: number;
  filename: string;
  title: string;
  isOcrRequested: boolean;
  status: StatusEnum;
}
```

### Services ###

#### Search Service ####

In the file ``service/search.service.ts`` we are using a ``BehaviorSubject``, which replays the 
last emitted event to all subscribers and starts with an empty search term.

```typescript
import { Injectable } from '@angular/core';
import { Subject, Observable, BehaviorSubject } from 'rxjs';
import { share } from 'rxjs/operators';

@Injectable()
export class SearchService {
    
  private searchSubmittings$ = new BehaviorSubject<{ term: string }>({ term: null });

  submitSearch(term: string) {
    this.searchSubmittings$.next({ term });
  }

  onSearchSubmit(): Observable<{ term: string }> {
    return this.searchSubmittings$.pipe(share());
  }
}
```

### Routes ###

Next we define the routes for the application. There are only two routes:

* ``/search`` for the actual search.
* ``/status`` for the status of indexed documents.

The Angular CLI generates a ``app-routing.module.ts`` file, where the routes can be defined:

```typescript
import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { SearchComponent } from '@app/components/search/search.component';
import { DocumentStatusComponent } from './components/document-status/document-status.component';


const routes: Routes = [
  { path: '',
    pathMatch: 'full',
    redirectTo: "search"
  },
  {
    path: 'search',
    component: SearchComponent
  },
  {
    path: 'status',
    component: DocumentStatusComponent
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
```

### Components ###

#### AppComponent ####

The ``AppComponent`` is going to host all other components. So it is going to contain a:

* An ``<input>`` with ``type="search"`` for the search bar.
* A ``<mat-menu>`` to navigate between pages.
* A ``<router-outlet>`` to host child components.
* A Floating Action Button to upload files.

Please note, that I have used the ``<mat-autocomplete>`` to display the suggestions.

The template is defined in the file ``app.component.html``:

```html
<div class="search-container" fxLayout="column">
    <div class="search-bar" fxLayout="row" fxLayoutAlign="center center">
        <input #search type="search" (keyup.enter)="onKeyupEnter(search.value)" [formControl]="control" [matAutocomplete]="auto">
        <mat-autocomplete #auto="matAutocomplete">
            <ng-container *ngIf="suggestions$ | async as suggestions">
                <mat-option *ngFor="let suggestion of suggestions?.results" [value]="suggestion.text">
                    <span [innerHtml]="suggestion.highlight"></span>
                </mat-option>
            </ng-container>
        </mat-autocomplete>
        <button mat-icon-button [matMenuTriggerFor]="menu" aria-label="Example icon-button with a menu">
            <mat-icon>more_vert</mat-icon>
        </button>
        <mat-menu #menu="matMenu">
            <button mat-menu-item (click)="openFileUploadDialog()">
                <mat-icon>add</mat-icon>
                <span>Upload Document</span>
            </button>
            <button mat-menu-item routerLink="/status">
                <mat-icon>schedule</mat-icon>
                <span>Document Status</span>
            </button>
        </mat-menu>
    </div>
    <div>
        <router-outlet></router-outlet>
    </div>
</div>
<button class="add-button" mat-mini-fab aria-label="Upload Button with Attachment Icon"
    (click)="openFileUploadDialog()">
    <mat-icon>add</mat-icon>
</button>
```

Then we add some styling to the components in the file ``app.component.scss``:


```scss
@import '~@angular/material/theming';

$accent:  mat-palette($mat-amber);

.search-container {
  height: auto;
}

.search-bar {
  height: 60px;
  background-color: mat-color($accent, 200);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05),0 1px 4px rgba(0,0,0,0.05),0 2px 8px rgba(0,0,0,0.05);
}

input {
  border: solid 1px black;
  outline: none;
  margin: 10px;
  padding: 6px 16px;
  width: 100%;
  max-width: 600px;
  height: 40px;
  font-size: 16px;
}

.add-button {
  position: fixed;
  top: auto;
  right: 30px;
  bottom: 30px;
  left: auto;
}
```

In the class component file at ``app.component.ts`` we wire things up. 

The suggestions for the ``<mat-autocomplete>`` work by listening to ``valueChanges`` observable of 
the ``FormControl`` and then ``pipe`` the value to an API endpoint. By using ``debounceTime(300)`` 
not every single keystroke will be sent to the endpoint, but only after 300ms.

Instead of sending the query directly to the search service, I am using Router navigation to transport 
the state. That has the nice side-effect, that you can use ``/search?q=MySearch`` to search for documents 
containing ``MySearch``. The ``OnInit`` method then submits the value to the ``SearchService``.

Make sure to always use the ``catchError`` operator when defining Observables, because you don't want an 
error to silently kill your atuo-complete or other subscriptions.

```typescript
import { Component, ViewChild } from '@angular/core';
import { SearchSuggestions } from '@app/app.model';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { Router, ActivatedRoute } from '@angular/router';
import { Observable, of } from 'rxjs';
import { switchMap, debounceTime, catchError, map, filter } from 'rxjs/operators';
import { FormControl } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { MatAutocompleteTrigger } from '@angular/material/autocomplete';
import { FileUploadComponent } from './components/file-upload/file-upload.component';
import { DocumentStatusComponent } from './components/document-status/document-status.component';
import { SearchService } from './services/search.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {

  destroy$: Observable<void>;

  control = new FormControl();

  query$: Observable<string>;
  suggestions$: Observable<SearchSuggestions>;

  @ViewChild('search', { read: MatAutocompleteTrigger }) 
  autoComplete: MatAutocompleteTrigger;

  constructor(private route: ActivatedRoute, 
    private searchService: SearchService,
    private dialog: MatDialog, 
    private router: Router, 
    private httpClient: HttpClient) {

  }

  ngOnInit(): void {

    this.route.queryParams
      .pipe(
        map(params => params['q']),
        filter(query => !!query)
      )
      .subscribe(query => {
        this.control.setValue(query);
        this.searchService.submitSearch(query);
      });

    this.suggestions$ = this.control.valueChanges
      .pipe(
        debounceTime(300), // Debounce time to not send every keystroke ...
        switchMap(value => this
          .getSuggestions(value)
          .pipe(catchError(() => of(<SearchSuggestions>{ query: value, results: []}))))
      );
  }

  onKeyupEnter(value: string): void {
    
    if(!!this.autoComplete) {
      this.autoComplete.closePanel();
    }
   
    // Instead of firing the Search directly, let's update the Route instead:
    this.router.navigate(['/search'], { queryParams: { q: value } });
  }

  getSuggestions(query: string): Observable<SearchSuggestions> {

    if (!query) {
      return of(null);
    }

    return this.httpClient
      // Get the Results from the API:
      .get<SearchSuggestions>(`${environment.apiUrl}/suggest`, {
        params: {
          q: query
        }
      })
      .pipe(catchError((err) => {
        console.error(`An error occured while fetching suggestions: ${err}`);

        return of(<SearchSuggestions>{ query: query, results: []})
      }));
  }

  openFileUploadDialog() {
    this.dialog.open(FileUploadComponent);
  }

  openDocumentStatusDialog() {
    this.dialog.open(DocumentStatusComponent);
  }
}
```

#### SearchComponent ####

The ``SearchComponent`` holds the results of a query. It basically works by subscribing to the ``SearchService``, but 
first let's take a look at the data model again:

```typescript
export enum SearchStateEnum {
  Loading = "loading",
  Finished = "finished",
  Error = "error"
}

export interface SearchQuery {
  state: SearchStateEnum;
  data: SearchResults;
  error: string;
}

export interface SearchResults {
  query: string;
  results: SearchResult[];
}

export interface SearchResult {
  identifier: string;
  title: string;
  matches: string[];
  keywords: string[];
  url: string;
  type: string;
}
```

The ``SearchStateEnum`` defines three states a query can have:

* ``Loading``
* ``Finished``
* ``Error``

Based on the state we want to give the user some feedback, that the query is currently being processed. If the query was 
successful, the ``SearchQuery`` holds the ``SearchResults``. Now if the query yielded no results, you probably want to 
display some message based upon. 

Long story short: In the template ``components/search/search.component.html`` you'll see, that the different states can 
be handeled by simply using a ``[ngIf]``.

```html
<div fxFill fxLayout="column" style="padding-top: 25px;">
  <ng-container *ngIf="query$ | async as query">
    <!--  -->
    <ng-template [ngIf]="query.state == 'loading'">
      <div fxFlex fxLayout="row" fxLayoutAlign="center" style="margin-bottom:25px;">
        <mat-spinner></mat-spinner>
      </div>
    </ng-template>
    <!-- There was an error processing this request -->
    <ng-template [ngIf]="query.state == 'error'">
      <div fxFlex fxLayout="row" fxLayoutAlign="center" style="margin-bottom:25px;">
        <p>We are very sorry... There was an error processing the request. Maybe try later again? 😓</p>
      </div>
    </ng-template>
    <!--No results found -->
    <ng-template [ngIf]="query.state == 'finished' && query.data?.results.length == 0">
      <div fxFlex fxLayout="row" fxLayoutAlign="center" style="margin-bottom:25px;">
        <p>This query has no results. Maybe try a different one? 😓</p>
      </div>      
    </ng-template>
    <ng-template [ngIf]="query.state == 'finished' && query.data?.results.length > 0">
      <div *ngFor="let result of query.data?.results" fxFlex fxLayout="row" style="margin-bottom:25px;">
        <div fxFlex fxLayoutAlign="center">
          <mat-card class="search-result">
            <mat-card-content>
              <div class="search-result-header" fxLayout="column">
                <h3><a class="search-link" href="{{result.url}}">{{result.title}}</a></h3>
              </div>
              <div>
                <br />
                <p><strong>Matches in Content:</strong></p>
                <ul>
                  <li *ngFor="let match of result?.matches"><span [innerHtml]="match"></span></li>
                </ul>
              </div>
              <div>
                <mat-chip-list aria-label="Keywords">
                  <mat-chip *ngFor="let keyword of result?.keywords" color="accent">{{keyword}}</mat-chip>
                </mat-chip-list>
              </div>
            </mat-card-content>
            <mat-card-actions>
            </mat-card-actions>
          </mat-card>
        </div>
      </div>
    </ng-template>
  </ng-container>
</div>
```

We style the search results in the ``components/search/search.component.scss``, by adding some colors and paddings

```scss
.search-result {
  width: 600px;
}

.search-results {
  background-color: #eee;
  height: 100%;
  padding: 25px;
}

.search-link {

  color: rgb(2, 80, 224);
  text-decoration: none;

  &:visited {
    color:  rgb(2, 80, 224);
  }
}

h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.3;
}

.mat-card-content {
  margin: 0;
  word-wrap: break-word;
}

p {
  margin: 0;
}
```

And finally the TypeScript file for the ``SearchComponent`` in ``components/search/search.component.ts`` is very concise. 

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { SearchResults, SearchStateEnum, SearchQuery } from '@app/app.model';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { Observable, of, concat, Subject } from 'rxjs';
import { map, switchMap, filter, catchError, takeUntil } from 'rxjs/operators';
import { FormControl } from '@angular/forms';
import { SearchService } from '@app/services/search.service';

@Component({
  selector: 'app-search',
  templateUrl: './search.component.html',
  styleUrls: ['./search.component.scss']
})
export class SearchComponent implements OnInit, OnDestroy {
  
  destroy$ = new Subject<void>();

  control = new FormControl();
  query$: Observable<SearchQuery>;

  constructor(private httpClient: HttpClient, private searchService: SearchService) {

  }

  ngOnInit(): void {
    this.query$ = this.searchService.onSearchSubmit()
      .pipe(
        filter(query => !!query.term),
        switchMap(query =>
          concat(
            of(<SearchQuery>{ state: SearchStateEnum.Loading }),
            this.doSearch(query.term).pipe(
              map(results => <SearchQuery>{state: SearchStateEnum.Finished, data: results}),
              catchError(err => of(<SearchQuery>{ state: SearchStateEnum.Error, error: err }))
            )
          )
        ),
        takeUntil(this.destroy$)
      );
  }

  doSearch(query: string): Observable<SearchResults> {
    return this.httpClient
      .get<SearchResults>(`${environment.apiUrl}/search`, {
        params: {
          q: query
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

I know the ``Observable`` in ``ngOnInit`` looks a bit frightening, so let's dissect it a bit. 

The component get's a ``SearchService`` injected, which provides a public method ``searchService.onSearchSubmit()``. This is 
an ``Observable``, that emits search terms entered probably in some other component. Now think in Streams: 

1. The ``SearchService`` emits a new search value...
2. ... we check if it is not empty or undefined using the ``filter`` operator.
3. ... we then transform the ``Observable`` with the search term into an ``Observable<SearchQuery>``, which is going to hold the results.
4. ... inside the ``switchMap`` we are using ``concatMap``. ``concatMap`` makes sure to evaluate sequentially.
5. ... we then query the API endpoint using ``doSearch`` method, which returns us the ``SearchResults``.
6. ... by using the ``map`` operator we are transforming the ``SearchResults`` into a finished ``SearchQuery``.
7. ... if an error occurs we are returning a ``SearchQuery`` in the error state.
8. ... we listen for the stream until the component is destroyed. This pattern for unsubscribing streams was taken from RxJS samples.

Now you might ask yourself: But where do you actually bind it to the component? This is done by using Angulars built-in ``async`` pipe:

```html
<ng-container *ngIf="query$ | async as query">
    <!-- Work the SearchQuery ... -->
</ng-container>
```

#### FileUploadComponent ####

The file upload is a bit tricky and probably hard to digest for the "pure RESTful" API folk. The simplest 
way to upload a file is what the browser offers, so I am sending a ``multipart/form-data`` HTTP request to 
an endpoint and send the values in form fields.

Basically I need ...

* An ``<input>`` for the document title.
* A ``<mat-chip-list>`` for a list of suggestions.
* A checkbox, that signals if OCR should be applied or not.
* An ``<input>`` with ``type="file"`` to upload a File

The Component template is defined in ``components/file-upload/file-upload-component.html``:

```html
<h2>Add a Document to the Search Index</h2>

<form [formGroup]="fileUploadForm" (ngSubmit)="onSubmit()">
    <div fxLayout="column" class="file-input-container">
        <div fxLayout="column">
            <mat-form-field fxFlex>
                <input matInput formControlName="title" type="text" placeholder="Document Title">
            </mat-form-field>
        </div>
        <div fxLayout="column">
            <mat-form-field fxFlex>
                <mat-chip-list #chipList aria-label="Suggestions" formControlName="suggestions">
                  <mat-chip *ngFor="let suggestion of fileUploadForm.get('suggestions').value" [selectable]="true" [removable]="true" (removed)="onRemoveSuggestion(suggestion)">
                    {{suggestion}}
                    <mat-icon matChipRemove>cancel</mat-icon>
                  </mat-chip>
                  <input class="min-chips-height" placeholder="Suggestions"
                         [matChipInputFor]="chipList"
                         [matChipInputSeparatorKeyCodes]="separatorKeysCodes"
                         [matChipInputAddOnBlur]="true"
                         (matChipInputTokenEnd)="onAddSuggestion($event)">
                </mat-chip-list>
              </mat-form-field>
        </div>
        <div fxLayout="row">
            <input #fileInput id="fileInput" type="file" [hidden]="true" (change)="onFileInputChange($event)">
            <mat-form-field fxFlex [floatLabel]="'never'">
                <input matInput type="text" formControlName="file" (click)="fileInput.click()"
                    placeholder="Please Select a File ..." readonly>
            </mat-form-field>
            <button mat-mini-fab aria-label="Upload Button with Attachment Icon" (click)="fileInput.click()">
                <mat-icon>attach_file</mat-icon>
            </button>
        </div>
        <div fxLayout="column" fxLayoutAlign="center start">
            <div style="margin: 20px">
                <mat-checkbox color="primary" formControlName="ocr">Add OCR Data to Search Index</mat-checkbox>
            </div>
        </div>
        <div fxLayout="column">
            <button type="submit" mat-raised-button color="accent" [disabled]="isFileUploading">Index Document</button>
        </div>
    </div>
</form>
```

The components styles are defined in ``components/file-upload/file-upload-component.scss``:

```scss
.file-input-container {
    width: 500px;
    margin: 25px;
}

.mat-form-field-padding {
    margin: 15px;
}
```

And the component class is defined in the TypeScript file ``components/file-upload/file-upload-component.ts``.

Again there is no magic involved: 

* Reactive Forms are used to bind the ``<input>`` values.
* The ``<mat-chip-list>`` code is copied from:
    * [https://material.angular.io/components/chips/examples](https://material.angular.io/components/chips/examples)
* A ``FormData`` object is sent to the endpoint ``${environment.apiUrl}/index``


```typescript
import { COMMA, ENTER } from '@angular/cdk/keycodes';
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { FormControl, FormGroup, Validators, AbstractControl } from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';
import { MatChipInputEvent } from '@angular/material/chips';
import { StringUtils } from '@app/utils/string-utils';

@Component({
    selector: 'app-fileupload',
    templateUrl: './file-upload.component.html',
    styleUrls: ['./file-upload.component.scss']
})
export class FileUploadComponent {
    file: File;

    separatorKeysCodes: number[] = [ENTER, COMMA];

    fileUploadForm = new FormGroup({
        title: new FormControl('', Validators.required),
        suggestions: new FormControl([], Validators.required),
        file: new FormControl('', Validators.required),
        ocr: new FormControl(false)
    });

    isFileUploading: boolean = false;

    constructor(public dialogRef: MatDialogRef<FileUploadComponent>, private httpClient: HttpClient) {

    }

    onFileInputChange(fileInputEvent: any): void {
        this.file = fileInputEvent.target.files[0];
        this.fileControl.setValue(this.file?.name);
    }

    onAddSuggestion(event: MatChipInputEvent): void {

        const input = event.input;
        const value = event.value;

        if (!StringUtils.isNullOrWhitespace(value)) {
            this.suggestionsControl.setErrors(null);
            this.suggestionsControl.value.push(value.trim());
        }

        if (input) {
            input.value = '';
        }

        this.suggestionsControl.updateValueAndValidity();
    }

    onRemoveSuggestion(suggestion: string): void {
        const index = this.suggestionsControl.value.indexOf(suggestion);

        if (index >= 0) {
            this.suggestionsControl.value.splice(index, 1);
        }

        this.suggestionsControl.updateValueAndValidity();
    }


    onSubmit(): void {

        if (this.fileUploadForm.invalid) {
            return;
        }

        this.isFileUploading = true;

        this.httpClient
            .post<any>(`${environment.apiUrl}/index`, this.buildRequestFormData())
            .subscribe(x => {
                this.isFileUploading = false;
                this.dialogRef.close();
            })
    }

    buildRequestFormData(): FormData {
        const formData = new FormData();

        formData.append('title', this.titleControl.value);
        formData.append('suggestions', this.getCommaSeparatedSuggestions(this.suggestionsControl.value));
        formData.append('file', this.file);
        formData.append('isOcrRequested', this.ocrControl.value);

        return formData;
    }

    getCommaSeparatedSuggestions(values: string[]): string {
        return values
            .map(x => `"${x}"`)
            .join(",");
    }

    get titleControl(): AbstractControl {
        return this.fileUploadForm.get('title');
    }

    get suggestionsControl(): AbstractControl {
        return this.fileUploadForm.get('suggestions');
    }

    get fileControl(): AbstractControl {
        return this.fileUploadForm.get('file');
    }

    get ocrControl(): AbstractControl {
        return this.fileUploadForm.get('ocr');
    }
}
```

#### Document Status ####

As a user you want to get some feedback what happened to my upload or what's happening *right now*. Has my document been 
processed yet? How many documents failed to process and what's the reason? You probably want to delete documents altogether 
or re-run some indexing.

For this we are using a ``<mat-table>`` containing the relevant bits of data in the template file ``components/document-status/document-status.component.html``:

```
<div fxFill fxLayout="column">
    <div fxFlex fxLayout="row" style="margin:25px;">
        <div fxFlex *ngIf="isDataSourceLoading" fxLayoutAlign="center">
            <mat-spinner></mat-spinner>
        </div>
        <div *ngIf="!isDataSourceLoading" fxFlex>
            <table mat-table [dataSource]="dataSource" class="mat-elevation-z8">
                <ng-container matColumnDef="select">
                    <th mat-header-cell *matHeaderCellDef>
                        <mat-checkbox color="primary" (change)="$event ? masterToggle() : null"
                            [checked]="selection.hasValue() && isAllSelected()"
                            [indeterminate]="selection.hasValue() && !isAllSelected()" [aria-label]="checkboxLabel()">
                        </mat-checkbox>
                    </th>
                    <td mat-cell *matCellDef="let row">
                        <mat-checkbox color="primary" (click)="$event.stopPropagation()"
                            (change)="$event ? selection.toggle(row) : null" [checked]="selection.isSelected(row)"
                            [aria-label]="checkboxLabel(row)">
                        </mat-checkbox>
                    </td>
                </ng-container>
                <ng-container matColumnDef="id">
                    <th mat-header-cell *matHeaderCellDef> Document ID </th>
                    <td mat-cell *matCellDef="let element"> {{element.id}} </td>
                </ng-container>
                <ng-container matColumnDef="title">
                    <th mat-header-cell *matHeaderCellDef> Title </th>
                    <td mat-cell *matCellDef="let element"> {{element.title}} </td>
                </ng-container>
                <ng-container matColumnDef="filename">
                    <th mat-header-cell *matHeaderCellDef> Filename </th>
                    <td mat-cell *matCellDef="let element"> {{element.filename}} </td>
                </ng-container>
                <ng-container matColumnDef="isOcrRequested">
                    <th mat-header-cell *matHeaderCellDef> Additional OCR </th>
                    <td mat-cell *matCellDef="let element">
                        <mat-checkbox color="primary" [checked]="element.isOcrRequested" [disableRipple]="true"
                            (click)="$event.preventDefault()"> </mat-checkbox>
                    </td>
                </ng-container>
                <ng-container matColumnDef="status">
                    <th mat-header-cell *matHeaderCellDef> Status </th>
                    <td mat-cell *matCellDef="let element"> {{element.status}} </td>
                </ng-container>
                <tr mat-header-row *matHeaderRowDef="displayedColumns; sticky: true"></tr>
                <tr mat-row *matRowDef="let row; columns: displayedColumns;" (click)="selection.toggle(row)">
                </tr>
            </table>
        </div>
    </div>
    <div fxFlex fxLayout="row" style="margin:25px;" fxLayoutAlign="end center" fxLayoutGap="25px">
        <button mat-raised-button color="accent" (click)="scheduleSelectedDocuments()">Re-Index Documents (Alt + R)</button>
        <button mat-raised-button color="accent" (click)="removeSelectedDocuments()">Remove Documents (Alt + Del)</button>
    </div>
</div>
```

The styling in ``components/document-status/document-status.component.scss`` sets the column width:

```scss
.document-status-container {
  margin: 25px;
}

.mat-form-field-padding {
  margin: 15px;
}

.min-chips-height {
  min-height: 50px;
}

table {
  width: 100%;
}

td.mat-column-select {
  width: 50px;
}

td.mat-column-documentId {
  width: 300px;
}

td.mat-column-filename {
  width: 400px;
}

td.mat-column-isOcrRequested {
  width: 100px;
}

td.mat-column-status {
  width: 150px;
}
```


In the class component file at ``components/document-status/document-status.component.ts`` the Document Status is loaded from 
the API endpoint ``/status``. Initially the entire table is reloaded in the ``ngOnInit`` method. Every five seconds only the 
state of each document is updated, so we do not override current selections.

Keyboard Shortcuts often make life a lot easier for Power Users. So if you are designing UIs make sure to also include Keyboard 
shortcuts for repititive tasks, so users don't get a Carpal tunnel syndrome.

```typescript
import { Component, OnInit, HostListener, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { MatTableDataSource } from '@angular/material/table';
import { SelectionModel } from '@angular/cdk/collections';
import { DocumentStatus } from '@app/app.model';
import { catchError, concatMap, mergeMap, toArray, tap, takeUntil } from 'rxjs/operators';
import { of, from, Subject, interval } from 'rxjs';

@Component({
  selector: 'app-document-status',
  templateUrl: './document-status.component.html',
  styleUrls: ['./document-status.component.scss']
})
export class DocumentStatusComponent implements OnInit, OnDestroy {

  private destroy$ = new Subject<void>();

  displayedColumns: string[] = ['select', 'id', 'title', 'filename', 'isOcrRequested', 'status'];

  isDataSourceLoading: boolean = false;
  dataSource = new MatTableDataSource<DocumentStatus>();
  selection = new SelectionModel<DocumentStatus>(true, []);

  constructor(private httpClient: HttpClient, private changeDetectorRefs: ChangeDetectorRef) {

  }

  ngOnInit(): void {
    interval(5000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.reloadStatusValues());

    this.reloadDataTable();
  }

  reloadDataTable() {
    this.selection.clear();

    this.httpClient
      .get<DocumentStatus[]>(`${environment.apiUrl}/status`)
      .pipe(
        catchError(() => of<DocumentStatus[]>([])))
      .subscribe(data => {
        this.dataSource.data = data;
      });
  }

  reloadStatusValues() {
    this.httpClient
      .get<DocumentStatus[]>(`${environment.apiUrl}/status`)
      .pipe(
        catchError(() => of<DocumentStatus[]>([])))
      .subscribe(data => {

        const status = new Map(data.map(i => [i.id, i.status]));

        this.dataSource.data
          .forEach(row => {
            if (status.has(row.id)) {
              row.status = status.get(row.id);
            }
          });

        this.changeDetectorRefs.detectChanges();
      });
  }


  /** Whether the number of selected elements matches the total number of rows. */
  isAllSelected() {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource.data.length;
    return numSelected === numRows;
  }

  /** Selects all rows if they are not all selected; otherwise clear selection. */
  masterToggle() {
    this.isAllSelected() ?
      this.selection.clear() :
      this.dataSource.data.forEach(row => this.selection.select(row));
  }

  /** The label for the checkbox on the passed row */
  checkboxLabel(row?: DocumentStatus): string {
    if (!row) {
      return `${this.isAllSelected() ? 'select' : 'deselect'} all`;
    }
    return `${this.selection.isSelected(row) ? 'deselect' : 'select'} row ${row.id}`;
  }

  @HostListener('document:keyup', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    if (event.altKey && event.key === 'Delete') {
      this.removeSelectedDocuments();
    }

    if (event.altKey && (event.key === 'r' || event.key === 'R')) {
      this.scheduleSelectedDocuments();
    }
  }

  removeSelectedDocuments() {

    var documentsToRemove = this.selection.selected

    from(documentsToRemove)
      .pipe(
        mergeMap(x => this.httpClient.delete(`${environment.apiUrl}/status/${x.id}`)),
        toArray()
      )
      .subscribe(() => this.reloadDataTable());
  }

  scheduleSelectedDocuments() {

    var documentsToIndex = this.selection.selected

    from(documentsToIndex)
      .pipe(
        mergeMap(x => this.httpClient.post<any>(`${environment.apiUrl}/status/${x.id}/index`, [])),
        toArray()
      )
      .subscribe(() => this.reloadDataTable());
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

## Backend ##

So far we have written the Frontend. Of course this whole process of writing applications is always some kind of 
Chicken-Egg problem. What comes first, the Frontend or the Backend? I say neither. It's evolution. 

In my projects I often start with a Database model. 



## Conclusion ##

I think Angular is a good framework to quickly **get something done**. 

## License ##

All code is released under terms of the [MIT License].

[MIT License]: https://opensource.org/licenses/MIT