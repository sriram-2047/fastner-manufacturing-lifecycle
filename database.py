import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("NOW_REGION"))

if IS_VERCEL:
    DB_DIR = "/tmp"
    DEFAULT_DB_PATH = os.path.join(DB_DIR, "fastener.db")
    repo_db = os.path.join(BASE_DIR, "database", "fastener.db")
    if os.path.exists(repo_db) and not os.path.exists(DEFAULT_DB_PATH):
        try:
            shutil.copy2(repo_db, DEFAULT_DB_PATH)
        except Exception as e:
            print(f"Error copying bundled db to /tmp: {e}")
else:
    DB_DIR = os.path.join(BASE_DIR, "database")
    os.makedirs(DB_DIR, exist_ok=True)
    DEFAULT_DB_PATH = os.path.join(DB_DIR, "fastener.db")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Ensure proper sqlite URL format
if DATABASE_URL.startswith("sqlite:///") and not os.path.isabs(DATABASE_URL.replace("sqlite:///", "")):
    rel_path = DATABASE_URL.replace("sqlite:///", "")
    abs_path = os.path.join(BASE_DIR, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    DATABASE_URL = f"sqlite:///{abs_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db(auto_seed=True):
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    if auto_seed:
        try:
            from models import Batch
            count = db_session.query(Batch).count()
            if count == 0:
                import seed
                seed.run_seed(force=False)
        except Exception as e:
            print(f"Auto-seed error: {e}")
