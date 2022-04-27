""""""
import logging
from logging.config import fileConfig

logger = logging.getLogger(__name__)

class ImageTextParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    name = "Image Text Extractor"
    version = "0.0.1"

    def __init__(self):
        pass

    def __str__(self):
        return "{} {}".format(self.name, self.version)
    
    def get_extensions(self):
        """
        
        Parameters
        ----------

        Returns
        -------
        None
        """
        return []

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
            "analyze": self.analyze,
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
    #fileConfig(r'config\logging_config.ini', disable_existing_loggers=False)
    logger.info("Running PDF Parser...")

    from argparse import ArgumentParser

    argparser = ArgumentParser(
        prog="PDF Scanner",
        description="will scan a PDF file and return the discovered information")

    argparser.add_argument('-fp', '--file_path',
        dest="file_path",
        help="The path for the file to scan.")

    args = argparser.parse_args()

    fp = args.file_path
    if not fp:
        fp = r"E:\users\ms\google\thoughtswin\Manitoba Hydro\General\Gartner\3 Steps to Creating Enterprise Architecture Services.pdf"

    obj = ImageTextParser()

    data = obj.get_metadata(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.get_contents(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.analyze(filepath=fp)
    print(data)
    logger.info(data)