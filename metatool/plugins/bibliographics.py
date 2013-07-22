import plugin as plugin
import re

class ISSN(plugin.Plugin):
    rx_1 = "\d{4}-\d{3}[0-9X]"
    rx_2 = "\d{7}[0-9X]"
    
    def supports(self, datatype, *args, **kwargs):
        return datatype.lower() == "issn"
    
    def run(self, issn, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # attempt format validation based on regular expressions first
        m = re.match(self.rx_1, issn)
        if m is None:
            m = re.match(self.rx_2, issn)
            if m is None:
                r.error("issn does not pass format check.  Should be in the form nnnn-nnnn")
                return r # we can't do any further validation
            else:
                r.warn("issn consists of 8 valid digits, but is not hyphenated; recommended form for issns in nnnn-nnnn")
        
        # if we get to here our issn at least consists of the right digits.  Now we can 
        # calculate the checksum ourselves
        checksum = self._checksum(issn)
        if checksum != issn[-1]:
            r.error("issn checksum digit does not match the calculated checksum")
        return r
        
        # we may go on after this to check for the issn in a database somewhere
    
    def _checksum(self, issn):
        digits = issn.replace("-", "")
        remainder = sum([int(b) * (8 - int(a)) for a, b in enumerate(digits) if a < 7]) % 11
        
        """
        total = 0
        multiplier = 8
        for c in checkon:
            total += int(c) * multiplier
            multiplier -= 1
        
        remainder = total % 11
        """
        
        if remainder == 0:
            return "0"
        check = 11 - remainder
        if check == 10:
            return "X"
        return str(check)



class ISBN(plugin.Plugin):
    rx_10 = "\d{9}[0-9X]"
    rx_13 = "\d{12}[0-9X]"

    def supports(self, datatype, *args, **kwargs):
        lower = datatype.lower()
        return lower == "isbn" or lower == "isbn10" or lower == "isbn13"
        
    def run(self, isbn, *args, **kwargs):
        r = plugin.ValidationResponse()
        
        # try to normalise out some of the isbn prefixes        
        norm = isbn.replace(" ", "").replace("-", "").lower()
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
            r.error("isbn checksum does not match calculated checksum")
        return r
    
    def _checksum10(self, isbn10):
        remainder = sum((10 - i) * (int(x)) for i, x in enumerate(isbn10) if i < 9) % 11
        
        if remainder == 0:
            return "0"
        check = 11 - remainder
        if check == 10:
            return "X"
        return str(check)
        
    def _checksum13(self, isbn13):
        remainder = (10 - (sum(int(digit) * (3 if idx % 2 else 1) for idx, digit in enumerate(isbn13[:12])) % 10)) % 10
        return str(remainder)
        
        
        
        
