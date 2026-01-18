from flask import Blueprint, request, jsonify, current_app
from models import db, Delegation, Employee, Expense, Currency, ExpenseCategory
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils import require_role, get_current_employee
from datetime import date, timedelta
from decimal import Decimal

bp = Blueprint('manager', __name__)

VALID_STATUSES = {'PENDING', 'APPROVED', 'REJECTED'}


def normalize_status(value):
    """Ensure status is one of the allowed uppercase values, defaulting to PENDING."""
    if not value:
        return 'PENDING'
    status = str(value).upper()
    return status if status in VALID_STATUSES else 'PENDING'


def compute_delegation_status(expenses):
    """
    Oblicza status delegacji na podstawie statusów wydatków.
    - PENDING: jeśli istnieje przynajmniej jeden wydatek pending
    - REJECTED: tylko jeśli wszystkie wydatki są rejected (i jest ich > 0)
    - APPROVED: jeśli pending = 0 i przynajmniej jeden wydatek jest approved
    - Jeśli brak wydatków: zwraca 'PENDING' (fallback)
    """
    if not expenses:
        return 'PENDING'
    
    normalized_statuses = [normalize_status(e.status) for e in expenses]
    pending_count = sum(1 for s in normalized_statuses if s == 'PENDING')
    approved_count = sum(1 for s in normalized_statuses if s == 'APPROVED')
    rejected_count = sum(1 for s in normalized_statuses if s == 'REJECTED')
    total_count = len(expenses)
    
    # Jeśli jest przynajmniej jeden pending -> PENDING
    if pending_count > 0:
        return 'PENDING'
    
    # Jeśli wszystkie są rejected -> REJECTED
    if rejected_count == total_count:
        return 'REJECTED'
    
    # Jeśli pending = 0 i przynajmniej jeden approved -> APPROVED
    if approved_count > 0:
        return 'APPROVED'
    
    # Fallback
    return 'PENDING'


