class Result:
    def __init__(self):
        self.head = ["race_name", "date1", "date2", "place", "round_name",
                     "type",
                     "landing_boat", "registration_number", "player_name",
                     "ﾓｰﾀｰ", "ﾎﾞｰﾄ", "展示", "進入", "ｽﾀｰﾄﾀｲﾐﾝｸ", "ﾚｰｽﾀｲﾑ"]
        self.race_info_header = ["round", "race_name", "rave_type",
                                 "course_length", "weather", "wind",
                                 "wind_direction", "wind_speed", "wave",
                                 "wave_height"]
        self.race_result_header = ["idx", "landing_boat",
                                   "registration_number",
                                   "player_name", "mortar", "board",
                                   "exhibition",
                                   "approach", "race_time"]
        self.dtypes = [int, int, int, str, int, int, float, int, float, str]
        self.sep_size = 79
        self.separator = "-" * self.sep_size
        self.race_info_length = 2
        self.race_result_length = 6

    def parse(self, path):
        sep_index = []
        raw_lines = []
        # get raw_txt and separator index
        with open(path, "r") as lines:
            for line_no, line in enumerate(lines):
                if line.rstrip() == self.separator:
                    sep_index.append(line_no)
                raw_lines.append(line.rstrip())
        txt = []
        # Retrieve text between delimiters and delimiters
        for idx in sep_index:
            txt.append(raw_lines[idx - self.race_info_length])
            txt += raw_lines[idx + 1:idx + self.race_result_length + 1]

        new_txt = []
        # strip text
        for line in txt:
            rline = line.strip().replace("\u3000", "").replace(".  .", "-")
            split_line = rline.split()
            # race_time is non-records
            if len(split_line) == 9:
                split_line.insert(self.race_info_length, "-")
            new_txt.append(split_line)

        start_line = new_txt[0]
        lines = []
        # add race_info(weather, wind_direction) per column
        for line_no, line in enumerate(new_txt):
            if line_no % (self.race_result_length + 1) == 0:
                start_line = line
            else:
                lines.append(start_line + line)
        return lines
