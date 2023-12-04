title: Google Zanzibar: Implementing the Check API and Expand API using .NET
date: 2023-12-04 20:22
tags: authorization, sql, google zanzibar
category: dotnet
slug: acl_google_zanzibar
author: Philipp Wagner
summary: This article takes the Google Zanzibar a step further and implements the Check API and Expand API in .NET.

In the previous articles we have seen how to implement a very simplified Relationship-based Access Control using 
a Google Zanzibar-like data model and some SQL queries. It worked good, and I quite like what we ended up with. But 
it doesn't let us define an effictive ACL, because at the moment we need to materialize *all relations* in 
the database.

But what about `unions` or `intersections` of permissions? What about modelling statements like: "If you are the `editor` 
of a `Document`, then you are also a `viewer` of a `Document`"? What about inheritance of permissions like: "If you 
are the `viewer` of a `Folder`, then you are also a `viewer` of its `Documents`"? 

So in this article we will take a look at the Google Zanzibar Namespace Configurations, and implement a simplified version 
of the Google Zanzibar Check API and Expand API.

All code can be found in a Git Repository at:

* [https://github.com/bytefish/AclExperiments](https://github.com/bytefish/AclExperiments)

## Table of contents ##

[TOC]

## What we have got so far ##

Let's take a look at what we've got so far.

At the moment the table to store our Relationshuip tuples looks like this:

```sql
CREATE TABLE [Identity].[RelationTuple](
    [RelationTupleID]       INT                                         CONSTRAINT [DF_Identity_RelationTuple_RelationTupleID] DEFAULT (NEXT VALUE FOR [Identity].[sq_RelationTuple]) NOT NULL,
    [ObjectKey]             INT                                         NOT NULL,
    [ObjectNamespace]       NVARCHAR(50)                                NOT NULL,
    [ObjectRelation]        NVARCHAR(50)                                NOT NULL,
    [SubjectKey]            INT                                         NOT NULL,
    [SubjectNamespace]      NVARCHAR(50)                                NOT NULL,
    [SubjectRelation]       NVARCHAR(50)                                NULL,
    -- ...
)
```

And the data? The original Google Zanzibar paper has examples for tuples in their notation:

<table>
    <thead>
        <tr>
            <th>Example Tuple in Text Notation</th>
            <th>Semantics</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>doc:readme#owner@10 </code></td>
            <td>User 10 is an owner of doc:readme</td>
        </tr>
        <tr>
            <td><code>group:eng#member@11</code></td>
            <td>User 11 is a member of group:eng</td>
        </tr>
        <tr>
            <td><code>doc:readme#viewer@group:eng#member</code></td>
            <td>Members of group:eng are viewers of doc:readme</td>
        </tr>
        <tr>
            <td><code>doc:readme#parent@folder:A#...</code></td>
            <td>doc:readme is in folder:A</td>
        </tr>
    </tbody>
</table>

And if we translate this into our relational table we would end up with the following entries:

```
ObjectKey           |  ObjectNamespace  |   ObjectRelation  |   SubjectKey          |   SubjectNamespace      |   SubjectRelation
--------------------|-------------------|-------------------|-----------------------|-------------------------|-------------------
:readme:            |   Document        |       owner       |   :10:                |       User              |   NULL
:engineering:       |   Group           |       member      |   :11:                |       User              |   NULL
:readme:            |   Document        |       viewer      |   :engineering:       |       Group             |   member
:readme:            |   Document        |       parent      |   :A:                 |       Folder            |   NULL
```

I think the Tuples are pretty easy to scan, if you read them from right to left, just like this:

* A `<Subject Relation>` of `<Subject Namespace> <Subject Key> is `<Object Relation>` of `<Object Namespace> <Object Key>`

So for the Tuples given in the Zanzibar Paper we can scan them like this:

* `User :10:` is *owner*  of `Document  :readme:`
* `User :11:` is *member* of `Group :engineering:`
* A *member* of `Group :engineering:` is a *viewer* of `Document :readme:`
* `Folder :A:` is *parent* of `Document :readme:`

We have previously written a T-SQL Function `[Identity].[udf_RelationTuples_Check]` to implement a function for 
checking if a `User` has a `Relation` to a given `Object` and thus has permission. It can be expressed in a 
few lines of SQL using a Common Table Expression (CTE).

```sql
CREATE FUNCTION [Identity].[udf_RelationTuples_Check]
(
     @ObjectNamespace NVARCHAR(50)
    ,@ObjectKey INT
    ,@ObjectRelation NVARCHAR(50)
    ,@SubjectNamespace NVARCHAR(50)
    ,@SubjectKey INT
)
RETURNS BIT
AS
BEGIN

    DECLARE @IsAuthorized BIT = 0;

    WITH RelationTuples AS
    (
       SELECT
    	   [RelationTupleID]
          ,[ObjectNamespace]
          ,[ObjectKey]
          ,[ObjectRelation]
          ,[SubjectNamespace]
          ,[SubjectKey]
          ,[SubjectRelation]
    	  , 0 AS [HierarchyLevel]
        FROM
          [Identity].[RelationTuple]
        WHERE
    		[ObjectNamespace] = @ObjectNamespace AND [ObjectKey] = @ObjectKey AND [ObjectRelation] = @ObjectRelation
    	  
    	UNION All
    	
    	SELECT        
    	   r.[RelationTupleID]
    	  ,r.[ObjectNamespace]
          ,r.[ObjectKey]
          ,r.[ObjectRelation]
          ,r.[SubjectNamespace]
          ,r.[SubjectKey]
          ,r.[SubjectRelation]
    	  ,[HierarchyLevel] + 1 AS [HierarchyLevel]
      FROM 
    	[Identity].[RelationTuple] r, [RelationTuples] cte
      WHERE 
    	cte.[SubjectKey] = r.[ObjectKey] 
    		AND cte.[SubjectNamespace] = r.[ObjectNamespace] 
    		AND cte.[SubjectRelation] = r.[ObjectRelation]
    )
    SELECT @IsAuthorized =
    	CASE
    		WHEN EXISTS(SELECT 1 FROM [RelationTuples] WHERE [SubjectNamespace] = @SubjectNamespace AND [SubjectKey] = @SubjectKey) 
    			THEN 1
    		ELSE 0
    	END;

    RETURN @IsAuthorized;
END
```

But this function is not an effective Access Control List, the Google Zanzibar Paper notes on it:

> While relation tuples reflect relationships between `objects` and `users`, they do not completely define the 
> effective ACLs. For example, some clients specify that users with *editor* permissions on each object 
> should have *viewer* permission on the same object. 
>
> While such relationships between relations can be represented by a relation tuple per object, storing a 
> tuple for each object in a namespace would be wasteful and make it hard to make modifications across all 
> objects. 
>
> Instead, we let clients define object-agnostic relationships via userset rewrite rules in relation configs.

The Zanzibar Paper then goes on to define a so called "Namespace Configuration Language" and shares some 
Pseudo-Code for it ...

```
name: "doc"
    
relation { name: "owner" }

relation {
    name: "editor"
    userset_rewrite {
        union {
            child { _this {} }
            child { computed_userset { relation: "owner" } }
} } }
relation {
    name: "viewer"
    userset_rewrite {
        union {
            child { _this {} }
            child { computed_userset { relation: "editor" } }
            child { tuple_to_userset {
                tupleset { relation: "parent" }
                computed_userset {
                    object: $TUPLE_USERSET_OBJECT # parent folder
                    relation: "viewer"
            } } }
} } }
```

The Pseudo-Code introduces several Node Types for so called "Userset Rewrite Rules", such as `_this`, `computed_userset` 
and `tuple_to_userset`...

<table>
    <thead>
        <tr>
            <th>Node Type</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>_this</code></td>
            <td>
                <p>
                    Returns all users from stored relation tuples for the <code>object#relation</code> pair, including 
                    indirect ACLs referenced by usersets from the tuples. This is the default behavior when no rewrite 
                    rule is specified.
                </p>
            </td>
        </tr>
        <tr>
            <td><code>computed_userset</code></td>
            <td>
                <p>
                    Computes, for the input object, a new userset. For example, this allows the userset expression for 
                    a viewer relation to refer to the editor userset on the same object, thus offering an ACL inheritance 
                    capability between relations.
                </p>
            </td>
        </tr>
        <tr>
            <td><code>tuple_to_userset</code></td>
            <td>
                <p>
                    Computes a tupleset (§2.4.1) from the input object, fetches relation tuples matching the tupleset, and computes 
                    a userset from every fetched relation tuple. This flexible primitive allows our clients to express complex 
                    policies such as "Look up the <i>parent</i> <code>Folder</code> of the <code>Document</code> and inherit 
                    its <i>viewers</i>".</p></td>
        </tr>
    </tbody>
</table>


What do we see here? To me it's a super weird terminology, that probably makes a lot of sense within Google, but not so much 
for my brain. I've read somewhere, that this is what the Protocol Buffer representation looks like an not neccessarily the 
actual configuration. I don't know. I will just implement it as is.

So let's try to break it down a bit, with my somewhat dangerously uninformed knowledge.

At Google there is a concept of Namespaces, most probably for partitioning the data within their distributed database like a 
`doc`, a `folder` and so on:

```
name: "doc"
```

All Objects in a a Namespace have Relations to a `Subject`, which can be expressed like this:

```
relation { name: "owner" }
```

This merely states, that there is a "direct" relationship between a `doc` and a `User` or `UserSet`, which 
is materialized in the database. This is interesting for validation, but we can't express any complex rules 
with it.

To "compute" relations, that are not materialized, Google introduced a `userset_rewrite`. A `userset_rewrite` always 
contains a set operation, such as `union`, `intersect` or `exclude`, and the child nodes of the set operation can be 
the `_this` leaf node, a `computed_userset` or a `tuple_to_userset`.

The paper has the following example, which states "If you are an `owner` of the `Document`, you are also the `editor` 
of the `Document`".

```   
relation {
    name: "editor"

    userset_rewrite {
        union {
            child { _this {} }
            child { computed_userset { relation: "owner" } }
        } 
    } 
}
```

So we could rewrite the first expression also as:

```
relation { 
    name: "owner" 
    
    userset_rewrite {
        union {
            child { _this {} }
        }
    }
}
```

But if, say, you want to authorize access to Google Drive items. You have to implement rules like: "You are the 
`viewer` of a `Document`, if you have a direct `viewer` relation to the `Document` OR you are an `editor` of the 
document OR you are a `viewer` of the parent `Folder`".

This done by using a `tuple_to_userset` operation. It starts by defining a `tupleset`, which according to the paper ...

> [...] specifies keys of a set of relation tuples. The set can include a single 
> tuple key, or all tuples with a given object ID or userset in a namespace, optionally 
> constrained by a relation name. 

To me a `tupleset` are  "All Relations with a given name between the related `Object` and a `User` or a `UserSet`".

```
relation {
    name: "viewer"
    userset_rewrite {
        union {
            child { _this {} }
            child { computed_userset { relation: "editor" } }
            child { tuple_to_userset {
                tupleset { 
                    relation: "parent" 
                }
                computed_userset {
                    object: $TUPLE_USERSET_OBJECT
                    relation: "viewer"
            } } }
} } }```


## Parsing the Google Zanzibar Configuration Language ##

[Kjell Holmgren]: https://github.com/kholmgren/
[acl-rewrite]: https://github.com/kholmgren/acl-rewrite

The first thing we need to do is to parse the namespace configuration language as described in the Google Zanzibar 
paper. We could try to hand-roll a Lexer and Parser for the language, but there's ANTLR4 we could use to generate the 
code.

### An ANTLR4 Grammar for the Configuration Language ###

After spending some hours learning ANTLR4 syntax and an amateurish Grammar, I have seen, that there's already an ANTLR4 
Grammar for the Google Zanzibar Configuration Language on GitHub, which was written by [Kjell Holmgren]. So all credit 
goes to him, his [acl-rewrite] is a great project and I've learnt tons about Google Zanzibar.

```antlr
/** 
  * This Grammar was written by Kjell Holmgren (https://github.com/kholmgren):
  * 
  *     - https://github.com/kholmgren/acl-rewrite/blob/master/src/main/antlr4/io/kettil/rewrite/parser/UsersetRewrite.g4
  */
grammar UsersetRewrite;

options { caseInsensitive=true; }

@header {#pragma warning disable 3021}

namespace
    : 'name' ':' namespaceName=STRING relation* EOF
    ;

relation
    : 'relation' '{' 'name' ':' relationName=STRING usersetRewrite? '}'
    ;

usersetRewrite
    : 'userset_rewrite' '{' userset '}'
    ;

userset
    : childUserset
    | computedUserset
    | setOperationUserset
    | thisUserset
    | tupleToUserset
    ;

childUserset
    : 'child' '{' userset '}'
    ;

computedUserset
    : 'computed_userset' '{' (usersetNamespaceRef | usersetObjectRef | usersetRelationRef)+ '}'
    ;

usersetNamespaceRef
    : 'namespace' ':' ref=(STRING | TUPLE_USERSET_NAMESPACE)
    ;

usersetObjectRef
    : 'object' ':' ref=(STRING | TUPLE_USERSET_OBJECT)
    ;

usersetRelationRef
    : 'relation' ':' ref=(STRING | TUPLE_USERSET_RELATION)
    ;

thisUserset
    : '_this' '{' '}'
    ;

tupleToUserset
    : 'tuple_to_userset' '{' tupleset computedUserset '}'
    ;

tupleset
    : 'tupleset' '{' (namespaceRef | objectRef | relationRef)+ '}'
    ;

namespaceRef
    : 'namespace' ':' ref=STRING
    ;

objectRef
    : 'object' ':' ref=STRING
    ;

relationRef
    : 'relation' ':' ref=STRING
    ;

setOperationUserset
    : op=(UNION | INTERSECT | EXCLUDE) '{' userset* '}'
    ;

UNION
    : 'union'
    ;

INTERSECT
    : 'intersect'
    ;

EXCLUDE
    : 'exclude'
    ;

TUPLE_USERSET_NAMESPACE
    : '$TUPLE_USERSET_NAMESPACE'
    ;

TUPLE_USERSET_OBJECT
    : '$TUPLE_USERSET_OBJECT'
    ;

TUPLE_USERSET_RELATION
    : '$TUPLE_USERSET_RELATION'
    ;

STRING
   : '"' ~["]* '"'
   | '\'' ~[']* '\''
   ;

SINGLE_LINE_COMMENT
   : '//' .*? (NEWLINE | EOF) -> skip
   ;

MULTI_LINE_COMMENT
   : '/*' .*? '*/' -> skip
   ;

IDENTIFIER
   : IDENTIFIER_START IDENTIFIER_PART*
   ;
fragment IDENTIFIER_START
   : [\p{L}]
   | '$'
   | '_'
   ;
fragment IDENTIFIER_PART
   : IDENTIFIER_START
   | [\p{M}]
   | [\p{N}]
   | [\p{Pc}]
   | '\u200C'
   | '\u200D'
   ;
fragment NEWLINE
   : '\r\n'
   | [\r\n\u2028\u2029]
   ;

WS
   : [ \t\n\r\u00A0\uFEFF\u2003] + -> skip
   ;
```

### Generating the C\# Lexer and Parser ###

The Grammar is unlikely to change, so it's totally fine for us to create it manually and not embed it in a build step. From 
the ANTLR homepage I am downloading the `antlr-4.13.1-complete.jar` and put it in a `tools` folder. In the root folder, we 
then create a file `makeUsersetRewriteParser.bat`:

```batch
@echo off

:: Licensed under the MIT license. See LICENSE file in the project root for full license information.

:: ANTLR4 Executable
set ANTLR4_JAR=%~dp0tools\antlr-4.13.1-complete.jar  

:: Parameters for the Code Generator
set PARAM_USERSET_GRAMMAR=%~dp0\RebacExperiments\RebacExperiments.Acl\Ast\UsersetRewrite.g4
set PARAM_OUTPUT_FOLDER=%~dp0\RebacExperiments\RebacExperiments.Acl\Ast\Generated
set PARAM_NAMESPACE=RebacExperiments.Acl.Ast.Generated

:: Run the "Antlr4" Code Generator
java -jar %ANTLR4_JAR%^
    -package %PARAM_NAMESPACE%^
    -visitor^
    -no-listener^
    -Dlanguage=CSharp^
    -Werror^
    -o %PARAM_OUTPUT_FOLDER%^
    %PARAM_USERSET_GRAMMAR%
```

Works! But the generated code contains some warnings, that we need to suppress. So we add a `#pragma` directive to 
both the Lexer and Parser for suppressing these warnings explicitly.

```antlr
grammar UsersetRewrite;

@parser::header {#pragma warning disable 3021}
@lexer::header {#pragma warning disable 3021}

namespace
    : 'name' ':' namespaceName=STRING relation* EOF
    ;
    
# ...
```

We can now see the files being created for the Grammar:

```
PS > .\makeUsersetRewriteParser.bat
PS > tree /f .\src\AclExperiments\Parser\
│
│   UsersetRewrite.g4
│
└───Generated
        UsersetRewrite.interp
        UsersetRewrite.tokens
        UsersetRewriteBaseVisitor.cs
        UsersetRewriteLexer.cs
        UsersetRewriteLexer.interp
        UsersetRewriteLexer.tokens
        UsersetRewriteParser.cs
        UsersetRewriteVisitor.cs
```

### Defining the Abstract Syntax Tree ###

What's next is parsing the namespace configuration to an Abstract Syntax Tree (AST).

Every Experession in the namespace configuration language is a `UsersetExpression`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// Base class for all Userset Expressions.
    /// </summary>
    public abstract record UsersetExpression
    {
    }
}
```

The root node is a `NamespaceUsersetExpression`, which has a name and its relations:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// The root node of the Zanzibar Configuration language. It contains the 
    /// name of the configured subject and an optional list of relations, expressed 
    /// as <see cref="RelationUsersetExpression"/>.
    /// </summary>
    public record NamespaceUsersetExpression : UsersetExpression
    {
        /// <summary>
        /// Gets or sets the Namespace being configured.
        /// </summary>
        public required string Name { get; set; }

        /// <summary>
        /// Gets or sets the Relations expressed by the Namespace configuration.
        /// </summary>
        public Dictionary<string, RelationUsersetExpression> Relations { get; set; } = new();
    }
}
```

A `RelationUsersetExpression` defines the relation name and has a `UsersetRewrite` associated. If the namespace 
configuration just contains a name, we assume to just use the direct relations, expressed by the 
`ThisUsersetExpression`:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// A Relation is expressed by its name and an optional rewrite, which is expressed as a 
    /// <see cref="UsersetExpression"/>. 
    /// </summary>
    public record RelationUsersetExpression : UsersetExpression
    {
        public required string Name { get; set; }

        public UsersetExpression Rewrite { get; set; } = new ThisUsersetExpression();
    }
}
```

In the paper we can see Relations having either no Userset rewrite assigned or having a union of userset rewrites, 
so you can have a union of... Direct relations stored in the database (`ThisUsersetExpression`), Computed Usersets 
(`ComputedUsersetExpression`) or inherited permissions (`TupleToUsersetExpression`).

The `_this` userset rewrite states to return the tupleset of all matching materialized relations:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// Returns all users from stored relation tuples for the <code>object#relation</code> pair, including 
    /// indirect ACLs referenced by usersets from the tuples.This is the default behavior when no rewrite
    /// rule is specified.
    /// </summary>
    public record ThisUsersetExpression : UsersetExpression
    {
    }
}
```

The `computed_userset` is expressed by using a `ComputedUsersetExpression`. It allows us to define inheritance 
of relations, such as *"You are a `viewer` of a document, if you are the `editor` of a document"*.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// Computes, for the input object, a new userset. For example, this allows the userset expression for 
    /// a viewer relation to refer to the editor userset on the same object, thus offering an ACL inheritance
    /// capability between relations.
    /// </summary>
    public record ComputedUsersetExpression : UsersetExpression
    {
        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public string? Namespace { get; set; }

        /// <summary>
        /// Gets or sets the Object,
        /// </summary>
        public string? Object { get; set; }

        /// <summary>
        /// Gets or sets the Relation.
        /// </summary>
        public string? Relation { get; set; }
    }
}
```

To model something statements like *"You are the `viewer` of a document, if you are the `viewer` of the documents `parent` folder"*, 
we need a `tuple_to_userset` expression, which is defined in the `TupleToUsersetExpression` expression.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    ///  Computes a tupleset (§2.4.1) from the input object, fetches relation tuples matching the tupleset, and computes 
    ///  a userset from every fetched relation tuple.This flexible primitive allows our clients to express complex
    ///  policies such as "Look up the 'parent' Folder of the Document and inherit 
    ///  its 'viewers'".
    /// </summary>
    public record TupleToUsersetExpression : UsersetExpression
    {
        /// <summary>
        /// Gets or sets the Tupleset.
        /// </summary>
        public required TuplesetExpression TuplesetExpression { get; set; }

        /// <summary>
        /// Gets or sets the Computer Userset.
        /// </summary>
        public required ComputedUsersetExpression ComputedUsersetExpression { get; set; }
    }
}
```

The `TuplesetExpression` holds the information, which set of relation tuples is going to passed to 
the computed userset rewrite: 

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// Each tupleset specifies keys of a set of relation tuples. The set can include a single tuple key, or 
    /// all tuples with a given object ID or userset in a namespace, optionally constrained by a relation 
    /// name.
    /// </summary>
    public record TuplesetExpression : UsersetExpression
    {
        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public string? Namespace;

        /// <summary>
        /// Gets or sets the Object.
        /// </summary>
        public string? Object { get; set; }

        /// <summary>
        /// Gets or sets the Relation.
        /// </summary>
        public required string Relation { get; set; }
    }
}
```

Now where it gets interesting in the Google Zanzibar paper is the Set Operations. You can no only include relation tuples 
in your result set, but also apply set operations on them, such as `union`, `intersection` or `exclude`. We can model this 
in a `SetOperationEnum` enumeration:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// The Set Operation to apply for a <see cref="UsersetExpression"/>.
    /// </summary>
    public enum SetOperationEnum
    {
        /// <summary>
        /// Unions together the relations/permissions referenced.
        /// </summary>
        Union = 1,

        /// <summary>
        /// Intersects the set of subjects found for the relations/permissions referenced.
        /// </summary>
        Intersect = 2,

        /// <summary>
        /// Excludes the set of subjects found for the relations/permissions referenced.
        /// </summary>
        Exclude = 3,
    }
}
```

