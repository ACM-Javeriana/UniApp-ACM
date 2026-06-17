"""
Parser Service
Service defined for parsing raw intranet data obtained from request of searching classes
"""
from datetime import datetime
from typing import Dict, Optional, Any

from soupsieve import match
from app.blueprints.pensum import index
from app.models.clase import Clase, BloqueHorario, DayOfWeek
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
import warnings
import re

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning) # Ingore warnings about parsing HTML as XML

class ParserService:
    """
    Service for parsing raw data class input
    and returning json serializable data for the API response.
    """

    # Constants to identify the codes used in the classes in the html
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
        """
        Function to parse the header of the groupbox and extract subject, catalog number and course name.
        """ 


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
        """
        Function to extract text from an element given a base id and index.
        """
        
        target_id = f"{base_id}${index}"
        el = container.find(id=target_id)
        if el:
            return el.get_text(separator=separator, strip=True)
        return None
    
    @staticmethod 
    def extract_status(container: BeautifulSoup, index: str) -> Optional[str]:
        """
        Function to extract the status from an element given a base id and index.
        """
        target_id = f"{ParserService.STATUS_BASE_ID}${index}"
        status_container = container.find(id=target_id) or container.find(id=f"win0div{ParserService.STATUS_BASE_ID}${index}")
        if status_container:
            img = status_container.find('img')
            if img and 'alt' in img.attrs:
                return img['alt']
            return None 
    
    @staticmethod
    def time_parser(days_times_str: Optional[str]) -> list[Dict[str, str]]:
        """
        Function to parse the days and times string and return a list of dictionaries with day, start time and end time.
        """

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
        """
        Function to parse a class row, returning a dictionary of the needed information for the API response. 
        """


        raw_materia = ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["class_number"], idx)
        raw_profesor = ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["instructor"], idx)
        raw_salon = ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["room"], idx)
        raw_status = ParserService.extract_status(gb, idx)

        result = {
            "codigo_materia": ParserService.clean_whitespace(raw_materia),
            "nombre_materia": ParserService.clean_course_name(course),
            "profesor": ParserService.clean_professor_name(raw_profesor),
            "creditos": 1,
            "bloques": ParserService.time_parser(ParserService.extract_element_text(gb, ParserService.FIELD_BASE_IDS["days_times"], idx)),

            # Aditional information obtained 
            "unidad_academica": ParserService.clean_whitespace(subject),
            "numero_unidad_academica": ParserService.clean_whitespace(number),
            "salon": ParserService.clean_salon_name(raw_salon),
            "estado": ParserService.clean_whitespace(raw_status)
        }
        return result 

    @staticmethod
    def parse_groupbox(gb: BeautifulSoup) -> list[Dict[str, Any]]:
        """
        Function to parse a groupbox and extract all the class information within it.
        """

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
    def obtain_subjects(classes: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Function to obtain unique subjects given the list of classes
        """
        unique_subjects = {}

        for cls in classes:
            nombre = cls.get("nombre_materia")

            if nombre and nombre not in unique_subjects:
                unique_subjects[nombre] = {
                    "nombre": nombre,
                    "codigo": cls.get(""),
                    "creditos": cls.get("creditos"),
                    "semestre": 1,
                    "prerrequisitos": [],
                    "correquisitos": [],
                    "estado": "pending",
                    "color": "#5091AF",
                    "tipo": 'basicas'
                }
                
        return list(unique_subjects.values())


    @staticmethod
    def parse_raw_data(raw_data: str) -> list[Dict[str, Any]]:
        """
        Function to parse the raw HTML data and returning a list of dictionaries with the classes information.
        """

        soup = BeautifulSoup(raw_data, 'lxml')
        extracted_clases = []

        groupboxes = soup.find_all(id=ParserService.GROUPBOX_PATTERN)
        for gb in groupboxes:
            results = ParserService.parse_groupbox(gb)
            mandatory_fields = {"codigo_materia", "nombre_materia", "bloques"}
            for res in results:
                if all(field in res and res[field] for field in mandatory_fields):
                    extracted_clases.extend(results)
        
        result_dict = {
            "clases": extracted_clases,
            "materias": ParserService.obtain_subjects(extracted_clases)
        }

        return result_dict