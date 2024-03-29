""""""
import logging
import pydicom

logger = logging.getLogger(__name__)

class BaseParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    name = "DICOM Parser"
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
        return [".dcm"]

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
            "contents": self.get_contents,
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
        dcm_file = pydicom.dcmread(filepath)
        print(dcm_file.to_json_dict())
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