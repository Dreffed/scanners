""""""

from datetime import datetime
import fitz
import logging
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
            "analyze": self.analyze,
            #"contents": self.get_contents
        }

    def get_metadata(self, filepath: str) -> dict:
        """This will return the doc info infomation from the
        Named file.

        Parameters
        ----------

        Returns
        ----    ---
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
        doc = fitz.open(filepath)
        lines = {}
        pages = {}
        blocks = {}
        html = {}
        for idx, page in enumerate(doc):
            text = page.get_text('text', sort=True, flags=2)
            if text:
                pages[idx] = []
                # the text is split on lines
                for line in text.split("\n"):
                    if line not in lines:
                        lines[line] = 0

                    pages[idx].append(line)
                    lines[line] += 1
                        
            # extract blocks if any...
            blocks[idx] = []
            for block in page.get_text("blocks", sort=True, flags=2):
                (x0, y0, x1, y1, block_text, block_no, block_type) = block
                blocks[idx].append(
                    {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "no": block_no,
                        "type": block_type,
                        "text": block_text.replace("\n", " ")
                    }
                )

            html[idx] = page.get_text('html', flags=2)

        return {
            "lines": lines,
            "pages": pages,
            "blocks": blocks,
            "html": html
        }

    def get_meta(self, filepath: str) -> dict:
        """ This will take the first page of the document and try to extract info from it
        """
        doc = fitz.open(filepath)
        page = doc[0]



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
        fp = r"E:\users\ms\google\thoughtswin\Manitoba Hydro\EA\General\Gartner\3 Monetization Approaches for Driving Digital Revenue.pdf"

    obj = PDFParser()

    data = obj.get_metadata(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.get_contents(filepath=fp)
    print(data)
    logger.info(data)

    data = obj.analyze(filepath=fp)
    #for k,v in data.items():
    #    print("====\n\t{}".format(k))
    #    print(v)
    #for k,v in data.get("lines",{}).items():
    #    print("{}\t{}".format(v,k))
    for k,v in data.get("pages",{}).items():
        print("===== {}".format(k))
        for line in v:
            print(line)
        break
    for k,v in data.get("blocks",{}).items():
        print("===== {}".format(k))
        print(v)
        break