The `SetOperationUsersetExpression` now contains the operation and the list of children.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Expressions
{
    /// <summary>
    /// Userset Expressions can be expressed as a union, intersection, ... and more 
    /// set operations, so we are able to define more complex authorization rules..
    /// </summary>
    public record SetOperationUsersetExpression : UsersetExpression
    {
        /// <summary>
        /// Gets or sets the Set Operation, such as a Union.
        /// </summary>
        public SetOperationEnum Operation { get; set; }

        /// <summary>
        /// Gets or sets the Children.
        /// </summary>
        public required List<UsersetExpression> Children { get; set; }
    }
}
```

### Parsing the Namespace Configuration to the Userset Expression Tree ###

We have previously generated a Lexer and a Parser using ANTLR4. We have also passed the `visitor` flag, so 
a Visitor named `UsersetRewriteBaseVisitor` has been created for us. This Visitor can be used to transform 
the ANTLR4 parse tree to our previously defined Abstract Syntax Tree.

That's a relatively simple task, because our AST mostly looks like the Grammar we have defined.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using Antlr4.Runtime;
using Antlr4.Runtime.Misc;
using AclExperiments.Expressions;
using AclExperiments.Parser.Generated;
using static AclExperiments.Parser.Generated.UsersetRewriteParser;

namespace AclExperiments.Parser
{
    public class NamespaceUsersetRewriteParser
    {
        public static NamespaceUsersetExpression Parse(string text)
        {
            var charStream = CharStreams.fromString(text);

            return Parse(charStream);
        }

        private static NamespaceUsersetExpression Parse(ICharStream input)
        {
            var parser = new UsersetRewriteParser(new CommonTokenStream(new UsersetRewriteLexer(input)));

            return (NamespaceUsersetExpression)new UsersetRewriteVisitor().Visit(parser.@namespace());
        }

        private class UsersetRewriteVisitor : UsersetRewriteBaseVisitor<UsersetExpression>
        {
            public override UsersetExpression VisitNamespace([NotNull] NamespaceContext context)
            {
                return new NamespaceUsersetExpression
                {
                    Name = Unquote(context.namespaceName.Text),
                    Relations = context.relation()
                        .Select(VisitRelation)
                        .Cast<RelationUsersetExpression>()
                        .ToDictionary(x => x.Name, x => x)
                };
            }

            public override UsersetExpression VisitRelation([NotNull] RelationContext context)
            {
                return new RelationUsersetExpression
                {
                    Name = Unquote(context.relationName.Text),
                    Rewrite = context.usersetRewrite() != null ? VisitUsersetRewrite(context.usersetRewrite()) : new ChildUsersetExpression { Userset = new ThisUsersetExpression() }
                };
            }

            public override UsersetExpression VisitUsersetRewrite([NotNull] UsersetRewriteContext context)
            {
                if (context.userset() == null)
                {
                    return new ChildUsersetExpression { Userset = new ThisUsersetExpression() };
                }

                return VisitUserset(context.userset());
            }

            public override UsersetExpression VisitChildUserset([NotNull] ChildUsersetContext context)
            {
                return new ChildUsersetExpression
                {
                    Userset = VisitUserset(context.userset())
                };
            }

            public override UsersetExpression VisitComputedUserset([NotNull] ComputedUsersetContext context)
            {
                string? @namespace = null;

                if (context.usersetNamespaceRef().Length > 1)
                {
                    throw new InvalidOperationException("More than one namespace specified");
                }

                if (context.usersetNamespaceRef().Length != 0)
                {
                    var usersetNamespaceRefContext = context.usersetNamespaceRef().First();

                    switch (usersetNamespaceRefContext.@ref.Type)
                    {
                        case STRING:
                            @namespace = Unquote(usersetNamespaceRefContext.STRING().GetText());
                            break;

                        case TUPLE_USERSET_NAMESPACE:
                            @namespace = UsersetRef.TUPLE_USERSET_NAMESPACE;
                            break;
                    }
                }

                string? @object = null;

                if (context.usersetObjectRef().Length > 1)
                {
                    throw new InvalidOperationException("More than one object specified");
                }

                if (context.usersetObjectRef().Length != 0)
                {
                    var usersetObjectRefContext = context.usersetObjectRef().First();

                    switch (usersetObjectRefContext.@ref.Type)
                    {
                        case STRING:
                            @object = Unquote(usersetObjectRefContext.STRING().GetText());
                            break;

                        case TUPLE_USERSET_OBJECT:
                            @object = UsersetRef.TUPLE_USERSET_OBJECT;
                            break;
                    }
                }

                if (@namespace == null && UsersetRef.TUPLE_USERSET_OBJECT.Equals(@object))
                {
                    @namespace = UsersetRef.TUPLE_USERSET_NAMESPACE;
                }

                string relation = string.Empty;

                if (context.usersetRelationRef().Length > 1)
                {
                    throw new InvalidOperationException("More than one relation specified"); 
                }

                if (context.usersetRelationRef().Length != 0)
                {
                    var usersetRelationRefContext = context.usersetRelationRef().First();

                    switch (usersetRelationRefContext.@ref.Type)
                    {
                        case STRING:
                            relation = Unquote(usersetRelationRefContext.STRING().GetText());
                            break;

                        case TUPLE_USERSET_RELATION:
                            relation = UsersetRef.TUPLE_USERSET_RELATION;
                            break;
                    }
                }

                return new ComputedUsersetExpression
                {
                    Namespace = @namespace,
                    Object = @object,
                    Relation = relation
                };
            }

            public override UsersetExpression VisitSetOperationUserset([NotNull] SetOperationUsersetContext context)
            {
                var op = context.op.Type switch
                {
                    UNION => SetOperationEnum.Union,
                    INTERSECT => SetOperationEnum.Intersect,
                    _ => throw new ArgumentException(nameof(context.op.Type)),
                };

                return new SetOperationUsersetExpression
                {
                    Operation = op,
                    Children = context.userset()
                        .Select(x => x.Accept(this))
                        .ToList()
                };
            }

            public override UsersetExpression VisitThisUserset([NotNull] ThisUsersetContext context)
            {
                return new ThisUsersetExpression();
            }

            public override UsersetExpression VisitTupleset([NotNull] TuplesetContext context)
            {
                string? @namespace = null;

                if (context.namespaceRef().Length > 1)
                {
                    throw new InvalidOperationException("More than one namespace specified");
                }

                if (context.namespaceRef().Length != 0)
                {
                    @namespace = Unquote(context.namespaceRef().First().@ref.Text);
                }

                string? @object = null;

                if (context.objectRef().Length > 1)
                {
                    throw new InvalidOperationException("More than one object specified");
                }

                if (context.objectRef().Length != 0)
                {
                    @object = Unquote(context.objectRef().First().@ref.Text);
                }

                string relation = string.Empty;

                if (context.relationRef().Length > 1)
                {
                    throw new InvalidOperationException("More than one relation specified");
                }

                if (context.relationRef().Length != 0)
                {
                    relation = Unquote(context.relationRef().First().@ref.Text);
                }

                return new TuplesetExpression
                {
                    Namespace = @namespace,
                    Object = @object,
                    Relation = relation
                };
            }

            public override UsersetExpression VisitTupleToUserset([NotNull] TupleToUsersetContext context)
            {
                return new TupleToUsersetExpression
                {
                    TuplesetExpression = (TuplesetExpression)VisitTupleset(context.tupleset()),
                    ComputedUsersetExpression = (ComputedUsersetExpression)VisitComputedUserset(context.computedUserset())
                };
            }

            private static string Unquote(string value)
            {
                return value.Trim('"');
            }
        }
    }
}
```

