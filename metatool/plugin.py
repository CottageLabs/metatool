import imp, os, json

MODULE_EXTENSIONS = ('.py') # only interested in .py files, not pyc or pyo

class Validator(object):
    # subclasses should override these methods with their implementations
    def supports(self, datatype, **validation_options):
        raise NotImplementedError
        
    def validate(self, datatype, value, **validation_options):
        raise NotImplementedError
        
    def validate_format(self, datatype, value, **validation_options):
        raise NotImplementedError
        
    def validate_realism(self, datatype, value, **validation_options):
        raise NotImplementedError
    
class ValidationResponse(object):
    def __init__(self):
        self._info = []
        self._warn = []
        self._error = []
        self._correction = []
        self._alternative = []
        
        # write to this directly if you have some data from some service
        # which might be useful to the validator later
        self.data = None
        
        # you can write to this if you want, but the validator will
        # probably overwrite it for you later anyway, so no need to bother
        self.provenance = None
        
    def info(self, info):
        self._info.append(info)
    
    def get_info(self):
        return self._info
    
    def warn(self, warn):
        self._warn.append(warn)
        
    def get_warn(self):
        return self._warn
    
    def has_warnings(self):
        return len(self._warn) > 0
    
    def error(self, error):
        self._error.append(error)
    
    def get_error(self):
        return self._error
        
    def has_errors(self):
        return len(self._error) > 0
    
    def correction(self, correction):
        self._correction.append(correction)
        
    def get_corrections(self):
        return self._correction
        
    def get_alternatives(self):
        return self._alternative
    
    def alternative(self, alt):
        self._alternative.append(alt)
    
    def json(self, indent=None):
        desc = {
            "provenance" : self.provenance,
            "info" : self._info,
            "warn" : self._warn,
            "error" : self._error,
            "correction" :  self._correction,
            "alternative" : self._alternative
        }
        if indent is None:
            return json.dumps(desc)
        else:
            return json.dumps(desc, indent=indent)
    
class DataWrapper(object):
    def source_name(self):
        raise NotImplementedError

    def get(self, datatype):
        raise NotImplementedError
        

class Comparator(object):
    # subclasses should override these methods with their implementations
    def supports(self, datatype, **comparison_options):
        raise NotImplementedError
    
    def compare(self, datatype, original, comparison, **comparison_options):
        raise NotImplementedError
        

class ComparisonResponse(object):
    def __init__(self):
        self.success = False
        self.comparator = None
        self.data_source = None
        self._correction = []
        self.compared_with = None
    
    def correction(self, correction):
        self._correction.append(correction)
    
    def get_corrections(self):
        return self._correction
    
    def json(self, indent=None):
        desc = {
            "success" : self.success,
            "comparator" : self.comparator,
            "correction" : self._correction,
            "data_source" : self.data_source,
            "compared_with" :  self.compared_with
        }
        if indent is None:
            return json.dumps(desc)
        else:
            return json.dumps(desc, indent=indent)

class Generator(object):
    # subclasses should override these methods with their implementations
    def supports(self, modeltype, **generator_options):
        raise NotImplementedError
        
    def generate(self, modeltype, model_stream, **generator_options):
        raise NotImplementedError

class FieldSet(object):
    def __init__(self):
        self.fieldset = {}
        
    def add(self, field_name, value):
        self._ensure(field_name)
        if value not in self.fieldset[field_name]["values"]:
            self.fieldset[field_name]["values"].append(value)
    
    def datatype(self, field_name, datatype):
        self._ensure(field_name)
        self.fieldset[field_name]["datatype"] = datatype
    
    def crossref(self, field_name, crossref):
        self._ensure(field_name)
        self.fieldset[field_name]["crossref"] = crossref
    
    def field(self, field_name, datatype, values, crossref=None):
        if type(values) != list:
            values = [values]
        self._ensure(field_name)
        self.fieldset[field_name]["datatype"] = datatype
        self.fieldset[field_name]["values"] = values
        if crossref is not None:
            self.fieldset[field_name]["crossref"] = crossref
    
    def fields(self):
        return self.fieldset.keys()
        
    def values(self, field_name):
        return self.fieldset.get(field_name, {}).get("values", [])
        
    def datatype(self, field_name):
        return self.fieldset.get(field_name, {}).get("datatype")
        
    def crossref(self, field_name):
        return self.fieldset.get(field_name, {}).get("crossref")
    
    def get_validations(self, field_name, value):
        return self.fieldset.get(field_name, {}).get("validation", {}).get(value, [])
    
    def get_comparisons(self, field_name, value):
        return self.fieldset.get(field_name, {}).get("comparison", {}).get(value) # return a None if there were no comparisons
        
    def has_comparisons(self, field_name, value):
        return value in self.fieldset.get(field_name, {}).get("comparison", {})
    
    def comparisons(self, field_name, comparisons):
        self._ensure(field_name)
        self.fieldset[field_name]["comparison"] = comparisons
        
    def additionals(self, field_name, additionals):
        self._ensure(field_name)
        self.fieldset[field_name]["additional"] = additionals
    
    def results(self, field_name, value, results):
        self._ensure(field_name)
        self.fieldset[field_name]["validation"][value] = results
    
    def get_crossref_data(self):
        cross_reference = []
        for field, obj in self.fieldset.iteritems():
            for value, validation_results in obj.get("validation", {}).iteritems():
                for r in validation_results:
                    if r.data is not None and isinstance(r.data, DataWrapper):
                        cross_reference.append(r.data)
        return cross_reference
    
    def _ensure(self, field_name):
        if field_name not in self.fieldset:
            self.fieldset[field_name] = {
                "datatype" : None, 
                "values" : [], 
                "crossref" : None, 
                "validation" : {},
                "comparison" : {},
                "additional" : {}
            }

def load_validators():
    return _load(Validator)

def load_comparators():
    return _load(Comparator)

def load_generators():
    return _load(Generator)

def _load(klazz):
    plugin_instances = {}
    modules = get_modules("metatool.plugins")
    for modname, modpath in modules:
        mod = imp.load_source(modname, os.path.join(modpath, modname + ".py"))
        members = dir(mod)
        for member in members:
            attr = getattr(mod, member)
            if isinstance(attr, type):
                if issubclass(attr, klazz):
                    plugin_instances[modname + "." + attr.__name__] = attr()
    return plugin_instances

def get_modules(package_heirarchy):
    bits = package_heirarchy.split(".")
    parent_path = None
    file = path = description = None
    for bit in bits:
        file, path, description = imp.find_module(bit, parent_path)
        mod = imp.load_module(bit, file, path, description)
        parent_path = mod.__path__
    
    # file, pathname, description = imp.find_module(package_name)
    if file:
        raise ImportError('Not a package: %r', package_heirarchy)
        
    # Use a set because some may be both source and compiled.
    return [(os.path.splitext(module)[0], path)
        for module in os.listdir(path)
        if module.endswith(MODULE_EXTENSIONS) and module != "__init__.py"]
