import re
import io
import json
import os
from typing import Optional

TIPO_COLORS = {
    'nucleo': '#0D9488',
    'basicas': '#0284C7',
    'sociohumano': '#D97706',
    'enfasis': '#7C3AED',
    'complementarias': '#DB2777',
    'electivas': '#4F46E5'
}

def cicle_sort_key(cicle: str) -> tuple:
    m= re.match(r'(Ter|Prim|Seg)Pe(\d{4})', cicle)
    if not m:
        return (9999, 0)
    year= int(m.group(2))
    period= {'Prim':1, 'Seg':2, 'Ter':3}.get(m.group(1), 9)
    return (year, period)

def build_cicle_semester_map(cicles:list) -> dict:
    unique_sorted= sorted(set(cicles), key=cicle_sort_key)
    return {c: i+1 for i, c in enumerate(unique_sorted)}

def try_float(val:str)-> Optional[float]:
    try:
        return float(val)
    except (ValueError,TypeError):
        return None

Historial_Marker = 'Historial de Cursos'

def _load_template_lookup() -> dict:
    """Load all pensum templates and build a lookup by course code."""
    lookup = {}
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'templates')
    if not os.path.isdir(templates_dir):
        return lookup
    for fname in os.listdir(templates_dir):
        if fname.startswith('pensum_') and fname.endswith('.json'):
            fpath = os.path.join(templates_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for m in data.get('materias', []):
                    code = m.get('codigo')
                    if code:
                        lookup[code] = m
            except Exception:
                continue
    return lookup

def parse_progress_report_pdf(pdf_bytes: bytes) -> dict:
    try:
        import pdfplumber
    except ImportError:
        return {'error': 'error in dependency pdfplumber'}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        start= None
        for i, page in enumerate(pdf.pages):
            if Historial_Marker in (page.extract_text() or ''):
                start = i
                break
        
        if start is None:
            return {'error': f'it cannot be finded the course historial in PDF' }
        
        combined_text = ''
        for offset, page in enumerate(pdf.pages[start:]):
            text = page.extract_text() or ''
            if offset == 0:
                text = text[text.find(Historial_Marker):]
            combined_text += '\n' + text
    raw_rows = parse_from_text(combined_text)    
    return build_output(raw_rows)

def parse_from_text(text:str) -> list:
    rows = []
    for line in text.splitlines():
        line=line.strip()
        if not re.match(r'^(Ter|Prim|Seg)Pe\d{4}', line):
            continue
        tokens=line.split()
        if len(tokens)<6:
            continue

        cicle=tokens[0]
        dept=tokens[1]
        cat= tokens[2]
        course= tokens[3].lstrip('0') or '0'
        Type= tokens[-1]
        cred= tokens[-2]

        possible_grade= tokens[-3]
        if re.match(r'^\d+\.\d+$', possible_grade):
            grade_str= possible_grade
            title_tokens= tokens[4:-3]
        else:
            grade_str= ''
            title_tokens= tokens[4:-2]
        
        title=' '.join(title_tokens)
        rows.append([cicle, dept, cat, course, title, grade_str, cred, Type])
    return rows

def build_output(raw_rows:list) -> dict:
    cicles=[r[0] for r in raw_rows if r and len(r) >=7]
    cicles_map= build_cicle_semester_map(cicles)

    template_lookup = _load_template_lookup()

    subjects = []
    grades = []
    seen = set()

    for row in raw_rows:
        if len(row) <7:
            continue
        cicle,dept,cat,course,title,grade_str,cred_str=row[:7]
        Type = row[7] if len(row) > 7 else ''

        if not course or course in seen:
            continue
        cred = try_float(cred_str) or 0.0
        if cred== 0.0:
            continue

        grade=try_float(grade_str)
        seen.add(course)
        semester= cicles_map.get(cicle,1)

        if grade is not None:
            status= 'passed' if grade >= 3.0 else 'failed'
        else:
            status = 'passed' if Type == 'Si' else 'pending'

        subjects.append ({
            'codigo': course,
            'nombre': title,
            'creditos': int(cred),
            'semestre': semester,
            'prerrequisitos': template_lookup.get(course, {}).get('prerrequisitos', []),
            'correquisitos': template_lookup.get(course, {}).get('correquisitos', []),
            'estado': status,
            'color': template_lookup.get(course, {}).get('color', TIPO_COLORS.get(Type, '#5091AF')),
            'tipo': template_lookup.get(course, {}).get('tipo', Type),
        })
        if grade is not None:
            grades.append({
                'codigo_materia': course,
                'nota': grade,
                'componentes': [],
                'fecha': None,
            })
    return {
        'version': '1.0',
        'source': 'informe_avance',
        'materias': subjects,
        'calificaciones': grades,
    }