""""""

from datetime import datetime
from dateutil.parser import parse
import fitz
import logging
from logging.config import fileConfig
import re

logger = logging.getLogger(__name__)

def convertdate(dobj):
    """
    """
    if str(dobj)[:2] == "D:":
        return datetime.strptime(str(dobj)[2:], "%Y%m%d%H%M%SZ").strftime("%Y-%m-%d %H:%M:%S")
    return str(dobj)

def convertzulu(dobj):
    """
    """
    dstr = str(dobj)

    reg = re.compile(r"D:(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})(?P<min>\d{2})(?P<sec>\d{2})(?P<os>.)(?P<oh>\d{2})'(?P<om>\d{2})'")
    m = reg.match(dstr)
    if m:
        return "{year}-{month}-{day} {hour}:{min}:{sec} TZ{os}{oh}:{om}".format(**m.groupdict())

    reg = re.compile(r"D:(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<hour>\d{2})(?P<min>\d{2})(?P<sec>\d{2})")
    m = reg.match(dstr)
    if m:
        return "{year}-{month}-{day} {hour}:{min}:{sec}".format(**m.groupdict())

    return str(dstr)

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
            #"contents": self.get_contents
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

        doc = fitz.open(filepath)

        data = doc.metadata
        data["pagecount"] = doc.page_count
        if "creationDate" in data:
            data["creationDate"] = convertzulu(data.get("creationDate"))
        if "modDate" in data:
            data["modDate"] = convertzulu(data.get("modDate"))
        
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
        """This will return the TOC of the document,

        Parameters
        ----------

        Returns
        -------
        None
        """
        data = []

        doc = fitz.open(filepath)

        data = doc.get_toc(simple=True)

        return {
            "type": "toc",
            "strings": data
        }

if __name__ == "__main__":
    fileConfig(r'config\logging_config.ini', disable_existing_loggers=False)
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
