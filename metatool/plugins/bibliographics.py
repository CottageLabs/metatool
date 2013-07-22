import plugin as plugin
import re

class ISSN(plugin.Plugin):
    rx_1 = "\d{4}-\d{3}[0-9X]"
    rx_2 = "\d{7}[0-9X]"
    
    def supports(self, datatype, *args, **kwargs):
        return datatype.lower() == "issn"
    
    def run(self, issn, *args, **kwargs):
        r = plugin.ValidationResponse(self.__name__)
        
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
        checkon = digits[:7]
        
        total = 0
        multiplier = 8
        for c in checkon:
            total += int(c) * multiplier
            multiplier -= 1
        
        remainder = total % 11
        
        if remainder == 0:
            return "0"
        check = 11 - remainder
        if check == 10:
            return "X"
        return str(check)