We can now write a test, to see if it works as expected, in here we only want to see if it parses the configuration without errors.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AclExperiments.Expressions;
using AclExperiments.Parser;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace AclExperiments.Tests.Parser
{
    [TestClass]
    public class NamespaceUsersetRewriteParserTests
    {
        /// <summary>
        /// Parses the namespace configuration described in Google Zanzibar paper:
        /// 
        ///             name: "doc"
        ///             
        ///             relation { name: "owner" }
        ///         
        ///             relation {
        ///                 name: "editor"
        ///         
        ///                 userset_rewrite {
        ///                     union {
        ///                         child { _this {} }
        ///                         child { computed_userset { relation: "owner" } }
        ///                     } } }
        ///             
        ///             relation {
        ///                 name: "viewer"
        ///                 userset_rewrite {
        ///                     union {
        ///                         child { _this {} }
        ///                         child { computed_userset { relation: "editor" } }
        ///                         child { tuple_to_userset {
        ///                             tupleset { 
        ///                                 relation: "parent"
        ///                             }
        ///                             computed_userset {
        ///                                 object: $TUPLE_USERSET_OBJECT
        ///                                 relation: "viewer"
        ///                         } } }
        ///         } } }
        /// </summary>
        [TestMethod]
        public void NamespaceUsersetRewriteParser_GoogleZanzibarExample_CheckAstBasic()
        {
            // Arrange
            var namespaceConfigText = File.ReadAllText("./Resources/doc.nsconfig");

            // Act
            var namespaceConfig = NamespaceUsersetRewriteParser.Parse(namespaceConfigText);

            // Assert
            Assert.AreEqual("doc", namespaceConfig.Name);

            Assert.AreEqual(3, namespaceConfig.Relations.Count);

            Assert.AreEqual(true, namespaceConfig.Relations.ContainsKey("owner"));
            Assert.AreEqual(true, namespaceConfig.Relations.ContainsKey("editor"));
            Assert.AreEqual(true, namespaceConfig.Relations.ContainsKey("viewer"));
        }
```

## Database Design and Data Access  ##

The database for the example is going to have 3 tables:

* `[Identity].[User]`
    * The User is required to audit all data modifications.
* `[Identity].[NamespaceConfiguration]`
    * The Namespace Configuration in the Google Zanzibar configuration language.
* `[Identity].[RelationTuple]`
    * The materialized Relation Tuples to with the Object-Relation-Subject information

We are going to use System Versioning (Temporal Tables) for all tables, so we can audit changes. The `[Identity].[User]` holds 
the user information, which is referenced when auditing the changes.

```sql
CREATE TABLE [Identity].[User](
    [UserID]                INT                                         CONSTRAINT [DF_Identity_User_UserID] DEFAULT (NEXT VALUE FOR [Identity].[sq_User]) NOT NULL,
    [FullName]              NVARCHAR(50)                                NOT NULL,
    [PreferredName]         NVARCHAR(50)                                NULL,
    [IsPermittedToLogon]    BIT                                         NOT NULL,
    [LogonName]             NVARCHAR (256)                              NULL,
    [HashedPassword]        NVARCHAR (MAX)                              NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_User] PRIMARY KEY ([UserID]),
    CONSTRAINT [FK_User_LastEditedBy_User_UserID] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[UserHistory]));
