import plugin

validators = plugin.load()

def validate_field(datatype, value, **validation_options):
    results = []
    for name, validator in validators.iteritems():
        if validator.supports(datatype, **validation_options):
            result = validator.run(datatype, value, **validation_options)
            result.provenance = name
            results.append(result)
    return results
