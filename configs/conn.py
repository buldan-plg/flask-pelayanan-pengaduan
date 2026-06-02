import pymysql
from .config import Config

def get_db():
    return pymysql.connect(
        cursorclass = pymysql.cursors.DictCursor,
        **Config.DB_CONFIG
    )