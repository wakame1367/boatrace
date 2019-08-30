from pathlib import Path

import yaml


class Config:
    def __init__(self, path):
        self.config_path = Path(path)
        with self.config_path.open("r", encoding="utf-8") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        self.config = config

    def get_field_code(self):
        jcd = self.config["jcd"]
        return dict(zip(range(1, len(jcd)+1), jcd))
