try:
    import metatool.plugin as plugin
except ImportError:
    import plugin as plugin

try:
    from metatool.plugins import acat
except ImportError:
    from plugins import acat

try:
    from metatool.plugins import text
except ImportError:
    from plugins import text

try:
    from metatool.plugins import number
except ImportError:
    from plugins import number

try:
    from metatool.plugins import dates
except ImportError:
    from plugins import dates

import re, requests, json
from lxml import etree

class ISSN(plugin.Validator):
    rx_1 = "\d{4}-\d{3}[0-9X]"
    rx_2 = "\d{7}[0-9X]"
    
    def supports(self, datatype, *args, **kwargs):
        return datatype.lower() == "issn"
    
    def validate(self, datatype, issn, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation - layout, hyphenation, checksum, etc.
        self._format_validate(issn, r)
        
        # then go and check the ACAT
        return self.validate_realism(datatype, issn, validation_response=r)
    
    def validate_format(self, datatype, issn, *args, **validation_options):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        oid = self._format_validate(issn, r)
        return r
    
    def validate_realism(self, datatype, issn, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        journals = acat.search(issn=[issn])
        if journals is None or len(journals) == 0:
            r.warn("Unable to locate ISSN in the ACAT - this does not mean it is not real, but it reduces the chances")
        else:
            r.info("ISSN was found in the ACAT")
            r.data = acat.ACATWrapper(journals)
        return r
    
    def _format_validate(self, issn, r):
        # attempt format validation based on regular expressions first
        m = re.match(self.rx_1, issn)
        if m is None:
            m = re.match(self.rx_2, issn)
            if m is None:
                r.error("issn does not pass format check.  Should be in the form nnnn-nnnn")
                return r # we can't do any further validation
            else:
                r.warn("issn consists of 8 valid digits, but is not hyphenated; recommended form for issns in nnnn-nnnn")
                r.correction(self._correct(issn))
        
        # if we get to here our issn at least consists of the right digits.  Now we can 
        # calculate the checksum ourselves
        checksum = self._checksum(issn)
        if checksum != issn[-1]:
            r.error("issn checksum digit does not match the calculated checksum")
        return r
    
    def _correct(self, issn):
        return issn[:4] + "-" + issn[4:]
    
    def _checksum(self, issn):
        digits = issn.replace("-", "")
        remainder = sum([int(b) * (8 - int(a)) for a, b in enumerate(digits) if a < 7]) % 11
        
        if remainder == 0:
            return "0"
        check = 11 - remainder
        if check == 10:
            return "X"
        return str(check)

# ISSN Compare is a Comparator implementation, which looks for exact equivalence
class ISSNCompare(text.Equivalent):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["issn"]

# Journal compare is a Comparator implementation, which uses Levenshtein distance to 
# decide on a match
class JournalCompare(text.LevenshteinDistance):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["journal", "journal_name", "journal_title"]

class JournalName(plugin.Validator):
    def supports(self, datatype, *args, **kwargs):
        return datatype.lower() in ["journal", "journal_name", "journal_title"]

    def validate(self, datatype, journal, *args, **kwargs):
        r = plugin.ValidationResponse()
        if kwargs is None:
            kwargs = {}
        kwargs["validation_response"] = r
        
        # first do the format validation - layout, hyphenation, checksum, etc.
        self.validate_format(datatype, journal, *args, **kwargs)
        
        # if the format validate fails, we don't do the realisim validation
        if r.has_errors():
            return r
        
        # else go and check the ACAT
        return self.validate_realism(datatype, journal, *args, **kwargs)
    
    def validate_format(self, datatype, journal, *args, **validation_options):
        r = validation_options.get("validation_response", plugin.ValidationResponse())
        # just check that it is not the empty string?
        if journal == "":
            r.error("Journal string is the empty string")
        return r
    
    def validate_realism(self, datatype, journal, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        journals = acat.search(journal_title=[journal])
        if journals is None or len(journals) == 0:
            r.warn("Unable to locate Journal in the ACAT - this does not mean it is not real, but it reduces the chances")
        else:
            r.info("Journal was found in the ACAT")
            r.data = acat.ACATWrapper(journals)
        return r

class ISBN(plugin.Validator):
    rx_10 = "^\d{9}[0-9X]$"
    rx_13 = "^\d{12}[0-9X]$"

    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower == "isbn" or lower == "isbn10" or lower == "isbn13"
        
    def run(self, datatype, isbn, *args, **kwargs):
        r = plugin.ValidationResponse()
        return self.validate_format(datatype, isbn, validation_response=r)
    
    def validate(self, datatype, isbn, *args, **kwargs):
        r = plugin.ValidationResponse()
        return self.validate_format(datatype, isbn, validation_response=r)
    
    def validate_format(self, datatype, isbn, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
    
        # try to normalise out some of the isbn prefixes        
        norm = isbn.replace(" ", "").replace("-", "").lower()
        print norm
        if norm.startswith("isbn"):
            norm = norm[len("isbn"):]
        
        if norm.startswith(":"):
            norm = norm[1:]
        
        m10 = re.match(self.rx_10, norm)
        m13 = None
        if m10 is None:
            m13 = re.match(self.rx_13, norm)
            if m13 is None:
                r.error("isbn does not pass format check.  Should be a 10 or 13 digit number (with optional hyphenation), possibly prefixed with 'ISBN:'")
                return r
        
        checksum = None
        if m10 is not None:
            checksum = self._checksum10(norm)
        elif m13 is not None:
            checksum = self._checksum13(norm)
            
        if checksum != norm[-1]:
            r.error("isbn checksum does not match calculated checksum (" + str(checksum) + ")")
        else:
            if m10 is not None:
                r.info("ISBN is a legal 10-digit ISBN")
            elif m13 is not None:
                r.info("ISBN is a legal 13-digit ISBN")
        return r
    
    def _checksum10(self, isbn10):
        remainder = 11 - (sum([int(n) * (10 - idx) for idx, n in enumerate(isbn10) if idx < 9]) % 11)
        print "CHECKSUM 10", remainder
        
        if remainder == 0:
            return "0"
        check = 11 - remainder
        if check == 10:
            return "X"
        return str(check)
        
    def _checksum13(self, isbn13):
        remainder = 10 - (sum([int(n) * (1 if idx % 2 == 0 else 3) for idx, n in enumerate(isbn13) if idx < 12]) % 10)
        print "CHECKSUM 13", remainder
        return str(remainder)


class DOI(plugin.Validator):
    rx = "^((http:\/\/){0,1}dx.doi.org/|(http:\/\/){0,1}hdl.handle.net\/|doi:|info:doi:){0,1}(?P<id>10\\..+\/.+)"
    
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["doi"]
    
    def validate(self, datatype, doi, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation
        kwargs["validation_response"] = r
        self.validate_format(datatype, doi, *args, **kwargs)
        
        # then go and check the ACAT
        return self.validate_realism(datatype, doi, *args, **kwargs)
    
    def validate_format(self, datatype, doi, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        result = re.match(self.rx, doi)
        if result is None:
            r.error("DOI does not match the form of a DOI")
        else:
            r.info("DOI meets the format criteria")
        return r
    
    def validate_realism(self, datatype, doi, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        # make the doi into something we can de-reference at dx.doi.org
        result = re.match(self.rx, doi)
        if result is None:
            # no need for a message, format check picks this up
            return
        
        # create the canonical version
        deref = "http://dx.doi.org/" + result.group(4)
        
        # make a request to the doi.org server, to see if there is a record
        # and if there is one, get back a json version of the data in this csl format
        try:
            resp = requests.get(deref, headers={"accept" : "application/vnd.citationstyles.csl+json"}, timeout=3)
        except requests.exceptions.Timeout:
            r.warn("Attempted to verify DOI against crossref, but request to server timed out")
            return r
                
        if resp.status_code >= 400 and resp.status_code < 500:
            r.error("Unable to locate DOI in the doi.org redirect service, so even if this DOI is real, it is broken")
        elif resp.status_code >= 500:
            r.warn("doi.org redirect threw a server error on retrieving this DOI - it's probably not your fault")
        else:
            r.info("doi.org successfully responded to this DOI")
            r.data = CrossRefCSL(resp.text)
        
        return r

class DOICompare(plugin.Comparator):
    rx = "^((http:\/\/){0,1}dx.doi.org/|(http:\/\/){0,1}hdl.handle.net\/|doi:|info:doi:){0,1}(?P<id>10\\..+\/.+)"
    
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["doi", "publication_identifier"]
    
    def compare(self, datatype, original, comparison, **comparison_options):
        r = plugin.ComparisonResponse()
        
        # first get the raw doi out of the original
        original_result = re.match(self.rx, original)
        if original_result is None:
            # could not match doi to regex, so match failed
            r.success = False
            return r
        
        # now get the raw doi out of the comparison
        comparison_result = re.match(self.rx, comparison)
        if comparison_result is None:
            # could not match doi to regex, so match failed
            r.success = False
            return r
        
        # compare the two operational parts of the DOI
        original_doi = original_result.group(4)
        compare_doi = comparison_result.group(4)
        
        # operational doi portions should be the same
        r.success = original_doi == compare_doi
        return r

class URICompare(text.Equivalent):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["uri", "url", "publication_identifier"]

class PageNumberCompare(number.IntegersEqual):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["page_count", "start_page", "end_page"]

class TitleAbstractCompare(text.LevenshteinDistance):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["title", "abstract"]

class PublishedDateCompare(dates.DatesSimilar):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["issued_date", "published_date"]

class VolumeCompare(number.IntegersEqual):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["volume"]

class IssueCompare(number.IntegersEqual):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["issue"]

class CrossRefCSL(plugin.DataWrapper):

    """
    Example document:
    
    {u'DOI': u'10.1016/S0550-3213(01)00405-9',
     u'URL': u'http://dx.doi.org/10.1016/S0550-3213(01)00405-9',
     u'author': [{u'family': u'McGuire', u'given': u'Scott'},
      {u'family': u'Catterall', u'given': u'Simon'},
      {u'family': u'Bowick', u'given': u'Mark'},
      {u'family': u'Warner', u'given': u'Simeon'}],
     u'container-title': u'Nuclear Physics B',
     u'editor': [],
     u'issue': u'3',
     u'issued': {u'date-parts': [[2001, 11]]},
     u'page': u'467-493',
     u'publisher': u'Elsevier ',
     u'title': u'The Ising model on a dynamically triangulated disk with a boundary magnetic field',
     u'type': u'article-journal',
     u'volume': u'614'}
    """

    type_map = {
        "doi" : ["DOI"],
        "publication_identifier" : ["DOI", "URL"],
        "uri" : ["URL"],
        "url" : ["URL"],
        "author" : ["author"],
        "journal_title" : ["container-title"],
        "journal_name" : ["container-title"],
        "journal" : ["container-title"],
        "issue" : ["issue"],
        "issued_date" : ["issued"],
        "published_date" : ["issued"],
        "start_page" : ["page"],
        "page_range" : ["page"],
        "pages" : ["page"],
        "page_count" : ["page"],
        "end_page" : ["page"],
        "publisher" : ["publisher"],
        "title" : ["title"],
        "volume" : ["volume"]
    }

    def __init__(self, raw):
        self.raw = json.loads(raw)

    def source_name(self):
        return "crossref"

    def get(self, datatype):
        got = []
        lower = datatype.lower()
        
        mapped = self.type_map.get(lower, [])
        for m in mapped:
            if m in ["author", "issued", "page"]:
                if m == "author":
                    authors = self._get_authors()
                    got += authors
                elif m == "issued":
                    issued = self._get_issued()
                    got += issued
                elif m == "page":
                    page = self._get_page(datatype)
                    got.append(page)
            else:
                vals = self.raw.get(m)
                if isinstance(vals, list):
                    got += vals
                else:
                    got.append(vals)
        
        if len(got) == 0:
            return None
        return list(set(got))
    
    def _get_authors(self):
        names = []
        authors = self.raw.get("author", [])
        for a in authors:
            name = a.get("given", "") + " " + a.get("family", "")
            name = name.strip()
            if name != "":
                names.append(name)
        return names
    
    def _get_issued(self):
        dates = []
        parts = self.raw.get("issued", {}).get("date-parts", [])
        for part in parts:
            if len(part) == 1:
                dates.append(str(part[0]))
            elif len(part) == 2:
                dates.append(str(part[0]) + "-" + str(part[1]))
            elif len(part) == 3:
                dates.append(str(part[0]) + "-" + str(part[1]) + "-" + str(part[2]))
        return dates
        
    def _get_page(self, datatype):
        r = self.raw.get("page")
        if datatype in ["pages", "page_range"]:
            return r
        bits = r.split("-")
        if len(bits) != 2:
            return None
        if datatype == "start_page":
            return bits[0]
        elif datatype == "end_page":
            return bits[1]
        elif datatype == "page_count":
            try:
                return int(bits[1]) - int(bits[2])
            except:
                return None

class URIValidator(plugin.Validator):
    rx = "^([a-z0-9+.-]+):(?://(?:((?:[a-z0-9-._~!$&'()*+,;=:]|%[0-9A-F]{2})*)@)?((?:[a-z0-9-._~!$&'()*+,;=]|%[0-9A-F]{2})*)(?::(\d*))?(/(?:[a-z0-9-._~!$&'()*+,;=:@/]|%[0-9A-F]{2})*)?|(/?(?:[a-z0-9-._~!$&'()*+,;=:@]|%[0-9A-F]{2})+(?:[a-z0-9-._~!$&'()*+,;=:@/]|%[0-9A-F]{2})*)?)(?:\?((?:[a-z0-9-._~!$&'()*+,;=:/?@]|%[0-9A-F]{2})*))?(?:#((?:[a-z0-9-._~!$&'()*+,;=:/?@]|%[0-9A-F]{2})*))?$"

    """
    Taken from: http://snipplr.com/view/6889/regular-expressions-for-uri-validationparsing/
    /*composed as follows:
	    ^
	    ([a-z0-9+.-]+):							#scheme
	    (?:
		    //							#it has an authority:
		    (?:((?:[a-z0-9-._~!$&'()*+,;=:]|%[0-9A-F]{2})*)@)?	#userinfo
		    ((?:[a-z0-9-._~!$&'()*+,;=]|%[0-9A-F]{2})*)		#host
		    (?::(\d*))?						#port
		    (/(?:[a-z0-9-._~!$&'()*+,;=:@/]|%[0-9A-F]{2})*)?	#path
		    |
									    #it doesn't have an authority:
		    (/?(?:[a-z0-9-._~!$&'()*+,;=:@]|%[0-9A-F]{2})+(?:[a-z0-9-._~!$&'()*+,;=:@/]|%[0-9A-F]{2})*)?	#path
	    )
	    (?:
		    \?((?:[a-z0-9-._~!$&'()*+,;=:/?@]|%[0-9A-F]{2})*)	#query string
	    )?
	    (?:
		    #((?:[a-z0-9-._~!$&'()*+,;=:/?@]|%[0-9A-F]{2})*)	#fragment
	    )?
	    $
    */
    """

    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["uri", "url"]
    
    def validate(self, datatype, uri, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation
        kwargs["validation_response"] = r
        self.validate_format(datatype, uri, *args, **kwargs)
        
        # then go and check the ACAT
        return self.validate_realism(datatype, uri, *args, **kwargs)
    
    def validate_format(self, datatype, uri, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        result = re.match(self.rx, uri)
        if result is None:
            r.error("URI does not match the form of a URI")
        else:
            r.info("URI meets the format criteria")
        return r
    
    def validate_realism(self, datatype, uri, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        # if the uri is a url, we can try to dereference it
        if uri.startswith("http"): # will cover https
            try:
                resp = requests.get(uri, timeout=3)
            except requests.exceptions.Timeout:
                r.warn("Attempted to verify HTTP URI, but request to server timed out")
                return r
            if resp.status_code >= 400 and resp.status_code < 500:
                r.error("HTTP URI does not resolve to a valid resource")
            if resp.status_code >= 500:
                r.warn("HTTP URI resolved to a server which suffered an internal error on attempting to retrieve it - it's probably not your fault")
            else:
                r.info("HTTP URI was successfully resolved - although this doesn't guarantee that it points to the document you think it points to!")
            
        return r

class PMID(plugin.Validator):
    rx = "^[\d]{1,8}$"
    nrx = "([\d]{1,8})"
    
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["pmid", "pubmed"]
    
    def validate(self, datatype, pmid, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation
        kwargs["validation_response"] = r
        self.validate_format(datatype, pmid, *args, **kwargs)
        
        # then go and check Entrez
        return self.validate_realism(datatype, pmid, *args, **kwargs)
    
    def validate_format(self, datatype, pmid, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        # first check for and strip any odd prefix
        lp = pmid.lower()
        if lp.startswith("pmc"):
            lp = lp[3:]
        if lp.startswith("pmid"):
            lp = lp[4:]
        if lp.startswith(":"):
            lp = lp[1:]
        
        if lp != pmid.lower():
            r.warn("Your PMID has a prefix; there is no standardisation on PMID expressions, so this is legal, but it might confuse some systems/users")
            r.correction(lp)
        
        # now check the format of the main pmid
        result = re.match(self.rx, lp)
        if result is None:
            r.error("PMID does not match the form of a PMID (should be a number of up to 8 digits)")
        else:
            r.info("PMID meets the format criteria")
        
        return r
    
    def validate_realism(self, datatype, pmid, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        result = re.search(self.nrx, pmid)
        xml_url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=" + result.group(0) + "&retmode=xml"
        
        # now dereference it and find out the target of the (chain of) 303(s)
        try:
            response = requests.get(xml_url, timeout=3)
        except requests.exceptions.Timeout:
            r.warn("Attempted to verify PMID against Entrez, but request to server timed out")
            return r
        if response.status_code >= 400 and response.status_code < 500:
            r.error("Could not locate this PMID in the Entrez authority database - it is very very likely to be wrong")
            return r
        if response.status_code >= 500:
            r.warn("Entrez suffered a server error when attempting to retrieve this PMID - it's probably not your fault")
            return r
        
        try:
            xml = etree.fromstring(response.text.encode("utf-8"))
            r.info("Successfully resolved this PMID to a record in the Entrez database")
            r.data = EntrezWrapper(xml)
            return r
        except:
            r.warn("XML retrieved from Entrez for this PMID could not be parsed")
            return r

class EntrezWrapper(plugin.DataWrapper):

    type_map = {
        "doi" : ["/PubmedArticleSet/PubmedArticle/PubmedData/ArticleIdList/ArticleId[@IdType='doi']"],
        "issn" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Journal/ISSN", 
                    "/PubmedArticleSet/PubmedArticle/MedlineCitation/MedlineJournalInfo/ISSNLinking"],
        "issue" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Journal/JournalIssue/Issue"],
        "published_date" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Journal/JournalIssue/PubDate"],
        "journal_title" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Journal/Title", 
                            "/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Journal/ISOAbbreviation"],
        "title" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/ArticleTitle"],
        "start_page" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Pagination/MedlinePgn"],
        "page_range" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Pagination/MedlinePgn"],
        "pages" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Pagination/MedlinePgn"],
        "page_count" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Pagination/MedlinePgn"],
        "end_page" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Pagination/MedlinePgn"],
        "author" : [], # placeholder - the example is not very good
        "language" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Language"],
        "iso-639-2" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/Language"],
        "publication_type" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/Article/PublicationTypeList/PublicationType"],
        "abstract" : ["/PubmedArticleSet/PubmedArticle/MedlineCitation/OtherAbstract/AbstractText"],
        "publication_identifier" : ["/PubmedArticleSet/PubmedArticle/PubmedData/ArticleIdList/ArticleId"],
        "pmid" : ["/PubmedArticleSet/PubmedArticle/PubmedData/ArticleIdList/ArticleId[@IdType='pubmed']"],
    }
    
    month_map = {
        "Jan" : "01", "Feb" : "02", "Mar" : "03", "Apr" : "04", "May" : "05", "Jun" : "06",
        "Jul" : "07", "Aug" : "08", "Sep" : "09", "Oct" : "10", "Nov" : "11", "Dec" : "12"
    }

    def __init__(self, xml):
        self.xml = xml

    def source_name(self):
        return "entrez"

    def get(self, datatype):
        got = []
        lower = datatype.lower()
        
        # special treatment for:
        # published_date, start_page, page_range, pages, page_count, end_page
        xps = self.type_map.get(lower, [])
        for xp in xps:
            if lower in ["published_date"]:
                dates = self._getPublishedDate()
                got += dates
            elif lower in ["start_page", "page_range", "pages", "page_count", "end_page"]:
                page = self._getPage(lower)
                got += page
            else:
                els = self.xml.xpath(xp)
                print xp, els
                if els is None or len(els) == 0:
                    continue
                for e in els:
                    text = e.text.strip()
                    got.append(text)
        
        if len(got) == 0:
            return None
        return list(set(got))
    
    def _getPublishedDate(self):
        dates = []
        xps = self.type_map.get("published_date", [])
        for xp in xps:
            els = self.xml.xpath(xp)
            if els is None or len(els) == 0:
                continue
            for e in els:
                year = e.find("Year")
                month = e.find("Month")
                day = e.find("Day")
                date = ""
                if year is not None:
                    date += year.text
                    if month is not None:
                        date += "-" + self.month_map.get(month.text, month.text)
                        if day is not None:
                            date += "-" + day.text
                    dates.append(date)
        return dates
    
    def _getPage(self, datatype):
        pages = []
        xps = self.type_map.get(datatype, [])
        for xp in xps:
            els = self.xml.xpath(xp)
            for e in els:
                if datatype in ["page_range", "pages"]:
                    pages.append(e.text)
                elif datatype == "start_page":
                    bits = e.text.split("-")
                    pages.append(bits[0])
                elif datatype == "end_page":
                    bits = e.text.split("-")
                    if len(bits) == 2:
                        pages.append(bits[1])
                elif datatype == "page_count":
                    bits = e.text.split("-")
                    if len(bits) == 2:
                        try:
                            count = int(bits[1]) - int(bits[0])
                            pages.append(count) 
                        except:
                            pass
        return pages

"""

xp = "/PubmedArticleSet/PubmedArticle/PubmedData/ArticleIdList/ArticleId[@IdType='doi']"

<PubmedArticleSet>
    <PubmedArticle>
        <MedlineCitation Owner="PIP" Status="MEDLINE">
            <PMID Version="1">12345678</PMID>
            <DateCreated>
                <Year>1995</Year>
                <Month>01</Month>
                <Day>04</Day>
            </DateCreated>
            <DateCompleted>
                <Year>1995</Year>
                <Month>01</Month>
                <Day>04</Day>
            </DateCompleted>
            <DateRevised>
                <Year>2002</Year>
                <Month>10</Month>
                <Day>04</Day>
            </DateRevised>
            <Article PubModel="Print">
                <Journal>
                    <ISSN IssnType="Print">0916-0582</ISSN>
                    <JournalIssue CitedMedium="Print">
                        <Issue>40</Issue>
                        <PubDate>
                            <Year>1994</Year>
                            <Month>Jun</Month>
                        </PubDate>
                    </JournalIssue>
                    <Title>Integration (Tokyo, Japan)</Title>
                    <ISOAbbreviation>Integration</ISOAbbreviation>
                </Journal>
                <ArticleTitle>
                    Denpasar Declaration on Population and Development.
                </ArticleTitle>
                <Pagination>
                    <MedlinePgn>27-9</MedlinePgn>
                </Pagination>
                <AuthorList CompleteYN="Y">
                    <Author ValidYN="Y">
                        <CollectiveName>
                            Ministerial Meeting on Population of the Non-Aligned Movement (1993: Bali)
                        </CollectiveName>
                    </Author>
                </AuthorList>
                <Language>eng</Language>
                <PublicationTypeList>
                    <PublicationType>Journal Article</PublicationType>
                </PublicationTypeList>
            </Article>
            <MedlineJournalInfo>
                <Country>JAPAN</Country>
                <MedlineTA>Integration</MedlineTA>
                <NlmUniqueID>9001944</NlmUniqueID>
                <ISSNLinking>0916-0582</ISSNLinking>
            </MedlineJournalInfo>
            <CitationSubset>J</CitationSubset>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName MajorTopicYN="Y">Developing Countries</DescriptorName>
                </MeshHeading>
                <MeshHeading>
                    <DescriptorName MajorTopicYN="Y">Economics</DescriptorName>
                </MeshHeading>
                <MeshHeading>
                    <DescriptorName MajorTopicYN="Y">International Cooperation</DescriptorName>
                </MeshHeading>
                <MeshHeading>
                    <DescriptorName MajorTopicYN="Y">Public Policy</DescriptorName>
                </MeshHeading>
            </MeshHeadingList>
            <OtherID Source="PIP">099526</OtherID>
            <OtherID Source="POP">00232894</OtherID>
            <OtherAbstract Language="eng" Type="PIP">
                <AbstractText>
                Ministers from the countries of the Non-Aligned Movement (NAM) got together at the Ministerial Meeting on Population in Bali, Indonesia, November 11-13, 1993, to develop the Denpasar Declaration on Population and Development. The declaration was made with full consideration and acceptance of the sovereignty of individual nations and the decisions on population of the heads of states and governments at the tenth conference of Non-Aligned Countries at Jakarta, 1992, and the results of the meeting of the Standing Ministerial Committee for Economic Cooperation of the NAM in Bali 1993. The ministers recognize that population should be an integral part of the development process, population policies and development efforts should be designed to improve the quality of life for present generations without compromising the ability of future generations to meet their own needs, and the alleviation of poverty is essential to the dignity of humankind and fundamental to the achievement of sustainable development. They further reaffirm the existence of humans as the center of concern for sustainable development, the right to an adequate standard of living for all, gender equality, greater multilateral cooperation for development, and that all developing countries should participate effectively at the International Conference on Population and Development to be convened in Cairo in 1994. The text of the declaration is included.
                </AbstractText>
            </OtherAbstract>
            <KeywordList Owner="PIP">
                <Keyword MajorTopicYN="Y">Developing Countries</Keyword>
                <Keyword MajorTopicYN="Y">Development Policy</Keyword>
                <Keyword MajorTopicYN="Y">Economic Development</Keyword>
                <Keyword MajorTopicYN="N">Economic Factors</Keyword>
                <Keyword MajorTopicYN="Y">International Cooperation</Keyword>
                <Keyword MajorTopicYN="N">Policy</Keyword>
                <Keyword MajorTopicYN="Y">Population Policy</Keyword>
                <Keyword MajorTopicYN="N">Social Policy</Keyword>
            </KeywordList>
            <GeneralNote Owner="PIP">TJ: INTEGRATION</GeneralNote>
        </MedlineCitation>
        <PubmedData>
            <History>
                <PubMedPubDate PubStatus="pubmed">
                    <Year>1994</Year>
                    <Month>6</Month>
                    <Day>1</Day>
                    <Hour>0</Hour>
                    <Minute>0</Minute>
                </PubMedPubDate>
                <PubMedPubDate PubStatus="medline">
                    <Year>2002</Year>
                    <Month>10</Month>
                    <Day>9</Day>
                    <Hour>4</Hour>
                    <Minute>0</Minute>
                </PubMedPubDate>
                <PubMedPubDate PubStatus="entrez">
                    <Year>1994</Year>
                    <Month>6</Month>
                    <Day>1</Day>
                    <Hour>0</Hour>
                    <Minute>0</Minute>
                </PubMedPubDate>
            </History>
            <PublicationStatus>ppublish</PublicationStatus>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345678</ArticleId>
            </ArticleIdList>
        </PubmedData>
    </PubmedArticle>
</PubmedArticleSet>

"""

class HandleValidator(plugin.Validator):
    rx = "^((http:\/\/){0,1}hdl.handle.net\/|hdl:){0,1}(\d+[\\.]{0,1}.*\/.+)"
    
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["handle", "hdl"]
    
    def validate(self, datatype, handle, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # first do the format validation
        kwargs["validation_response"] = r
        self.validate_format(datatype, handle, *args, **kwargs)
        
        # then go and check the handle server
        return self.validate_realism(datatype, handle, *args, **kwargs)
    
    def validate_format(self, datatype, handle, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        result = re.match(self.rx, handle)
        if result is None:
            r.error("Handle does not match the form of a Handle")
        else:
            r.info("Handle meets the format criteria")
        
        if not handle.startswith("http://hdl.handle.net") and not handle.startswith("hdl:") and not handle.startswith("hdl.handle.net"):
            r.warn("Your handle does not start with a prefix, which may make it ambiguous in some contexts")
            r.correction("http://hdl.handle.net/" + result.group(3))
        
        if handle.startswith("hdl.handle.net"):
            r.warn("Your handle does not start with the http protocol prefix")
            r.correction("http://" + handle)
        
        return r
    
    def validate_realism(self, datatype, handle, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        # make the handle into something we can de-reference at dx.doi.org
        result = re.match(self.rx, handle)
        if result is None:
            # no need for a message, format check picks this up
            return
        
        # create the canonical version
        deref = "http://hdl.handle.net/" + result.group(3)
        
        # make a request to the handle server, to see if there is a record
        # and if there is one, get back a json version of the data in this csl format
        try:
            resp = requests.get(deref, timeout=3)
        except requests.exceptions.Timeout:
            r.warn("Attempted to verify Handle against handle.net, but request to server timed out")
            return r
                
        if resp.status_code >= 400 and resp.status_code < 500:
            r.error("Unable to locate Handle in the handle.net redirect service, so even if this Handle is real, it is broken")
        elif resp.status_code >= 500:
            r.warn("handle.net redirect threw a server error on retrieving this Handle - it's probably not your fault")
        else:
            r.info("handle.net successfully responded to this Handle")
            r.data = HandleRecord(resp.url)
        
        return r

class HandleRecord(plugin.DataWrapper):
    def __init__(self, url):
        self.url = url

    def source_name(self):
        return "handle"

    def get(self, datatype):
        got = []
        lower = datatype.lower()
        
        if datatype in ["publication_identifier", "url", "uri"]:
            return [self.url]
        else:
            return None

class LanguageComparison(plugin.Comparator):
    def supports(self, datatype, **comparison_options):
        lower = datatype.lower()
        return lower in ["language", "iso-639-1", "iso-639-2"]
        
    def compare(self, datatype, original, comparison, **comparison_options):
        r = plugin.ComparisonResponse()
        
        # whatever they are, if they are the same they are the same
        if original == comparison:
            r.success = True
            return r
        
        # if they are not equivalent, get them into iso-639-2 (the superset)
        # and compare them
        orig6392 = original
        if original in ISO6391.codes:
            orig6392 = ISO6391.codes.get(original).get("iso6392")
        elif original in Language.langs:
            orig6392 = Language.langs.get(original).get("iso6392")
        
        comp6392 = comparison
        if comparison in ISO6391.codes:
            comp6392 = ISO6391.codes.get(comparison).get("iso6392")
        elif comparison in Language.langs:
            comp6392 = Language.langs.get(comparison).get("iso6392")
        
        r.success = orig6392 == comp6392
        return r
    
class ISO6391(plugin.Validator):

    codes = {
        "aa" : {'iso6392': u'aar', 'T': u'', 'name': u'Afar'},
        "ab" : {'iso6392': u'abk', 'T': u'', 'name': u'Abkhazian'},
        "ae" : {'iso6392': u'ave', 'T': u'', 'name': u'Avestan'},
        "af" : {'iso6392': u'afr', 'T': u'', 'name': u'Afrikaans'},
        "ak" : {'iso6392': u'aka', 'T': u'', 'name': u'Akan'},
        "am" : {'iso6392': u'amh', 'T': u'', 'name': u'Amharic'},
        "an" : {'iso6392': u'arg', 'T': u'', 'name': u'Aragonese'},
        "ar" : {'iso6392': u'ara', 'T': u'', 'name': u'Arabic'},
        "as" : {'iso6392': u'asm', 'T': u'', 'name': u'Assamese'},
        "av" : {'iso6392': u'ava', 'T': u'', 'name': u'Avaric'},
        "ay" : {'iso6392': u'aym', 'T': u'', 'name': u'Aymara'},
        "az" : {'iso6392': u'aze', 'T': u'', 'name': u'Azerbaijani'},
        "ba" : {'iso6392': u'bak', 'T': u'', 'name': u'Bashkir'},
        "be" : {'iso6392': u'bel', 'T': u'', 'name': u'Belarusian'},
        "bg" : {'iso6392': u'bul', 'T': u'', 'name': u'Bulgarian'},
        "bh" : {'iso6392': u'bih', 'T': u'', 'name': u'Bihari languages'},
        "bi" : {'iso6392': u'bis', 'T': u'', 'name': u'Bislama'},
        "bm" : {'iso6392': u'bam', 'T': u'', 'name': u'Bambara'},
        "bn" : {'iso6392': u'ben', 'T': u'', 'name': u'Bengali'},
        "bo" : {'iso6392': u'tib', 'T': u'bod', 'name': u'Tibetan'},
        "br" : {'iso6392': u'bre', 'T': u'', 'name': u'Breton'},
        "bs" : {'iso6392': u'bos', 'T': u'', 'name': u'Bosnian'},
        "ca" : {'iso6392': u'cat', 'T': u'', 'name': u'Catalan; Valencian'},
        "ce" : {'iso6392': u'che', 'T': u'', 'name': u'Chechen'},
        "ch" : {'iso6392': u'cha', 'T': u'', 'name': u'Chamorro'},
        "co" : {'iso6392': u'cos', 'T': u'', 'name': u'Corsican'},
        "cr" : {'iso6392': u'cre', 'T': u'', 'name': u'Cree'},
        "cs" : {'iso6392': u'cze', 'T': u'ces', 'name': u'Czech'},
        "cu" : {'iso6392': u'chu', 'T': u'', 'name': u'Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic'},
        "cv" : {'iso6392': u'chv', 'T': u'', 'name': u'Chuvash'},
        "cy" : {'iso6392': u'wel', 'T': u'cym', 'name': u'Welsh'},
        "da" : {'iso6392': u'dan', 'T': u'', 'name': u'Danish'},
        "de" : {'iso6392': u'ger', 'T': u'deu', 'name': u'German'},
        "dv" : {'iso6392': u'div', 'T': u'', 'name': u'Divehi; Dhivehi; Maldivian'},
        "dz" : {'iso6392': u'dzo', 'T': u'', 'name': u'Dzongkha'},
        "ee" : {'iso6392': u'ewe', 'T': u'', 'name': u'Ewe'},
        "el" : {'iso6392': u'gre', 'T': u'ell', 'name': u'Greek, Modern (1453-)'},
        "en" : {'iso6392': u'eng', 'T': u'', 'name': u'English'},
        "eo" : {'iso6392': u'epo', 'T': u'', 'name': u'Esperanto'},
        "es" : {'iso6392': u'spa', 'T': u'', 'name': u'Spanish; Castilian'},
        "et" : {'iso6392': u'est', 'T': u'', 'name': u'Estonian'},
        "eu" : {'iso6392': u'baq', 'T': u'eus', 'name': u'Basque'},
        "fa" : {'iso6392': u'per', 'T': u'fas', 'name': u'Persian'},
        "ff" : {'iso6392': u'ful', 'T': u'', 'name': u'Fulah'},
        "fi" : {'iso6392': u'fin', 'T': u'', 'name': u'Finnish'},
        "fj" : {'iso6392': u'fij', 'T': u'', 'name': u'Fijian'},
        "fo" : {'iso6392': u'fao', 'T': u'', 'name': u'Faroese'},
        "fr" : {'iso6392': u'fre', 'T': u'fra', 'name': u'French'},
        "fy" : {'iso6392': u'fry', 'T': u'', 'name': u'Western Frisian'},
        "ga" : {'iso6392': u'gle', 'T': u'', 'name': u'Irish'},
        "gd" : {'iso6392': u'gla', 'T': u'', 'name': u'Gaelic; Scottish Gaelic'},
        "gl" : {'iso6392': u'glg', 'T': u'', 'name': u'Galician'},
        "gn" : {'iso6392': u'grn', 'T': u'', 'name': u'Guarani'},
        "gu" : {'iso6392': u'guj', 'T': u'', 'name': u'Gujarati'},
        "gv" : {'iso6392': u'glv', 'T': u'', 'name': u'Manx'},
        "ha" : {'iso6392': u'hau', 'T': u'', 'name': u'Hausa'},
        "he" : {'iso6392': u'heb', 'T': u'', 'name': u'Hebrew'},
        "hi" : {'iso6392': u'hin', 'T': u'', 'name': u'Hindi'},
        "ho" : {'iso6392': u'hmo', 'T': u'', 'name': u'Hiri Motu'},
        "hr" : {'iso6392': u'hrv', 'T': u'', 'name': u'Croatian'},
        "ht" : {'iso6392': u'hat', 'T': u'', 'name': u'Haitian; Haitian Creole'},
        "hu" : {'iso6392': u'hun', 'T': u'', 'name': u'Hungarian'},
        "hy" : {'iso6392': u'arm', 'T': u'hye', 'name': u'Armenian'},
        "hz" : {'iso6392': u'her', 'T': u'', 'name': u'Herero'},
        "ia" : {'iso6392': u'ina', 'T': u'', 'name': u'Interlingua (International Auxiliary Language Association)'},
        "id" : {'iso6392': u'ind', 'T': u'', 'name': u'Indonesian'},
        "ie" : {'iso6392': u'ile', 'T': u'', 'name': u'Interlingue; Occidental'},
        "ig" : {'iso6392': u'ibo', 'T': u'', 'name': u'Igbo'},
        "ii" : {'iso6392': u'iii', 'T': u'', 'name': u'Sichuan Yi; Nuosu'},
        "ik" : {'iso6392': u'ipk', 'T': u'', 'name': u'Inupiaq'},
        "io" : {'iso6392': u'ido', 'T': u'', 'name': u'Ido'},
        "is" : {'iso6392': u'ice', 'T': u'isl', 'name': u'Icelandic'},
        "it" : {'iso6392': u'ita', 'T': u'', 'name': u'Italian'},
        "iu" : {'iso6392': u'iku', 'T': u'', 'name': u'Inuktitut'},
        "ja" : {'iso6392': u'jpn', 'T': u'', 'name': u'Japanese'},
        "jv" : {'iso6392': u'jav', 'T': u'', 'name': u'Javanese'},
        "ka" : {'iso6392': u'geo', 'T': u'kat', 'name': u'Georgian'},
        "kg" : {'iso6392': u'kon', 'T': u'', 'name': u'Kongo'},
        "ki" : {'iso6392': u'kik', 'T': u'', 'name': u'Kikuyu; Gikuyu'},
        "kj" : {'iso6392': u'kua', 'T': u'', 'name': u'Kuanyama; Kwanyama'},
        "kk" : {'iso6392': u'kaz', 'T': u'', 'name': u'Kazakh'},
        "kl" : {'iso6392': u'kal', 'T': u'', 'name': u'Kalaallisut; Greenlandic'},
        "km" : {'iso6392': u'khm', 'T': u'', 'name': u'Central Khmer'},
        "kn" : {'iso6392': u'kan', 'T': u'', 'name': u'Kannada'},
        "ko" : {'iso6392': u'kor', 'T': u'', 'name': u'Korean'},
        "kr" : {'iso6392': u'kau', 'T': u'', 'name': u'Kanuri'},
        "ks" : {'iso6392': u'kas', 'T': u'', 'name': u'Kashmiri'},
        "ku" : {'iso6392': u'kur', 'T': u'', 'name': u'Kurdish'},
        "kv" : {'iso6392': u'kom', 'T': u'', 'name': u'Komi'},
        "kw" : {'iso6392': u'cor', 'T': u'', 'name': u'Cornish'},
        "ky" : {'iso6392': u'kir', 'T': u'', 'name': u'Kirghiz; Kyrgyz'},
        "la" : {'iso6392': u'lat', 'T': u'', 'name': u'Latin'},
        "lb" : {'iso6392': u'ltz', 'T': u'', 'name': u'Luxembourgish; Letzeburgesch'},
        "lg" : {'iso6392': u'lug', 'T': u'', 'name': u'Ganda'},
        "li" : {'iso6392': u'lim', 'T': u'', 'name': u'Limburgan; Limburger; Limburgish'},
        "ln" : {'iso6392': u'lin', 'T': u'', 'name': u'Lingala'},
        "lo" : {'iso6392': u'lao', 'T': u'', 'name': u'Lao'},
        "lt" : {'iso6392': u'lit', 'T': u'', 'name': u'Lithuanian'},
        "lu" : {'iso6392': u'lub', 'T': u'', 'name': u'Luba-Katanga'},
        "lv" : {'iso6392': u'lav', 'T': u'', 'name': u'Latvian'},
        "mg" : {'iso6392': u'mlg', 'T': u'', 'name': u'Malagasy'},
        "mh" : {'iso6392': u'mah', 'T': u'', 'name': u'Marshallese'},
        "mi" : {'iso6392': u'mao', 'T': u'mri', 'name': u'Maori'},
        "mk" : {'iso6392': u'mac', 'T': u'mkd', 'name': u'Macedonian'},
        "ml" : {'iso6392': u'mal', 'T': u'', 'name': u'Malayalam'},
        "mn" : {'iso6392': u'mon', 'T': u'', 'name': u'Mongolian'},
        "mr" : {'iso6392': u'mar', 'T': u'', 'name': u'Marathi'},
        "ms" : {'iso6392': u'may', 'T': u'msa', 'name': u'Malay'},
        "mt" : {'iso6392': u'mlt', 'T': u'', 'name': u'Maltese'},
        "my" : {'iso6392': u'bur', 'T': u'mya', 'name': u'Burmese'},
        "na" : {'iso6392': u'nau', 'T': u'', 'name': u'Nauru'},
        "nb" : {'iso6392': u'nob', 'T': u'', 'name': u'Bokm\xe5l, Norwegian; Norwegian Bokm\xe5l'},
        "nd" : {'iso6392': u'nde', 'T': u'', 'name': u'Ndebele, North; North Ndebele'},
        "ne" : {'iso6392': u'nep', 'T': u'', 'name': u'Nepali'},
        "ng" : {'iso6392': u'ndo', 'T': u'', 'name': u'Ndonga'},
        "nl" : {'iso6392': u'dut', 'T': u'nld', 'name': u'Dutch; Flemish'},
        "nn" : {'iso6392': u'nno', 'T': u'', 'name': u'Norwegian Nynorsk; Nynorsk, Norwegian'},
        "no" : {'iso6392': u'nor', 'T': u'', 'name': u'Norwegian'},
        "nr" : {'iso6392': u'nbl', 'T': u'', 'name': u'Ndebele, South; South Ndebele'},
        "nv" : {'iso6392': u'nav', 'T': u'', 'name': u'Navajo; Navaho'},
        "ny" : {'iso6392': u'nya', 'T': u'', 'name': u'Chichewa; Chewa; Nyanja'},
        "oc" : {'iso6392': u'oci', 'T': u'', 'name': u'Occitan (post 1500); Proven\xe7al'},
        "oj" : {'iso6392': u'oji', 'T': u'', 'name': u'Ojibwa'},
        "om" : {'iso6392': u'orm', 'T': u'', 'name': u'Oromo'},
        "or" : {'iso6392': u'ori', 'T': u'', 'name': u'Oriya'},
        "os" : {'iso6392': u'oss', 'T': u'', 'name': u'Ossetian; Ossetic'},
        "pa" : {'iso6392': u'pan', 'T': u'', 'name': u'Panjabi; Punjabi'},
        "pi" : {'iso6392': u'pli', 'T': u'', 'name': u'Pali'},
        "pl" : {'iso6392': u'pol', 'T': u'', 'name': u'Polish'},
        "ps" : {'iso6392': u'pus', 'T': u'', 'name': u'Pushto; Pashto'},
        "pt" : {'iso6392': u'por', 'T': u'', 'name': u'Portuguese'},
        "qu" : {'iso6392': u'que', 'T': u'', 'name': u'Quechua'},
        "rm" : {'iso6392': u'roh', 'T': u'', 'name': u'Romansh'},
        "rn" : {'iso6392': u'run', 'T': u'', 'name': u'Rundi'},
        "ro" : {'iso6392': u'rum', 'T': u'ron', 'name': u'Romanian; Moldavian; Moldovan'},
        "ru" : {'iso6392': u'rus', 'T': u'', 'name': u'Russian'},
        "rw" : {'iso6392': u'kin', 'T': u'', 'name': u'Kinyarwanda'},
        "sa" : {'iso6392': u'san', 'T': u'', 'name': u'Sanskrit'},
        "sc" : {'iso6392': u'srd', 'T': u'', 'name': u'Sardinian'},
        "sd" : {'iso6392': u'snd', 'T': u'', 'name': u'Sindhi'},
        "se" : {'iso6392': u'sme', 'T': u'', 'name': u'Northern Sami'},
        "sg" : {'iso6392': u'sag', 'T': u'', 'name': u'Sango'},
        "si" : {'iso6392': u'sin', 'T': u'', 'name': u'Sinhala; Sinhalese'},
        "sk" : {'iso6392': u'slo', 'T': u'slk', 'name': u'Slovak'},
        "sl" : {'iso6392': u'slv', 'T': u'', 'name': u'Slovenian'},
        "sm" : {'iso6392': u'smo', 'T': u'', 'name': u'Samoan'},
        "sn" : {'iso6392': u'sna', 'T': u'', 'name': u'Shona'},
        "so" : {'iso6392': u'som', 'T': u'', 'name': u'Somali'},
        "sq" : {'iso6392': u'alb', 'T': u'sqi', 'name': u'Albanian'},
        "sr" : {'iso6392': u'srp', 'T': u'', 'name': u'Serbian'},
        "ss" : {'iso6392': u'ssw', 'T': u'', 'name': u'Swati'},
        "st" : {'iso6392': u'sot', 'T': u'', 'name': u'Sotho, Southern'},
        "su" : {'iso6392': u'sun', 'T': u'', 'name': u'Sundanese'},
        "sv" : {'iso6392': u'swe', 'T': u'', 'name': u'Swedish'},
        "sw" : {'iso6392': u'swa', 'T': u'', 'name': u'Swahili'},
        "ta" : {'iso6392': u'tam', 'T': u'', 'name': u'Tamil'},
        "te" : {'iso6392': u'tel', 'T': u'', 'name': u'Telugu'},
        "tg" : {'iso6392': u'tgk', 'T': u'', 'name': u'Tajik'},
        "th" : {'iso6392': u'tha', 'T': u'', 'name': u'Thai'},
        "ti" : {'iso6392': u'tir', 'T': u'', 'name': u'Tigrinya'},
        "tk" : {'iso6392': u'tuk', 'T': u'', 'name': u'Turkmen'},
        "tl" : {'iso6392': u'tgl', 'T': u'', 'name': u'Tagalog'},
        "tn" : {'iso6392': u'tsn', 'T': u'', 'name': u'Tswana'},
        "to" : {'iso6392': u'ton', 'T': u'', 'name': u'Tonga (Tonga Islands)'},
        "tr" : {'iso6392': u'tur', 'T': u'', 'name': u'Turkish'},
        "ts" : {'iso6392': u'tso', 'T': u'', 'name': u'Tsonga'},
        "tt" : {'iso6392': u'tat', 'T': u'', 'name': u'Tatar'},
        "tw" : {'iso6392': u'twi', 'T': u'', 'name': u'Twi'},
        "ty" : {'iso6392': u'tah', 'T': u'', 'name': u'Tahitian'},
        "ug" : {'iso6392': u'uig', 'T': u'', 'name': u'Uighur; Uyghur'},
        "uk" : {'iso6392': u'ukr', 'T': u'', 'name': u'Ukrainian'},
        "ur" : {'iso6392': u'urd', 'T': u'', 'name': u'Urdu'},
        "uz" : {'iso6392': u'uzb', 'T': u'', 'name': u'Uzbek'},
        "ve" : {'iso6392': u'ven', 'T': u'', 'name': u'Venda'},
        "vi" : {'iso6392': u'vie', 'T': u'', 'name': u'Vietnamese'},
        "vo" : {'iso6392': u'vol', 'T': u'', 'name': u'Volap\xfck'},
        "wa" : {'iso6392': u'wln', 'T': u'', 'name': u'Walloon'},
        "wo" : {'iso6392': u'wol', 'T': u'', 'name': u'Wolof'},
        "xh" : {'iso6392': u'xho', 'T': u'', 'name': u'Xhosa'},
        "yi" : {'iso6392': u'yid', 'T': u'', 'name': u'Yiddish'},
        "yo" : {'iso6392': u'yor', 'T': u'', 'name': u'Yoruba'},
        "za" : {'iso6392': u'zha', 'T': u'', 'name': u'Zhuang; Chuang'},
        "zh" : {'iso6392': u'chi', 'T': u'zho', 'name': u'Chinese'},
        "zu" : {'iso6392': u'zul', 'T': u'', 'name': u'Zulu'}
    }
    
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["iso-639-1", "language"]
    
    def validate(self, datatype, lang, *args, **kwargs):
        r = plugin.ValidationResponse()
        return self.validate_format(datatype, lang, validation_response=r)
    
    def validate_format(self, datatype, lang, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        if lang not in self.codes.keys():
            if datatype == "iso-639-1":
                r.error("Language code does not appear in the iso-639-1 list of valid codes")
            elif datatype == "language":
                r.warn("Language code does not appear in the iso-639-1 list of valid codes")
        else:
            info = self.codes.get(lang)
            r.info("Equivalent iso-639-2 tag is " + info.get("iso6392"))
            r.alternative(info.get("iso6392"))
            r.info("Language code refers to " + info.get("name"))
            r.alternative(info.get("name"))
        
        return r

class ISO6392(plugin.Validator):
    
    codes = {
        "aar" : {'iso6391': u'aa', 'T': u'', 'name': u'Afar'},
        "abk" : {'iso6391': u'ab', 'T': u'', 'name': u'Abkhazian'},
        "ace" : {'iso6391': u'', 'T': u'', 'name': u'Achinese'},
        "ach" : {'iso6391': u'', 'T': u'', 'name': u'Acoli'},
        "ada" : {'iso6391': u'', 'T': u'', 'name': u'Adangme'},
        "ady" : {'iso6391': u'', 'T': u'', 'name': u'Adyghe; Adygei'},
        "afa" : {'iso6391': u'', 'T': u'', 'name': u'Afro-Asiatic languages'},
        "afh" : {'iso6391': u'', 'T': u'', 'name': u'Afrihili'},
        "afr" : {'iso6391': u'af', 'T': u'', 'name': u'Afrikaans'},
        "ain" : {'iso6391': u'', 'T': u'', 'name': u'Ainu'},
        "aka" : {'iso6391': u'ak', 'T': u'', 'name': u'Akan'},
        "akk" : {'iso6391': u'', 'T': u'', 'name': u'Akkadian'},
        "alb" : {'iso6391': u'sq', 'T': u'sqi', 'name': u'Albanian'},
        "ale" : {'iso6391': u'', 'T': u'', 'name': u'Aleut'},
        "alg" : {'iso6391': u'', 'T': u'', 'name': u'Algonquian languages'},
        "alt" : {'iso6391': u'', 'T': u'', 'name': u'Southern Altai'},
        "amh" : {'iso6391': u'am', 'T': u'', 'name': u'Amharic'},
        "ang" : {'iso6391': u'', 'T': u'', 'name': u'English, Old (ca.450-1100)'},
        "anp" : {'iso6391': u'', 'T': u'', 'name': u'Angika'},
        "apa" : {'iso6391': u'', 'T': u'', 'name': u'Apache languages'},
        "ara" : {'iso6391': u'ar', 'T': u'', 'name': u'Arabic'},
        "arc" : {'iso6391': u'', 'T': u'', 'name': u'Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE)'},
        "arg" : {'iso6391': u'an', 'T': u'', 'name': u'Aragonese'},
        "arm" : {'iso6391': u'hy', 'T': u'hye', 'name': u'Armenian'},
        "arn" : {'iso6391': u'', 'T': u'', 'name': u'Mapudungun; Mapuche'},
        "arp" : {'iso6391': u'', 'T': u'', 'name': u'Arapaho'},
        "art" : {'iso6391': u'', 'T': u'', 'name': u'Artificial languages'},
        "arw" : {'iso6391': u'', 'T': u'', 'name': u'Arawak'},
        "asm" : {'iso6391': u'as', 'T': u'', 'name': u'Assamese'},
        "ast" : {'iso6391': u'', 'T': u'', 'name': u'Asturian; Bable; Leonese; Asturleonese'},
        "ath" : {'iso6391': u'', 'T': u'', 'name': u'Athapascan languages'},
        "aus" : {'iso6391': u'', 'T': u'', 'name': u'Australian languages'},
        "ava" : {'iso6391': u'av', 'T': u'', 'name': u'Avaric'},
        "ave" : {'iso6391': u'ae', 'T': u'', 'name': u'Avestan'},
        "awa" : {'iso6391': u'', 'T': u'', 'name': u'Awadhi'},
        "aym" : {'iso6391': u'ay', 'T': u'', 'name': u'Aymara'},
        "aze" : {'iso6391': u'az', 'T': u'', 'name': u'Azerbaijani'},
        "bad" : {'iso6391': u'', 'T': u'', 'name': u'Banda languages'},
        "bai" : {'iso6391': u'', 'T': u'', 'name': u'Bamileke languages'},
        "bak" : {'iso6391': u'ba', 'T': u'', 'name': u'Bashkir'},
        "bal" : {'iso6391': u'', 'T': u'', 'name': u'Baluchi'},
        "bam" : {'iso6391': u'bm', 'T': u'', 'name': u'Bambara'},
        "ban" : {'iso6391': u'', 'T': u'', 'name': u'Balinese'},
        "baq" : {'iso6391': u'eu', 'T': u'eus', 'name': u'Basque'},
        "bas" : {'iso6391': u'', 'T': u'', 'name': u'Basa'},
        "bat" : {'iso6391': u'', 'T': u'', 'name': u'Baltic languages'},
        "bej" : {'iso6391': u'', 'T': u'', 'name': u'Beja; Bedawiyet'},
        "bel" : {'iso6391': u'be', 'T': u'', 'name': u'Belarusian'},
        "bem" : {'iso6391': u'', 'T': u'', 'name': u'Bemba'},
        "ben" : {'iso6391': u'bn', 'T': u'', 'name': u'Bengali'},
        "ber" : {'iso6391': u'', 'T': u'', 'name': u'Berber languages'},
        "bho" : {'iso6391': u'', 'T': u'', 'name': u'Bhojpuri'},
        "bih" : {'iso6391': u'bh', 'T': u'', 'name': u'Bihari languages'},
        "bik" : {'iso6391': u'', 'T': u'', 'name': u'Bikol'},
        "bin" : {'iso6391': u'', 'T': u'', 'name': u'Bini; Edo'},
        "bis" : {'iso6391': u'bi', 'T': u'', 'name': u'Bislama'},
        "bla" : {'iso6391': u'', 'T': u'', 'name': u'Siksika'},
        "bnt" : {'iso6391': u'', 'T': u'', 'name': u'Bantu (Other)'},
        "bos" : {'iso6391': u'bs', 'T': u'', 'name': u'Bosnian'},
        "bra" : {'iso6391': u'', 'T': u'', 'name': u'Braj'},
        "bre" : {'iso6391': u'br', 'T': u'', 'name': u'Breton'},
        "btk" : {'iso6391': u'', 'T': u'', 'name': u'Batak languages'},
        "bua" : {'iso6391': u'', 'T': u'', 'name': u'Buriat'},
        "bug" : {'iso6391': u'', 'T': u'', 'name': u'Buginese'},
        "bul" : {'iso6391': u'bg', 'T': u'', 'name': u'Bulgarian'},
        "bur" : {'iso6391': u'my', 'T': u'mya', 'name': u'Burmese'},
        "byn" : {'iso6391': u'', 'T': u'', 'name': u'Blin; Bilin'},
        "cad" : {'iso6391': u'', 'T': u'', 'name': u'Caddo'},
        "cai" : {'iso6391': u'', 'T': u'', 'name': u'Central American Indian languages'},
        "car" : {'iso6391': u'', 'T': u'', 'name': u'Galibi Carib'},
        "cat" : {'iso6391': u'ca', 'T': u'', 'name': u'Catalan; Valencian'},
        "cau" : {'iso6391': u'', 'T': u'', 'name': u'Caucasian languages'},
        "ceb" : {'iso6391': u'', 'T': u'', 'name': u'Cebuano'},
        "cel" : {'iso6391': u'', 'T': u'', 'name': u'Celtic languages'},
        "cha" : {'iso6391': u'ch', 'T': u'', 'name': u'Chamorro'},
        "chb" : {'iso6391': u'', 'T': u'', 'name': u'Chibcha'},
        "che" : {'iso6391': u'ce', 'T': u'', 'name': u'Chechen'},
        "chg" : {'iso6391': u'', 'T': u'', 'name': u'Chagatai'},
        "chi" : {'iso6391': u'zh', 'T': u'zho', 'name': u'Chinese'},
        "chk" : {'iso6391': u'', 'T': u'', 'name': u'Chuukese'},
        "chm" : {'iso6391': u'', 'T': u'', 'name': u'Mari'},
        "chn" : {'iso6391': u'', 'T': u'', 'name': u'Chinook jargon'},
        "cho" : {'iso6391': u'', 'T': u'', 'name': u'Choctaw'},
        "chp" : {'iso6391': u'', 'T': u'', 'name': u'Chipewyan; Dene Suline'},
        "chr" : {'iso6391': u'', 'T': u'', 'name': u'Cherokee'},
        "chu" : {'iso6391': u'cu', 'T': u'', 'name': u'Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic'},
        "chv" : {'iso6391': u'cv', 'T': u'', 'name': u'Chuvash'},
        "chy" : {'iso6391': u'', 'T': u'', 'name': u'Cheyenne'},
        "cmc" : {'iso6391': u'', 'T': u'', 'name': u'Chamic languages'},
        "cop" : {'iso6391': u'', 'T': u'', 'name': u'Coptic'},
        "cor" : {'iso6391': u'kw', 'T': u'', 'name': u'Cornish'},
        "cos" : {'iso6391': u'co', 'T': u'', 'name': u'Corsican'},
        "cpe" : {'iso6391': u'', 'T': u'', 'name': u'Creoles and pidgins, English based'},
        "cpf" : {'iso6391': u'', 'T': u'', 'name': u'Creoles and pidgins, French-based '},
        "cpp" : {'iso6391': u'', 'T': u'', 'name': u'Creoles and pidgins, Portuguese-based '},
        "cre" : {'iso6391': u'cr', 'T': u'', 'name': u'Cree'},
        "crh" : {'iso6391': u'', 'T': u'', 'name': u'Crimean Tatar; Crimean Turkish'},
        "crp" : {'iso6391': u'', 'T': u'', 'name': u'Creoles and pidgins '},
        "csb" : {'iso6391': u'', 'T': u'', 'name': u'Kashubian'},
        "cus" : {'iso6391': u'', 'T': u'', 'name': u'Cushitic languages'},
        "cze" : {'iso6391': u'cs', 'T': u'ces', 'name': u'Czech'},
        "dak" : {'iso6391': u'', 'T': u'', 'name': u'Dakota'},
        "dan" : {'iso6391': u'da', 'T': u'', 'name': u'Danish'},
        "dar" : {'iso6391': u'', 'T': u'', 'name': u'Dargwa'},
        "day" : {'iso6391': u'', 'T': u'', 'name': u'Land Dayak languages'},
        "del" : {'iso6391': u'', 'T': u'', 'name': u'Delaware'},
        "den" : {'iso6391': u'', 'T': u'', 'name': u'Slave (Athapascan)'},
        "dgr" : {'iso6391': u'', 'T': u'', 'name': u'Dogrib'},
        "din" : {'iso6391': u'', 'T': u'', 'name': u'Dinka'},
        "div" : {'iso6391': u'dv', 'T': u'', 'name': u'Divehi; Dhivehi; Maldivian'},
        "doi" : {'iso6391': u'', 'T': u'', 'name': u'Dogri'},
        "dra" : {'iso6391': u'', 'T': u'', 'name': u'Dravidian languages'},
        "dsb" : {'iso6391': u'', 'T': u'', 'name': u'Lower Sorbian'},
        "dua" : {'iso6391': u'', 'T': u'', 'name': u'Duala'},
        "dum" : {'iso6391': u'', 'T': u'', 'name': u'Dutch, Middle (ca.1050-1350)'},
        "dut" : {'iso6391': u'nl', 'T': u'nld', 'name': u'Dutch; Flemish'},
        "dyu" : {'iso6391': u'', 'T': u'', 'name': u'Dyula'},
        "dzo" : {'iso6391': u'dz', 'T': u'', 'name': u'Dzongkha'},
        "efi" : {'iso6391': u'', 'T': u'', 'name': u'Efik'},
        "egy" : {'iso6391': u'', 'T': u'', 'name': u'Egyptian (Ancient)'},
        "eka" : {'iso6391': u'', 'T': u'', 'name': u'Ekajuk'},
        "elx" : {'iso6391': u'', 'T': u'', 'name': u'Elamite'},
        "eng" : {'iso6391': u'en', 'T': u'', 'name': u'English'},
        "enm" : {'iso6391': u'', 'T': u'', 'name': u'English, Middle (1100-1500)'},
        "epo" : {'iso6391': u'eo', 'T': u'', 'name': u'Esperanto'},
        "est" : {'iso6391': u'et', 'T': u'', 'name': u'Estonian'},
        "ewe" : {'iso6391': u'ee', 'T': u'', 'name': u'Ewe'},
        "ewo" : {'iso6391': u'', 'T': u'', 'name': u'Ewondo'},
        "fan" : {'iso6391': u'', 'T': u'', 'name': u'Fang'},
        "fao" : {'iso6391': u'fo', 'T': u'', 'name': u'Faroese'},
        "fat" : {'iso6391': u'', 'T': u'', 'name': u'Fanti'},
        "fij" : {'iso6391': u'fj', 'T': u'', 'name': u'Fijian'},
        "fil" : {'iso6391': u'', 'T': u'', 'name': u'Filipino; Pilipino'},
        "fin" : {'iso6391': u'fi', 'T': u'', 'name': u'Finnish'},
        "fiu" : {'iso6391': u'', 'T': u'', 'name': u'Finno-Ugrian languages'},
        "fon" : {'iso6391': u'', 'T': u'', 'name': u'Fon'},
        "fre" : {'iso6391': u'fr', 'T': u'fra', 'name': u'French'},
        "frm" : {'iso6391': u'', 'T': u'', 'name': u'French, Middle (ca.1400-1600)'},
        "fro" : {'iso6391': u'', 'T': u'', 'name': u'French, Old (842-ca.1400)'},
        "frr" : {'iso6391': u'', 'T': u'', 'name': u'Northern Frisian'},
        "frs" : {'iso6391': u'', 'T': u'', 'name': u'Eastern Frisian'},
        "fry" : {'iso6391': u'fy', 'T': u'', 'name': u'Western Frisian'},
        "ful" : {'iso6391': u'ff', 'T': u'', 'name': u'Fulah'},
        "fur" : {'iso6391': u'', 'T': u'', 'name': u'Friulian'},
        "gaa" : {'iso6391': u'', 'T': u'', 'name': u'Ga'},
        "gay" : {'iso6391': u'', 'T': u'', 'name': u'Gayo'},
        "gba" : {'iso6391': u'', 'T': u'', 'name': u'Gbaya'},
        "gem" : {'iso6391': u'', 'T': u'', 'name': u'Germanic languages'},
        "geo" : {'iso6391': u'ka', 'T': u'kat', 'name': u'Georgian'},
        "ger" : {'iso6391': u'de', 'T': u'deu', 'name': u'German'},
        "gez" : {'iso6391': u'', 'T': u'', 'name': u'Geez'},
        "gil" : {'iso6391': u'', 'T': u'', 'name': u'Gilbertese'},
        "gla" : {'iso6391': u'gd', 'T': u'', 'name': u'Gaelic; Scottish Gaelic'},
        "gle" : {'iso6391': u'ga', 'T': u'', 'name': u'Irish'},
        "glg" : {'iso6391': u'gl', 'T': u'', 'name': u'Galician'},
        "glv" : {'iso6391': u'gv', 'T': u'', 'name': u'Manx'},
        "gmh" : {'iso6391': u'', 'T': u'', 'name': u'German, Middle High (ca.1050-1500)'},
        "goh" : {'iso6391': u'', 'T': u'', 'name': u'German, Old High (ca.750-1050)'},
        "gon" : {'iso6391': u'', 'T': u'', 'name': u'Gondi'},
        "gor" : {'iso6391': u'', 'T': u'', 'name': u'Gorontalo'},
        "got" : {'iso6391': u'', 'T': u'', 'name': u'Gothic'},
        "grb" : {'iso6391': u'', 'T': u'', 'name': u'Grebo'},
        "grc" : {'iso6391': u'', 'T': u'', 'name': u'Greek, Ancient (to 1453)'},
        "gre" : {'iso6391': u'el', 'T': u'ell', 'name': u'Greek, Modern (1453-)'},
        "grn" : {'iso6391': u'gn', 'T': u'', 'name': u'Guarani'},
        "gsw" : {'iso6391': u'', 'T': u'', 'name': u'Swiss German; Alemannic; Alsatian'},
        "guj" : {'iso6391': u'gu', 'T': u'', 'name': u'Gujarati'},
        "gwi" : {'iso6391': u'', 'T': u'', 'name': u"Gwich'in"},
        "hai" : {'iso6391': u'', 'T': u'', 'name': u'Haida'},
        "hat" : {'iso6391': u'ht', 'T': u'', 'name': u'Haitian; Haitian Creole'},
        "hau" : {'iso6391': u'ha', 'T': u'', 'name': u'Hausa'},
        "haw" : {'iso6391': u'', 'T': u'', 'name': u'Hawaiian'},
        "heb" : {'iso6391': u'he', 'T': u'', 'name': u'Hebrew'},
        "her" : {'iso6391': u'hz', 'T': u'', 'name': u'Herero'},
        "hil" : {'iso6391': u'', 'T': u'', 'name': u'Hiligaynon'},
        "him" : {'iso6391': u'', 'T': u'', 'name': u'Himachali languages; Western Pahari languages'},
        "hin" : {'iso6391': u'hi', 'T': u'', 'name': u'Hindi'},
        "hit" : {'iso6391': u'', 'T': u'', 'name': u'Hittite'},
        "hmn" : {'iso6391': u'', 'T': u'', 'name': u'Hmong; Mong'},
        "hmo" : {'iso6391': u'ho', 'T': u'', 'name': u'Hiri Motu'},
        "hrv" : {'iso6391': u'hr', 'T': u'', 'name': u'Croatian'},
        "hsb" : {'iso6391': u'', 'T': u'', 'name': u'Upper Sorbian'},
        "hun" : {'iso6391': u'hu', 'T': u'', 'name': u'Hungarian'},
        "hup" : {'iso6391': u'', 'T': u'', 'name': u'Hupa'},
        "iba" : {'iso6391': u'', 'T': u'', 'name': u'Iban'},
        "ibo" : {'iso6391': u'ig', 'T': u'', 'name': u'Igbo'},
        "ice" : {'iso6391': u'is', 'T': u'isl', 'name': u'Icelandic'},
        "ido" : {'iso6391': u'io', 'T': u'', 'name': u'Ido'},
        "iii" : {'iso6391': u'ii', 'T': u'', 'name': u'Sichuan Yi; Nuosu'},
        "ijo" : {'iso6391': u'', 'T': u'', 'name': u'Ijo languages'},
        "iku" : {'iso6391': u'iu', 'T': u'', 'name': u'Inuktitut'},
        "ile" : {'iso6391': u'ie', 'T': u'', 'name': u'Interlingue; Occidental'},
        "ilo" : {'iso6391': u'', 'T': u'', 'name': u'Iloko'},
        "ina" : {'iso6391': u'ia', 'T': u'', 'name': u'Interlingua (International Auxiliary Language Association)'},
        "inc" : {'iso6391': u'', 'T': u'', 'name': u'Indic languages'},
        "ind" : {'iso6391': u'id', 'T': u'', 'name': u'Indonesian'},
        "ine" : {'iso6391': u'', 'T': u'', 'name': u'Indo-European languages'},
        "inh" : {'iso6391': u'', 'T': u'', 'name': u'Ingush'},
        "ipk" : {'iso6391': u'ik', 'T': u'', 'name': u'Inupiaq'},
        "ira" : {'iso6391': u'', 'T': u'', 'name': u'Iranian languages'},
        "iro" : {'iso6391': u'', 'T': u'', 'name': u'Iroquoian languages'},
        "ita" : {'iso6391': u'it', 'T': u'', 'name': u'Italian'},
        "jav" : {'iso6391': u'jv', 'T': u'', 'name': u'Javanese'},
        "jbo" : {'iso6391': u'', 'T': u'', 'name': u'Lojban'},
        "jpn" : {'iso6391': u'ja', 'T': u'', 'name': u'Japanese'},
        "jpr" : {'iso6391': u'', 'T': u'', 'name': u'Judeo-Persian'},
        "jrb" : {'iso6391': u'', 'T': u'', 'name': u'Judeo-Arabic'},
        "kaa" : {'iso6391': u'', 'T': u'', 'name': u'Kara-Kalpak'},
        "kab" : {'iso6391': u'', 'T': u'', 'name': u'Kabyle'},
        "kac" : {'iso6391': u'', 'T': u'', 'name': u'Kachin; Jingpho'},
        "kal" : {'iso6391': u'kl', 'T': u'', 'name': u'Kalaallisut; Greenlandic'},
        "kam" : {'iso6391': u'', 'T': u'', 'name': u'Kamba'},
        "kan" : {'iso6391': u'kn', 'T': u'', 'name': u'Kannada'},
        "kar" : {'iso6391': u'', 'T': u'', 'name': u'Karen languages'},
        "kas" : {'iso6391': u'ks', 'T': u'', 'name': u'Kashmiri'},
        "kau" : {'iso6391': u'kr', 'T': u'', 'name': u'Kanuri'},
        "kaw" : {'iso6391': u'', 'T': u'', 'name': u'Kawi'},
        "kaz" : {'iso6391': u'kk', 'T': u'', 'name': u'Kazakh'},
        "kbd" : {'iso6391': u'', 'T': u'', 'name': u'Kabardian'},
        "kha" : {'iso6391': u'', 'T': u'', 'name': u'Khasi'},
        "khi" : {'iso6391': u'', 'T': u'', 'name': u'Khoisan languages'},
        "khm" : {'iso6391': u'km', 'T': u'', 'name': u'Central Khmer'},
        "kho" : {'iso6391': u'', 'T': u'', 'name': u'Khotanese; Sakan'},
        "kik" : {'iso6391': u'ki', 'T': u'', 'name': u'Kikuyu; Gikuyu'},
        "kin" : {'iso6391': u'rw', 'T': u'', 'name': u'Kinyarwanda'},
        "kir" : {'iso6391': u'ky', 'T': u'', 'name': u'Kirghiz; Kyrgyz'},
        "kmb" : {'iso6391': u'', 'T': u'', 'name': u'Kimbundu'},
        "kok" : {'iso6391': u'', 'T': u'', 'name': u'Konkani'},
        "kom" : {'iso6391': u'kv', 'T': u'', 'name': u'Komi'},
        "kon" : {'iso6391': u'kg', 'T': u'', 'name': u'Kongo'},
        "kor" : {'iso6391': u'ko', 'T': u'', 'name': u'Korean'},
        "kos" : {'iso6391': u'', 'T': u'', 'name': u'Kosraean'},
        "kpe" : {'iso6391': u'', 'T': u'', 'name': u'Kpelle'},
        "krc" : {'iso6391': u'', 'T': u'', 'name': u'Karachay-Balkar'},
        "krl" : {'iso6391': u'', 'T': u'', 'name': u'Karelian'},
        "kro" : {'iso6391': u'', 'T': u'', 'name': u'Kru languages'},
        "kru" : {'iso6391': u'', 'T': u'', 'name': u'Kurukh'},
        "kua" : {'iso6391': u'kj', 'T': u'', 'name': u'Kuanyama; Kwanyama'},
        "kum" : {'iso6391': u'', 'T': u'', 'name': u'Kumyk'},
        "kur" : {'iso6391': u'ku', 'T': u'', 'name': u'Kurdish'},
        "kut" : {'iso6391': u'', 'T': u'', 'name': u'Kutenai'},
        "lad" : {'iso6391': u'', 'T': u'', 'name': u'Ladino'},
        "lah" : {'iso6391': u'', 'T': u'', 'name': u'Lahnda'},
        "lam" : {'iso6391': u'', 'T': u'', 'name': u'Lamba'},
        "lao" : {'iso6391': u'lo', 'T': u'', 'name': u'Lao'},
        "lat" : {'iso6391': u'la', 'T': u'', 'name': u'Latin'},
        "lav" : {'iso6391': u'lv', 'T': u'', 'name': u'Latvian'},
        "lez" : {'iso6391': u'', 'T': u'', 'name': u'Lezghian'},
        "lim" : {'iso6391': u'li', 'T': u'', 'name': u'Limburgan; Limburger; Limburgish'},
        "lin" : {'iso6391': u'ln', 'T': u'', 'name': u'Lingala'},
        "lit" : {'iso6391': u'lt', 'T': u'', 'name': u'Lithuanian'},
        "lol" : {'iso6391': u'', 'T': u'', 'name': u'Mongo'},
        "loz" : {'iso6391': u'', 'T': u'', 'name': u'Lozi'},
        "ltz" : {'iso6391': u'lb', 'T': u'', 'name': u'Luxembourgish; Letzeburgesch'},
        "lua" : {'iso6391': u'', 'T': u'', 'name': u'Luba-Lulua'},
        "lub" : {'iso6391': u'lu', 'T': u'', 'name': u'Luba-Katanga'},
        "lug" : {'iso6391': u'lg', 'T': u'', 'name': u'Ganda'},
        "lui" : {'iso6391': u'', 'T': u'', 'name': u'Luiseno'},
        "lun" : {'iso6391': u'', 'T': u'', 'name': u'Lunda'},
        "luo" : {'iso6391': u'', 'T': u'', 'name': u'Luo (Kenya and Tanzania)'},
        "lus" : {'iso6391': u'', 'T': u'', 'name': u'Lushai'},
        "mac" : {'iso6391': u'mk', 'T': u'mkd', 'name': u'Macedonian'},
        "mad" : {'iso6391': u'', 'T': u'', 'name': u'Madurese'},
        "mag" : {'iso6391': u'', 'T': u'', 'name': u'Magahi'},
        "mah" : {'iso6391': u'mh', 'T': u'', 'name': u'Marshallese'},
        "mai" : {'iso6391': u'', 'T': u'', 'name': u'Maithili'},
        "mak" : {'iso6391': u'', 'T': u'', 'name': u'Makasar'},
        "mal" : {'iso6391': u'ml', 'T': u'', 'name': u'Malayalam'},
        "man" : {'iso6391': u'', 'T': u'', 'name': u'Mandingo'},
        "mao" : {'iso6391': u'mi', 'T': u'mri', 'name': u'Maori'},
        "map" : {'iso6391': u'', 'T': u'', 'name': u'Austronesian languages'},
        "mar" : {'iso6391': u'mr', 'T': u'', 'name': u'Marathi'},
        "mas" : {'iso6391': u'', 'T': u'', 'name': u'Masai'},
        "may" : {'iso6391': u'ms', 'T': u'msa', 'name': u'Malay'},
        "mdf" : {'iso6391': u'', 'T': u'', 'name': u'Moksha'},
        "mdr" : {'iso6391': u'', 'T': u'', 'name': u'Mandar'},
        "men" : {'iso6391': u'', 'T': u'', 'name': u'Mende'},
        "mga" : {'iso6391': u'', 'T': u'', 'name': u'Irish, Middle (900-1200)'},
        "mic" : {'iso6391': u'', 'T': u'', 'name': u"Mi'kmaq; Micmac"},
        "min" : {'iso6391': u'', 'T': u'', 'name': u'Minangkabau'},
        "mis" : {'iso6391': u'', 'T': u'', 'name': u'Uncoded languages'},
        "mkh" : {'iso6391': u'', 'T': u'', 'name': u'Mon-Khmer languages'},
        "mlg" : {'iso6391': u'mg', 'T': u'', 'name': u'Malagasy'},
        "mlt" : {'iso6391': u'mt', 'T': u'', 'name': u'Maltese'},
        "mnc" : {'iso6391': u'', 'T': u'', 'name': u'Manchu'},
        "mni" : {'iso6391': u'', 'T': u'', 'name': u'Manipuri'},
        "mno" : {'iso6391': u'', 'T': u'', 'name': u'Manobo languages'},
        "moh" : {'iso6391': u'', 'T': u'', 'name': u'Mohawk'},
        "mon" : {'iso6391': u'mn', 'T': u'', 'name': u'Mongolian'},
        "mos" : {'iso6391': u'', 'T': u'', 'name': u'Mossi'},
        "mul" : {'iso6391': u'', 'T': u'', 'name': u'Multiple languages'},
        "mun" : {'iso6391': u'', 'T': u'', 'name': u'Munda languages'},
        "mus" : {'iso6391': u'', 'T': u'', 'name': u'Creek'},
        "mwl" : {'iso6391': u'', 'T': u'', 'name': u'Mirandese'},
        "mwr" : {'iso6391': u'', 'T': u'', 'name': u'Marwari'},
        "myn" : {'iso6391': u'', 'T': u'', 'name': u'Mayan languages'},
        "myv" : {'iso6391': u'', 'T': u'', 'name': u'Erzya'},
        "nah" : {'iso6391': u'', 'T': u'', 'name': u'Nahuatl languages'},
        "nai" : {'iso6391': u'', 'T': u'', 'name': u'North American Indian languages'},
        "nap" : {'iso6391': u'', 'T': u'', 'name': u'Neapolitan'},
        "nau" : {'iso6391': u'na', 'T': u'', 'name': u'Nauru'},
        "nav" : {'iso6391': u'nv', 'T': u'', 'name': u'Navajo; Navaho'},
        "nbl" : {'iso6391': u'nr', 'T': u'', 'name': u'Ndebele, South; South Ndebele'},
        "nde" : {'iso6391': u'nd', 'T': u'', 'name': u'Ndebele, North; North Ndebele'},
        "ndo" : {'iso6391': u'ng', 'T': u'', 'name': u'Ndonga'},
        "nds" : {'iso6391': u'', 'T': u'', 'name': u'Low German; Low Saxon; German, Low; Saxon, Low'},
        "nep" : {'iso6391': u'ne', 'T': u'', 'name': u'Nepali'},
        "new" : {'iso6391': u'', 'T': u'', 'name': u'Nepal Bhasa; Newari'},
        "nia" : {'iso6391': u'', 'T': u'', 'name': u'Nias'},
        "nic" : {'iso6391': u'', 'T': u'', 'name': u'Niger-Kordofanian languages'},
        "niu" : {'iso6391': u'', 'T': u'', 'name': u'Niuean'},
        "nno" : {'iso6391': u'nn', 'T': u'', 'name': u'Norwegian Nynorsk; Nynorsk, Norwegian'},
        "nob" : {'iso6391': u'nb', 'T': u'', 'name': u'Bokm\xe5l, Norwegian; Norwegian Bokm\xe5l'},
        "nog" : {'iso6391': u'', 'T': u'', 'name': u'Nogai'},
        "non" : {'iso6391': u'', 'T': u'', 'name': u'Norse, Old'},
        "nor" : {'iso6391': u'no', 'T': u'', 'name': u'Norwegian'},
        "nqo" : {'iso6391': u'', 'T': u'', 'name': u"N'Ko"},
        "nso" : {'iso6391': u'', 'T': u'', 'name': u'Pedi; Sepedi; Northern Sotho'},
        "nub" : {'iso6391': u'', 'T': u'', 'name': u'Nubian languages'},
        "nwc" : {'iso6391': u'', 'T': u'', 'name': u'Classical Newari; Old Newari; Classical Nepal Bhasa'},
        "nya" : {'iso6391': u'ny', 'T': u'', 'name': u'Chichewa; Chewa; Nyanja'},
        "nym" : {'iso6391': u'', 'T': u'', 'name': u'Nyamwezi'},
        "nyn" : {'iso6391': u'', 'T': u'', 'name': u'Nyankole'},
        "nyo" : {'iso6391': u'', 'T': u'', 'name': u'Nyoro'},
        "nzi" : {'iso6391': u'', 'T': u'', 'name': u'Nzima'},
        "oci" : {'iso6391': u'oc', 'T': u'', 'name': u'Occitan (post 1500); Proven\xe7al'},
        "oji" : {'iso6391': u'oj', 'T': u'', 'name': u'Ojibwa'},
        "ori" : {'iso6391': u'or', 'T': u'', 'name': u'Oriya'},
        "orm" : {'iso6391': u'om', 'T': u'', 'name': u'Oromo'},
        "osa" : {'iso6391': u'', 'T': u'', 'name': u'Osage'},
        "oss" : {'iso6391': u'os', 'T': u'', 'name': u'Ossetian; Ossetic'},
        "ota" : {'iso6391': u'', 'T': u'', 'name': u'Turkish, Ottoman (1500-1928)'},
        "oto" : {'iso6391': u'', 'T': u'', 'name': u'Otomian languages'},
        "paa" : {'iso6391': u'', 'T': u'', 'name': u'Papuan languages'},
        "pag" : {'iso6391': u'', 'T': u'', 'name': u'Pangasinan'},
        "pal" : {'iso6391': u'', 'T': u'', 'name': u'Pahlavi'},
        "pam" : {'iso6391': u'', 'T': u'', 'name': u'Pampanga; Kapampangan'},
        "pan" : {'iso6391': u'pa', 'T': u'', 'name': u'Panjabi; Punjabi'},
        "pap" : {'iso6391': u'', 'T': u'', 'name': u'Papiamento'},
        "pau" : {'iso6391': u'', 'T': u'', 'name': u'Palauan'},
        "peo" : {'iso6391': u'', 'T': u'', 'name': u'Persian, Old (ca.600-400 B.C.)'},
        "per" : {'iso6391': u'fa', 'T': u'fas', 'name': u'Persian'},
        "phi" : {'iso6391': u'', 'T': u'', 'name': u'Philippine languages'},
        "phn" : {'iso6391': u'', 'T': u'', 'name': u'Phoenician'},
        "pli" : {'iso6391': u'pi', 'T': u'', 'name': u'Pali'},
        "pol" : {'iso6391': u'pl', 'T': u'', 'name': u'Polish'},
        "pon" : {'iso6391': u'', 'T': u'', 'name': u'Pohnpeian'},
        "por" : {'iso6391': u'pt', 'T': u'', 'name': u'Portuguese'},
        "pra" : {'iso6391': u'', 'T': u'', 'name': u'Prakrit languages'},
        "pro" : {'iso6391': u'', 'T': u'', 'name': u'Proven\xe7al, Old (to 1500)'},
        "pus" : {'iso6391': u'ps', 'T': u'', 'name': u'Pushto; Pashto'},
        "qaa-qtz" : {'iso6391': u'', 'T': u'', 'name': u'Reserved for local use'},
        "que" : {'iso6391': u'qu', 'T': u'', 'name': u'Quechua'},
        "raj" : {'iso6391': u'', 'T': u'', 'name': u'Rajasthani'},
        "rap" : {'iso6391': u'', 'T': u'', 'name': u'Rapanui'},
        "rar" : {'iso6391': u'', 'T': u'', 'name': u'Rarotongan; Cook Islands Maori'},
        "roa" : {'iso6391': u'', 'T': u'', 'name': u'Romance languages'},
        "roh" : {'iso6391': u'rm', 'T': u'', 'name': u'Romansh'},
        "rom" : {'iso6391': u'', 'T': u'', 'name': u'Romany'},
        "rum" : {'iso6391': u'ro', 'T': u'ron', 'name': u'Romanian; Moldavian; Moldovan'},
        "run" : {'iso6391': u'rn', 'T': u'', 'name': u'Rundi'},
        "rup" : {'iso6391': u'', 'T': u'', 'name': u'Aromanian; Arumanian; Macedo-Romanian'},
        "rus" : {'iso6391': u'ru', 'T': u'', 'name': u'Russian'},
        "sad" : {'iso6391': u'', 'T': u'', 'name': u'Sandawe'},
        "sag" : {'iso6391': u'sg', 'T': u'', 'name': u'Sango'},
        "sah" : {'iso6391': u'', 'T': u'', 'name': u'Yakut'},
        "sai" : {'iso6391': u'', 'T': u'', 'name': u'South American Indian (Other)'},
        "sal" : {'iso6391': u'', 'T': u'', 'name': u'Salishan languages'},
        "sam" : {'iso6391': u'', 'T': u'', 'name': u'Samaritan Aramaic'},
        "san" : {'iso6391': u'sa', 'T': u'', 'name': u'Sanskrit'},
        "sas" : {'iso6391': u'', 'T': u'', 'name': u'Sasak'},
        "sat" : {'iso6391': u'', 'T': u'', 'name': u'Santali'},
        "scn" : {'iso6391': u'', 'T': u'', 'name': u'Sicilian'},
        "sco" : {'iso6391': u'', 'T': u'', 'name': u'Scots'},
        "sel" : {'iso6391': u'', 'T': u'', 'name': u'Selkup'},
        "sem" : {'iso6391': u'', 'T': u'', 'name': u'Semitic languages'},
        "sga" : {'iso6391': u'', 'T': u'', 'name': u'Irish, Old (to 900)'},
        "sgn" : {'iso6391': u'', 'T': u'', 'name': u'Sign Languages'},
        "shn" : {'iso6391': u'', 'T': u'', 'name': u'Shan'},
        "sid" : {'iso6391': u'', 'T': u'', 'name': u'Sidamo'},
        "sin" : {'iso6391': u'si', 'T': u'', 'name': u'Sinhala; Sinhalese'},
        "sio" : {'iso6391': u'', 'T': u'', 'name': u'Siouan languages'},
        "sit" : {'iso6391': u'', 'T': u'', 'name': u'Sino-Tibetan languages'},
        "sla" : {'iso6391': u'', 'T': u'', 'name': u'Slavic languages'},
        "slo" : {'iso6391': u'sk', 'T': u'slk', 'name': u'Slovak'},
        "slv" : {'iso6391': u'sl', 'T': u'', 'name': u'Slovenian'},
        "sma" : {'iso6391': u'', 'T': u'', 'name': u'Southern Sami'},
        "sme" : {'iso6391': u'se', 'T': u'', 'name': u'Northern Sami'},
        "smi" : {'iso6391': u'', 'T': u'', 'name': u'Sami languages'},
        "smj" : {'iso6391': u'', 'T': u'', 'name': u'Lule Sami'},
        "smn" : {'iso6391': u'', 'T': u'', 'name': u'Inari Sami'},
        "smo" : {'iso6391': u'sm', 'T': u'', 'name': u'Samoan'},
        "sms" : {'iso6391': u'', 'T': u'', 'name': u'Skolt Sami'},
        "sna" : {'iso6391': u'sn', 'T': u'', 'name': u'Shona'},
        "snd" : {'iso6391': u'sd', 'T': u'', 'name': u'Sindhi'},
        "snk" : {'iso6391': u'', 'T': u'', 'name': u'Soninke'},
        "sog" : {'iso6391': u'', 'T': u'', 'name': u'Sogdian'},
        "som" : {'iso6391': u'so', 'T': u'', 'name': u'Somali'},
        "son" : {'iso6391': u'', 'T': u'', 'name': u'Songhai languages'},
        "sot" : {'iso6391': u'st', 'T': u'', 'name': u'Sotho, Southern'},
        "spa" : {'iso6391': u'es', 'T': u'', 'name': u'Spanish; Castilian'},
        "srd" : {'iso6391': u'sc', 'T': u'', 'name': u'Sardinian'},
        "srn" : {'iso6391': u'', 'T': u'', 'name': u'Sranan Tongo'},
        "srp" : {'iso6391': u'sr', 'T': u'', 'name': u'Serbian'},
        "srr" : {'iso6391': u'', 'T': u'', 'name': u'Serer'},
        "ssa" : {'iso6391': u'', 'T': u'', 'name': u'Nilo-Saharan languages'},
        "ssw" : {'iso6391': u'ss', 'T': u'', 'name': u'Swati'},
        "suk" : {'iso6391': u'', 'T': u'', 'name': u'Sukuma'},
        "sun" : {'iso6391': u'su', 'T': u'', 'name': u'Sundanese'},
        "sus" : {'iso6391': u'', 'T': u'', 'name': u'Susu'},
        "sux" : {'iso6391': u'', 'T': u'', 'name': u'Sumerian'},
        "swa" : {'iso6391': u'sw', 'T': u'', 'name': u'Swahili'},
        "swe" : {'iso6391': u'sv', 'T': u'', 'name': u'Swedish'},
        "syc" : {'iso6391': u'', 'T': u'', 'name': u'Classical Syriac'},
        "syr" : {'iso6391': u'', 'T': u'', 'name': u'Syriac'},
        "tah" : {'iso6391': u'ty', 'T': u'', 'name': u'Tahitian'},
        "tai" : {'iso6391': u'', 'T': u'', 'name': u'Tai languages'},
        "tam" : {'iso6391': u'ta', 'T': u'', 'name': u'Tamil'},
        "tat" : {'iso6391': u'tt', 'T': u'', 'name': u'Tatar'},
        "tel" : {'iso6391': u'te', 'T': u'', 'name': u'Telugu'},
        "tem" : {'iso6391': u'', 'T': u'', 'name': u'Timne'},
        "ter" : {'iso6391': u'', 'T': u'', 'name': u'Tereno'},
        "tet" : {'iso6391': u'', 'T': u'', 'name': u'Tetum'},
        "tgk" : {'iso6391': u'tg', 'T': u'', 'name': u'Tajik'},
        "tgl" : {'iso6391': u'tl', 'T': u'', 'name': u'Tagalog'},
        "tha" : {'iso6391': u'th', 'T': u'', 'name': u'Thai'},
        "tib" : {'iso6391': u'bo', 'T': u'bod', 'name': u'Tibetan'},
        "tig" : {'iso6391': u'', 'T': u'', 'name': u'Tigre'},
        "tir" : {'iso6391': u'ti', 'T': u'', 'name': u'Tigrinya'},
        "tiv" : {'iso6391': u'', 'T': u'', 'name': u'Tiv'},
        "tkl" : {'iso6391': u'', 'T': u'', 'name': u'Tokelau'},
        "tlh" : {'iso6391': u'', 'T': u'', 'name': u'Klingon; tlhIngan-Hol'},
        "tli" : {'iso6391': u'', 'T': u'', 'name': u'Tlingit'},
        "tmh" : {'iso6391': u'', 'T': u'', 'name': u'Tamashek'},
        "tog" : {'iso6391': u'', 'T': u'', 'name': u'Tonga (Nyasa)'},
        "ton" : {'iso6391': u'to', 'T': u'', 'name': u'Tonga (Tonga Islands)'},
        "tpi" : {'iso6391': u'', 'T': u'', 'name': u'Tok Pisin'},
        "tsi" : {'iso6391': u'', 'T': u'', 'name': u'Tsimshian'},
        "tsn" : {'iso6391': u'tn', 'T': u'', 'name': u'Tswana'},
        "tso" : {'iso6391': u'ts', 'T': u'', 'name': u'Tsonga'},
        "tuk" : {'iso6391': u'tk', 'T': u'', 'name': u'Turkmen'},
        "tum" : {'iso6391': u'', 'T': u'', 'name': u'Tumbuka'},
        "tup" : {'iso6391': u'', 'T': u'', 'name': u'Tupi languages'},
        "tur" : {'iso6391': u'tr', 'T': u'', 'name': u'Turkish'},
        "tut" : {'iso6391': u'', 'T': u'', 'name': u'Altaic languages'},
        "tvl" : {'iso6391': u'', 'T': u'', 'name': u'Tuvalu'},
        "twi" : {'iso6391': u'tw', 'T': u'', 'name': u'Twi'},
        "tyv" : {'iso6391': u'', 'T': u'', 'name': u'Tuvinian'},
        "udm" : {'iso6391': u'', 'T': u'', 'name': u'Udmurt'},
        "uga" : {'iso6391': u'', 'T': u'', 'name': u'Ugaritic'},
        "uig" : {'iso6391': u'ug', 'T': u'', 'name': u'Uighur; Uyghur'},
        "ukr" : {'iso6391': u'uk', 'T': u'', 'name': u'Ukrainian'},
        "umb" : {'iso6391': u'', 'T': u'', 'name': u'Umbundu'},
        "und" : {'iso6391': u'', 'T': u'', 'name': u'Undetermined'},
        "urd" : {'iso6391': u'ur', 'T': u'', 'name': u'Urdu'},
        "uzb" : {'iso6391': u'uz', 'T': u'', 'name': u'Uzbek'},
        "vai" : {'iso6391': u'', 'T': u'', 'name': u'Vai'},
        "ven" : {'iso6391': u've', 'T': u'', 'name': u'Venda'},
        "vie" : {'iso6391': u'vi', 'T': u'', 'name': u'Vietnamese'},
        "vol" : {'iso6391': u'vo', 'T': u'', 'name': u'Volap\xfck'},
        "vot" : {'iso6391': u'', 'T': u'', 'name': u'Votic'},
        "wak" : {'iso6391': u'', 'T': u'', 'name': u'Wakashan languages'},
        "wal" : {'iso6391': u'', 'T': u'', 'name': u'Walamo'},
        "war" : {'iso6391': u'', 'T': u'', 'name': u'Waray'},
        "was" : {'iso6391': u'', 'T': u'', 'name': u'Washo'},
        "wel" : {'iso6391': u'cy', 'T': u'cym', 'name': u'Welsh'},
        "wen" : {'iso6391': u'', 'T': u'', 'name': u'Sorbian languages'},
        "wln" : {'iso6391': u'wa', 'T': u'', 'name': u'Walloon'},
        "wol" : {'iso6391': u'wo', 'T': u'', 'name': u'Wolof'},
        "xal" : {'iso6391': u'', 'T': u'', 'name': u'Kalmyk; Oirat'},
        "xho" : {'iso6391': u'xh', 'T': u'', 'name': u'Xhosa'},
        "yao" : {'iso6391': u'', 'T': u'', 'name': u'Yao'},
        "yap" : {'iso6391': u'', 'T': u'', 'name': u'Yapese'},
        "yid" : {'iso6391': u'yi', 'T': u'', 'name': u'Yiddish'},
        "yor" : {'iso6391': u'yo', 'T': u'', 'name': u'Yoruba'},
        "ypk" : {'iso6391': u'', 'T': u'', 'name': u'Yupik languages'},
        "zap" : {'iso6391': u'', 'T': u'', 'name': u'Zapotec'},
        "zbl" : {'iso6391': u'', 'T': u'', 'name': u'Blissymbols; Blissymbolics; Bliss'},
        "zen" : {'iso6391': u'', 'T': u'', 'name': u'Zenaga'},
        "zgh" : {'iso6391': u'', 'T': u'', 'name': u'Standard Moroccan Tamazight'},
        "zha" : {'iso6391': u'za', 'T': u'', 'name': u'Zhuang; Chuang'},
        "znd" : {'iso6391': u'', 'T': u'', 'name': u'Zande languages'},
        "zul" : {'iso6391': u'zu', 'T': u'', 'name': u'Zulu'},
        "zun" : {'iso6391': u'', 'T': u'', 'name': u'Zuni'},
        "zxx" : {'iso6391': u'', 'T': u'', 'name': u'No linguistic content; Not applicable'},
        "zza" : {'iso6391': u'', 'T': u'', 'name': u'Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki'}
    }
    
    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["iso-639-2", "language"]
    
    def validate(self, datatype, lang, *args, **kwargs):
        r = plugin.ValidationResponse()
        return self.validate_format(datatype, lang, validation_response=r)
    
    def validate_format(self, datatype, lang, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        if len(lang) != 3:
            r.error("ISO-639-2 language codes are all 3 letters")
            return r
        
        if lang not in self.codes.keys():
            if datatype == "iso-639-2":
                r.error("Language code does not appear in the iso-639-2 list of valid codes")
            elif datatype == "language":
                r.warn("Language code does not appear in the iso-639-2 list of valid codes")
        else:
            info = self.codes.get(lang)
            if info.get("iso6391", "") != "":
                r.info("Equivalent iso-639-1 tag is " + info.get("iso6391"))
                r.alternative(info.get("iso6391"))
            if info.get("name", "") != "":
                r.info("Language code refers to " + info.get("name"))
                r.alternative(info.get("name"))
        
        return r
    
class Language(plugin.Validator):

    langs = {
        "abkhazian" : {'iso6392': u'abk', 'iso6391': u'ab', 'T': u''},
        "achinese" : {'iso6392': u'ace', 'iso6391': u'', 'T': u''},
        "acoli" : {'iso6392': u'ach', 'iso6391': u'', 'T': u''},
        "adangme" : {'iso6392': u'ada', 'iso6391': u'', 'T': u''},
        "adyghe; adygei" : {'iso6392': u'ady', 'iso6391': u'', 'T': u''},
        "afar" : {'iso6392': u'aar', 'iso6391': u'aa', 'T': u''},
        "afrihili" : {'iso6392': u'afh', 'iso6391': u'', 'T': u''},
        "afrikaans" : {'iso6392': u'afr', 'iso6391': u'af', 'T': u''},
        "afro-asiatic languages" : {'iso6392': u'afa', 'iso6391': u'', 'T': u''},
        "ainu" : {'iso6392': u'ain', 'iso6391': u'', 'T': u''},
        "akan" : {'iso6392': u'aka', 'iso6391': u'ak', 'T': u''},
        "akkadian" : {'iso6392': u'akk', 'iso6391': u'', 'T': u''},
        "albanian" : {'iso6392': u'alb', 'iso6391': u'sq', 'T': u'sqi'},
        "aleut" : {'iso6392': u'ale', 'iso6391': u'', 'T': u''},
        "algonquian languages" : {'iso6392': u'alg', 'iso6391': u'', 'T': u''},
        "altaic languages" : {'iso6392': u'tut', 'iso6391': u'', 'T': u''},
        "amharic" : {'iso6392': u'amh', 'iso6391': u'am', 'T': u''},
        "angika" : {'iso6392': u'anp', 'iso6391': u'', 'T': u''},
        "apache languages" : {'iso6392': u'apa', 'iso6391': u'', 'T': u''},
        "arabic" : {'iso6392': u'ara', 'iso6391': u'ar', 'T': u''},
        "aragonese" : {'iso6392': u'arg', 'iso6391': u'an', 'T': u''},
        "arapaho" : {'iso6392': u'arp', 'iso6391': u'', 'T': u''},
        "arawak" : {'iso6392': u'arw', 'iso6391': u'', 'T': u''},
        "armenian" : {'iso6392': u'arm', 'iso6391': u'hy', 'T': u'hye'},
        "aromanian; arumanian; macedo-romanian" : {'iso6392': u'rup', 'iso6391': u'', 'T': u''},
        "artificial languages" : {'iso6392': u'art', 'iso6391': u'', 'T': u''},
        "assamese" : {'iso6392': u'asm', 'iso6391': u'as', 'T': u''},
        "asturian; bable; leonese; asturleonese" : {'iso6392': u'ast', 'iso6391': u'', 'T': u''},
        "athapascan languages" : {'iso6392': u'ath', 'iso6391': u'', 'T': u''},
        "australian languages" : {'iso6392': u'aus', 'iso6391': u'', 'T': u''},
        "austronesian languages" : {'iso6392': u'map', 'iso6391': u'', 'T': u''},
        "avaric" : {'iso6392': u'ava', 'iso6391': u'av', 'T': u''},
        "avestan" : {'iso6392': u'ave', 'iso6391': u'ae', 'T': u''},
        "awadhi" : {'iso6392': u'awa', 'iso6391': u'', 'T': u''},
        "aymara" : {'iso6392': u'aym', 'iso6391': u'ay', 'T': u''},
        "azerbaijani" : {'iso6392': u'aze', 'iso6391': u'az', 'T': u''},
        "balinese" : {'iso6392': u'ban', 'iso6391': u'', 'T': u''},
        "baltic languages" : {'iso6392': u'bat', 'iso6391': u'', 'T': u''},
        "baluchi" : {'iso6392': u'bal', 'iso6391': u'', 'T': u''},
        "bambara" : {'iso6392': u'bam', 'iso6391': u'bm', 'T': u''},
        "bamileke languages" : {'iso6392': u'bai', 'iso6391': u'', 'T': u''},
        "banda languages" : {'iso6392': u'bad', 'iso6391': u'', 'T': u''},
        "bantu (other)" : {'iso6392': u'bnt', 'iso6391': u'', 'T': u''},
        "basa" : {'iso6392': u'bas', 'iso6391': u'', 'T': u''},
        "bashkir" : {'iso6392': u'bak', 'iso6391': u'ba', 'T': u''},
        "basque" : {'iso6392': u'baq', 'iso6391': u'eu', 'T': u'eus'},
        "batak languages" : {'iso6392': u'btk', 'iso6391': u'', 'T': u''},
        "beja; bedawiyet" : {'iso6392': u'bej', 'iso6391': u'', 'T': u''},
        "belarusian" : {'iso6392': u'bel', 'iso6391': u'be', 'T': u''},
        "bemba" : {'iso6392': u'bem', 'iso6391': u'', 'T': u''},
        "bengali" : {'iso6392': u'ben', 'iso6391': u'bn', 'T': u''},
        "berber languages" : {'iso6392': u'ber', 'iso6391': u'', 'T': u''},
        "bhojpuri" : {'iso6392': u'bho', 'iso6391': u'', 'T': u''},
        "bihari languages" : {'iso6392': u'bih', 'iso6391': u'bh', 'T': u''},
        "bikol" : {'iso6392': u'bik', 'iso6391': u'', 'T': u''},
        "bini; edo" : {'iso6392': u'bin', 'iso6391': u'', 'T': u''},
        "bislama" : {'iso6392': u'bis', 'iso6391': u'bi', 'T': u''},
        "blin; bilin" : {'iso6392': u'byn', 'iso6391': u'', 'T': u''},
        "blissymbols; blissymbolics; bliss" : {'iso6392': u'zbl', 'iso6391': u'', 'T': u''},
        u"bokm\xe5l, norwegian; norwegian bokm\xe5l" : {'iso6392': u'nob', 'iso6391': u'nb', 'T': u''},
        "bosnian" : {'iso6392': u'bos', 'iso6391': u'bs', 'T': u''},
        "braj" : {'iso6392': u'bra', 'iso6391': u'', 'T': u''},
        "breton" : {'iso6392': u'bre', 'iso6391': u'br', 'T': u''},
        "buginese" : {'iso6392': u'bug', 'iso6391': u'', 'T': u''},
        "bulgarian" : {'iso6392': u'bul', 'iso6391': u'bg', 'T': u''},
        "buriat" : {'iso6392': u'bua', 'iso6391': u'', 'T': u''},
        "burmese" : {'iso6392': u'bur', 'iso6391': u'my', 'T': u'mya'},
        "caddo" : {'iso6392': u'cad', 'iso6391': u'', 'T': u''},
        "catalan; valencian" : {'iso6392': u'cat', 'iso6391': u'ca', 'T': u''},
        "caucasian languages" : {'iso6392': u'cau', 'iso6391': u'', 'T': u''},
        "cebuano" : {'iso6392': u'ceb', 'iso6391': u'', 'T': u''},
        "celtic languages" : {'iso6392': u'cel', 'iso6391': u'', 'T': u''},
        "central american indian languages" : {'iso6392': u'cai', 'iso6391': u'', 'T': u''},
        "central khmer" : {'iso6392': u'khm', 'iso6391': u'km', 'T': u''},
        "chagatai" : {'iso6392': u'chg', 'iso6391': u'', 'T': u''},
        "chamic languages" : {'iso6392': u'cmc', 'iso6391': u'', 'T': u''},
        "chamorro" : {'iso6392': u'cha', 'iso6391': u'ch', 'T': u''},
        "chechen" : {'iso6392': u'che', 'iso6391': u'ce', 'T': u''},
        "cherokee" : {'iso6392': u'chr', 'iso6391': u'', 'T': u''},
        "cheyenne" : {'iso6392': u'chy', 'iso6391': u'', 'T': u''},
        "chibcha" : {'iso6392': u'chb', 'iso6391': u'', 'T': u''},
        "chichewa; chewa; nyanja" : {'iso6392': u'nya', 'iso6391': u'ny', 'T': u''},
        "chinese" : {'iso6392': u'chi', 'iso6391': u'zh', 'T': u'zho'},
        "chinook jargon" : {'iso6392': u'chn', 'iso6391': u'', 'T': u''},
        "chipewyan; dene suline" : {'iso6392': u'chp', 'iso6391': u'', 'T': u''},
        "choctaw" : {'iso6392': u'cho', 'iso6391': u'', 'T': u''},
        "church slavic; old slavonic; church slavonic; old bulgarian; old church slavonic" : {'iso6392': u'chu', 'iso6391': u'cu', 'T': u''},
        "chuukese" : {'iso6392': u'chk', 'iso6391': u'', 'T': u''},
        "chuvash" : {'iso6392': u'chv', 'iso6391': u'cv', 'T': u''},
        "classical newari; old newari; classical nepal bhasa" : {'iso6392': u'nwc', 'iso6391': u'', 'T': u''},
        "classical syriac" : {'iso6392': u'syc', 'iso6391': u'', 'T': u''},
        "coptic" : {'iso6392': u'cop', 'iso6391': u'', 'T': u''},
        "cornish" : {'iso6392': u'cor', 'iso6391': u'kw', 'T': u''},
        "corsican" : {'iso6392': u'cos', 'iso6391': u'co', 'T': u''},
        "cree" : {'iso6392': u'cre', 'iso6391': u'cr', 'T': u''},
        "creek" : {'iso6392': u'mus', 'iso6391': u'', 'T': u''},
        "creoles and pidgins " : {'iso6392': u'crp', 'iso6391': u'', 'T': u''},
        "creoles and pidgins, english based" : {'iso6392': u'cpe', 'iso6391': u'', 'T': u''},
        "creoles and pidgins, french-based " : {'iso6392': u'cpf', 'iso6391': u'', 'T': u''},
        "creoles and pidgins, portuguese-based " : {'iso6392': u'cpp', 'iso6391': u'', 'T': u''},
        "crimean tatar; crimean turkish" : {'iso6392': u'crh', 'iso6391': u'', 'T': u''},
        "croatian" : {'iso6392': u'hrv', 'iso6391': u'hr', 'T': u''},
        "cushitic languages" : {'iso6392': u'cus', 'iso6391': u'', 'T': u''},
        "czech" : {'iso6392': u'cze', 'iso6391': u'cs', 'T': u'ces'},
        "dakota" : {'iso6392': u'dak', 'iso6391': u'', 'T': u''},
        "danish" : {'iso6392': u'dan', 'iso6391': u'da', 'T': u''},
        "dargwa" : {'iso6392': u'dar', 'iso6391': u'', 'T': u''},
        "delaware" : {'iso6392': u'del', 'iso6391': u'', 'T': u''},
        "dinka" : {'iso6392': u'din', 'iso6391': u'', 'T': u''},
        "divehi; dhivehi; maldivian" : {'iso6392': u'div', 'iso6391': u'dv', 'T': u''},
        "dogri" : {'iso6392': u'doi', 'iso6391': u'', 'T': u''},
        "dogrib" : {'iso6392': u'dgr', 'iso6391': u'', 'T': u''},
        "dravidian languages" : {'iso6392': u'dra', 'iso6391': u'', 'T': u''},
        "duala" : {'iso6392': u'dua', 'iso6391': u'', 'T': u''},
        "dutch, middle (ca.1050-1350)" : {'iso6392': u'dum', 'iso6391': u'', 'T': u''},
        "dutch; flemish" : {'iso6392': u'dut', 'iso6391': u'nl', 'T': u'nld'},
        "dyula" : {'iso6392': u'dyu', 'iso6391': u'', 'T': u''},
        "dzongkha" : {'iso6392': u'dzo', 'iso6391': u'dz', 'T': u''},
        "eastern frisian" : {'iso6392': u'frs', 'iso6391': u'', 'T': u''},
        "efik" : {'iso6392': u'efi', 'iso6391': u'', 'T': u''},
        "egyptian (ancient)" : {'iso6392': u'egy', 'iso6391': u'', 'T': u''},
        "ekajuk" : {'iso6392': u'eka', 'iso6391': u'', 'T': u''},
        "elamite" : {'iso6392': u'elx', 'iso6391': u'', 'T': u''},
        "english" : {'iso6392': u'eng', 'iso6391': u'en', 'T': u''},
        "english, middle (1100-1500)" : {'iso6392': u'enm', 'iso6391': u'', 'T': u''},
        "english, old (ca.450-1100)" : {'iso6392': u'ang', 'iso6391': u'', 'T': u''},
        "erzya" : {'iso6392': u'myv', 'iso6391': u'', 'T': u''},
        "esperanto" : {'iso6392': u'epo', 'iso6391': u'eo', 'T': u''},
        "estonian" : {'iso6392': u'est', 'iso6391': u'et', 'T': u''},
        "ewe" : {'iso6392': u'ewe', 'iso6391': u'ee', 'T': u''},
        "ewondo" : {'iso6392': u'ewo', 'iso6391': u'', 'T': u''},
        "fang" : {'iso6392': u'fan', 'iso6391': u'', 'T': u''},
        "fanti" : {'iso6392': u'fat', 'iso6391': u'', 'T': u''},
        "faroese" : {'iso6392': u'fao', 'iso6391': u'fo', 'T': u''},
        "fijian" : {'iso6392': u'fij', 'iso6391': u'fj', 'T': u''},
        "filipino; pilipino" : {'iso6392': u'fil', 'iso6391': u'', 'T': u''},
        "finnish" : {'iso6392': u'fin', 'iso6391': u'fi', 'T': u''},
        "finno-ugrian languages" : {'iso6392': u'fiu', 'iso6391': u'', 'T': u''},
        "fon" : {'iso6392': u'fon', 'iso6391': u'', 'T': u''},
        "french" : {'iso6392': u'fre', 'iso6391': u'fr', 'T': u'fra'},
        "french, middle (ca.1400-1600)" : {'iso6392': u'frm', 'iso6391': u'', 'T': u''},
        "french, old (842-ca.1400)" : {'iso6392': u'fro', 'iso6391': u'', 'T': u''},
        "friulian" : {'iso6392': u'fur', 'iso6391': u'', 'T': u''},
        "fulah" : {'iso6392': u'ful', 'iso6391': u'ff', 'T': u''},
        "ga" : {'iso6392': u'gaa', 'iso6391': u'', 'T': u''},
        "gaelic; scottish gaelic" : {'iso6392': u'gla', 'iso6391': u'gd', 'T': u''},
        "galibi carib" : {'iso6392': u'car', 'iso6391': u'', 'T': u''},
        "galician" : {'iso6392': u'glg', 'iso6391': u'gl', 'T': u''},
        "ganda" : {'iso6392': u'lug', 'iso6391': u'lg', 'T': u''},
        "gayo" : {'iso6392': u'gay', 'iso6391': u'', 'T': u''},
        "gbaya" : {'iso6392': u'gba', 'iso6391': u'', 'T': u''},
        "geez" : {'iso6392': u'gez', 'iso6391': u'', 'T': u''},
        "georgian" : {'iso6392': u'geo', 'iso6391': u'ka', 'T': u'kat'},
        "german" : {'iso6392': u'ger', 'iso6391': u'de', 'T': u'deu'},
        "german, middle high (ca.1050-1500)" : {'iso6392': u'gmh', 'iso6391': u'', 'T': u''},
        "german, old high (ca.750-1050)" : {'iso6392': u'goh', 'iso6391': u'', 'T': u''},
        "germanic languages" : {'iso6392': u'gem', 'iso6391': u'', 'T': u''},
        "gilbertese" : {'iso6392': u'gil', 'iso6391': u'', 'T': u''},
        "gondi" : {'iso6392': u'gon', 'iso6391': u'', 'T': u''},
        "gorontalo" : {'iso6392': u'gor', 'iso6391': u'', 'T': u''},
        "gothic" : {'iso6392': u'got', 'iso6391': u'', 'T': u''},
        "grebo" : {'iso6392': u'grb', 'iso6391': u'', 'T': u''},
        "greek, ancient (to 1453)" : {'iso6392': u'grc', 'iso6391': u'', 'T': u''},
        "greek, modern (1453-)" : {'iso6392': u'gre', 'iso6391': u'el', 'T': u'ell'},
        "guarani" : {'iso6392': u'grn', 'iso6391': u'gn', 'T': u''},
        "gujarati" : {'iso6392': u'guj', 'iso6391': u'gu', 'T': u''},
        "gwich'in" : {'iso6392': u'gwi', 'iso6391': u'', 'T': u''},
        "haida" : {'iso6392': u'hai', 'iso6391': u'', 'T': u''},
        "haitian; haitian creole" : {'iso6392': u'hat', 'iso6391': u'ht', 'T': u''},
        "hausa" : {'iso6392': u'hau', 'iso6391': u'ha', 'T': u''},
        "hawaiian" : {'iso6392': u'haw', 'iso6391': u'', 'T': u''},
        "hebrew" : {'iso6392': u'heb', 'iso6391': u'he', 'T': u''},
        "herero" : {'iso6392': u'her', 'iso6391': u'hz', 'T': u''},
        "hiligaynon" : {'iso6392': u'hil', 'iso6391': u'', 'T': u''},
        "himachali languages; western pahari languages" : {'iso6392': u'him', 'iso6391': u'', 'T': u''},
        "hindi" : {'iso6392': u'hin', 'iso6391': u'hi', 'T': u''},
        "hiri motu" : {'iso6392': u'hmo', 'iso6391': u'ho', 'T': u''},
        "hittite" : {'iso6392': u'hit', 'iso6391': u'', 'T': u''},
        "hmong; mong" : {'iso6392': u'hmn', 'iso6391': u'', 'T': u''},
        "hungarian" : {'iso6392': u'hun', 'iso6391': u'hu', 'T': u''},
        "hupa" : {'iso6392': u'hup', 'iso6391': u'', 'T': u''},
        "iban" : {'iso6392': u'iba', 'iso6391': u'', 'T': u''},
        "icelandic" : {'iso6392': u'ice', 'iso6391': u'is', 'T': u'isl'},
        "ido" : {'iso6392': u'ido', 'iso6391': u'io', 'T': u''},
        "igbo" : {'iso6392': u'ibo', 'iso6391': u'ig', 'T': u''},
        "ijo languages" : {'iso6392': u'ijo', 'iso6391': u'', 'T': u''},
        "iloko" : {'iso6392': u'ilo', 'iso6391': u'', 'T': u''},
        "inari sami" : {'iso6392': u'smn', 'iso6391': u'', 'T': u''},
        "indic languages" : {'iso6392': u'inc', 'iso6391': u'', 'T': u''},
        "indo-european languages" : {'iso6392': u'ine', 'iso6391': u'', 'T': u''},
        "indonesian" : {'iso6392': u'ind', 'iso6391': u'id', 'T': u''},
        "ingush" : {'iso6392': u'inh', 'iso6391': u'', 'T': u''},
        "interlingua (international auxiliary language association)" : {'iso6392': u'ina', 'iso6391': u'ia', 'T': u''},
        "interlingue; occidental" : {'iso6392': u'ile', 'iso6391': u'ie', 'T': u''},
        "inuktitut" : {'iso6392': u'iku', 'iso6391': u'iu', 'T': u''},
        "inupiaq" : {'iso6392': u'ipk', 'iso6391': u'ik', 'T': u''},
        "iranian languages" : {'iso6392': u'ira', 'iso6391': u'', 'T': u''},
        "irish" : {'iso6392': u'gle', 'iso6391': u'ga', 'T': u''},
        "irish, middle (900-1200)" : {'iso6392': u'mga', 'iso6391': u'', 'T': u''},
        "irish, old (to 900)" : {'iso6392': u'sga', 'iso6391': u'', 'T': u''},
        "iroquoian languages" : {'iso6392': u'iro', 'iso6391': u'', 'T': u''},
        "italian" : {'iso6392': u'ita', 'iso6391': u'it', 'T': u''},
        "japanese" : {'iso6392': u'jpn', 'iso6391': u'ja', 'T': u''},
        "javanese" : {'iso6392': u'jav', 'iso6391': u'jv', 'T': u''},
        "judeo-arabic" : {'iso6392': u'jrb', 'iso6391': u'', 'T': u''},
        "judeo-persian" : {'iso6392': u'jpr', 'iso6391': u'', 'T': u''},
        "kabardian" : {'iso6392': u'kbd', 'iso6391': u'', 'T': u''},
        "kabyle" : {'iso6392': u'kab', 'iso6391': u'', 'T': u''},
        "kachin; jingpho" : {'iso6392': u'kac', 'iso6391': u'', 'T': u''},
        "kalaallisut; greenlandic" : {'iso6392': u'kal', 'iso6391': u'kl', 'T': u''},
        "kalmyk; oirat" : {'iso6392': u'xal', 'iso6391': u'', 'T': u''},
        "kamba" : {'iso6392': u'kam', 'iso6391': u'', 'T': u''},
        "kannada" : {'iso6392': u'kan', 'iso6391': u'kn', 'T': u''},
        "kanuri" : {'iso6392': u'kau', 'iso6391': u'kr', 'T': u''},
        "kara-kalpak" : {'iso6392': u'kaa', 'iso6391': u'', 'T': u''},
        "karachay-balkar" : {'iso6392': u'krc', 'iso6391': u'', 'T': u''},
        "karelian" : {'iso6392': u'krl', 'iso6391': u'', 'T': u''},
        "karen languages" : {'iso6392': u'kar', 'iso6391': u'', 'T': u''},
        "kashmiri" : {'iso6392': u'kas', 'iso6391': u'ks', 'T': u''},
        "kashubian" : {'iso6392': u'csb', 'iso6391': u'', 'T': u''},
        "kawi" : {'iso6392': u'kaw', 'iso6391': u'', 'T': u''},
        "kazakh" : {'iso6392': u'kaz', 'iso6391': u'kk', 'T': u''},
        "khasi" : {'iso6392': u'kha', 'iso6391': u'', 'T': u''},
        "khoisan languages" : {'iso6392': u'khi', 'iso6391': u'', 'T': u''},
        "khotanese; sakan" : {'iso6392': u'kho', 'iso6391': u'', 'T': u''},
        "kikuyu; gikuyu" : {'iso6392': u'kik', 'iso6391': u'ki', 'T': u''},
        "kimbundu" : {'iso6392': u'kmb', 'iso6391': u'', 'T': u''},
        "kinyarwanda" : {'iso6392': u'kin', 'iso6391': u'rw', 'T': u''},
        "kirghiz; kyrgyz" : {'iso6392': u'kir', 'iso6391': u'ky', 'T': u''},
        "klingon; tlhingan-hol" : {'iso6392': u'tlh', 'iso6391': u'', 'T': u''},
        "komi" : {'iso6392': u'kom', 'iso6391': u'kv', 'T': u''},
        "kongo" : {'iso6392': u'kon', 'iso6391': u'kg', 'T': u''},
        "konkani" : {'iso6392': u'kok', 'iso6391': u'', 'T': u''},
        "korean" : {'iso6392': u'kor', 'iso6391': u'ko', 'T': u''},
        "kosraean" : {'iso6392': u'kos', 'iso6391': u'', 'T': u''},
        "kpelle" : {'iso6392': u'kpe', 'iso6391': u'', 'T': u''},
        "kru languages" : {'iso6392': u'kro', 'iso6391': u'', 'T': u''},
        "kuanyama; kwanyama" : {'iso6392': u'kua', 'iso6391': u'kj', 'T': u''},
        "kumyk" : {'iso6392': u'kum', 'iso6391': u'', 'T': u''},
        "kurdish" : {'iso6392': u'kur', 'iso6391': u'ku', 'T': u''},
        "kurukh" : {'iso6392': u'kru', 'iso6391': u'', 'T': u''},
        "kutenai" : {'iso6392': u'kut', 'iso6391': u'', 'T': u''},
        "ladino" : {'iso6392': u'lad', 'iso6391': u'', 'T': u''},
        "lahnda" : {'iso6392': u'lah', 'iso6391': u'', 'T': u''},
        "lamba" : {'iso6392': u'lam', 'iso6391': u'', 'T': u''},
        "land dayak languages" : {'iso6392': u'day', 'iso6391': u'', 'T': u''},
        "lao" : {'iso6392': u'lao', 'iso6391': u'lo', 'T': u''},
        "latin" : {'iso6392': u'lat', 'iso6391': u'la', 'T': u''},
        "latvian" : {'iso6392': u'lav', 'iso6391': u'lv', 'T': u''},
        "lezghian" : {'iso6392': u'lez', 'iso6391': u'', 'T': u''},
        "limburgan; limburger; limburgish" : {'iso6392': u'lim', 'iso6391': u'li', 'T': u''},
        "lingala" : {'iso6392': u'lin', 'iso6391': u'ln', 'T': u''},
        "lithuanian" : {'iso6392': u'lit', 'iso6391': u'lt', 'T': u''},
        "lojban" : {'iso6392': u'jbo', 'iso6391': u'', 'T': u''},
        "low german; low saxon; german, low; saxon, low" : {'iso6392': u'nds', 'iso6391': u'', 'T': u''},
        "lower sorbian" : {'iso6392': u'dsb', 'iso6391': u'', 'T': u''},
        "lozi" : {'iso6392': u'loz', 'iso6391': u'', 'T': u''},
        "luba-katanga" : {'iso6392': u'lub', 'iso6391': u'lu', 'T': u''},
        "luba-lulua" : {'iso6392': u'lua', 'iso6391': u'', 'T': u''},
        "luiseno" : {'iso6392': u'lui', 'iso6391': u'', 'T': u''},
        "lule sami" : {'iso6392': u'smj', 'iso6391': u'', 'T': u''},
        "lunda" : {'iso6392': u'lun', 'iso6391': u'', 'T': u''},
        "luo (kenya and tanzania)" : {'iso6392': u'luo', 'iso6391': u'', 'T': u''},
        "lushai" : {'iso6392': u'lus', 'iso6391': u'', 'T': u''},
        "luxembourgish; letzeburgesch" : {'iso6392': u'ltz', 'iso6391': u'lb', 'T': u''},
        "macedonian" : {'iso6392': u'mac', 'iso6391': u'mk', 'T': u'mkd'},
        "madurese" : {'iso6392': u'mad', 'iso6391': u'', 'T': u''},
        "magahi" : {'iso6392': u'mag', 'iso6391': u'', 'T': u''},
        "maithili" : {'iso6392': u'mai', 'iso6391': u'', 'T': u''},
        "makasar" : {'iso6392': u'mak', 'iso6391': u'', 'T': u''},
        "malagasy" : {'iso6392': u'mlg', 'iso6391': u'mg', 'T': u''},
        "malay" : {'iso6392': u'may', 'iso6391': u'ms', 'T': u'msa'},
        "malayalam" : {'iso6392': u'mal', 'iso6391': u'ml', 'T': u''},
        "maltese" : {'iso6392': u'mlt', 'iso6391': u'mt', 'T': u''},
        "manchu" : {'iso6392': u'mnc', 'iso6391': u'', 'T': u''},
        "mandar" : {'iso6392': u'mdr', 'iso6391': u'', 'T': u''},
        "mandingo" : {'iso6392': u'man', 'iso6391': u'', 'T': u''},
        "manipuri" : {'iso6392': u'mni', 'iso6391': u'', 'T': u''},
        "manobo languages" : {'iso6392': u'mno', 'iso6391': u'', 'T': u''},
        "manx" : {'iso6392': u'glv', 'iso6391': u'gv', 'T': u''},
        "maori" : {'iso6392': u'mao', 'iso6391': u'mi', 'T': u'mri'},
        "mapudungun; mapuche" : {'iso6392': u'arn', 'iso6391': u'', 'T': u''},
        "marathi" : {'iso6392': u'mar', 'iso6391': u'mr', 'T': u''},
        "mari" : {'iso6392': u'chm', 'iso6391': u'', 'T': u''},
        "marshallese" : {'iso6392': u'mah', 'iso6391': u'mh', 'T': u''},
        "marwari" : {'iso6392': u'mwr', 'iso6391': u'', 'T': u''},
        "masai" : {'iso6392': u'mas', 'iso6391': u'', 'T': u''},
        "mayan languages" : {'iso6392': u'myn', 'iso6391': u'', 'T': u''},
        "mende" : {'iso6392': u'men', 'iso6391': u'', 'T': u''},
        "mi'kmaq; micmac" : {'iso6392': u'mic', 'iso6391': u'', 'T': u''},
        "minangkabau" : {'iso6392': u'min', 'iso6391': u'', 'T': u''},
        "mirandese" : {'iso6392': u'mwl', 'iso6391': u'', 'T': u''},
        "mohawk" : {'iso6392': u'moh', 'iso6391': u'', 'T': u''},
        "moksha" : {'iso6392': u'mdf', 'iso6391': u'', 'T': u''},
        "mon-khmer languages" : {'iso6392': u'mkh', 'iso6391': u'', 'T': u''},
        "mongo" : {'iso6392': u'lol', 'iso6391': u'', 'T': u''},
        "mongolian" : {'iso6392': u'mon', 'iso6391': u'mn', 'T': u''},
        "mossi" : {'iso6392': u'mos', 'iso6391': u'', 'T': u''},
        "multiple languages" : {'iso6392': u'mul', 'iso6391': u'', 'T': u''},
        "munda languages" : {'iso6392': u'mun', 'iso6391': u'', 'T': u''},
        "n'ko" : {'iso6392': u'nqo', 'iso6391': u'', 'T': u''},
        "nahuatl languages" : {'iso6392': u'nah', 'iso6391': u'', 'T': u''},
        "nauru" : {'iso6392': u'nau', 'iso6391': u'na', 'T': u''},
        "navajo; navaho" : {'iso6392': u'nav', 'iso6391': u'nv', 'T': u''},
        "ndebele, north; north ndebele" : {'iso6392': u'nde', 'iso6391': u'nd', 'T': u''},
        "ndebele, south; south ndebele" : {'iso6392': u'nbl', 'iso6391': u'nr', 'T': u''},
        "ndonga" : {'iso6392': u'ndo', 'iso6391': u'ng', 'T': u''},
        "neapolitan" : {'iso6392': u'nap', 'iso6391': u'', 'T': u''},
        "nepal bhasa; newari" : {'iso6392': u'new', 'iso6391': u'', 'T': u''},
        "nepali" : {'iso6392': u'nep', 'iso6391': u'ne', 'T': u''},
        "nias" : {'iso6392': u'nia', 'iso6391': u'', 'T': u''},
        "niger-kordofanian languages" : {'iso6392': u'nic', 'iso6391': u'', 'T': u''},
        "nilo-saharan languages" : {'iso6392': u'ssa', 'iso6391': u'', 'T': u''},
        "niuean" : {'iso6392': u'niu', 'iso6391': u'', 'T': u''},
        "no linguistic content; not applicable" : {'iso6392': u'zxx', 'iso6391': u'', 'T': u''},
        "nogai" : {'iso6392': u'nog', 'iso6391': u'', 'T': u''},
        "norse, old" : {'iso6392': u'non', 'iso6391': u'', 'T': u''},
        "north american indian languages" : {'iso6392': u'nai', 'iso6391': u'', 'T': u''},
        "northern frisian" : {'iso6392': u'frr', 'iso6391': u'', 'T': u''},
        "northern sami" : {'iso6392': u'sme', 'iso6391': u'se', 'T': u''},
        "norwegian" : {'iso6392': u'nor', 'iso6391': u'no', 'T': u''},
        "norwegian nynorsk; nynorsk, norwegian" : {'iso6392': u'nno', 'iso6391': u'nn', 'T': u''},
        "nubian languages" : {'iso6392': u'nub', 'iso6391': u'', 'T': u''},
        "nyamwezi" : {'iso6392': u'nym', 'iso6391': u'', 'T': u''},
        "nyankole" : {'iso6392': u'nyn', 'iso6391': u'', 'T': u''},
        "nyoro" : {'iso6392': u'nyo', 'iso6391': u'', 'T': u''},
        "nzima" : {'iso6392': u'nzi', 'iso6391': u'', 'T': u''},
        u"occitan (post 1500); proven\xe7al" : {'iso6392': u'oci', 'iso6391': u'oc', 'T': u''},
        "official aramaic (700-300 bce); imperial aramaic (700-300 bce)" : {'iso6392': u'arc', 'iso6391': u'', 'T': u''},
        "ojibwa" : {'iso6392': u'oji', 'iso6391': u'oj', 'T': u''},
        "oriya" : {'iso6392': u'ori', 'iso6391': u'or', 'T': u''},
        "oromo" : {'iso6392': u'orm', 'iso6391': u'om', 'T': u''},
        "osage" : {'iso6392': u'osa', 'iso6391': u'', 'T': u''},
        "ossetian; ossetic" : {'iso6392': u'oss', 'iso6391': u'os', 'T': u''},
        "otomian languages" : {'iso6392': u'oto', 'iso6391': u'', 'T': u''},
        "pahlavi" : {'iso6392': u'pal', 'iso6391': u'', 'T': u''},
        "palauan" : {'iso6392': u'pau', 'iso6391': u'', 'T': u''},
        "pali" : {'iso6392': u'pli', 'iso6391': u'pi', 'T': u''},
        "pampanga; kapampangan" : {'iso6392': u'pam', 'iso6391': u'', 'T': u''},
        "pangasinan" : {'iso6392': u'pag', 'iso6391': u'', 'T': u''},
        "panjabi; punjabi" : {'iso6392': u'pan', 'iso6391': u'pa', 'T': u''},
        "papiamento" : {'iso6392': u'pap', 'iso6391': u'', 'T': u''},
        "papuan languages" : {'iso6392': u'paa', 'iso6391': u'', 'T': u''},
        "pedi; sepedi; northern sotho" : {'iso6392': u'nso', 'iso6391': u'', 'T': u''},
        "persian" : {'iso6392': u'per', 'iso6391': u'fa', 'T': u'fas'},
        "persian, old (ca.600-400 b.c.)" : {'iso6392': u'peo', 'iso6391': u'', 'T': u''},
        "philippine languages" : {'iso6392': u'phi', 'iso6391': u'', 'T': u''},
        "phoenician" : {'iso6392': u'phn', 'iso6391': u'', 'T': u''},
        "pohnpeian" : {'iso6392': u'pon', 'iso6391': u'', 'T': u''},
        "polish" : {'iso6392': u'pol', 'iso6391': u'pl', 'T': u''},
        "portuguese" : {'iso6392': u'por', 'iso6391': u'pt', 'T': u''},
        "prakrit languages" : {'iso6392': u'pra', 'iso6391': u'', 'T': u''},
        u"proven\xe7al, old (to 1500)" : {'iso6392': u'pro', 'iso6391': u'', 'T': u''},
        "pushto; pashto" : {'iso6392': u'pus', 'iso6391': u'ps', 'T': u''},
        "quechua" : {'iso6392': u'que', 'iso6391': u'qu', 'T': u''},
        "rajasthani" : {'iso6392': u'raj', 'iso6391': u'', 'T': u''},
        "rapanui" : {'iso6392': u'rap', 'iso6391': u'', 'T': u''},
        "rarotongan; cook islands maori" : {'iso6392': u'rar', 'iso6391': u'', 'T': u''},
        "reserved for local use" : {'iso6392': u'qaa-qtz', 'iso6391': u'', 'T': u''},
        "romance languages" : {'iso6392': u'roa', 'iso6391': u'', 'T': u''},
        "romanian; moldavian; moldovan" : {'iso6392': u'rum', 'iso6391': u'ro', 'T': u'ron'},
        "romansh" : {'iso6392': u'roh', 'iso6391': u'rm', 'T': u''},
        "romany" : {'iso6392': u'rom', 'iso6391': u'', 'T': u''},
        "rundi" : {'iso6392': u'run', 'iso6391': u'rn', 'T': u''},
        "russian" : {'iso6392': u'rus', 'iso6391': u'ru', 'T': u''},
        "salishan languages" : {'iso6392': u'sal', 'iso6391': u'', 'T': u''},
        "samaritan aramaic" : {'iso6392': u'sam', 'iso6391': u'', 'T': u''},
        "sami languages" : {'iso6392': u'smi', 'iso6391': u'', 'T': u''},
        "samoan" : {'iso6392': u'smo', 'iso6391': u'sm', 'T': u''},
        "sandawe" : {'iso6392': u'sad', 'iso6391': u'', 'T': u''},
        "sango" : {'iso6392': u'sag', 'iso6391': u'sg', 'T': u''},
        "sanskrit" : {'iso6392': u'san', 'iso6391': u'sa', 'T': u''},
        "santali" : {'iso6392': u'sat', 'iso6391': u'', 'T': u''},
        "sardinian" : {'iso6392': u'srd', 'iso6391': u'sc', 'T': u''},
        "sasak" : {'iso6392': u'sas', 'iso6391': u'', 'T': u''},
        "scots" : {'iso6392': u'sco', 'iso6391': u'', 'T': u''},
        "selkup" : {'iso6392': u'sel', 'iso6391': u'', 'T': u''},
        "semitic languages" : {'iso6392': u'sem', 'iso6391': u'', 'T': u''},
        "serbian" : {'iso6392': u'srp', 'iso6391': u'sr', 'T': u''},
        "serer" : {'iso6392': u'srr', 'iso6391': u'', 'T': u''},
        "shan" : {'iso6392': u'shn', 'iso6391': u'', 'T': u''},
        "shona" : {'iso6392': u'sna', 'iso6391': u'sn', 'T': u''},
        "sichuan yi; nuosu" : {'iso6392': u'iii', 'iso6391': u'ii', 'T': u''},
        "sicilian" : {'iso6392': u'scn', 'iso6391': u'', 'T': u''},
        "sidamo" : {'iso6392': u'sid', 'iso6391': u'', 'T': u''},
        "sign languages" : {'iso6392': u'sgn', 'iso6391': u'', 'T': u''},
        "siksika" : {'iso6392': u'bla', 'iso6391': u'', 'T': u''},
        "sindhi" : {'iso6392': u'snd', 'iso6391': u'sd', 'T': u''},
        "sinhala; sinhalese" : {'iso6392': u'sin', 'iso6391': u'si', 'T': u''},
        "sino-tibetan languages" : {'iso6392': u'sit', 'iso6391': u'', 'T': u''},
        "siouan languages" : {'iso6392': u'sio', 'iso6391': u'', 'T': u''},
        "skolt sami" : {'iso6392': u'sms', 'iso6391': u'', 'T': u''},
        "slave (athapascan)" : {'iso6392': u'den', 'iso6391': u'', 'T': u''},
        "slavic languages" : {'iso6392': u'sla', 'iso6391': u'', 'T': u''},
        "slovak" : {'iso6392': u'slo', 'iso6391': u'sk', 'T': u'slk'},
        "slovenian" : {'iso6392': u'slv', 'iso6391': u'sl', 'T': u''},
        "sogdian" : {'iso6392': u'sog', 'iso6391': u'', 'T': u''},
        "somali" : {'iso6392': u'som', 'iso6391': u'so', 'T': u''},
        "songhai languages" : {'iso6392': u'son', 'iso6391': u'', 'T': u''},
        "soninke" : {'iso6392': u'snk', 'iso6391': u'', 'T': u''},
        "sorbian languages" : {'iso6392': u'wen', 'iso6391': u'', 'T': u''},
        "sotho, southern" : {'iso6392': u'sot', 'iso6391': u'st', 'T': u''},
        "south american indian (other)" : {'iso6392': u'sai', 'iso6391': u'', 'T': u''},
        "southern altai" : {'iso6392': u'alt', 'iso6391': u'', 'T': u''},
        "southern sami" : {'iso6392': u'sma', 'iso6391': u'', 'T': u''},
        "spanish; castilian" : {'iso6392': u'spa', 'iso6391': u'es', 'T': u''},
        "sranan tongo" : {'iso6392': u'srn', 'iso6391': u'', 'T': u''},
        "standard moroccan tamazight" : {'iso6392': u'zgh', 'iso6391': u'', 'T': u''},
        "sukuma" : {'iso6392': u'suk', 'iso6391': u'', 'T': u''},
        "sumerian" : {'iso6392': u'sux', 'iso6391': u'', 'T': u''},
        "sundanese" : {'iso6392': u'sun', 'iso6391': u'su', 'T': u''},
        "susu" : {'iso6392': u'sus', 'iso6391': u'', 'T': u''},
        "swahili" : {'iso6392': u'swa', 'iso6391': u'sw', 'T': u''},
        "swati" : {'iso6392': u'ssw', 'iso6391': u'ss', 'T': u''},
        "swedish" : {'iso6392': u'swe', 'iso6391': u'sv', 'T': u''},
        "swiss german; alemannic; alsatian" : {'iso6392': u'gsw', 'iso6391': u'', 'T': u''},
        "syriac" : {'iso6392': u'syr', 'iso6391': u'', 'T': u''},
        "tagalog" : {'iso6392': u'tgl', 'iso6391': u'tl', 'T': u''},
        "tahitian" : {'iso6392': u'tah', 'iso6391': u'ty', 'T': u''},
        "tai languages" : {'iso6392': u'tai', 'iso6391': u'', 'T': u''},
        "tajik" : {'iso6392': u'tgk', 'iso6391': u'tg', 'T': u''},
        "tamashek" : {'iso6392': u'tmh', 'iso6391': u'', 'T': u''},
        "tamil" : {'iso6392': u'tam', 'iso6391': u'ta', 'T': u''},
        "tatar" : {'iso6392': u'tat', 'iso6391': u'tt', 'T': u''},
        "telugu" : {'iso6392': u'tel', 'iso6391': u'te', 'T': u''},
        "tereno" : {'iso6392': u'ter', 'iso6391': u'', 'T': u''},
        "tetum" : {'iso6392': u'tet', 'iso6391': u'', 'T': u''},
        "thai" : {'iso6392': u'tha', 'iso6391': u'th', 'T': u''},
        "tibetan" : {'iso6392': u'tib', 'iso6391': u'bo', 'T': u'bod'},
        "tigre" : {'iso6392': u'tig', 'iso6391': u'', 'T': u''},
        "tigrinya" : {'iso6392': u'tir', 'iso6391': u'ti', 'T': u''},
        "timne" : {'iso6392': u'tem', 'iso6391': u'', 'T': u''},
        "tiv" : {'iso6392': u'tiv', 'iso6391': u'', 'T': u''},
        "tlingit" : {'iso6392': u'tli', 'iso6391': u'', 'T': u''},
        "tok pisin" : {'iso6392': u'tpi', 'iso6391': u'', 'T': u''},
        "tokelau" : {'iso6392': u'tkl', 'iso6391': u'', 'T': u''},
        "tonga (nyasa)" : {'iso6392': u'tog', 'iso6391': u'', 'T': u''},
        "tonga (tonga islands)" : {'iso6392': u'ton', 'iso6391': u'to', 'T': u''},
        "tsimshian" : {'iso6392': u'tsi', 'iso6391': u'', 'T': u''},
        "tsonga" : {'iso6392': u'tso', 'iso6391': u'ts', 'T': u''},
        "tswana" : {'iso6392': u'tsn', 'iso6391': u'tn', 'T': u''},
        "tumbuka" : {'iso6392': u'tum', 'iso6391': u'', 'T': u''},
        "tupi languages" : {'iso6392': u'tup', 'iso6391': u'', 'T': u''},
        "turkish" : {'iso6392': u'tur', 'iso6391': u'tr', 'T': u''},
        "turkish, ottoman (1500-1928)" : {'iso6392': u'ota', 'iso6391': u'', 'T': u''},
        "turkmen" : {'iso6392': u'tuk', 'iso6391': u'tk', 'T': u''},
        "tuvalu" : {'iso6392': u'tvl', 'iso6391': u'', 'T': u''},
        "tuvinian" : {'iso6392': u'tyv', 'iso6391': u'', 'T': u''},
        "twi" : {'iso6392': u'twi', 'iso6391': u'tw', 'T': u''},
        "udmurt" : {'iso6392': u'udm', 'iso6391': u'', 'T': u''},
        "ugaritic" : {'iso6392': u'uga', 'iso6391': u'', 'T': u''},
        "uighur; uyghur" : {'iso6392': u'uig', 'iso6391': u'ug', 'T': u''},
        "ukrainian" : {'iso6392': u'ukr', 'iso6391': u'uk', 'T': u''},
        "umbundu" : {'iso6392': u'umb', 'iso6391': u'', 'T': u''},
        "uncoded languages" : {'iso6392': u'mis', 'iso6391': u'', 'T': u''},
        "undetermined" : {'iso6392': u'und', 'iso6391': u'', 'T': u''},
        "upper sorbian" : {'iso6392': u'hsb', 'iso6391': u'', 'T': u''},
        "urdu" : {'iso6392': u'urd', 'iso6391': u'ur', 'T': u''},
        "uzbek" : {'iso6392': u'uzb', 'iso6391': u'uz', 'T': u''},
        "vai" : {'iso6392': u'vai', 'iso6391': u'', 'T': u''},
        "venda" : {'iso6392': u'ven', 'iso6391': u've', 'T': u''},
        "vietnamese" : {'iso6392': u'vie', 'iso6391': u'vi', 'T': u''},
        u"volap\xfck" : {'iso6392': u'vol', 'iso6391': u'vo', 'T': u''},
        "votic" : {'iso6392': u'vot', 'iso6391': u'', 'T': u''},
        "wakashan languages" : {'iso6392': u'wak', 'iso6391': u'', 'T': u''},
        "walamo" : {'iso6392': u'wal', 'iso6391': u'', 'T': u''},
        "walloon" : {'iso6392': u'wln', 'iso6391': u'wa', 'T': u''},
        "waray" : {'iso6392': u'war', 'iso6391': u'', 'T': u''},
        "washo" : {'iso6392': u'was', 'iso6391': u'', 'T': u''},
        "welsh" : {'iso6392': u'wel', 'iso6391': u'cy', 'T': u'cym'},
        "western frisian" : {'iso6392': u'fry', 'iso6391': u'fy', 'T': u''},
        "wolof" : {'iso6392': u'wol', 'iso6391': u'wo', 'T': u''},
        "xhosa" : {'iso6392': u'xho', 'iso6391': u'xh', 'T': u''},
        "yakut" : {'iso6392': u'sah', 'iso6391': u'', 'T': u''},
        "yao" : {'iso6392': u'yao', 'iso6391': u'', 'T': u''},
        "yapese" : {'iso6392': u'yap', 'iso6391': u'', 'T': u''},
        "yiddish" : {'iso6392': u'yid', 'iso6391': u'yi', 'T': u''},
        "yoruba" : {'iso6392': u'yor', 'iso6391': u'yo', 'T': u''},
        "yupik languages" : {'iso6392': u'ypk', 'iso6391': u'', 'T': u''},
        "zande languages" : {'iso6392': u'znd', 'iso6391': u'', 'T': u''},
        "zapotec" : {'iso6392': u'zap', 'iso6391': u'', 'T': u''},
        "zaza; dimili; dimli; kirdki; kirmanjki; zazaki" : {'iso6392': u'zza', 'iso6391': u'', 'T': u''},
        "zenaga" : {'iso6392': u'zen', 'iso6391': u'', 'T': u''},
        "zhuang; chuang" : {'iso6392': u'zha', 'iso6391': u'za', 'T': u''},
        "zulu" : {'iso6392': u'zul', 'iso6391': u'zu', 'T': u''},
        "zuni" : {'iso6392': u'zun', 'iso6391': u'', 'T': u''}
    }

    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower in ["language"]
    
    def validate(self, datatype, lang, *args, **kwargs):
        r = plugin.ValidationResponse()
        return self.validate_format(datatype, lang, validation_response=r)
    
    def validate_format(self, datatype, lang, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        
        info = self.langs.get(lang.lower())
        possibles = []
        if info is None:
            for k, v in self.langs.iteritems():
                if lang in k:
                    possibles.append(k)
        
        if info is None and len(possibles) == 0:
            r.warn("Unable to locate language in list of common language names")
        
        if info is not None:
            if info.get("iso6391", "") != "":
                r.info("ISO-639-1 language code for this language is " + info.get("iso6391"))
                r.alternative(info.get("iso6391"))
            if info.get("iso6392", "") != "":
                r.info("ISO-639-2 language code for this language is " + info.get("iso6392"))
                r.alternative(info.get("iso6392"))
        
        if len(possibles) > 0:
            r.warn("Could not get an exact match for this language in list of common language names, but a partial match was found")
            for possible in possibles:
                i = self.langs.get(possible)
                r.alternative(possible)
                if i.get("iso6391", "") != "":
                    r.info("ISO-639-1 language code for this language is " + i.get("iso6391"))
                    r.alternative(i.get("iso6391"))
                if i.get("iso6392", "") != "":
                    r.info("ISO-639-2 language code for this language is " + i.get("iso6392"))
                    r.alternative(i.get("iso6392"))
        
        return r
    
        
