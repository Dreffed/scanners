import hashlib
import logging
import os
import re
import stat
import time
import uuid
from .utils_core import convert_size

logger = logging.getLogger(__name__)

def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def get_stat(entry):
    time_format = "%Y-%m-%d %H:%M:%S"

    f = {
        "file":entry.name,
        "folder":os.path.split(os.path.abspath(entry.path))[0],
        "inode":entry.inode()
    }
    
    # get the stats
    # os.stat_result(
    #	st_mode=33206, 
    #	st_ino=0, 
    #	st_dev=0, 
    #	st_nlink=0, 
    #	st_uid=0, 
    #	st_gid=0, 
    #	st_size=92702, 
    #	st_atime=1543724526, 
    #	st_mtime=1523310306, 
    #	st_ctime=1523310474)
    f["accessed"] = time.strftime(time_format,time.localtime(entry.stat().st_atime))
    f["modified"] = time.strftime(time_format,time.localtime(entry.stat().st_mtime))
    f["created"] = time.strftime(time_format,time.localtime(entry.stat().st_ctime))
    f["size"] = entry.stat().st_size
    f["mode"] = entry.stat().st_mode
    return f

def get_filename(f):
    """Will accept a json object of file details and return the
    full filename
        {
            "root":
            "folders": []
            "name":
            "ext": expects a "."
        }"""
    logger.debug("F: {}".format(f))
    if f.get("root") == ".":
        f["root"] = os.getcwd()
        logger.debug("using current drive {}".format(f.get("root")))
        
    path = os.path.expanduser(os.path.join(f.get("root"), *f.get("folders",[])))
    
    if "name" in f and "ext" in f:
        path = os.path.join(path, "{}{}".format(f.get("name"), f.get("ext")))

    return path

def get_info(filepath):
    """ Scans the file and returns the access, mod and create time in a YYYY-MM-DD HH:MM:SS format"""
    time_format = "%Y-%m-%d %H:%M:%S"
    try:
        file_stats = os.stat(filepath)
        modification_time = time.strftime(time_format,time.localtime(file_stats[stat.ST_MTIME]))
        access_time = time.strftime(time_format,time.localtime(file_stats[stat.ST_ATIME]))
        file_size = file_stats[stat.ST_SIZE]

    except:
        modification_time, access_time, file_size = ["","",0]

    return modification_time, access_time, file_size

def get_file_metadata(filepath, options):
    """return dict of file meats data based on the options passed
        "file": the file name of the file, if "splitextension" specified it is just the filename not extension
        "ext": the dotted extension of the file
        "folder"L the folder path of the file
        
        optional output:
            "folders": an arrazzy of the folder names, option "split"
            date and size details: option "stats"
                "modified"
                "accessed" 
                "size"
                "bytes": szie in mb, gb, etc.
            
    """
    dirpath = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    fname, ext = os.path.splitext(filename)
    data =  {
            "folder" : dirpath, 
            "file" : filename, 
            "ext": ext
    }

    if options.get("splitextention"):
        data["file"] = fname

    if options.get("splitfolders"):
        data["folders"] = splitall(dirpath)

    if options.get("stats"):
        try:
            m_time, a_time, f_size = get_info(filepath)
            # save the format
            data["modified"] = m_time
            data["accessed"] = a_time
            data["size"] = f_size
            data["bytes"] = convert_size(f_size)
        except Exception as e:
            logger.error("Error: scanning file stats - {}".format(e))
    return data

def scan_files(folder, options={}):
    """ This method will recursively scan the specified folder and add records if neccessary"""
    for dirpath, _, filenames in os.walk(folder):
        for filename in filenames:
            filepath = os.path.join(dirpath,filename)
            data = get_file_metadata(filepath=filepath, options=options)
            data["guid"] = str(uuid.uuid1())
            fname, ext = os.path.splitext(filename)

            # filter the files is needed...
            filter_config = options.get("filter")
            output = {}
            if filter_config:
                if "exts" in filter_config:
                    output["ext"] = 0
                    if ext in filter_config.get("exts", []):
                        output["ext"] = 1
                
                if "regex" in filter_config:
                    output["regex"] = 0
                    filter_reg = re.compile(filter_config.get("regex", ""))
                    m = filter_reg.match(fname)
                    if m:
                        output["regex"] = 1

            if output:
                c_filters = len(output)
                c_match = 0
                for k,v in output.items():
                    if v == 1:
                        c_match += 1

                if c_filters != c_match:
                    continue
 
            # check for HASH
            if options.get("generatehash"):
                maxsize = options.get("maxhashsize", 0)
                if maxsize == 0 or maxsize >= data.get("size",0):
                    data["hash"] = make_hash(filepath=filepath)

            yield data

def make_hash(filepath):
    """ Will hash the files for both MD5 and SHA1 and return a dict of the hashes"""
    hashes = {}
    #print('[{}]'.format(file_path))

    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!

    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    try:
        if os.path.exists(filepath):
            logger.debug('{}'.format(filepath))
            with open(filepath, 'rb') as f:
                while True:
                    d = f.read(BUF_SIZE)
                    if not d:
                        break
                    md5.update(d)
                    sha1.update(d)

            hashes['MD5'] = md5.hexdigest()
            hashes['SHA1'] = sha1.hexdigest()
        else:
            hashes['MD5'] = 'Missing file'
            hashes['SHA1'] = 'Missing file'
    except Exception as e:
        logger.error('ERROR: [{}]\n{}'.format(filepath,e))
        
        hashes['MD5'] = 'ERROR'
        hashes['SHA1'] = 'ERROR'

    return hashes

    