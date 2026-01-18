from flask import Blueprint, request, jsonify, current_app, abort
from models import db, Employee, Delegation, Expense
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from utils import require_role, get_current_employee
from decimal import Decimal

bp = Blueprint('admin', __name__)

def normalize_status(status):
    """Normalizuje status do uppercase EN: PENDING | APPROVED | REJECTED"""
    if not status:
        return 'PENDING'
    s = str(status).upper().strip()
    if s in ['PENDING', 'APPROVED', 'REJECTED']:
        return s
    # Fallback dla starych wartości
    if s in ['ACCEPTED', 'ZAAKCEPTOWANY']:
        return 'APPROVED'
    if s in ['ODRZUCONY', 'DENIED']:
        return 'REJECTED'
    return 'PENDING'

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
        
        username_raw = (data.get('username') or '').strip()
        email_raw = (data.get('email') or '').strip().lower()
        password = data.get('password')
        
        # Walidacja danych
        if not username_raw or not email_raw or not password:
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
        
        # Sprawdzenie duplikatów
        existing_username = Employee.query.filter(func.lower(func.trim(Employee.username)) == func.lower(username_raw)).first()
        if existing_username:
            return jsonify({
                "error": "DUPLICATE",
                "field": "username",
                "message": "Username already exists"
            }), 409
        
        existing_email = Employee.query.filter(func.lower(func.trim(Employee.email)) == func.lower(email_raw)).first()
        if existing_email:
            return jsonify({
                "error": "DUPLICATE",
                "field": "email",
                "message": "Email already exists"
            }), 409
        
        # Hashowanie hasła
        bcrypt = get_bcrypt()
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Tworzenie nowego pracownika
        # FIX: first_name i last_name są wymagane w modelu, więc ustawiamy defaults
        new_employee = Employee(
            username=username_raw,
            email=email_raw,
            password=hashed_password,
            first_name=data.get('first_name', username_raw),
            last_name=data.get('last_name', 'User'),
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
        
    except IntegrityError as e:
        db.session.rollback()
        err_text = str(e.orig).lower() if hasattr(e, 'orig') else ''
        if 'username' in err_text:
            return jsonify({
                "error": "DUPLICATE",
                "field": "username",
                "message": "Username already exists"
            }), 409
        if 'email' in err_text:
            return jsonify({
                "error": "DUPLICATE",
                "field": "email",
                "message": "Email already exists"
            }), 409
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
def compute_delegation_status(expenses):
    """
    Oblicza status delegacji na podstawie statusów wydatków.
    Jedno źródło prawdy - używa normalize_status.
    - PENDING: jeśli istnieje przynajmniej jeden wydatek pending
    - REJECTED: tylko jeśli wszystkie wydatki są rejected (i jest ich > 0)
    - APPROVED: jeśli pending = 0 i przynajmniej jeden wydatek jest approved
    - Jeśli brak wydatków: zwraca 'PENDING'
    """
    if not expenses:
        return 'PENDING'
    
    statuses = [normalize_status(e.status) for e in expenses]
    pending_count = statuses.count('PENDING')
    approved_count = statuses.count('APPROVED')
    rejected_count = statuses.count('REJECTED')
    total_count = len(statuses)
    
    if pending_count > 0:
        return 'PENDING'
    if rejected_count == total_count:
        return 'REJECTED'
    if approved_count > 0:
        return 'APPROVED'
    return 'PENDING'
@bp.route('/managers', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_all_managers():
    '''Pobranie listy wszystkich managerów (tylko admin)'''
    try:
        managers = Employee.query.filter_by(role='manager').all()
        managers_data = [{
            "id": mgr.id,
            "username": mgr.username,
            "first_name": mgr.first_name,
            "last_name": mgr.last_name,
            "email": mgr.email,
            "is_active": mgr.is_active,
            "created_at": mgr.created_at.isoformat() if mgr.created_at else None
        } for mgr in managers]
        return jsonify({
            "status": "success",
            "managers": managers_data
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@bp.route('/managers/<int:manager_id>', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_manager_details(manager_id):
    '''Pobranie szczegółów managera wraz z listą jego pracowników (tylko admin)'''
    try:
        manager = Employee.query.get(manager_id)
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Manager not found"
            }), 404
        if manager.role != 'manager':
            return jsonify({
                "status": "error",
                "message": "User is not a manager"
            }), 400
        # Pobierz pracowników przypisanych do managera
        employees = Employee.query.filter_by(manager_id=manager_id).all()
        manager_data = {
            "id": manager.id,
            "username": manager.username,
            "first_name": manager.first_name,
            "last_name": manager.last_name,
            "email": manager.email,
            "role": manager.role,
            "is_active": manager.is_active
        }
        employees_data = [{
            "id": emp.id,
            "username": emp.username,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "role": emp.role,
            "is_active": emp.is_active
        } for emp in employees]
        return jsonify({
            "status": "success",
            "manager": manager_data,
            "employees": employees_data
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@bp.route('/employees/<int:employee_id>', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_admin_employee_details(employee_id):
    '''Pobranie szczegółów pracownika wraz z jego delegacjami (tylko admin)'''
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        # Pobierz delegacje pracownika
        delegations = Delegation.query.filter_by(employee_id=employee_id).all()
        employee_data = {
            "id": employee.id,
            "username": employee.username,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "role": employee.role,
            "is_active": employee.is_active,
            "manager_id": employee.manager_id
        }
        delegations_data = []
        for d in delegations:
            # WALIDACJA: delegacja musi należeć do tego pracownika
            if d.employee_id != employee_id:
                return jsonify({
                    "status": "error",
                    "message": f"Inconsistent delegation.employee_id: delegation {d.id} has employee_id={d.employee_id}, expected {employee_id}"
                }), 500
            
            # Pobierz wydatki delegacji i oblicz status
            expenses = Expense.query.filter_by(delegation_id=d.id).all()
            derived_status = compute_delegation_status(expenses)
            
            delegations_data.append({
                "id": d.id,
                "name": d.name,
                "city": d.city,
                "country": d.country,
                "start_date": d.start_date.isoformat() if d.start_date else None,
                "end_date": d.end_date.isoformat() if d.end_date else None,
                "status": derived_status,
                "employee_id": d.employee_id,
                "purpose": d.purpose,
                "created_at": d.created_at.isoformat() if d.created_at else None
            })
        return jsonify({
            "status": "success",
            "employee": employee_data,
            "delegations": delegations_data
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@bp.route('/delegations/<int:delegation_id>', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_admin_delegation_details(delegation_id):
    '''Pobranie szczegółów delegacji wraz z wydatkami (tylko admin)'''
    try:
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Pobierz pracownika i waliduj spójność
        employee = Employee.query.get(delegation.employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        if delegation.employee_id != employee.id:
            abort(500, description=f"Inconsistent delegation employee: delegation.employee_id={delegation.employee_id}, employee.id={employee.id}")
        
        # Pobierz wydatki delegacji
        expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        # Oblicz status delegacji na podstawie wydatków (jedno źródło prawdy)
        derived_status = compute_delegation_status(expenses)
        
        delegation_data = {
            "id": delegation.id,
            "name": delegation.name,
            "country": delegation.country,
            "city": delegation.city,
            "purpose": delegation.purpose,
            "start_date": delegation.start_date.isoformat() if delegation.start_date else None,
            "end_date": delegation.end_date.isoformat() if delegation.end_date else None,
            "status": derived_status,
            "employee_id": delegation.employee_id
        }
        employee_data = {
            "id": employee.id,
            "username": employee.username,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email
        }
        # Przygotuj dane wydatków z obliczonymi sumami
        expenses_data = []
        total_amount = Decimal('0')
        pending_amount = Decimal('0')
        approved_amount = Decimal('0')
        rejected_amount = Decimal('0')
        for exp in expenses:
            # WALIDACJA: expense musi należeć do tej delegacji
            if exp.delegation_id != delegation_id:
                abort(500, description=f"Inconsistent expense delegation_id: expense {exp.id} has delegation_id={exp.delegation_id}, expected {delegation_id}")
            
            amount = exp.pln_amount or exp.amount or Decimal('0')
            status = normalize_status(exp.status)
            
            expenses_data.append({
                "id": exp.id,
                "delegation_id": exp.delegation_id,
                "name": exp.explanation or "No description",
                "amount": float(amount),
                "status": status,
                "category_id": exp.category_id,
                "created_at": exp.created_at.isoformat() if exp.created_at else None
            })
            
            total_amount += amount
            if status == 'PENDING':
                pending_amount += amount
            elif status == 'APPROVED':
                approved_amount += amount
            elif status == 'REJECTED':
                rejected_amount += amount
        
        return jsonify({
            "status": "success",
            "delegation": delegation_data,
            "employee": employee_data,
            "items": expenses_data,
            "summary": {
                "total": float(total_amount),
                "pending": float(pending_amount),
                "approved": float(approved_amount),
                "rejected": float(rejected_amount)
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
