import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime

Base = declarative_base()

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	email = Column(String(250), nullable = False)
	picture = Column(String(250))

class Category(Base):
	__tablename__ = 'category'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	hidden = Column(Boolean, default=False)
	owner_id = Column(Integer, ForeignKey('user.id'))
	owner = relationship(User)
	@property
	def serialize(self):
		return {
			'id' : self.id,
			'name' : self.name,
		}

class Item(Base):
	__tablename__ = 'item'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	category_id = Column(Integer, ForeignKey('category.id'))
	category = relationship(Category)
	owner_id = Column(Integer, ForeignKey('user.id'))
	owner = relationship(User)
	description = Column(String(1000), nullable=False)
	price = Column(Float, nullable=False)
	added = Column(DateTime, default=datetime.datetime.now())

	@property
	def serialize(self):
		return {
			'id' : self.id,
			'name' : self.name,
			'category_id' : self.category_id,
			#'owner_id' : self.owner_id,
			'description' : self.description,
			'price' : self.price,
		}


engine = create_engine('postgresql+psycopg2://postgres:waitrose702@localhost/catalog')
Base.metadata.create_all(engine)
