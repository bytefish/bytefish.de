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

### Components ###

#### File Upload ####

``components/file-upload/file-upload-component.html`` 

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
        <!-- Upload Item -->
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



## License ##

All code is released under terms of the [MIT License].

[MIT License]: https://opensource.org/licenses/MIT