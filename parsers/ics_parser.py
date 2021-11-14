""""""
from os import path
import io
from ics import Calendar, attendee
from pathlib import Path

import logging
from logging.config import fileConfig

fileConfig('config\logging_config.ini')
logger = logging.getLogger(__name__)

class ICSParser:
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
        if not path.exists(filepath):
            return {
                "name": filepath,
                "error": "path is not accessible"
            }

        data = {
            "name": filepath,
            "todos": [],
            "events": []
        }
        f = io.open(file=filepath, encoding="utf-8", mode="r")
        #txt = Path(filepath, encoding="utf-8").read_text()
        c = Calendar(f.read())
        for e in c.events:
            attendees = []
            for a in e.attendees:
                attendees.append({
                    "name": a.common_name,
                    "type": a.cutype,
                    "email": a.email,
                    "role": a.role,
                    "rsvp": a.rsvp
                }
                )
            
            for a in e.alarms:
                print(a)

            for a in e.categories:
                print(a)

            data["events"].append({
                "name": e.name,
                "begin ": e.begin,
                "end": e.end,
                "uid": e.uid,
                "description": e.description,
                "created ": e.created,
                "last_modified": e.last_modified,
                "location": e.location,
                "url": e.url,
                "transparent": e.transparent,
                "status": e.status,
                "organizer": e.organizer,
                "classification ": e.classification
                }
            )

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
    obj = ICSParser()
    filepaths = [
        r"D:\users\ms\Downloads\invite.ics",
        r"D:\users\ms\Downloads\invite (1).ics",
        r"D:\users\ms\Downloads\invite (2).ics",
        r"D:\users\ms\Downloads\invite (3).ics",
        r"D:\users\ms\Downloads\invite (4).ics",
        r"D:\users\ms\Downloads\david.gloyn-cox@thoughtswinsystems.com.ics"
    ]

    for fp in filepaths:
        data =obj.get_metadata(fp)
