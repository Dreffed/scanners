""""""
import argparse
import win32com
from dateutil.parser import parse

import logging
from logging.config import fileConfig

fileConfig('config\logging_config.ini')
logger = logging.getLogger(__name__)

class VisioParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    
    name = "Visio Parser"
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
        return [".vsdx", ".vsd"]

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

        try:
            visio = win32com.client.Dispatch("Visio.Application")
            visio.Visible = 0
            dwg = visio.Documents.Open(filepath)
            pages = dwg.Pages

            data['name'] = dwg.Name
            data['title'] = dwg.Title  
            data['creator'] = dwg.Creator  
            data['description'] = dwg.Description  
            data['keywords'] = dwg.Keywords  
            data['subject'] = dwg.Subject  
            data['manager'] = dwg.Manager  
            data['category'] = dwg.Category 
            data['pagecount'] = len(pages)
            data['created'] = parse(str(dwg.TimeCreated))
            data['saved'] = parse(str(dwg.TimeSaved))

        except Exception as ex:
             logger.error("{}\n\t>>>{}".format(filepath, ex))
        finally:
            visio.Quit()

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

        return {
            "type": "nodes",   
            "data": data
        }

    def get_thunbnail(self, filepath: str) -> list:
        """ this will take a thumbnail fo each page in the document
        
        Parameters
        ----------

        Returns
        -------
        None
        """
        pass

if __name__ == "__main__":
    from argparse import ArgumentParser
    argparser = ArgumentParser(
        prog="Visio Scanner",
        description="will scan a visio file and return the discovered information")

    argparser.add_argument('-fp', '--file_path',
        dest="file_path",
        help="The path for the file to scan.") 

    argparser.add_argument('-md', '--metadata', dest='metadata', help='display file metadata')
    argparser.add_argument('-c', '--contents',  dest='contents', help='display file contents')
    argparser.add_argument('-a', '--analyze',  dest='analyze', help='analyze the file')

    args = argparser.parse_args()

    obj = VisioParser()

    if args.metadata:
        data = obj.get_metadata(filepath=args.file_path)
        logger.info(data)

    if args.contents:
        data = obj.get_contents(filepath=args.file_path)
        logger.info(data)

    if args.analyze:
        data = obj.analyze(filepath=args.file_path)
        logger.info(data)

