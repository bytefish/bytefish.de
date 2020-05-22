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

#### App Component ####

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

.search-link {

  color: rgb(2, 80, 224);
  text-decoration: none;

  &:visited {
    color:  rgb(2, 80, 224);
  }
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

.small {
  font-size: 12px;
}

h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.3;
}

.mat-card-content {
  margin: 0;
}

p {
  margin: 0;
}

cite {
  font-size: 12px;
}

.search-results {
  background-color: #eee;
  height: 100%;
  padding: 25px;
}

.search-result {
  width: 500px;
}

.add-button {
  position: fixed;
  top: auto;
  right: 30px;
  bottom: 30px;
  left: auto;
}
```

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
#### File Upload ####

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

And the component class is defined in the TypeScript file ``components/file-upload/file-upload-component.ts``:


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

There is no magic involved: 

* Reactive Forms are used to bind the ``<input>`` values.
* The ``<mat-chip-list>`` code is copied from:
    * [https://material.angular.io/components/chips/examples](https://material.angular.io/components/chips/examples)
* A ``FormData`` object is sent to the endpoint ``${environment.apiUrl}/index``

And that's it.
    
[@angular/flex-layout]: https://github.com/angular/flex-layout

## License ##

All code is released under terms of the [MIT License].

[MIT License]: https://opensource.org/licenses/MIT