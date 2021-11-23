""""""
import PIL.Image, PIL.ExifTags
import os
import logging

logger = logging.getLogger(__name__)

class EXIFParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    name = "names"
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
        return [".bmp",".dds",".dib",".eps",".gif",".icns",".ico",".im",".jpeg",".msp",".pcx",".png",".ppm",
        ".sgi",".tga",".tiff",".webp",".xbm",".blp",".cur",".dcx",".fli",".flc",".fpx",".ftex",".gbr",".gd",".imt",",iptc",".naa",".mcidas",".mic",".mpo",".pcd",".pixar",".psd",".wal",".wmf",",xpm"]

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
        if not os.path.exists(filepath):
            logger.error("MISSING FILE {}".format(filepath))
            return

        img = PIL.Image.open(filepath)
        width, height = img.size
        tags = {PIL.ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in PIL.ExifTags.TAGS}
        data = {
            "width": width,
            "height": height,
            "tags": tags,
            "mode": img.mode,
            "info": img.info,
            "bands": list(img.getbands())
        }        
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
    argparser = ArgumentParser(
        prog="Visio Scanner",
        description="will scan a visio file and return the discovered information")

    argparser.add_argument('-fp', '--file_path',
        dest="file_path",
        help="The path for the file to scan.") 

    args = argparser.parse_args()

    fp = args.file_path
    if not fp:
        #fp = r"D:\users\ms\Gallery\2016-12-26\20161226123549.jpg"
        fp = r"D:\users\David\Pictures\Gallery\2017-01-08\IMAG0662.jpg"

    obj = EXIFParser()
    
    data = obj.get_metadata(filepath=fp)
    logger.info(data)

    data = obj.get_contents(filepath=fp)
    logger.info(data)

    data = obj.analyze(filepath=fp)
    logger.info(data)  