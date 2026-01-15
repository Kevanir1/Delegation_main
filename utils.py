"""
Utility functions for role-based access control
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from models import Employee

def require_role(*allowed_roles):
    """
    Decorator to require specific role(s) for an endpoint
    Usage: @require_role('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            employee_id = get_jwt_identity()
            if not employee_id:
                return jsonify({
                    "status": "error",
                    "message": "Authentication required"
                }), 401
            
            employee = Employee.query.get(employee_id)
            if not employee:
                return jsonify({
                    "status": "error",
                    "message": "Employee not found"
                }), 404
            
            if not employee.is_active:
                return jsonify({
                    "status": "error",
                    "message": "Account is inactive"
                }), 403
            
            if employee.role not in allowed_roles:
                return jsonify({
                    "status": "error",
                    "message": f"Access denied. Required role: {', '.join(allowed_roles)}"
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_employee():
    """Helper function to get current employee from JWT"""
    employee_id = get_jwt_identity()
    if not employee_id:
        return None
    return Employee.query.get(employee_id)
