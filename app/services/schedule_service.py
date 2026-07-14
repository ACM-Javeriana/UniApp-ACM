"""
Schedule Service
Business logic for schedule generation, conflict detection, and optimization
"""
from typing import Optional
from itertools import product
import uuid
from app.models.clase import Clase, BloqueHorario
from app.models.horario import Franja, FranjaStatus, HorarioCombination
from app.models.materia import Pensum


class ScheduleService:
    """
    Service for schedule operations including:
    - Time conflict detection
    - Schedule combination generation
    - Optimization and filtering
    """
    
    # Warning threshold for number of combinations
    COMBINATION_WARNING_THRESHOLD = 1000
    
    @staticmethod
    def check_conflicts(clases: list[Clase]) -> list[dict]:
        """
        Check for time conflicts between classes
        
        Args:
            clases: List of classes to check
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        for i, clase1 in enumerate(clases):
            for clase2 in clases[i + 1:]:
                if clase1.conflicts_with(clase2):
                    # Find specific overlapping blocks
                    for b1 in clase1.schedule:
                        for b2 in clase2.schedule:
                            if b1.overlaps_with(b2):
                                conflicts.append({
                                    'class1': {
                                        'materia': clase1.materia_code,
                                        'section': clase1.class_code,
                                        'day': b1.day.value,
                                        'time': f"{b1.start}-{b1.end}"
                                    },
                                    'class2': {
                                        'materia': clase2.materia_code,
                                        'section': clase2.class_code,
                                        'day': b2.day.value,
                                        'time': f"{b2.start}-{b2.end}"
                                    }
                                })
        
        return conflicts
    
    @staticmethod
    def check_franja_conflicts(
        clase: Clase,
        franjas: list[Franja]
    ) -> list[dict]:
        """
        Check if a class conflicts with blocked time slots
        
        Args:
            clase: Class to check
            franjas: List of time slot preferences
            
        Returns:
            List of conflicts with blocked slots
        """
        blocked_franjas = [f for f in franjas if f.status == FranjaStatus.BLOCKED]
        conflicts = []
        
        for block in clase.schedule:
            for franja in blocked_franjas:
                franja_block = franja.to_bloque()
                if block.overlaps_with(franja_block):
                    conflicts.append({
                        'class': {
                            'materia': clase.materia_code,
                            'section': clase.class_code
                        },
                        'blocked_slot': {
                            'day': franja.day.value,
                            'time': f"{franja.start}-{franja.end}"
                        }
                    })
        
        return conflicts
    
    @staticmethod
    def generate_combinations(
        clases_by_materia: dict[str, list[Clase]],
        franjas: list[Franja] = None,
        max_combinations: int = None
    ) -> dict:
        """
        Generate all valid schedule combinations
        
        Args:
            clases_by_materia: Dict mapping course codes to their class sections
            franjas: Time slot preferences
            max_combinations: Maximum combinations to generate (None = unlimited)
            
        Returns:
            Dict with combinations list and metadata
        """
        if franjas is None:
            franjas = []
        
        # Get blocked time slots
        blocked_slots = [f.to_bloque() for f in franjas if f.status == FranjaStatus.BLOCKED]
        
        # Get list of courses and their options
        courses = list(clases_by_materia.keys())
        class_options = [clases_by_materia[course] for course in courses]
        
        # Calculate total possible combinations
        total_possible = 1
        for options in class_options:
            total_possible *= len(options) if options else 1
        
        # Generate warning if too many combinations
        warning = None
        if total_possible > ScheduleService.COMBINATION_WARNING_THRESHOLD:
            warning = f"Large number of possible combinations ({total_possible}). Generation may take a while."
        
        valid_combinations = []
        checked = 0
        
        # Generate combinations using itertools.product
        for combo in product(*class_options):
            checked += 1
            
            # Check if we've hit the limit
            if max_combinations and len(valid_combinations) >= max_combinations:
                break
            
            # Check for conflicts within the combination
            combo_list = list(combo)
            has_internal_conflict = False
            
            for i, clase1 in enumerate(combo_list):
                for clase2 in combo_list[i + 1:]:
                    if clase1.conflicts_with(clase2):
                        has_internal_conflict = True
                        break
                if has_internal_conflict:
                    break
            
            if has_internal_conflict:
                continue
            
            # Check for conflicts with blocked slots
            has_blocked_conflict = False
            for clase in combo_list:
                if clase.conflicts_with_blocks(blocked_slots):
                    has_blocked_conflict = True
                    break
            
            if has_blocked_conflict:
                continue
            
            # Valid combination found
            combination = HorarioCombination(
                id=str(uuid.uuid4())[:8],
                clases=combo_list,
                total_credits=sum(clase.credits for clase in combo_list)
            )
            combination.calculate_metrics(franjas)
            valid_combinations.append(combination)
        
        return {
            'combinations': valid_combinations,
            'total_generated': len(valid_combinations),
            'total_possible': total_possible,
            'total_checked': checked,
            'warning': warning
        }
    
    @staticmethod
    def filter_combinations(
        combinations: list[HorarioCombination],
        filters: dict
    ) -> list[HorarioCombination]:
        """
        Filter and sort combinations based on preferences
        
        Args:
            combinations: List of valid combinations
            filters: Filter options dict with keys:
                - min_free_days: Minimum number of free days
                - max_gaps: Maximum number of gaps between classes
                - max_gap_minutes: Maximum total gap time
                - earliest_start: Earliest acceptable start time (HH:MM)
                - latest_end: Latest acceptable end time (HH:MM)
                - sort_by: Field to sort by (free_days, gaps_count, gaps_minutes, etc.)
                - sort_order: 'asc' or 'desc'
            
        Returns:
            Filtered and sorted list of combinations
        """
        filtered = combinations.copy()
        
        # Apply filters
        if 'min_free_days' in filters and filters['min_free_days'] is not None:
            filtered = [c for c in filtered if c.free_days >= filters['min_free_days']]
        
        if 'max_gaps' in filters and filters['max_gaps'] is not None:
            filtered = [c for c in filtered if c.gaps_count <= filters['max_gaps']]
        
        if 'max_gap_minutes' in filters and filters['max_gap_minutes'] is not None:
            filtered = [c for c in filtered if c.gaps_minutes <= filters['max_gap_minutes']]
        
        if 'earliest_start' in filters and filters['earliest_start']:
            min_start = BloqueHorario._time_to_minutes(filters['earliest_start'])
            filtered = [
                c for c in filtered 
                if BloqueHorario._time_to_minutes(c.earliest_start) >= min_start
            ]
        
        if 'latest_end' in filters and filters['latest_end']:
            max_end = BloqueHorario._time_to_minutes(filters['latest_end'])
            filtered = [
                c for c in filtered
                if BloqueHorario._time_to_minutes(c.latest_end) <= max_end
            ]
        
        # Sort
        sort_by = filters.get('sort_by', 'free_days')
        sort_order = filters.get('sort_order', 'desc')
        reverse = sort_order == 'desc'
        
        sort_key_map = {
            'free_days': lambda c: c.free_days,
            'gaps_count': lambda c: -c.gaps_count if reverse else c.gaps_count,
            'gaps_minutes': lambda c: -c.gaps_minutes if reverse else c.gaps_minutes,
            'preferred_slots': lambda c: c.preferred_slots_used,
            'earliest_start': lambda c: BloqueHorario._time_to_minutes(c.earliest_start),
            'latest_end': lambda c: BloqueHorario._time_to_minutes(c.latest_end)
        }
        
        if sort_by in sort_key_map:
            # For gaps, we want ascending by default (fewer is better)
            if sort_by in ['gaps_count', 'gaps_minutes']:
                reverse = sort_order == 'asc'  # Invert for gaps
            filtered.sort(key=sort_key_map[sort_by], reverse=reverse)
        
        return filtered
    
    @staticmethod
    def get_optimization_presets() -> list[dict]:
        """
        Get predefined filter presets for common preferences
        
        Returns:
            List of preset configurations
        """
        return [
            {
                'id': 'max_free_days',
                'name': 'Más días libres',
                'description': 'Prioriza horarios con más días sin clases',
                'filters': {
                    'sort_by': 'free_days',
                    'sort_order': 'desc'
                }
            },
            {
                'id': 'min_gaps',
                'name': 'Menos huecos',
                'description': 'Prioriza horarios con menos tiempo muerto entre clases',
                'filters': {
                    'sort_by': 'gaps_count',
                    'sort_order': 'asc'
                }
            },
            {
                'id': 'early_bird',
                'name': 'Madrugador',
                'description': 'Prioriza horarios que empiecen temprano',
                'filters': {
                    'sort_by': 'earliest_start',
                    'sort_order': 'asc',
                    'latest_end': '14:00'
                }
            },
            {
                'id': 'night_owl',
                'name': 'Tarde',
                'description': 'Prioriza horarios que empiecen tarde',
                'filters': {
                    'sort_by': 'earliest_start',
                    'sort_order': 'desc',
                    'earliest_start': '10:00'
                }
            },
            {
                'id': 'compact',
                'name': 'Compacto',
                'description': 'Minimiza la duración total del día',
                'filters': {
                    'sort_by': 'gaps_minutes',
                    'sort_order': 'asc'
                }
            },
            {
                'id': 'preferred_times',
                'name': 'Horarios preferidos',
                'description': 'Prioriza horarios en tus franjas preferidas',
                'filters': {
                    'sort_by': 'preferred_slots',
                    'sort_order': 'desc'
                }
            }
        ]
    
    @staticmethod
    def get_schedule_grid(combination: HorarioCombination) -> dict:
        """
        Convert a schedule combination to a grid format for display
        
        Args:
            combination: Schedule combination
            
        Returns:
            Dict with grid data organized by day and time
        """
        days_order = ['L', 'M', 'W', 'J', 'V', 'S']
        day_names = {
            'L': 'Lunes',
            'M': 'Martes', 
            'W': 'Miércoles',
            'J': 'Jueves',
            'V': 'Viernes',
            'S': 'Sábado'
        }
        
        # Generate time slots (30 min intervals from 6:00 to 22:00)
        time_slots = []
        for hour in range(6, 22):
            time_slots.append(f"{hour:02d}:00")
            time_slots.append(f"{hour:02d}:30")
        
        # Initialize grid
        grid = {day: {time: None for time in time_slots} for day in days_order}
        
        # Populate grid with classes
        for clase in combination.clases:
            for block in clase.schedule:
                day = block.day.value
                if day not in grid:
                    continue
                
                start_minutes = block.get_start_minutes()
                end_minutes = block.get_end_minutes()
                
                # Mark all time slots covered by this block
                for time in time_slots:
                    time_minutes = BloqueHorario._time_to_minutes(time)
                    if start_minutes <= time_minutes < end_minutes:
                        grid[day][time] = {
                            'materia_code': clase.materia_code,
                            'class_code': clase.class_code,
                            'professor': clase.professor,
                            'location': clase.location,
                            'is_start': time_minutes == start_minutes,
                            'start': block.start,
                            'end': block.end
                        }
        
        return {
            'days': days_order,
            'day_names': day_names,
            'time_slots': time_slots,
            'grid': grid,
            'metrics': {
                'free_days': combination.free_days,
                'gaps_count': combination.gaps_count,
                'gaps_minutes': combination.gaps_minutes,
                'earliest_start': combination.earliest_start,
                'latest_end': combination.latest_end
            }
        }
    
    @staticmethod
    def validate_class_data(clase_data: dict) -> dict:
        """
        Validate class data before creation
        
        Args:
            clase_data: Dict with class data
            
        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []
        
        if not clase_data.get('materia_code'):
            errors.append('Course code is required')
        
        if not clase_data.get('class_code'):
            errors.append('Class/Section code is required')
        
        schedule = clase_data.get('schedule', [])
        if not schedule:
            errors.append('At least one time block is required')
        
        # Validate each time block
        for i, block in enumerate(schedule):
            if not block.get('day'):
                errors.append(f'Block {i+1}: Day is required')
            if not block.get('start'):
                errors.append(f'Block {i+1}: Start time is required')
            if not block.get('end'):
                errors.append(f'Block {i+1}: End time is required')
            
            # Validate time format and order
            try:
                if block.get('start') and block.get('end'):
                    start = BloqueHorario._time_to_minutes(block['start'])
                    end = BloqueHorario._time_to_minutes(block['end'])
                    if end <= start:
                        errors.append(f'Block {i+1}: End time must be after start time')
            except:
                errors.append(f'Block {i+1}: Invalid time format')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
