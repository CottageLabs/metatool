try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

from lxml import etree

class OutputsNodes(plugin.NodeMaker):
    NS = "{urn:xmlns:org:eurocris:cerif-1.6-2}"
    
    def supports(self, modeltype, **nodemaker_options):
        return modeltype == "ukriss_outputs"
        
    def get_nodes(self, modeltype, model_stream, **nodemaker_options):
        tree = etree.parse(model_stream)
        root = tree.getroot()
        
        nodetree = {"name" : "CERIF", "children" : []}
        for child in root.getchildren():
            if not isinstance(child.tag, str):
                continue
            
            if not child.tag.startswith("{urn:xmlns:org:eurocris:cerif-1.6-2}"):
                continue
            
            nodetree["children"].append(self._do_nodes(child))
        
        print nodetree
        return nodetree
    
    def _do_nodes(self, node):
        name = node.tag[36:]
        rawname = name[2:] if name.startswith("cf") else name
        nodetree = {"name" : name, "children" : []}
        classes = []
        relations = []
        properties = []
        
        for child in node.getchildren():
            if not isinstance(child.tag, str):
                continue
            
            if not child.tag.startswith("{urn:xmlns:org:eurocris:cerif-1.6-2}"):
                continue

            if self._is_class(rawname, child):
                classes.append(self._do_class(child))
            elif self._is_rel(rawname, child):
                relations.append(self._do_relations(child))
            else:
                properties.append(self._do_properties(child))
        
        if len(classes) > 0:
            nodetree["children"].append({"name" : "CLASSES", "children" : classes})
        if len(relations) > 0:
            nodetree["children"].append({"name" : "RELATIONS", "children" : relations})
        if len(properties) > 0:
            nodetree["children"].append({"name" : "PROPERTIES", "children" : properties})
            
        return nodetree
    
    def _do_class(self, node):
        class_id = node.find(self.NS + "cfClassId")
        class_scheme = node.find(self.NS + "cfClassSchemeId")
        return {"name" : class_scheme.text, "children" : [{"name" : class_id.text}]}
        # return {"name" : "Scheme: " + class_scheme.text + ", ID: " + class_id.text}
    
    def _do_relations(self, node):
        class_id = node.find(self.NS + "cfClassId")
        class_scheme = node.find(self.NS + "cfClassSchemeId")
        obj = {"name" : class_scheme.text + "/" + class_id.text, "children" : []}
        for child in node:
            if not isinstance(child.tag, str):
                continue
            
            if not child.tag.startswith("{urn:xmlns:org:eurocris:cerif-1.6-2}"):
                continue
                
            if (not child.tag.endswith("cfClassId") and 
                    not child.tag.endswith("cfClassSchemeId")):
                obj["children"].append({"name" : child.tag[36:]})
                # return {"name" : child.tag[36:] + ": " + obj.get("name", "")}
        return obj
                
    def _do_properties(self, node):
        if len(node.getchildren()) > 0:
            return self._do_nodes(node)
        return {"name" : node.tag[36:], "children" : [{"name" : str(node.text)}]}
        # return {"name" : node.tag[36:] + ": " + str(node.text)} # FIXME: need to deal with attributes somewhere
    
    def _is_class(self, rawname, child):
        return child.tag.endswith("cf" + rawname + "_Class")
    
    def _is_rel(self, rawname, child):
        p1 = "cf" + rawname + "_"
        p2 = "_" + rawname
        return p1 in child.tag or p2 in child.tag
    
    

