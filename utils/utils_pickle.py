import pickle
import os
import csv
from utils.utils_files import get_filename

import logging
from logging.config import fileConfig

logger = logging.getLogger(__name__)

def load_pickle(filename):
    data = {}
    if os.path.exists(filename):
        logger.info('Loading Saved Data... [%s]' % filename)
        with open(filename, 'rb') as handle:
            data = pickle.load(handle)
    return data

def save_pickle(data, filename):
    logger.info('Saving Data... [%s]' % filename)
    with open(filename, 'wb') as handle:
        pickle.dump(data, handle)

def get_data(config: dict = {}) -> dict: 
    """
    
    Parameters
    ----------

    Returns
    -------
    None
    
    """
    
    data = load_pickle(get_filename(config.get("locations", {}).get("data", {})))
    return data

def save_data(data: dict, config: dict) -> None:
    """
    
    Parameters
    ----------

    Returns
    -------
    None
    
    """
    save_pickle(data=data, filename=get_filename(config.get("locations", {}).get("data", {})))
