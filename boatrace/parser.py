import re
from pathlib import Path
from urllib.parse import urlparse, parse_qsl

import lxml.html
import pandas as pd
import requests

from boatrace.util import Config

config = Config(path=Path(__file__).parent / "params.yaml")
racer_class = config.get_racer_class()
field_name2code = config.get_field_code()


class AdvanceInfo:
    def __init__(self, url):
        self.parse_url = urlparse(url)
        self.url_pat = "beforeinfo"
        if self.url_pat not in self.parse_url.path:
            raise ValueError("url not matched {}".format(self.url_pat))
        request = requests.get(url)
        root = lxml.html.fromstring(request.text)
        self.table = self.scrape(root)

    def scrape(self, root):
        players = 6
        table = []
        enf_info = []
        xpath_race_prefix = "/html/body/main/div/div/div/div[2]/div[4]/div[1]/div[1]/table/"
        xpath_weather_prefix = "/html/body/main/div/div/div/div[2]/div[4]/div[2]/div[2]/div[1]/"

        temp_xpath = xpath_weather_prefix + "div[1]/div/span[2]/text()"
        weather_xpath = xpath_weather_prefix + "div[2]/div/span/text()"
        wind_speed_xpath = xpath_weather_prefix + "div[3]/div/span[2]/text()"
        water_temp_xpath = xpath_weather_prefix + "div[5]/div/span[2]/text()"
        wave_height_xpath = xpath_weather_prefix + "div[6]/div/span[2]/text()"
        for xpath in [temp_xpath, weather_xpath, wind_speed_xpath,
                      water_temp_xpath, wave_height_xpath]:
            for elem in root.xpath(xpath):
                enf_info.append(elem.strip())
        for idx in range(1, players + 1):
            elements = []
            player_elem = xpath_race_prefix + "tbody[{}]/".format(idx)
            weight_xpath = player_elem + "tr[1]/td[4]/text()"
            exhibition_xpath = player_elem + "tr[1]/td[5]/text()"
            tilt_xpath = player_elem + "tr[1]/td[6]/text()"
            assigned_weight_xpath = player_elem + "tr[3]/td[1]/text()"
            for xpath in [weight_xpath, exhibition_xpath, tilt_xpath,
                          assigned_weight_xpath]:
                for elem in root.xpath(xpath):
                    elements.append(elem.strip())
            table.append(enf_info + elements)
        return table

    def preprocess(self):
        pass


