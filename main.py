from flask import Flask, render_template, request, redirect, url_for
from flask import flash, jsonify, send_from_directory
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
import re
import datetime
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('/var/www/client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Udacity Catalog"

engine = create_engine('postgresql+psycopg2://postgres:waitrose702@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app.secret_key = "CLhf04GmiNpkugVLox4Di1qwq"

@app.route('/var/www/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/var/www/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)

# Helpers

def getUserById(uid):  # Fetches the user with the given ID
    try:
        user = session.query(User).filter_by(id=uid).one()
        return user
    except:
        return None


def getUserByEmail(email):  # Fetches the user with the given email.
    try:
        user = session.query(User).filter_by(email=email).one()
        return user
    except:
        return None

# Slight misnomer. Creates a user entry if one by that email doesn't
# already exist, otherwise updates their picture and nickname to match
# their third party one.
def createUser(login_session):
    user = getUserByEmail(login_session['email'])
    if user is not None:
        user.name = login_session['username']
        user.picture = login_session['picture']
        session.commit()
        return user
    else:
        newUser = User(name=login_session['username'], email=login_session['email'], picture=login_session['picture'])
        session.add(newUser)
        session.commit()
        return newUser

# Checks the login session is the owner of the item.
def checkAuth(login_session, item):
    if 'user_id' in login_session:
        if login_session['user_id'] == item.owner_id:
            return True
    return False

def checkLoggedIn(login_session):  # Checks that the user is logged in.
    if 'user_id' in login_session:
        return True
    else:
        return False

def isItems(query):  # Verifies if a query returned any results.
    if query.first() is not None:
        return query
    else:
        return False

@app.route('/')
@app.route('/home/')
@app.route('/index/')
def homePage():  # Routing function for the homepage
    categories = session.query(Category).filter_by(hidden=False)
    latest_items = session.query(Item).order_by(desc('added')).limit(15)
    params = {}
    params['categories'] = isItems(categories)
    params['latest_items'] = isItems(latest_items)
    params['login_session'] = login_session
    return render_template('index.html', **params)


@app.route('/add/category/', methods=['GET', 'POST'])
def addCategory():  # Routing function for the add category page.
    params = {}
    if not checkLoggedIn(login_session):
        return redirect(url_for('showLogin'))
    if request.method == 'POST':
        name = request.form['categoryName']
        if name:
            category = Category(name=name, owner_id=login_session['user_id'])
            session.add(category)
            session.commit()
            message = "Category '%s' was successfully added!" % (name,)
            referrer = "addCategory"
            return redirect(url_for('addSuccess',
                                    message=message,
                                    referrer=referrer))
        else:
            params['login_session'] = login_session
            params['name_error'] = "You must include a category name!"
            params['name_error_class'] = "has-error"
            return render_template('add_category.html', **params)
    else:
        params['login_session'] = login_session
        return render_template('add_category.html', **params)


@app.route('/add/item/', methods=['GET', 'POST'])
def addItem():
    if not checkLoggedIn(login_session):
        return redirect(url_for('showLogin'))
    params = {}
    hasErrors = False
    classError = "has-error"
    if request.method == 'POST':
        name = request.form['itemName']
        category = request.form['itemCategory']
        price = request.form['itemPrice']
        desc = request.form['itemDesc']
        if not name:  # Runs through possible errors and outputs to the
            # appropriate error param where necessary.
            hasErrors = True
            params['name_error'] = "You must give an item name!"
            params['name_error_class'] = classError
        if not category:
            hasErrors = True
            params['category_error'] = "You must choose an item category!"
            params['category_error_class'] = classError
        else:
            category = session.query(Category).filter_by(name=category).one()
            if category:
                category_id = category.id
            else:
                hasErrors = True
                params['category_error'] = "That category does not exist!"
                params['category_error_class'] = classError
        if not desc:
            hasErrors = True
            params['desc_error'] = "You must give an item description!"
            params['desc_error_class'] = classError
        if not price:
            hasErrors = True
            params['price_error'] = "You must given an item price!"
            params['price_error_class'] = classError
        else:
            pattern = '^\d+\.\d\d$'
            if not re.match(pattern, price):
                hasErrors = True
                params['price_error'] = "That is not a valid price!"
                params['price_error_class'] = classError
        if not hasErrors:
            item = Item(name=name, category_id=category_id, description=desc,
                        price=float(price),
                        owner_id=login_session['user_id'])
            session.add(item)
            session.commit()
            message = "Item '%s' was successfully added!" % (name,)
            referrer = "addItem"
            return redirect(
                url_for('addSuccess', message=message, referrer=referrer))
        else:
            params['login_session'] = login_session
            params['name'] = name
            params['chosenCategory'] = category.name
            params['price'] = price
            params['desc'] = desc
            categories = session.query(Category).filter_by(hidden=False)
            params['categories'] = categories
            return render_template('add_item.html', **params)
    else:
        params['login_session'] = login_session
        params['chosenCategory'] = ""
        params['price'] = "0.00"
        categories = session.query(Category).filter_by(hidden=False)
        params['categories'] = categories
        return render_template('add_item.html', **params)


@app.route('/add/success/', defaults={'message': "", 'referrer': ""})
@app.route('/add/success/<message>/<referrer>')
def addSuccess(message, referrer):  # Displays an appropriate success page
    # on successful item/category INSERT to database. Also has a
    # referrer term so the user can click a link and be redirected to
    # the page where they originated.
    if not checkLoggedIn(login_session):
        return redirect(url_for('showLogin'))
    if message != "" and referrer != "":
        params = {'message': message}
        params['referrer'] = url_for(referrer)
        params['login_session'] = login_session
        return render_template('add_success.html', **params)
    else:
        return redirect(url_for('homePage'))


@app.route('/category/<int:category_id>/item/all/', methods=['GET', 'POST'])
# Displays items belonging to the category corresponding to the category ID.
def itemsByCategory(category_id):
    params = {}
    if request.method == 'POST':
        pass
    else:
        try:
            category = session.query(Category).filter_by(id=category_id).one()
        except:
            category = False
            error = {'title': "Category Does Not Exist",
                     'body': "That category does not exist yet!",
                     'head': "Whoops!"}
            params['error'] = error
            return render_template('gen_error.html', **params)
        items = session.query(Item).filter_by(category_id=category_id)
        params['items'] = isItems(items)
        params['category'] = category
        params['login_session'] = login_session
        return render_template('items_by_category.html', **params)


@app.route('/category/<int:category_id>/item/<int:item_id>/',
           methods=['GET', 'POST'])
def itemByItem(category_id, item_id):  # Displays an individual item.
    params = {}
    error = False
    if request.method == 'POST':
        pass
    else:
        try:
            item = session.query(Item).filter_by(
                id=item_id, category_id=category_id).one()
        except:
            error = {'title': "Item Not Found", 'head': "Aw snap!",
                     "body": "It looks like that item doesn't exist yet!"}
        try:
            category = session.query(Category).filter_by(id=category_id).one()
        except:
            error = {'title': "Category Not Found", 'head': "Aw snap!",
                     'body': 'It looks like that category doesn\'t exist yet!'}
        if error:
            params['error'] = error
            params['login_session'] = login_session
            return render_template('gen_error.html', **params)
        else:
            params['category'] = category
            params['item'] = item
            params['login_session'] = login_session
            return render_template('item_page.html', **params)


@app.route('/delete/item/<int:item_id>/', methods=['GET', 'POST'])
def deleteItem(item_id):  # Responsible for deleting items.
    params = {}
    try:  # Checks if item exists and catches the exception if not.
        item = session.query(Item).filter_by(id=item_id).one()
    except:
        error = {'title': "Item Not Found", 'head': "Aw snap!",
                 "body":
                 "We couldn't delete that item for you as it doesn't exist!"}
        params['error'] = error
        params['login_session'] = login_session
        return render_template('gen_error.html', **params)
    # Checks the user is authorised to delete that item.
    if checkAuth(login_session, item) is not True:
        error = {'title': "Nope!", 'head': "Not so fast...",
                 "body":
                 """Slow it down Sneaky Pete...
                 No deleting what you didn't bring into this world!"""}
        params['error'] = error
        return render_template('gen_error.html', **params)
    category = session.query(Category).filter_by(id=item.category_id).one()
    if request.method == 'POST':
        params['message'] = "Item %s deleted successfully!" % (item.name,)
        params['referrer'] = url_for(
            'itemsByCategory', category_id=category.id)
        session.delete(item)
        session.commit()
        params['login_session'] = login_session
        return render_template('delete_success.html', **params)
    else:
        params['category'] = category
        params['item'] = item
        params['login_session'] = login_session
        return render_template('delete_item.html', **params)


@app.route('/edit/item/<int:item_id>/', methods=['GET', 'POST'])
def editItem(item_id):  # Facilitates the editing of items.
    params = {}
    hasErrors = False
    classError = "has-error"
    try:  # Checks if item exists.
        item = session.query(Item).filter_by(id=item_id).one()
    except:
        error = {'title': "Item doesn't exist!", 'head': "Whoops!",
                 'body':
                 """We were unable to find the item you wished to edit.
                 Sorry about that!"""}
        params['error'] = error
        return render_template('gen_error.html', **params)
    # Checks if user is authorised to edit the item,
    if checkAuth(login_session, item) is not True:
        error = {'title': "Not So Fast!", 'head': "Nope!",
                 'body':
                 """Sorry friend... Can't edit what's not yours I'm afraid.
                 So sorry."""}
        params['error'] = error
        return render_template('gen_error.html', **params)
    if request.method == 'POST':
        name = request.form['itemName']
        category = request.form['itemCategory']
        price = request.form['itemPrice']
        desc = request.form['itemDesc']
        if not name:  # Error checks in the same way as add item,.
            hasErrors = True
            params['name_error'] = "You must give an item name!"
            params['name_error_class'] = classError
        if not category:
            hasErrors = True
            params['category_error'] = "You must choose an item category!"
            params['category_error_class'] = classError
        else:
            category = session.query(Category).filter_by(name=category).one()
            if category:
                category_id = category.id
            else:
                hasErrors = True
                params['category_error'] = "That category does not exist!"
                params['category_error_class'] = classError
        if not desc:
            hasErrors = True
            params['desc_error'] = "You must give an item description!"
            params['desc_error_class'] = classError
        if not price:
            hasErrors = True
            params['price_error'] = "You must given an item price!"
            params['price_error_class'] = classError
        else:
            pattern = '^\d+\.\d\d$'
            if not re.match(pattern, price):
                hasErrors = True
                params['price_error'] = "That is not a valid price!"
                params['price_error_class'] = classError
        if not hasErrors:
            item.name = name
            item.category_id = category_id
            item.description = desc
            item.price = price
            session.commit()
            message = "Item '%s' was successfully edited!" % (name,)
            return redirect(url_for('editSuccess', message=message,
                                    item_id=item.id, category_id=category_id))
        else:
            params['name'] = name
            params['chosenCategory'] = category.name
            params['price'] = price
            params['desc'] = desc
            categories = session.query(Category).filter_by(hidden=False)
            params['categories'] = categories
            params['login_session'] = login_session
            params['item'] = item
            return render_template('edit_item.html', **params)
    else:
        params['chosenCategory'] = session.query(
            Category).filter_by(id=item.category_id).one().name
        params['name'] = item.name
        params['price'] = item.price
        params['desc'] = item.description
        categories = session.query(Category).filter_by(hidden=False)
        params['categories'] = categories
        params['login_session'] = login_session
        params['item'] = item
        return render_template('edit_item.html', **params)


@app.route('/edit/success/', defaults={'message': "", 'item_id': ""})
@app.route('/edit/success/<message>/<int:category_id>/<int:item_id>/')
# Displays an edit success page with referrer destined for the page for
# which the edit was actioned upon.
def editSuccess(message, item_id, category_id):
    if not checkLoggedIn(login_session):
        return redirect(url_for('showLogin'))
    if message != "" and item_id != "":
        params = {'message': message}
        params['referrer'] = url_for(
            'itemByItem', item_id=item_id, category_id=category_id)
        params['login_session'] = login_session
        return render_template('edit_success.html', **params)
    else:
        return redirect(url_for('homePage'))

# Start of JSON Endpoints


@app.route('/category/JSON/')
def allCategoriesJSON():  # Lists all categories in serialized JSON
    categories = session.query(Category).filter_by(hidden=False).all()
    return jsonify(Category=[i.serialize for i in categories])


@app.route('/category/<int:category_id>/item/all/JSON/')
# Lists all items in a given category in serialized JSON
def allItemInCategoryJSON(category_id):
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(Item=[i.serialize for i in items])


@app.route('/category/<int:category_id>/item/<int:item_id>/JSON/')
def itemByIdJSON(category_id, item_id):
    # Lists a specific item in serialized JSON
    items = session.query(Item).filter_by(
        category_id=category_id, id=item_id).all()
    return jsonify(Item=[i.serialize for i in items])

# End of JSON Endpoints


@app.route('/login')
# Displays the log in page and generates the anti-forgery state token.
def showLogin():
   if 'username' in login_session:
   	return redirect(url_for('homePage'))
   state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
   login_session['state'] = state
   params = {}
   params['login_session'] = login_session
   params['STATE'] = state
   return render_template('login.html', **params)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Runs the authorisation process with the third party authenticator.
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('/var/www/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('Access Token Error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    user = createUser(login_session)
    login_session['user_id'] = user.id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    # Responsible for revoking user's auth access token and deleting their
    # session when they choose to log out.
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = """https://accounts.google.com/o/
    oauth2/revoke?token=%s""" % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':  # Login session deletion.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


