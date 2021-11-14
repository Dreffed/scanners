import argparse
import win32com.client
import os
from enum import Enum
from dateutil.parser import parse

import logging
from logging.config import fileConfig

fileConfig('config\logging_config.ini')
logger = logging.getLogger(__name__)

class Zoom(Enum):
    wdPageFitNone = 0 #	Do not adjust the view settings for the page.
    wdPageFitFullPage = 1 #	View the full page.
    wdPageFitBestFit = 2 #	Best fit the page to the active window.
    wdPageFitTextFit = 3 #	Best fit the text of the page to the active window.    

def get_app(filepath: str, appname: str):
    data = {}

    try:
        app = win32com.client.Dispatch(appname)
        app.Visible = True
        doc = app.Documents.Open(filepath)

        app.ActiveWindow.View = 50 #.PageFit = Zoom.wdPageFitFullPage
        
        input("Press enter to continue")
        doc.close()
        
    except Exception as ex:
        logger.error("{}\n\t>>>{}".format(filepath, ex))
    finally:
        app.Quit()

    return data        

if __name__ == "__main__":
    appnames = {
        ".vsdx": "Visio.Application",
        ".vsd": "Visio.Application",
        ".docx": "Word.Application",
        ".doc": "Word.Application",
        ".xlsx": "Excel.Application",
        ".xls": "Excel.Application"
    }

    filelist = [
        r"E:\users\ms\google\dreffed\1-2021 2022 Information-School Cash-Welcome Online.docx",
        r"E:\users\ms\google\dreffed\1-2021 2022-School Cash -PARENTS - FAQ.pdf",
        r"E:\users\ms\google\dreffed\Scouts Apple Day.xlsx",
    ]

    for f in filelist:
        _, ext = os.path.splitext(f)
        if ext in appnames:
            get_app(filepath=f, appname=appnames.get(ext))
