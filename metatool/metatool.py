import plugin
from copy import deepcopy

validators = plugin.load_validators()
comparators = plugin.load_comparators()
generators = plugin.load_generators()

def validate_field(datatype, value, **validation_options):
    results = []
    for name, validator in validators.iteritems():
        if validator.supports(datatype, **validation_options):
            result = validator.validate(datatype, value, **validation_options)
            result.provenance = name
            results.append(result)
    return results

def validate_fieldset(fieldset, **validation_options):
    # first task is to validate all the individual fields, which may
    # also obtain from us some data to cross-reference
    for field in fieldset.fields():
        datatype = fieldset.datatype(field)
        for value in fieldset.values(field):
            results = validate_field(datatype, value, **validation_options)
            fieldset.results(field, value, results)

    # see if there's any crossreferencing we can do
    crossref_data = fieldset.get_crossref_data()
    if len(crossref_data) == 0:
        return
    
    # cross reference each field where possible
    for field in fieldset.fields():
        crossref = fieldset.crossref(field)
        
        # prune out all the comparator plugins that don't apply
        comparator_plugins = {}
        for name, comparator in comparators.iteritems():
            if comparator.supports(crossref):
                comparator_plugins[name] = comparator
        if len(comparator_plugins.keys()) == 0:
            continue
        
        additionals = {}
        field_comparison_register = {}
        for cr in crossref_data:
            compare = cr.get(crossref)
            additional = _list_compare(field_comparison_register, crossref, fieldset.values(field), compare, comparator_plugins, cr, **validation_options)
            for a in additional:
                _append(additionals, a, cr.source_name())
        
        if len(field_comparison_register.keys()) > 0: 
            fieldset.comparisons(field, field_comparison_register)
        
        if len(additionals.keys()) > 0:
            fieldset.additionals(field, additionals)
    

def _list_compare(comparison_register, datatype, original, compare, comparator_plugins, data_source, **comparison_options):
    additional = deepcopy(compare)
    for o in original:
        for c in compare:
            for name, p in comparator_plugins.iteritems():
                result = p.compare(datatype, o, c, **comparison_options)
                result.compared_with = c
                result.comparator = name
                result.data_source = data_source.source_name()
                if result.success:
                    _append(comparison_register, o, result)
                    if o in additional:
                        additional.remove(o)
                        
        # if we don't get any successful hits, record a blank result for the value
        if o not in comparison_register:
            comparison_register[o] = []
            
    return additional

def _append(d, k, v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]                

"""
def validate_fieldset_old(fieldset, **validation_options):

    # first validate each of the datatype/value pairs independently
    field_validation_results = {}
    cross_reference = []
    for datatype, values in fieldset.iteritems():
        field_validation_results[datatype] = {}
        for value in values:
            results = validate_field(datatype, value)
            field_validation_results[datatype][value] = results
            for r in results:
                if r.data is not None and isinstance(r.data, plugin.DataWrapper):
                    cross_reference.append(r.data)
    
    # now cross reference the fieldset as a whole with data collected during validation
    for cr in cross_reference:                              # for each dataset to cross reference against
        for datatype, values in fieldset.iteritems():       # for each field in the incoming fieldset
            
            refertos = cr.get(datatype)                     # get the dataset's reference field(s)
            if refertos is None or len(refertos) == 0:
                continue
            
            for name, comparator in comparators.iteritems():    # for each comparator plugin    
                if not comparator.supports(datatype, **validation_options):    # check the plugin supports this datatype
                    continue
                
                for value in values:                            # for each value in the fieldset
                    value_results = []
                    success_results = []
                    for referto in refertos:                      # for each comparison field in the reference set
                        result = comparator.compare(datatype, value, referto, **validation_options) # pass the value and the reference in
                        result.provenance = name
                        result.compared_with = referto
                        value_results.append(result)
                        if result.success:
                            success_results.append(result)
                    
                    if len(success_results) > 0:                
                        # if the field was successfully validated, record the successes, as they may contain useful info
                        field_validation_results[datatype][value] += success_results
                    else:
                        # if the field could not be validated against any of the references, record all failures
                        field_validation_results[datatype][value] += value_results
    
    return field_validation_results
"""

def validate_model(modeltype, model_stream, **validation_options):
    fieldsets = None
    for name, genny in generators.iteritems():
        if genny.supports(modeltype, **validation_options):
            fieldsets = genny.generate(modeltype, model_stream, **validation_options)
            break
    
    for fieldset in fieldsets:
        validate_fieldset(fieldset, **validation_options)
    
    return fieldsets






































                            
                    
