""""""
import os
from datetime import datetime
import logging
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

    files = data.get("files", {})
    exts = data.get("exts", {})
    filenames = data.get("filenames", {})
    hashes = data.get("hashes", {})
    guids = data.get("guids", {})
    scans = data.get("scans", [])

    for scanitem in config.get("locations", {}).get("scanpaths", []):
        scan = {
            "scandate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            #"sysinfo": sysinfo(),
            "files": [],
            "basepaths": []
        }      
        scanpath = get_filename(scanitem)
        scan["basepaths"].append(scanpath)

        if not os.path.exists(scanpath):
            logger.error("MISSING PATH {}".format(scanpath))
            continue

        logger.info("SCANNING {}".format(scanpath))
        for idx, f in enumerate(scan_files(scanpath, options=config.get("scanoptions", {}))):
            uuid = f.get("guid")
            if config.get("scanoptions", {}).get("splitextention"):
                filename = "{}{}".format(f.get("file"), f.get("ext"))
            else:
                filename = f.get("file")

            filepath = os.path.join(f.get("folder"), filename)

            if idx % 10000 == 0:
                logger.info("Tick {} - {}".format(idx, filepath))

            # get the name profile
            if "profile" not in f:
                f["profile"] = profile(source=filename, regexes=get_regexes())

            # check if the file has changed...
            if filepath in files:
                # get the former GUID if known
                uuid = files.get(filepath, {}).get("guid", uuid)
                f_old = files.get(filepath)
                if f_old.get("size", 0) == f.get("size", -1) and f_old.get("hash", {}).get("SHA1", "") == f.get("hash", {}).get("SHA1", ""):
                    logger.debug("Already scanned: {}".format(filepath))
                    if "profile" not in f_old:
                        logger.debug("Updating name profile: {}".format(filepath))
                        files[filepath] = f
                    if "hash" not in f_old:
                        files[filepath] = f
                        
                    continue
                else:
                    logger.info("Updated: {}".format(filepath))

            # Save the  scan hits...
            scan["files"].append(uuid)
            files[filepath] = f

            # guid index
            if uuid not in guids:
                guids[uuid] = []
            guids[uuid].append(filepath)

            # sort extensions...
            if f.get("ext").lower() not in exts:
                exts[f.get("ext").lower()] = []
            
            exts[f.get("ext").lower()].append(uuid)

            # sort filenames
            if filename not in filenames:
                filenames[filename] = []
            
            filenames[filename].append(uuid)

            # hash
            hashvalue = f.get("hash", {}).get("SHA1", "")
            if hashvalue:
                if hashvalue not in hashes:
                    hashes[hashvalue] = []
                hashes[hashvalue].append(uuid)

        scans.append(scan)

        # update the data object...
        data["files"] = files
        data["exts"] = exts
        data["filenames"] = filenames
        data["hashes"] = hashes
        data["guids"] = guids
        data["scans"] = scans

        # save the file
        save_pickle(data=data, filename=get_filename(config.get("locations", {}).get("data", {})))

def print_results(data: dict):
    """
    
    Parameters
    ----------

    Returns
    -------
    None

    """

    # display the results...
    for k,v in data.items():
        if v:
            logger.info("{} -> {}".format(k, len(v)))
        else:
            logger.info("{} -> {}".format(k, "n/a"))

    for _, files in data.get("hashes",{}).items():
        if len(files) > 1:
            logger.info("=====================")
            for guid in files:
                logger.info(data.get("guids",{}).get(guid))


if __name__ == "__main__":
    logger.info("Running Scan Files...")
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
    logger.info("Config: {}".format(args.config_path))
    config = get_setup(filename=args.config_path)
    process(config=config)