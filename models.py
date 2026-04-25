from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'citizen' or 'cleaner'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }

class Report(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    user_lat = db.Column(db.Float, nullable=False)
    user_lon = db.Column(db.Float, nullable=False)
    user_image_path = db.Column(db.String(255), nullable=False)
    
    cleaner_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)
    cleaner_lat = db.Column(db.Float, nullable=True)
    cleaner_lon = db.Column(db.Float, nullable=True)
    cleaner_image_path = db.Column(db.String(255), nullable=True)
    
    status = db.Column(db.String(50), default='pending') # pending, verified, rejected
    rejection_reason = db.Column(db.String(255), nullable=True)
    match_score = db.Column(db.Float, nullable=True)
    distance_meters = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    cleaner = db.relationship('User', foreign_keys=[cleaner_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict() if self.user else None,
            'user_lat': self.user_lat,
            'user_lon': self.user_lon,
            'user_image_path': self.user_image_path,
            'cleaner': self.cleaner.to_dict() if self.cleaner else None,
            'cleaner_lat': self.cleaner_lat,
            'cleaner_lon': self.cleaner_lon,
            'cleaner_image_path': self.cleaner_image_path,
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'match_score': self.match_score,
            'distance_meters': self.distance_meters,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }
