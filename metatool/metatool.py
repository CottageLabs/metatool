import plugin

validators = plugin.load_validators()
comparators = plugin.load_comparators()

def validate_field(datatype, value, **validation_options):
    results = []
    for name, validator in validators.iteritems():
        if validator.supports(datatype, **validation_options):
            result = validator.validate(datatype, value, **validation_options)
            result.provenance = name
            results.append(result)
    return results
    
def validate_fieldset(fieldset, **validation_options):

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
            origin = cr.origin()
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
                    
                            
                    
