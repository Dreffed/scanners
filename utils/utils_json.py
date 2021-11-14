import os
import logging
from json import load, dump, dumps
from utils.utils_files import get_filename

from logging.config import fileConfig

logger = logging.getLogger(__name__)

def load_json(filename=r"settings.json"):
    # Load credentials from json file
    data = None
    if os.path.exists(filename):
        with open(filename, "r") as file:  
            data = load(file)
    return data

def save_json(data = {}, filename=r"settings.json"):
    # Save the credentials object to file
    with open(filename, "w") as file:  
        file.write(dumps(data, indent = 4)) 

def get_setup(filename: str ="config_scanner") -> dict:
    """returns a base config for the code based in filename
    
    Parameters
    ----------
    filename : str
        a filename located in the config directory, if the extension is omitted assumed to be JSON
        will check for valid file paths.

    Returns
    -------
    dict
        a JSON config object use by the rest of the program

    """
    if filename is None:
        filename = "config_scanner"

    if os.path.exists(filename):
        filepath = filename
    else:
        name, ext = os.path.splitext(filename)
        if not ext:
            ext = ".json"

        setup = {
            "root": ".",
            "folders": ["config"],
            "name": filename,
            "ext":ext
        }
        filepath = get_filename(setup)

    
    config = load_json(filename=filepath)

    return config
