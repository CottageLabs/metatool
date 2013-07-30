import plugin as plugin

"""
class TestOrcid(plugin.Validator):
    def supports(self, datatype, **validation_options):
        lower = datatype.lower()
        return lower == "orcid"
    
    def validate(self, datatype, value, *args, **validation_options):
        r = plugin.ValidationResponse()
        r.data = TestOrcidWrapper()
        return r

class TestOrcidWrapper(plugin.DataWrapper):
    def get(self, field):
        if field == "name": return ["richard"]
        return None
"""
