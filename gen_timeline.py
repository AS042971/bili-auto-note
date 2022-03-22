import sys
import json

def main(config_path: str):
    with open(config_path,'r',encoding='utf8') as fp:
        json_data = json.load(fp)
        print(json_data)

if __name__ == '__main__':
    # add default config filepath
    if len(sys.argv) == 1:
        st = "./config/gen_timeline.json"
        print(f'Loading default config file: {st}')
        try:
            with open(st, "r", encoding="utf-8") as f:
                pass
            print(f'Successfully loaded {st}')
        except FileNotFoundError as e_f:
            print(e_f)
            print('Usage: gen_timeline.py <path to config file>')
            sys.exit(-1)
    else:
        st = sys.argv[1]

    main(st)
