"""
Configuracion (Settings) and Calificacion (Grade) Models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Calificacion(BaseModel):
    """
    A grade entry for a specific evaluation
    """
    id: str = Field(..., description="Unique identifier")
    materia_code: str = Field(..., description="Course code")
    nombre: str = Field(..., min_length=1, max_length=100, description="Name of the evaluation")
    nota: float = Field(..., ge=0.0, le=5.0, description="Grade obtained (0-5 scale)")
    porcentaje: float = Field(..., ge=0.0, le=100.0, description="Weight percentage")
    fecha: str = Field(..., description="Date of the evaluation (ISO format)")
    is_simulation: bool = Field(default=False, description="Whether this is a simulated grade")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'materia_code': self.materia_code,
            'nombre': self.nombre,
            'nota': self.nota,
            'porcentaje': self.porcentaje,
            'fecha': self.fecha,
            'is_simulation': self.is_simulation
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Calificacion':
        """Create Calificacion from dictionary"""
        return cls(**data)


class GradeHistory(BaseModel):
    """
    Historical grade record for a course
    """
    materia_code: str = Field(..., description="Course code")
    semester_taken: int = Field(..., ge=1, description="Semester when the course was taken")
    final_grade: float = Field(..., ge=0.0, le=5.0, description="Final grade")
    status: str = Field(..., description="passed, failed, dropped")
    date_recorded: str = Field(..., description="Date recorded (ISO format)")
    attempt_number: int = Field(default=1, ge=1, description="Which attempt this was")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'materia_code': self.materia_code,
            'semester_taken': self.semester_taken,
            'final_grade': self.final_grade,
            'status': self.status,
            'date_recorded': self.date_recorded,
            'attempt_number': self.attempt_number
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GradeHistory':
        """Create GradeHistory from dictionary"""
        return cls(**data)


class Configuracion(BaseModel):
    """
    User configuration and preferences
    """
    # Credit limits
    max_credits_per_semester: int = Field(default=24, ge=1, le=30, description="Maximum credits per semester")
    
    # GPA settings
    gpa_alert_threshold: float = Field(default=3.0, ge=0.0, le=5.0, description="Alert if GPA falls below this")
    gpa_scale: float = Field(default=5.0, ge=4.0, le=5.0, description="GPA scale (4.0 or 5.0)")
    passing_grade: float = Field(default=3.0, ge=0.0, le=5.0, description="Minimum grade to pass")
    
    # Schedule preferences
    preferred_start_time: str = Field(default="07:00", pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    preferred_end_time: str = Field(default="18:00", pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    avoid_saturday: bool = Field(default=True, description="Try to avoid Saturday classes")
    
    # Current semester tracking
    current_semester: int = Field(default=1, ge=1, le=15, description="Current semester number")
    current_period: str = Field(default="2025-1", description="Current academic period (e.g., 2025-1)")
    
    # UI preferences
    theme: str = Field(default="light", description="UI theme: light or dark")
    accent_color: str = Field(default="#5091AF", pattern=r'^#[0-9A-Fa-f]{6}$')
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'max_credits_per_semester': self.max_credits_per_semester,
            'gpa_alert_threshold': self.gpa_alert_threshold,
            'gpa_scale': self.gpa_scale,
            'passing_grade': self.passing_grade,
            'preferred_start_time': self.preferred_start_time,
            'preferred_end_time': self.preferred_end_time,
            'avoid_saturday': self.avoid_saturday,
            'current_semester': self.current_semester,
            'current_period': self.current_period,
            'theme': self.theme,
            'accent_color': self.accent_color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Configuracion':
        """Create Configuracion from dictionary"""
        return cls(**data)
