from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import text
from datetime import timedelta
import os
from models import db
from routes.auth import bp as auth_bp
from routes.delegations import bp as delegations_bp
from routes.admin import bp as admin_bp
from routes.manager import bp as manager_bp
from seed_users import init_seed

load_dotenv()

app = Flask(__name__)

# CORS Configuration
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/delegations_db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['DEV_SEED'] = os.getenv('DEV_SEED', 'false')

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
# Zapisujemy bcrypt w extensions, żeby był dostępny w blueprintach
app.extensions['bcrypt'] = bcrypt

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(delegations_bp, url_prefix='/api/delegations')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(manager_bp, url_prefix='/api/manager')

def run_migration_if_needed():
    """Run migration if needed (check if role column exists)"""
    try:
        with db.engine.begin() as connection:
            # Check if role column exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'employee' AND column_name = 'role'
            """))
            if result.fetchone() is None:
                print("[MIGRATION] Missing columns detected, running migration...")
                with open('migration.sql', 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                connection.execute(text(migration_sql))
                print("[MIGRATION] ✓ Migration completed")
            else:
                print("[MIGRATION] Database schema is up to date")
    except Exception as e:
        print(f"[MIGRATION] Warning: Could not check/run migration: {e}")
        print("[MIGRATION] You may need to run migration.sql manually")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Run migration if needed
        run_migration_if_needed()
        # Run seed after DB initialization
        init_seed(app)
    app.run(host='0.0.0.0', port=5000, debug=True)
