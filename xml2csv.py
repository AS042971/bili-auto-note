from xml.dom import minidom
import datetime
import sys

def parseFile(filename: str):
    xml_file = minidom.parse(filename)
    root = xml_file.documentElement
    # start_time = 0

    dm_list = []
    sc_list = []

    for node in root.childNodes:
        # if node.nodeName == 'BililiveRecorderRecordInfo':
        #     time_str = node.attributes['start_time'].value
        #     time = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f0%z")
        #     start_time = time.timestamp()
        if node.nodeName == 'd' and node.childNodes:
            param = node.attributes['p'].value
            params = param.split(',')
            user = node.attributes['user'].value
            content = node.childNodes[0].data
            delta = float(params[0])
            dm_list.append((delta, user, content))
        if node.nodeName == 'sc' and node.childNodes:
            delta = float(node.attributes['ts'].value)
            user = node.attributes['user'].value
            if (node.childNodes):
                content = node.childNodes[0].data
            else:
                content = '(空白SC)'
            sc_list.append((delta, user, content))
    with open('dm.csv', "w", encoding="utf-8-sig") as f:
        for item in dm_list:
            m, s = divmod(item[0], 60)
            h, m = divmod(m, 60)
            time_str ="%02d:%02d:%02d" % (h, m, s)
            f.write(f"{time_str},{item[1].replace(',','，')},{item[2].replace(',','，')}\n")
    with open('sc.csv', "w", encoding="utf-8-sig") as f:
        for item in sc_list:
            m, s = divmod(item[0], 60)
            h, m = divmod(m, 60)
            time_str ="%02d:%02d:%02d" % (h, m, s)
            f.write(f"{time_str},{item[1].replace(',','，')},{item[2].replace(',','，')}\n")

if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        print(f'Usage: xml2csv path_to.xml')
        sys.exit(-1)
    else:
        parseFile(sys.argv[1])