```

The Namespace Configurations are going to be stored in a Table `[Identity].[NamespaceConfiguration]`. All Rows also have a version, because we might need them to understand past Authorization decisions. 

```sql
CREATE TABLE [Identity].[NamespaceConfiguration](
    [NamespaceConfigurationID]      INT                                         CONSTRAINT [DF_Identity_NamespaceConfiguration_NamespaceConfigurationID] DEFAULT (NEXT VALUE FOR [Identity].[sq_NamespaceConfiguration]) NOT NULL,
    [Name]                          NVARCHAR(255)                               NOT NULL,
    [Content]                       NVARCHAR(MAX)                               NOT NULL,
    [Version]                       INT                                         NOT NULL,
    [RowVersion]                    ROWVERSION                                  NULL,
    [LastEditedBy]                  INT                                         NOT NULL,
    [ValidFrom]                     DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]                       DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_NamespaceConfiguration] PRIMARY KEY ([NamespaceConfigurationID]),
    CONSTRAINT [FK_NamespaceConfiguration_LastEditedBy_User_UserID] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[NamespaceConfigurationHistory]));
```

The Relation Tuples are going to be stored in a Table `[Identity].[RelationTuple]`.

```sql
CREATE TABLE [Identity].[RelationTuple](
    [RelationTupleID]       INT                                         CONSTRAINT [DF_Identity_RelationTuple_RelationTupleID] DEFAULT (NEXT VALUE FOR [Identity].[sq_RelationTuple]) NOT NULL,
    [Namespace]             NVARCHAR(50)                                NOT NULL,
    [Object]                NVARCHAR(50)                                NOT NULL,
    [Relation]              NVARCHAR(50)                                NOT NULL,
    [Subject]               NVARCHAR(50)                                NOT NULL,
    [RowVersion]            ROWVERSION                                  NULL,
    [LastEditedBy]          INT                                         NOT NULL,
    [ValidFrom]             DATETIME2 (7) GENERATED ALWAYS AS ROW START NOT NULL,
    [ValidTo]               DATETIME2 (7) GENERATED ALWAYS AS ROW END   NOT NULL,
    CONSTRAINT [PK_RelationTuple] PRIMARY KEY ([RelationTupleID]),
    CONSTRAINT [FK_RelationTuple_LastEditedBy_User_UserID] FOREIGN KEY ([LastEditedBy]) REFERENCES [Identity].[User] ([UserID]),
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = [Identity].[RelationTupleHistory]));
```

Everything is put into a nicely structured SQL Server Database Project, which can be used to create the database and create scripts, without ever leaving Visual Studio. 

## AclService: A .NET Implementation for the Expand and Check API ##

We are creating a class named `AclService`, which is going to implement the Google Zanzibar Check and Expand APIs. 

To do this, the `AclService` uses two dependencies, I didn't show in the article, the `INamespaceConfigurationStore` and 
the `IRelationTupleStore`. The `IRelationTupleStore` provides methods to query for materialized relation tuples, the 
`INamespaceConfigurationStore` is used to query for available namespace configurations.


### The ACL Domain Model ###

Now let's start with the domain model we are going to work with.

Objects in Google Zanzibar always have a `Namespace` and an `Id`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Models
{
    /// <summary>
    /// The Object of an Object to Subject Relation.
    /// </summary>
    public record AclObject
    {
        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public required string Namespace { get; set; }

        /// <summary>
        /// Gets or sets the Id.
        /// </summary>
        public required string Id { get; set; }
    }
}
```

