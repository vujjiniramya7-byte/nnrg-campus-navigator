import os
from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/metrics')
def get_metrics():
    # Return simulated real-time metrics data for college dashboard
    data = {
        "enrolled": "2,500+",
        "placementRate": "95%",
        "avgPackage": "₹53 LPA",
        "partners": "50+",
        "recentPlacements": [
            "TCS: 12 LPA",
            "ICICI: 8 LPA",
            "Cognizant: 10 LPA",
            "Microsoft: 53 LPA"
        ],
        "admissionStatus": "Category-B / NRI Admissions Open",
        "timestamp": 2026
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
