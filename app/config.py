import os

API_TOKEN = os.getenv("API_TOKEN", "dev-token")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cra.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

MAX_BODY_BYTES = 64 * 1024
