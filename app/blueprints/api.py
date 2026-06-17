"""
API Blueprint
REST API endpoints for frontend communication
"""
from datetime import datetime, timezone
import os

from flask import Blueprint, request, jsonify, Response
from app.models.materia import Materia, MateriaStatus, Pensum
from app.models.clase import Clase, BloqueHorario, DayOfWeek
from app.models.horario import Franja, FranjaStatus, HorarioCombination
from app.models.configuracion import Configuracion, Calificacion
from app.services.pensum_service import PensumService
from app.services.gpa_service import GPAService
from app.services.schedule_service import ScheduleService
from app.services.export_service import ExportService
from app.services.database import DatabaseService
from app.services.parser_service import ParserService


api_bp = Blueprint('api', __name__)


# ==================== Auth Endpoints ====================

@api_bp.route('/keepalive', methods=['GET'])
def keepalive():
    """Lightweight database ping for scheduled keepalive jobs."""
    expected_secret = os.environ.get('KEEPALIVE_SECRET', '').strip()
    provided_secret = request.headers.get('X-Keepalive-Secret', '').strip() or request.args.get('secret', '').strip()

    if expected_secret and provided_secret != expected_secret:
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

    result = DatabaseService.keepalive()
    status_code = 200 if result.get('ok') else 503

    return jsonify({
        **result,
        'checked_at': datetime.now(timezone.utc).isoformat()
    }), status_code

@api_bp.route('/auth/signup', methods=['POST'])
def signup():
    """Register a new user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    result = DatabaseService.sign_up(email, password)
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@api_bp.route('/auth/signin', methods=['POST'])
def signin():
    """Sign in existing user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    result = DatabaseService.sign_in(email, password)
    if 'error' in result:
        return jsonify(result), 401
    
    return jsonify(result)


@api_bp.route('/auth/signout', methods=['POST'])
def signout():
    """Sign out user"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header else ''
    
    result = DatabaseService.sign_out(token)
    return jsonify(result)


@api_bp.route('/auth/verify', methods=['POST'])
def verify_email():
    """Verify email confirmation token"""
    data = request.get_json()
    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    
    if not access_token:
        return jsonify({'error': 'Token de acceso requerido', 'error_code': 'invalid_token'}), 400
    
    result = DatabaseService.verify_token(access_token, refresh_token)
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@api_bp.route('/auth/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email requerido'}), 400
    
    result = DatabaseService.resend_verification(email)
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@api_bp.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token requerido'}), 400
    
    result = DatabaseService.refresh_session(refresh_token)
    if 'error' in result:
        return jsonify(result), 401
    
    return jsonify(result)


# ==================== Sync Endpoints ====================

@api_bp.route('/sync', methods=['POST'])
def sync_data():
    """Sync local data to cloud (for authenticated users)"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Extract token from header
    access_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    result = DatabaseService.sync_all_data(user_id, data, access_token)
    if 'error' in result:
        # Include details for debugging
        return jsonify(result), 400
    
    return jsonify(result)


