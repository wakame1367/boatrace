class Result:
    def __init__(self):
        self.head = ["race_name", "date1", "date2", "place", "round_name",
                     "type",
                     "landing_boat", "registration_number", "player_name",
                     "ﾓｰﾀｰ", "ﾎﾞｰﾄ", "展示", "進入", "ｽﾀｰﾄﾀｲﾐﾝｸ", "ﾚｰｽﾀｲﾑ"]
        self.header = ["idx", "landing_boat", "registration_number",
                       "player_name", "mortar", "board", "exhibition",
                       "approach", "race_time"]
        self.dtypes = [int, int, int, str, int, int, float, int, float, str]
        self.sep_size = 79
        self.separator = "-" * self.sep_size
        self.race_info_length = 2
        self.race_result_length = 6

    def parse(self, path):
        sep_index = []
        raw_lines = []
        with open(path, "r") as lines:
            for line_no, line in enumerate(lines):
                if line.rstrip() == self.separator:
                    sep_index.append(line_no)
                raw_lines.append(line.rstrip())
        txt = []
        for idx in sep_index:
            txt.append(raw_lines[idx - self.race_info_length])
            txt += raw_lines[idx + 1:idx + self.race_result_length + 1]

        new_txt = []
        for line in txt:
            rline = line.strip().replace("\u3000", "").replace(".  .", "-")
            new_txt.append(rline.split())
        return new_txt
