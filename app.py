import os
import uuid
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Report, User
from image_processing import compare_images
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///waste_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# Haversine formula to calculate distance between two lat/lon points in meters
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371e3 # Earth radius in meters
    phi1 = lat1 * math.pi / 180
    phi2 = lat2 * math.pi / 180
    delta_phi = (lat2 - lat1) * math.pi / 180
    delta_lambda = (lon2 - lon1) * math.pi / 180
    
    a = math.sin(delta_phi / 2) * math.sin(delta_phi / 2) + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) * math.sin(delta_lambda / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/')
def home():
    return jsonify({"message": "EcoClean API Running"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'username' not in data or 'password' not in data or 'role' not in data:
        return jsonify({"error": "Missing required fields"}), 400
        
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
        
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'], 
        password_hash=hashed_password, 
        role=data['role']
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully", "user": new_user.to_dict()}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Missing username or password"}), 400
        
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({"error": "Invalid username or password"}), 401
        
    return jsonify({"message": "Login successful", "user": user.to_dict()}), 200

@app.route('/api/report', methods=['POST'])
def create_report():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
    
    file = request.files['image']
    user_id = request.form.get('user_id')
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    
    if not user_id or not lat or not lon:
        return jsonify({"error": "Missing user_id, lat, or lon"}), 400
        
    user = User.query.get(user_id)
    if not user or user.role != 'citizen':
        return jsonify({"error": "Only registered citizens can report waste"}), 403
        
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(f"user_{uuid.uuid4().hex}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        new_report = Report(
            user_id=user_id,
            user_lat=float(lat),
            user_lon=float(lon),
            user_image_path=filepath
        )
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
    cleaner_id = request.form.get('cleaner_id')
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    
    if not cleaner_id or not lat or not lon:
        return jsonify({"error": "Missing cleaner_id, lat, or lon"}), 400
        
    cleaner = User.query.get(cleaner_id)
    if not cleaner or cleaner.role != 'cleaner':
        return jsonify({"error": "Only registered cleaners can verify cleanups"}), 403
        
    if report.user_id == cleaner_id:
        return jsonify({"error": "You cannot verify a task that you reported yourself"}), 403
        
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = secure_filename(f"cleaner_{uuid.uuid4().hex}.jpg")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        report.cleaner_id = cleaner_id
        report.cleaner_image_path = filepath
        report.cleaner_lat = float(lat)
        report.cleaner_lon = float(lon)
        
        # Calculate distance
        distance = calculate_distance(report.user_lat, report.user_lon, report.cleaner_lat, report.cleaner_lon)
        report.distance_meters = distance
        
        if distance > 100:
            report.status = 'rejected'
            report.rejection_reason = f'Verification rejected: Cleaner is too far from report location ({int(distance)}m).'
            db.session.commit()
            return jsonify({
                "error": report.rejection_reason,
                "distance": distance
            }), 400
        
        # Compare images
        difference, match_score = compare_images(report.user_image_path, report.cleaner_image_path)
        
        if difference < 0.05:
            report.status = 'rejected'
            report.rejection_reason = 'Verification rejected: AI detected no meaningful change between before and after photos.'
        else:
            report.status = 'verified'
            report.rejection_reason = None
            
        report.match_score = match_score
        db.session.commit()
        
        return jsonify({
            "message": "Cleanup verification processed",
            "report": report.to_dict(),
            "comparison": {
                "difference": difference,
                "match_score": match_score,
                "distance_meters": distance
            }
        }), 200

@app.route('/api/reports', methods=['GET'])
def get_reports():
    user_id = request.args.get('user_id')
    if user_id:
        reports = Report.query.filter_by(user_id=user_id).all()
    else:
        reports = Report.query.all()
    return jsonify([report.to_dict() for report in reports]), 200

@app.route('/api/rate/<report_id>', methods=['POST'])
def rate_cleaner(report_id):
    data = request.json
    user_id = data.get('user_id')
    rating = data.get('rating')

    if not user_id or not rating:
        return jsonify({"error": "Missing user_id or rating"}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
    except ValueError:
        return jsonify({"error": "Rating must be a number"}), 400

    report = Report.query.get(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    if report.user_id != user_id:
        return jsonify({"error": "Only the citizen who created this report can rate it"}), 403

    if report.status != 'verified':
        return jsonify({"error": "You can only rate verified cleanups"}), 400

    report.rating = rating
    db.session.commit()

    return jsonify({"message": "Rating saved successfully", "report": report.to_dict()}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)


