import argparse
from pathlib import Path

import pandas as pd

from boatrace.parser import StartTable


def get_arguments():
    _parser = argparse.ArgumentParser()
    _parser.add_argument("lzh_path", type=str)
    _args = _parser.parse_args()
    return _args


def main():
    args = get_arguments()
    root_path = Path(args.lzh_path)
    # unlzh(root_path)
    data = []
    for path in root_path.glob("*.TXT"):
        st = StartTable(path=path)
        df = st.preprocess()
        data.append(df)
    new_df = pd.concat(data, ignore_index=True)


if __name__ == '__main__':
    main()
