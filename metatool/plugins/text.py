import metatool.plugin as plugin
import Levenshtein

class TitleAbstract(plugin.Validator):

    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower == "title" or lower == "description" or lower == "abstract"
        
    def validate(self, datatype, value, *arg, **kwargs):
        r = plugin.ValidationResponse()
        self.validate_format(datatype, value, validation_response=r)
        return r
    
    def validate_format(self, datatype, value, *arg, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        if len(value) <= 1 and datatype == "title":
            r.warn("Title field is one character or less long - might not really be the title")
        elif len(value) <= 3 and datatype == "title":
            r.warn("Title is very short - might not really be the title")
        
        if len(value) <= 1 and datatype in ["description", "abstract"]:
            r.warn("Description/Abstract field is one character or less long - very unlikely to be valid")
        elif len(value) <= 10 and datatype in ["description", "abstract"]:
            r.warn("Description/Abstract is very short - it may not be the actual description/abstract, or may be inadequate")
        
        return r

class Equivalent(plugin.Comparator):
    def supports(self, datatype, **comparison_options):
        return False
    
    def compare(self, datatype, original, comparison, **comparison_options):
        r = plugin.ComparisonResponse()
        # equivalent things have to be equivalent!
        r.success = original == comparison
        return r

class LevenshteinDistance(plugin.Comparator):
    def supports(self, datatype, **comparison_options):
        return False
    
    def compare(self, datatype, original, comparison, **comparison_options):
        r = plugin.ComparisonResponse()
        
        # ensure everything is unicode
        original = original.decode("utf-8")
        comparison = comparison.decode("utf-8")
        
        # find out if we have a distance ratio threshold to meet
        threshold = comparison_options.get("levenshtein_ratio_threshold", 0.90)
        
        # equivalent things have to be equivalent!
        ratio = Levenshtein.ratio(original, comparison)
        r.success = ratio > threshold
        
        print original, comparison, threshold, ratio
        
        # if this is not an exact match, suggest the data source's version as a correction
        if ratio != 1.0:
            r.correction(comparison)
            
        return r