class OutputsModel(plugin.Generator):
    NS = "{urn:xmlns:org:eurocris:cerif-1.6-2}"

    def supports(self, modeltype, **generator_options):
        return modeltype == "ukriss_outputs"
    
    def generate(self, modeltype, model_stream, **generator_options):
        tree = etree.parse(model_stream)
        root = tree.getroot()
        
        fieldsets = []
        fs = plugin.FieldSet()
        rp = root.find(self.NS + "cfResPubl")
        
        # date published
        rpd = rp.find(self.NS + "cfResPublDate")
        if rpd is not None:
            fs.field("cfResPublDate", "date", rpd.text, "published_date")
        
        # volume number
        vol = rp.find(self.NS + "cfVol")
        if vol is not None:
            fs.field("cfVol", "integer", vol.text, "volume")
        
        # edition
        ed = rp.find(self.NS + "cfEdition")
        if ed is not None:
            fs.field("cfEdition", "edition", ed.text, "edition")
        
        # issue number
        issue = rp.find(self.NS + "cfIssue")
        if issue is not None:
            fs.field("cfIssue", "number", issue.text, "issue")
        
        # start page
        sp = rp.find(self.NS + "cfStartPage")
        if sp is not None:
            fs.field("cfStartPage", "integer", sp.text, "start_page")
        
        # end page
        ep = rp.find(self.NS + "cfEndPage")
        if ep is not None:
            fs.field("cfEndPage", "integer", ep.text, "end_page")
        
        # FIXME: we could do some validation here? total = end - start
        # total pages
        tp = rp.find(self.NS + "cfTotalPages")
        if tp is not None:
            fs.field("cfTotalPages", "integer", tp.text, "page_count")
        
        uri = rp.find(self.NS + "cfURI")
        if uri is not None:
            fs.field("cfURI", "uri", uri.text, "uri")
            
        title = rp.find(self.NS + "cfTitle")
        if title is not None:
            fs.field("cfTitle", "title", title.text, "title")
            
            lang = title.get("cfLangCode")
            if lang is not None:
                titlelang = plugin.FieldSet()
                titlelang.field("cfTitle/cfLangCode", "iso-639-1", lang, "language")
                fieldsets.append(titlelang)
        
        abstract = rp.find(self.NS + "cfAbstr")
        if abstract is not None:
            fs.field("cfAbstr", "abstract", abstract.text, "abstract")
            
            lang = abstract.get("cfLangCode")
            if lang is not None:
                abslang = plugin.FieldSet()
                abslang.field("cfAbstract/cfLangCode", "iso-639-1", lang, "language")
                fieldsets.append(abslang)
        
        classes = rp.findall(self.NS + "cfResPubl_Class")
        for c in classes:
            scheme = c.find(self.NS + "cfClassSchemeId")
            cid = c.find(self.NS + "cfClassId")
            
            if scheme.text == "iso:639-1":
                fs.field("cfResPubl_Class/cfClassSchemeId/iso:639-1", "iso-639-1", cid.text, "language")
            
            if scheme.text == "rcuk:oa-policy-embargo-periods-scheme-uuid":
                fs.field("cfResPubl_Class/rcuk:oa-policy-embargo-periods-scheme-uuid", "embargo", cid.text, "embargo")
            
        prp = rp.findall(self.NS + "cfProj_ResPubl")
        for p in prp:
            scheme = p.find(self.NS + "cfClassSchemeId")
            cid = p.find(self.NS + "cfClassId")
            pid = p.find(self.NS + "cfProjId")
            
            if (scheme.text == "ukriss:grant-reference-scheme-uuid" and 
                    cid.text == "grant-uuid" and pid is not None):
                fs.field("cfProj_ResPubl/cfClassSchemeId/grant", "grant_number", pid.text, "grant_number")
        
        fids = rp.findall(self.NS + "cfFedId")
        for fid in fids:
            fed = fid.find(self.NS + "cfFedId")
            fcl = fid.find(self.NS + "cfFedId_Class")
            scheme = fcl.find(self.NS + "cfClassSchemeId")
            cid = fcl.find(self.NS + "cfClassId")
            
            if (scheme.text == "ukriss:identifier-types-scheme-uuid" and 
                    cid.text == "handle-uuid"):
                fs.field("cfFedId/handle", "handle", fed.text, "publication_identifier")
            
            if (scheme.text == "ukriss:identifier-types-scheme-uuid" and 
                    cid.text == "isbn-uuid"):
                fs.field("cfFedId/isbn", "isbn", fed.text, "isbn")
        
            if (scheme.text == "ukriss:identifier-types-scheme-uuid" and 
                    cid.text == "issn-uuid"):
                fs.field("cfFedId/issn", "issn", fed.text, "issn")
        
            if (scheme.text == "ukriss:identifier-types-scheme-uuid" and 
                    cid.text == "pubmed-uuid"):
                fs.field("cfFedId/pubmed", "pmid", fed.text, "publication_identifier")
            
            if (scheme.text == "ukriss:identifier-types-scheme-uuid" and 
                    cid.text == "doi-uuid"):
                fs.field("cfFedId/doi", "doi", fed.text, "publication_identifier")
        
        fieldsets.append(fs)
        return fieldsets








































