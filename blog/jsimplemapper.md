title: Introducing JSimpleMapper
date: 2016-01-15 18:36
tags: JSimpleMapper, java
category: jsimplemapper 
slug: jsimplemapper
author: Philipp Wagner
summary: This article introduces JSimpleMapper for mapping between Java Beans.

[MIT License]: https://opensource.org/licenses/MIT
[JSimpleMapper]: https://codeberg.org/bytefish/JSimpleMapper
[Oracle Documentation]: http://www.oracle.com/technetwork/java/javase/documentation/spec-136004.html

[JSimpleMapper] is a small library for mapping between Java beans. It makes use of Java 1.8 lambda functions and doesn't use any reflection.

## Basic Usage ##

A lot of problems in software development boil down to converting or mapping data. 

The Webservice receives JSON data, that needs to be mapped into an object of the application. A database sends a query result, 
which has to be mapped to an object in our application. A device sends data with a binary protocol, that has to be parsed and 
mapped to a protocol model in the application. The UI works with a UI-specific ViewModel, that needs to be mapped to the model 
in the application...

So [JSimpleMapper] is a small program to map between two Java Beans, which happens a lot in layered applications. 

A Java Bean is just a convention (see the [Oracle Documentation]), that says:

1. All properties are private (only getters/setters)
2. A public, no-argument constructor
3. Implements Serializable

The basic idea of [JSimpleMapper] is, that you only have to implement an ``AbstractMapper<TSourceEntity, TTargetEntity>`` for mapping between 
two entities in your application. 

Imagine, you need to convert between a ``PersonViewModel`` and ``PersonDomainModel``, where the property 
``PersonViewModel.birthDate`` is a ``String`` and ``PersonDomainModel.birthDate`` is a ``LocalDate``.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jsimplemapper;

import de.bytefish.jsimplemapper.converters.LocalDateTimeToStringConverter;
import de.bytefish.jsimplemapper.func.ICreator;
import de.bytefish.jsimplemapper.mapping.MappingResult;
import org.junit.Assert;
import org.junit.Test;

import java.time.LocalDate;

public class PersonMapperTest {

    // A View Model, that needs to be converted to a Domain Model.
    public class PersonViewModel {

        private String firstName;
        private String lastName;
        private String birthDate;

        public String getFirstName() {
            return firstName;
        }

        public void setFirstName(String firstName) {
            this.firstName = firstName;
        }

        public String getLastName() {
            return lastName;
        }

        public void setLastName(String lastName) {
            this.lastName = lastName;
        }

        public String getBirthDate() {
            return birthDate;
        }

        public void setBirthDate(String birthDate) {
            this.birthDate = birthDate;
        }
    }

    // A Domain Model with correct types, such as LocalDate for a BirthDate.
    public class PersonDomainModel {

        private String firstName;
        private String lastName;
        private LocalDate birthDate;

        public String getFirstName() {
            return firstName;
        }

        public void setFirstName(String firstName) {
            this.firstName = firstName;
        }

        public String getLastName() {
            return lastName;
        }

        public void setLastName(String lastName) {
            this.lastName = lastName;
        }

        public LocalDate getBirthDate() {
            return birthDate;
        }

        public void setBirthDate(LocalDate birthDate) {
            this.birthDate = birthDate;
        }
    }

    // Mapper between PersonViewModel and PersonDomainModel.
    public class PersonMapper extends AbstractMapper<PersonViewModel, PersonDomainModel> {

        public PersonMapper(ICreator<PersonDomainModel> creator) {
            super(creator);

            mapProperty(PersonViewModel::getFirstName, String.class, PersonDomainModel::setFirstName, String.class);
            mapProperty(PersonViewModel::getLastName, String.class, PersonDomainModel::setLastName, String.class);
            mapProperty(PersonViewModel::getBirthDate, String.class, PersonDomainModel::setBirthDate, LocalDate.class);
        }
    }

    @Test
    public void testMapping() {
        PersonMapper mapper = new PersonMapper(() -> new PersonDomainModel());

        PersonViewModel personViewModel = new PersonViewModel();

        personViewModel.setFirstName("Philipp");
        personViewModel.setLastName("Wagner");
        personViewModel.setBirthDate("1986-05-12");

        MappingResult<PersonDomainModel> result = mapper.map(personViewModel);

        Assert.assertEquals(true, result.isValid());

        PersonDomainModel personDomainModel = result.getEntity().get();

        Assert.assertEquals("Philipp", personDomainModel.getFirstName());
        Assert.assertEquals("Wagner", personDomainModel.getLastName());
        Assert.assertEquals(LocalDate.of(1986, 5, 12), personDomainModel.getBirthDate());
    }

