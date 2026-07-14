"""
Pensum Service
Business logic for pensum management, prerequisites validation, and course simulation
"""
from typing import Optional
from collections import defaultdict, deque
from app.models.materia import Materia, MateriaStatus, Pensum


class PensumService:
    """
    Service for pensum operations including:
    - CRUD operations
    - Prerequisite/corequisite validation
    - Course loss simulation
    - Move between semesters
    """
    
    @staticmethod
    def validate_pensum_structure(pensum: Pensum) -> dict:
        """
        Validate the entire pensum structure for consistency
        
        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []
        materia_codes = {m.code for m in pensum.materias}
        
        for materia in pensum.materias:
            # Check prerequisites exist
            for prereq in materia.prerequisites:
                if prereq not in materia_codes:
                    errors.append(f"{materia.code}: Prerequisite '{prereq}' not found in pensum")
            
            # Check corequisites exist
            for coreq in materia.corequisites:
                if coreq not in materia_codes:
                    errors.append(f"{materia.code}: Corequisite '{coreq}' not found in pensum")
            
            # Check prerequisite semester order
            for prereq in materia.prerequisites:
                prereq_materia = pensum.get_materia(prereq)
                if prereq_materia and prereq_materia.semester >= materia.semester:
                    errors.append(
                        f"{materia.code}: Prerequisite '{prereq}' must be in an earlier semester "
                        f"(prereq in sem {prereq_materia.semester}, course in sem {materia.semester})"
                    )
        
        # Check for circular dependencies
        cycle = PensumService.detect_circular_dependencies(pensum)
        if cycle:
            errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def detect_circular_dependencies(pensum: Pensum) -> Optional[list[str]]:
        """
        Detect circular dependencies using topological sort (Kahn's algorithm)
        
        Returns:
            List of codes forming a cycle, or None if no cycle
        """
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        codes = {m.code for m in pensum.materias}
        
        for materia in pensum.materias:
            in_degree[materia.code] = in_degree.get(materia.code, 0)
            for prereq in materia.prerequisites + materia.corequisites:
                if prereq in codes:
                    graph[prereq].append(materia.code)
                    in_degree[materia.code] += 1
        
        # Kahn's algorithm
        queue = deque([code for code in codes if in_degree[code] == 0])
        sorted_count = 0
        
        while queue:
            current = queue.popleft()
            sorted_count += 1
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If we couldn't sort all nodes, there's a cycle
        if sorted_count != len(codes):
            # Find a node in the cycle
            remaining = [code for code in codes if in_degree[code] > 0]
            if remaining:
                return remaining[:5]  # Return first few nodes in cycle
        
        return None
    
    @staticmethod
    def can_move_to_semester(
        materia: Materia,
        target_semester: int,
        pensum: Pensum
    ) -> dict:
        """
        Check if a course can be moved to a different semester
        
        Args:
            materia: The course to move
            target_semester: Target semester number
            pensum: Current pensum
            
        Returns:
            Dict with 'can_move' bool and 'reasons' list
        """
        reasons = []
        
        # Check prerequisites - they must be in earlier semesters
        for prereq_code in materia.prerequisites:
            prereq = pensum.get_materia(prereq_code)
            if prereq and prereq.semester >= target_semester:
                reasons.append(
                    f"Prerequisite '{prereq.name}' ({prereq.code}) is in semester {prereq.semester}, "
                    f"which is not before the target semester {target_semester}"
                )
        
        # Check dependents - courses that depend on this one
        for other in pensum.materias:
            if materia.code in other.prerequisites:
                if other.semester <= target_semester:
                    reasons.append(
                        f"'{other.name}' ({other.code}) in semester {other.semester} "
                        f"requires this course as prerequisite"
                    )
            
            # Check corequisites
            if materia.code in other.corequisites:
                if other.semester < target_semester:
                    reasons.append(
                        f"'{other.name}' ({other.code}) in semester {other.semester} "
                        f"requires this course as corequisite"
                    )
        
        return {
            'can_move': len(reasons) == 0,
            'reasons': reasons
        }
    
    @staticmethod
    def simulate_course_loss(
        materia_code: str,
        pensum: Pensum
    ) -> dict:
        """
        Simulate losing/failing a course and show impact on dependent courses
        
        Args:
            materia_code: Code of the course being "lost"
            pensum: Current pensum
            
        Returns:
            Dict with affected courses grouped by impact type
        """
        materia_code = materia_code.upper()
        materia = pensum.get_materia(materia_code)
        
        if not materia:
            return {'error': f"Course '{materia_code}' not found"}
        
        # Build reverse dependency graph
        prereq_dependents = defaultdict(list)  # courses that need this as prerequisite
        coreq_dependents = defaultdict(list)   # courses that need this as corequisite
        
        for m in pensum.materias:
            for prereq in m.prerequisites:
                prereq_dependents[prereq].append(m.code)
            for coreq in m.corequisites:
                coreq_dependents[coreq].append(m.code)
        
        # BFS to find all affected courses
        directly_blocked = []      # Cannot take without this course
        indirectly_blocked = []    # Blocked due to chain effect
        coreq_affected = []        # Affected corequisites
        
        # First level: direct dependents
        visited = {materia_code}
        queue = deque()
        
        for dep in prereq_dependents[materia_code]:
            if dep not in visited:
                directly_blocked.append(dep)
                visited.add(dep)
                queue.append(dep)
        
        for dep in coreq_dependents[materia_code]:
            if dep not in visited:
                coreq_affected.append(dep)
                visited.add(dep)
        
        # BFS for indirect effects
        while queue:
            current = queue.popleft()
            
            for dep in prereq_dependents[current]:
                if dep not in visited:
                    indirectly_blocked.append(dep)
                    visited.add(dep)
                    queue.append(dep)
        
        # Get full materia info for each affected course
        def get_materia_info(codes):
            result = []
            for code in codes:
                m = pensum.get_materia(code)
                if m:
                    result.append({
                        'code': m.code,
                        'name': m.name,
                        'semester': m.semester,
                        'credits': m.credits
                    })
            return sorted(result, key=lambda x: (x['semester'], x['code']))
        
        total_blocked_credits = sum(
            pensum.get_materia(c).credits 
            for c in directly_blocked + indirectly_blocked 
            if pensum.get_materia(c)
        )
        
        return {
            'lost_course': {
                'code': materia.code,
                'name': materia.name,
                'semester': materia.semester,
                'credits': materia.credits
            },
            'directly_blocked': get_materia_info(directly_blocked),
            'indirectly_blocked': get_materia_info(indirectly_blocked),
            'corequisite_affected': get_materia_info(coreq_affected),
            'total_blocked_courses': len(directly_blocked) + len(indirectly_blocked),
            'total_blocked_credits': total_blocked_credits
        }
    
    @staticmethod
    def get_available_courses(
        semester: int,
        pensum: Pensum,
        passed_courses: set[str] = None,
        enrolled_courses: set[str] = None
    ) -> list[Materia]:
        """
        Get courses that can be taken in a semester based on prerequisites
        
        Args:
            semester: Target semester
            pensum: Current pensum
            passed_courses: Set of passed course codes
            enrolled_courses: Set of courses enrolled this semester
            
        Returns:
            List of available courses
        """
        if passed_courses is None:
            passed_courses = set()
        if enrolled_courses is None:
            enrolled_courses = set()
        
        available = []
        
        for materia in pensum.materias:
            if materia.semester <= semester and materia.status == MateriaStatus.PENDING:
                if materia.is_available(passed_courses, enrolled_courses):
                    available.append(materia)
        
        return available
    
    @staticmethod
    def update_course_statuses(pensum: Pensum) -> Pensum:
        """
        Update course statuses based on prerequisites fulfillment
        Marks courses as BLOCKED if prerequisites not met
        
        Args:
            pensum: Pensum to update
            
        Returns:
            Updated pensum
        """
        # Get passed courses
        passed = {m.code for m in pensum.materias if m.status == MateriaStatus.PASSED}
        enrolled = {m.code for m in pensum.materias if m.status == MateriaStatus.ENROLLED}
        
        for materia in pensum.materias:
            if materia.status in [MateriaStatus.PENDING, MateriaStatus.BLOCKED]:
                if materia.is_available(passed, enrolled):
                    if materia.status == MateriaStatus.BLOCKED:
                        materia.status = MateriaStatus.PENDING
                else:
                    materia.status = MateriaStatus.BLOCKED
        
        return pensum
    
    @staticmethod
    def get_semester_credits(semester: int, pensum: Pensum) -> int:
        """Get total credits for a semester"""
        return sum(
            m.credits for m in pensum.materias 
            if m.semester == semester
        )
    
    @staticmethod
    def can_add_to_semester(
        credits_to_add: int,
        semester: int,
        pensum: Pensum,
        max_credits: int = 24
    ) -> dict:
        """
        Check if adding credits to a semester is allowed
        
        Returns:
            Dict with 'allowed' bool and current/new totals
        """
        current = PensumService.get_semester_credits(semester, pensum)
        new_total = current + credits_to_add
        
        return {
            'allowed': new_total <= max_credits,
            'current_credits': current,
            'new_total': new_total,
            'max_credits': max_credits,
            'excess': max(0, new_total - max_credits)
        }
    
    @staticmethod
    def create_materia(data: dict, pensum: Pensum) -> dict:
        """
        Create a new course in the pensum
        
        Args:
            data: Course data dict
            pensum: Current pensum
            
        Returns:
            Dict with 'success' or 'error'
        """
        try:
            # Check for duplicate code
            if pensum.get_materia(data.get('code', '')):
                return {'error': f"Course with code '{data['code']}' already exists"}
            
            # Create materia
            materia = Materia(**data)
            
            # Validate prerequisites exist
            for prereq in materia.prerequisites:
                if not pensum.get_materia(prereq):
                    return {'error': f"Prerequisite '{prereq}' not found in pensum"}
            
            # Validate corequisites exist
            for coreq in materia.corequisites:
                if not pensum.get_materia(coreq):
                    return {'error': f"Corequisite '{coreq}' not found in pensum"}
            
            pensum.materias.append(materia)
            pensum.total_credits = sum(m.credits for m in pensum.materias)
            
            return {'success': True, 'materia': materia.to_dict()}
        
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def update_materia(code: str, data: dict, pensum: Pensum) -> dict:
        """
        Update an existing course
        
        Args:
            code: Course code to update
            data: New course data
            pensum: Current pensum
            
        Returns:
            Dict with 'success' or 'error'
        """
        materia = pensum.get_materia(code)
        if not materia:
            return {'error': f"Course '{code}' not found"}
        
        try:
            # Update fields
            for key, value in data.items():
                if hasattr(materia, key):
                    setattr(materia, key, value)
            
            # Revalidate
            validation = PensumService.validate_pensum_structure(pensum)
            if not validation['valid']:
                return {'error': 'Update would create invalid pensum', 'details': validation['errors']}
            
            pensum.total_credits = sum(m.credits for m in pensum.materias)
            
            return {'success': True, 'materia': materia.to_dict()}
        
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def delete_materia(code: str, pensum: Pensum) -> dict:
        """
        Delete a course from the pensum
        
        Args:
            code: Course code to delete
            pensum: Current pensum
            
        Returns:
            Dict with 'success' or 'error'
        """
        code = code.upper()
        materia = pensum.get_materia(code)
        
        if not materia:
            return {'error': f"Course '{code}' not found"}
        
        # Check if other courses depend on this one
        dependents = []
        for m in pensum.materias:
            if code in m.prerequisites or code in m.corequisites:
                dependents.append(m.code)
        
        if dependents:
            return {
                'error': f"Cannot delete: course is a prerequisite/corequisite for {', '.join(dependents)}",
                'dependents': dependents
            }
        
        pensum.materias = [m for m in pensum.materias if m.code != code]
        pensum.total_credits = sum(m.credits for m in pensum.materias)
        
        return {'success': True, 'deleted': code}
