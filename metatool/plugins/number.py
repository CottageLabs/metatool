try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

from dateutil import parser

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




