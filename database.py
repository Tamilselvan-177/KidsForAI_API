from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = "mysql+mysqlconnector://root:AkTAMIL7708#@localhost:3306/kids"  # Change this
# DATABASE_URL = "mysql+mysqlconnector://if0_39623100:Q6BS7JoUA1c5WKh@sql311.infinityfree.com:3306/if0_39623100_XXX"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

