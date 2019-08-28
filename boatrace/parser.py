import re
from urllib.parse import urlparse, parse_qs

import lxml.html
import requests


class StartTable:
    def __init__(self, url):
        self.parse_url = urlparse(url)
        request = requests.get(url)
        root = lxml.html.fromstring(request.text)
        self.start_table = self.scrape(root)

    def scrape(self, root):
        players = 6
        start_table = []
        xpath_prefix = "/html/body/main/div/div/div/div[2]/div[4]/table/"
        for idx in range(1, players + 1):
            player_elem_1 = xpath_prefix + "tbody[{}]/tr[1]/td[3]/div[1]/".format(idx)
            player_elem_2 = xpath_prefix + "tbody[{}]/tr[1]/td[3]/div[2]/".format(idx)
            player_elem_3 = xpath_prefix + "tbody[{}]/tr[1]/td[3]/div[3]/".format(idx)
            race_results = []
            for td_idx in range(4, 8):
                race_results.append(xpath_prefix + "tbody[{}]/tr[1]/td[{}]/text()".format(idx, td_idx))
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
                profile_url = self.parse_url._replace(path=parse_profile_url.path)
                profile_url = profile_url._replace(query=parse_profile_url.query)
                elements.append(profile_url.geturl())
            for elem in root.xpath(player_info_xpath):
                for e in elem.strip().split("/"):
                    elements.append(e.strip())
            for xpath in race_results:
                for elem in root.xpath(xpath):
                    elements.append(elem.strip())
            start_table.append(elements)
        return start_table

    def preprocess(self):
        pass


class Result:
    def __init__(self):
        self.race_info_header = ["date", "boat_race_track", "course_length", "weather",
                                 "wind_direction", "wind_speed", "wave_height"]
        self.race_result_header = ["idx", "landing_boat",
                                   "registration_number",
                                   "player_name", "mortar", "board",
                                   "exhibition",
                                   "approach", "start_timing", "race_time", "is_anomaly_landing"]
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
        self.landing_boat_pattern = re.compile("|".join(pat.pattern for pat in [self.landing_boat_pattern,
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
                    boat_race_tracks.append(boat_race_track.group().replace("\u3000", "").strip())
                raw_lines.append(raw_line)
        txt = []
        # Retrieve text between delimiters and delimiters
        for idx in sep_index:
            txt.append(raw_lines[idx - self.race_info_length])
            txt += raw_lines[idx + 1:idx + self.race_result_length + 1]

        new_txt = []
        # strip text
        for line in txt:
            rline = line.strip().replace("\u3000", "").replace(".  .", "-").replace("L .", "- -") \
                .replace("K .         K .", "- - -")
            is_race_info = self.course_length_pattern.search(rline)
            if is_race_info:
                # cut out after course_length
                rline = rline[is_race_info.span()[0]:]
                wave_info = [w.strip() for w in self.wave_pattern.search(rline).groups()]
                wind_info = [w.strip() for w in self.wind_pattern.search(rline).groups()]
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
        self.split_bytes = [4, 16, 15, 4, 2, 1, 6, 1, 2, 3, 2, 2, 4, 4, 3, 3, 3, 2, 2, 3,
                            3, 4, 3, 3, 3, 4, 3, 3, 3, 4, 3, 3, 3, 4, 3, 3, 3, 4, 3, 3, 3, 4, 3, 3,
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