class StartTable:
    def __init__(self, url=None, path=None):
        self.header = ["date", "field_name", "race_idx", "registration_number",
                       "age", "weight", "class",
                       "global_win_perc", "global_win_in_second",
                       "local_win_perc", "local_win_in_second",
                       "mortar", "mortar_win_in_second", "board",
                       "board_win_in_second"]
        self.racer_class = racer_class
        self.field_name2code = field_name2code
        self.is_scrape = False
        if url or path:
            if url:
                self.parse_url = urlparse(url)
                self.url_pat = "racelist"
                if self.url_pat not in self.parse_url.path:
                    raise ValueError("url not matched {}".format(self.url_pat))
                request = requests.get(url)
                root = lxml.html.fromstring(request.text)
                self.start_table = self.scrape(root)
                self.is_scrape = True
            elif path:
                if not path.exists():
                    raise FileExistsError("{} is not exist".format(path))
                self.__parse(path)
        else:
            raise ValueError("set url or path")

    def __parse(self, path, encoding="cp932"):
        date = path.stem[1:]
        tables = []
        raw_lines = []
        begin_idx = []
        end_idx = []
        race_header_length = 12
        result_header_length = 5
        interval_per_race_length = 1
        interval_per_day_length = 12
        players = 6
        with path.open("r", encoding=encoding) as lines:
            for line_no, line in enumerate(lines):
                raw_line = line.strip()
                raw_lines.append(raw_line)
                if "BBGN" in raw_line:
                    begin_idx.append(line_no)
                if "BEND" in raw_line:
                    end_idx.append(line_no)
        for b_idx, e_idx in zip(begin_idx, end_idx):
            # skip headers
            race_info = raw_lines[b_idx + 1].strip().replace("\u3000",
                                                             "").split()
            field_name = race_info[0].replace("ボートレース", "")
            one_day_lines = raw_lines[b_idx + race_header_length:e_idx]
            end_race_idx = 0
            for race_idx in range(interval_per_day_length):
                if race_idx == 0:
                    begin_race_idx = race_idx * players + result_header_length
                else:
                    begin_race_idx = end_race_idx + result_header_length + interval_per_race_length
                end_race_idx = begin_race_idx + players
                for line in one_day_lines[begin_race_idx:end_race_idx]:
                    tables.append([date, field_name,
                                   race_idx + 1] + self.__preprocess_line(line))
        self.start_table = tables

    def __preprocess_line(self, line):
        split_line = line.strip().replace("\u3000", "").split()
        # drop after index 10 to same length
        split_line = split_line[:10]
        target = split_line[1]
        reg_number = re.match(r"\d+", target).group()
        target = target.replace(reg_number, "")
        age = re.search(r"\d+", target).group()
        target = target.replace(age, "")
        weight = re.search(r"\d+", target).group()
        c = None
        for c in self.racer_class.keys():
            if c in target:
                break
        del split_line[1]
        split_line.insert(1, reg_number)
        split_line.insert(2, age)
        split_line.insert(3, weight)
        split_line.insert(4, c)
        return split_line

    def scrape(self, root):
        players = 6
        start_table = []
        xpath_prefix = "/html/body/main/div/div/div/div[2]/div[4]/table/"
        query_params = dict(parse_qsl(self.parse_url.query))
        date = query_params["hd"]
        race_idx = query_params["rno"]
        field_name = query_params["jcd"]
        for idx in range(1, players + 1):
            player_elem_1 = xpath_prefix + "tbody[{}]/tr[1]/td[3]/div[1]/".format(
                idx)
            player_elem_2 = xpath_prefix + "tbody[{}]/tr[1]/td[3]/div[2]/".format(
                idx)
            player_elem_3 = xpath_prefix + "tbody[{}]/tr[1]/td[3]/div[3]/".format(
                idx)
            race_results = []
            for td_idx in range(4, 9):
                race_results.append(
                    xpath_prefix + "tbody[{}]/tr[1]/td[{}]/text()".format(idx,
                                                                          td_idx))
            reg_number_xpath = player_elem_1 + "text()"
            class_xpath = player_elem_1 + "span/text()"
            profile_url_xpath = player_elem_2 + "a/@href"
            player_info_xpath = player_elem_3 + "text()"
            elements = []
            for elem in root.xpath(reg_number_xpath):
                match = re.search(r"\d+", elem.strip())
                if match:
                    elements.append(match.group())
            for elem in root.xpath(class_xpath):
                elements.append(elem.strip())
            for elem in root.xpath(profile_url_xpath):
                parse_profile_url = urlparse(elem.strip())
                profile_url = self.parse_url._replace(
                    path=parse_profile_url.path)
                profile_url = profile_url._replace(
                    query=parse_profile_url.query)
                elements.append(profile_url.geturl())
            for elem in root.xpath(player_info_xpath):
                for e in elem.strip().split("/"):
                    elements.append(e.strip())
            for xpath in race_results:
                for elem in root.xpath(xpath):
                    elements.append(elem.strip())
            start_table.append([date, field_name, race_idx] + elements)
        return start_table

    def preprocess(self):
        int_cols = ["age"]
        float_cols = ["weight", "global_win_perc", "global_win_in_second",
                      "local_win_perc", "local_win_in_second",
                      "mortar_win_in_second", "board_win_in_second"]
        cat_cols = ["registration_number", "mortar", "board"]

        if self.is_scrape:
            df = pd.DataFrame(self.start_table).drop(
                columns=[5, 6, 7, 10, 11, 12,
                         15, 18, 21, 24])
            df = df.loc[:, [0, 1, 2, 3, 8, 9, 4, 13, 14, 16, 17, 19, 20, 22, 23]]
            df.columns = self.header
            df["field_name"] = df["field_name"].astype(int)
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df["race_idx"] = df["race_idx"].astype(int)
            df["age"] = df["age"].str.replace("歳", "")
            df["weight"] = df["weight"].str.replace("kg", "")
            df["class"] = df["class"].map(self.racer_class)
            for col in int_cols:
                df[col] = df[col].astype(int)
            for col in float_cols:
                df[col] = df[col].astype(float)
            for col in cat_cols:
                df[col] = df[col].astype("category")
            return df
        else:
            # drop idx
            df = pd.DataFrame(self.start_table).drop(columns=[3])
            df.columns = self.header
            df["field_name"] = df["field_name"].map(self.field_name2code)
            df["date"] = pd.to_datetime(df["date"], format="%y%m%d")
            df["class"] = df["class"].map(self.racer_class)

            for col in int_cols:
                df[col] = df[col].astype(int)
            for col in float_cols:
                df[col] = df[col].astype(float)
            for col in cat_cols:
                df[col] = df[col].astype("category")
            return df


