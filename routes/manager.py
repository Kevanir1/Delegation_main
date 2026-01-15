from flask import Blueprint, request, jsonify
from models import db, Delegation, Employee
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils import require_role, get_current_employee

bp = Blueprint('manager', __name__)

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
            delegations_data.append({
                'id': d.id,
                'employee_id': d.employee_id,
                'employee_name': employee.username if employee else None,
                'employee_email': employee.email if employee else None,
                'start_date': d.start_date.isoformat() if d.start_date else None,
                'end_date': d.end_date.isoformat() if d.end_date else None,
                'status': d.status,
                'destination': d.destination,
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

@bp.route('/delegations/<int:delegation_id>/approve', methods=['POST'])
@jwt_required()
@require_role('manager')
def approve_delegation(delegation_id):
    """Zatwierdzenie delegacji (tylko menedżer)"""
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
                "message": "You can only approve delegations of your subordinates"
            }), 403
        
        if delegation.status not in ['pending', 'draft']:
            return jsonify({
                "status": "error",
                "message": f"Cannot approve delegation with status: {delegation.status}"
            }), 400
        
        delegation.status = 'approved'
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
                "message": "You can only reject delegations of your subordinates"
            }), 403
        
        if delegation.status not in ['pending', 'draft']:
            return jsonify({
                "status": "error",
                "message": f"Cannot reject delegation with status: {delegation.status}"
            }), 400
        
        data = request.get_json() or {}
        rejection_reason = data.get('reason', '')
        
        delegation.status = 'rejected'
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
