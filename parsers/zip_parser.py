""""""
from zipfile import ZipFile
from datetime import datetime
import logging
from logging.config import fileConfig

fileConfig('config\logging_config.ini')
logger = logging.getLogger(__name__)

def datetuple_str(datetuple):
    y, m, d, h, mm, s = datetuple
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(y, m, d, h, mm, s)    

class ZipParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    name = "Zip File Parser"
    version = "0.0.1"
    extensions = [".zip"]

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
        return self.extensions

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
        count = 0
        totalsize = 0
        mindate = None
        maxdate = None

        with ZipFile(filepath, 'r') as zipObj:
            for f in zipObj.infolist():
                count += 1
                totalsize += f.file_size
                if not mindate:
                    mindate = f.date_time
                else:
                    if mindate > f.date_time:
                        mindate = f.date_time

                if not maxdate:
                    maxdate = f.date_time
                else:
                    if maxdate < f.date_time:
                        maxdate = f.date_time
        if mindate:
            mindate = datetuple_str(mindate)
        if maxdate:
            maxdate = datetuple_str(maxdate)

        return {
            "count": count,
            "size": totalsize,
            "min_date": mindate,
            "max_date": maxdate
        }

    def get_contents(self, filepath: str) -> list:
        """This will return the paragroah objects in a word document
        
        Parameters
        ----------

        Returns
        -------
        dictionary
        {
            files: [
                {
                    name
                    original
                    size
                    compress
                    date
                    system
                    version
                }
            ]
        }
        """
        filelist = []
        
        with ZipFile(filepath, 'r') as zipObj:
            for f in zipObj.infolist():
                if f.is_dir():
                    fobj = {
                        "type": "folder",
                        "name":  f.filename,
                        "original": f.orig_filename,
                        "date": datetuple_str(f.date_time),
                        "system": f.create_system,
                        "version": f.create_version,
                    }
                else:
                    fobj = {
                        "type": "file",
                        "name":  f.filename,
                        "original": f.orig_filename,
                        "date": datetuple_str(f.date_time),
                        "system": f.create_system,
                        "version": f.create_version,
                        "size": f.file_size,
                        "compress": f.compress_size,
                    }
                filelist.append(fobj)
        
        return {
            "type": "fileobj",
            "files": filelist
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    strings = [
        "E:\\Windows.old\\ProgramData\\XrmToolBox\\update.zip",
        "D:\\users\\David\\Dropbox\\3d\\RGB+LED+Remote+Control+Holder.zip",
        "D:\\archives\\Home_2016-02-11\\myd\\My Archives\\Cast for Tens.zip",
        "D:\\archives\\Home_2016-02-11\\myd\\Personal\\Cast for Tens\\Cast for tens part 2.zip",
        "D:\\archives\\Home_2016-02-11\\myd\\My Archives\\Balfour beatty.zip",
        "D:\\archives\\Home_2016-02-11\\myd\\My Archives\\Zipped.zip"
    ]

    obj = ZipParser()
    logger.info("{} {}".format(obj.name, obj.version))
    for s in strings:
        pr = obj.get_metadata(s)
        logger.info("\n=== {}\n{}".format(s, pr))
        
        # only display if there are less than 50 files...
        if pr.get("count",0) < 50:
            data = obj.get_contents(s)
            for f in data.get("files"):
                logger.info(f)