For Subjects we need to differentiate between a `UserId` and a `Userset`. In a later article or incarnation, we might 
not only authorize users, so I have called these a `SubjectId` and a `SubjectSet`. Both have a common base class 
`AclSubject`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Models
{
    /// <summary>
    /// Base class for Subjects, which is either a <see cref="AclSubjectId"/> or a <see cref="AclSubjectSet"/>.
    /// </summary>
    public abstract record AclSubject
    {
        /// <summary>
        /// Formats the given <see cref="AclSubject"/> as a <see cref="string"/>.
        /// </summary>
        /// <returns>Textual Representation of the <see cref="AclSubject"/></returns>
        public abstract string FormatString();
    }
}
```

A `SubjectId` refers to the specific user and only contains the User ID.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Models
{
    /// <summary>
    /// A Subject ID.
    /// </summary>
    public record AclSubjectId : AclSubject
    {
        /// <summary>
        /// Gets or sets the ID.
        /// </summary>
        public required string Id { get; set; }

        public static AclSubjectId FromString(string s)
        {
            return new AclSubjectId { Id = s };
        }

        public override string FormatString()
        {
            return Id;
        }
    }
}
```

A Userset is defined by a Namespace, Object and Relation, in the format `<Namespace>:<Object>#<Relation>`, 
to express something like group members having viewer access to a document, we would write something like: 
`doc:1#viewer@group:2#member`. 

Something interesting to notice is, how the textual representation of the Tuple in the Google Zanzibar paper models 
the relationship between the document and the parent folder as as a SubjectSet: `doc:doc_1#parent@folder:folder_1#...` 
using the special relation `...`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Models
{
    /// <summary>
    /// A Subject Set.
    /// </summary>
    public record AclSubjectSet : AclSubject
    {
        /// <summary>
        /// Gets or sets the Namespace.
        /// </summary>
        public required string Namespace { get; set; }

        /// <summary>
        /// Gets or sets the Object.
        /// </summary>
        public required string Object { get; set; }

        /// <summary>
        /// Gets or sets the Relation.
        /// </summary>
        public required string Relation { get; set; }

        /// <summary>
        /// Formats the <see cref="AclSubjectSet"/> as a <see cref="string"/> in the Google Zanzibar notation.
        /// </summary>
        /// <returns>The textual SubjectSet representation</returns>
        public override string FormatString()
        {
            return string.Format("{0}:{1}#{2}", Namespace, Object, Relation);
        }

        /// <summary>
        /// Parses a given <see cref="string"/> in Google Zanzibar notation to an <see cref="AclSubjectSet"/>.
        /// </summary>
        /// <param name="s">Textual representation of a Subject Set in Google Zanzibar notation</param>
        /// <returns>The <see cref="AclSubject"/> for the given text</returns>
        /// <exception cref="InvalidOperationException">Thrown, if the input string is not a valid SubjectSet</exception>
        public static AclSubjectSet FromString(string s)
        {
            var parts = s.Split("#");

            if (parts.Length != 2)
            {
                throw new InvalidOperationException("Invalid SubjectSet String");
            }

            var innerParts = parts[0].Split(":");

            if (innerParts.Length != 2)
            {
                throw new InvalidOperationException("Invalid SubjectSet String");
            }

            return new AclSubjectSet
            {
                Namespace = innerParts[0],
                Object = innerParts[1],
                Relation = parts[1]
            };
        }
    }
}
```

The `Object` and the `Subject` are connected via a `Relation`. We model this as a `AclRelation` object:

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

namespace AclExperiments.Models
{
    /// <summary>
    /// A Relation between an Object and a Subject (or SubjectSet).
    /// </summary>
    public record AclRelation
    {
        /// <summary>
        /// Gets or sets the Object.
        /// </summary>
        public required AclObject Object { get; set; }

        /// <summary>
        /// Gets or sets the Relation.
        /// </summary>
        public required string Relation { get; set; }

        /// <summary>
        /// Gets or sets the Subject.
        /// </summary>
        public required AclSubject Subject { get; set; }
    }
}
```

Finally we need a was to convert between a given Google Zanzibar subject notation (`user_1`, `folder:folder_1#...`) and 
the `AclSubject` (`AclSubjectId` or a `AclSubject`). This is put into a static class `AclSubjects`.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AclExperiments.Models;

namespace AclExperiments.Utils
{
    /// <summary>
    /// Utility methods for working with an <see cref="AclSubject"/>.
    /// </summary>
    public static class AclSubjects
    {
        /// <summary>
        /// Converts a given string to a <see cref="AclSubject"/>, which is either a <see cref="AclSubjectId"/> or a <see cref="AclSubjectSet"/>.
        /// </summary>
        /// <param name="s">Subject String in Google Zanzibar Notation</param>
        /// <returns>The <see cref="AclSubject"/></returns>
        public static AclSubject SubjectFromString(string s)
        {
            if (s.Contains('#'))
            {
                return AclSubjectSet.FromString(s);
            }

            return AclSubjectId.FromString(s);
        }

