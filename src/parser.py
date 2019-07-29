import re


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
        # Reference
        # http://boat-advisor.com/soft/manual/data_keyword.htm
        self.landing_boat_pattern = re.compile(r"0[1-6]")
        self.disqualification_pattern = re.compile(r"S[0-2]")
        self.false_start_pattern = re.compile(r"F")
        self.delay_pattern = re.compile(r"L[0-1]")
        self.miss_race_pattern = re.compile(r"K[0-1]")
        self.landing_boat_pattern = re.compile("|".join(pat.pattern for pat in [self.landing_boat_pattern,
                                                                                self.disqualification_pattern,
                                                                                self.false_start_pattern,
                                                                                self.delay_pattern,
                                                                                self.miss_race_pattern]))

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
            rline = line.strip().replace("\u3000", "").replace(".  .", "-").replace("L .", "- -")\
                .replace("K .         K .", "- - -")
            split_line = rline.split()
            # add race_name to race_info
            if len(split_line) == 9:
                split_line.insert(self.race_info_length, "-")
            # is_race_result
            if self.is_race_result(split_line):
                # Reference
                # http://boat-advisor.com/soft/manual/data_keyword.htm
                # 着順情報が 01 ~ 06 以外の情報が存在する
                # 観測できたのは K0 : 欠場, 欠場の場合race_time等が歯抜けになる
                is_anomaly_landing = False
                if not re.match("0[1-6]", split_line[0]):
                    is_anomaly_landing = True
                split_line.append(is_anomaly_landing)
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

    def is_race_result(self, line):
        landing_boat = line[0]
        if self.landing_boat_pattern.match(landing_boat):
            return True
        else:
            return False

    def is_race_info(self, line):
        landing_boat = line[0]
        if self.landing_boat_pattern.match(landing_boat):
            return False
        else:
            return True
