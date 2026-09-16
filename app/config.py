import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    MAX_ACTIVE_LOANS = 3
    DATABASE_PATH = DB_PATH