        /// <summary>
        /// Converts a given <see cref="AclSubject"/> to the textual Google Zanzibar representation.
        /// </summary>
        /// <param name="s">Subject, which is either a SubjectId or SubjectSet</param>
        /// <returns>Google Zanzibar Notation for the ACL Relation</returns>
        /// <exception cref="InvalidOperationException">Thrown, if the <see cref="AclSubject"/> couldn't be formatted as a string</exception>
        public static string SubjectToString(AclSubject s)
        {
            switch (s)
            {
                case AclSubjectId subjectId:
                    return subjectId.FormatString();
                case AclSubjectSet subjectSet:
                    return subjectSet.FormatString();
                default:
                    throw new InvalidOperationException($"Cannot format Subject Type '{s.GetType().Name}'");
            }
        }
    }
}
```

### Check API ###

The Check API is used to check if the user has a given permission, which means: Check if a `Subject` (user) has 
a `Relation` to a given `Object`. We can implement the basic algorithm in a few lines of code.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AclExperiments
{
    /// <summary>
    /// The <see cref="AclService"/> implements the Google Zanzibar algorithms, such as Expand, Check and ListObjects.
    /// </summary>
    public class AclService
    {
        private readonly ILogger _logger;
        private readonly IRelationTupleStore _relationTupleStore;
        private readonly INamespaceConfigurationStore _namespaceConfigurationStore;

        public AclService(ILogger<AclService> logger, IRelationTupleStore relationTupleStore, INamespaceConfigurationStore namespaceConfigurationStore)
        {
            _logger = logger;
            _relationTupleStore = relationTupleStore;
            _namespaceConfigurationStore = namespaceConfigurationStore;
        }

        #region Check API

        public async Task<bool> CheckAsync(string @namespace, string @object, string relation, string subject, CancellationToken cancellationToken)
        {
            // Get the latest Namespace Configuration from the Store:
            var namespaceConfiguration = await _namespaceConfigurationStore
                .GetLatestNamespaceConfigurationAsync(@namespace, cancellationToken)
                .ConfigureAwait(false);

            // Get the Rewrite for the Relation from the Namespace Configuration:
            var rewrite = GetUsersetRewrite(namespaceConfiguration, relation);

            // Check Rewrite Rules for the Relation:
            return await this
                .CheckUsersetRewriteAsync(rewrite, @namespace, @object, relation, subject, cancellationToken)
                .ConfigureAwait(false);
        }

        /// <summary>
        /// Returns the <see cref="UsersetExpression"/> for a given Namespace Configuration and Relation.
        /// </summary>
        /// <param name="namespaceUsersetExpression">Namespace Configuration</param>
        /// <param name="relation">Relation to Check</param>
        /// <returns>The <see cref="UsersetExpression"/> for the given relation</returns>
        /// <exception cref="InvalidOperationException">Thrown, if the Relation isn't configured in the Namespace Configuration</exception>
        private static UsersetExpression GetUsersetRewrite(NamespaceUsersetExpression namespaceUsersetExpression, string relation)
        {
            if (!namespaceUsersetExpression.Relations.TryGetValue(relation, out var relationUsersetExpression))
            {
                throw new InvalidOperationException($"Namespace '{namespaceUsersetExpression.Name}' has no Relation '{relation}'");
            }

            return relationUsersetExpression.Rewrite;
        }

        /// <summary>
        /// Checks a Userset Rewrite.
        /// </summary>
        /// <param name="rewrite">Rewrite Rule for the Relation</param>
        /// <param name="namespace">Object Namespace</param>
        /// <param name="object">Object ID</param>
        /// <param name="relation">Relation name</param>
        /// <param name="subject">Subject Name</param>
        /// <param name="cancellationToken"></param>
        /// <returns></returns>
        /// <exception cref="InvalidOperationException"></exception>
        public async Task<bool> CheckUsersetRewriteAsync(UsersetExpression rewrite, string @namespace, string @object, string relation, string subject, CancellationToken cancellationToken)
        {
            switch (rewrite)
            {
                case ThisUsersetExpression thisUsersetExpression:
                    return await this
                        .CheckThisAsync(thisUsersetExpression, @namespace, @object, relation, subject, cancellationToken)
                        .ConfigureAwait(false);
                case ChildUsersetExpression childUsersetExpression:
                    return await this
                        .CheckUsersetRewriteAsync(childUsersetExpression.Userset, @namespace, @object, relation, subject, cancellationToken)
                        .ConfigureAwait(false);
                case ComputedUsersetExpression computedUsersetExpression:
                    return await
                        CheckComputedUsersetAsync(computedUsersetExpression, @namespace, @object, subject, cancellationToken)
                        .ConfigureAwait(false);
                case TupleToUsersetExpression tupleToUsersetExpression:
                    return await
                        CheckTupleToUsersetAsync(tupleToUsersetExpression, @namespace, @object, relation, subject, cancellationToken)
                        .ConfigureAwait(false);
                case SetOperationUsersetExpression setOperationExpression:
                    return await
                        CheckSetOperationExpression(setOperationExpression, @namespace, @object, relation, subject, cancellationToken)
                        .ConfigureAwait(false);
                default:
                    throw new InvalidOperationException($"Unable to execute check for Expression '{rewrite.GetType().Name}'");
            }
        }

        private async Task<bool> CheckSetOperationExpression(SetOperationUsersetExpression setOperationExpression, string @namespace, string @object, string relation, string user, CancellationToken cancellationToken)
        {
            switch (setOperationExpression.Operation)
            {
                case SetOperationEnum.Intersect:
                    {
                        foreach (var child in setOperationExpression.Children)
                        {
                            var permitted = await this
                                .CheckUsersetRewriteAsync(child, @namespace, @object, relation, user, cancellationToken)
                                .ConfigureAwait(false);

                            if (!permitted)
                            {
                                return false;
                            }
                        }

                        return true;
                    }
                case SetOperationEnum.Union:
                    {
                        foreach (var child in setOperationExpression.Children)
                        {
                            var permitted = await this
                                .CheckUsersetRewriteAsync(child, @namespace, @object, relation, user, cancellationToken)
                                .ConfigureAwait(false);

                            if (permitted)
                            {
                                return true;
                            }
                        }

                        return false;
                    }
                default:
                    throw new NotImplementedException($"No Implementation for Set Operator '{setOperationExpression.Operation}'");
            }
        }

        private async Task<bool> CheckThisAsync(ThisUsersetExpression thisUsersetExpression, string @namespace, string @object, string relation, string user, CancellationToken cancellationToken)
        {
            var aclObject = new AclObject
            {
                Namespace = @namespace,
                Id = @object,
            };

            var aclSubject = AclSubjects.SubjectFromString(user);

            var count = await _relationTupleStore
                .GetRelationTuplesRowCountAsync(aclObject, relation, aclSubject, cancellationToken)
                .ConfigureAwait(false);

            if (count > 0)
            {
                return true;
            }

            var subjestSets = await _relationTupleStore
                .GetSubjectSetsAsync(aclObject, relation, cancellationToken)
                .ConfigureAwait(false);

            foreach (var subjectSet in subjestSets)
            {
                var permitted = await this
                    .CheckAsync(subjectSet.Namespace, subjectSet.Object, subjectSet.Relation, user, cancellationToken)
                    .ConfigureAwait(false);

                if (permitted)
                {
                    return true;
                }
            }

            return false;
        }

        private async Task<bool> CheckComputedUsersetAsync(ComputedUsersetExpression computedUsersetExpression, string @namespace, string @object, string user, CancellationToken cancellationToken)
        {
            if (computedUsersetExpression.Relation == null)
            {
                throw new InvalidOperationException("A Computed Userset requires a relation");
            }

            return await this
                .CheckAsync(@namespace, @object, computedUsersetExpression.Relation, user, cancellationToken)
                .ConfigureAwait(false);
        }

        private async Task<bool> CheckTupleToUsersetAsync(TupleToUsersetExpression tupleToUsersetExpression, string @namespace, string @object, string relation, string user, CancellationToken cancellationToken)
        {
            {
                var aclObject = new AclObject
                {
                    Namespace = @namespace,
                    Id = @object
                };

                var subjectSets = await _relationTupleStore
                    .GetSubjectSetsAsync(aclObject, tupleToUsersetExpression.TuplesetExpression.Relation, cancellationToken)
                    .ConfigureAwait(false);

                if (subjectSets.Count == 0)
                {
                    return false;
                }

                foreach (var subject in subjectSets)
                {
                    relation = subject.Relation;

                    if (relation == "...")
                    {
                        relation = tupleToUsersetExpression.ComputedUsersetExpression.Relation!;

                        var permitted = await this
                            .CheckAsync(subject.Namespace, subject.Object, relation, user, cancellationToken)
                            .ConfigureAwait(false);

                        if (permitted)
                        {
                            return true;
                        }
                    }
                }

                return false;
            }
        }


        #endregion Check API

    }
}
```

We can now test, if the Check API works as expected. The test case is described extensively.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AclExperiments.Tests
{
    [TestClass]
    public class AclServiceTests : IntegrationTestBase
    {
        private AclService _aclService = null!;

        private INamespaceConfigurationStore _namespaceConfigurationStore = null!;
        private IRelationTupleStore _relationTupleStore = null!;

        protected override Task OnSetupBeforeCleanupAsync()
        {
            _aclService = _services.GetRequiredService<AclService>();
            _relationTupleStore = _services.GetRequiredService<IRelationTupleStore>();
            _namespaceConfigurationStore = _services.GetRequiredService<INamespaceConfigurationStore>();

            return Task.CompletedTask;
        }

        public override void RegisterServices(IServiceCollection services)
        {
            services.AddSingleton<ISqlConnectionFactory>((sp) =>
            {
                var connectionString = _configuration.GetConnectionString("ApplicationDatabase");

                if (connectionString == null)
                {
                    throw new InvalidOperationException($"No Connection String named 'ApplicationDatabase' found in appsettings.json");
                }

                return new SqlServerConnectionFactory(connectionString);
            });

            services.AddSingleton<AclService>();
            services.AddSingleton<INamespaceConfigurationStore, SqlNamespaceConfigurationStore>();
            services.AddSingleton<IRelationTupleStore, SqlRelationTupleStore>();
        }

        #region Check API

        ///// <summary>
        /// In this test we have one document "doc_1", and two users "user_1" and "user_2". "user_1" 
        /// has a "viewer" permission on "doc_1", because he has a direct relationto it. "user_2" has 
        /// a viewer permission on a folder "folder_1". 
        /// 
        /// The folder "folder_1" is a "parent" of the document, and thus "user_2" inherits the folders 
        /// permission through the computed userset.
        /// 
        /// Namespace |  Object       |   Relation    |   Subject             |
        /// ----------|---------------|---------------|-----------------------|
        /// doc       |   doc_1       |   viewer      |   user_1              |
        /// doc       |   doc_1       |   parent      |   folder:folder_1#... |
        /// folder    |   folder_1    |   viewer      |   user_2              |
        /// </summary>
        [TestMethod]
        public async Task CheckAsync_CheckUserPermissions()
        {
            // Arrange
            await _namespaceConfigurationStore.AddNamespaceConfigurationAsync("doc", 1, File.ReadAllText("Resources/doc.nsconfig"), 1, default);
            await _namespaceConfigurationStore.AddNamespaceConfigurationAsync("folder", 1, File.ReadAllText("Resources/folder.nsconfig"), 1, default);

            var aclRelations = new[]
            {
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "doc",
                            Id = "doc_1"
                        },
                        Relation = "owner",
                        Subject = new AclSubjectId
                        {
                            Id = "user_1"
                        }
                    },
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "doc",
                            Id = "doc_1"
                        },
                        Relation = "parent",
                        Subject = new AclSubjectId
                        {
                            Id = "folder:folder_1#..."
                        }
                    },
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "folder",
                            Id = "folder_1"
                        },
                        Relation = "viewer",
                        Subject = new AclSubjectId
                        {
                            Id = "user_2"
                        }
                    },
                };

            await _relationTupleStore.AddRelationTuplesAsync(aclRelations, 1, default);

            // Act
            var user_1_is_permitted = await _aclService.CheckAsync("doc", "doc_1", "viewer", "user_1", default);
            var user_2_is_permitted = await _aclService.CheckAsync("doc", "doc_1", "viewer", "user_2", default);
            var user_3_is_permitted = await _aclService.CheckAsync("doc", "doc_1", "viewer", "user_3", default);

            // Assert
            Assert.AreEqual(true, user_1_is_permitted);
            Assert.AreEqual(true, user_2_is_permitted);
            Assert.AreEqual(false, user_3_is_permitted);
        }

        #endregion Check API
        
        // ...

    }
}
```

### Expand API ###

While the Check API only dealth with the Question "Are we permitted to access the object?", the Expand API is used to determine 
the full ACL for a user. This is especially useful for debugging, to understand *why* a user has been granted or been denied 
permission to an object.

It starts by defining a `SubjectTree`, which is going to hold all Subjects determined by the Expand API.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using AclExperiments.Expressions;

namespace AclExperiments.Models
{
    /// <summary>
    /// The expanded Subject Tree.
    /// </summary>
    public record SubjectTree
    {
        /// <summary>
        /// Gets or sets the Userset Expression for this.
        /// </summary>
        public required UsersetExpression Expression { get; set; }

        /// <summary>
        /// Gets or sets the determined Subjects.
        /// </summary>
        public HashSet<AclSubject> Result { get; set; } = [];

        /// <summary>
        /// Gets or sets the Children Trees.
        /// </summary>
        public List<SubjectTree> Children { get; set; } = new();
    }
}
```

