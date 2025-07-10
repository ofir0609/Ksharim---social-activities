from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from datetime import datetime
from flask_login import UserMixin
import hashlib

Base = declarative_base()


class Admin(Base):
    __tablename__ = 'admin'

    AdminID = Column(Integer, primary_key=True)
    AdminUsername = Column(String(100), unique=True, nullable=False)
    AdminPassword = Column(String(100), nullable=False)

    def __repr__(self):  # representation for the Admin object
        return f'Admin: {self.AdminUsername}'


class User(UserMixin, Base):
    __tablename__ = 'user'

    UserID = Column(Integer, primary_key=True)
    Username = Column(String(100), unique=True, nullable=False)
    Email = Column(String(320), unique=True, nullable=False)
    Password = Column(String(64), nullable=False)  # Length for hashed passwords
    Age = Column(Integer, nullable=False)
    Bio = Column(Text, nullable=True)
    Deleted = Column(Boolean, nullable=False, default=False)

    UserCityID = Column(Integer, ForeignKey('city.CityID'), nullable=True)
    user_city = relationship('City', backref='users')

    def __repr__(self):  # representation for the User object
        return f'<Username: {self.Username}, Age: {self.Age}, User ID: {self.UserID}>'

    def get_id(self):
        return str(self.UserID)


class Activity(Base):
    __tablename__ = 'activity'

    ActivityID = Column(Integer, primary_key=True)
    ActivityName = Column(String(100), nullable=False)
    Description = Column(String(2000), nullable=False)
    AgeRangeMax = Column(Integer, nullable=True)
    AgeRangeMin = Column(Integer, nullable=True)
    ActivityDate = Column(Date, nullable=True)
    Deleted = Column(Boolean, nullable=False, default=False)

    # 'fk' stands for 'foreign key'
    ActivityCityID = Column(Integer, ForeignKey('city.CityID'), name='fk_activity_city_activity', nullable=True)
    activity_city = relationship('City', backref='activities')
    CreatorID = Column(Integer, ForeignKey('user.UserID'), name='fk_creator_activity', nullable=False)
    creator = relationship('User', backref='activities')

    def __repr__(self):  # representation for the Activity object
        city_name = None
        return f'<Name: {self.ActivityName}, ActivityCity: {city_name}, ' \
               f'Minimum Age:{self.AgeRangeMin}, Maximum Age: {self.AgeRangeMax}, ActivityID: {self.ActivityID},' \
               f'Date: {self.ActivityDate}>'  # If I wanted to shoed the creator too, I'd need a session


class Category(Base):
    __tablename__ = 'category'

    CategoryID = Column(Integer, primary_key=True)
    CategoryName = Column(String(100), unique=True, nullable=False)
    Deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'CategoryName: {self.CategoryName}, CategoryID: {self.CategoryID}'


class City(Base):  # Defining the city table
    __tablename__ = 'city'

    CityID = Column(Integer, primary_key=True)
    CityName = Column(String(100), unique=True, nullable=False)
    Deleted = Column(Boolean, nullable=False, default=False)  # what should be inside the brackets?

    def __repr__(self):  # representation for the User object
        return f'CategoryName: {self.CityName}, CategoryID: {self.CityID}'


class Participant(Base):  # Defining the Participants table (many-to-many relationship between users and
    # activities they are signed for)
    __tablename__ = 'participant'

    ParticipantID = Column(Integer, primary_key=True)
    UserID = Column(Integer, ForeignKey('user.UserID'), name='fk_user_participant')
    ActivityID = Column(Integer, ForeignKey('activity.ActivityID'), name='fk_activity_participant')

    user = relationship('User', backref='users_activities')
    activity = relationship('Activity', backref='participants')


class JoinRequest(Base):
    __tablename__ = 'join_request'

    JoinRequestID = Column(Integer, primary_key=True)
    UserID = Column(Integer, ForeignKey('user.UserID'), name='fk_user_join_request')
    ActivityID = Column(Integer, ForeignKey('activity.ActivityID'), name='fk_activity_join_request')

    user = relationship('User', backref='users_wanted_activities')
    activity = relationship('Activity', backref='wanting_to_join')


class ActivityCategory(Base):
    __tablename__ = 'activity_category'

    ActivityCategoryID = Column(Integer, primary_key=True)
    ActivityID = Column(Integer, ForeignKey('activity.ActivityID'), name='fk_activity_activity_category')
    CategoryID = Column(Integer, ForeignKey('category.CategoryID'), name='fk_category_activity_category')

    activity = relationship('Activity', backref='categories')
    category = relationship('Category', backref='activities')


