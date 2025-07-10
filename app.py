from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user  # , UserMixin
from database_models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os
import msvcrt
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'd089e0eb4455d6871fc0a19e29d2998e'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/website_database.db'

# Engine initialization
engine = create_engine('sqlite:///instance/website_database.db')
Session = sessionmaker(bind=engine)
session = Session()
# Base = declarative_base()

login_manager = LoginManager(app)
login_manager.login_view = 'sign_in'


@login_manager.user_loader
def load_user(user_id):
    try:
        return session.get(User, user_id)
    except Exception as e:
        print(f"Error loading user: {e}")
        return None


@app.route('/', methods=['POST', 'GET'])
def index():
    try:
        if request.method == 'POST':  # TODO add something in home page?
            return "No, what are you doing."
        else:
            return render_template('index.html')
    except Exception as e:
        print(f"Error in home page", str(e))  # TODO Should I redirect the user? I fear the same error returning.
        return None


@app.route('/sign_up', methods=['POST', 'GET'])  # This is the sign-up page
def sign_up():
    try:
        if request.method == 'POST':
            Username = request.form['Username']
            Email = request.form['Email']
            Password = request.form['Password']
            UserCity = request.form['UserCity']
            TextAge = request.form['Age']
            Bio = request.form['Bio']

            existing_city = session.query(City).filter_by(CityName=UserCity, Deleted=False).first()
            if UserCity and not existing_city:
                flash('Unknown city', 'error')
                return render_template('sign_up.html', Username=Username, Email=Email, Password=Password,
                                       UserCity=UserCity, Age=TextAge, Bio=Bio)
            UserCityID = existing_city.CityID if existing_city else None

            Age = None
            if TextAge:
                try:
                    Age = int(TextAge)
                except ValueError:
                    flash('Age should be a whole number', 'error')
                    return render_template('sign_up.html', Username=Username, Email=Email, Password=Password,
                                           UserCity=UserCity, Age=TextAge, Bio=Bio)

            check_dict = input_for_user_check(session=session, Username=Username, Email=Email, Password=Password,
                                              UserCityID=UserCityID, Age=Age, Bio=Bio)

            hashed_password = encrypt_password(Password)

            if check_dict["is_valid"]:
                new_user = User(Username=Username, Email=Email, Password=hashed_password, UserCityID=UserCityID,
                                Age=Age, Bio=Bio)
                session.add(new_user)
                session.commit()
                return redirect('/sign_in')
            else:
                flash(check_dict["message"], 'error')
            return render_template('sign_up.html', Username=Username, Email=Email, Password=Password, UserCity=UserCity,
                                   Age=TextAge, Bio=Bio)
        else:
            return render_template('sign_up.html')
    except SQLAlchemyError as e:
        flash("Database error", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_up'))
    except Exception as e:
        print(f"Error in sign up page", str(e))
        return None


@app.route('/sign_in', methods=['POST', 'GET'])  # This is the sign-up page
def sign_in():
    try:
        if request.method == 'POST':
            Username = request.form['Username']
            Password = request.form['Password']
            if not Username:
                return render_template('sign_in.html', error='Enter your username', Password=Password)
            if not Password:
                return render_template('sign_in.html', error='Enter your password, if you forgot it, contact us',
                                       Username=Username)

            user = session.query(User).filter_by(Username=Username, Deleted=False).first()
            if not user:
                return render_template('sign_in.html', error='No such user', Username=Username, Password=Password)
            elif encrypt_password(Password) != user.Password:
                return render_template('sign_in.html', error='incorrect password', Username=Username, Password=Password)
            else:
                login_user(user)
                return redirect(url_for(f'profile', user_id=user.UserID))
        return render_template('sign_in.html')
    except SQLAlchemyError as e:
        flash("Database error", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in sign in page", str(e))
        return None


@app.route('/sign_out')
@login_required  # This decorator ensures the user is logged in
def sign_out():
    try:
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('index'))  # Redirect to the homepage or any other page
    except Exception as e:
        print(f"Error in sign out page", str(e))
        return None


@app.route('/profile/<int:user_id>')
def profile(user_id):
    try:
        if request.method == 'POST':
            return "No, what are you doing."  # TODO allow editing one's info.
        else:
            user = session.query(User).filter_by(UserID=user_id, Deleted=False).first()
            if user:
                user_data = {  # this method avoids sending the password
                    'UserID': user.UserID,
                    'Username': user.Username,
                    'Age': user.Age,
                    'Bio': user.Bio, }
                city_name = get_city_name_for_id(session, user.UserCityID)
                category_names = get_category_names_for_user(session, user)
                return render_template('profile.html', user_data=user_data, city_name=city_name,
                                       category_names=category_names)
            else:
                return "User not found", 404
    except SQLAlchemyError as e:
        flash("Database error", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error in profile page", str(e))
        return None


@app.route('/activity_list')
def activity_list():
    try:
        activities = session.query(Activity).filter_by(Deleted=False).all()
        return render_template('activity_list.html', activities=activities)
    except SQLAlchemyError as e:
        flash("Database error while creating your activity", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error in activity list page", str(e))
        return None


@app.route('/activity/<int:activity_id>')
def activity(activity_id):
    try:
        activity = session.query(Activity).filter_by(ActivityID=activity_id, Deleted=False).one()
        if not activity:
            flash('Activity not found', 'error')
            return redirect(url_for('my_activities'))

        creator_name = get_user_name_for_id(session, activity.CreatorID)

        city = session.query(City).filter_by(CityID=activity.ActivityCityID, Deleted=False).one_or_none()
        city_name = city.CityName if city else None

        date = activity.ActivityDate if activity.ActivityDate else None

        category_names = get_category_names_for_activity(session, activity)

        participants = session.query(User).join(Participant, User.UserID == Participant.UserID) \
            .join(Activity, Activity.ActivityID == Participant.ActivityID) \
            .filter(Participant.ActivityID == activity.ActivityID) \
            .filter(User.Deleted == False, Activity.Deleted == False) \
            .with_entities(User.UserID, User.Username).all()  # List of the participants in the activity

        if activity:
            if current_user.is_authenticated and int(current_user.UserID) == int(activity.CreatorID):
                join_requests = session.query(JoinRequest).filter_by(ActivityID=activity_id).all()
                complete_join_requests = []
                for join_request in join_requests:
                    username = get_user_name_for_id(session, join_request.UserID)
                    complete_join_requests.append({"join_request": join_request, "username": username})
                return render_template('activity.html', activity=activity, creator_name=creator_name,
                                       creator_id=activity.CreatorID, city=city_name, date=date,
                                       category_names=category_names,
                                       participants=participants, complete_join_requests=complete_join_requests)
            else:
                return render_template('activity.html', activity=activity, creator_name=creator_name,
                                       creator_id=activity.CreatorID, city=city_name, date=date,
                                       category_names=category_names,
                                       participants=participants)
    except SQLAlchemyError as e:
        flash("Database error", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('my_activities'))
    except Exception as e:
        print(f"Error in activity page", str(e))
        return None


@app.route('/create_activity', methods=["GET", "POST"])
@login_required
def create_activity():
    try:
        if request.method == 'POST':
            CreatorID = current_user.UserID
            ActivityName = request.form['ActivityName']
            Description = request.form['Description']
            Str_MinimumAge = request.form['MinimumAge']
            Str_MaximumAge = request.form['MaximumAge']
            Str_ActivityDate = request.form['ActivityDate']
            ActivityCity = request.form['ActivityCity']

            ActivityCityID = None
            if ActivityCity:
                existing_city = session.query(City).filter_by(CityName=ActivityCity, Deleted=False).first()
                if not existing_city:
                    flash('Unknown city', 'error')
                    return render_template('create_activity.html', ActivityName=ActivityName, Description=Description,
                                           MinimumAge=Str_MinimumAge, MaximumAge=Str_MaximumAge,
                                           ActivityDate=Str_ActivityDate, ActivityCity=ActivityCity)
                ActivityCityID = existing_city.CityID

            check_dict = input_for_activity_check(session=session, ActivityName=ActivityName, Description=Description,
                                                  AgeRangeMin=Str_MinimumAge, AgeRangeMax=Str_MaximumAge,
                                                  ActivityDate=Str_ActivityDate, ActivityCityID=ActivityCityID,
                                                  CreatorID=CreatorID)

            if check_dict["is_valid"]:
                try:
                    with session.begin_nested():  # Start a nested transaction. It avoids a scenario where
                        # the activity is created, but the creator, for some reason, isn't added as a participant
                        new_activity = Activity(CreatorID=CreatorID, ActivityName=ActivityName, Description=Description,
                                                AgeRangeMin=Str_MinimumAge, AgeRangeMax=Str_MaximumAge,
                                                ActivityDate=check_dict["ActivityDate"], ActivityCityID=ActivityCityID)
                        session.add(new_activity)
                        session.flush()  # Flush changes to get the ActivityID before committing
                        new_participant = Participant(UserID=CreatorID, ActivityID=new_activity.ActivityID)
                        session.add(new_participant)
                        session.commit()  # Commit the nested transaction
                        flash('The activity was created successfully, you can view it in your activities', 'success')
                except SQLAlchemyError:
                    session.rollback()  # Rollback changes if there's an error with the database
                    flash('There was an issue creating your activity', 'error')
            else:
                flash(check_dict["message"], 'error')
            return render_template('create_activity.html', ActivityName=ActivityName, Description=Description,
                                   MinimumAge=Str_MinimumAge, MaximumAge=Str_MaximumAge, ActivityDate=Str_ActivityDate,
                                   ActivityCity=ActivityCity)
        return render_template('create_activity.html')
    except SQLAlchemyError as e:
        flash("Database error while creating your activity", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('index'))
    # except Exception as e:
    #    print(f"Error in create activity page", str(e))
    #    return redirect(url_for('index'))


@app.route('/join_activity/<int:activity_id>', methods=['GET', 'POST'])
@login_required
def join_activity(activity_id):
    try:
        user_id = current_user.UserID
        check_dict = input_for_join_request_check(session=session, UserID=user_id, ActivityID=activity_id)
        if check_dict["is_valid"]:
            new_join_request = JoinRequest(UserID=user_id, ActivityID=activity_id)
            try:
                session.add(new_join_request)
                session.commit()
                flash('Your request to join the activity has been submitted.', 'success')
                return redirect(request.referrer or url_for('activity_list'))
            except Exception:
                return 'There was an issue adding your request'
        if check_dict["message"] == "Join request already exists":
            flash('Your request to join the activity has been submitted.', 'success')
            return redirect(request.referrer or url_for('activity_list'))

        else:
            flash(check_dict["message"], 'error')
        return redirect(request.referrer or url_for('activity_list'))
    except SQLAlchemyError as e:
        flash("Database error with the join request", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in join activity route", str(e))
        return None


@app.route('/accept_request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    try:
        request = session.query(JoinRequest).filter_by(JoinRequestID=request_id).first()
        activity = session.query(Activity).filter_by(ActivityID=request.ActivityID, Deleted=False).first()
        UserID = request.UserID
        ActivityID = request.ActivityID
        if current_user.UserID == activity.CreatorID:
            check_dict = input_for_participant_check(session, UserID=UserID, ActivityID=ActivityID)
            if check_dict["is_valid"]:
                try:
                    with session.begin_nested():  # Start a nested transaction
                        # Add the user to the participants
                        participant = Participant(UserID=request.UserID, ActivityID=request.ActivityID)
                        session.add(participant)
                        # Remove the request
                        session.delete(request)
                        session.commit()  # Commit the nested transaction
                        flash('Request accepted', 'success')
                except SQLAlchemyError:
                    session.rollback()  # Rollback changes if there's an error with the database
                    flash('Error in accepting the request', 'error')
            else:
                flash(check_dict["message"], 'error')
        else:
            flash('You are not authorized to perform this action', 'error')
        return redirect(url_for('activity', activity_id=ActivityID))
    except SQLAlchemyError as e:
        flash("Database error with accepting the join request", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in accept request route", str(e))
        return None


@app.route('/deny_request/<int:request_id>', methods=['POST'])
@login_required
def deny_request(request_id):
    try:
        request = session.query(JoinRequest).filter_by(JoinRequestID=request_id).first()
        if not request:
            flash('Request not found', 'error')
            redirect(url_for('my_activities'))

        activity = session.query(Activity).filter_by(ActivityID=request.ActivityID, Deleted=False).first()
        if not activity:
            flash('Woops, There is no such activity, maybe was deleted. We will delete that request.', 'error')
            session.delete(request)
            session.commit()
            redirect(url_for('my_activities'))

        user = session.query(User).filter_by(UserID=request.UserID, Deleted=False).first()
        if not user:
            flash('Woops, There is no such user, maybe was deleted. We will delete that request.', 'error')
            session.delete(request)
            session.commit()
        else:
            if current_user.UserID == activity.creator.UserID:
                # Remove the request
                session.delete(request)
                session.commit()
                flash('Request denied', 'success')
            else:
                flash('You are not authorized to perform this action', 'error')
        activity_id = request.ActivityID
        return redirect(url_for('activity', activity_id=activity_id))
    except SQLAlchemyError as e:
        flash("Database error with denying the request", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in deny request route", str(e))
        return None


@app.route('/my_activities', methods=["GET", "POST"])
@login_required
def my_activities():
    try:
        # Get the IDs of activities where the current user is a participant
        participant_values = session.query(Participant).filter_by(UserID=current_user.UserID).all()

        activity_ids = [participant.ActivityID for participant in participant_values]

        # Query the Activity table to get the activities where the current user is a participant
        activities = session.query(Activity).filter(Activity.ActivityID.in_(activity_ids),
                                                    Activity.Deleted == False).all()

        complete_activities = []
        for activity in activities:
            creator_name = get_user_name_for_id(session, activity.CreatorID)
            city = session.query(City).filter_by(CityID=activity.ActivityCityID, Deleted=False).first()
            city_name = city.CityName if city else None
            complete_activities.append({"activity": activity, "creator_name": creator_name, "city_name": city_name})
        return render_template('my_activities.html', complete_activities=complete_activities)
    except SQLAlchemyError as e:
        flash("Database error with my-activities page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in my-activities route", str(e))
        return None


@app.route('/user_categories', methods=["GET", "POST"])
@login_required
def user_categories():
    try:
        user_id = int(current_user.UserID)
        user = session.query(User).filter_by(UserID=user_id).first()

        if request.method == "POST":
            new_category_name = request.form.get("new_category")
            if new_category_name:
                # Check if the category exists
                category = session.query(Category).filter_by(CategoryName=new_category_name.lower()).first()
                if category:
                    # Add a new row to UserCategory table
                    check_dict = input_for_user_category_check(session, user_id, category.CategoryID)
                    if check_dict["is_valid"]:
                        user_category = UserCategory(UserID=user.UserID, CategoryID=category.CategoryID)
                        session.add(user_category)
                        session.commit()
                    else:
                        flash(check_dict["message"], 'error')
                else:
                    flash("We don't have this category in our lists, if you think it belongs there, contact us", 'error')

        # Remove category if remove button is clicked
        if "remove_category" in request.form:
            category_id_to_remove = request.form.get("remove_category")
            category_id_to_remove = session.query(Category).filter_by(CategoryID=category_id_to_remove).first()
            if category_id_to_remove:
                category_id_to_remove = int(request.form.get("remove_category"))
                user_category_to_remove = session.query(UserCategory).\
                    filter_by(UserID=user.UserID, CategoryID=category_id_to_remove).first()
                if user_category_to_remove:
                    session.delete(user_category_to_remove)
                    session.commit()

        user_category_list = session.query(UserCategory).filter_by(UserID=user.UserID).all()
        user_categories = [session.query(Category).filter_by(CategoryID=user_category.CategoryID, Deleted=False).first()
                           for user_category in user_category_list]

        return render_template('user_categories.html', user_categories=user_categories)
    except AttributeError:
        flash("You need to login first", 'error')
        return redirect(url_for('sign_in'))
    except SQLAlchemyError as e:
        flash("Database error with user-categories page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in user-categories route", str(e))
        return None


@app.route('/activity_categories/<int:activity_id>', methods=["GET", "POST"])
@login_required
def activity_categories(activity_id):
    try:
        user_id = int(current_user.UserID)
        activity = session.query(Activity).filter_by(ActivityID=activity_id).first()
        if not activity:
            flash('No such activity', 'error')
            return redirect(url_for('index'))
        if activity.CreatorID != user_id:
            flash('You are not the creator of the activity', 'error')
            return redirect(url_for('index'))

        if request.method == "POST":
            if "add_category" in request.form:
                new_category_name = request.form.get("new_category")
                if new_category_name:
                    # Check if the category exists
                    category = session.query(Category).filter_by(CategoryName=new_category_name.lower()).first()
                    if category:
                        # Add a new row to ActivityCategory table
                        check_dict = input_for_activity_category_check(session, activity_id, category.CategoryID)
                        if check_dict["is_valid"]:
                            activity_category = ActivityCategory(ActivityID=activity_id, CategoryID=category.CategoryID)
                            session.add(activity_category)
                            session.commit()
                        else:
                            flash(check_dict["message"], 'error')
                    else:
                        flash("We don't have this category in our lists, if you think it belongs there, contact us", 'error')

            if "remove_category" in request.form:
                category_id_to_remove = request.form.get("remove_category")
                category = session.query(Category).filter_by(CategoryID=category_id_to_remove).first()
                if category:
                    category_id_to_remove = int(category_id_to_remove)
                    activity_category_to_remove = session.query(ActivityCategory).\
                        filter_by(ActivityID=activity_id, CategoryID=category_id_to_remove).first()
                    if activity_category_to_remove:
                        session.delete(activity_category_to_remove)
                        session.commit()

            return redirect(url_for('activity_categories', activity_id=activity_id))

        activity_category_list = session.query(ActivityCategory).filter_by(ActivityID=activity_id).all()
        activity_categories = [session.query(Category).filter_by(CategoryID=activity_category.CategoryID, Deleted=False).first()
                           for activity_category in activity_category_list]

        return render_template('activity_categories.html', activity_id=activity_id, activity_categories=activity_categories)
    except AttributeError:
        flash("You need to login first", 'error')
        return redirect(url_for('sign_in'))
    except SQLAlchemyError as e:
        flash("Database error with activity-categories page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))
    except Exception as e:
        print(f"Error in activity-categories route", str(e))
        return None


def categories_to_ids(categories_string=None):
    print(f"categories_string |{categories_string}|")
    category_ids = []
    no_such_categories = []

    if categories_string and categories_string != "None":
        text_categories = categories_string.split(",")
        text_categories = [category.strip().lower() for category in text_categories]
        for category_name in text_categories:
            category_to_add = session.query(Category).filter_by(CategoryName=category_name, Deleted=False).first()
            if category_to_add:
                category_ids.append(category_to_add.CategoryID)
            else:
                no_such_categories.append(category_name)

    print(f"category_ids |{category_ids}|  no_such_categories |{no_such_categories}|")
    return [category_ids, no_such_categories]


def cities_to_ids(cities_string=None):
    city_ids = []
    no_such_cities = []

    if cities_string and cities_string!="None":
        text_cities = cities_string.split(",")
        text_cities = [city.strip() for city in text_cities]
        for city_name in text_cities:
            city_to_add = session.query(City).filter_by(CityName=city_name, Deleted=False).first()
            if city_to_add:
                city_ids.append(city_to_add.CityID)
            else:
                no_such_cities.append(city_name)

    print(f"city_ids |{city_ids}| no_such_cities |{no_such_cities}|")
    return [city_ids, no_such_cities]


def parse_date_range(date_txt):
    min_date = None
    max_date = None
    if date_txt.startswith("-"):
        max_date = date_txt[1:]
    elif date_txt.endswith("-"):
        min_date = date_txt[:-1]
    elif len(date_txt) > 10 and date_txt[10] == "-":
        min_date = date_txt[:-11]
        max_date = date_txt[11:]
    else:
        min_date = date_txt
        max_date = date_txt

    if (min_date and not is_valid_date(min_date)) or (max_date and not is_valid_date(max_date)):
        return {"is_valid": False, "message": "Put a valid date or date range. date format: YYYY-MM-DD"}

    if min_date and max_date and max_date < min_date:
        max_date, min_date = min_date, max_date

    return {"is_valid": True, "range": [min_date, max_date]}


def get_filtered_activities_check(min_date, max_date, categories, cities):
    category_ids, no_such_categories = categories_to_ids(categories)
    city_ids, no_such_cities = cities_to_ids(cities)

    # Base query to filter activities
    base_query = session.query(Activity).filter(Activity.Deleted == False)

    if min_date:
        date_range_check = parse_date_range(min_date)
        if not date_range_check["is_valid"]:
            return {"is_valid": False, "message": date_range_check["message"]}
        base_query = base_query.filter(Activity.ActivityDate >= min_date)

    if max_date:
        date_range_check = parse_date_range(max_date)
        if not date_range_check["is_valid"]:
            return {"is_valid": False, "message": date_range_check["message"]}
        base_query = base_query.filter(Activity.ActivityDate <= max_date)

    if category_ids:
        print("category_ids-True")
        # Join with ActivityCategory table and filter by category IDs
        base_query = base_query.join(ActivityCategory).filter(ActivityCategory.CategoryID.in_(category_ids))

    if city_ids:
        print("city_ids-True")
        # Filter by city IDs
        base_query = base_query.filter(Activity.ActivityCityID.in_(city_ids))

    # Execute the final query
    filtered_activities = base_query.all()
    return {"is_valid": True, "filtered": filtered_activities, "no_cities": no_such_cities,
            "no_categories": no_such_categories}


@app.route('/for_you', methods=['GET'])
@login_required
def for_you():
    print("~~~~~~~ 'For you' button pressed ~~~~~~~")
    try:
        user_id = int(current_user.UserID)
        user = session.query(User).filter_by(UserID=user_id).first()

        categories_list = get_category_names_for_user(session, user)
        categories = ", ".join(categories_list)

        city = session.query(City).filter_by(CityID=user.UserCityID).first()
        cities = city.CityName if city else ""

        first_date = datetime.datetime.today().strftime('%Y-%m-%d')

        return render_template('find_activities.html', first_date=first_date, cities=cities, categories=categories)
    except SQLAlchemyError as e:
        flash("Database error with for_you button", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('find_activities'))


@app.route('/find_activities', methods=['POST', 'GET'])
def find_activities(first_date=None, last_date=None, categories='', cities=''):
    try:
        if request.method == 'POST':
            first_date = request.form['First Date']
            last_date = request.form['Last Date']
            categories = request.form['Categories']
            cities = request.form['Cities']

            filtered_check = get_filtered_activities_check(first_date, last_date, categories, cities)
            if not filtered_check["is_valid"]:
                return render_template('/find_activities.html', first_date=first_date, last_date=last_date,
                                       categories=categories, cities=cities, date_error=filtered_check["message"])

            filtered_activities = filtered_check["filtered"]

            print(f"no_such_cities |{filtered_check['no_cities']}|")

            return render_template('/find_activities.html', first_date=first_date, last_date=last_date,
                                   categories=categories, cities=cities, searched=True, activities=filtered_activities,
                                   no_such_cities=filtered_check["no_cities"],
                                   no_such_categories=filtered_check["no_categories"])
        else:
            return render_template('/find_activities.html', first_date=first_date, last_date=last_date,
                                   categories=categories, cities=cities)
    except SQLAlchemyError as e:
        flash("Database error with find_activities page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('index'))


def get_users_private_chats(user_id):
    private_chats = []

    # Get a list of the files in private_chats folder
    folder_path = "private_chats"
    files = os.listdir(folder_path)

    for file_name in files:
        # Check if the file name has the user's ID
        if str(user_id) in file_name:
            # Extract the IDs from the file name
            chat_ids = file_name.split("_")[2:]
            other_user_id = chat_ids[0] if chat_ids[0] != str(user_id) else chat_ids[1]
            private_chats.append(other_user_id)

    return private_chats


def get_users_activities_ids(user_id):
    participant_list = session.query(Participant).filter_by(UserID=user_id).all()

    activity_ids = [participant.ActivityID for participant in participant_list]

    return activity_ids


def add_message_to_chat(file_name, message, sender_id):
    try:
        with open(file_name, 'a') as file:
            # Add metadata to the message
            full_message = add_metadata_to_message(message, str(sender_id))

            msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, os.path.getsize(file_name))  # Acquire lock

            file.write(full_message + '\n')  # Write the message to the file

            msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, os.path.getsize(file_name))  # Release lock

        print("Message added to chat successfully.")
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")


def add_metadata_to_message(message, sender_id):
    # Add metadata (sender_id and message length) to the message
    date = datetime.datetime.today().strftime('%d/%m/%Y')
    time = datetime.datetime.today().strftime('%H:%M')
    metadata = f"{sender_id.zfill(5)}|{str(len(message)).zfill(3)}|{date}|{time}"
    full_message = f"{message}|{metadata}|"
    print(f"full message~{full_message}~")
    return full_message


def get_messages_and_chatters_from_chat(file_name, max_messages):
    messages = []
    chatters = set()
    try:
        with open(file_name, 'r') as file:
            # Move the file pointer to the end of the file
            file.seek(0, 2)

            # going backwards, retrieving a message at a time, parsing it and saving it as (sender_id, message)
            position = file.seek(0, 2)
            while position > 0 and len(messages) < max_messages:
                # Move the file pointer 11 characters back from the current position
                position = max(0, position - 29)
                file.seek(position)

                # Read the last 10 characters (metadata)
                metadata = file.read(27)
                print(f"metadata~{metadata}~")
                sender_id, message_length, date, time = parse_metadata(metadata)

                chatters.add(sender_id)

                # Move the file pointer to the beginning of the message
                position = max(0, position - int(message_length) - 1)
                file.seek(position)

                # Read the message content
                message = file.read(int(message_length))

                # Add the message to the list
                print(f"append this message - ~{(sender_id, message)}~")
                messages.append((sender_id, message, date, time))
            # Reverse the order of messages to maintain chronological order
            messages.reverse()
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
    except Exception as e:
        print(e)
    return messages, chatters


def parse_metadata(metadata):
    parts = metadata.split('|')
    print(f"PARTS{parts}")
    sender_id = int(parts[0])
    message_length = int(parts[1])
    date = parts[2]
    time = parts[3]
    return sender_id, message_length, date, time


@login_required
@app.route('/chat_list')
def chat_list():
    try:
        user_id = int(current_user.UserID)

        # A chat file isn't created until there's a message between two users, until then, the chat shouldn't be presented
        private_chat_ids = get_users_private_chats(user_id)
        # Every activity has a chat
        activity_chat_ids = get_users_activities_ids(user_id)

        private_chats = []
        for private_chat_id in private_chat_ids:
            other_user = session.query(User).filter_by(UserID=private_chat_id).first()
            if other_user:
                private_chats.append((private_chat_id, other_user.Username))
        activity_chats = []
        for activity_chat_id in activity_chat_ids:
            activity_name = session.query(Activity).filter_by(ActivityID=activity_chat_id).first().ActivityName
            activity_chats.append((activity_chat_id, activity_name))
        return render_template('chat_list.html', private_chats=private_chats, activity_chats=activity_chats)
    #except AttributeError:
    #    flash("You need to login first", 'error')
    #    return redirect(url_for('sign_in'))
    except SQLAlchemyError as e:
        flash("Database error with chat_list page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('index'))


@login_required
@app.route('/activity_chat/<int:activity_id>', methods=['POST', 'GET'])
def activity_chat(activity_id):
    try:
        user_id = int(current_user.UserID)
    except AttributeError:
        flash("You must log in first", "error")
        return redirect(url_for('sign_in'))
    try:
        is_participant = session.query(Participant).filter_by(UserID=user_id, ActivityID=activity_id).first()
        if not is_participant:
            flash('You are not a participant in the activity', 'error')
            return redirect(url_for('chat_list'))

        file_name = f"activity_chats/activity_chat_{activity_id}"
        activity_name = session.query(Activity).filter_by(ActivityID=activity_id).first().ActivityName

        return chat(file_name=file_name, chat_name=activity_name, sender_id=user_id, kind="activity",
                    id_for_chat=activity_id)
    except SQLAlchemyError as e:
        flash("Database error with my activities page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))


@login_required
@app.route('/private_chat/<int:other_user_id>', methods=['POST', 'GET'])
def private_chat(other_user_id):
    try:
        user_id = int(current_user.UserID)
    except AttributeError:
        flash("You must log in first", "error")
        return redirect(url_for('sign_in'))
    try:
        messaging_oneself = True if user_id == other_user_id else False
        existing_other_user = session.query(User).filter_by(UserID=other_user_id).first()
        if not existing_other_user:
            flash("no such user", 'error')
            return redirect(url_for('chat_list'))
        name_of_other_user = existing_other_user.Username

        chat_ids = f"{other_user_id}_{user_id}" if user_id > int(other_user_id) else f"{user_id}_{other_user_id}"

        file_name = f"private_chats/private_chat_{chat_ids}"

        print(file_name)

        return chat(file_name=file_name, chat_name=name_of_other_user, sender_id=user_id, kind="private",
                    id_for_chat=other_user_id, messaging_oneself=messaging_oneself)
    except SQLAlchemyError as e:
        flash("Database error with my activities page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))


def chat(file_name, chat_name, sender_id, kind, id_for_chat, messaging_oneself=False):
    message_to_send = None
    message_to_resend = None

    try:
        if request.method == 'POST':
            message_to_send = request.form['message_to_send'].strip()
            if len(message_to_send) > 999:
                flash("message too long", 'error')
                message_to_resend = message_to_send
            elif len(message_to_send) == 0:
                pass
            else:
                add_message_to_chat(file_name, message_to_send, sender_id)

        messages, chatters = get_messages_and_chatters_from_chat(file_name, 50)
        chatters_names = {}
        for chatter_id in chatters:
            chatters_names[chatter_id] = session.query(User).filter_by(UserID=chatter_id).first().Username

        return render_template('chat.html', kind=kind, chat_name=chat_name, id_for_chat=id_for_chat,
                               messages=messages, message_to_send=message_to_send, message_to_resend=message_to_resend,
                               chatters_names=chatters_names, messaging_oneself=messaging_oneself)
    except SQLAlchemyError as e:
        flash("Database error with my activities page", 'error')
        print(f"Database error: {str(e)}")
        return redirect(url_for('sign_in'))


if __name__ == "__main__":
    app.run(host='192.168.1.147', port=5000, debug=True, threaded=True)
