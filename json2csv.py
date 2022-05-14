import sys
import json

def delta2str(delta: float) -> str:
    m, s = divmod(delta, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:%02d" % (h, m, s)

def parseFile(jsonl_path: str, csv_path: str):
    dm_cnt = 0
    total_cnt = 0
    start_time = None
    dm_list = []
    with open(jsonl_path, "r", encoding="utf-8") as ifile:
        while True:
            line = ifile.readline()
            total_cnt += 1
            if (total_cnt % 1000 == 0):
                print(f'已处理{dm_cnt} / {total_cnt}条数据')
            if not line:
                break

            if not start_time:
                # 首条数据，读取时间
                live_obj = json.loads(line)
                start_time = live_obj['live_time']

            if line[9:18] == 'DANMU_MSG':
                raw_dm_obj = json.loads(line)
                dm_cnt += 1
                info = raw_dm_obj['info']
                dm_time = info[0][4]
                delta_time = dm_time / 1000 - start_time
                content = info[1].strip()
                uid = info[2][0]
                uname = info[2][1]
                dm_list.append((delta_time, uid, uname, content))

    print(f'存储{dm_cnt}条弹幕中')

    with open(csv_path, "w", encoding="utf-8-sig") as f:
        for item in dm_list:
            # TODO: 根据UID访问B站API获得用户信息
            f.write(f"{delta2str(item[0])},{item[1]},{item[2].replace(',','，')},{item[3].replace(',','，')}\n")

if __name__ == '__main__':
    parseFile('./test.jsonl', './test.csv')