class UserCategory(Base):
    __tablename__ = 'user_category'

    UserCategoryID = Column(Integer, primary_key=True)
    UserID = Column(Integer, ForeignKey('user.UserID'), name='fk_user_user_category')
    CategoryID = Column(Integer, ForeignKey('category.CategoryID'), name='fk_category_user_category')

    user = relationship('User', backref='categories')
    category = relationship('Category', backref='users')


def is_only_english_letters(text: str) -> bool:
    english_alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for char in text:
        if char not in english_alphabet:
            return False
    return True


def is_only_english_letters_and_digits(text: str) -> bool:
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for char in text:
        if char not in allowed_chars:
            return False
    return True


def input_for_user_check(session, Username=None, Password=None, Email=None, UserCityID=None, Age=None, Bio=None,
                         Deleted=False, id_for_updating=None):
    if not Username:
        return {"is_valid": False, "message": 'Username Needed'}

    if not is_only_english_letters(Username):
        return {"is_valid": False, "message": 'Username should only contain English letters'}

    existing_user = session.query(User).filter_by(Username=Username, Deleted=False).\
        filter(User.UserID!=id_for_updating).first()
    if existing_user:
        return {"is_valid": False, "message": 'Username already used'}

    if not Password:
        return {"is_valid": False, "message": 'Password Needed'}

    if len(Password) < 4:
        return {"is_valid": False, "message": 'Password too short'}

    if not is_only_english_letters_and_digits(Password):
        return {"is_valid": False, "message": 'Password should only contain English letters and numbers'}

    if not Email:
        return {"is_valid": False, "message": 'Email Needed'}

    existing_email = session.query(User).filter_by(Email=Email, Deleted=False).\
        filter(User.UserID!=id_for_updating).first()
    if existing_email:
        return {"is_valid": False, "message": 'Email already used'}

    if not Age:
        return {"is_valid": False, "message": 'Age Needed'}

    if not str(Age).isdigit():
        return {"is_valid": False, "message": 'Age not valid'}
    Age = int(Age)
    if Age < 0 or Age > 120:
        return {"is_valid": False, "message": 'Age not valid'}

    if UserCityID:
        existing_city = session.query(City).filter_by(CityID=UserCityID, Deleted=False).first()
        if not existing_city:
            return {"is_valid": False, "message": 'No such city'}

    if not boolean_check(Deleted)["is_valid"]:
        return {"is_valid": False, "message": 'Invalid deleted'}

    return {"is_valid": True}


def input_for_activity_check(session, ActivityName=None, Description=None, AgeRangeMin=None, AgeRangeMax=None,
                             ActivityDate=None, ActivityCityID=None, CreatorID=None, Deleted=False, id_for_updating=None):
    if not ActivityName:
        return {"is_valid": False, 'message': 'ActivityName needed'}

    elif not Description:
        return {"is_valid": False, 'message': 'Description needed'}

    if not CreatorID:
        return {"is_valid": False, 'message': "CreatorID needed"}

    creator = session.query(User).filter_by(UserID=CreatorID, Deleted=False).first()
    if not creator:
        return {"is_valid": False, 'message': "no such user"}

    creator_age = creator.Age
    AgeCheck = age_range_check(AgeRangeMin, AgeRangeMax, creator_age)
    if not AgeCheck["is_valid"]:
        return {"is_valid": False, 'message': AgeCheck["message"]}

    DateCheck = date_check(ActivityDate)
    if not DateCheck["is_valid"]:
        return {"is_valid": False, 'message': "Invalid date, write valid date in this format YYYY-MM-DD"}

    if ActivityCityID:
        city = session.query(City).filter_by(CityID=ActivityCityID, Deleted=False).first()
        if not city:
            return {"is_valid": False, 'message': "no such city"}

    if not boolean_check(Deleted)["is_valid"]:
        return {"is_valid": False, "message": 'Invalid deleted'}

    return {"is_valid": True, "ActivityDate": DateCheck["date"]}


def input_for_category_check(session, CategoryName=None, Deleted=False, id_for_updating=None):
    if not CategoryName:
        return {"is_valid": False, "message": "category name needed"}
    existing_category = session.query(Category).filter_by(CategoryName=CategoryName.lower(), Deleted=False).\
        filter(Category.CategoryID != id_for_updating).first()
    if existing_category:
        return {"is_valid": False, "message": "category already exists"}

    if not boolean_check(Deleted)["is_valid"]:
        return {"is_valid": False, "message": 'Invalid deleted'}

    return {"is_valid": True}


def input_for_city_check(session, CityName=None, Deleted=False, id_for_updating=None):
    if not CityName:
        return {"is_valid": False, "message": "city name needed"}
    existing_city = session.query(City).filter_by(CityName=CityName, Deleted=False).\
        filter(City.CityID != id_for_updating).first()
    if existing_city:
        return {"is_valid": False, "message": "city already exists"}

    if not boolean_check(Deleted)["is_valid"]:
        return {"is_valid": False, "message": 'Invalid deleted'}

    return {"is_valid": True}


