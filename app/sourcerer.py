'''
Author: Yaleesa Borgman
Date: 8-8-2019
simple sourcerer outside the scraper. merged later in life
'''

import requests, json, re, html
from requests_html import HTMLSession
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import xmltodict
import pandas as pd
from joblib import dump, load

from elasticer import Elasticer

NoneType = type(None)
'''
options for pandas
'''
pd.set_option("display.max_rows", 25)
pd.set_option('max_columns',10)
pd.set_option('display.width', 240)
pd.set_option('display.column_space', 18)

session = HTMLSession()


class SchemaFinder:
    '''
    finder for schema, json-ld & microdata
    '''
    def microdata_finder(self, url):
        schema = 'schema.org/JobPosting'

        try:
            r = session.get(url)
            html = r.html.search(schema)
            if not isinstance(html, NoneType):
                return "True"
            else:
                return "False"
        except Exception as exc:
            return f"Exception {exc}"

    def microdata_parser(self, url):
        r = session.get(url)
        itemprops = r.html.find('[itemprop]')
        response = []
        for element in itemprops:
            item = {}
            attr = element.attrs
            item['item'] = attr['itemprop']
            text = element.text
            if text is not '':
                item['text'] = text
            if 'content' in attr:
                item['content'] = attr['content']
            response.append(item)
        return response

    def json_ld(self, url):
        r = session.get(url)
        try:
            elements = r.html.xpath('//script[@type="application/ld+json"]')
            for unit in elements:
                text = unit.text
                text = text.replace('&#13;', '')
                json_text = json.loads(text)
                return json_text
        except Exception as err:
            return err


class UnstructeredText:
    '''
    would parse unstructured text, needs some intelligence
    '''
    def normal_parser(self, url):
        r = session.get(url)
        titles = r.html.xpath('//section//h1 | //section//h2 | //section//p | //section//ul', clean=True)
        # titles = r.html.find('h1', clean=True)
        # p = r.html.find('p', clean=True)
        # span = r.html.find('span', clean=True)
        # print([title.text for title in titles], [x.text for x in p], [sp.text for sp in span])
        # for unit, unit2, unit3 in titles, p, span:
        #     print(unit.text, unit2.text, unit3.text)

class XMLifier:
    def xml_parser(self, url):
        '''
        XML parser with ET, parses one layer
        '''
        r = requests.get(url)
        tree = ET.fromstring(r.text)
        count = 0
        unit = {}
        for job in tree.iter('JobDetails'):
            unit[count] = {}
            for job2 in job:
                unit[count].update({job2.tag: job2.text})

            count += 1
        print(count)
        return unit

    def xml_to_dict(self, url):
        '''
        XML parser for all of the childs
        '''
        r = requests.get(url)
        unit = xmltodict.parse(r.text)
        dumpling = json.dumps(unit)
        loading = json.loads(dumpling)
    
        list_unit = [listing['JobDetails'] for listing in loading['source']['JobPosition']]
        return list_unit

    def xml_to_frame(self, url):
        '''
        convert xml to dataframe and save it as json
        '''
        vacs = self.xml_parser(url)
        drop_list = ['companyLogo', 'Id', 'JobCompanyBranch', 'JobCompanyProfile' , 'JobMinDaysPerWeek', 'JobUrl', 'topjob', 'HoursWeek', 'country', 'JobParttime', 'DatePlaced']
        df = pd.DataFrame.from_dict(vacs, orient='index')

        df.drop(drop_list, inplace=True, axis=1)
        df.to_json('data/columns_xml_data.json', orient='records')


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        if '\n' in d:
            d = ' '       
        self.fed.append(d)
    def get_data(self):
        return ' '.join(self.fed)


class DescriptionCleaner:
    '''
    cleans description of any lingering HTML tags
    begin of splitting requirements and benefits (not finished)
    '''
    def __init__(self, dataset):
        self.dataset = dataset

    def splitter(self, text):
        try:
            text = text.split('<h4>')
            return text
        except Exception:
            return text

    def strip_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()

    def replace(self):
        for job in self.dataset:
            split = self.splitter(job['JobDescription']) #already there if i decide to split on responsibilities, qualifications & benefits
            job.update((k, ' '.join([self.strip_tags(text) for text in split])) for k, v in job.items() if k == "JobDescription")
        return self.dataset

