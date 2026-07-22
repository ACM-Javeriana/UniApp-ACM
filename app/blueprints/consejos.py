"""
Consejos Blueprint
Consejos de inductores por carrera
"""
from flask import Blueprint, render_template

consejos_bp = Blueprint('consejos', __name__, url_prefix='/consejos')


@consejos_bp.route('/')
def index():
    return render_template('consejos/index.html')
