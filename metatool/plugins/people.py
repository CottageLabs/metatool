import plugin
import orcid, re

class ORCID(plugin.Plugin):
    rx_1 = "(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])"
    rx_2 = "(\d{15}[0-9X])"

    def supports(self, datatype, **validation_options):
        lower = datatype.lower()
        return lower == "orcid"
    
    def validate(self, datatype, value, *args, **validation_options):
        r = plugin.ValidationResponse()
        
        # first do the format validation - layout, hyphenation, checksum, etc.
        # returns just the identifier part of the orcid if successful
        oid = self._format_validate(value, r)
        
        return self.validate_realism(datatype, value, validation_response=r, oid=oid)
        
    def validate_format(self, datatype, value, *args, **validation_options):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        oid = self._format_validate(value, r)
        return r
    
    def validate_realism(self, datatype, value, *args, **kwargs):
        r = kwargs.get("validation_response", plugin.ValidationResponse())
        oid = kwargs.get("oid", None)
        
        if oid is None:
            return r
        
        # now make a request to the ORCID service to see if this orcid is
        # resolvable
        author = orcid.get(oid)
        
        # FIXME: would be nice to error here, but we need to make sure that a
        # failure to connect to the orcid service does not cause a validation failure
        if author.orcid is None:
            r.warn("could not resolve orcid in the orcid database, so is highly likely to be wrong")
            return r
        
        # save the data we got back from orcid in case it is useful to the validator
        r.data = author._original_dict
        return r
    
    def _format_validate(self, orcid_string, r):
        correction_required = False
        
        # first let's see if there really is an orcid here, and validate it and correct it if necessary
        corrected_id = None
        m = re.search(self.rx_1, orcid_string)
        if m is None:
            m = re.search(self.rx_2, orcid_string)
            if m is not None:
                r.warn("Your orcid lacks hyphenation; preferred format for orcid is nnnn-nnnn-nnnn-nnnn")
                corrected_id = self._correct(m.groups()[0])
                correction_required = True
                
            else:
                r.error("Your orcid could not be validated - format is incorrect")
                return
        
        # get the properly formatted orcid
        oid = m.groups()[0] if corrected_id is None else corrected_id
        
        # do the checksum
        checksum = self._checksum(oid)
        if checksum != oid[-1]:
            r.error("The calculated checksum did not match the provided checksum")
            return
        
        # now check that the orcid has the relevant prefix
        # all orcids should start with http://orcid.org
        # they may also start with http://www.orcid.org, which would work but is technically incorrect
        if orcid_string.startswith("http://www.orcid.org"):
            r.warn("Your orcid starts with http://www.orcid.org/, which is ok-ish, but should really start with http://orcid.org")
            correction_required = True
            
        elif orcid_string.startswith("www.orcid.org"):
            r.warn("Your orcid starts with www.orcid.org which isn't right.  It might work, but it ought to start with http://orcid.org/")
            correction_required = True
            
        elif orcid_string.startswith("orcid.org"):
            r.warn("Your orcid starts with orcid.org, which is ok-ish, but should really start with http://orcid.org/")
            correction_required = True
        
        elif not orcid_string.startswith("http://orcid.org"):
            r.error("Your orcid does not begin with the required prefix: http://orcid.org/")
            correction_required = True
        
        # this may be a url with other things after it (orcid API permits this, for example)
        # so let's check
        if orcid_string[-1] not in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "X"]:
            r.error("There appears to have stuff beyond the end of the identifier")
            correction_required = True
        
        if correction_required:
            r.correction("http://orcid.org/" + oid)
        
        return oid
        
    def _checksum(self, orcid_string):
        norm = orcid_string.replace(" ", "").replace("-", "")
        digits = [a for i, a in enumerate(norm) if i < 15]
        total = 0
        for i in digits:
            total = (total + int(i)) * 2
        remainder = total % 11
        check = (12 - remainder) % 12
        
        if check == 10:
            return "X"
        else:
            return str(check)
    
    def _correct(self, s):
        return s[:4] + "-" + s[4:8] + "-" + s[8:12] + "-" + s[12:]
