from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = "mysql+mysqlconnector://root:AkTAMIL7708#@localhost:3306/kids"  # Change this
# DATABASE_URL = "postgresql+asyncpg://kidsforai_user:@dpg-d27ggtp5pdvs73fjots0-a.oregon-postgres.render.com:5432/kidsforai"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

