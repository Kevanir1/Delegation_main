from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Delegation, Employee

bp = Blueprint('delegations', __name__)

@bp.route('', methods=['GET'])
@jwt_required()
def get_delegations():
    """Pobranie listy delegacji zalogowanego pracownika"""
    employee_id = get_jwt_identity()
    
    try:
        # Sprawdź czy pracownik istnieje
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        delegations = Delegation.query.filter_by(employee_id=employee_id).all()
        return jsonify({
            "status": "success",
            "delegations": [{
                'id': d.id,
                'start_date': d.start_date.isoformat(),
                'end_date': d.end_date.isoformat(),
                'status': d.status
            } for d in delegations]
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('', methods=['POST'])
@jwt_required()
def create_delegation():
    """Utworzenie nowej delegacji"""
    employee_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        # Sprawdź czy pracownik istnieje
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        new_delegation = Delegation(
            employee_id=employee_id,
            start_date=data['start_date'],
            end_date=data['end_date'],
            status=data.get('status', 'draft')
        )
        
        db.session.add(new_delegation)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "delegation": {
                'id': new_delegation.id,
                'start_date': new_delegation.start_date.isoformat(),
                'end_date': new_delegation.end_date.isoformat(),
                'status': new_delegation.status
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
