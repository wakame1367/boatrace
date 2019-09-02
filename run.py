import argparse
import re
import numpy as np
import lightgbm as lgb
import pandas as pd
from pathlib import Path

from boatrace.parser import StartTable, RaceResult
from boatrace.util import Config


def get_arguments():
    _parser = argparse.ArgumentParser()
    _parser.add_argument("lzh_path", type=str)
    _args = _parser.parse_args()
    return _args


# https://stackoverflow.com/questions/12093940/
# reading-files-in-a-particular-order-in-python
def numerical_sort(value):
    numbers = re.compile(r'(\d+)')
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts


def main():
    args = get_arguments()
    config = Config(Path("boatrace/params.yaml"))
    root_path = Path(args.lzh_path)
    root_path2 = Path("resources/download_raceresult")
    race_info_paths = sorted(root_path.glob("*.TXT"),
                             key=lambda x: numerical_sort(x.stem))
    race_result_paths = sorted(root_path2.glob("*.TXT"),
                               key=lambda x: numerical_sort(x.stem))
    # unlzh(root_path)
    data = []
    stop = "141231"
    for race_info_path, race_result_path in zip(race_info_paths,
                                                race_result_paths):
        st = StartTable(path=race_info_path).preprocess()
        rr = RaceResult(path=race_result_path).preprocess()
        df = st.merge(rr, on=["date", "field_name", "race_idx",
                              "registration_number"])
        data.append(df)
        if stop in race_info_path.stem:
            break

    new_df = pd.concat(data, ignore_index=True)
    print(new_df.shape)
    print(new_df.head())
    print(new_df.isnull().sum())
    print(new_df.columns)

    seed = 20190801
    max_position = 4
    players = 6
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

    train_query = (("2013-01-01" <= all_data["date"]) & (
            all_data["date"] <= "2013-12-31"))
    val_query = (("2014-01-01" <= all_data["date"]) & (
            all_data["date"] <= "2014-8-31"))
    test_query = (("2014-08-31" <= all_data["date"]) & (
            all_data["date"] <= "2014-10-31"))

    train = all_data[train_query]
    valid = all_data[val_query]
    test = all_data[test_query]
    tr_length, val_length, test_length = train.shape[0], valid.shape[0], \
                                         test.shape[0]
    print(tr_length, val_length, test_length)
    tr_target = train["rank"]
    val_target = valid["rank"]
    te_target = test["rank"]
    drop_cols = ["date", "field_name", "race_idx", "rank"]

    train.drop(columns=drop_cols, inplace=True)
    valid.drop(columns=drop_cols, inplace=True)
    test.drop(columns=drop_cols, inplace=True)
    for col in train.columns:
        train[col] = train[col].astype(int)

    for col in valid.columns:
        valid[col] = valid[col].astype(int)
    cat_feature_idx = [idx for idx, col in enumerate(train.columns)
                       if col in ["registration_number", "mortar", "board"]]

    lgb_train = lgb.Dataset(train, tr_target,
                            categorical_feature=cat_feature_idx,
                            group=np.array([players] * (tr_length // players)))
    lgb_valid = lgb.Dataset(valid, val_target,
                            categorical_feature=cat_feature_idx,
                            group=np.array([players] * (val_length // players)))

    lgb_clf = lgb.train(
        lgbm_params,
        lgb_train,
        categorical_feature=cat_feature_idx,
        num_boost_round=2000,
        valid_sets=[lgb_train, lgb_valid],
        valid_names=['train', 'valid'],
        early_stopping_rounds=200,
        verbose_eval=1
    )

    lgb_model_cv = lgb.cv(
        lgbm_params,
        lgb_train,
        categorical_feature=cat_feature_idx,
        num_boost_round=5000,
        # valid_sets=[lgb_train, lgb_valid],
        # valid_names=['train','valid'],
        early_stopping_rounds=400,
        verbose_eval=1,
        nfold=5,
        shuffle=True,
        seed=42
    )


if __name__ == '__main__':
    main()
