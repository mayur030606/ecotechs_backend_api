import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Report
from image_processing import compare_images
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///waste.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return jsonify({"message": "EcoClean API Running"})

@app.route('/api/report', methods=['POST'])
def create_report():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(f"user_{uuid.uuid4().hex}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        new_report = Report(user_image_path=filepath)
        db.session.add(new_report)
        db.session.commit()
        
        return jsonify({
            "message": "Report created successfully",
            "report": new_report.to_dict()
        }), 201

@app.route('/api/verify/<report_id>', methods=['POST'])
def verify_cleanup(report_id):
    report = Report.query.get(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
        
    if report.status != 'pending':
        return jsonify({"error": f"Report already processed with status: {report.status}"}), 400

    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = secure_filename(f"cleaner_{uuid.uuid4().hex}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        report.cleaner_image_path = filepath
        
        # Compare images
        difference, match_score = compare_images(report.user_image_path, report.cleaner_image_path)
        
        # Determine status (if difference is small, it implies it looks the same... wait!)
        # Wait, if difference is high, it means it was cleaned.
        # Let's keep the logic from before, but adjust for waste.
        # Actually in the previous `app.py`, difference < 0.05 meant "no_change".
        # So if difference >= 0.05, it means it's processed/cleaned.
        
        if difference < 0.05:
            report.status = 'rejected'
        else:
            report.status = 'verified'
            
        report.match_score = match_score
        db.session.commit()
        
        return jsonify({
            "message": "Cleanup verification processed",
            "report": report.to_dict(),
            "comparison": {
                "difference": difference,
                "match_score": match_score
            }
        }), 200

@app.route('/api/reports', methods=['GET'])
def get_reports():
    reports = Report.query.all()
    return jsonify([report.to_dict() for report in reports]), 200

@app.route('/api/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    report = Report.query.get(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report.to_dict()), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
