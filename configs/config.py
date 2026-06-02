import os

class Config :
    
    DB_CONFIG = {
        "host" : os.getenv("DB_HOST", "localhost"),
        "user" : os.getenv("DB_USER", "root"),
        "password" : os.getenv("DB_PASSWORD", ""),
        "database" : os.getenv("DB_DTABASE", "pengaduan_db")
    }
    
    SECRET_KEY = "$DannDevv26"