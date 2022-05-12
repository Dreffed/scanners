""""""
import os
from datetime import datetime
import logging
import pandas as pd
import pandas.io.formats.excel
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
    f_fields = 0
    w_fields = 0
    m_cols = set()

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

        df_cols = list(row.keys())

        # expand folders
        for idx, fldr in enumerate(f.get("folders", [])):
            row[f'f{idx:02}'] = fldr
            if idx > f_fields:
                f_fields = idx

        # get extracted words
        step = -1
        for idx, parts in enumerate(f.get("profile", {}).get("parts",{})):
            word = parts.get("value")
            word_type = parts.get("type")
            if word_type in ["W", "U", "N", "B"]:
                step += 1
                row[f'w{step:02}'.format(step)] = word
                if step > w_fields:
                    w_fields = step
        
        # get the fields in metadata
        for field, value in f.get("metadata", {}).items():
            m_cols.add(field)
            row[field] = value

        rows.append(row)

    f_cols = [f'f{i:02}' for i in range(0, f_fields+1, 1)]
    logger.debug(f'Folders: {f_cols}')
    df_cols.extend(f_cols)

    w_cols = [f'w{i:02}' for i in range(0, w_fields+1, 1)]
    logger.debug(f'Words: {w_cols}')
    df_cols.extend(w_cols)

    logger.debug(f'Metadata: {sorted(m_cols)}')
    df_cols.extend(sorted(m_cols))

    # convert the rows to a dataframe
    df = pd.DataFrame(rows)
    df = df[df_cols]
    sps = config.get("locations", {}).get("scanpaths", [])
    excel_path = "Document List - {}.xlsx".format(sps[0].get("folders",[])[-1])
    writer = pd.ExcelWriter(excel_path, engine="xlsxwriter")
    name = "Filelist"
    row_offset = 1
    header_offset = 1
    use_header = True
    df.to_excel(writer, sheet_name=name, startrow=row_offset+header_offset, index=False, header=use_header)
    writer.save()

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
    logger.debug("Config: {}".format(args.config_path))
    config = get_setup(filename=args.config_path)
    process(config=config)