class Result:
    def __init__(self):
        self.race_info_header = ["date", "boat_race_track", "course_length",
                                 "weather",
                                 "wind_direction", "wind_speed", "wave_height"]
        self.race_result_header = ["idx", "landing_boat",
                                   "registration_number",
                                   "player_name", "mortar", "board",
                                   "exhibition",
                                   "approach", "start_timing", "race_time",
                                   "is_anomaly_landing"]
        self.header = self.race_info_header + self.race_result_header
        self.dtypes = [int, int, int, str, int, int, float, int, float, str]
        self.sep_size = 79
        self.separator = "-" * self.sep_size
        self.race_info_length = 2
        self.race_result_length = 6
        self.race_round = 12
        # Reference
        # http://boat-advisor.com/soft/manual/data_keyword.htm
        self.landing_boat_pattern = re.compile(r"0[1-6]")
        self.disqualification_pattern = re.compile(r"S[0-2]")
        self.false_start_pattern = re.compile(r"F")
        self.delay_pattern = re.compile(r"L[0-1]")
        self.miss_race_pattern = re.compile(r"K[0-1]")
        self.landing_boat_pattern = re.compile(
            "|".join(pat.pattern for pat in [self.landing_boat_pattern,
                                             self.disqualification_pattern,
                                             self.false_start_pattern,
                                             self.delay_pattern,
                                             self.miss_race_pattern]))
        self.course_length_pattern = re.compile(r"H(\d+)m")
        self.wave_pattern = re.compile(r"波.*(\d+cm)")
        self.wind_pattern = re.compile(r"風(.*?)(\d+m)")
        self.boat_race_track_pattern = re.compile(r"ボートレース.{2,3}\n")

    def parse(self, path, encoding="cp932"):
        """

        Parameters
        ----------
        path : pathlib.Path
        encoding : str

        Returns
        -------
            list
        """
        boat_race_tracks = []
        sep_index = []
        raw_lines = []
        # K190701.TXT
        date = path.stem[1:]
        # get raw_txt and separator index
        with path.open("r", encoding=encoding) as lines:
            for line_no, line in enumerate(lines):
                raw_line = line.rstrip()
                boat_race_track = self.boat_race_track_pattern.search(line)
                if raw_line == self.separator:
                    sep_index.append(line_no)
                elif boat_race_track:
                    boat_race_tracks.append(
                        boat_race_track.group().replace("\u3000", "").strip())
                raw_lines.append(raw_line)
        txt = []
        # Retrieve text between delimiters and delimiters
        for idx in sep_index:
            txt.append(raw_lines[idx - self.race_info_length])
            txt += raw_lines[idx + 1:idx + self.race_result_length + 1]

        new_txt = []
        # strip text
        for line in txt:
            rline = line.strip().replace("\u3000", "").replace(".  .",
                                                               "-").replace(
                "L .", "- -") \
                .replace("K .         K .", "- - -")
            is_race_info = self.course_length_pattern.search(rline)
            if is_race_info:
                # cut out after course_length
                rline = rline[is_race_info.span()[0]:]
                wave_info = [w.strip() for w in
                             self.wave_pattern.search(rline).groups()]
                wind_info = [w.strip() for w in
                             self.wind_pattern.search(rline).groups()]
                # get course_length and wether
                split_line = rline.split()[:2] + wind_info + wave_info
            else:
                split_line = rline.split()
            # add race_name to race_info
            if len(split_line) == 9:
                split_line.insert(self.race_info_length, "-")
            split_line = split_line
            # is_race_result
            if self.is_race_result(split_line):
                # Reference
                # http://boat-advisor.com/soft/manual/data_keyword.htm
                # 着順情報が 01 ~ 06 以外の情報が存在する
                # 観測できたのは K0 : 欠場, 欠場の場合race_time等が歯抜けになる
                is_anomaly_landing = False
                if not re.match("0[1-6]", split_line[0]):
                    is_anomaly_landing = True
                    # is_false_start
                    approach_time = split_line[8]
                    if re.match("F", approach_time):
                        split_line[8] = approach_time.split("F")[1]
                    elif re.match("L", approach_time):
                        split_line[8] = approach_time.split("L")[1]
                split_line.append(is_anomaly_landing)
            new_txt.append(split_line)

        start_line = new_txt[0]
        lines = []
        # add race_info(weather, wind_direction) per column
        for line_no, line in enumerate(new_txt):
            if line_no % (self.race_result_length + 1) == 0:
                start_line = [date] + line
            else:
                lines.append(start_line + line)

        begin_idx = 0
        for boat_race_idx, boat_race_track in enumerate(boat_race_tracks, 1):
            end_idx = boat_race_idx * self.race_result_length * self.race_round
            for line in lines[begin_idx:end_idx]:
                line.insert(1, boat_race_track)
            begin_idx = end_idx
        return lines

    def is_race_result(self, line):
        landing_boat = line[0]
        if self.landing_boat_pattern.match(landing_boat):
            return True
        else:
            return False


