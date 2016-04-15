title: A Spliterator for MatchResults in Java
date: 2016-02-23 08:27
tags: java
category: java
slug: matcher_spliterator
author: Philipp Wagner
summary: A Spliterator for MatchResults.

[MIT License]: https://opensource.org/licenses/MIT

I recently needed to iterate over the ``MatchResult`` of a ``Matcher``, so I have implemented an ``AbstractSpliterator`` for it.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

import java.util.Spliterators;
import java.util.function.Consumer;
import java.util.regex.MatchResult;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

public class MatchSpliterator extends Spliterators.AbstractSpliterator<MatchResult> {

    private Matcher matcher;

    public MatchSpliterator(Matcher matcher) {
        super(Long.MAX_VALUE, NONNULL | ORDERED);

        this.matcher = matcher;
    }

    @Override
    public boolean tryAdvance(Consumer<? super MatchResult> action) {
        if(matcher.find()) {
            action.accept(matcher.toMatchResult());
            return true;
        }
        return false;
    }

    public static Stream<MatchResult> stream(String regex, String input) {
        return stream(Pattern.compile(regex), input);
    }

    public static Stream<MatchResult> stream(Pattern pattern, String input) {
        return stream(pattern.matcher(input));
    }

    public static Stream<MatchResult> stream(Matcher matcher) {
        return StreamSupport.stream(new MatchSpliterator(matcher), false);
    }
}
```