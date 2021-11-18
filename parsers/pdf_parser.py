""""""
#from PyPDF2 import PdfFileReader
import logging
import pikepdf
import pdfplumber

from logging.config import fileConfig

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
            pdf = pikepdf.Pdf.open(f)
            cp = pdf.docinfo

        for k,v in cp.items():
            data[k] = v

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

if __name__ == "__main__":
    from argparse import ArgumentParser

    fileConfig(r'config\logging_config.ini')
    argparser = ArgumentParser(
        prog="PDF Scanner",
        description="will scan a PDF file and return the discovered information")

    argparser.add_argument('-fp', '--file_path',
        dest="file_path",
        help="The path for the file to scan.")

    args = argparser.parse_args()

    fp = args.file_path
    if not fp:
        fp = r"E:\users\ms\google\dreffed\Books\20 Python Libraries You Aren't - Caleb Hattingh.pdf"

    obj = PDFParser()

    data = obj.get_metadata(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.get_contents(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.analyze(filepath=fp)
    print(data)
    logger.info(data)
