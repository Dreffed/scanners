""""""
import os
from datetime import datetime
import logging
import pandas as PD
from utils.utils_files import scan_files, get_filename
from utils.utils_pickle import save_pickle, get_data
from utils.utils_json import get_setup
from utils.utils_rules import get_regexes, profile
#from utils.utils_systems import sysinfo, boottime

logger = logging.getLogger(__name__)
logging.config.fileConfig('logging_config.ini', disable_existing_loggers=False)

def process(config: dict = dict):
    """
    
    Parameters
    ----------
    config: dict


    Returns
    -------
    None

    """
    data = get_data(config=config)
    rows = []
    for idx, (filepath, f) in enumerate(data.get("files", {}).items()):
        if "profile" not in f:
            f["profile"] = profile(source=f.get("file",""), regexes=get_regexes())

        row = {
            "filename": f.get("file"),
            "fileext": f.get("ext"),
            "modified": f.get("modified"),
            "guid": f.get("guid"),
            "size": f.get("size"),
            "hash": f.get("hash",{}).get("SHA1"),
            "profile": f.get("profile",{}).get("profile")
        }

        # expand folders
        for idx, fldr in enumerate(f.get("folders", [])):
            row["f{}".format(idx)] = fldr

        # get extracted words
        step = -1
        for idx, parts in enumerate(f.get("profile", {}).get("parts",{})):
            word = parts.get("value")
            word_type = parts.get("type")
            if word_type in ["W", "U", "N", "B"]:
                step += 1
                row["w{}".format(step)] = word

        rows.append(row)

    # convert the rows to a dataframe
    df = DataFrame(rows)

if __name__ == "__main__":
    logger.info("Running Export Files...")
    from argparse import ArgumentParser
    argparser = ArgumentParser(
        prog="exportfiles",
        description="will scan files based on a a set of locations, saving result to a data pickle")

    argparser.add_argument('-cp', '--config_path',
        dest="config_path",
        help="The name or path for the config file to use.",
        default=r".\config\config_scanner_google.json")

    argparser.add_argument('-v', '--version',
        action='version',
        version='%(prog)s 1.0')

    args = argparser.parse_args()
    logger.info("Config: {}".format(args.config_path))
    config = get_setup(filename=args.config_path)
    process(config=config)