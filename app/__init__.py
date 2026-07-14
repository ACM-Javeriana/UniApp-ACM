"""
Uni-App: University Academic Management Application
Flask Application Factory
"""
from flask import Flask
from app.config import config
import os
from pathlib import Path


def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


# Load .env on module import
load_env()


def create_app(config_name: str = None) -> Flask:
    """
    Application Factory Pattern
    Creates and configures the Flask application
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    # Load configuration
    app.config.from_object(config[config_name])

    if app.config.get('DEBUG'):
        @app.after_request
        def add_dev_no_cache_headers(response):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
    
    # Register blueprints
    from app.blueprints.pensum import pensum_bp
    from app.blueprints.semester import semester_bp
    from app.blueprints.schedule import schedule_bp
    from app.blueprints.api import api_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.faq import faq_bp

    app.register_blueprint(pensum_bp)
    app.register_blueprint(semester_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)
    app.register_blueprint(faq_bp)
    
    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        # VERCEL_GIT_COMMIT_SHA is provided by Vercel during deployment
        commit_sha = os.environ.get('VERCEL_GIT_COMMIT_SHA', '')

        def asset_version(filename: str) -> str:
            asset_path = Path(app.static_folder) / filename
            try:
                return str(int(asset_path.stat().st_mtime))
            except OSError:
                return 'dev'

        return {
            'commit_sha': commit_sha[:7] if commit_sha else 'dev',
            'asset_version': asset_version
        }
    
    # Register main route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('pensum.index'))
    
    return app
