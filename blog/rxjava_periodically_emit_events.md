title: Reactive Programming: Periodically emitting Events with RxJava2
date: 2017-09-17 07:26
tags: java, rxjava, reactive
category: rxjava
slug: reactive_periodically_emitting_events
author: Philipp Wagner
summary: This article shows how to emit values periodically with RxJava2.

[Reactive Extensions]: https://github.com/Reactive-Extensions/Rx.NET
[RxJava]: https://github.com/ReactiveX/RxJava
[RxJS]: https://github.com/Reactive-Extensions/RxJS
[RxJava2]: https://github.com/ReactiveX/RxJava
[RxCpp]: https://github.com/Reactive-Extensions/RxCpp
[Reactive Programming]: https://en.wikipedia.org/wiki/Reactive_programming

[Reactive Programming] is an asynchronous programming language paradigm, which makes it astonishingly easy to work with Data Streams.

I started to work with [Reactive Extensions] in .NET some years ago and by now almost every other programming language has additional 
libraries for Reactive Programming like [RxJava], [RxJS] or [RxCpp]. Like every other technology reactive programming doesn't come 
without its pitfalls and it often has a steep learning curve, but learning it is really worth the time.

Yesterday I needed to emit events periodically in a synchronous fashion in Java, and it is easy with [RxJava]. I think sharing the 
solution is a nice showcase for Reactive Programming.

## RxJava Implementation ##

I needed a simple function, which takes a ``List`` and emits its values in a specified interval. The implementation should be synchronous, so 
I subscribed to the ``Observable`` in a blocking fashion. 

```java
public <TEventType> void emitEvents(Iterable<TEventType> events, Duration duration) {
    Observable.zip(
            Observable.fromIterable(events),
            Observable.interval(duration.toMillis(), TimeUnit.MILLISECONDS),
            (obs, timer) -> obs
    ).blockingSubscribe(new Consumer<TEventType>() {
        @Override
        public void accept(TEventType event) throws Exception {
            // Do something with the event...
        }
    });
}
```