And now we can finally implement the Expand API to traverse the Expression Tree and evaluate the 
Rewrite Rules recursively. I initially tried to use a Visitor pattern, but my brain just couldn't 
digest a double dispatch.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AclExperiments
{
    /// <summary>
    /// The <see cref="AclService"/> implements the Google Zanzibar algorithms, such as Expand, Check and ListObjects.
    /// </summary>
    public class AclService
    {
        private readonly ILogger _logger;
        private readonly IRelationTupleStore _relationTupleStore;
        private readonly INamespaceConfigurationStore _namespaceConfigurationStore;

        public AclService(ILogger<AclService> logger, IRelationTupleStore relationTupleStore, INamespaceConfigurationStore namespaceConfigurationStore)
        {
            _logger = logger;
            _relationTupleStore = relationTupleStore;
            _namespaceConfigurationStore = namespaceConfigurationStore;
        }
        
        // ...
        
        #region Expand API

        public async Task<SubjectTree> ExpandAsync(string @namespace, string @object, string relation, int depth, CancellationToken cancellationToken)
        {
            var namespaceConfiguration = await _namespaceConfigurationStore
                .GetLatestNamespaceConfigurationAsync(@namespace, cancellationToken)
                .ConfigureAwait(false);

            var usersetRewriteForRelation = GetUsersetRewrite(namespaceConfiguration, relation);

            var t = await this
                 .ExpandRewriteAsync(usersetRewriteForRelation, @namespace, @object, relation, depth, cancellationToken)
                 .ConfigureAwait(false);

            return new SubjectTree
            {
                Expression = namespaceConfiguration,
                Children = [t],
                Result = t.Result
            };
        }

        public async Task<SubjectTree> ExpandRewriteAsync(UsersetExpression rewrite, string @namespace, string @object, string relation, int depth, CancellationToken cancellationToken)
        {
            switch (rewrite)
            {
                case ThisUsersetExpression thisUsersetExpression:
                    return await this
                        .ExpandThisAsync(thisUsersetExpression, @namespace, @object, relation, depth, cancellationToken)
                        .ConfigureAwait(false);
                case ComputedUsersetExpression computedUsersetExpression:
                    return await this
                        .ExpandComputedUserSetAsync(computedUsersetExpression, @namespace, @object, relation, depth, cancellationToken)
                        .ConfigureAwait(false);
                case TupleToUsersetExpression tupleToUsersetExpression:
                    return await this
                        .ExpandTupleToUsersetAsync(tupleToUsersetExpression, @namespace, @object, relation, depth, cancellationToken)
                        .ConfigureAwait(false);
                case ChildUsersetExpression childUsersetExpression:
                    return await this
                        .ExpandRewriteAsync(childUsersetExpression.Userset, @namespace, @object, relation, depth, cancellationToken)
                        .ConfigureAwait(false);
                case SetOperationUsersetExpression setOperationExpression:
                    return await this
                        .ExpandSetOperationAsync(setOperationExpression, @namespace, @object, relation, depth, cancellationToken)
                        .ConfigureAwait(false);
                default:
                    throw new InvalidOperationException($"Unable to execute check for Expression '{rewrite.GetType().Name}'");
            }
        }

        public async Task<SubjectTree> ExpandSetOperationAsync(SetOperationUsersetExpression setOperationUsersetExpression, string @namespace, string @object, string relation, int depth, CancellationToken cancellationToken)
        {
            List<SubjectTree> children = [];

            // TODO This could be done in Parallel
            foreach (var child in setOperationUsersetExpression.Children)
            {
                var t = await this
                    .ExpandRewriteAsync(child, @namespace, @object, relation, depth, cancellationToken)
                    .ConfigureAwait(false);

                children.Add(t);
            }

            HashSet<AclSubject>? subjects = null;

            foreach (var child in children)
            {
                if (subjects == null)
                {
                    subjects = new HashSet<AclSubject>(child.Result);
                }
                else
                {
                    switch (setOperationUsersetExpression.Operation)
                    {
                        case SetOperationEnum.Union:
                            subjects.UnionWith(child.Result);
                            break;
                        case SetOperationEnum.Intersect:
                            subjects.IntersectWith(child.Result);
                            if (subjects.Count == 0)
                                goto eval;
                            break;
                        case SetOperationEnum.Exclude:
                            subjects.ExceptWith(child.Result);
                            if (subjects.Count == 0)
                                goto eval;
                            break;
                        default:
                            throw new InvalidOperationException();
                    }
                }
            }

        eval:

            return new SubjectTree
            {
                Expression = setOperationUsersetExpression,
                Result = subjects ?? [],
                Children = children
            };
        }

        public async Task<SubjectTree> ExpandThisAsync(ThisUsersetExpression expression, string @namespace, string @object, string relation, int depth, CancellationToken cancellationToken)
        {
            var query = new RelationTupleQuery
            {
                Namespace = @namespace,
                Object = @object,
                Relation = relation
            };

            var tuples = await _relationTupleStore
                .GetRelationTuplesAsync(query, cancellationToken)
                .ConfigureAwait(false);

            var children = new List<SubjectTree>();
            var result = new HashSet<AclSubject>();

            foreach (var tuple in tuples)
            {
                if (tuple.Subject is AclSubjectSet subjectSet)
                {
                    var rr = subjectSet.Relation;

                    if (rr == "...")
                    {
                        rr = relation;
                    }

                    var t = await this
                        .ExpandAsync(subjectSet.Namespace, subjectSet.Object, rr, depth - 1, cancellationToken)
                        .ConfigureAwait(false);

                    children.Add(t);
                }
                else
                {
                    var t = new SubjectTree
                    {
                        Expression = expression,
                        Result = [tuple.Subject]
                    };

                    children.Add(t);

                    result.Add(tuple.Subject);
                }
            }

            return new SubjectTree
            {
                Expression = expression,
                Result = result,
                Children = children
            };
        }

        public async Task<SubjectTree> ExpandComputedUserSetAsync(ComputedUsersetExpression computedUsersetExpression, string @namespace, string @object, string relation, int depth, CancellationToken cancellationToken)
        {
            if (computedUsersetExpression.Relation == null)
            {
                throw new InvalidOperationException("A Computed Userset requires a relation");
            }

            var subTree = await this
                .ExpandAsync(@namespace, @object, computedUsersetExpression.Relation, depth - 1, cancellationToken)
                .ConfigureAwait(false);

            return new SubjectTree
            {
                Expression = computedUsersetExpression,
                Children = [subTree],
                Result = subTree.Result
            };
        }

        public async Task<SubjectTree> ExpandTupleToUsersetAsync(TupleToUsersetExpression tupleToUsersetExpression, string @namespace, string @object, string relation, int depth, CancellationToken cancellationToken)
        {
            var rr = tupleToUsersetExpression.TuplesetExpression.Relation;

            if (rr == "...")
            {
                rr = relation;
            }

            var query = new RelationTupleQuery
            {
                Namespace = @namespace,
                Object = @object,
                Relation = rr
            };

            var tuples = await _relationTupleStore
                .GetRelationTuplesAsync(query, cancellationToken)
                .ConfigureAwait(false);

            var children = new List<SubjectTree>();

            var subjects = new HashSet<AclSubject>();

            foreach (var tuple in tuples)
            {
                if (tuple.Subject is AclSubjectSet subjectSet)
                {
                    rr = subjectSet.Relation;

                    if (rr == "...")
                    {
                        rr = relation;
                    }

                    var t = await this
                        .ExpandAsync(subjectSet.Namespace, subjectSet.Object, rr, depth - 1, cancellationToken)
                        .ConfigureAwait(false);

                    children.Add(new SubjectTree
                    {
                        Expression = new ComputedUsersetExpression
                        {
                            Namespace = @namespace,
                            Object = @object,
                            Relation = rr
                        },
                        Children = [t],
                        Result = t.Result
                    });

                    subjects.UnionWith(t.Result);
                }
                else
                {
                    var t = new SubjectTree
                    {
                        Expression = new ComputedUsersetExpression
                        {
                            Namespace = @namespace,
                            Object = @object,
                            Relation = rr,
                        },
                        Result = [tuple.Subject]
                    };

                    children.Add(t);
                    subjects.UnionWith(t.Result);
                }
            }

            return new SubjectTree
            {
                Expression = tupleToUsersetExpression,
                Children = children,
                Result = subjects
            };
        }

        #endregion Expand API
    }
}
```

We can use the Expand API to get the full... This is useful, if we need. 

Finally let's write some Integration tests. The comments in the test are exhaustive, so we don't need 
to repeat them here. Enjoy! And feel free to add more complex tests and probably uncover cases I 
didn't think of yet.

```csharp
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

