title: Create delegates for Constructors, Property Getters and Property Setters by Compiling Expression Trees in C#
date: 2015-11-08 13:41
tags: csharp, reflection, software design
category: csharp
slug: expression_trees_csharp
author: Philipp Wagner
summary: This article shows how to use expression trees in C#.

[TinyCsvParser]: https://codeberg.org/bytefish/TinyCsvParser
[MIT License]: https://opensource.org/licenses/MIT
[Activator.CreateInstance]: https://msdn.microsoft.com/en-us/library/system.activator.createinstance(v=vs.110).aspx
[PropertyInfo.GetValue]: https://msdn.microsoft.com/en-us/library/hh194385(v=vs.110).aspx
[PropertyInfo.SetValue]: https://msdn.microsoft.com/en-us/library/hh194291(v=vs.110).aspx
[Compile]: https://msdn.microsoft.com/en-us/library/bb345362.aspx
[Expression Trees]: https://msdn.microsoft.com/en-us/library/bb397951.aspx
[Expression Tree]: https://msdn.microsoft.com/en-us/library/bb397951.aspx
[Microsoft]: https://www.microsoft.com

Some time ago I have written [TinyCsvParser], which is a high-performing library to parse data.

One of the crucial aspects of such a library is the creation and population objects. So how can you do it in an efficient way? 
The initial benchmarks showed, that using [Activator.CreateInstance] to instantiate an object, using [PropertyInfo.SetValue] to set 
a value and using [PropertyInfo.GetValue] to get a value is way too slow for real world applications.

Instead of using slow Reflection, we can use [Expression Trees] in .NET4 to create delegates for a standard constructor, a property getter 
and a property setter... without using Reflection at all. So what is an Expression Tree?

[Microsoft] writes ([Expression Trees (C# and Visual Basic)](https://msdn.microsoft.com/en-us/library/bb397951.aspx)):

> Expression trees represent code in a tree-like data structure, where each node is an expression, for example, a method 
> call or a binary operation such as ``x < y``.
>
> You can compile and run code represented by expression trees. This enables dynamic modification of executable code, the execution of LINQ queries in 
> various databases, and the creation of dynamic queries. For more information about expression trees in LINQ, see How to: Use Expression Trees to 
> Build Dynamic Queries (C# and Visual Basic).

So what actually happens? 

When the [Compile] method on an expression tree is called, the IL code is emitted to convert the expression tree into a 
delegate. This delegate can be used to run the code represented by the expression tree without using Reflection at all. Since [Compile] is a very 
expensive operation, it should be called only once and the resulting delegate should be cached.

I think sharing my code is useful, because a lot of people are looking for something similar I guess. The Unit Tests show you how to use the methods.

## ExpressionUtils ##

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Linq.Expressions;
using System.Reflection;

namespace ExpressionExample
{
    public static class ExpressionUtils
    {
        public static PropertyInfo GetProperty<TEntity, TProperty>(Expression<Func<TEntity, TProperty>> expression)
        {
            var member = GetMemberExpression(expression).Member;
            var property = member as PropertyInfo;
            if (property == null)
            {
                throw new InvalidOperationException(string.Format("Member with Name '{0}' is not a property.", member.Name));
            }
            return property;
        }

        private static MemberExpression GetMemberExpression<TEntity, TProperty>(Expression<Func<TEntity, TProperty>> expression)
        {
            MemberExpression memberExpression = null;
            if (expression.Body.NodeType == ExpressionType.Convert)
            {
                var body = (UnaryExpression)expression.Body;
                memberExpression = body.Operand as MemberExpression;
            }
            else if (expression.Body.NodeType == ExpressionType.MemberAccess)
            {
                memberExpression = expression.Body as MemberExpression;
            }

            if (memberExpression == null)
            {
                throw new ArgumentException("Not a member access", "expression");
            }

            return memberExpression;
        }

        public static Action<TEntity, TProperty> CreateSetter<TEntity, TProperty>(Expression<Func<TEntity, TProperty>> property)
        {
            PropertyInfo propertyInfo = ExpressionUtils.GetProperty(property);

            ParameterExpression instance = Expression.Parameter(typeof(TEntity), "instance");
            ParameterExpression parameter = Expression.Parameter(typeof(TProperty), "param");

            var body = Expression.Call(instance, propertyInfo.GetSetMethod(), parameter);
            var parameters = new ParameterExpression[] { instance, parameter };

            return Expression.Lambda<Action<TEntity, TProperty>>(body, parameters).Compile();
        }

        public static Func<TEntity, TProperty> CreateGetter<TEntity, TProperty>(Expression<Func<TEntity, TProperty>> property)
        {
            PropertyInfo propertyInfo = ExpressionUtils.GetProperty(property);

            ParameterExpression instance = Expression.Parameter(typeof(TEntity), "instance");

            var body = Expression.Call(instance, propertyInfo.GetGetMethod());
            var parameters = new ParameterExpression[] { instance };

            return Expression.Lambda<Func<TEntity, TProperty>>(body, parameters).Compile();
        }

        public static Func<TEntity> CreateDefaultConstructor<TEntity>()
        {
            var body = Expression.New(typeof(TEntity));
            var lambda = Expression.Lambda<Func<TEntity>>(body);

            return lambda.Compile();
        }
    }
}
```

## Unit Tests ##

```csharp
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using NUnit.Framework;

namespace ExpressionExample
{
    [TestFixture]
    public class ExpressionUtilsTest
    {
        public class SampleClass 
        {
            public int IntegerProperty { get; set; }
            public string StringProperty { get; set; }
        }

        [Test]
        public void SetterTest()
        {
            var setterIntegerProperty = ExpressionUtils.CreateSetter<SampleClass, int>(x => x.IntegerProperty);
            var setterStringProperty = ExpressionUtils.CreateSetter<SampleClass, string>(x => x.StringProperty);

            SampleClass sampleClassInstance = new SampleClass();

            setterIntegerProperty(sampleClassInstance, 1);
            setterStringProperty(sampleClassInstance, "2");

            Assert.AreEqual(1, sampleClassInstance.IntegerProperty);
            Assert.AreEqual("2", sampleClassInstance.StringProperty);
        }

        [Test]
        public void GetterTest()
        {
            var getterIntegerProperty = ExpressionUtils.CreateGetter<SampleClass, int>(x => x.IntegerProperty);
            var getterStringProperty = ExpressionUtils.CreateGetter<SampleClass, string>(x => x.StringProperty);

            SampleClass sampleClassInstance = new SampleClass()
            {
                IntegerProperty = 1,
                StringProperty = "2"
            };
            
            Assert.AreEqual(1, getterIntegerProperty(sampleClassInstance));
            Assert.AreEqual("2", getterStringProperty(sampleClassInstance));
        }

        [Test]
        public void CreateDefaultConstructorTest()
        {
            var defaultConstructor = ExpressionUtils.CreateDefaultConstructor<SampleClass>();
            var setterIntegerProperty = ExpressionUtils.CreateSetter<SampleClass, int>(x => x.IntegerProperty);
            
            var sampleEntity = defaultConstructor();

            setterIntegerProperty(sampleEntity, 1);

            Assert.AreEqual(1, sampleEntity.IntegerProperty);
        }
    }
}
```