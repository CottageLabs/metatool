try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

from dateutil import parser

class DateValidator(plugin.Validator):
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["date"]
    
    def validate(self, datatype, thedate, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation
        kwargs["validation_response"] = r
        return self.validate_format(datatype, thedate, *args, **kwargs)
    
    def validate_format(self, datatype, thedate, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        try:
            parsed_date = parser.parse(thedate)
            r.info("Date was successfully parsed")
        except:
            r.error("Unable to parse the supplied date")
        return r
    
    def validate_realism(self, datatype, thedate, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        return r

class DatesSimilar(plugin.Comparator):
    def supports(self, datatype, **comparison_options):
        return False
    
    def compare(self, datatype, original, comparison, **comparison_options):
        r = plugin.ComparisonResponse()
        
        ods = []
        try:
            od1 = parser.parse(original, dayfirst=True, yearfirst=True)
            ods.append(od1)
        except:
            pass
        
        try:
            od2 = parser.parse(original, dayfirst=True, yearfirst=False)
            ods.append(od2)
        except:
            pass
        
        try:
            od3 = parser.parse(original, dayfirst=False, yearfirst=True)
            ods.append(od3)
        except:
            pass
        
        try:
            od4 = parser.parse(original, dayfirst=False, yearfirst=False)
            ods.append(od4)
        except:
            pass
        
        cds = []
        try:
            cd1 = parser.parse(comparison, dayfirst=True, yearfirst=True)
            cds.append(cd1)
        except:
            pass
        
        try:
            cd2 = parser.parse(comparison, dayfirst=True, yearfirst=False)
            cds.append(cd2)
        except:
            pass
            
        try:
            cd3 = parser.parse(comparison, dayfirst=False, yearfirst=True)
            cds.append(cd3)
        except:
            pass
            
        try:
            cd4 = parser.parse(comparison, dayfirst=False, yearfirst=False)
            cds.append(cd4)
        except:
            pass
        
        for od in ods:
            for cd in cds:
                if od == cd:
                    r.success = True
                    return r
        
        r.sucess = False
        return r
