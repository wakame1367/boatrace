import argparse
import re
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from boatrace.parser import StartTable, RaceResult
from boatrace.util import Config


def get_arguments():
    _parser = argparse.ArgumentParser()
    _parser.add_argument("lzh_path", type=str)
    _args = _parser.parse_args()
    return _args


# reference:
# https://www.kaggle.com/kenmatsu4/
# using-trained-booster-from-lightgbm-cv-w-callback
class ModelExtractionCallback:
    """Callback class for retrieving trained model from lightgbm.cv()
    NOTE: This class depends on '_CVBooster' which is hidden class, so it might doesn't work if the specification is changed.
    """

    def __init__(self):
        self._model = None

    def __call__(self, env):
        # Saving _CVBooster object.
        self._model = env.model

    def _assert_called_cb(self):
        if self._model is None:
            # Throw exception if the callback class is not called.
            raise RuntimeError('callback has not called yet')

    @property
    def boosters_proxy(self):
        self._assert_called_cb()
        # return Booster object
        return self._model

    @property
    def raw_boosters(self):
        self._assert_called_cb()
        # return list of Booster
        return self._model.boosters

    @property
    def best_iteration(self):
        self._assert_called_cb()
        # return boosting round when early stopping.
        return self._model.best_iteration


# https://stackoverflow.com/questions/12093940/
# reading-files-in-a-particular-order-in-python
def numerical_sort(value):
    numbers = re.compile(r'(\d+)')
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts


def lgb_cv(df, field_code, rank2win_points, lgb_params, players=6):
    all_data = df[df["field_name"] == field_code]
    all_data["rank"] = all_data["rank"].map(rank2win_points)
    train_query = (("2013-01-01" <= all_data["date"]) & (
            all_data["date"] <= "2017-12-31"))
    val_query = (("2018-01-01" <= all_data["date"]) & (
            all_data["date"] <= "2018-8-31"))
    test_query = (("2018-08-31" <= all_data["date"]) & (
            all_data["date"] <= "2018-10-31"))

    train = all_data[train_query]
    valid = all_data[val_query]
    test = all_data[test_query]
    test.to_csv("resources/test_{}.csv".format(field_code), index=False)
    tr_length, val_length, test_length = train.shape[0], valid.shape[0], \
                                         test.shape[0]
    print(tr_length, val_length, test_length)
    tr_target = train["rank"]
    val_target = valid["rank"]
    te_target = test["rank"]
    drop_cols = ["date", "field_name", "race_idx", "rank"]

    tr_group = np.array([players] * (tr_length // players))
    val_group = np.array([players] * (val_length // players))
    train.drop(columns=drop_cols, inplace=True)
    valid.drop(columns=drop_cols, inplace=True)
    test.drop(columns=drop_cols, inplace=True)

    print(train.shape)
    print(valid.shape)
    print(tr_group.shape)
    print(val_group.shape)

    for col in train.columns:
        train[col] = train[col].astype(int)

    for col in valid.columns:
        valid[col] = valid[col].astype(int)
    cat_feature_idx = [idx for idx, col in enumerate(train.columns)
                       if col in ["registration_number", "mortar", "board"]]

    lgb_train = lgb.Dataset(train, tr_target,
                            categorical_feature=cat_feature_idx,
                            group=tr_group)
    lgb_valid = lgb.Dataset(valid, val_target,
                            categorical_feature=cat_feature_idx,
                            group=val_group)

    lgb_clf = lgb.train(
        lgb_params,
        lgb_train,
        categorical_feature=cat_feature_idx,
        num_boost_round=2000,
        valid_sets=[lgb_train, lgb_valid],
        valid_names=['train', 'valid'],
        early_stopping_rounds=200,
        verbose_eval=1
    )

    lgb_clf.save_model("resources/model/model_{}.txt".format(field_code),
                       num_iteration=lgb_clf.best_iteration)

    extraction_cb = ModelExtractionCallback()
    callbacks = [
        extraction_cb,
    ]

    lgb_model_cv = lgb.cv(
        lgb_params,
        lgb_train,
        categorical_feature=cat_feature_idx,
        num_boost_round=5000,
        # valid_sets=[lgb_train, lgb_valid],
        # valid_names=['train','valid'],
        early_stopping_rounds=400,
        verbose_eval=1,
        nfold=5,
        shuffle=True,
        seed=42,
        callbacks=callbacks
    )

    # Retrieving booster and training information.
    proxy = extraction_cb.boosters_proxy
    boosters = extraction_cb.raw_boosters
    best_iteration = extraction_cb.best_iteration

    for i, booster in enumerate(boosters):
        booster.save_model("resources/model_{}_cv_{}.txt".format(field_code, i),
                           num_iteration=best_iteration)


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
    stop = "181231"
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
    rank2win_points = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2, 6: 1}
    for code in config.get_field_code().values():
        lgb_cv(new_df, code, rank2win_points, lgbm_params, players)


if __name__ == '__main__':
    main()
