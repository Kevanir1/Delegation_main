from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Date, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

class Employee(db.Model):
    __tablename__ = 'employee'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.String(50), default='employee', nullable=False)  # employee, manager, accountant, admin
    manager_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    delegations = relationship("Delegation", back_populates="employee")
    # Relacja self-referential dla manager-employee
    manager = relationship("Employee", remote_side=[id], backref="subordinates")

class Delegation(db.Model):
    __tablename__ = 'delegation'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String, default='draft')  # draft, pending, approved, rejected, cancelled
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    name = db.Column(db.String(255))
    purpose = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    export_date = db.Column(db.DateTime)
    
    employee = relationship("Employee", back_populates="delegations")
    expenses = relationship("Expense", back_populates="delegation")
    documents = relationship("Document", back_populates="delegation", cascade="all, delete-orphan")

class Expense(db.Model):
    __tablename__ = 'expense'
    
    id = db.Column(db.Integer, primary_key=True)
    explanation = db.Column(db.Text)
    payed_at = db.Column(db.DateTime)  # Zmienione z Date na DateTime zgodnie z diagramem ERD
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    pln_amount = db.Column(db.Numeric(10, 2), nullable=False)
    exchange_rate = db.Column(db.Numeric(8, 4), nullable=False)
    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'), nullable=False)
    delegation_id = db.Column(db.Integer, db.ForeignKey('delegation.id'), nullable=False)
    status = db.Column(db.String)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    
    # Relacje zgodne z diagramem ERD
    delegation = relationship("Delegation", back_populates="expenses")
    currency = relationship("Currency", back_populates="expenses")
    category = relationship("ExpenseCategory", back_populates="expenses")

class ExpenseCategory(db.Model):
    __tablename__ = 'expense_category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    
    # Relacja zgodna z diagramem ERD: expense_category -> expense (1:N)
    expenses = relationship("Expense", back_populates="category")

class Currency(db.Model):
    __tablename__ = 'currency'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    
    # Relacje zgodne z diagramem ERD:
    # currency -> expense (1:N)
    # currency -> exchange_rate (1:N)
    expenses = relationship("Expense", back_populates="currency")
    exchange_rates = relationship("ExchangeRate", back_populates="currency")

class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rate'
    
    id = db.Column(db.Integer, primary_key=True)
    currency_id = db.Column(db.Integer, db.ForeignKey('currency.id'), nullable=False)
    rate_to_pln = db.Column(db.Numeric(8, 4), nullable=False)
    date_set = db.Column(db.Date, nullable=False)
    
    # Relacja zgodna z diagramem ERD: currency -> exchange_rate (1:N)
    currency = relationship("Currency", back_populates="exchange_rates")

class Document(db.Model):
    __tablename__ = 'document'
    
    id = db.Column(db.Integer, primary_key=True)
    delegation_id = db.Column(db.Integer, db.ForeignKey('delegation.id'), nullable=False)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=True)  # Opcjonalne - dokument może być przypisany do wydatku
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    delegation = relationship("Delegation", back_populates="documents")
    expense = relationship("Expense", backref="documents")