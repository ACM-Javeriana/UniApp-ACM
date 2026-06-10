"""
Parser Service
Service defined for parsing raw intranet data obtained from request of searching classes
"""
from datetime import datetime
from typing import Dict, Optional, Any
from app.blueprints.pensum import index
from app.models.clase import Clase, BloqueHorario, DayOfWeek
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
import re


"""
{
    "codigo_materia": "MAT101",
    "nombre_materia": "Cálculo I",
    "seccion": "A1",
    "profesor": "Dr. García",
    "creditos": 4,
    "bloques": [
        { "dia": "L", "hora_inicio": "07:00", "hora_fin": "09:00" },
        { "dia": "W", "hora_inicio": "07:00", "hora_fin": "09:00" }
    ]
},
"""


class ParserService:
    """
    Service for parsing raw data class input
    and returning json serializable data for the API response.
    """
    GROUPBOX_PATTERN = re.compile(r"^win0divSSR_CLSRSLT_WRK_GROUPBOX2\$\d+$")
    CLASS_NBR_PATTERN = re.compile(r"^MTG_CLASS_NBR\$\d+$")
    HEADER_CLASS = "PAGROUPBOXLABELLEVEL1"

    FIELD_BASE_IDS = {
        "class_number": "MTG_CLASS_NBR",
        "section": "MTG_CLASSNAME",
        "days_times": "MTG_DAYTIME",
        "room": "MTG_ROOM",
        "instructor": "MTG_INSTR",
        "dates": "MTG_TOPIC",
    }
    STATUS_BASE_ID = "DERIVED_CLSRCH_SSR_STATUS_LONG"
    
    DAY_MAPPING = {
        "Lun": "L",
        "Mart": "M",
        "Miérc": "W",
        "Jue": "J",
        "V": "V",
        "Sáb": "S",
        "Dom": "D"
    }


    @staticmethod
    def parse_header(header_text: str) -> tuple[str, str, Optional[str]]:
        subject = ""
        catalog_number = ""
        course = ""
        
        if not header_text:
            return subject, catalog_number, course

        parts = [p.strip() for p in header_text.split('-')]
        if len(parts) > 0:
            sub_parts = parts[0].split(None, 1)
            if len(sub_parts) >= 2:
                subject = sub_parts[0]
                catalog_number = sub_parts[1]
            else:
                subject = parts[0]
                catalog_number = ""
        if len(parts) > 1:
            course = parts[1]

        return subject, catalog_number, course
    
    @staticmethod
    def extract_element_text(container: BeautifulSoup, base_id: str, index: str, separator: str = " | ") -> Optional[str]:
        target_id = f"{base_id}${index}"
        el = container.find(id=target_id)
        if el:
            return el.get_text(separator=separator, strip=True)
        return None
    
    @staticmethod 
    def extract_status(container: BeautifulSoup, index: str) -> Optional[str]:
        target_id = f"{ParserService.STATUS_BASE_ID}${index}"
        status_container = container.find(id=target_id) or container.find(id=f"win0div{ParserService.STATUS_BASE_ID}${index}")
        if status_container:
            img = status_container.find('img')
            if img and 'alt' in img.attrs:
                return img['alt']
            return None 
    
    @staticmethod
    def time_parser(days_times_str: Optional[str]) -> list[Dict[str, str]]:
        bloques = []
        
        clean_str = days_times_str.split('|')[0].strip()
        entries = [e.strip() for e in clean_str.split(',')]
        
        for entry in entries:
            match = re.search(r"([A-Za-záéíóúÁÉÍÓÚ]+)\s+(\d{1,2}:\d{2}[AP]M)\s*-\s*(\d{1,2}:\d{2}[AP]M)", entry, re.IGNORECASE)
            
            if match:
                dia_str, hora_inicio_str, hora_fin_str = match.groups()
                dia_normalized = ParserService.DAY_MAPPING.get(dia_str.capitalize(), dia_str[0].upper())

                try:
                    h_inicio = datetime.strptime(hora_inicio_str.strip(), "%I:%M%p").strftime("%H:%M")
                    h_fin = datetime.strptime(hora_fin_str.strip(), "%I:%M%p").strftime("%H:%M")
                except ValueError:
                    h_inicio, h_fin = hora_inicio_str, hora_fin_str

                bloques.append({
                    "dia": dia_normalized,
                    "hora_inicio": h_inicio,
                    "hora_fin": h_fin
                })
                
        return bloques 
    @staticmethod
    def clean_whitespace(text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        cleaned = re.sub(r'\s+', ' ', text).strip()
        return cleaned if cleaned else None

    @staticmethod
    def clean_course_name(name: Optional[str]) -> Optional[str]:
        return ParserService.clean_whitespace(name)

    @staticmethod
    def clean_professor_name(professor: Optional[str]) -> Optional[str]:
        if not professor:
            return professor
        
        parts = [p.strip() for p in professor.split('|')]
        cleaned_parts = []
        for part in parts:
            cleaned_part = ParserService.clean_whitespace(part)
            if cleaned_part and cleaned_part not in cleaned_parts:
                cleaned_parts.append(cleaned_part)
                
        announcement_keywords = {"a anunciar", "por anunciar", "anunciar"}
        real_names = [p for p in cleaned_parts if p.lower() not in announcement_keywords]
        
        if real_names:
            return " / ".join(real_names)
        elif cleaned_parts:
            return "A Anunciar"
        return None

    @staticmethod
    def clean_salon_name(salon: Optional[str]) -> Optional[str]:
        if not salon:
            return salon
            
        parts = [p.strip() for p in salon.split('|')]
        cleaned_parts = []
        for part in parts:
            cleaned_part = ParserService.clean_whitespace(part)
            if cleaned_part and cleaned_part not in cleaned_parts:
                cleaned_parts.append(cleaned_part)
                
        no_salon_keywords = {"no requiere salón", "no requiere salon", "no salon"}
        real_rooms = [p for p in cleaned_parts if p.lower() not in no_salon_keywords]
        
        if real_rooms:
            return " / ".join(real_rooms)
        elif cleaned_parts:
            return cleaned_parts[0]
        return None

    @staticmethod
    def parse_class_row(gb: BeautifulSoup, idx: str, subject: str, number: str, course: Optional[str]) -> Dict[str, Any]:
        raw_materia = ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["class_number"], idx)
        raw_profesor = ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["instructor"], idx)
        raw_salon = ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["room"], idx)
        raw_status = ParserService.extract_status(gb, idx)

        result = {
            "codigo_materia": ParserService.clean_whitespace(raw_materia),
            "nombre_materia": ParserService.clean_course_name(course),
            "profesor": ParserService.clean_professor_name(raw_profesor),
            "creditos": None,
            "bloques": ParserService.time_parser(ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["days_times"], idx)),

            # Aditional information obtained 
            "Unidad_academica": ParserService.clean_whitespace(subject),
            "numero_unidad_academica": ParserService.clean_whitespace(number),
            "salon": ParserService.clean_salon_name(raw_salon),
            "estado": ParserService.clean_whitespace(raw_status)
        }
        return result 

    @staticmethod
    def parse_groupbox(gb: BeautifulSoup) -> list[Dict[str, Any]]:
        header = gb.find(class_=ParserService.HEADER_CLASS) 
        header_text = header.get_text(strip=True) if header else ""
        subject, number, course = ParserService.parse_header(header_text)

        classes = []
        class_elements = gb.find_all(id=ParserService.CLASS_NBR_PATTERN)

        for elem in class_elements:
            elem_id = elem.get('id')
            if not elem_id or '$' not in elem_id:
                continue
            idx = elem_id.split('$')[-1]
            class_data = ParserService.parse_class_row(gb, idx, subject, number, course)
            classes.append(class_data)

        return classes

    @staticmethod
    def parse_raw_data(raw_data: str) -> list[Dict[str, Any]]:
        soup = BeautifulSoup(raw_data, 'lxml')
        extracted_clases = []

        groupboxes = soup.find_all(id=ParserService.GROUPBOX_PATTERN)
        for gb in groupboxes:
            extracted_clases.extend(ParserService.parse_groupbox(gb))
        
        return extracted_clases