def input_for_join_request_check(session, UserID=None, ActivityID=None, id_for_updating=None):
    existing_user = session.query(User).filter_by(UserID=UserID, Deleted=False).first()
    if not existing_user:
        return {"is_valid": False, "message": "no such user"}

    existing_activity = session.query(Activity).filter_by(ActivityID=ActivityID, Deleted=False).first()
    if not existing_activity:
        return {"is_valid": False, "message": "no such activity"}

    existing_participant = session.query(Participant).filter_by(UserID=UserID, ActivityID=ActivityID).first()
    if existing_participant:
        return {"is_valid": False, "message": "Already a participant"}

    existing_join_request = session.query(JoinRequest).filter_by(UserID=UserID, ActivityID=ActivityID).\
        filter(JoinRequest.JoinRequestID != id_for_updating).first()
    if existing_join_request:
        return {"is_valid": False, "message": "Join request already exists"}

    age_check_dict = age_range_check(existing_activity.AgeRangeMin, existing_activity.AgeRangeMax, existing_user.Age)
    if not age_check_dict["is_valid"]:
        return {"is_valid": False, "message": age_check_dict["message"]}

    return {"is_valid": True}


def input_for_participant_check(session, UserID=None, ActivityID=None, id_for_updating=None):
    existing_user = session.query(User).filter_by(UserID=UserID, Deleted=False).first()
    if not existing_user:
        return {"is_valid": False, "message": "no such user"}

    existing_activity = session.query(Activity).filter_by(ActivityID=ActivityID, Deleted=False).first()
    if not existing_activity:
        return {"is_valid": False, "message": "no such activity"}

    existing_participant = session.query(Participant).filter_by(UserID=UserID, ActivityID=ActivityID).\
        filter(Participant.ParticipantID != id_for_updating).first()
    if existing_participant:
        return {"is_valid": False, "message": "Participant already exists"}

    age_check_dict = age_range_check(existing_activity.AgeRangeMin, existing_activity.AgeRangeMax, existing_user.Age)
    if not age_check_dict["is_valid"]:
        return {"is_valid": False, "message": age_check_dict["message"]}

    return {"is_valid": True}


def input_for_activity_category_check(session, ActivityID=None, CategoryID=None, id_for_updating=None):
    existing_activity = session.query(Activity).filter_by(ActivityID=ActivityID, Deleted=False).first()
    if not existing_activity:
        return {"is_valid": False, "message": "no such activity"}

    existing_category = session.query(Category).filter_by(CategoryID=CategoryID, Deleted=False).first()
    if not existing_category:
        return {"is_valid": False, "message": "no such category"}

    existing_activity_category = session.query(ActivityCategory).filter_by(ActivityID=ActivityID, CategoryID=CategoryID)\
        .filter(ActivityCategory.ActivityCategoryID != id_for_updating).first()
    if existing_activity_category:
        return {"is_valid": False, "message": "activity category already exists"}

    return {"is_valid": True}


def input_for_user_category_check(session, UserID=None, CategoryID=None, id_for_updating=None):
    existing_user = session.query(User).filter_by(UserID=UserID, Deleted=False).first()
    if not existing_user:
        return {"is_valid": False, "message": "no such user"}

    existing_category = session.query(Category).filter_by(CategoryID=CategoryID, Deleted=False).first()
    if not existing_category:
        return {"is_valid": False, "message": "no such category"}

    existing_user_category = session.query(UserCategory).filter_by(UserID=UserID, CategoryID=CategoryID).\
        filter(UserCategory.UserCategoryID != id_for_updating).first()
    if existing_user_category:
        return {"is_valid": False, "message": "The user already has the category"}

    return {"is_valid": True}


MAIN_TABLES = {
    'User': {"table": User, "input_check": input_for_user_check,
             "columns": ("Username", "Email", "Password", "Age", "Bio", "Deleted", "UserCityID")},
    'Activity': {"table": Activity, "input_check": input_for_activity_check,
                 "columns": ("ActivityName", "Description", "AgeRangeMax", "AgeRangeMin", "ActivityDate", "Deleted",
                             "ActivityCityID", "CreatorID")},
    'Category': {"table": Category, "input_check": input_for_category_check, "columns": ("CategoryName", "Deleted")},
    'City': {"table": City, "input_check": input_for_city_check, "columns": ("CityName", "Deleted")}
}

