from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Report(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_image_path = db.Column(db.String(255), nullable=False)
    cleaner_image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='pending') # pending, verified, rejected
    match_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_image_path': self.user_image_path,
            'cleaner_image_path': self.cleaner_image_path,
            'status': self.status,
            'match_score': self.match_score,
            'created_at': self.created_at.isoformat()
        }
