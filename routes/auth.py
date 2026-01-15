from flask import Blueprint, request, jsonify, current_app
from models import db, User, Employee
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError

bp = Blueprint('auth', __name__)

def get_bcrypt():
    """Pobiera instancję bcrypt z current_app"""
    return current_app.extensions.get('bcrypt')

@bp.route('/register', methods=['POST'])
def register():
    """Rejestracja nowego użytkownika"""
    try:
        data = request.get_json() or {}
        
        # Walidacja danych
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({
                "status": "error",
                "message": "Username, email and password are required"
            }), 400
        
        # Sprawdzenie czy użytkownik już istnieje
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({
                "status": "error",
                "message": "User with this username or email already exists"
            }), 409
        
        # Hashowanie hasła
        bcrypt = get_bcrypt()
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        # Tworzenie nowego użytkownika
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=hashed_password,
            is_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "user_id": new_user.id,
            "message": "User created successfully"
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "User with this username or email already exists"
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/login', methods=['POST'])
def login():
    """Logowanie użytkownika - zwraca JWT token"""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "status": "error",
                "message": "Email and password are required"
            }), 400
        
        # Znajdź użytkownika po emailu
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Sprawdź czy konto jest aktywne
        if not user.is_active:
            return jsonify({
                "status": "error",
                "message": "User account is inactive"
            }), 403
        
        # Weryfikacja hasła
        bcrypt = get_bcrypt()
        if not bcrypt.check_password_hash(user.password, password):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Generowanie JWT tokena
        access_token = create_access_token(identity=user.id)
        
        # Przygotowanie odpowiedzi
        response_data = {
            "status": "success",
            "token": access_token,
            "user_id": user.id,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
        
        # Jeśli użytkownik ma powiązany profil Employee, dodaj informacje
        if user.employee_id:
            employee = Employee.query.get(user.employee_id)
            if employee:
                response_data["employee_id"] = employee.id
                response_data["user"]["employee"] = {
                    "id": employee.id,
                    "name": employee.name,
                    "surname": employee.surname,
                    "role": employee.role
                }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Pobranie danych aktualnego zalogowanego użytkownika"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        
        # Jeśli użytkownik ma powiązany profil Employee
        if user.employee_id:
            employee = Employee.query.get(user.employee_id)
            if employee:
                user_data["employee"] = {
                    "id": employee.id,
                    "name": employee.name,
                    "surname": employee.surname,
                    "role": employee.role
                }
        
        return jsonify({
            "status": "success",
            "user": user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Weryfikacja JWT tokena"""
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "valid": True,
            "claims": claims
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 401
