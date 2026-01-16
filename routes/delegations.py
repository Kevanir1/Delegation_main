from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Delegation, Employee, Document, Expense
from datetime import datetime
from utils import get_current_employee

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
        return jsonify([{
                'id': d.id,
                'start_date': d.start_date.isoformat() if d.start_date else None,
                'end_date': d.end_date.isoformat() if d.end_date else None,
                'status': d.status,
                'destination': d.destination,
                'purpose': d.purpose,
                'created_at': d.created_at.isoformat() if d.created_at else None
            } for d in delegations]
        ), 200
    
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
    data = request.get_json() or {}
    
    try:
        # Sprawdź czy pracownik istnieje
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        # Walidacja wymaganych pól
        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({
                "status": "error",
                "message": "start_date and end_date are required"
            }), 400
        
        # Parsowanie dat
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        if start_date > end_date:
            return jsonify({
                "status": "error",
                "message": "start_date must be before or equal to end_date"
            }), 400
        
        new_delegation = Delegation(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            status=data.get('status', 'draft'),
            destination=data.get('destination'),
            purpose=data.get('purpose')
        )
        
        db.session.add(new_delegation)
        db.session.flush()  # Flush to get the delegation ID
        
        # Handle expenses if provided
        created_expenses = []
        expenses_data = data.get('expenses', [])
        
        if expenses_data:
            for expense_data in expenses_data:
                # Validate required fields for expense
                if not expense_data.get('amount'):
                    db.session.rollback()
                    return jsonify({
                        "status": "error",
                        "message": "Each expense must have an amount"
                    }), 400
                
                if not expense_data.get('currency_id'):
                    db.session.rollback()
                    return jsonify({
                        "status": "error",
                        "message": "Each expense must have a currency_id"
                    }), 400
                
                if not expense_data.get('category_id'):
                    db.session.rollback()
                    return jsonify({
                        "status": "error",
                        "message": "Each expense must have a category_id"
                    }), 400
                
                # Parse payed_at if provided
                payed_at = None
                if expense_data.get('payed_at'):
                    try:
                        payed_at = datetime.strptime(expense_data['payed_at'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            payed_at = datetime.strptime(expense_data['payed_at'], '%Y-%m-%d')
                        except ValueError:
                            db.session.rollback()
                            return jsonify({
                                "status": "error",
                                "message": "Invalid payed_at format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
                            }), 400
                
                new_expense = Expense(
                    delegation_id=new_delegation.id,
                    explanation=expense_data.get('explanation'),
                    payed_at=payed_at,
                    amount=expense_data['amount'],
                    pln_amount=expense_data.get('pln_amount', expense_data['amount']),
                    exchange_rate=expense_data.get('exchange_rate', 1.0),
                    currency_id=expense_data['currency_id'],
                    category_id=expense_data['category_id'],
                    status=expense_data.get('status', 'draft')
                )
                
                db.session.add(new_expense)
                created_expenses.append(new_expense)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Delegation created successfully",
            "delegation": {
                'id': new_delegation.id,
                'start_date': new_delegation.start_date.isoformat(),
                'end_date': new_delegation.end_date.isoformat(),
                'status': new_delegation.status,
                'destination': new_delegation.destination,
                'purpose': new_delegation.purpose,
                'expenses': [{
                    'id': exp.id,
                    'explanation': exp.explanation,
                    'payed_at': exp.payed_at.isoformat() if exp.payed_at else None,
                    'amount': float(exp.amount),
                    'pln_amount': float(exp.pln_amount),
                    'exchange_rate': float(exp.exchange_rate),
                    'currency_id': exp.currency_id,
                    'category_id': exp.category_id,
                    'status': exp.status
                } for exp in created_expenses]
            }
        }), 201
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Invalid date format: {str(e)}"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/<int:delegation_id>', methods=['GET'])
@jwt_required()
def get_delegation(delegation_id):
    """Pobranie szczegółów delegacji"""
    employee_id = get_jwt_identity()
    
    try:
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy użytkownik ma dostęp do tej delegacji
        employee = get_current_employee()
        if not employee:
            return jsonify({
                "status": "error",
                "message": "Employee not found"
            }), 404
        
        # Pracownik może zobaczyć tylko swoje delegacje
        # Menedżer może zobaczyć delegacje swoich podwładnych
        # Admin może zobaczyć wszystkie delegacje
        can_access = False
        if delegation.employee_id == employee_id:
            can_access = True
        elif employee.role == 'manager' and delegation.employee.manager_id == employee_id:
            can_access = True
        elif employee.role == 'admin':
            can_access = True
        
        if not can_access:
            return jsonify({
                "status": "error",
                "message": "Access denied"
            }), 403
        
        # Pobierz dokumenty
        documents = Document.query.filter_by(delegation_id=delegation_id).all()
        
        return jsonify({
            "status": "success",
            "delegation": {
                'id': delegation.id,
                'employee_id': delegation.employee_id,
                'start_date': delegation.start_date.isoformat() if delegation.start_date else None,
                'end_date': delegation.end_date.isoformat() if delegation.end_date else None,
                'status': delegation.status,
                'destination': delegation.destination,
                'purpose': delegation.purpose,
                'created_at': delegation.created_at.isoformat() if delegation.created_at else None,
                'documents': [{
                    'id': doc.id,
                    'filename': doc.filename,
                    'file_type': doc.file_type,
                    'description': doc.description,
                    'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None
                } for doc in documents]
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/<int:delegation_id>', methods=['PUT'])
@jwt_required()
def update_delegation(delegation_id):
    """Aktualizacja delegacji (tylko właściciel, tylko gdy status to 'draft')"""
    employee_id = get_jwt_identity()
    data = request.get_json() or {}
    
    try:
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy użytkownik jest właścicielem delegacji
        if delegation.employee_id != employee_id:
            return jsonify({
                "status": "error",
                "message": "You can only edit your own delegations"
            }), 403
        
        # Można edytować tylko delegacje w statusie 'draft'
        if delegation.status != 'draft':
            return jsonify({
                "status": "error",
                "message": f"Cannot edit delegation with status: {delegation.status}. Only 'draft' delegations can be edited."
            }), 400
        
        # Aktualizacja pól
        if 'start_date' in data:
            delegation.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        if 'end_date' in data:
            delegation.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        if 'destination' in data:
            delegation.destination = data['destination']
        
        if 'purpose' in data:
            delegation.purpose = data['purpose']
        
        # Walidacja dat
        if delegation.start_date and delegation.end_date:
            if delegation.start_date > delegation.end_date:
                return jsonify({
                    "status": "error",
                    "message": "start_date must be before or equal to end_date"
                }), 400
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Delegation updated successfully",
            "delegation": {
                'id': delegation.id,
                'start_date': delegation.start_date.isoformat() if delegation.start_date else None,
                'end_date': delegation.end_date.isoformat() if delegation.end_date else None,
                'status': delegation.status,
                'destination': delegation.destination,
                'purpose': delegation.purpose
            }
        }), 200
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Invalid date format: {str(e)}"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/<int:delegation_id>/submit', methods=['POST'])
@jwt_required()
def submit_delegation(delegation_id):
    """Przesłanie delegacji do zatwierdzenia przez menedżera"""
    employee_id = get_jwt_identity()
    
    try:
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy użytkownik jest właścicielem delegacji
        if delegation.employee_id != employee_id:
            return jsonify({
                "status": "error",
                "message": "You can only submit your own delegations"
            }), 403
        
        # Sprawdź czy delegacja ma menedżera
        employee = Employee.query.get(employee_id)
        if not employee or not employee.manager_id:
            return jsonify({
                "status": "error",
                "message": "You must be assigned to a manager to submit delegations"
            }), 400
        
        # Można przesłać tylko delegacje w statusie 'draft'
        if delegation.status != 'draft':
            return jsonify({
                "status": "error",
                "message": f"Cannot submit delegation with status: {delegation.status}. Only 'draft' delegations can be submitted."
            }), 400
        
        delegation.status = 'pending'
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Delegation submitted for approval",
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

@bp.route('/<int:delegation_id>/documents', methods=['POST'])
@jwt_required()
def add_document(delegation_id):
    """Dodanie dokumentu do delegacji"""
    employee_id = get_jwt_identity()
    
    try:
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy użytkownik jest właścicielem delegacji
        if delegation.employee_id != employee_id:
            return jsonify({
                "status": "error",
                "message": "You can only add documents to your own delegations"
            }), 403
        
        data = request.get_json() or {}
        
        if not data.get('filename') or not data.get('file_path'):
            return jsonify({
                "status": "error",
                "message": "filename and file_path are required"
            }), 400
        
        new_document = Document(
            delegation_id=delegation_id,
            expense_id=data.get('expense_id'),
            filename=data['filename'],
            file_path=data['file_path'],
            file_type=data.get('file_type'),
            description=data.get('description')
        )
        
        db.session.add(new_document)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Document added successfully",
            "document": {
                'id': new_document.id,
                'filename': new_document.filename,
                'file_type': new_document.file_type,
                'description': new_document.description
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/<int:delegation_id>/documents/<int:document_id>', methods=['DELETE'])
@jwt_required()
def delete_document(delegation_id, document_id):
    """Usunięcie dokumentu z delegacji"""
    employee_id = get_jwt_identity()
    
    try:
        delegation = Delegation.query.get(delegation_id)
        if not delegation:
            return jsonify({
                "status": "error",
                "message": "Delegation not found"
            }), 404
        
        # Sprawdź czy użytkownik jest właścicielem delegacji
        if delegation.employee_id != employee_id:
            return jsonify({
                "status": "error",
                "message": "You can only delete documents from your own delegations"
            }), 403
        
        document = Document.query.filter_by(
            id=document_id,
            delegation_id=delegation_id
        ).first()
        
        if not document:
            return jsonify({
                "status": "error",
                "message": "Document not found"
            }), 404
        
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Document deleted successfully"
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
