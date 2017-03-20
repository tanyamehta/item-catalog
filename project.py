from flask import Flask, request, redirect, url_for, flash, jsonify
from flask import render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
    	print request.args.get('state') , "q ",login_session['state']
    	response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
    	print 2
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
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
    	print 3
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
    	print 4
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
    	user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
       # Only disconnect a connected user.

    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

        # Execute HTTP GET request to revoke current token

    access_token = credentials
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':

        # Reset the user's session

        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['picture']
        del login_session['username']
        del login_session['email']
		


        response = make_response(json.dumps('User disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = \
            make_response(json.dumps('''Failed to revoke token for \
                                     given user! \
									 result = %s \
 								     credentials = %s'''
                          % (result, credentials)), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase+string.digits)for x in range(32))
	login_session['state'] = state;
	return render_template('login.html' , STATE = state)


@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

@app.route('/restaurant/JSON')
def restaurantJSON():
    Item = session.query(Restaurant).all()
    return jsonify(MenuItem=[i.serialize for i in Item])


# ADD JSON ENDPOINT HERE
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=menuItem.serialize)
    

@app.route('/')
@app.route('/restaurant')
def restaurantAll():
	res = session.query(Restaurant).all()
	if 'username' not in login_session:
		return render_template('publicrestaurantall.html', res=res)
	else:
		return render_template('restaurantall.html', res=res)

@app.route('/restaurant/new', methods=['GET','POST'])
def newRestaurant():
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':	
		if request.form['name']:
			newres = Restaurant(name = request.form['name'], user_id = login_session['user_id'])
			session.add(newres)
			session.commit()
		return redirect(url_for('restaurantAll' ))
	else:
		return render_template('newrestaurant.html')

@app.route('/restaurant/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
    	return render_template("publicmenu.html", restaurant = restaurant, items = items)
    else:
    	return render_template("menu.html", restaurant = restaurant, items = items)

   
# Task 1: Create route for newMenuItem function here

@app.route('/restaurant/<int:restaurant_id>/new', methods =['GET', 'POST'])
def newMenuItem(restaurant_id):
	if 'username' not in login_session:
		return redirect('/login')

	restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
	if restaurant.user_id != login_session['user_id']:
		return "<script>function myFunction(){alert('Not authorised to\
		 add items to this restaurant');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		new = MenuItem(name = request.form['name'],restaurant_id=restaurant_id, user_id = restaurant.user_id)
		session.add(new)
		session.commit()
		flash("New item created!")
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	else:
		return render_template('newmenuitem.html', restaurant_id=restaurant_id)

# Task 2: Create route for editMenuItem function here

@app.route('/restaurant/<int:id>/edit', methods = ['GET', 'POST'])
def editRestaurant(id):
	if 'username' not in login_session:
		return redirect('/login')
	editItem = session.query(Restaurant).filter_by(id=id).one()
	if editItem.user_id != login_session['user_id']:
		return "<script>function myFunction(){alert('Not authorised to\
		 edit this restaurant');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		if request.form['name']:
			editItem.name = request.form['name']
		session.add(editItem)
		session.commit()
		return redirect(url_for('restaurantAll'))
	else:
		return render_template('editrestaurant.html',id=id, item=editItem)


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit', methods = ['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
	if 'username' not in login_session:
		return redirect('/login')
	editItem = session.query(MenuItem).filter_by(id=menu_id).one()
	if request.method == 'POST':
		if request.form['name']:
			editItem.name = request.form['name']
		if request.form['description']:
			editItem.description = request.form['description']
		if request.form['price']:
			editItem.price = request.form['price']
		if request.form['course']:
			editItem.course = request.form['course']
				
		session.add(editItem)
		session.commit()
		flash("Item editing successful!")
		return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
	else:
		return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editItem)
# Task 3: Create a route for deleteMenuItem function here

@app.route('/restaurant/<int:id>/delete', methods = ['GET', 'POST'])
def deleteRestaurant(id):
	if 'username' not in login_session:
		return redirect('/login')
	delItem = session.query(Restaurant).filter_by(id=id).one()
	if delItem.user_id != login_session['user_id']:
		return "<script>function myFunction(){alert('Not authorised to\
		 delete this restaurant');}</script><body onload='myFunction()''>"
	if request.method == 'POST':
		session.delete(delItem)
		session.commit()
		return redirect(url_for('restaurantAll'))
	else:
		return render_template('deleterestaurant.html',id=id)


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete', methods = ['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
	if 'username' not in login_session:
		return redirect('/login')
	delItem = session.query(MenuItem).filter_by(id=menu_id).one()
	if request.method == 'POST':
		session.delete(delItem)
		session.commit()
		flash("Item deleted successfully!")
		return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
	else:
		return render_template('deleteitem.html',restaurant_id=restaurant_id, menu_id=menu_id, item=delItem)



if __name__ == '__main__':
    app.secret_key = 'super_secret_key'	
    app.debug = True
    app.run(host='0.0.0.0', port=5000)