""""""
import os
from utils.utils_pickle import load_pickle, save_pickle, get_data
from utils.utils_files import get_filename
from utils.utils_json import load_json, get_setup
import parser_loader

import logging
from logging.config import fileConfig

fileConfig('.\config\logging_config.ini')
logger = logging.getLogger(__name__)

def process(config: dict = dict()):
    """This will take the saved files data and process the using the main plugins, see config files
    
    Parameters
    ----------
    config: dict
        a dictionary of information for the files
        locations: a labelled dict of file details
            root: str, folders: list, opt. name: str, opt. ext: str
        parsers: a labelled list of parsers

    Returns
    -------
    None

    """

    data = get_data(config=config)
    parsers = parser_loader.load(get_filename(config.get("locations",{}).get("parsers",{})))

    """load in the parsers for the avaailable file types...
        name: {
            parser  : <class name>
            exts    : list of extensions
        }
    """
    functions = dict()
    functions[":ALL:"] = []
    generics = dict()

    """ get the parsers, this will only used the parsers specified in the config file
    
    "parsers":{
        <label>:{
            "parser": <Parser Class Name>
        }, 
        ...
    }
    """
    for k,v in config.get("parsers", {}).items():
        if not v:
            continue

        if isinstance(v,dict) \
                and v.get("parser", "") in parsers:

            cls = parsers.get(v.get("parser"))
            if len(cls().get_extensions()) == 0:
                """        
                "allfiles": {
                    "parsers": ["NameParser"],
                    "methods": ["metadata"],
                    "fields": ["file"]
                }       
                """
                if v.get("parser","") in config.get("allfiles",{}).get("parsers",[]):
                    functions[":ALL:"].append(cls())
            else:
                for ext in cls().get_extensions():
                    if ext not in functions:
                        functions[ext] = []    
                    functions[ext].append(cls())

    # list the available parsers...
    for k,v in functions.items():
        for cls in v:
            logger.info("\tFileTypes: {} => {} [{}]".format(k, cls.name, cls.version))
    
    # process the files...
    for idx, (filepath, f) in enumerate(data.get("files").items()):
        if os.path.exists(filepath):
            try:
                # process the file by extensions...
                if len(config.get("analyze",{}).get("exts",[])) == 0 or f.get("ext","") in config.get("analyze",{}).get("exts",[]):
                    for cls_list in functions.get(f.get("ext"), []):
                        if not isinstance(cls_list, list):
                            cls_list = [cls_list]

                        for cls in cls_list:
                            if cls:
                                """ the process node in the anlyze config section
                                    "process":[
                                        {
                                            "methods": [<method alias to call>, ...],
                                            "exts": [<empty> | <ext>, ...]
                                        }
                                        ...
                                    ],                                    
                                """
                                for p in config.get("analyze", {}).get("process",[]):
                                    if len(p.get("exts",[])) == 0 or f.get("ext") in p.get("exts",[]):
                                        for name in p.get("methods",[]):
                                            func = cls.get_functions().get(name)
                                            if func:
                                                if "{}.{}".format(cls.name, name) not in f:
                                                    f["{}.{}".format(cls.name, name)] = func(filepath)

                # handle the all case...
                for cls_list in functions.get(":ALL:", []):
                    for cls in cls_list:
                        if cls:
                            for name, func in cls.get_functions().items():
                                if name in config.get("analyze", {}).get("allfiles",{}).get("methods",[]):
                                    if "{}.{}".format(cls.name, name) not in f:
                                        f["{}.{}".format(cls.name, name)] = func(filepath)

            except Exception as ex:
                print("{} {}".format(ex, f))
                logger.error("{} {}".format(ex, f))

    save_pickle(data=data, filename=get_filename(config.get("locations", {}).get("data", {})))


if __name__ == "__main__":
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