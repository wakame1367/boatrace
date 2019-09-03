from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

model_path = Path("resources/model")


def main():
    test = pd.read_csv("resources/test.csv")
    drop_cols = ["date", "field_name", "race_idx", "rank"]
    rank2win_points = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2, 6: 1}
    rank2win_points_inv = {win_point: rank for rank, win_point in
                           rank2win_points.items()}
    target = test["rank"].map(rank2win_points_inv)
    test.drop(columns=drop_cols, inplace=True)

    scores = []
    for path in model_path.glob("*_cv_*.txt"):
        bst = lgb.Booster(model_file=str(path))
        preds = bst.predict(test)
        scores.append(preds)
    ave_scores = np.array(scores).mean(axis=0)

    a = np.array_split(ave_scores,
                       ave_scores.shape[0] // 6)
    b = np.array_split(target.values,
                       target.values.shape[0] // 6)
    for idx, (t, p) in enumerate(zip(a, b)):
        print(t)
        print(t.argsort()[::-1] + 1)
        print(p)
        if idx == 10:
            break


if __name__ == '__main__':
    main()
