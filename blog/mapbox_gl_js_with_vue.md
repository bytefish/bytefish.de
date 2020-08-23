title: Using Mapbox GL JS in a Vue.js Application
date: 2020-08-23 20:56
tags: osm, dotnet, mapbox, tiles
category: dotnet
slug: mapbox_gl_js_with_vue
author: Philipp Wagner
summary: This article shows how to use Mapbox GL JS in a Vue.js application.

I have been playing around with Vue.js this weekend. Why? Because Vue.js often comes up when discussing technologies 
for Single Page Applications (SPA). But it's hard for me to make an informed decision without knowing anything about 
Vue.js. So... Let's take a look at it!

According to Wikipedia ...

> Vue.js (commonly referred to as Vue; pronounced /vjuː/, like "view") is an open-source 
> model–view–viewmodel JavaScript  framework for building user interfaces and single-page 
> applications.

## What we are going to build ##

For my [MapboxTileServer] project I have written an ``index.html`` "Frontend", that supports to search for 
locations and made it possible to display the OSM properties of a map item. Of course, this approach will 
end up in a giant noodle without a proper structure. 

So let's recreate the Frontend in Vue.js!

The final result makes it possible to add markers, lines and search for places.

<div style="display:flex; align-items:center; justify-content:center;">
    <a href="/static/images/blog/mapbox_gl_js_with_vue/VueMuenster.png">
        <img src="/static/images/blog/mapbox_gl_js_with_vue/VueMuenster.png">
    </a>
</div>

## Starting with Vue.js ##

So. I know next to nothing about Vue.js! Let me explain how I start such projects.

The plan basically is:

1. Research existing Mapbox libraries for Vue.js.
2. Take a look at GitHub Projects using the libraries to get an *inspiration*. 
3. Profit!

I want to learn Vue.js as I go along.

But sadly the Vue.js libraries I found didn't fit my needs. They have been either abandoned, lacked basic 
features for displaying markers or lines... or have been released under terms of the GPL-license, which I 
won't release my code with.

So I took a step back and found this beautiful tutorial on using Google Maps with Vue.js:

