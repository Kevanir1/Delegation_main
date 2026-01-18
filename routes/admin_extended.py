# Extended admin endpoints for manager and delegation management
# Append these to admin.py

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
    
    pending_count = sum(1 for e in expenses if (e.status or 'PENDING').upper() == 'PENDING')
    approved_count = sum(1 for e in expenses if (e.status or '').upper() == 'APPROVED')
    rejected_count = sum(1 for e in expenses if (e.status or '').upper() == 'REJECTED')
    total_count = len(expenses)
    
    if pending_count > 0:
        return 'PENDING'
    
    if rejected_count == total_count:
        return 'REJECTED'
    
    if approved_count > 0:
        return 'APPROVED'
    
    return 'PENDING'


# Add these routes to admin.py Blueprint

"""
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
        
        # Pobierz pracownika
        employee = Employee.query.get(delegation.employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        # Pobierz wydatki delegacji
        expenses = Expense.query.filter_by(delegation_id=delegation_id).all()
        
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
            amount = exp.pln_amount or exp.amount or Decimal('0')
            status = (exp.status or 'PENDING').upper()
            
            expenses_data.append({
                "id": exp.id,
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
"""
