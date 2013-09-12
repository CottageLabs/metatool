try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

class IntegerValidator(plugin.Validator):
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["integer"]
    
    def validate(self, datatype, number, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation
        kwargs["validation_response"] = r
        return self.validate_format(datatype, number, *args, **kwargs)
    
    def validate_format(self, datatype, number, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        # inputs might be string representations of ints, or ints
        if not isinstance(number, int) and not isinstance(number, str):
            r.error("Field content is not an integer")
            return r
        
        # convert any strings to ints
        try:
            number = int(number)
        except:
            r.error("Field content is not an integer")
            return r
        
        r.info("Field content is an integer")
        return r
    
    def validate_realism(self, datatype, doi, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        return r

class IntegersEqual(plugin.Comparator):
    def supports(self, datatype, **comparison_options):
        return False
    
    def compare(self, datatype, original, comparison, **comparison_options):
        r = plugin.ComparisonResponse()
        
        # inputs might be string representations of ints, or ints
        if not isinstance(original, int) and not isinstance(original, str):
            r.success = False
            return r
        if not isinstance(comparison, int) and not isinstance(comparison, str):
            r.success = False
            return r
        
        # convert any strings to ints
        try:
            original = int(original)
        except:
            r.success = False
        try:
            comparison = int(comparison)
        except:
            r.success = False
        
        # equivalent things have to be equivalent!
        r.success = original == comparison
        return r




