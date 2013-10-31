try:
    from metatool.dao import DomainObject
except ImportError:
    from dao import DomainObject

class Publication(DomainObject):
    __type__ = 'publication'
    es_index = 'ukriss'
