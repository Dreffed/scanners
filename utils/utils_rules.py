"""A collection of functions to help process a string and break out useful information."""
from collections import Counter
import logging
import re

logger = logging.getLogger(__name__)

def get_regexes():
    """will return the case regex to do a basic profile of a string"""    
    return {
        "^": re.compile("[A-Z]{2,}"),
        "|": re.compile("[A-Z][a-z]+"),
        "U": re.compile("[A-Z]+"),
        "L": re.compile("[a-z]+"),
        "*": re.compile(r"[\u4e00-\u9fff]+"),
        "N": re.compile(r"\d+"),
        "B": re.compile(r"[()\[\]{}']+"),
        "P": re.compile(r"[,!@#$%&+=?]+"),
        ".": re.compile(r"[\. _\-]+")
    }

def profile(source: str, regexes: list) -> dict:
    positions = {}
    p = {}
    for k, v in regexes.items():
        for m in v.finditer(source):
            l = len(m.group())
            s = m.start()
            e = m.end()
            if s not in p:
                p[s] = {
                    "start": s,
                    "end": e,
                    "type": k.replace("^", "U").replace("|", "W"),
                    "value": m.group()
                }
                source = "{}{}{}".format(source[:s], k*l, source[e:])
                if l == 1:
                    positions[s] = k
                else:
                    positions[s] = "{}{}".format(k,l)

    output = []
    parts = []
    for k, v in sorted(positions.items()):
        output.append(v)
        parts.append(p.get(k))

    return {
        "parts": parts,
        "profile": "".join(output).replace("^","U").replace("|", "W"),
        "expand": source.replace("^", "U").replace("|", "W")
    }

def expand_profile(s):
    stack = []
    cc = None
    for c in s:
        if c.isdigit():
            if cc:
                stack.append(cc*int(c))
            cc = None
        else:
            if cc:
                stack.append(cc)
            cc = c
    return "".join(stack)

def consolidate_profile(s):
    p = re.sub(r"\.\.+", "-", s).replace('.','')
    p = re.sub("WW+", "w", p)
    p = re.sub("NN+", "n", p)
    p = re.sub("UU+", "u", p)
    p = re.sub("PP+", "p", p).replace('J','-')
    return p

def frequency(s):
    """
    :type s: str
    :rtype: str
    """
    d = Counter(s)
    return d

