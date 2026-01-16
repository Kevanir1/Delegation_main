"""
DEV-ONLY: Seed script to create test users
Only runs when DEV_SEED=true environment variable is set
"""
from models import db, Employee, ExpenseCategory, Currency, ExchangeRate
from flask import current_app
from datetime import date


def seed_dev_users():
    """
    Create test users for development
    Only creates users if they don't already exist
    """
    dev_seed = current_app.config.get('DEV_SEED', 'false').lower() == 'true'
    
    if not dev_seed:
        print("[SEED] DEV_SEED not enabled, skipping seed")
        return
    
    print("[SEED] DEV_SEED enabled, checking for test data...")
    
    # First, seed expense categories
    seed_expense_categories()
    
    # Then, seed currencies and exchange rates
    seed_currencies()
    
    # Finally, seed users
    seed_users()
    
    print("[SEED] Seed complete")


def seed_expense_categories():
    """Create expense categories if they don't exist"""
    categories = [
        'Hotel',
        'Transport',
        'Food',
        'Conference',
        'Other'
    ]
    
    for category_name in categories:
        existing = ExpenseCategory.query.filter_by(name=category_name).first()
        if not existing:
            new_category = ExpenseCategory(name=category_name)
            try:
                db.session.add(new_category)
                db.session.commit()
                print(f"[SEED] ✓ Created expense category: '{category_name}'")
            except Exception as e:
                db.session.rollback()
                print(f"[SEED] ✗ Failed to create category '{category_name}': {e}")
        else:
            print(f"[SEED] Expense category '{category_name}' already exists, skipping")


def seed_currencies():
    """Create currencies and exchange rates if they don't exist"""
    currencies_data = [
        {'name': 'PLN'},
        {'name': 'EUR'},
        {'name': 'USD'},
        {'name': 'GBP'}
    ]
    
    exchange_rates_data = {
        'PLN': 1.0,
        'EUR': 4.30,
        'USD': 4.05,
        'GBP': 5.10
    }
    
    for currency_data in currencies_data:
        existing = Currency.query.filter_by(name=currency_data['name']).first()
        if not existing:
            new_currency = Currency(name=currency_data['name'])
            try:
                db.session.add(new_currency)
                db.session.commit()
                print(f"[SEED] ✓ Created currency: '{currency_data['name']}'")
                
                # Add exchange rate
                rate = exchange_rates_data.get(currency_data['name'], 1.0)
                exchange_rate = ExchangeRate(
                    currency_id=new_currency.id,
                    rate_to_pln=rate,
                    date_set=date.today()
                )
                db.session.add(exchange_rate)
                db.session.commit()
                print(f"[SEED] ✓ Created exchange rate for '{currency_data['name']}': {rate} PLN")
            except Exception as e:
                db.session.rollback()
                print(f"[SEED] ✗ Failed to create currency '{currency_data['name']}': {e}")
        else:
            print(f"[SEED] Currency '{currency_data['name']}' already exists, skipping")


def seed_users():
    """
    Create test users for development
    Only creates users if they don't already exist
    """
    print("[SEED] Checking for test users...")
    
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


def init_seed(app):
    """Initialize seed on app startup"""
    with app.app_context():
        seed_dev_users()
