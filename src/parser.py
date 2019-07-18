class Result:
    def __init__(self):
        self.head = ["race_name", "date1", "date2", "place", "round_name",
                     "type",
                     "landing_boat", "registration_number", "player_name",
                     "ﾓｰﾀｰ", "ﾎﾞｰﾄ", "展示", "進入", "ｽﾀｰﾄﾀｲﾐﾝｸ", "ﾚｰｽﾀｲﾑ"]
        self.sep_size = 79
        self.separator = "-" * self.sep_size
        self.race_info_length = 2
        self.race_result_length = 6

    def parse(self, path):
        sep_index = []
        raw_lines = []
        with open(path, "r") as lines:
            for line_no, line in enumerate(lines):
                # get separator index
                if line.rstrip() == self.separator:
                    sep_index.append(line_no)
                raw_lines.append(line.rstrip())
        txt = []
        # before and after separator
        # get before 2rows
        # get after 6rows
        for idx in sep_index:
            txt += raw_lines[idx - self.race_info_length:idx]
            txt += raw_lines[idx + 1:idx + self.race_result_length + 1]
        return txt
