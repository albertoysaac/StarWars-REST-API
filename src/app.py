"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from datetime import timedelta
from flask import Flask, request, jsonify, url_for
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Planet, People, Favoritos
#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

app.config['JWT_SECRET_KEY'] = 'tu_secreto_aqui'  
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)  # Configura la duración del token a 24 horas
jwt = JWTManager(app)

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email, password=password).first()
    if user is not None:
        return jsonify({"message": "Email already in use"}), 409
    new_user = User(names=data.get('names'),last_name=data.get('last_name'), age=data.get('age') ,email=data.get('email'), password=data.get('password'))
    db.session.add(new_user)
    db.session.commit()
    access_token = create_access_token(identity=new_user.id)
    return jsonify(access_token=access_token), 200

@app.route('/login', methods=['POST'])
def login():
    request_body = request.get_json()
    email = request_body.get('email')
    password = request_body.get('password')
    user = User.query.filter_by(email=email, password=password).first()
    if user is None:
        return jsonify({"message": "Invalid email or password"}), 401
    else:
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200

@app.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200

@app.route('/users/favorites', methods=['GET'])
@jwt_required()
def list_user_favorites():
    current_user_id = get_jwt_identity()
    print(current_user_id)
    user_favorites = Favoritos.query.filter_by(user_id=current_user_id).all()
    favorites = {
        "planets": [favorite.planet.serialize() for favorite in user_favorites if favorite.planet],
        "people": [favorite.people.serialize() for favorite in user_favorites if favorite.people]
    }
    return jsonify(favorites), 200

@app.route('/favorite/planet/<int:planet_id>', methods=['POST'])
@jwt_required()
def add_favorite_planet(planet_id):
    current_user_id = get_jwt_identity()
    new_favorite = Favoritos(user_id=current_user_id, planet_id=planet_id)
    db.session.add(new_favorite)
    db.session.commit()
    return jsonify({"message": "Planet added to favorites"}), 201

@app.route('/favorite/people/<int:people_id>', methods=['POST'])
@jwt_required()
def add_favorite_people(people_id):
    current_user_id = get_jwt_identity()
    new_favorite = Favoritos(user_id=current_user_id, people_id=people_id)
    db.session.add(new_favorite)
    db.session.commit()
    return jsonify({"message": "People added to favorites"}), 201

@app.route('/favorite/planet/<int:planet_id>', methods=['DELETE'])
@jwt_required()
def delete_favorite_planet(planet_id):
    current_user_id = get_jwt_identity()
    favorite = Favoritos.query.filter_by(user_id=current_user_id, planet_id=planet_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({"message": "Planet removed from favorites"}), 200
    else:
        return jsonify({"message": "Favorite planet not found"}), 404

@app.route('/favorite/people/<int:people_id>', methods=['DELETE'])
@jwt_required()
def delete_favorite_people(people_id):
    current_user_id = get_jwt_identity()
    favorite = Favoritos.query.filter_by(user_id=current_user_id, people_id=people_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({"message": "People removed from favorites"}), 200
    else:
        return jsonify({"message": "Favorite people not found"}), 404



@app.route('/people', methods=['GET'])
def get_people():
    people_list = People.query.all()
    return jsonify([person.serialize() for person in people_list]), 200

@app.route('/people/<int:people_id>', methods=['GET'])
def get_person(people_id):
    person = People.query.get(people_id)
    if person:
        return jsonify(person.serialize()), 200
    else:
        return jsonify({"message": "Person not found"}), 404
    
@app.route('/people/<int:people_id>', methods=['DELETE'])
def delete_person(people_id):
    person = People.query.get(people_id)
    if person:
        db.session.delete(person)
        db.session.commit()
        return jsonify({"message": "Person deleted"}), 200
    else:
        return jsonify({"message": "Person not found"}), 404

@app.route('/people', methods=['POST'])
def new_person():
    data = request.get_json()
    new_person = People(name=data.get('name'), height=data.get('height'), mass=data.get('mass'),
                        hair_color=data.get('hair_color'), skin_color=data.get('skin_color'),
                        eye_color=data.get('eye_color'), birth_year=data.get('birth_year'),
                        gender=data.get('gender'), homeworld_id=data.get('homeworld_id'))
    db.session.add(new_person)
    db.session.commit()
    return jsonify({"message": "Person created"}), 201

@app.route('/planets', methods=['GET'])
def get_planets():
    planet_list = Planet.query.all()
    return jsonify([planet.serialize() for planet in planet_list]), 200

@app.route('/planets/<int:planet_id>', methods=['GET'])
def get_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if planet:
        return jsonify(planet.serialize()), 200
    else:
        return jsonify({"message": "Planet not found"}), 404

@app.route('/planets/<int:planet_id>', methods=['DELETE'])
def delete_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if planet:
        db.session.delete(planet)
        db.session.commit()
        return jsonify({"message": "Planet deleted"}), 200
    else:
        return jsonify({"message": "Planet not found"}), 404
    
@app.route('/planets', methods=['POST'])
def new_planet():
    data = request.get_json()
    new_planet = Planet(name=data.get('name'), rotation_period=data.get('rotation_period'), orbital_period=data.get('orbital_period'),
                        diameter=data.get('diameter'), climate=data.get('climate'), gravity=data.get('gravity'),
                        terrain=data.get('terrain'), surface_water=data.get('surface_water'), population=data.get('population'))
    db.session.add(new_planet)
    db.session.commit()
    return jsonify({"message": "Planet created"}), 201



# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