    @Test
    public void testMapping_Error() {
        PersonMapper mapper = new PersonMapper(() -> new PersonDomainModel());

        PersonViewModel personViewModel = new PersonViewModel();

        personViewModel.setFirstName("Philipp");
        personViewModel.setLastName("Wagner");
        personViewModel.setBirthDate("1986-05");

        MappingResult<PersonDomainModel> result = mapper.map(personViewModel);

        Assert.assertEquals(false, result.isValid());
    }
}
```

## Advanced Usage: Nested Properties ##

[JSimpleMapper] also allows to map complex nested objects. In the following example you can see how to map a flat ``PersonAddress`` class into a rich domain 
model ``Person``, which has a nested ``Address`` property. You simply implement two converters for the mapping ``PersonAddress -> Address`` and the mapping 
``PersonAddress -> Person``. The ``PersonMapper``, then defines to use the ``AddressMapper`` for the ``Person.address`` property.

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.jsimplemapper;

import de.bytefish.jsimplemapper.func.ICreator;
import de.bytefish.jsimplemapper.mapping.MappingResult;
import org.junit.Assert;
import org.junit.Test;

public class PersonNestedEntityTest {

    public class PersonAddress {

        private String firstName;
        private String lastName;

        private String street;
        private String city;

        public String getFirstName() {
            return firstName;
        }

        public void setFirstName(String firstName) {
            this.firstName = firstName;
        }

        public String getLastName() {
            return lastName;
        }

        public void setLastName(String lastName) {
            this.lastName = lastName;
        }

        public String getStreet() {
            return street;
        }

        public void setStreet(String street) {
            this.street = street;
        }

        public String getCity() {
            return city;
        }

        public void setCity(String city) {
            this.city = city;
        }
    }

    public class Person {
        private String firstName;
        private String lastName;
        private Address address;

        public String getFirstName() {
            return firstName;
        }

        public void setFirstName(String firstName) {
            this.firstName = firstName;
        }

        public String getLastName() {
            return lastName;
        }

        public void setLastName(String lastName) {
            this.lastName = lastName;
        }

        public Address getAddress() {
            return address;
        }

        public void setAddress(Address address) {
            this.address = address;
        }
    }

    public class Address {
        private String street;
        private String city;

        public String getStreet() {
            return street;
        }

        public void setStreet(String street) {
            this.street = street;
        }

        public String getCity() {
            return city;
        }

        public void setCity(String city) {
            this.city = city;
        }
    }

    public class AddressMapper extends AbstractMapper<PersonAddress, Address> {

        public AddressMapper(ICreator<Address> creator) {
            super(creator);

            mapProperty(PersonAddress::getStreet, String.class, Address::setStreet, String.class);
            mapProperty(PersonAddress::getCity, String.class, Address::setCity, String.class);
        }
    }

    public class PersonMapper extends AbstractMapper<PersonAddress, Person> {

        public PersonMapper(ICreator<Person> creator) {
            super(creator);

            mapProperty(PersonAddress::getFirstName, String.class, Person::setFirstName, String.class);
            mapProperty(PersonAddress::getLastName, String.class, Person::setLastName, String.class);
            mapProperty(Person::setAddress, new AddressMapper(() -> new Address()));
        }
    }

    @Test
    public void testMapping_nested() {
        PersonAddress personAddress = new PersonAddress();

        personAddress.setFirstName("Philipp");
        personAddress.setLastName("Wagner");

        personAddress.setStreet("Fake Street 123");
        personAddress.setCity("Faketown");

        PersonMapper mapper = new PersonMapper(() -> new Person());

        MappingResult<Person> result = mapper.map(personAddress);

        Assert.assertEquals(true, result.isValid());

        Person person = result.getEntity().get();

        Assert.assertEquals("Philipp", person.getFirstName());
        Assert.assertEquals("Wagner", person.getLastName());

        Address address = person.getAddress();

        Assert.assertNotNull(address);

        Assert.assertEquals("Fake Street 123", address.getStreet());
        Assert.assertEquals("Faketown", address.getCity());
    }
}
```