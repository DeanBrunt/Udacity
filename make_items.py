from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Item, User, Base

engine = create_engine('postgresql+psycopg2://postgres:waitrose702@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

user = User(id=1, name="Dean Brunt", email="deanbrunt@googlemail.com")

session.add(user)
session.commit()

category1 = Category(name="Shoes", owner_id="1")

session.add(category1)
session.commit()

Item1 = Item(name="brogues", description="broguey boys",
                     price="7.50", category=category1, owner_id="1")

session.add(Item1)
session.commit()

category2 = Category(name="Jumpers", owner_id="1")

session.add(category2)
session.commit()

Item2 = Item(name="turtle neck", description="turtles",
                     price="15.49", category=category2, owner_id="1")

session.add(Item2)
session.commit()

Item3 = Item(name="crew neck", description="crew",
                     price="12.49", category=category2, owner_id="1")

session.add(Item3)
session.commit()

category3 = Category(name="Uncategorised", hidden=True, owner_id="1")

session.add(category3)
session.commit()