RELATIONSHIP_TABLES = {
    'Participant': {"table": Participant, "input_check": input_for_participant_check,
                    "columns": ("UserID", "ActivityID")},
    'JoinRequest': {"table": JoinRequest, "input_check": input_for_join_request_check,
                    "columns": ("UserID", "ActivityID")},
    'ActivityCategory': {"table": ActivityCategory, "input_check": input_for_activity_category_check,
                         "columns": ("ActivityID", "CategoryID")},
    'UserCategory': {"table": UserCategory, "input_check": input_for_user_category_check,
                     "columns": ("UserID", "CategoryID")}
}

def encrypt_password(password):
    # Use hashlib to create a hash of the password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    return hashed_password


def get_city_name_for_id(session, city_id):  # Input should not be none
    city = session.query(City).filter_by(CityID=city_id, Deleted=False).first()
    if city:
        return city.CityName
    return "Unknown city"


def get_category_name_for_id(session, category_id):
    category = session.query(Category).filter_by(CategoryID=category_id, Deleted=False).first()
    if category:
        return category.CategoryName
    return "Unknown category"


def get_user_name_for_id(session, user_id):
    user = session.query(User).filter_by(UserID=user_id, Deleted=False).first()
    if user:
        return user.Username
    return None


def get_category_names_for_user(session, user):
    # Fetches category names associated with a user.
    categories = user.categories  # Get all categories associated with the user
    category_names = [get_category_name_for_id(session, category.CategoryID) for category in categories]
    return category_names


def get_category_names_for_activity(session, activity):
    categories = activity.categories
    category_names = [get_category_name_for_id(session, category.CategoryID) for category in categories]
    return category_names


def user_age_check(text_age):
    try:
        Age = int(text_age)
        if Age < 0 or Age > 120:
            return {"is_valid": False}
    except ValueError:
        return {"is_valid": False}
    return {"is_valid": True, "Age": Age}


def age_range_check(Str_MinimumAge, Str_MaximumAge, current_user_age):
    MinimumAge = None
    MaximumAge = None
    try:
        if Str_MaximumAge:
            if not str(Str_MaximumAge).isdigit():
                return {"is_valid": False, "message": "age limits must be positive whole numbers"}
            MaximumAge = int(Str_MaximumAge)
            if MaximumAge > 120 or MaximumAge < 0:
                return {"is_valid": False, "message": "age limits must be between 0-120"}
            if current_user_age > MaximumAge:
                print(f"current_user_age: {current_user_age}, MaximumAge: {MaximumAge}")
                return {"is_valid": False, "message": "the limits do not fit the creator"}

        if Str_MinimumAge:
            if not str(Str_MinimumAge).isdigit():
                return {"is_valid": False, "message": "age limits must be positive whole numbers"}
            MinimumAge = int(Str_MinimumAge)
            if MinimumAge > 120 or MinimumAge < 0:
                return {"is_valid": False, "message": "age limits must be between 0-120"}
            if current_user_age < MinimumAge:
                print(f"current_user_age: {current_user_age}, MinimumAge: {MinimumAge}")
                return {"is_valid": False, "message": "the limits do not fit the creator"}

        if MinimumAge and MaximumAge and MaximumAge < MinimumAge:
            return {"is_valid": False, "message": "Mimimum above Maximum"}

    except ValueError:
        return {"is_valid": False, "message": "Age not integer"}

    return {"is_valid": True, "max": MinimumAge, "min": MaximumAge}


def excess_columns_check(table_name, values_for_table_dict: dict):
    # returns if the dictionary contains columns that the table doesn't have, and if yes, which one/s
    # no need to check for key duplication - it's not possible. And duplication is checked in text_to_dictionary
    if table_name not in MAIN_TABLES.keys() and table_name not in RELATIONSHIP_TABLES.keys():
        return {"is_valid": False, "message": "No such table"}
    table_dict = MAIN_TABLES[table_name] if table_name in MAIN_TABLES.keys() else RELATIONSHIP_TABLES[table_name]
    columns = table_dict["columns"]
    excess = []
    for key in values_for_table_dict:
        if key not in columns and key != "id_for_updating":
            excess.append(key)
    if excess:
        return {"is_valid": False, "message": f"{table_name} doesn't have column/s named {[key for key in excess]}"}
    return {"is_valid": True}


def is_valid_date(date_string):
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def date_check(Str_ActivityDate):
    ActivityDate = None
    if Str_ActivityDate:
        if not is_valid_date(Str_ActivityDate):
            return {"is_valid": False, "message": "invalid date"}
        else:
            ActivityDate = datetime.strptime(Str_ActivityDate, '%Y-%m-%d').date()
    return {"is_valid": True, "date": ActivityDate}


def boolean_check(var):
    if var in [True, "true", "True"]:
        return {"is_valid": True, "value": True}
    if var in [False, "false", "False"]:
        return {"is_valid": True, "value": False}
    return {"is_valid": False}
