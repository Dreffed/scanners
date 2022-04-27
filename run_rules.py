""""""
from functools import reduce
from importlib.metadata import metadata  # forward compatibility for Python 3
import logging
import operator
import re
from utils.utils_files import get_filename
from utils.utils_pickle import save_data, get_data
from utils.utils_json import get_setup, load_json


logger = logging.getLogger(__name__)
logging.config.fileConfig('logging_config.ini', disable_existing_loggers=False)

def run_regex(item: object, rule: dict) -> dict:
    """This will run a regex against the returns a dict of tags found"""
    if rule.get("type","").lower() != "regex":
        # break and return
        logger.error("Invalid rule for regex")
        return None
    
    data = {}
    #logger.debug("EXPR: {}".format(rule.get("expr")))
    m = re.match(rule.get("expr"), item)
    if m:
        logger.debug(m.groups(), m.groupdict())
        if "tags" in rule:
            for tag in rule.get("tags", []):
                try:
                    tn = tag.get("name")
                    tr = tag.get("regex")
                    if "value" in tag:
                        tv = tag.get("value")
                    else:
                        tv = m.group(tr)
                    data[tn] = tv
                except Exception as ex:
                    logger.error(f'{ex} {tag} {m.groups()} {m.groupdict()}')
        else:
            if m.groupdict():
                data = m.groupdict()
            else:
                for idx, g in enumerate(m.groups()):
                    data[idx] = g
    return data

def get_rules(config: dict) -> dict:
    """Will load in the rules and the groups from the db or files"""
    data_path = get_filename(config.get("locations", {}).get("rulesfile",{}))
    data = load_json(data_path)
    return data

def get_node_from_dict(data: dict, node: dict) -> object:
    """ Will return a value from a dict based on a list of fields
    https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    try:
        return reduce(operator.getitem, node.get("node",[]), data)
    except KeyError:
        return None

def get_regex_tags(node: dict, rule: dict) -> dict:
    """"""
    data = {}

    # the node can be a value, list or dict
    if isinstance(node, list):
        for item in node:
            # process the list item...
            d = get_regex_tags(node=item, rule=rule)
            for k,v in d.items():
                data[k] = v

    elif isinstance(node, dict):
        # use the selector to extract the item from the dict
        if "node" in rule.get("source", {}):
            # we have a selector,, extract the node
            item = get_node_from_dict(node, rule.get("source", {}))
            d = get_regex_tags(node=item, rule=rule)
            for k,v in d.items():
                data[k] = v

        else:
            for _, item in node.items():
                d = get_regex_tags(node=item, rule=rule)
                for k,v in d.items():
                    data[k] = v

    else:
        # match using regex
        d = run_regex(item=node, rule=rule)
        for k,v in d.items():
            data[k] = v

    return data

def process(config: dict = dict):
    """
    
    Parameters
    ----------
    config: dict


    Returns
    -------
    None

    """
    data = get_data(config=config)

    # load the rules
    rules = get_rules(config = config)
    logger.info(f"{rules}")

    source_func = {
        "path": get_node_from_dict
    }

    rules_func = {
        "regex": get_regex_tags
    }

    for idx, (filepath, f) in enumerate(data.get("files", {}).items()):
        stop_rule = False

        for r in rules.get("rules",{}):
            stop_rule = r.get("stop", False)
            matched_rule = False
            source = r.get("source")
            values = {}

            # now to process each rule...
            node = source_func[source.get("type")](data=f, node=source)
            if not node:
                break

            if isinstance(node, list):
                # handle the list of values...
                for item in node:
                    rule_output = rules_func[r.get("type")](node=item, rule=r)
                    if rule_output:
                        # handle the output
                        logger.debug(f'{rule_output} {item}')
                        matched_rule = True

                        for k,v in rule_output.items():
                            values[k] = v

                        if stop_rule:
                            break
            else:
                rule_output = rules_func[r.get("type")](node=node, rule=r)
                if rule_output:
                    # handle the output
                    logger.debug(f'{rule_output} {node}')
                    for k,v in rule_output.items():
                        values[k] = v
                    matched_rule = True

            # add the found values to the f path
            dest_key = r.get("destination", {}).get("node")
            for k,v in values.items():
                if dest_key not in f:
                    f[dest_key] = {}
                f[dest_key][k] = v

            # stop the rule if matched
            if matched_rule and stop_rule:
                break
    
    # Save pickle
    save_data(data=data, config=config)

if __name__ == "__main__":
    logger.info("Running Rule Engine Files...")
    from argparse import ArgumentParser
    argparser = ArgumentParser(
        prog="rulesengine",
        description="will run rules from the rule configuration file")

    argparser.add_argument('-cp', '--config_path',
        dest="config_path",
        help="The name or path for the config file to use.",
        default=r".\config\config_scanner_google.json")

    argparser.add_argument('-v', '--version',
        action='version',
        version='%(prog)s 1.0')

    args = argparser.parse_args()
    logger.info("Config: {}".format(args.config_path))
    config = get_setup(filename=args.config_path)
    process(config=config)