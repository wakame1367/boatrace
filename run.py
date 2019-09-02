import argparse
import numpy as np
from pathlib import Path

import pandas as pd

from boatrace.parser import StartTable
from boatrace.util import Config


def get_arguments():
    _parser = argparse.ArgumentParser()
    _parser.add_argument("lzh_path", type=str)
    _args = _parser.parse_args()
    return _args


def main():
    args = get_arguments()
    config = Config(Path("boatrace/params.yaml"))
    root_path = Path(args.lzh_path)
    # unlzh(root_path)
    data = []
    for idx, path in enumerate(root_path.glob("*.TXT")):
        st = StartTable(path=path)
        df = st.preprocess()
        data.append(df)

    new_df = pd.concat(data, ignore_index=True)
    print(new_df.shape)
    print(new_df.head())
    print(new_df.isnull().sum())
    print(new_df.columns)

    seed = 20190801
    max_position = 4
    lgbm_params = {
        'task': 'train',
        'boosting_type': 'gbdt',
        'objective': 'lambdarank',
        'metric': 'ndcg',  # for lambdarank
        'ndcg_eval_at': [3],  # for lambdarank
        'max_position': max_position,  # for lambdarank
        'learning_rate': 1e-3,
        'min_data': 1,
        'min_data_in_bin': 1,
    }

    all_data = new_df[new_df["field_name"] == 1]

    train_query = (("2016-01-01" <= all_data["date"]) & (
            all_data["date"] <= "2017-12-31"))
    val_query = (("2018-01-01" <= all_data["date"]) & (
            all_data["date"] <= "2018-8-31"))
    test_query = (("2018-08-31" <= all_data["date"]) & (
            all_data["date"] <= "2018-10-31"))

    train = all_data[train_query]
    valid = all_data[val_query]
    test = all_data[test_query]
    tr_length, val_length, test_length = train.shape[0], valid.shape[0], \
                                         test.shape[0]
    print(tr_length, val_length, test_length)

    drop_cols = ["date", "field_name"]

    tr_target = np.array(list(range(1, 7)) * (tr_length // 6))
    val_target = np.array(list(range(1, 7)) * (val_length // 6))


if __name__ == '__main__':
    main()
