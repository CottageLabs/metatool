import imp, os

MODULE_EXTENSIONS = ('.py') # only interested in .py files, not pyc or pyo

class Plugin(object):
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
        
def load():
    plugin_instances = {}
    modules = get_modules("plugins")
    for modname, modpath in modules:
        mod = imp.load_source(modname, os.path.join(modpath, modname + ".py"))
        members = dir(mod)
        for member in members:
            attr = getattr(mod, member)
            if isinstance(attr, type):
                if issubclass(attr, Plugin):
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
