import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template # Added render_template
from flask_cors import CORS # Added CORS

# Remove user model and routes as they are not used for this project
# from src.models.user import db
# from src.routes.user import user_bp
from src.routes.api_routes import api_bp # Import the new api_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'), template_folder=os.path.join(os.path.dirname(__file__), 'templates')) # Specified template_folder
CORS(app) # Enable CORS for all routes

app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Register the API blueprint for scoring
app.register_blueprint(api_bp, url_prefix='/api')

# The user_bp is not needed for this application, so it's removed.
# app.register_blueprint(user_bp, url_prefix='/api') 

# Database setup is not needed for this version of the application
# app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'mydb')}"
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db.init_app(app)
# with app.app_context():
#     db.create_all()

@app.route('/')
def serve_index():
    # Serve index.html from the templates folder
    return render_template('index.html')

# This route is for serving other static files if needed, but index.html is handled by serve_index
# @app.route('/<path:path>')
# def serve_static_files(path):
#     static_folder_path = app.static_folder
#     if static_folder_path is None:
#             return "Static folder not configured", 404
# 
#     if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
#         return send_from_directory(static_folder_path, path)
#     else:
#         # Fallback to index.html if path not found, handled by '/' route now
#         return send_from_directory(static_folder_path, 'index.html')

if __name__ == '__main__':
    # Ensure python-dotenv is installed if .env file is used for API keys
    try:
        from dotenv import load_dotenv
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            print("Loaded .env file")
    except ImportError:
        print("python-dotenv not installed, .env file will not be loaded automatically by main.py. Ensure GOOGLE_GEMINI_API_KEY is set in environment.")
    app.run(host='0.0.0.0', port=8000, debug=True)
