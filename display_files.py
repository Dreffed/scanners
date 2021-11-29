""""""
import os
from utils.utils_files import scan_files, make_hash, get_filename
from utils.utils_pickle import load_pickle, save_pickle, get_data
from utils.utils_json import load_json, get_setup

import logging


logger = logging.getLogger(__name__)
logging.config.fileConfig('logging_config.ini', disable_existing_loggers=False)

def process(config: dict = dict):
    """
    
    Parameters
    ----------

    Returns
    -------
    None

    """

    data = get_data(config=config)

    # display the results...
    if config.get("display", {}).get("summary"):
        logger.info("\n==== Items ====")
        for k,v in data.items():
            if v:
                logger.info("{} -> {}".format(k, len(v)))
            else:
                logger.info("{} -> {}".format(k, "n/a"))

    if config.get("display", {}).get("duplicates"):
        logger.info("\n==== Hashes ====")
        for hash, files in data.get("hashes",{}).items():
            if len(files) > 1:
                logger.info("=====================")
                for guid in files:
                    logger.info(data.get("guids",{}).get(guid))

    if config.get("display", {}).get("extensions"):
        logger.info("\n==== Extensions ====")
        for ext, files in data.get("exts",{}).items():
            logger.info("\t{}:\t{}".format(ext, len(files)))

    if config.get("display", {}).get("sample"):
        exts = []
        
        logger.info("\n==== First Match extensions ====")
        for filepath, f in data.get("files", {}).items():
            if f.get("ext","") not in exts:
                logger.info("{}".format(f))
                exts.append(f.get("ext",""))

    if len(config.get("display", {}).get("report",[])) > 0:
        logger.info("\n===Extension Report ===")
        for ext in config.get("display", {}).get("report",[]):
            logger.info("\n=== {} ===".format(ext))
            for guid in data.get("exts",{}).get(ext,[]):
                f = data.get("guids",{}).get(guid)
                logger.info(f)

def fix_extensions(config: dict = dict):
    """
    
    Parameters
    ----------

    Returns
    -------
    None

    """

    data = get_data(config=config)
    exts = {}

    for k,v in data.get("exts",{}).items():
        k = k.lower()
        if k in exts:
            exts[k].extend(v)
        else:
            exts[k] = v

    print(len(exts), len(data.get("exts",{})))
    data["exts"] = exts

    save_pickle(data=data, filename=get_filename(config.get("locations", {}).get("data", {})))


if __name__ == "__main__":
    logger.info("Running Display Files...")

    from argparse import ArgumentParser
    argparser = ArgumentParser(
        prog="scanfiles",
        description="will scan files based on a a set of locations, saving result to a data pickle")


    argparser.add_argument('-cp', '--config_path',
        dest="config_path",
        help="The name or path for the config file to use.",
        default=r".\config\config_scanner_google.json")

    argparser.add_argument('-v', '--version',
        action='version',
        version='%(prog)s 1.0')

    args = argparser.parse_args()
    config = get_setup(filename=args.config_path)
    process(config=config)
    #fix_extensions(config=config)