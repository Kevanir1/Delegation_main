"""
DEV-ONLY: Seed script to create test users
Only runs when DEV_SEED=true environment variable is set
"""
from models import db, Employee
from flask import current_app


def seed_dev_users():
    """
    Create test users for development
    Only creates users if they don't already exist
    """
    dev_seed = current_app.config.get('DEV_SEED', 'false').lower() == 'true'
    
    if not dev_seed:
        print("[SEED] DEV_SEED not enabled, skipping seed")
        return
    
    print("[SEED] DEV_SEED enabled, checking for test users...")
    
    # Test user data
    test_users = [
        {
            'username': 'adamas',
            'email': 'adamas@example.com',
            'password': '12345678'
        }
    ]
    
    bcrypt = current_app.extensions.get('bcrypt')
    if not bcrypt:
        print("[SEED] ERROR: Bcrypt not initialized")
        return
    
    for user_data in test_users:
        # Check if user already exists
        existing_user = Employee.query.filter_by(email=user_data['email']).first()
        
        if existing_user:
            print(f"[SEED] User '{user_data['username']}' ({user_data['email']}) already exists, skipping")
            continue
        
        # Hash password using the same logic as /api/auth/register
        hashed_password = bcrypt.generate_password_hash(user_data['password']).decode('utf-8')
        
        # Create new user
        new_user = Employee(
            username=user_data['username'],
            email=user_data['email'],
            password=hashed_password,
            is_active=True
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"[SEED] ✓ Created test user: '{user_data['username']}' ({user_data['email']})")
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] ✗ Failed to create user '{user_data['username']}': {e}")
    
    print("[SEED] Seed complete")


def init_seed(app):
    """Initialize seed on app startup"""
    with app.app_context():
        seed_dev_users()
