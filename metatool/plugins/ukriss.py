try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

from lxml import etree

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








































