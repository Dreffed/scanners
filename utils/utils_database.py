from ctypes import sizeof
import logging
from neo4j import GraphDatabase
from neomodel import db
from neomodel import (config, StructuredNode, StringProperty, IntegerProperty,
    UniqueIdProperty, DateTimeFormatProperty, RelationshipTo)

logger = logging.getLogger(__name__)

class GraphDB:
    """ this will load the neo4j database, and provide methods to handle the connection"""
    def __init__(self, config) -> None:
        self.config = config
        self.driver = None

    def connect(self):
        """connects to the database"""
        config_gdb = self.config.get("database", {}).get("graphdb",{})
        uri = "bolt://{}:{}".format(config_gdb.get("uri"),config_gdb.get("port"))
        auth = (config_gdb.get("user"), config_gdb.get("passwd"))
        self.driver = GraphDatabase.driver(uri, auth=auth)


    def close(self):
        """Closes the database connection."""
        self.driver.close()

def set_connection(config):
    config_gdb = config.get("database", {}).get("graphdb",{})
    uri = "bolt://{}:{}@{}:{}".format(config_gdb.get("user"), config_gdb.get("passwd"), \
        config_gdb.get("uri"),config_gdb.get("port"))
    db.set_connection(uri)

class Scan(StructuredNode):
    uri = StringProperty(required=True)
    dateAdded = DateTimeFormatProperty(required=True)

class Entity(StructuredNode):
    uri = StringProperty(unique_index=True)
    name = StringProperty(required=True)
    suffix = StringProperty()
    prefix = StringProperty()

class Version(StructuredNode):
    size = IntegerProperty(index=True, default=0)
    hash = StringProperty()
    dateCreated = DateTimeFormatProperty(required=True)
    dateModified = DateTimeFormatProperty(required=True)
    dateRemoved = DateTimeFormatProperty()

class Tags(StructuredNode):
    key = StringProperty(required=True)
    value = StringProperty(required=True)
    dateAdded = DateTimeFormatProperty(required=True)
    dateRemoved = DateTimeFormatProperty()