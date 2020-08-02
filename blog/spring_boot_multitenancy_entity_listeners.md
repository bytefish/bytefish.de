title: Using EntityListeners to provide Multitenancy with Spring Boot
date: 2020-08-02 15:17
tags: java, spring
category: java
slug: spring_boot_multitenancy_entity_listeners
author: Philipp Wagner
summary: This article shows how to provide Multitenancy with Spring Boot using Row Level Security.

In a previous post I have shown how to build a multitenant application using the Row Level Security features of PostgreSQL:

* [https://bytefish.de/blog/spring_boot_multitenancy_using_rls/](https://bytefish.de/blog/spring_boot_multitenancy_using_rls/)

Let's iterate on this work and see how to automatically set the Tenant before persisting records to the database.

All code can be found in the GitHub repository at:

* [https://github.com/bytefish/SpringBootMultiTenancyUsingRowLevelSecurity](https://github.com/bytefish/SpringBootMultiTenancyUsingRowLevelSecurity)

## Setting the Tenant using an EntityListener ##

[Explicit is better, than implicit]: https://en.wikipedia.org/wiki/Zen_of_Python

The previous example had a column ``tenant_name`` on each entity, that we set the row level policy on. This column has been set to the 
Tenant name before writing the data to the database. While being [explicit is better, than implicit] it can be tedious to do this for 
each entity.

So we first start by defining an ``@Embeddable`` class named ``Tenant``. This way we can embed the class in a JPA entity and 
it defines the ``tenant_name`` column:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.model;

import javax.persistence.Column;
import javax.persistence.Embeddable;

@Embeddable
public class Tenant {

    @Column(name = "tenant_name")
    private String tenantName;

    public String getTenantName() {
        return tenantName;
    }

    public void setTenantName(String tenantName) {
        this.tenantName = tenantName;
    }
}
```

A class that should be only available to a specifc Tenant then implements the ``TenantAware`` interface:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.core;

import de.bytefish.multitenancy.model.Tenant;

public interface TenantAware {

    Tenant getTenant();

    void setTenant(Tenant tenant);
}
```

This way we can set the Tenant information from the ``ThreadLocalStorage`` to the class from the outside. Now 
this ``TenantAware`` interface can be used in an ``EntityListener``, that implements the ``@PreUpdate``, 
``@PreRemove`` and ``PrePersist`` events:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.core;

import de.bytefish.multitenancy.model.Tenant;

import javax.persistence.PrePersist;
import javax.persistence.PreRemove;
import javax.persistence.PreUpdate;

public class TenantListener {

    @PreUpdate
    @PreRemove
    @PrePersist
    public void setTenant(TenantAware entity) {
        Tenant tenant = entity.getTenant();

        if(tenant == null) {
            tenant = new Tenant();

            entity.setTenant(tenant);
        }

        final String tenantName = ThreadLocalStorage.getTenantName();

        tenant.setTenantName(tenantName);
    }
}
```

What's left is to implement the actual ``Customer`` JPA Entity. It implements the ``TenantAware`` interface, and is annotated with our ``TenantListener``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.model;

import de.bytefish.multitenancy.core.TenantAware;
import de.bytefish.multitenancy.core.TenantListener;

import javax.persistence.*;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(schema = "sample", name = "customer")
@EntityListeners(TenantListener.class)
public class Customer implements TenantAware {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "customer_id")
    private Long id;

    @Embedded
    private Tenant tenant;

    @Column(name = "first_name")
    private String firstName;

    @Column(name = "last_name")
    private String lastName;

    @OneToMany(mappedBy = "customer", fetch = FetchType.EAGER, cascade = CascadeType.ALL)
    List<CustomerAddress> addresses = new ArrayList<>();

    public Customer() {
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

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

    public List<CustomerAddress> getAddresses() {
        return addresses;
    }

    public void setAddresses(List<CustomerAddress> addresses) {
        this.addresses = addresses;
    }

    @Override
    public Tenant getTenant() {
        return tenant;
    }

    @Override
    public void setTenant(Tenant tenant) {
        this.tenant = tenant;
    }
}
```

And we also annotate the ``Address``, that belongs to a ``Customer``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.model;

import de.bytefish.multitenancy.core.TenantAware;
import de.bytefish.multitenancy.core.TenantListener;

import javax.persistence.*;
import java.util.Set;

@Entity
@Table(schema = "sample", name = "address")
@EntityListeners(TenantListener.class)
public class Address implements TenantAware {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "address_id")
    private Long id;

    @Embedded
    private Tenant tenant;

    @Column(name = "name")
    private String name;

    @Column(name = "street")
    private String street;

    @Column(name = "postalcode")
    private String postalcode;

    @Column(name = "city")
    private String city;

    @Column(name = "country")
    private String country;

    public Address() {

    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getStreet() {
        return street;
    }

    public void setStreet(String street) {
        this.street = street;
    }

    public String getPostalcode() {
        return postalcode;
    }

    public void setPostalcode(String postalcode) {
        this.postalcode = postalcode;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getCountry() {
        return country;
    }

    public void setCountry(String country) {
        this.country = country;
    }

    @Override
    public Tenant getTenant() {
        return tenant;
    }

    @Override
    public void setTenant(Tenant tenant) {
        this.tenant = tenant;
    }
}
```

I didn't find a simple way to extend a ``@JoinTable`` using JPA, so it can be made ``TenantAware``. That's why 
I suppose to define the join table yourself in a separate entity, instead of having JPA generating it. This way 
it can participate in the ``TenantListener``:

```java
// Copyright (c) Philipp Wagner. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

package de.bytefish.multitenancy.model;

import de.bytefish.multitenancy.core.TenantAware;
import de.bytefish.multitenancy.core.TenantListener;

import javax.persistence.*;
import java.io.Serializable;
import java.util.Objects;

@Entity
@Table(schema = "sample", name = "customer_address")
@EntityListeners(TenantListener.class)
public class CustomerAddress implements TenantAware {

    @Embeddable
    public static class Id implements Serializable {

        @Column(name = "customer_id", nullable = false)
        private Long customerId;

        @Column(name = "address_id", nullable = false)
        private Long addressId;

        private Id() {

        }

        public Id(Long customerId, Long addressId) {
            this.customerId = customerId;
            this.addressId = addressId;
        }

        public Long getCustomerId() {
            return customerId;
        }

        public Long getAddressId() {
            return addressId;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Id that = (Id) o;
            return Objects.equals(customerId, that.customerId) &&
                    Objects.equals(addressId, that.addressId);
        }

        @Override
        public int hashCode() {
            return Objects.hash(customerId, addressId);
        }
    }

    @EmbeddedId
    private Id id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id", insertable = false, updatable = false)
    private Customer customer;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "address_id", insertable = false, updatable = false)
    private Address address;

    @Embedded
    private Tenant tenant;

    private CustomerAddress() {
    }

    public CustomerAddress(Customer customer, Address address) {
        this.id = new Id(customer.getId(), address.getId());
        this.customer = customer;
        this.address = address;
    }

    public Id getId() {
        return id;
    }

    public Customer getCustomer() {
        return customer;
    }

    public Address getAddress() {
        return address;
    }

    @Override
    public Tenant getTenant() {
        return tenant;
    }

    @Override
    public void setTenant(Tenant tenant) {
       this.tenant = tenant;
    }

}
```

Now let's see, if it works.

### Example ###

We start with inserting customers to the database of Tenant ``TenantOne``:

```
> curl -H "X-TenantID: TenantOne" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Philipp\", \"lastName\" : \"Wagner\", \"addresses\": [ { \"name\": \"Philipp Wagner\", \"street\" : \"Hans-Andersen-Weg 90875\", \"postalcode\": \"54321\", \"city\": \"Duesseldorf\", \"country\": \"Germany\"} ] }" http://localhost:8080/customers

{"id":1,"firstName":"Philipp","lastName":"Wagner","addresses":[{"id":1,"name":"Philipp Wagner","street":"Hans-Andersen-Weg 90875","postalcode":"54321","city":"Duesseldorf","country":"Germany"}]}

> curl -H "X-TenantID: TenantOne" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Max\", \"lastName\" : \"Mustermann\", \"addresses\": [ { \"name\": \"Max Mustermann\", \"street\" : \"Am Wald 8797\", \"postalcode\": \"12345\", \"city\": \"Berlin\", \"country\": \"Germany\"} ] }" http://localhost:8080/customers

{"id":2,"firstName":"Max","lastName":"Mustermann","addresses":[{"id":2,"name":"Max Mustermann","street":"Am Wald 8797","postalcode":"12345","city":"Berlin","country":"Germany"}]}
```

Getting a list of all customers for ``TenantOne`` will now return two customers:

```
> curl -H "X-TenantID: TenantOne" -X GET http://localhost:8080/customers

[{"id":1,"firstName":"Philipp","lastName":"Wagner","addresses":[{"id":1,"name":"Philipp Wagner","street":"Hans-Andersen-Weg 90875","postalcode":"54321","city":"Duesseldorf","country":"Germany"}]},{"id":2,"firstName":"Max","lastName":"Mustermann","addresses":[{"id":2,"name":"Max Mustermann","street":"Am Wald 8797","postalcode":"12345","city":"Berlin","country":"Germany"}]}]
```

While requesting a list of all customers for ``TenantTwo`` returns an empty list:

```
> curl -H "X-TenantID: TenantTwo" -X GET http://localhost:8080/customers

[]
```

We can now insert a customer into the ``TenantTwo`` database:

```
> curl -H "X-TenantID: TenantTwo" -H "Content-Type: application/json" -X POST -d "{\"firstName\" : \"Hans\", \"lastName\" : \"McMillan\", \"addresses\": [ { \"name\": \"Hans McMillan\", \"street\" : \"Lilienweg 50875\", \"postalcode\": \"59756\", \"city\": \"Muenchen\", \"country\": \"Germany\"} ] }" http://localhost:8080/customers

{"id":3,"firstName":"Hans","lastName":"McMillan","addresses":[{"id":3,"name":"Hans McMillan","street":"Lilienweg 50875","postalcode":"59756","city":"Muenchen","country":"Germany"}]}
```

Querying the ``TenantOne`` database still returns the two customers:

```
> curl -H "X-TenantID: TenantOne" -X GET http://localhost:8080/customers

[{"id":1,"firstName":"Philipp","lastName":"Wagner","addresses":[{"id":1,"name":"Philipp Wagner","street":"Hans-Andersen-Weg 90875","postalcode":"54321","city":"Duesseldorf","country":"Germany"}]},{"id":2,"firstName":"Max","lastName":"Mustermann","addresses":[{"id":2,"name":"Max Mustermann","street":"Am Wald 8797","postalcode":"12345","city":"Berlin","country":"Germany"}]}]
```

Querying the ``TenantTwo`` database will now return the inserted customer:

```
> curl -H "X-TenantID: TenantTwo" -X GET http://localhost:8080/customers

[{"id":3,"firstName":"Hans","lastName":"McMillan","addresses":[{"id":3,"name":"Hans McMillan","street":"Lilienweg 50875","postalcode":"59756","city":"Muenchen","country":"Germany"}]}]
```