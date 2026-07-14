"""
FAQ Blueprint
Preguntas frecuentes sobre el reglamento académico de la Javeriana
"""
from flask import Blueprint, render_template

faq_bp = Blueprint('faq', __name__, url_prefix='/faq')


@faq_bp.route('/')
def index():
    return render_template('faq/index.html')
