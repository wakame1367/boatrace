import argparse
from pathlib import Path

from src.lzh import unlzh


def get_arguments():
    _parser = argparse.ArgumentParser()
    _parser.add_argument("lzh_path", type=str)
    _args = _parser.parse_args()
    return _args


def main():
    args = get_arguments()
    unlzh(Path(args.lzh_path))


if __name__ == '__main__':
    main()
