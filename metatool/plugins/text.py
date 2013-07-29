import plugin as plugin

class TitleAbstract(plugin.Plugin):

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
        
