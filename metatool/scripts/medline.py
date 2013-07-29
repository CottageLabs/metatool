import xml.etree.cElementTree as cetree

pmids = []
issns = []
names = []

filepath = "/home/richard/MedLine/xml/medline11n0653.xml"

tree = cetree.parse(filepath)
root = tree.getroot()

# brute force inspection of every element - this won't work when
# we want to get structured data out, but it will do as a first experiment
for element in root.iter():
    # PMID
    if element.tag == "PMID":
        if element.text not in pmids:
            pmids.append(element.text)
    
    # ISSN
    if element.tag == "ISSN" or element.tag == "ISSNLinking":
        if element.text not in issns:
            issns.append(element.text)
    
    # Title
    if element.tag == "Title" or element.tag == "ISOAbbreviation" or element.tag == "MedlineTA":
        if element.text not in names:
            names.append(element.text)
