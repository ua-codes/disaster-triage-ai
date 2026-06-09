from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import json
import os
from datetime import datetime
import base64

app = Flask(__name__)
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# Load reports
def load_reports():
    if os.path.exists('data/reports.json'):
        with open('data/reports.json', 'r') as f:
            return json.load(f)
    return []

def save_reports(reports):
    os.makedirs('data', exist_ok=True)
    with open('data/reports.json', 'w') as f:
        json.dump(reports, f, indent=2)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    reports = load_reports()
    reports.sort(key=lambda x: {
        'CRITICAL': 0,
        'HIGH': 1,
        'MODERATE': 2,
        'LOW': 3
    }.get(x.get('priority'), 4))
    return render_template('dashboard.html', reports=reports)

@app.route('/api/upload', methods=['POST'])
def upload_report():
    try:
        image_file = request.files['image']
        location = request.form.get('location')
        description = request.form.get('description')
        disaster_type = request.form.get('disaster_type')
        
        image_data = image_file.read()
        
        # Analyze with Gemini
        model = genai.GenerativeModel('gemini-pro-vision')
        prompt = f"Analyze this {disaster_type} damage image. Return ONLY JSON with severity (1-5), hazards list, and status."
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": base64.b64encode(image_data).decode()}
        ])
        
        assessment = response.text
        
        # Calculate priority
        from risk_scorer import calculate_priority
        priority = calculate_priority(disaster_type, assessment, description)
        
        # Save report
        reports = load_reports()
        report = {
            'id': len(reports),
            'timestamp': datetime.now().isoformat(),
            'disaster_type': disaster_type,
            'location': location,
            'description': description,
            'assessment': assessment,
            'priority': priority['priority'],
            'hazards': priority['hazards'],
            'severity': priority['severity']
        }
        reports.append(report)
        save_reports(reports)
        
        return jsonify({
            'success': True,
            'report_id': len(reports) - 1,
            'priority': priority['priority'],
            'severity': priority['severity'],
            'hazards': priority['hazards']
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/reports')
def get_reports():
    reports = load_reports()
    reports.sort(key=lambda x: {
        'CRITICAL': 0, 'HIGH': 1, 'MODERATE': 2, 'LOW': 3
    }.get(x.get('priority'), 4))
    return jsonify(reports)

if __name__ == '__main__':
    app.run(debug=True)