from flask import Blueprint, request, jsonify, current_app
from models import db, Employee
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from utils import require_role, get_current_employee

bp = Blueprint('admin', __name__)

def get_bcrypt():
    """Pobiera instancję bcrypt z current_app"""
    return current_app.extensions.get('bcrypt')

@bp.route('/employees', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_all_employees():
    """Pobranie listy wszystkich pracowników (tylko admin)"""
    try:
        employees = Employee.query.all()
        employees_data = [{
            "id": emp.id,
            "username": emp.username,
            "email": emp.email,
            "role": emp.role,
            "is_active": emp.is_active,
            "manager_id": emp.manager_id,
            "created_at": emp.created_at.isoformat() if emp.created_at else None
        } for emp in employees]
        
        return jsonify({
            "status": "success",
            "employees": employees_data
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/employees', methods=['POST'])
@jwt_required()
@require_role('admin')
def create_employee():
    """Tworzenie nowego profilu pracownika (tylko admin)"""
    try:
        data = request.get_json() or {}
        
        # Walidacja danych
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({
                "status": "error",
                "message": "Username, email and password are required"
            }), 400
        
        role = data.get('role', 'employee')
        if role not in ['employee', 'manager', 'accountant', 'admin']:
            return jsonify({
                "status": "error",
                "message": "Invalid role. Allowed roles: employee, manager, accountant, admin"
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
            role=role,
            is_active=data.get('is_active', True),
            manager_id=data.get('manager_id')
        )
        
        db.session.add(new_employee)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "employee_id": new_employee.id,
            "message": "Employee created successfully",
            "employee": {
                "id": new_employee.id,
                "username": new_employee.username,
                "email": new_employee.email,
                "role": new_employee.role,
                "is_active": new_employee.is_active,
                "manager_id": new_employee.manager_id
            }
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

@bp.route('/employees/<int:employee_id>', methods=['PUT'])
@jwt_required()
@require_role('admin')
def update_employee(employee_id):
    """Aktualizacja profilu pracownika (tylko admin)"""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        data = request.get_json() or {}
        
        # Aktualizacja roli
        if 'role' in data:
            if data['role'] not in ['employee', 'manager', 'accountant', 'admin']:
                return jsonify({
                    "status": "error",
                    "message": "Invalid role. Allowed roles: employee, manager, accountant, admin"
                }), 400
            employee.role = data['role']
        
        # Aktualizacja statusu aktywnego
        if 'is_active' in data:
            employee.is_active = data['is_active']
        
        # Aktualizacja menedżera
        if 'manager_id' in data:
            manager_id = data['manager_id']
            if manager_id:
                manager = Employee.query.get(manager_id)
                if not manager:
                    return jsonify({
                        "status": "error",
                        "message": "Manager not found"
                    }), 404
                if manager.role != 'manager':
                    return jsonify({
                        "status": "error",
                        "message": "Assigned manager must have 'manager' role"
                    }), 400
            employee.manager_id = manager_id
        
        # Aktualizacja username i email (jeśli podane)
        if 'username' in data:
            # Sprawdź czy username nie jest zajęty przez innego użytkownika
            existing = Employee.query.filter(
                Employee.username == data['username'],
                Employee.id != employee_id
            ).first()
            if existing:
                return jsonify({
                    "status": "error",
                    "message": "Username already taken"
                }), 409
            employee.username = data['username']
        
        if 'email' in data:
            # Sprawdź czy email nie jest zajęty przez innego użytkownika
            existing = Employee.query.filter(
                Employee.email == data['email'],
                Employee.id != employee_id
            ).first()
            if existing:
                return jsonify({
                    "status": "error",
                    "message": "Email already taken"
                }), 409
            employee.email = data['email']
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Employee updated successfully",
            "employee": {
                "id": employee.id,
                "username": employee.username,
                "email": employee.email,
                "role": employee.role,
                "is_active": employee.is_active,
                "manager_id": employee.manager_id
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/employees/<int:employee_id>/activate', methods=['POST'])
@jwt_required()
@require_role('admin')
def activate_employee(employee_id):
    """Aktywacja profilu pracownika (tylko admin)"""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        employee.is_active = True
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Employee activated successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/employees/<int:employee_id>/block', methods=['POST'])
@jwt_required()
@require_role('admin')
def block_employee(employee_id):
    """Blokowanie profilu pracownika (tylko admin)"""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        employee.is_active = False
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Employee blocked successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/employees/<int:employee_id>/assign-manager', methods=['POST'])
@jwt_required()
@require_role('admin')
def assign_manager(employee_id):
    """Przypisanie pracownika do menedżera (tylko admin)"""
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        data = request.get_json() or {}
        manager_id = data.get('manager_id')
        
        if manager_id:
            manager = Employee.query.get(manager_id)
            if not manager:
                return jsonify({
                    "status": "error",
                    "message": "Manager not found"
                }), 404
            if manager.role != 'manager':
                return jsonify({
                    "status": "error",
                    "message": "Assigned user must have 'manager' role"
                }), 400
            employee.manager_id = manager_id
        else:
            employee.manager_id = None
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Manager assigned successfully",
            "employee": {
                "id": employee.id,
                "username": employee.username,
                "manager_id": employee.manager_id
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
