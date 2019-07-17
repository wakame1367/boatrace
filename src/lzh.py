from pathlib import Path

import lhafile


# https://trac.neotitans.net/wiki/lhafile/
def unlzh(lzh_name):
    """Extract files under current directory"""
    print("Extract", lzh_name, "...")
    if not isinstance(lzh_name, Path):
        raise ValueError("{} is not supported.".format(type(lzh_name)))
    if not lzh_name.suffix == ".lzh":
        raise ValueError("{} is not supported extension.".format(lzh_name.suffix))
    # make directory to extract
    if not lzh_name.parent.exists():
        lzh_name.parent.mkdir()

    # open lzh file and get file names in it.
    lha = lhafile.Lhafile(str(lzh_name))

    # extract all files
    for lha_info in lha.infolist():
        file_path = lha_info.filename
        print("extract", file_path)
        with open(lzh_name.parent / file_path, "wb") as f:
            f.write(lha.read(file_path))
