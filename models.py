from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Date, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacja z Employee (opcjonalna - dla autentykacji, nie jest w diagramie ERD)
    # Diagram ERD pokazuje tylko employee, ale user jest potrzebny do logowania
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    employee = relationship("Employee", backref="users")

class Employee(db.Model):
    __tablename__ = 'employee'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    surname = db.Column(db.String, nullable=False)
    sex = db.Column(db.String)
    role = db.Column(db.String)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    
    delegations = relationship("Delegation", back_populates="employee")

class Delegation(db.Model):
    __tablename__ = 'delegation'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String, default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    export_date = db.Column(db.DateTime)
    
    employee = relationship("Employee", back_populates="delegations")
    expenses = relationship("Expense", back_populates="delegation")

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