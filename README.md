# FieldSet Data Structure

## Full Overview

The FieldSet object expressed as a pything data structure is as follows:

    {
        "<field name>" : {
            "comparison": {
                "<value>" : ["<comparison response object>"]
            },
            "additional" : {
                "<value>" : ["<data source>"]
            },
            "datatype" : "<datatype of field>",
            "values" : ["<value>"],
            "validation" : {
                "<value>" : ["<validation response object>"]
            },
            "crossref" : "<generic name of field>"
        }
    }

In this there are two objects, a "comparison response" and a "validation response".

The ValidationResponse object, when expressed as a data structure is as follows:

    {
        "info" : ["<human readable information for user>"],
        "warn" : ["<human readable warnings for user>"],
        "error" : ["<human readable error message for user>"],
        "correction": ["<suggested correction to supplied value>"],
        "alternative" : ["<suggested alternatives or additional values>"],
        "provenance" : "<plugin which produced these results>"
    }

The ComparisonResponse object, when expressed as a data structure is as follows:

    {
        "correction": ["<suggested correction to supplied value>"],
        "data_source" : "<name of data source compared to>",
        "comparator" : "<plugin which produced these results>",
        "success" : true/false,
        "compared_with" : "<data source's value that the supplied value was compared with>"
    }

## FieldSet in detail

The top level keys in a FieldSet are the native names of the fields in the language of the client supplying the data.  This means they could be anything.  For example:

    {
        "ISSN": { ... },
        "Journal Title" : { ... },
        "Author ID" : { ... }
        "Author" : { ... }
    }

Each field has 6 standard properties: comparison, additional, datatype, values, validation, crossref.  Of these, datatype, values and crossref must be supplied by the client (probably via a Generator).  For example:

    {
        "Author ID" : {
            "datatype" : "orcid",
            "values" : ["0000-0002-0069-726X"],
            "crossref" : "orcid"
        }
    }

The fields have the following meanings:

* datatype - the datatype of the content of the field.  In our example, the datatype of the Author ID is an ORCID, so we'd expect to find values which validate as ORCIDs in there
* values - the list of values the client is providing us for this field.  In our example, we are hoping they turn out to be ORCIDs!
* crossref - a generic name for the field, so that it can be compared to external data sources.  In our example we use ORCID again, and we hope that external data sources which contain ORCIDs will be able to supply them when we ask for them.

Both datatype and crossref are best-guess fields - there is no taxonomy/ontology/controlled vocabulary.  If you assert that a field is an "orcid" datatype, then it will be inspected by any plugin that says that it understands the "orcid" datatype.  Beyond that, the datatype has no implicit meaning.  Similarly, the crossref field is used to request values from a remote datasource's DataWrapper, so if the DataWrapper understand what an "orcid" is, it will work, and if it does not it will not!

The remaining fields are computed during validation and have the following meanings:

* validation - a list of ValidationResponse objects for each supplied value.  Each one is from a single plugin which attempted to validate the data.  Multiple plugins may attempt to validate for you, and you will see all of the results in this field.  Every plugin which runs will add a response object to this list, irrespective of whether the validation was successful or not - it may supply warnings or error messages which are of value to the client.
* comparison - a list of ComparisonResponse objects for each supplied value.  Each one is from a single plugin which attempted to compare the value to an external data source.  Only comparisons which are successful are attached to the field/value.  Therefore, if there is a value in the "comparison" list with one or more ComparisonResponse objects, then external validation of the value was possible; if there is a value in the "comparison" list, with an empty list, then external validation of the value was attempted, but was unsuccessful; if there is no value in the "comparison" list, then no external validation was even attempted on this field.
* additional - any values found in external data sources which may belong in this field, but which do not appear in the supplied list of values.  The new/additional value is the key, and each value lists the datasets where it was located.

So, the full picture of a fieldset datastructure is:

    {
        "<field name>" : {
            "comparison": {
                "<value>" : ["<comparison response object>"]
            },
            "additional" : {
                "<value>" : ["<data source>"]
            },
            "datatype" : "<datatype of field>",
            "values" : ["<value>"],
            "validation" : {
                "<value>" : ["<validation response object>"]
            },
            "crossref" : "<generic name of field>"
        }
    }

Note that construction of fieldset datastructures should be done via the FieldSet object, which provides a coherent API for reading and writing into this datastructure.

# Plugin Types

## Validator

## Comparator

## Generator

## DataWrapper
