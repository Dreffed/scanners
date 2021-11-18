""""""
from datetime import datetime
import logging
from logging.config import fileConfig
import psutil
import platform

logger = logging.getLogger(__name__)

class SystemParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    
    name = "System Parser"
    version = "0.0.1"

    def __init__(self):
        pass

    def __str__(self):
        return "{} {}".format(self.name, self.version)

    def get_functions(self):
        """
        
        Parameters
        ----------

        Returns
        -------
        None
        """
        return {
            "metadata": self.get_metadata,
            "analyse": self.analyze,
            "contents": self.get_contents
        }

    def get_metadata(self, filepath: str) -> dict:
        """This will return the doc info infomation from the 
        Named file.
        
        Parameters
        ----------

        Returns
        -------
        None
        """

        data = {}
        
        return data

    def analyze(self, filepath: str) -> dict:
        """
        
        Parameters
        ----------

        Returns
        -------
        None
        """
        data = dict
        
        return data

    def get_contents(self, filepath: str) -> list:
        """This will return the paragroah objects in a word document
        
        Parameters
        ----------

        Returns
        -------
        None
        """
        data = []

        return data

if __name__ == "__main__":
    from argparse import ArgumentParser

    fileConfig(r'config\logging_config.ini')
    argparser = ArgumentParser(
        prog="System Scanner",
        description="will scan a ssytem and return the discovered information")

    argparser.add_argument('-fp', '--file_path',
        dest="file_path",
        help="The path for the system to scan.")

    args = argparser.parse_args()

    fp = args.file_path

    obj = SystemParser()

    data = obj.get_metadata(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.get_contents(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.analyze(filepath=fp)
    print(data)
    logger.info(data)