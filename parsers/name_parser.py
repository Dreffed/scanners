""""""
import re
import logging

logger = logging.getLogger(__name__)

class NameParser:
    """
    
    ---
    Attributes
    ----------


    Methods
    -------

    
    """
    name = "names"
    version = "0.0.1"

    _regexes = {
        "tcase": re.compile("[A-Z][a-z]+"),
        "abbrv": re.compile("[A-Z]{2,}"),
        "ucase": re.compile("[A-Z]+"),
        "lcase": re.compile("[a-z]+"),
        "code": re.compile(r"[\u4e00-\u9fff]+"),
        "decimal": re.compile(r"\d+\.\d+"),
        "int": re.compile(r"\d+"),
        "group": re.compile(r"[()\[\]{}']+"),
        "formula": re.compile(r"[,!@#$%&+=?]+"),
        "space": re.compile(r"[\. _\-\t]+")
    }

    def __init__(self):
        pass

    def __str__(self):
        return "Filename parser"
        
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
            "metadata": self.get_metadata
        }

    def get_metadata(self, filepath: str) -> dict:
        """This will return a profile of the file path and name
        
        Parameters
        ----------

        Returns
        -------
        None
        """
        input = filepath
        positions = {}
        p = {}
        for k,v in self._regexes.items():
            for m in v.finditer(input):
                l = len(m.group())
                s = m.start()
                e = m.end()
                if s not in p:
                    p[s] = {
                        "start": s,
                        "end": e,
                        "type": k,
                        "value": m.group()
                    }
                    input = "{}{}{}".format(input[:s], k[0]*l, input[e:])
                    if l == 1:
                        positions[s] = k[0]
                    else:
                        positions[s] = "{}{}".format(k[0],l)

        output = []
        parts = []
        for k,v in sorted(positions.items()):
            output.append(v.upper())
            parts.append(p.get(k))

        return {
            "parts": parts,
            "profile": "".join(output),
            "expand": input
        }        


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    strings = [
        '1.4 Protection of Privacy - Information Incidents (Privacy Breaches)',
        'Accept Amendment to Disclosure Statement_02112019_0328',
        'DS1 29560',
        'RBC-20080401-ABCPmarket',
        'Accept Form V_05222018_1043',
        'Accept Disclosure_06202018_0915',
        'Deficiency (Discl)_06072018_0908',
        '29563 - Undertaking - Hillcrest Place',
        'BCFSA Application for Consent Application Section #2 - Sub-Section #2 - November 30 2019 MERGER AGREEMENTS',
        'Bulkley Valley - X020317',
        "D:\\users\\ms\\Dropbox\\personal\\accounts\\tosort\\TD_EMERALD_FLEX_RATE_VISA_CARD_1504_Oct_25-2021.pdf"
    ]

    obj = NameParser()
    print("{} {}".format(obj.name, obj.version))
    for s in strings:
        pr = obj.get_metadata(s)
        print("==={}\n{}\n\n".format(s, pr))