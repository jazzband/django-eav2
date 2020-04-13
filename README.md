[![Build Status](https://travis-ci.org/makimo/django-eav2.svg?branch=master)](https://travis-ci.org/makimo/django-eav2)
[![Coverage Status](https://coveralls.io/repos/github/makimo/django-eav2/badge.svg?branch=master)](https://coveralls.io/github/makimo/django-eav2?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/159540d899bd41bb860f0ce996427e1f)](https://www.codacy.com/app/IwoHerka/django-eav2?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=makimo/django-eav2&amp;utm_campaign=Badge_Grade)
[![Maintainability](https://api.codeclimate.com/v1/badges/b90eacf7a90db4b58f13/maintainability)](https://codeclimate.com/github/makimo/django-eav2/maintainability)
![Python Version](https://img.shields.io/badge/Python-2.7,%203.5,%203.6,%203.7dev-blue.svg)
![Django Version](https://img.shields.io/badge/Django-1.11,%202.0,%203.0,%20tip-green.svg)

## Django EAV 2 - Entity-Attribute-Value storage for Django

Django EAV 2 is a fork of django-eav (which itself was derived from eav-django).
You can find documentation <a href="https://django-eav-2.rtfd.io">here</a>.

## What is EAV anyway?

> Entity–attribute–value model (EAV) is a data model to encode, in a space-efficient manner, entities where the number of attributes (properties, parameters) that can be used to describe them is potentially vast, but the number that will actually apply to a given entity is relatively modest. Such entities correspond to the mathematical notion of a sparse matrix. (Wikipedia)

Data in EAV is stored as a 3-tuple (typically corresponding to three distinct tables):

* The entity: the item being described, e.g. `Person(name='Mike')`.
* The attribute: often a foreign key into a table of attributes, e.g. `Attribute(slug='height', datatype=FLOAT)`.
* The value of the attribute, with links both an attribute and an entity, e.g. `Value(value_float=15.5, person=mike, attr=height)`.

Entities in **django-eav2** are your typical Django model instances. Attributes (name and type) are stored in their own table, which makes it easy to manipulate the list of available attributes in the system. Values are an intermediate table between attributes and entities, each instance holding a single value.
This implementation also makes it easy to edit attributes in Django Admin and form instances.

You will find detailed description of the EAV here:

* [Wikipedia - Entity–attribute–value model](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model)

## EAV - The Good, the Bad or the Ugly?

EAV is a trade-off between flexibility and complexity. As such, it should not be thought of as either an amelioration pattern, nor an anti-pattern. It is more of a [gray pattern](http://wiki.c2.com/?GreyPattern) - it exists in some context, to solve certain set of problems. When used appropriately, it can introduce great flexibility, cut prototyping time or deacrease complexity. When used carelessly, however, it can complicate database schema, degrade the performance and make maintainance hard. **As with every tool, it should not be overused.** In the following paragraphs we briefly discuss the pros, the cons and pointers to keep in mind when using EAV.

### When to use EAV?

Originally, EAV was introduced to workaround a problem which cannot be easily solved within relational model. In order to achieve this, EAV bypasses normal schema restrictions. Some refer to this as an example of the [inner-platform effect](https://en.wikipedia.org/wiki/Inner-platform_effect#Examples). Naturally, in such scenarios RDMS resources cannot be used efficiently.

Typical application of the EAV model sets to solve the problem of sparse data with a large number of applicable attributes, but only a small fraction that applies to a given entity that may not be known beforehand. Consider the classic example:

 > A problem that data modelers commonly encounter in the biomedical domain is organizing and storing highly diverse and heterogeneous data. For example, a single patient may have thousands of applicable descriptive parameters, all of which need to be easily accessible in an electronic patient record system. These requirements pose significant modeling and implementation challenges. [1]

 And:

 > [...] what do you do when you have customers that demand real-time, on-demand addition of attributes that they want to store?  In one of the systems I manage, our customers wanted to do exactly this.  Since we run a SaaS (software as a service) application, we have many customers across several different industries, who in turn want to use our system to store different types of information about *their* customers.  A salon chain might want to record facts such as 'hair color,' 'hair type,' and 'haircut frequency'; while an investment company might want to record facts such as 'portfolio name,' 'last portfolio adjustment date,' and 'current portfolio balance.' [2]

 In both of these problems we have to deal with sparse and heterogeneous properties that apply only to potentially different subsets of particular entities. Applying EAV to a sub-schema of the database allows to model the desired behaviour. Traditional solution would involves wide tables with many columns storing NULL values for attributes that don't apply to an entity.

Very common use case for EAV are custom product attributes in E-commerce implementations, such as Magento. [3]

 As a rule of thumb, EAV can be used when:
 
 * Model attributes are to be added and removed by end users (or are unknowable in some different way). EAV supports these without ALTER TABLE statements and allows the attributes to be strongly typed and easily searchable.
 * There will be many attributes and values are sparse, in contrast to having tables with mostly-null columns.
 * The data is highly dynamic/volatile/vulnerable to change. This problem is present in the second example given above. Other example would be rapidly evolving system, such as a prototype with constantly changing requirements.
 * We want to store meta-data or supporting information, e.g. to customize system's behavior.
 * Numerous classes of data need to be represented, each class has a limited number of attributes, but the number of instances of each class is very small.
* We want to minimise programmer's input when changing the data model.

For more throughout discussion on the appriopriate use-cases see:

1. [Wikipedia - Scenarios that are appropriate for EAV modeling](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model#Scenarios_that_are_appropriate_for_EAV_modeling)
2. [StackOverflow - Entity Attribute Value Database vs. strict Relational Model E-commerce](https://stackoverflow.com/questions/870808/entity-attribute-value-database-vs-strict-relational-model-ecommerce)
3. [WikiWikiWeb - Generic Data Model](http://wiki.c2.com/?GenericDataModel)

## When to avoid it?

As we outlined in the opening section, EAV is a trade-off. It should not be used when:

##### 1. System is performance critical

> Attribute-centric query is inherently more difficult when data are stored in EAV form than when they are stored conventionally. [4]

In general, the more structured your data model, the more efficiently you can deal with it. Therefore, loose data storage such as EAV has obvious trade-off in performance. Specifically, application of the EAV model makes performing JOINs on tables more complicated.

##### 2. Low complexity/low maintenance cost is of priority

EAV complicates data model by splitting information across tables. This increases conceptual complexity as well as SQL statements required to query the data. In consequence, optimization in one area that also makes the system harder to understand and maintain.

However, it is important to note that:

> An EAV design should be employed only for that sub-schema of a database where sparse attributes need to be modeled: even here, they need to be supported by third normal form metadata tables. There are relatively few database-design problems where sparse attributes are encountered: this is why the circumstances where EAV design is applicable are relatively rare. [1]

## Alternatives

In some use-cases, JSONB (binary JSON data) datatype (Postgres 9.4+ and analogous in other RDMSs) can be used as an alternative to EAV. JSONB supports indexing, which amortizes performance trade-off. It's important to keep in mind that JSONB is not RDMS-agnostic solution and has it's own problems, such as typing.

## Installation

You can install **django-eav2** from three sources:
```bash
# From PyPI via pip
pip install django-eav2

# From source via pip
pip install git+https://github.com/makimo/django-eav2@master

# From source via setuptools
git clone git@github.com:makimo/django-eav2.git
cd django-eav2
python setup.py install

# To uninstall:
python setup.py install --record files.txt
rm $(cat files.txt)
```

## Getting started

**Step 1.** Register a model:

```python
import eav
eav.register(Supplier)
```

or with decorators:

```python
from eav.decorators import register_eav

@register_eav
class Supplier(models.Model):
    ...
```

**Step 2.** Create an attribute:

```python
Attribute.objects.create(name='City', datatype=Attribute.TYPE_TEXT)
```

**Step 3.** That’s it! You’re ready to go:

```python
supplier.eav.city = 'London'
supplier.save()

Supplier.objects.filter(eav__city='London')
# = <EavQuerySet [<Supplier: Supplier object (1)>]>
```

### What next? Check out <a href="https://django-eav-2.readthedocs.io/en/improvement-docs/">documentation</a>.

<hr>
<br>

### References

[1] Exploring Performance Issues for a Clinical Database Organized Using an Entity-Attribute-Value Representation, https://doi.org/10.1136/jamia.2000.0070475 <br>
[2] What is so bad about EAV, anyway?, https://sqlblog.org/2009/11/19/what-is-so-bad-about-eav-anyway <br>
[3] Magento for Developers: Part 7—Advanced ORM: Entity Attribute Value, https://devdocs.magento.com/guides/m1x/magefordev/mage-for-dev-7.html <br>
[4] Data Extraction and Ad Hoc Query of an Entity— Attribute— Value Database, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC61332/
