import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()
class User(Base):
    __tablename__ = 'user'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable = False)
    picture = Column(String(250))

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,
           'picture'      : self.picture,
       }
class Restaurant(Base):
	__tablename__ = 'restaurant'
	
	name = Column(
		String(80), nullable = False)

	id = Column(
		Integer, primary_key = True)

	user = relationship(User)
	user_id = Column(Integer, ForeignKey('user.id'))
	
	@property
	def serialize(self):
		return {'name': self.name,'id': self.id,}
	@property
	def serialize(self):
		return {'name': self.name,}
	

class MenuItem(Base):
	__tablename__ = 'menu_item'

	name = Column(
		String(80), nullable = False)

	id = Column(
		Integer, primary_key = True)

	course = Column(
		String(250))

	description = Column(
		String(250))

	price = Column(
		String(8))

	restaurant_id = Column(
		Integer, ForeignKey(Restaurant.id))

	restaurant = relationship(Restaurant)
	user = relationship(User)
	user_id = Column(Integer, ForeignKey('user.id'))
	

	@property
	def serialize(self):
		return {'name': self.name,
		 'description': self.description,
		 'id': self.id,
		 'price': self.price,
		 'course': self.course,}

####### insert at end of file ##########

engine = create_engine(
	'sqlite:///restaurantmenuwithusers.db')

Base.metadata.create_all(engine)