class Player:
    def __init__(self):
        # https://www.boatrace.jp/owpc/pc/extra/data/layout.html
        self.split_bytes = [4, 16, 15, 4, 2, 1, 6, 1, 2, 3, 2, 2, 4, 4, 3, 3, 3,
                            2, 2, 3,
                            3, 4, 3, 3, 3, 4, 3, 3, 3, 4, 3, 3, 3, 4, 3, 3, 3,
                            4, 3, 3, 3, 4, 3, 3,
                            2, 2, 2, 4, 4, 4, 1, 8, 8, 3,
                            3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2,
                            3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2,
                            2, 2, 2, 2, 6]

    # reference
    # https://www.saintsouth.net/blog/truncate-strings-by-specified-bytes-in-python3/
    @staticmethod
    def truncate(strings, num_bytes, encoding='utf-8'):
        while len(strings.encode(encoding)) > num_bytes:
            strings = strings[:-1]
        return strings

    def parse(self, path, encoding="cp932"):
        """

        Parameters
        ----------
        path : pathlib.Path
        encoding : str

        Returns
        -------
            list
        """
        raw_lines = []
        # get raw_txt and separator index
        with path.open("r", encoding=encoding) as lines:
            for line_no, line in enumerate(lines):
                # skip blank line
                if line.strip():
                    # to byte
                    byte_line = line.encode(encoding)
                    start = 0
                    new_lines = []
                    for split_byte in self.split_bytes:
                        end = start + split_byte
                        # to str
                        str_line = byte_line[start:end].decode(encoding)
                        # to raw text
                        new_lines.append(str_line.replace("\u3000", "").strip())
                        start = end
                    raw_lines.append(new_lines)
        return raw_lines