@bp.route('/employees', methods=['GET'])
@jwt_required()
@require_role('manager')
def get_my_employees():
    """Pobranie listy pracowników przypisanych do menedżera"""
    try:
        manager_id = get_jwt_identity()
        manager = Employee.query.get(manager_id)
        
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Manager not found"
            }), 404
        
        # Pobierz pracowników przypisanych do menedżera
        employees = Employee.query.filter_by(manager_id=manager_id).all()
        
        # Jeśli brak pracowników i DEV_SEED jest włączony, utwórz testowych
        if not employees and current_app.config.get('DEV_SEED', 'false').lower() == 'true':
            employees = _create_test_employees_for_manager(manager_id)
        
        employees_data = [
            {
                'id': emp.id,
                'username': emp.username,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'email': emp.email,
                'role': emp.role,
                'is_active': emp.is_active
            }
            for emp in employees
        ]
        
        return jsonify({
            "status": "success",
            "employees": employees_data
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def _create_test_employees_for_manager(manager_id):
    """
    Helper: tworzy testowych pracowników dla menedżera (tylko w DEV)
    Idempotentny - sprawdza czy użytkownicy już istnieją
    """
    bcrypt = current_app.extensions.get('bcrypt')
    if not bcrypt:
        return []
    
    test_employees_data = [
        {
            'username': f'pracownik_test1',
            'first_name': 'Tomasz',
            'last_name': 'Lewandowski',
            'email': f'tomasz.lewandowski@manager{manager_id}.local',
            'password': '12345678'
        },
        {
            'username': f'pracownik_test2',
            'first_name': 'Katarzyna',
            'last_name': 'Wójcik',
            'email': f'katarzyna.wojcik@manager{manager_id}.local',
            'password': '12345678'
        },
        {
            'username': f'pracownik_test3',
            'first_name': 'Michał',
            'last_name': 'Kamiński',
            'email': f'michal.kaminski@manager{manager_id}.local',
            'password': '12345678'
        }
    ]
    
    created_employees = []
    
    for emp_data in test_employees_data:
        # Sprawdź czy użytkownik już istnieje
        existing = Employee.query.filter_by(email=emp_data['email']).first()
        
        if existing:
            created_employees.append(existing)
            continue
        
        # Hashuj hasło
        hashed_password = bcrypt.generate_password_hash(emp_data['password']).decode('utf-8')
        
        # Utwórz nowego pracownika
        new_employee = Employee(
            username=emp_data['username'],
            email=emp_data['email'],
            password=hashed_password,
            first_name=emp_data['first_name'],
            last_name=emp_data['last_name'],
            role='employee',
            is_active=True,
            manager_id=manager_id
        )
        
        try:
            db.session.add(new_employee)
            db.session.commit()
            created_employees.append(new_employee)
        except Exception as e:
            db.session.rollback()
    
    return created_employees


@bp.route('/employees/<int:employee_id>', methods=['GET'])
@jwt_required()
@require_role('manager')
def get_employee_details(employee_id):
    """Pobranie szczegółów pracownika wraz z jego delegacjami"""
    try:
        manager_id = int(get_jwt_identity())
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        # Sprawdź czy pracownik jest przypisany do tego menedżera
        if employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only view employees assigned to you"
            }), 403
        
        # Pobierz delegacje pracownika
        delegations = Delegation.query.filter_by(employee_id=employee_id).all()
        
        # Jeśli brak delegacji i DEV_SEED jest włączony, utwórz testowe
        if not delegations and current_app.config.get('DEV_SEED', 'false').lower() == 'true':
            delegations = _create_test_delegations_for_employee(employee_id)
        
        employee_data = {
            'id': employee.id,
            'username': employee.username,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': employee.email,
            'role': employee.role,
            'is_active': employee.is_active
        }
        
        delegations_data = []
        for d in delegations:
            # Pobierz wydatki delegacji i oblicz status (jedno źródło prawdy)
            expenses = Expense.query.filter_by(delegation_id=d.id).all()
            derived_status = compute_delegation_status(expenses)
            
            delegations_data.append({
                'id': d.id,
                'employee_id': d.employee_id,
                'start_date': d.start_date.isoformat() if d.start_date else None,
                'end_date': d.end_date.isoformat() if d.end_date else None,
                'status': derived_status,
                'country': d.country,
                'city': d.city,
                'name': d.name,
                'purpose': d.purpose,
                'created_at': d.created_at.isoformat() if d.created_at else None
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


def _create_test_delegations_for_employee(employee_id):
    """
    Helper: tworzy testowe delegacje dla pracownika (tylko w DEV)
    Idempotentny - sprawdza czy delegacje już istnieją
    """
    from datetime import date, timedelta
    
    test_delegations_data = [
        {
            'name': 'Wyjazd służbowy do Warszawy',
            'country': 'Polska',
            'city': 'Warszawa',
            'purpose': 'Spotkanie z klientem - prezentacja produktu',
            'start_date': date.today() + timedelta(days=7),
            'end_date': date.today() + timedelta(days=9),
            'status': 'pending'
        },
        {
            'name': 'Konferencja branżowa w Krakowie',
            'country': 'Polska',
            'city': 'Kraków',
            'purpose': 'Udział w konferencji IT Summit 2026',
            'start_date': date.today() + timedelta(days=14),
            'end_date': date.today() + timedelta(days=16),
            'status': 'pending'
        },
        {
            'name': 'Szkolenie w Gdańsku',
            'country': 'Polska',
            'city': 'Gdańsk',
            'purpose': 'Szkolenie z zarządzania projektami',
            'start_date': date.today() + timedelta(days=21),
            'end_date': date.today() + timedelta(days=23),
            'status': 'pending'
        }
    ]
    
    created_delegations = []
    
    for deleg_data in test_delegations_data:
        # Sprawdź czy delegacja o podobnych parametrach już istnieje
        existing = Delegation.query.filter_by(
            employee_id=employee_id,
            city=deleg_data['city'],
            start_date=deleg_data['start_date']
        ).first()
        
        if existing:
            created_delegations.append(existing)
            continue
        
        # Utwórz nową delegację
        new_delegation = Delegation(
            employee_id=employee_id,
            name=deleg_data['name'],
            country=deleg_data['country'],
            city=deleg_data['city'],
            purpose=deleg_data['purpose'],
            start_date=deleg_data['start_date'],
            end_date=deleg_data['end_date'],
            status=deleg_data['status']
        )
        
        try:
            db.session.add(new_delegation)
            db.session.commit()
            created_delegations.append(new_delegation)
        except Exception as e:
            db.session.rollback()
    
    return created_delegations


@bp.route('/delegations/<int:delegation_id>', methods=['GET'])
@jwt_required()
@require_role('manager')
def get_delegation_details(delegation_id):
    """Pobranie szczegółów delegacji wraz z wydatkami"""
    try:
        manager_id = int(get_jwt_identity())
        delegation = Delegation.query.get(delegation_id)
        
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy delegacja należy do pracownika tego menedżera
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only view delegations of your subordinates"
            }), 403
        
        # Pobierz wydatki delegacji
        expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        
        # Jeśli brak wydatków i DEV_SEED jest włączony, utwórz testowe
        if not expenses and current_app.config.get('DEV_SEED', 'false').lower() == 'true':
            expenses = _create_test_expenses_for_delegation(delegation_id)
        
        # Oblicz status delegacji na podstawie wydatków (jedno źródło prawdy)
        derived_status = compute_delegation_status(expenses)
        
        delegation_data = {
            'id': delegation.id,
            'name': delegation.name,
            'country': delegation.country,
            'city': delegation.city,
            'purpose': delegation.purpose,
            'start_date': delegation.start_date.isoformat() if delegation.start_date else None,
            'end_date': delegation.end_date.isoformat() if delegation.end_date else None,
            'status': derived_status,
            'employee_id': delegation.employee_id
        }
        
        # Dane pracownika
        employee_data = {
            'id': employee.id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': employee.email
        }
        
        # Przygotuj dane wydatków z obliczonymi sumami
        expenses_data = []
        total_amount = Decimal('0')
        pending_amount = Decimal('0')
        approved_amount = Decimal('0')
        rejected_amount = Decimal('0')
        
        for exp in expenses:
            amount = exp.pln_amount or exp.amount or Decimal('0')
            status = normalize_status(exp.status)
            
            expenses_data.append({
                'id': exp.id,
                'delegation_id': exp.delegation_id,
                'name': exp.explanation or 'No description',
                'amount': float(amount),
                'status': status,
                'category_id': exp.category_id,
                'created_at': exp.created_at.isoformat() if exp.created_at else None
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


def _create_test_expenses_for_delegation(delegation_id):
    """
    Helper: tworzy testowe wydatki dla delegacji (tylko w DEV)
    Idempotentny - sprawdza czy wydatki już istnieją
    """
    # Pobierz domyślną kategorię i walutę
    default_category = ExpenseCategory.query.first()
    default_currency = Currency.query.filter_by(name='PLN').first()
    
    if not default_category or not default_currency:
        return []
    
    test_expenses_data = [
        {
            'explanation': 'Hotel - nocleg (2 noce)',
            'amount': Decimal('450.00'),
            'status': 'PENDING'
        },
        {
            'explanation': 'Bilet kolejowy (powrót)',
            'amount': Decimal('120.00'),
            'status': 'PENDING'
        },
        {
            'explanation': 'Obiad służbowy z klientem',
            'amount': Decimal('180.00'),
            'status': 'PENDING'
        },
        {
            'explanation': 'Taxi z lotniska',
            'amount': Decimal('65.00'),
            'status': 'PENDING'
        },
        {
            'explanation': 'Materiały konferencyjne',
            'amount': Decimal('85.00'),
            'status': 'PENDING'
        }
    ]
    
    created_expenses = []
    
    for exp_data in test_expenses_data:
        # Sprawdź czy wydatek już istnieje
        existing = Expense.query.filter_by(
            delegation_id=delegation_id,
            explanation=exp_data['explanation']
        ).first()
        
        if existing:
            created_expenses.append(existing)
            continue
        
        # Utwórz nowy wydatek
        new_expense = Expense(
            delegation_id=delegation_id,
            explanation=exp_data['explanation'],
            amount=exp_data['amount'],
            pln_amount=exp_data['amount'],
            exchange_rate=Decimal('1.0'),
            currency_id=default_currency.id,
            category_id=default_category.id,
            status=exp_data['status']
        )
        
        try:
            db.session.add(new_expense)
            db.session.commit()
            created_expenses.append(new_expense)
        except Exception as e:
            db.session.rollback()
    
    return created_expenses


@bp.route('/delegations', methods=['GET'])
@jwt_required()
@require_role('manager')
def get_subordinates_delegations():
    """Pobranie delegacji podwładnych pracowników (tylko menedżer)"""
    try:
        manager_id = get_jwt_identity()
        manager = Employee.query.get(manager_id)
        
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Manager not found"
            }), 404
        
        # Pobierz wszystkich podwładnych
        subordinates = Employee.query.filter_by(manager_id=manager_id).all()
        subordinate_ids = [sub.id for sub in subordinates]
        
        # Pobierz delegacje podwładnych
        delegations = Delegation.query.filter(
            Delegation.employee_id.in_(subordinate_ids)
        ).all()
        
        delegations_data = []
        for d in delegations:
            employee = Employee.query.get(d.employee_id)
            expenses = Expense.query.filter_by(delegation_id=d.id).all()
            derived_status = compute_delegation_status(expenses)

            delegations_data.append({
                'id': d.id,
                'employee_id': d.employee_id,
                'employee_name': employee.username if employee else None,
                'employee_email': employee.email if employee else None,
                'start_date': d.start_date.isoformat() if d.start_date else None,
                'end_date': d.end_date.isoformat() if d.end_date else None,
                'status': derived_status,
                'country': d.country,
                'city': d.city,
                'name': d.name,
                'purpose': d.purpose,
                'created_at': d.created_at.isoformat() if d.created_at else None
            })
        
        return jsonify({
            "status": "success",
            "delegations": delegations_data
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@bp.route('/delegations/<int:delegation_id>/items/<int:item_id>/approve', methods=['POST'])
@jwt_required()
@require_role('manager')
def approve_expense_item(delegation_id, item_id):
    """Zatwierdzenie pojedynczego wydatku"""
    try:
        manager_id = int(get_jwt_identity())
        
        # Sprawdź delegację i uprawnienia
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only approve items of your subordinates' delegations"
            }), 403
        
        # Sprawdź wydatek
        expense = Expense.query.get(item_id)
        if not expense or expense.delegation_id != delegation_id:
            return jsonify({
                "status": "error",
                "message": "Item not found in this delegation"
            }), 404
        
        expense.status = 'APPROVED'
        
        # Przelicz status delegacji na podstawie wszystkich wydatków
        all_expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        delegation.status = compute_delegation_status(all_expenses)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Item approved successfully",
            "item": {
                "id": expense.id,
                "status": expense.status
            },
            "delegation_status": delegation.status
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@bp.route('/delegations/<int:delegation_id>/items/<int:item_id>/reject', methods=['POST'])
@jwt_required()
@require_role('manager')
def reject_expense_item(delegation_id, item_id):
    """Odrzucenie pojedynczego wydatku"""
    try:
        manager_id = int(get_jwt_identity())
        
        # Sprawdź delegację i uprawnienia
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only reject items of your subordinates' delegations"
            }), 403
        
        # Sprawdź wydatek
        expense = Expense.query.get(item_id)
        if not expense or expense.delegation_id != delegation_id:
            return jsonify({
                "status": "error",
                "message": "Item not found in this delegation"
            }), 404
        
        expense.status = 'REJECTED'
        
        # Przelicz status delegacji na podstawie wszystkich wydatków
        all_expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        delegation.status = compute_delegation_status(all_expenses)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Item rejected successfully",
            "item": {
                "id": expense.id,
                "status": expense.status
            },
            "delegation_status": delegation.status
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@bp.route('/delegations/<int:delegation_id>/items/approve_all', methods=['POST'])
@jwt_required()
@require_role('manager')
def approve_all_pending_items(delegation_id):
    """Zatwierdzenie wszystkich wydatków w statusie PENDING"""
    try:
        manager_id = int(get_jwt_identity())
        
        # Sprawdź delegację i uprawnienia
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only approve items of your subordinates' delegations"
            }), 403
        
        # Znajdź wszystkie wydatki PENDING
        pending_expenses = Expense.query.filter_by(
            delegation_id=delegation_id
        ).filter(db.func.upper(Expense.status) == 'PENDING').all()
        
        count = 0
        for expense in pending_expenses:
            expense.status = 'APPROVED'
            count += 1
        
        # Przelicz status delegacji na podstawie wszystkich wydatków
        all_expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        delegation.status = compute_delegation_status(all_expenses)
        
        # Oblicz summary
        total_amount = Decimal('0')
        pending_amount = Decimal('0')
        approved_amount = Decimal('0')
        rejected_amount = Decimal('0')
        
        for exp in all_expenses:
            amount = exp.pln_amount or exp.amount or Decimal('0')
            status = normalize_status(exp.status)
            total_amount += amount
            if status == 'PENDING':
                pending_amount += amount
            elif status == 'APPROVED':
                approved_amount += amount
            elif status == 'REJECTED':
                rejected_amount += amount
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Approved {count} pending items",
            "count": count,
            "delegation_status": delegation.status,
            "summary": {
                "total": float(total_amount),
                "pending": float(pending_amount),
                "approved": float(approved_amount),
                "rejected": float(rejected_amount)
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@bp.route('/delegations/<int:delegation_id>/items/reject_all', methods=['POST'])
@jwt_required()
@require_role('manager')
def reject_all_pending_items(delegation_id):
    """Odrzucenie wszystkich wydatków w statusie PENDING"""
    try:
        manager_id = int(get_jwt_identity())
        
        # Sprawdź delegację i uprawnienia
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only reject items of your subordinates' delegations"
            }), 403
        
        # Znajdź wszystkie wydatki PENDING
        pending_expenses = Expense.query.filter_by(
            delegation_id=delegation_id
        ).filter(db.func.upper(Expense.status) == 'PENDING').all()
        
        count = 0
        for expense in pending_expenses:
            expense.status = 'REJECTED'
            count += 1
        
        # Przelicz status delegacji na podstawie wszystkich wydatków
        all_expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        delegation.status = compute_delegation_status(all_expenses)
        
        # Oblicz summary
        total_amount = Decimal('0')
        pending_amount = Decimal('0')
        approved_amount = Decimal('0')
        rejected_amount = Decimal('0')
        
        for exp in all_expenses:
            amount = exp.pln_amount or exp.amount or Decimal('0')
            status = normalize_status(exp.status)
            total_amount += amount
            if status == 'PENDING':
                pending_amount += amount
            elif status == 'APPROVED':
                approved_amount += amount
            elif status == 'REJECTED':
                rejected_amount += amount
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Rejected {count} pending items",
            "count": count,
            "delegation_status": delegation.status,
            "summary": {
                "total": float(total_amount),
                "pending": float(pending_amount),
                "approved": float(approved_amount),
                "rejected": float(rejected_amount)
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@bp.route('/delegations/<int:delegation_id>/approve', methods=['POST'])
@jwt_required()
@require_role('manager')
def approve_delegation(delegation_id):
    """Zatwierdzenie delegacji (tylko menedżer)"""
    try:
        manager_id = int(get_jwt_identity())
        delegation = Delegation.query.get(delegation_id)
        
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy delegacja należy do podwładnego
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only approve delegations of your subordinates"
            }), 403
        
        current_status = normalize_status(delegation.status)
        if current_status != 'PENDING':
            return jsonify({
                "status": "error",
                "message": f"Cannot approve delegation with status: {delegation.status}"
            }), 400
        
        delegation.status = 'APPROVED'
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Delegation approved successfully",
            "delegation": {
                'id': delegation.id,
                'status': delegation.status
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/delegations/<int:delegation_id>/reject', methods=['POST'])
@jwt_required()
@require_role('manager')
def reject_delegation(delegation_id):
    """Odrzucenie delegacji (tylko menedżer)"""
    try:
        manager_id = int(get_jwt_identity())
        delegation = Delegation.query.get(delegation_id)
        
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy delegacja należy do podwładnego
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only reject delegations of your subordinates"
            }), 403
        
        current_status = normalize_status(delegation.status)
        if current_status != 'PENDING':
            return jsonify({
                "status": "error",
                "message": f"Cannot reject delegation with status: {delegation.status}"
            }), 400
        
        data = request.get_json() or {}
        rejection_reason = data.get('reason', '')
        
        delegation.status = 'REJECTED'
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Delegation rejected successfully",
            "delegation": {
                'id': delegation.id,
                'status': delegation.status,
                'rejection_reason': rejection_reason
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/delegations/<int:delegation_id>/cancel', methods=['POST'])
@jwt_required()
@require_role('manager')
def cancel_delegation(delegation_id):
    """Anulowanie delegacji (tylko menedżer)"""
    try:
        manager_id = get_jwt_identity()
        delegation = Delegation.query.get(delegation_id)
        
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy delegacja należy do podwładnego
        employee = Employee.query.get(delegation.employee_id)
        if not employee or employee.manager_id != manager_id:
            return jsonify({
                "status": "error",
                "message": "You can only cancel delegations of your subordinates"
            }), 403
        
        delegation.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Delegation cancelled successfully",
            "delegation": {
                'id': delegation.id,
                'status': delegation.status
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
