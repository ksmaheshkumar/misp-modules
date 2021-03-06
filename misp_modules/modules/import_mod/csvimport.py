# -*- coding: utf-8 -*-
import json, os, base64
import pymisp

misperrors = {'error': 'Error'}
mispattributes = {'inputSource': ['file'], 'output': ['MISP attributes']}
moduleinfo = {'version': '0.1', 'author': 'Christian Studer',
              'description': 'Import Attributes from a csv file.',
              'module-type': ['import']}
moduleconfig = ['header']

duplicatedFields = {'mispType': {'mispComment': 'comment'},
                    'attrField': {'attrComment': 'comment'}}

class CsvParser():
    def __init__(self, header):
        self.header = header
        self.attributes = []

    def parse_data(self, data):
        return_data = []
        for line in data:
            l = line.split('#')[0].strip() if '#' in line else line.strip()
            if l:
                return_data.append(l)
        self.data = return_data
        # find which delimiter is used
        self.delimiter, self.length = self.findDelimiter()

    def findDelimiter(self):
        n = len(self.header)
        if n > 1:
            tmpData = []
            for da in self.data:
                tmp = []
                for d in (';', '|', '/', ',', '\t', '    ',):
                    if da.count(d) == (n-1):
                        tmp.append(d)
                if len(tmp) == 1 and tmp == tmpData:
                    return tmpData[0], n
                else:
                    tmpData = tmp
        else:
            return None, 1

    def buildAttributes(self):
        # if there is only 1 field of data
        if self.delimiter is None:
            mispType = self.header[0]
            for data in self.data:
                d = data.strip()
                if d:
                    self.attributes.append({'types': mispType, 'values': d})
        else:
            # split fields that should be recognized as misp attribute types from the others
            list2pop, misp, head = self.findMispTypes()
            # for each line of data
            for data in self.data:
                datamisp = []
                datasplit = data.split(self.delimiter)
                # in case there is an empty line or an error
                if len(datasplit) != self.length:
                    continue
                # pop from the line data that matches with a misp type, using the list of indexes
                for l in list2pop:
                    datamisp.append(datasplit.pop(l).strip())
                # for each misp type, we create an attribute
                for m, dm in zip(misp, datamisp):
                    attribute = {'types': m, 'values': dm}
                    for h, ds in zip(head, datasplit):
                        if h:
                            attribute[h] = ds.strip()
                    self.attributes.append(attribute)

    def findMispTypes(self):
        descFilename = os.path.join(pymisp.__path__[0], 'data/describeTypes.json')
        with open(descFilename, 'r') as f:
            MispTypes = json.loads(f.read())['result'].get('types')
        list2pop = []
        misp = []
        head = []
        for h in reversed(self.header):
            n = self.header.index(h)
            # fields that are misp attribute types
            if h in MispTypes:
                list2pop.append(n)
                misp.append(h)
            # handle confusions between misp attribute types and attribute fields
            elif h in duplicatedFields['mispType']:
                # fields that should be considered as misp attribute types
                list2pop.append(n)
                misp.append(duplicatedFields['mispType'].get(h))
            elif h in duplicatedFields['attrField']:
                # fields that should be considered as attribute fields
                head.append(duplicatedFields['attrField'].get(h))
            # otherwise, it is an attribute field
            else:
                head.append(h)
        # return list of indexes of the misp types, list of the misp types, remaining fields that will be attribute fields
        return list2pop, misp, list(reversed(head))

def handler(q=False):
    if q is False:
        return False
    request = json.loads(q)
    if request.get('data'):
        data = base64.b64decode(request['data']).decode('utf-8')
    else:
        misperrors['error'] = "Unsupported attributes type"
        return misperrors
    if not request.get('config') and not request['config'].get('header'):
        misperrors['error'] = "Configuration error"
        return misperrors
    config = request['config'].get('header').split(',')
    config = [c.strip() for c in config]
    csv_parser = CsvParser(config)
    csv_parser.parse_data(data.split('\n'))
    # build the attributes
    csv_parser.buildAttributes()
    r = {'results': csv_parser.attributes}
    return r

def introspection():
    return mispattributes

def version():
    moduleinfo['config'] = moduleconfig
    return moduleinfo
