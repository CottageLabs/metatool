try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

import catflap

def search(issn=[], journal_title=[]):
    if len(issn) > 0:
        return catflap.Journal.search(issn=issn)
    elif len(journal_title) > 0:
        return catflap.Journal.search(journal_title=journal_title)
    return None

class ACATWrapper(plugin.DataWrapper):
    def __init__(self, journals):
        self.journals = journals

    def source_name(self):
        return "acat"

    def get(self, datatype):
        got = []
        lower = datatype.lower()
        if lower == "issn":
            for j in self.journals:
                got += j.data.get("issn", [])
        elif lower in ["journal", "journal_name", "journal_title"]:
            for j in self.journals:
                got += j.data.get("journal_name", [])
        return list(set(got))