@api_bp.route('/sync/pull', methods=['GET'])
def pull_data():
    """Pull data from cloud"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Extract token from header
    access_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
    
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    data = {}
    updated_at = {}
    
    pensum_result = DatabaseService.get_pensum(user_id, access_token)
    if pensum_result.get('data') is not None:
        data['pensum'] = pensum_result['data']
    if pensum_result.get('updated_at'):
        updated_at['pensum'] = pensum_result['updated_at']
    
    clases_result = DatabaseService.get_clases(user_id, access_token)
    if clases_result.get('data') is not None:
        data['clases'] = clases_result['data']
    if clases_result.get('updated_at'):
        updated_at['clases'] = clases_result['updated_at']
    
    config_result = DatabaseService.get_configuracion(user_id, access_token)
    if config_result.get('data') is not None:
        data['configuracion'] = config_result['data']
    if config_result.get('updated_at'):
        updated_at['configuracion'] = config_result['updated_at']
    
    calificaciones_result = DatabaseService.get_calificaciones(user_id, access_token)
    if calificaciones_result.get('data') is not None:
        data['calificaciones'] = calificaciones_result['data']
    if calificaciones_result.get('updated_at'):
        updated_at['calificaciones'] = calificaciones_result['updated_at']
    
    franjas_result = DatabaseService.get_franjas(user_id, access_token)
    if franjas_result.get('data') is not None:
        data['franjas'] = franjas_result['data']
    if franjas_result.get('updated_at'):
        updated_at['franjas'] = franjas_result['updated_at']

    if updated_at:
        data['_updated_at'] = updated_at
        data['_latest_updated_at'] = max(updated_at.values())

    return jsonify({'data': data})


# ==================== Pensum Endpoints ====================

@api_bp.route('/pensum/validate', methods=['POST'])
def validate_pensum():
    """Validate pensum structure"""
    data = request.get_json()
    
    try:
        pensum = Pensum.from_dict(data)
        result = PensumService.validate_pensum_structure(pensum)
        return jsonify(result)
    except Exception as e:
        return jsonify({'valid': False, 'errors': [str(e)]}), 400


@api_bp.route('/pensum/simulate-loss', methods=['POST'])
def simulate_loss():
    """Simulate losing a course"""
    data = request.get_json()
    materia_code = data.get('materia_code')
    pensum_data = data.get('pensum')
    
    if not materia_code or not pensum_data:
        return jsonify({'error': 'materia_code and pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        result = PensumService.simulate_course_loss(materia_code, pensum)
        
        if 'error' in result:
            return jsonify(result), 404
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/pensum/can-move', methods=['POST'])
def can_move_course():
    """Check if a course can be moved to another semester"""
    data = request.get_json()
    materia_code = data.get('materia_code')
    target_semester = data.get('target_semester')
    pensum_data = data.get('pensum')
    
    if not all([materia_code, target_semester, pensum_data]):
        return jsonify({'error': 'materia_code, target_semester, and pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        materia = pensum.get_materia(materia_code)
        
        if not materia:
            return jsonify({'error': f"Course '{materia_code}' not found"}), 404
        
        result = PensumService.can_move_to_semester(materia, target_semester, pensum)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/pensum/materia', methods=['POST'])
def create_materia():
    """Create a new course"""
    data = request.get_json()
    materia_data = data.get('materia')
    pensum_data = data.get('pensum')
    
    if not materia_data or not pensum_data:
        return jsonify({'error': 'materia and pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        result = PensumService.create_materia(materia_data, pensum)
        
        if 'error' in result:
            return jsonify(result), 400
        
        result['pensum'] = pensum.to_dict()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/pensum/materia/<code>', methods=['PUT'])
def update_materia(code: str):
    """Update an existing course"""
    data = request.get_json()
    materia_data = data.get('materia')
    pensum_data = data.get('pensum')
    
    if not materia_data or not pensum_data:
        return jsonify({'error': 'materia and pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        result = PensumService.update_materia(code, materia_data, pensum)
        
        if 'error' in result:
            return jsonify(result), 400
        
        result['pensum'] = pensum.to_dict()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/pensum/materia/<code>', methods=['DELETE'])
def delete_materia(code: str):
    """Delete a course"""
    data = request.get_json()
    pensum_data = data.get('pensum')
    
    if not pensum_data:
        return jsonify({'error': 'pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        result = PensumService.delete_materia(code, pensum)
        
        if 'error' in result:
            return jsonify(result), 400
        
        result['pensum'] = pensum.to_dict()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/pensum/credits-check', methods=['POST'])
def check_credits():
    """Check if credits can be added to a semester"""
    data = request.get_json()
    credits_to_add = data.get('credits', 0)
    semester = data.get('semester')
    pensum_data = data.get('pensum')
    max_credits = data.get('max_credits', 21)
    
    if semester is None or not pensum_data:
        return jsonify({'error': 'semester and pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        result = PensumService.can_add_to_semester(credits_to_add, semester, pensum, max_credits)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==================== GPA Endpoints ====================

@api_bp.route('/gpa/semester', methods=['POST'])
def calculate_semester_gpa():
    """Calculate GPA for a specific semester"""
    data = request.get_json()
    semester = data.get('semester')
    pensum_data = data.get('pensum')
    config_data = data.get('config', {})
    
    if semester is None or not pensum_data:
        return jsonify({'error': 'semester and pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        config = Configuracion.from_dict(config_data) if config_data else None
        result = GPAService.calculate_semester_gpa(semester, pensum, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/gpa/cumulative', methods=['POST'])
def calculate_cumulative_gpa():
    """Calculate cumulative GPA"""
    data = request.get_json()
    pensum_data = data.get('pensum')
    config_data = data.get('config', {})
    
    if not pensum_data:
        return jsonify({'error': 'pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        config = Configuracion.from_dict(config_data) if config_data else None
        result = GPAService.calculate_cumulative_gpa(pensum, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/gpa/simulate', methods=['POST'])
def simulate_grades():
    """Simulate grades and see impact on GPA"""
    data = request.get_json()
    pensum_data = data.get('pensum')
    simulated_grades = data.get('simulated_grades', {})
    config_data = data.get('config', {})
    
    if not pensum_data:
        return jsonify({'error': 'pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        config = Configuracion.from_dict(config_data) if config_data else None
        result = GPAService.simulate_grades(pensum, simulated_grades, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/gpa/needed', methods=['POST'])
def get_needed_grade():
    """Calculate needed grade for target GPA"""
    data = request.get_json()
    pensum_data = data.get('pensum')
    target_gpa = data.get('target_gpa')
    remaining_courses = data.get('remaining_courses', [])
    config_data = data.get('config', {})
    
    if not pensum_data or target_gpa is None:
        return jsonify({'error': 'pensum and target_gpa required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        config = Configuracion.from_dict(config_data) if config_data else None
        result = GPAService.get_needed_grade_for_target(pensum, target_gpa, remaining_courses, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/gpa/alerts', methods=['POST'])
def get_gpa_alerts():
    """Get GPA alerts"""
    data = request.get_json()
    pensum_data = data.get('pensum')
    config_data = data.get('config', {})
    
    if not pensum_data:
        return jsonify({'error': 'pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        config = Configuracion.from_dict(config_data) if config_data else None
        alerts = GPAService.check_gpa_alerts(pensum, config)
        return jsonify({'alerts': alerts})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/gpa/progress', methods=['POST'])
def get_academic_progress():
    """Get comprehensive academic progress"""
    data = request.get_json()
    pensum_data = data.get('pensum')
    config_data = data.get('config', {})
    
    if not pensum_data:
        return jsonify({'error': 'pensum required'}), 400
    
    try:
        pensum = Pensum.from_dict(pensum_data)
        config = Configuracion.from_dict(config_data) if config_data else None
        result = GPAService.get_academic_progress(pensum, config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==================== Schedule Endpoints ====================

@api_bp.route('/schedule/conflicts', methods=['POST'])
def check_schedule_conflicts():
    """Check for conflicts between classes"""
    data = request.get_json()
    clases_data = data.get('clases', [])
    
    try:
        clases = [Clase.from_dict(c) for c in clases_data]
        conflicts = ScheduleService.check_conflicts(clases)
        return jsonify({
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/schedule/generate', methods=['POST'])
def generate_schedules():
    """Generate all valid schedule combinations"""
    data = request.get_json()
    clases_by_materia = data.get('clases_by_materia', {})
    franjas_data = data.get('franjas', [])
    max_combinations = data.get('max_combinations')
    
    try:
        # Convert clases data
        converted_clases = {}
        for materia_code, clases_list in clases_by_materia.items():
            converted_clases[materia_code] = [Clase.from_dict(c) for c in clases_list]
        
        # Convert franjas
        franjas = [Franja.from_dict(f) for f in franjas_data]
        
        result = ScheduleService.generate_combinations(
            converted_clases,
            franjas,
            max_combinations
        )
        
        # Convert combinations to dict
        result['combinations'] = [c.to_dict() for c in result['combinations']]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/schedule/filter', methods=['POST'])
def filter_schedules():
    """Filter and sort schedule combinations"""
    data = request.get_json()
    combinations_data = data.get('combinations', [])
    filters = data.get('filters', {})
    
    try:
        combinations = [HorarioCombination.from_dict(c) for c in combinations_data]
        filtered = ScheduleService.filter_combinations(combinations, filters)
        
        return jsonify({
            'combinations': [c.to_dict() for c in filtered],
            'total': len(filtered)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/schedule/presets', methods=['GET'])
def get_filter_presets():
    """Get optimization presets"""
    presets = ScheduleService.get_optimization_presets()
    return jsonify({'presets': presets})


@api_bp.route('/schedule/grid', methods=['POST'])
def get_schedule_grid():
    """Get grid representation of a schedule"""
    data = request.get_json()
    combination_data = data.get('combination')
    
    if not combination_data:
        return jsonify({'error': 'combination required'}), 400
    
    try:
        combination = HorarioCombination.from_dict(combination_data)
        grid = ScheduleService.get_schedule_grid(combination)
        return jsonify(grid)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/schedule/validate-class', methods=['POST'])
def validate_class():
    """Validate class data before creation"""
    data = request.get_json()
    result = ScheduleService.validate_class_data(data)
    return jsonify(result)


# ==================== Export Endpoints ====================

@api_bp.route('/export/ics', methods=['POST'])
def export_ics():
    """Export schedule as ICS file"""
    data = request.get_json()
    combination_data = data.get('combination')
    semester_start = data.get('semester_start')
    semester_end = data.get('semester_end')
    course_names = data.get('course_names', {})
    
    if not all([combination_data, semester_start, semester_end]):
        return jsonify({'error': 'combination, semester_start, and semester_end required'}), 400
    
    # Validate dates
    date_validation = ExportService.validate_export_dates(semester_start, semester_end)
    if not date_validation['valid']:
        return jsonify({'error': date_validation['error']}), 400
    
    try:
        combination = HorarioCombination.from_dict(combination_data)
        ics_content = ExportService.generate_ics(
            combination,
            semester_start,
            semester_end,
            course_names
        )
        
        return Response(
            ics_content,
            mimetype='text/calendar',
            headers={
                'Content-Disposition': 'attachment; filename=horario.ics'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/export/html', methods=['POST'])
def export_html():
    """Get HTML for PNG export (rendered client-side)"""
    data = request.get_json()
    combination_data = data.get('combination')
    course_names = data.get('course_names', {})
    course_colors = data.get('course_colors', {})
    
    if not combination_data:
        return jsonify({'error': 'combination required'}), 400
    
    try:
        combination = HorarioCombination.from_dict(combination_data)
        html = ExportService.get_schedule_html_for_export(
            combination,
            course_names,
            course_colors
        )
        return jsonify({'html': html})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==================== Course Grade Calculation ====================

@api_bp.route('/grade/calculate', methods=['POST'])
def calculate_course_grade():
    """Calculate grade for a course based on individual evaluations"""
    data = request.get_json()
    calificaciones_data = data.get('calificaciones', [])
    include_simulation = data.get('include_simulation', True)
    
    try:
        calificaciones = [Calificacion.from_dict(c) for c in calificaciones_data]
        result = GPAService.calculate_course_grade_with_simulation(
            calificaciones,
            include_simulation
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==================== Parser endpoints ====================

@api_bp.route('/parser/parse', methods=['POST'])
def parse_raw_classes():
    """
    Parse raw HTML data obtained from intranet
    Needs to be provided as a string in the 'raw_html' field of the request body
    """

    data = request.get_json()
    raw_html = data.get('raw_html')
    
    if not raw_html:
        return jsonify({'error': 'raw_html required'}), 400
    
    try:
        result = ParserService.parse_raw_data(raw_html)
        return jsonify(result)
    except Exception as e:
        return jsonify({'failed to parse raw HTML error: ': str(e)}), 400
