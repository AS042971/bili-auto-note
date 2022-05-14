from xml.dom import minidom
import datetime
import sys

def parseFile(filename: str):
    xml_file = minidom.parse(filename)
    root = xml_file.documentElement
    sc_list = []
    price = 0

    for node in root.childNodes:
        if node.nodeName == 'sc':
            delta = float(node.attributes['ts'].value)
            user = node.attributes['user'].value
            if (node.childNodes):
                content = node.childNodes[0].data
            else:
                content = '(空白SC)'
            duration = node.attributes['time'].value
            price += float(node.attributes['price'].value)
            sc_list.append((delta, user, content, duration))

    print(f'解析得到{len(sc_list)}条SC, 累计{price}元')

    with open('sc.txt', "w", encoding="utf-8-sig") as f:
        for item in sc_list:
            m, s = divmod(item[0], 60)
            h, m = divmod(m, 60)
            if (h == 0):
                time_str = "%02d:%02d" % (m, s)
            else:
                time_str ="%d:%02d:%02d" % (h, m, s)
            f.write(f"{time_str} @{item[1]}: {item[2]}*{item[3]}\n")

if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        print(f'Usage: xml2txt.py path_to.xml')
        sys.exit(-1)
    else:
        parseFile(sys.argv[1])