// ...

namespace AclExperiments.Tests
{
    [TestClass]
    public class AclServiceTests : IntegrationTestBase
    {
        private AclService _aclService = null!;

        private INamespaceConfigurationStore _namespaceConfigurationStore = null!;
        private IRelationTupleStore _relationTupleStore = null!;

        protected override Task OnSetupBeforeCleanupAsync()
        {
            _aclService = _services.GetRequiredService<AclService>();
            _relationTupleStore = _services.GetRequiredService<IRelationTupleStore>();
            _namespaceConfigurationStore = _services.GetRequiredService<INamespaceConfigurationStore>();

            return Task.CompletedTask;
        }

        public override void RegisterServices(IServiceCollection services)
        {
            services.AddSingleton<ISqlConnectionFactory>((sp) =>
            {
                var connectionString = _configuration.GetConnectionString("ApplicationDatabase");

                if (connectionString == null)
                {
                    throw new InvalidOperationException($"No Connection String named 'ApplicationDatabase' found in appsettings.json");
                }

                return new SqlServerConnectionFactory(connectionString);
            });

            services.AddSingleton<AclService>();
            services.AddSingleton<INamespaceConfigurationStore, SqlNamespaceConfigurationStore>();
            services.AddSingleton<IRelationTupleStore, SqlRelationTupleStore>();
        }

        #region Check API

        ///// <summary>
        /// In this test we have one document "doc_1", and two users "user_1" and "user_2". "user_1" 
        /// has a "viewer" permission on "doc_1", because he has a direct relationto it. "user_2" has 
        /// a viewer permission on a folder "folder_1". 
        /// 
        /// The folder "folder_1" is a "parent" of the document, and thus "user_2" inherits the folders 
        /// permission through the computed userset.
        /// 
        /// Namespace |  Object       |   Relation    |   Subject             |
        /// ----------|---------------|---------------|-----------------------|
        /// doc       |   doc_1       |   viewer      |   user_1              |
        /// doc       |   doc_1       |   parent      |   folder:folder_1#... |
        /// folder    |   folder_1    |   viewer      |   user_2              |
        /// </summary>
        [TestMethod]
        public async Task CheckAsync_CheckUserPermissions()
        {
            // Arrange
            await _namespaceConfigurationStore.AddNamespaceConfigurationAsync("doc", 1, File.ReadAllText("Resources/doc.nsconfig"), 1, default);
            await _namespaceConfigurationStore.AddNamespaceConfigurationAsync("folder", 1, File.ReadAllText("Resources/folder.nsconfig"), 1, default);

            var aclRelations = new[]
            {
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "doc",
                            Id = "doc_1"
                        },
                        Relation = "owner",
                        Subject = new AclSubjectId
                        {
                            Id = "user_1"
                        }
                    },
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "doc",
                            Id = "doc_1"
                        },
                        Relation = "parent",
                        Subject = new AclSubjectId
                        {
                            Id = "folder:folder_1#..."
                        }
                    },
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "folder",
                            Id = "folder_1"
                        },
                        Relation = "viewer",
                        Subject = new AclSubjectId
                        {
                            Id = "user_2"
                        }
                    },
                };

            await _relationTupleStore.AddRelationTuplesAsync(aclRelations, 1, default);

            // Act
            var user_1_is_permitted = await _aclService.CheckAsync("doc", "doc_1", "viewer", "user_1", default);
            var user_2_is_permitted = await _aclService.CheckAsync("doc", "doc_1", "viewer", "user_2", default);
            var user_3_is_permitted = await _aclService.CheckAsync("doc", "doc_1", "viewer", "user_3", default);

            // Assert
            Assert.AreEqual(true, user_1_is_permitted);
            Assert.AreEqual(true, user_2_is_permitted);
            Assert.AreEqual(false, user_3_is_permitted);
        }

        #endregion Check API

        #region Expand API

        ///// <summary>
        /// In this test we have one document "doc_1", and two users "user_1" and "user_2". "user_1" 
        /// has a "viewer" permission on "doc_1", because he has a direct relationto it. "user_2" has 
        /// a viewer permission on a folder "folder_1". 
        /// 
        /// The folder "folder_1" is a "parent" of the document, and thus "user_2" inherits the folders 
        /// permission through the computed userset.
        /// 
        /// Namespace |  Object       |   Relation    |   Subject             |
        /// ----------|---------------|---------------|-----------------------|
        /// doc       |   doc_1       |   viewer      |   user_1              |
        /// doc       |   doc_1       |   parent      |   folder:folder_1#... |
        /// folder    |   folder_1    |   viewer      |   user_2              |
        /// </summary>
        [TestMethod]
        public async Task Expand_ExpandUsersetRewrites()
        {
            // Arrange
            await _namespaceConfigurationStore.AddNamespaceConfigurationAsync("doc", 1, File.ReadAllText("Resources/doc.nsconfig"), 1, default);
            await _namespaceConfigurationStore.AddNamespaceConfigurationAsync("folder", 1, File.ReadAllText("Resources/folder.nsconfig"), 1, default);

            var aclRelations = new[]
            {
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "doc",
                            Id = "doc_1"
                        },
                        Relation = "owner",
                        Subject = new AclSubjectId
                        {
                            Id = "user_1"
                        }
                    },
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "doc",
                            Id = "doc_1"
                        },
                        Relation = "parent",
                        Subject = new AclSubjectId
                        {
                            Id = "folder:folder_1#..."
                        }
                    },
                    new AclRelation
                    {
                        Object = new AclObject
                        {
                            Namespace = "folder",
                            Id = "folder_1"
                        },
                        Relation = "viewer",
                        Subject = new AclSubjectId
                        {
                            Id = "user_2"
                        }
                    },
                };

            await _relationTupleStore.AddRelationTuplesAsync(aclRelations, 1, default);

            // Act
            var subjectTree = await _aclService.ExpandAsync("doc", "doc_1", "viewer", 100, default);

            // Assert
            Assert.AreEqual(2, subjectTree.Result.Count);

            var sortedSubjectTreeResults = subjectTree.Result
                .Cast<AclSubjectId>()
                .OrderBy(x => x.Id)
                .ToList();

            Assert.AreEqual("user_1", sortedSubjectTreeResults[0].Id);
            Assert.AreEqual("user_2", sortedSubjectTreeResults[1].Id);
        }

        #endregion Expand API
    }
}
```

## Conclusion ##

And that's it!

So let's see what we have developed in this article.

We can parse the Google Zanzibar Namespace Configuration language and implemented a basic version of the 
Check API and Expand API. We've learnt about ANTLR4 and have seen how to go from idea to implementation.

There's a lot more we could do... we could parallelize set operations to speed up the code significantly. We 
could cache Namespace Configurations so we don't waste cycles parsing them all over. We could cache relation 
tuples, to waste expensive database resources for querying the same data all over.

But it's an open source project. Let's work on it together! 👍

Yes, at the end this article was mostly just pasting code. It's because I wanted to finally get *something* out 
and didn't want to waste weeks on trying to find the "perfect abstraction". There's a lot more interesting code 
in the Git repository, enjoy!