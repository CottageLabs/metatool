import xml.etree.cElementTree as cetree
import json

pmids = []
issns = []
names = []

outfile = "/home/richard/MedLine/json/medline11n0653.json"
filepath = "/home/richard/MedLine/xml/medline11n0653.xml"

tree = cetree.parse(filepath)
root = tree.getroot()

pmids = []
records = []
for mlc in root.findall("MedlineCitation"):
    record = {"electronic_issn" : [], "print_issn" : [], "issn" : [], "journal_name" : [], "journal_abbr" : []}
    
    # record any pubmed ids that we encounter
    pmidels = mlc.findall("PMID")
    for e in pmidels:
        if e.text not in pmids:
            pmids.append(e.text)
    
    article = mlc.find("Article")
    journal = article.find("Journal")
    
    # record any ISSNs in their appropriate type field
    issnels = journal.findall("ISSN")
    for e in issnels:
        if e.get("IssnType") == "Electronic":
            if e.text not in record["electronic_issn"]:
                record["electronic_issn"].append(e.text)
            if e.text in record["issn"]:
                record["issn"].remove(e.text)
        elif e.get("IssnType") == "Print":
            if e.text not in record["print_issn"]:
                record["print_issn"].append(e.text)
            if e.text in record["issn"]:
                record["issn"].remove(e.text)
        else:
            if e.text not in record["issn"]:
                record["issn"].append(e.text)
    
    # add journal titles
    titlels = journal.findall("Title")
    for e in titlels:
        if e.text not in record["journal_name"]:
            record["journal_name"].append(e.text)
    
    # add journal abbreviations
    isoels = journal.findall("ISOAbbreviation")
    for e in isoels:
        if e.text not in record["journal_abbr"]:
            record["journal_abbr"].append(e.text)
    
    info = mlc.find("MedlineJournalInfo")
    
    # record medline's version of the name (which may well be the iso abbreviation)
    taels = info.findall("MedlineTA")
    for e in taels:
        if e.text not in record["journal_name"] and e.text not in record["journal_abbr"]:
            record["journal_abbr"].append(e.text)
    
    # record the medline knowledge of this other issn - we don't necessarily know what type it is
    links = info.findall("ISSNLinking")
    for e in links:
        if e.text not in record["electronic_issn"] and e.text not in record["print_issn"] and e.text not in record["issn"]:
            record["issn"].append(e.text)
    
    records.append(record)

f = open(outfile, "w")
f.write(json.dumps(records))
f.close()
