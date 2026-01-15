from flask import Blueprint, request, jsonify, current_app
from models import db, Employee
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError

bp = Blueprint('auth', __name__)

def get_bcrypt():
    """Pobiera instancję bcrypt z current_app"""
    return current_app.extensions.get('bcrypt')

@bp.route('/register', methods=['POST'])
def register():
    """Rejestracja nowego pracownika"""
    try:
        data = request.get_json() or {}
        
        # Walidacja danych
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({
                "status": "error",
                "message": "Username, email and password are required"
            }), 400
        
        # Sprawdzenie czy pracownik już istnieje
        existing_employee = Employee.query.filter(
            (Employee.username == data['username']) | (Employee.email == data['email'])
        ).first()
        
        if existing_employee:
            return jsonify({
                "status": "error",
                "message": "Employee with this username or email already exists"
            }), 409
        
        # Hashowanie hasła
        bcrypt = get_bcrypt()
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        # Tworzenie nowego pracownika
        new_employee = Employee(
            username=data['username'],
            email=data['email'],
            password=hashed_password,
            is_active=True
        )
        
        db.session.add(new_employee)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "employee_id": new_employee.id,
            "message": "Employee created successfully"
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Employee with this username or email already exists"
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/login', methods=['POST'])
def login():
    """Logowanie pracownika - zwraca JWT token"""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "status": "error",
                "message": "Email and password are required"
            }), 400
        
        # Znajdź pracownika po emailu
        employee = Employee.query.filter_by(email=email).first()
        
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Sprawdź czy konto jest aktywne
        if not employee.is_active:
            return jsonify({
                "status": "error",
                "message": "Employee account is inactive"
            }), 403
        
        # Weryfikacja hasła
        bcrypt = get_bcrypt()
        if not bcrypt.check_password_hash(employee.password, password):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Generowanie JWT tokena
        access_token = create_access_token(identity=employee.id)
        
        # Przygotowanie odpowiedzi
        response_data = {
            "status": "success",
            "token": access_token,
            "employee_id": employee.id,
            "employee": {
                "id": employee.id,
                "username": employee.username,
                "email": employee.email
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_employee():
    """Pobranie danych aktualnego zalogowanego pracownika"""
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        employee_data = {
            "id": employee.id,
            "username": employee.username,
            "email": employee.email,
            "is_active": employee.is_active,
            "created_at": employee.created_at.isoformat() if employee.created_at else None
        }
        
        return jsonify({
            "status": "success",
            "employee": employee_data
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
        employee_id = get_jwt_identity()
        claims = get_jwt()
        
        return jsonify({
            "status": "success",
            "employee_id": employee_id,
            "valid": True,
            "claims": claims
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 401
