from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_token = db.Column(db.String(100), unique=True)
    session_expiry = db.Column(db.DateTime)
    
    tips = db.relationship('Tip', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_session_token(self):
        self.session_token = str(uuid.uuid4())
        # Set session to expire in 7 days
        self.session_expiry = datetime.utcnow() + timedelta(days=7)
        return self.session_token
    
    def is_session_valid(self):
        if not self.session_token or not self.session_expiry:
            return False
        return datetime.utcnow() < self.session_expiry
    
    def __repr__(self):
        return f'<User {self.username}>'

class Tip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    league = db.Column(db.String(100), nullable=False)
    match = db.Column(db.String(200), nullable=False)
    bet_type = db.Column(db.String(100), nullable=False)
    odds = db.Column(db.Float, nullable=False)
    stake = db.Column(db.Integer, nullable=False)
    reasoning = db.Column(db.Text)
    result = db.Column(db.String(50), default='pending')  # win, loss, pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    match_time = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Tip {self.match}>'