from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, URL
from flask_bootstrap import Bootstrap

app = Flask(__name__)

bootstrap = Bootstrap(app)
CAFE_API_URL = 'http://127.0.0.1:5000'
TOP_SECRET_API_KEY = "password123"

# Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret'
db = SQLAlchemy(app)


# Cafe TABLE Configuration
class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)

    def to_dict(self):
        # Use Dictionary Comprehension to do the same thing.
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


# Cafe Add form with API validation
class AddCafeForm(FlaskForm):
    name = StringField('Cafe Name', validators=[DataRequired()])
    location = StringField('Cafe Location', validators=[DataRequired()])
    location_url = StringField('Cafe Location on Google Maps (URL)', validators=[DataRequired(), URL()])
    image = StringField('Cafe Image URL', validators=[DataRequired(), URL()])
    wifi = BooleanField('Wifi Available')
    socket = BooleanField('Power Socket Available')
    seats = StringField('Number of Seats', validators=[DataRequired()])
    toilet = BooleanField('Has Toilet')
    call = BooleanField('Can Take Calls')
    coffee_price = StringField('Price of Black Coffee', validators=[DataRequired()])
    api_key = StringField('API Key', validators=[DataRequired()])
    submit = SubmitField('Submit')


# Cafe delete form with API validation
class DeleteForm(FlaskForm):
    api_key = StringField("API Key")
    confirm = SubmitField("Confirm")
    cancel = SubmitField("Cancel")


@app.route("/")
def home():
    return render_template("index.html")


## API ##

# Pull random cafe from database
@app.route("/random")
def random_cafe():
    cafe = random.choice(db.session.query(Cafe).all())
    return jsonify(cafe=cafe.to_dict())


# Pull all cafes from db
@app.route("/all")
def load_all():
    all_cafes = db.session.query(Cafe).all()
    cafe_dict = jsonify(cafes=[cafe.to_dict() for cafe in all_cafes]).get_data()
    return cafe_dict

# Search cafe based on location
@app.route("/search", methods=["GET", "POST"])
def search_cafe():
    location = request.args.get("loc")
    cafes = db.session.query(Cafe).filter_by(location=location).all()
    cafe_dict = jsonify(cafes=[cafe.to_dict() for cafe in cafes]).get_data()
    if cafe_dict:
        return cafe_dict
    else:
        return jsonify(error={"Not Found": "Sorry we don't have a cafe at that location"})


# Add new cafe using form
@app.route("/add", methods=["GET", "POST"])
def add():
    api_key = request.form.get("api_key")
    if api_key == TOP_SECRET_API_KEY:
        new_cafe = Cafe(
            name=request.form.get("name"),
            map_url=request.form.get("map_url"),
            img_url=request.form.get("img_url"),
            location=request.form.get("loc"),
            has_sockets=bool(request.form.get("sockets")),
            has_toilet=bool(request.form.get("toilet")),
            has_wifi=bool(request.form.get("wifi")),
            can_take_calls=bool(request.form.get("calls")),
            seats=request.form.get("seats"),
            coffee_price=request.form.get("coffee_price"),
        )
        db.session.add(new_cafe)
        db.session.commit()
        print("Successfully added new cafe")
        return jsonify(response={"success": "Successfully added new cafe"})
    else:
        return jsonify(response={"failed": "API key incorrect"})


# Update the price of a coffee in a cafe using its ID
@app.route('/update-price/<cafe_id>', methods=["PATCH"])
def edit_price(cafe_id):
    new_price = request.args.get("new_price")
    cafe_to_update = Cafe.query.get(cafe_id)
    cafe_to_update.coffee_price = new_price
    db.session.commit()
    return jsonify(response={"success": "Successfully updated the price"})


# Delete cafe record from db
@app.route('/report-closed/<cafe_id>', methods=["DELETE", "GET"])
def delete_cafe(cafe_id):
    api_key = request.args.get("api-key")
    if api_key == TOP_SECRET_API_KEY:
        cafe_to_delete = Cafe.query.get(cafe_id)
        if cafe_to_delete:
            db.session.delete(cafe_to_delete)
            db.session.commit()
            return jsonify(response={"success": "Successfully deleted cafe"})
        else:
            return jsonify(error={"Not Found": "Sorry a cafe with that id was not found in the database"})
    else:
        return jsonify(error={"Error": "Sorry that's not allowed"})

## Web routes ##

# Call API and display all cafes in db
@app.route("/cafes")
def all_cafes():
    response = requests.get(url=f'{CAFE_API_URL}/all')
    cafes_response = response.json()['cafes']
    return render_template("cafes.html", cafes=cafes_response)


# Call API to pull cafe with matching name from the db
@app.route("/<name>")
def cafe_page(name):
    response = requests.get(url=f'{CAFE_API_URL}/all')
    cafes_response = response.json()['cafes']
    clicked_cafe = [cafe for cafe in cafes_response if cafe["name"] == name]
    print(f"Clicked cafe: {clicked_cafe}")
    return render_template("cafe_page.html", cafe=clicked_cafe)


# Call API to search db for location from search bar
@app.route("/search-location", methods=["GET", "POST"])
def show_search():
    location = request.form.get('search')
    response = requests.get(url=f"{CAFE_API_URL}/search?loc={location}")
    # cafes_response = response.json()
    cafes_response = response.json()['cafes']
    print(response)
    return render_template("cafes.html", cafes=cafes_response, location=location)


# Page with WTForms to add cafe, passing params into add API request.
@app.route("/add-cafe", methods=["GET", "POST"])
def add_cafe():
    form = AddCafeForm()
    params = {'name': form.name.data,
              'map_url': form.location_url.data,
              'img_url': form.image.data,
              'loc': form.location.data,
              'sockets': form.socket.data,
              'toilet': form.toilet.data,
              'wifi': form.wifi.data,
              'calls': form.call.data,
              'seats': form.seats.data,
              'coffee_price': form.coffee_price.data,
              'api_key': form.api_key.data
              }
    requests.post(f"{CAFE_API_URL}/add", data=params)
    if form.validate_on_submit():
        return redirect(url_for('add_cafe'))
    return render_template('add-cafe.html', form=form)


# Pull random cafe using API
@app.route("/random-cafe", methods=["GET", "POST"])
def display_random():
    response = requests.get(url=f'{CAFE_API_URL}/random')
    random_cafe = response.json()
    random_cafe = [random_cafe['cafe']]
    print(random_cafe)
    return render_template("cafe_page.html", cafe=random_cafe)


# Report a cafe as closed using API key validation and API delete request.
@app.route("/delete/<name>/<id>", methods=["GET", "POST", "DELETE"])
def delete(id, name):
    form = DeleteForm()
    if form.validate_on_submit():
        if form.cancel.data:
            return redirect(url_for('cafe_page', name=name))
        if form.api_key.data == TOP_SECRET_API_KEY and form.confirm.data:
            response = requests.get(url=f'{CAFE_API_URL}/report-closed/{id}?api-key={form.api_key.data}')
            print(response.json())
            return redirect(url_for('all_cafes'))
    return render_template('delete.html', form=form, name=name)


if __name__ == '__main__':
    app.run(debug=True)
