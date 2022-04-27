The scanner set of programs are a set of utilities to perform the following:

scan_files.py
reads in the supplied path to a configuration file, and will scan the files contained in the specified fodlers.

analyze files
will load the config file
loads the parsers in the parser directory, module matches pattern *_parser$
Build list of extensions that can be parsed, and attaches the classes to this list, multiple parsers can serve a particular file type
Will load in the saved directory listing, and apply the parsers to the items if the files hasn't already beeing scanned by that parser.

display_files
Will output details from the saved directory listing
