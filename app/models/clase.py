"""
Clase (Class Section) and BloqueHorario (Time Block) Models
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from enum import Enum


class DayOfWeek(str, Enum):
    """Days of the week"""
    MONDAY = "L"      # Lunes
    TUESDAY = "M"     # Martes
    WEDNESDAY = "W"   # Miércoles
    THURSDAY = "J"    # Jueves
    FRIDAY = "V"      # Viernes
    SATURDAY = "S"    # Sábado
    SUNDAY = "D"      # Domingo


class BloqueHorario(BaseModel):
    """
    A time block for a specific day
    """
    day: DayOfWeek = Field(..., description="Day of the week")
    start: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Start time HH:MM")
    end: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="End time HH:MM")
    
    @model_validator(mode='after')
    def validate_time_order(self) -> 'BloqueHorario':
        """Ensure end time is after start time"""
        start_minutes = self._time_to_minutes(self.start)
        end_minutes = self._time_to_minutes(self.end)
        if end_minutes <= start_minutes:
            raise ValueError('End time must be after start time')
        return self
    
    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """Convert HH:MM to minutes since midnight"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    def get_start_minutes(self) -> int:
        """Get start time in minutes since midnight"""
        return self._time_to_minutes(self.start)
    
    def get_end_minutes(self) -> int:
        """Get end time in minutes since midnight"""
        return self._time_to_minutes(self.end)
    
    def overlaps_with(self, other: 'BloqueHorario') -> bool:
        """
        Check if this block overlaps with another block
        
        Args:
            other: Another time block to compare
            
        Returns:
            True if blocks overlap on the same day
        """
        if self.day != other.day:
            return False
        
        self_start = self.get_start_minutes()
        self_end = self.get_end_minutes()
        other_start = other.get_start_minutes()
        other_end = other.get_end_minutes()
        
        # No overlap if one ends before the other starts
        return not (self_end <= other_start or other_end <= self_start)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'day': self.day.value,
            'start': self.start,
            'end': self.end
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BloqueHorario':
        """Create BloqueHorario from dictionary"""
        day = data['day']
        if isinstance(day, str):
            day = DayOfWeek(day)
        return cls(day=day, start=data['start'], end=data['end'])


class Clase(BaseModel):
    """
    A class section for a course
    """
    materia_code: str = Field(..., description="Course code this class belongs to")
    class_code: str = Field(..., min_length=1, max_length=10, description="Section identifier, e.g., 'A1'")
    schedule: list[BloqueHorario] = Field(default_factory=list, description="Time blocks for this class")
    professor: Optional[str] = Field(default=None, max_length=100, description="Professor name")
    location: Optional[str] = Field(default=None, max_length=50, description="Classroom location")
    credits: int = Field(default=0, ge=0, description="Credits for this course")
    
    @field_validator('materia_code')
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        """Normalize course code to uppercase"""
        return v.upper().strip()
    
    @field_validator('class_code')
    @classmethod
    def class_code_uppercase(cls, v: str) -> str:
        """Normalize class code to uppercase"""
        return v.upper().strip()
    
    def conflicts_with(self, other: 'Clase') -> bool:
        """
        Check if this class has time conflicts with another class
        
        Args:
            other: Another class to check conflicts with
            
        Returns:
            True if any time blocks overlap
        """
        for block in self.schedule:
            for other_block in other.schedule:
                if block.overlaps_with(other_block):
                    return True
        return False
    
    def conflicts_with_blocks(self, blocks: list[BloqueHorario]) -> bool:
        """
        Check if this class conflicts with a list of time blocks
        
        Args:
            blocks: List of blocked time slots
            
        Returns:
            True if any schedule block overlaps with blocked times
        """
        for block in self.schedule:
            for blocked in blocks:
                if block.overlaps_with(blocked):
                    return True
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'materia_code': self.materia_code,
            'class_code': self.class_code,
            'schedule': [b.to_dict() for b in self.schedule],
            'professor': self.professor,
            'location': self.location,
            'credits': self.credits
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Clase':
        """Create Clase from dictionary"""
        schedule = [BloqueHorario.from_dict(b) for b in data.get('schedule', [])]
        return cls(
            materia_code=data['materia_code'],
            class_code=data['class_code'],
            schedule=schedule,
            professor=data.get('professor'),
            location=data.get('location'),
            credits=data.get('credits', 0)
        )
