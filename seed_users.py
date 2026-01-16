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
    
    # Test user data - po jednym koncie dla każdej roli
    test_users = [
        {
            'username': 'pracownik',
            'email': 'pracownik@example.com',
            'password': '12345678',
            'role': 'employee',
            'manager_id': None  # Będzie przypisany do menedżera później
        },
        {
            'username': 'menedzer',
            'email': 'menedzer@example.com',
            'password': '12345678',
            'role': 'manager',
            'manager_id': None
        },
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'password': '12345678',
            'role': 'admin',
            'manager_id': None
        }
    ]
    
    bcrypt = current_app.extensions.get('bcrypt')
    if not bcrypt:
        print("[SEED] ERROR: Bcrypt not initialized")
        return
    
    # Najpierw utwórz wszystkich użytkowników
    created_users = {}
    
    for user_data in test_users:
        # Check if user already exists
        existing_user = Employee.query.filter_by(email=user_data['email']).first()
        
        if existing_user:
            print(f"[SEED] User '{user_data['username']}' ({user_data['email']}) already exists, skipping")
            created_users[user_data['role']] = existing_user
            continue
        
        # Hash password using the same logic as /api/auth/register
        hashed_password = bcrypt.generate_password_hash(user_data['password']).decode('utf-8')
        
        # Create new user
        new_user = Employee(
            username=user_data['username'],
            email=user_data['email'],
            password=hashed_password,
            role=user_data['role'],
            is_active=True,
            manager_id=user_data.get('manager_id')
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"[SEED] ✓ Created test user: '{user_data['username']}' ({user_data['email']}) - Role: {user_data['role']}")
            created_users[user_data['role']] = new_user
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] ✗ Failed to create user '{user_data['username']}': {e}")
    
    # Przypisz pracownika do menedżera
    if 'employee' in created_users and 'manager' in created_users:
        employee = created_users['employee']
        manager = created_users['manager']
        
        if employee.manager_id != manager.id:
            employee.manager_id = manager.id
            try:
                db.session.commit()
                print(f"[SEED] ✓ Assigned employee '{employee.username}' to manager '{manager.username}'")
            except Exception as e:
                db.session.rollback()
                print(f"[SEED] ✗ Failed to assign manager: {e}")
    
    print("[SEED] Seed complete")


def init_seed(app):
    """Initialize seed on app startup"""
    with app.app_context():
        seed_dev_users()
