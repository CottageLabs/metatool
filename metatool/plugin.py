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
    
    def warn(self, warn):
        self._warn.append(warn)
        
    def error(self, error):
        self._error.append(error)
        
    def has_errors(self):
        return len(self._error) > 0
    
    def correction(self, correction):
        self._correction.append(correction)
    
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
        self.provenance = None
        self._correction = []
        self._alternative = []
        self.compared_with = None
    
    def json(self, indent=None):
        desc = {
            "success" : self.success,
            "provenance" : self.provenance,
            "correction" : self._correction,
            "alternative" : self._alternative,
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

    def _ensure(self, field_name):
        if field_name not in self.fieldset:
            self.fieldset[field_name] = {"datatype" : None, "values" : [], "crossref" : None}

def load_validators():
    return _load(Validator)

def load_comparators():
    return _load(Comparator)

def load_generators():
    return _load(Generator)

def _load(klazz):
    plugin_instances = {}
    modules = get_modules("plugins")
    for modname, modpath in modules:
        mod = imp.load_source(modname, os.path.join(modpath, modname + ".py"))
        members = dir(mod)
        for member in members:
            attr = getattr(mod, member)
            if isinstance(attr, type):
                if issubclass(attr, klazz):
                    plugin_instances[modname + "." + attr.__name__] = attr()
    return plugin_instances

def get_modules(package_name):
    file, pathname, description = imp.find_module(package_name)
    if file:
        raise ImportError('Not a package: %r', package_name)
        
    # Use a set because some may be both source and compiled.
    return [(os.path.splitext(module)[0], pathname)
        for module in os.listdir(pathname)
        if module.endswith(MODULE_EXTENSIONS) and module != "__init__.py"]
