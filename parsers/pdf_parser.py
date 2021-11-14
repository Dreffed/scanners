""""""
from PyPDF2 import PdfFileReader
import pdfplumber

import logging
from logging.config import fileConfig

fileConfig('config\logging_config.ini')
logger = logging.getLogger(__name__)

class PDFParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    
    name = "PDF Parser"
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
        return [".pdf"]

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

        with open(filepath, 'rb') as f:
            pdf = PdfFileReader(f)
            cp = pdf.getDocumentInfo()
        
        if cp:
            # get the core properties from the file...
            data['author'] = cp.author
            data['creator'] = cp.creator
            data['producer'] = cp.producer
            data['subject'] = cp.subject
            data['title'] = cp.title
        
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

        with pdfplumber.open(filepath) as pdf:
            for p in pdf.pages:
                data.append(p.extract_text())
                
        return {
            "type": "strings",
            "strings": data
        }