* [https://vuejs.org/v2/cookbook/practical-use-of-scoped-slots.html](https://vuejs.org/v2/cookbook/practical-use-of-scoped-slots.html)

If it works for Google Maps, why shouldn't it work for the Mapbox client?

## Integrating Mapbox with Vue.js ##

### Setting the Project up ###

All Angular, React or Vue.js projects start with a ``package.json``, which defines the packages to download from the 
npm (Node package manager) repositories. I tried to update all dependecies to their latest stable versions, so I am 
somewhat up to date.

```json
{
  "name": "mbtiles-viewer",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "serve": "vue-cli-service serve",
    "build": "vue-cli-service build",
    "lint": "vue-cli-service lint"
  },
  "dependencies": {
    "core-js": "~3.6.5",
    "mapbox-gl": "~1.12.0",
    "vue": "2.6.12",
    "vue-router": "^3.4.3"
  },
  "devDependencies": {
    "@vue/cli-plugin-babel": "~4.5.4",
    "@vue/cli-plugin-eslint": "~4.5.4",
    "@vue/cli-plugin-router": "~4.5.4",
    "@vue/cli-service": "~4.5.4",
    "babel-eslint": "~10.0.3",
    "eslint": "^6.8.0",
    "eslint-config-prettier": "^6.11.0",
    "eslint-plugin-prettier": "^3.1.4",
    "eslint-plugin-vue": "^6.2.2",
    "prettier": "~2.0.5",
    "vue-template-compiler": "2.6.12"
  },
  "eslintConfig": {
    "root": true,
    "env": {
      "node": true
    },
    "extends": [
      "plugin:vue/essential",
      "plugin:prettier/recommended",
      "eslint:recommended"
    ],
    "parserOptions": {
      "parser": "babel-eslint"
    },
    "rules": {}
  },
  "browserslist": [
    "> 1%",
    "last 2 versions"
  ]
}
```

If you are using Visual Studio Code, then you are probably using [Vetur]. Vetur uses a library called 
prettier to format the JavaScript and Vue templates. It is very opinionated. I am also very opinionated, 
so I set some rules to match my style better in the ``.prettierrc``:

```json
{
  "trailingComma": "none",
  "semi": true,
  "singleQuote": true,
  "printWidth": 140
}
```

And Vue.js often also comes with linting, which is a good thing in a dynamic language to get some 
warnings and hints. But I also wanted to configure it, so some of the recommended rules for Vue.js 
don't throw errors. 

I am setting the following configurations in the ``.eslintrc.js``:

```javascript
module.exports = {
  extends: [
    // add more generic rulesets here, such as:
    // 'eslint:recommended',
    'plugin:vue/recommended'
  ],
  rules: {
    // override/add rules settings here, such as:
    // 'vue/no-unused-vars': 'error'
    'vue/max-attributes-per-line': 0,
    'vue/require-render-return': "off"
  }
}
```

## Defining the Mapbox Vue Components ##

### State Management ###

[vuex]: https://vuex.vuejs.org/

Now if you start with Vue.js, then chance is good you stumble upon [vuex] for managing the state 
of your application and modelling the data flow in your application. I like what the documentation 
writes on vuex: 

> Vuex helps us deal with shared state management with the cost of more concepts and boilerplate. It's 
> a trade-off between short term and long term productivity.
> 
> If you've never built a large-scale SPA and jump right into Vuex, it may feel verbose and daunting. That's 
> perfectly normal - if your app is simple, you will most likely be fine without Vuex. A simple store pattern 
> may be all you need. 

We want to start out simple, so I like to go with the proposed "Simple State Management from Scratch":

* [https://vuejs.org/v2/guide/state-management.html#Simple-State-Management-from-Scratch](https://vuejs.org/v2/guide/state-management.html#Simple-State-Management-from-Scratch)

Our ``store`` is very basic and just shares the information, if the map is mounted and ready for use:

```javascript
import Vue from "vue";

export const store = Vue.observable({
  mbglCenter: null
});

export const mutations = {
  setMbglCenter(val) {
    store.mbglCenter = val;
  }
};
```

### MapboxLoader: Defining the Mapbox GL JS Canvas ###

We then start by defining the ``MapboxLoader`` component. It has a ``<div>`` element that is 
going to hold the Mapbox GL JS canvas and uses a ``slot`` to share the map to all Vue components 
it may contain.

We also listen for changes to the ``store.mbglCenter``, because we want to update the Mapbox 
canvas when a new center is set by some other component. We assume, that the map is ready when 
the styledata has been loaded.

```html
<template>
  <div>
    <div ref="mapboxMap" class="mapbox-map" />
    <template v-if="isReady">
      <slot :map="map" />
    </template>
  </div>
</template>

<script>
import 'mapbox-gl/dist/mapbox-gl.css';
import mapboxgl from 'mapbox-gl';
import { mapboxMapOptions } from '../model/mapbox-map-options';
import { store } from '../store';

export default {
  props: {
    ...mapboxMapOptions
  },

  data: function() {
    return {
      map: null,
      isReady: false
    };
  },
  computed: {
    mapCenter() {
      return store.mbglCenter;
    }
  },
  watch: {
    mapCenter(coordinates) {
      this.map.jumpTo({ center: coordinates });
    }
  },
  mounted() {
    this.initializeMap();
  },
  methods: {
    initializeMap() {
      var vm = this;

      const mapContainer = this.$refs.mapboxMap;

      this.map = new mapboxgl.Map({
        container: mapContainer,
        style: this.mapStyle,
        center: this.center,
        zoom: this.zoom
      });

      this.map.on('styledata', function () {
        if(!vm.isReady) {
          vm.isReady = true;
        }
      });
    }
  }
};
</script>

<style scoped>
.mapbox-map {
  width: 100%;
  height: 100%;
}
</style>
```

You can already include this component and it is going to display a map. I have defined the properties in a file 
``mapbox-map-options.js`` and used the Spread Operator to define them in the ``MapboxLoader`` component. The following 
is a snippet off the ``mapbox-map-options.js``.

```javascript
export const mapboxMapOptions = {
  center: {
    type: Array,
    required: false,
    default: [51.961563, 7.628202]
  },
  minZoom: {
    type: Number,
    default: 0
  },
  maxZoom: {
    type: Number,
    default: 22
  },
  mapStyle: {
    type: [String, Object],
    required: true
  },
  ...
};
```

### MapboxMarker: Filling the Map with Life ###

Now you can scroll around the map, but there isn't much happening yet. You remember, that we have defined a ``slot`` in the 
``MapboxLoader``? This ``slot`` makes it possible to include a child component in the ``MapboxLoader`` and pass the map 
as a property into it.

We are creating a ``MapboxMarker`` component to display a Marker. I have already created a marker in the ``index.html`` example, 
so I can just copy and paste the code into it.

```javascript
<script>
import mapboxgl from 'mapbox-gl';

export default {
  props: {
    map: {
      type: Object,
      required: true
    },
    marker: {
      type: Object,
      required: true
    }
  },
  mounted() {
    var marker = new mapboxgl.Marker()
      .setLngLat(this.marker.lnglat)
      .setDraggable(this.marker.draggable)
      .setRotation(this.marker.rotation)
      .addTo(this.map);
  },
  render() {
  }
};
</script>
```
### MapboxLine: Using GeoJSON to draw lines ###

And we define a ``MapboxLine`` component to draw lines onto the map. We can use GeoJSON to do this!

For each line we are adding a new GeoJSON source and add it as a new layer.

```javascript
<script>
import { mapboxLineOptions } from '../model/mapbox-line-options';

export default {
  props: {
    map: {
      type: Object,
      required: true
    },
    ...mapboxLineOptions
  },

  mounted() {
    this.map.addSource(`line_${this.id}`, {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: {
              color: this.color
            },
            geometry: {
              type: 'LineString',
              coordinates: this.path
            }
          }
        ]
      }
    });

    this.map.addLayer({
      id: `line_${this.id}`,
      type: 'line',
      source: `line_${this.id}`,
      paint: {
        'line-width': 3,
        // Use a get expression (https://docs.mapbox.com/mapbox-gl-js/style-spec/#expressions-get)
        // to set the line-color to a feature property value.
        'line-color': ['get', 'color']
      }
    });
  },
  render() {}
};
</script>
```

The ``props`` for the component have been defined in the file ``mapbox-line-options.js`` and I have used 
the spread operator to set them in the components property list.

```javascript
export const mapboxLineOptions = {
  id: {
    type: String,
    required: true
  },
  path: {
    type: Array,
    required: true
  },
  color: {
    type: String,
    required: false,
    default: '#33C9EB'
  }
};
```

The Mapbox part is already done!

## Search: Locating things on the Map ##

There are probably great libraries to provide auto completion, but... I have been burnt in so many projects, that it 
is often easier to write small components all by yourself instead of taking yet another dependency.

### The Vue.js component ###

The DigitalOcean Community pages have a great tutorial on how to implement an Auto Complete component with Vue.js, and 
that's what I am going to use:

* [https://www.digitalocean.com/community/tutorials/vuejs-vue-autocomplete-component](https://www.digitalocean.com/community/tutorials/vuejs-vue-autocomplete-component)

In the end I have reused almost everything of the tutorial. There are some minor changes, like emitting an event on 
selection or adding a caption to the result item.

```javascript
<template>
  <div class="autocomplete">
    <input v-model="search" type="text" @input="onChange" @keydown.down="onArrowDown" @keydown.up="onArrowUp" @keydown.enter="onEnter">
    <ul v-show="isOpen" id="autocomplete-results" class="autocomplete-results">
      <li v-if="isLoading" class="loading">
        Loading results...
      </li>
      <li
        v-for="(result, i) in results"
        v-else
        :key="i"
        :class="{ 'is-active': i === arrowCounter }"
        class="autocomplete-result"
        @click="setResult(result)"
      >
        {{ result.caption }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'Search',
  props: {
    items: {
      type: Array,
      required: false,
      default: () => []
    }
  },
  data() {
    return {
      isOpen: false,
      results: [],
      search: '',
      isLoading: false,
      arrowCounter: 0
    };
  },
  watch: {
    items: function (val, oldValue) {
      this.results = val;
      this.isLoading = false;
    }
  },
  mounted() {
    document.addEventListener('click', this.handleClickOutside);
  },
  destroyed() {
    document.removeEventListener('click', this.handleClickOutside);
  },
  methods: {
    onChange() {
      this.$emit('input', this.search);
      this.isOpen = true;
      this.isLoading = true;
    },
    setResult(result) {
      if (!!result) {
        this.search = result.caption;
        this.isOpen = false;

        this.$emit('selected', result);
      }
    },
    onArrowDown(evt) {
      if (this.arrowCounter < this.results.length) {
        this.arrowCounter = this.arrowCounter + 1;
      }
    },
    onArrowUp() {
      if (this.arrowCounter > 0) {
        this.arrowCounter = this.arrowCounter - 1;
      }
    },
    onEnter() {
      this.setResult(this.results[this.arrowCounter]);
      this.arrowCounter = -1;
    },
    handleClickOutside(evt) {
      if (!this.$el.contains(evt.target)) {
        this.isOpen = false;
        this.arrowCounter = -1;
      }
    }
  }
};
</script>

<style>
.autocomplete {
  position: relative;
}

.autocomplete input {
  width: 500px;
}

.autocomplete-results {
  color: black;
  background-color: white;
  padding: 0;
  margin: 0;
  height: auto;
  overflow: auto;
  width: 100%;
}

.autocomplete-result {
  list-style: none;
  text-align: left;
  padding: 4px 2px;
  cursor: pointer;
}

.autocomplete-result.is-active,
.autocomplete-result:hover {
  background-color: #4aae9b;
  color: white;
}
</style>
```

### Querying Photon: The Search Results ###

In the previous post I have written a small method, which turns a result of the Photon Webservice into a summary (or say label, caption). To 
share this functionality between multiple components I add it to a class ``osm.js``.

```javascript
export function featureToString(feature) {
  var components = [];

  if (feature.properties.name) {
    components.push(feature.properties.name);
  }

  if (feature.properties.street && feature.properties.housenumber) {
    components.push(`${feature.properties.street} ${feature.properties.housenumber}`);
  }

  if (feature.properties.street && !feature.properties.housenumber) {
    components.push(feature.properties.street);
  }

  if (!feature.properties.postcode && feature.properties.city) {
    components.push(`${feature.properties.city}`);
  }

  if (feature.properties.postcode && feature.properties.city) {
    components.push(`${feature.properties.postcode} ${feature.properties.city}`);
  }

  if (feature.properties.country) {
    components.push(feature.properties.country);
  }

  return components.join(', ');
}
```

And we saw in the last post, that we probably need to filter the list for duplicates. So I am adding a ``groupBy`` 
method in the file ``core.js``.

```javascript
// https://stackoverflow.com/questions/14446511/most-efficient-method-to-groupby-on-an-array-of-objects

export function isNullOrUndefined(element) {
  return element === null || element === undefined;
}

export function groupBy(list, keyGetter) {
  const map = new Map();
  list.forEach((item) => {
    const key = keyGetter(item);
    const collection = map.get(key);
    if (!collection) {
      map.set(key, [item]);
    } else {
      collection.push(item);
    }
  });
  return map;
}
```

And what's left is to actually query the Photon Webservice and prepare the results. It basically loads the features first, 
then transforms it into a more suitable representation and groups the results by their caption. To make the results distinct 
I am then taking only the first element of each group.

```javascript
import { groupBy } from '../utils/core';
import { featureToString } from '../utils/osm';

function transformFeature(feature) {
  return {
    caption: featureToString(feature),
    coordinates: feature.geometry.coordinates,
    properties: feature.properties
  };
}

export async function searchPhotonAsync(url, query) {
  const endpoint = new URL(url);
  const searchParams = new URLSearchParams({ q: query });

  endpoint.search = searchParams.toString();

  var response = await fetch(endpoint, { method: 'GET', mode: 'cors', cache: 'no-cache' });

  if (response.status === 200) {
    var data = await response.json();
    // First check if we got data and features:
    if (!!data && !!data.features) {
      // We first transform the OSM Feature returned by Photon into something
      // simpler, that can be consumed by some other code.
      const allSearchResults = data.features.map((x) => transformFeature(x));
      // Then we group by the caption of the result. We are doing this, because
      // we can have multiple items with the same name, say: The Street and a
      // Point of Interest, which will both resolve to the same name.
      const groupedSearchResults = groupBy(allSearchResults, (x) => x.caption);
      // Now the grouped items looks like this:
      //
      //  [
      //    [ "A", [ searchResultA, searchResultB ] ],
      //    [ "B", [ searchResultC ] ],
      //    [ "C", [ searchResultD, searchResultE ] ]
      //  ]
      //
      // So to have distinct search results, we are only taking the first search
      // result and discard the rest.
      return Array.from(groupedSearchResults, ([key, value]) => value[0]);
    }
  }

  return [];
}
```

## Home.vue: Connecting all the things ##

Now what's left is connecting everything. In the data section we are defining the lines and markers to 
be displayed by our Map components. These properties are automatically registered as reactive properties 
by Vue.js, so adding or removing markers will directly be reflected in the map.

We wire up the ``input`` event of the ``Search``, so that the ``searchPhotonAsync`` is invoked and 
sets the ``searchResults``. The ``searchResults`` are passed down into the ``SearchComponents`` using 
the ``:item`` property.

When the user selects an entry from the Search auto complete, then the ``Search`` component emits a 
``@selected`` event, which passes the selected search item to the registered handler. We are then using 
the ``item.coordinates`` property to create a Marker and use the ``store`` to set the new center.


```javascript
<template>
  <div id="home">
    <Search id="search" :items="searchResults" @input="search" @selected="onItemSelected" />
    <MapboxLoader id="map" v-bind="mapOptions">
      <template slot-scope="{ map }">
        <MapboxMarker v-for="marker in markers" :key="marker.id" :marker="marker" :map="map" />
        <MapboxLine v-for="line in lines" :id="line.id" :key="line.id" :map="map" :color.sync="line.color" :path.sync="line.path" />
      </template>
    </MapboxLoader>
  </div>
</template>

<script>
import { store, mutations } from '../store';
import { MapboxLoader, MapboxLine, MapboxMarker, Search } from '../components';
import { searchPhotonAsync } from '../api/search-service';
import { isNullOrUndefined } from '../utils/core';
import {
  LNGLAT_MUENSTER,
  URL_MAPBOX_STYLE,
  URL_PHOTON_SEARCH,
  MARKER_MUENSTER_CITY_CENTER,
  LINE_WALK_THROUGH_MUENSTER
} from '../model/sample-data';

export default {
  name: 'Home',
  components: {
    MapboxLoader,
    MapboxMarker,
    MapboxLine,
    Search
  },
  data: function () {
    return {
      mapOptions: {
        mapStyle: URL_MAPBOX_STYLE,
        zoom: 14,
        center: LNGLAT_MUENSTER
      },
      markers: [MARKER_MUENSTER_CITY_CENTER],
      lines: [LINE_WALK_THROUGH_MUENSTER],
      searchResults: []
    };
  },
  methods: {
    search: async function (val) {
      var endpoint = URL_PHOTON_SEARCH;
      var features = await searchPhotonAsync(endpoint, val);

      this.searchResults = features;
    },
    onItemSelected: function (item) {
      if (isNullOrUndefined(item)) {
        return;
      }

      const markerId = this.getLastMarkerId() + 1;

      this.markers.push({
        id: `${markerId}`,
        lnglat: item.coordinates
      });

      mutations.setMbglCenter(item.coordinates);
    },
    getLastMarkerId: function () {
      if (isNullOrUndefined(this.markers)) {
        return 0;
      }

      return this.markers
        .map((x) => x.id)
        .reduce((a, b) => {
          return Math.max(a, b);
        });
    }
  }
};
</script>

<style scoped>
#map {
  position: absolute;
  top: 0;
  bottom: 0;
  height: 100%;
  width: 100%;
}

#search {
  position: relative;
  margin: 15px;
  z-index: 1;
}
</style>
```

### The Sample Data ###

For initial data I am adding some sample data in the file ``sample-data.js``.

```javascript
// The Longitude and Latitude of Münster Center.
const LNGLAT_MUENSTER = [7.628202, 51.961563];

// A Marker in Münster City Center.
const MARKER_MUENSTER_CITY_CENTER = {
  id: '1',
  lnglat: LNGLAT_MUENSTER
};

// A walk around Münster Domplatz.
const LINE_WALK_THROUGH_MUENSTER = {
  id: '2',
  path: [
    [7.62566594560235, 51.96209250243865],
    [7.625469237316111, 51.962116744080475],
    [7.625166306555457, 51.96213371322199],
    [7.624902717451505, 51.96214825819561],
    [7.624702074999391, 51.962150682357105],
    [7.624375539244738, 51.962150682357105],
    [7.624147357632523, 51.96214825819561],
    [7.624076542648822, 51.962145834033606],
    [7.624108015974798, 51.96223552793663],
    [7.6241434234666485, 51.962342190722325],
    [7.624182765124488, 51.9624876395668],
    [7.624190633454873, 51.962582181063084],
    [7.624237843444462, 51.96271550847459],
    [7.624273250935062, 51.96280035298457],
    [7.62429292176455, 51.96290943854751],
    [7.624351934249262, 51.96301609973003],
    [7.624430617564826, 51.96313730531105],
    [7.624584050027352, 51.9632391177457],
    [7.6248948491196415, 51.96324639005354],
    [7.6251938457155575, 51.963260934665726],
    [7.625206587356388, 51.96339260581493],
    [7.625197848345579, 51.963492222114525],
    [7.625241543398147, 51.96358106889758],
    [7.6254032150908415, 51.963632223026224],
    [7.62560858183474, 51.963680684778325],
    [7.6257964705583845, 51.96371030026731],
    [7.625993098292952, 51.96371837721594],
    [7.626172248005787, 51.96371837721594],
    [7.626180987016596, 51.96368337709603],
    [7.626189726027405, 51.963605299807625],
    [7.626198465036737, 51.963546068670496],
    [7.626285855140509, 51.96345183715488],
    [7.626386353760495, 51.963354913103416],
    [7.6265130694114305, 51.96324721946752],
    [7.626805826260579, 51.96320683428709],
    [7.626945650426251, 51.96316914141934],
    [7.627041779540718, 51.963080293819786],
    [7.627050518551528, 51.962994138403616],
    [7.627015562509769, 51.96292952173249],
    [7.6269937149842235, 51.96283259655209],
    [7.626989345478819, 51.96274374828542],
    [7.626989345478819, 51.96263605318063],
    [7.627007356767308, 51.96250981619778],
    [7.626996576699412, 51.96238028864178],
    [7.626985796632425, 51.96224079700855],
    [7.626969626531491, 51.96214115986257],
    [7.62692111622755, 51.96207141372844],
    [7.6268833859916185, 51.96202159499458],
    [7.6268510457896355, 51.96198173996751],
    [7.626683954744976, 51.96198173996751],
    [7.626565374003121, 51.96199834623323],
    [7.626441403227432, 51.9620083099895],
    [7.626204241743835, 51.96202823749536],
    [7.626037150699176, 51.96205812873811]
  ],
  color: '#33C9EB'
};

// The URL for the Style of the Map.
const URL_MAPBOX_STYLE = 'http://localhost:9000/static/style/osm_liberty/osm_liberty.json';

// The URL for the Photon Geocoding Search.
const URL_PHOTON_SEARCH = 'http://localhost:9000/search';

export { LNGLAT_MUENSTER, URL_MAPBOX_STYLE, URL_PHOTON_SEARCH, MARKER_MUENSTER_CITY_CENTER, LINE_WALK_THROUGH_MUENSTER };
```

## Conclusion ##

And that's it. In a few hundred lines of code the Mapbox GL JS API has been abstracted away, we have an 
auto complete without external dependencies and can query a Photon Webservice for getting Geocoding results.

Vue.js is an interesting technology to work with. I like its MVVM-approach for providing reactivity a lot, but at 
the same time I find it hard to work without type-safety. Yes, that's JavaScript. And it's possible to use Typescript 
with Vue.js, but this felt more like fighting the framework.

[Vetur]: https://github.com/vuejs/vetur
[MapboxTileServer]: https://github.com/bytefish/MapboxTileServer/