import csv
import os
import random
from lxml import etree
import requests, json

try:
    from metatool import metatool
except ImportError:
    import metatool

try:
    from metatool import config
except ImportError:
    import config

try:
    from metatool.models import Publication
except ImportError:
    from models import Publication


primary_fields = ['author', 'cfFedId/doi', 'cfTitle', 'cfFedId/issn', 'cfFedId/pubmed', 'cfFedId/handle', 'cfFedId/isbn', 'publisher_name', 'journal_title']
secondary_fields = ['cfResPublDate', 'cfResPubl_Class/rcuk:oa-policy-embargo-periods-scheme-uuid', 'cfTotalPages', 'cfStartPage', 'cfEndPage', 'cfVol']

static_fields = {
        'cfAbstr': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce tristique tellus vitae bibendum rhoncus. Donec ac imperdiet metus, a dapibus odio. Nullam eget risus et purus gravida cursus. ' * 7
}

# cfAbstract/cfLangCode - "secondary" but only if cfAbstr?
def generate_and_index(how_many):
    # limit the size of the lists somewhat, in order to get the same
    # values multiple times (e.g. multiple John Doe authors) - for
    # showcasing aggregation better
    global contributing_orgs, authors, titles, journal_titles, publishers
    contributing_org(); author(); title(); journal_title(); publisher();

    contributing_orgs = contributing_orgs[:how_many/200]
    authors = authors[:how_many/100]
    titles = titles[:how_many/10]
    journal_titles = journal_titles[:how_many/100]
    publishers = publishers[:how_many/200]

    for i in range(0, how_many):
        record = {}
        record['id'] = str(i)
        record['contributing_org'] = contributing_org()
        record['author'] = author()
        record['cfTitle'] = title()
        record['journal_title'] = journal_title()
        record['publisher_name'] = publisher()
        # add secondary fields to some of the records generated
        if random.random() > 0.5:
            record['cfTotalPages'] = random.randint(1,50)
        pub = Publication(**record)
        pub.save()


def contributing_org():
    contributing_orgs = _get_contributing_orgs()
    return contributing_orgs[ _pick(contributing_orgs) ]


read_contributing_orgs = False
contributing_orgs = []
def _get_contributing_orgs():
    global read_contributing_orgs, contributing_orgs

    if read_contributing_orgs:
        return contributing_orgs

    script_dir = os.path.dirname(__file__)
    filename = os.path.join(script_dir, '../resources/HE_org_names.json')
    with open(filename, 'rb') as f:
        contributing_orgs = json.loads(f.read())
    contributing_orgs = list(set(contributing_orgs)) # deduplicate, not sure if needed for this file

    read_contributing_orgs = True
    return contributing_orgs


def journal_title():
    journal_titles = _get_journal_titles()
    return journal_titles[ _pick(journal_titles) ]


read_journal_titles = False
journal_titles = []
def _get_journal_titles():
    global read_journal_titles, journal_titles

    if read_journal_titles:
        return journal_titles

    acat_journals = json.loads(requests.get(config.ES_HOST + '/acat/journal/_search?q=*&size=10000000').text)
    acat_journals = acat_journals['hits']['hits']
    for j in acat_journals:
        try:
            journal_titles += j['_source']['journal_title']
        except KeyError:
            continue
    journal_titles = list(set(journal_titles)) # deduplicate the flattened list of journal_title names

    read_journal_titles = True
    return journal_titles


def publisher():
    publishers = _get_publishers()
    return publishers[ _pick(publishers) ]


read_publishers = False
publishers = []
def _get_publishers():
    global read_publishers, publishers

    if read_publishers:
        return publishers

    acat_journals = json.loads(requests.get(config.ES_HOST + '/acat/journal/_search?q=*&size=10000000').text)
    acat_journals = acat_journals['hits']['hits']
    for j in acat_journals:
        try:
            publishers += j['_source']['publisher_name']
        except KeyError:
            continue
    publishers = list(set(publishers)) # deduplicate the flattened list of publisher names

    read_publishers = True
    return publishers


def author():
    authors = _get_authors()
    return authors[ _pick(authors) ]

read_authors = False
authors = []
def _get_authors():
    global read_authors, authors

    if read_authors:
        return authors

    script_dir = os.path.dirname(__file__)
    filename = os.path.join(script_dir, '../resources/medline11n0653.xml')
    root = etree.parse(filename)
    xml_authors = root.xpath('//Author')
    for xml_author in xml_authors:
        try:
            authors.append(xml_author.xpath('ForeName')[0].text + ' ' + xml_author.xpath('LastName')[0].text)
        except IndexError:
            continue

    read_authors = True
    return authors

def title():
    titles = _get_titles()
    return titles[ _pick(titles) ]

read_titles = False
titles = []
def _get_titles():
    global read_titles, titles

    if read_titles:
        return titles

    script_dir = os.path.dirname(__file__)
    filename = os.path.join(script_dir, '../resources/google_scholar_example_results.csv')
    with open(filename, 'rb') as f:
        c = csv.reader(f, delimiter='|')
        TITLE_COL = 0
        for row in c:
            titles.append(row[TITLE_COL].strip())

    read_titles = True
    return titles

def _pick(_list):
    return random.randint(0, len(_list) - 1)
