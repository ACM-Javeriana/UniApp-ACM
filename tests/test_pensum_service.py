import pytest
from app.models.materia import Materia, MateriaStatus, Pensum
from app.services.pensum_service import PensumService


class TestValidatePensumStructure:
    def test_valid_pensum(self, pensum_con_prereqs):
        result = PensumService.validate_pensum_structure(pensum_con_prereqs)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_prerequisite(self):
        m = Materia(code="B", name="B", credits=3, semester=2, prerequisites=["NONEXISTENT"])
        result = PensumService.validate_pensum_structure(Pensum(materias=[m]))
        assert result["valid"] is False
        assert any("NONEXISTENT" in e for e in result["errors"])

    def test_prerequisite_in_same_semester(self):
        m1 = Materia(code="A", name="A", credits=3, semester=1)
        m2 = Materia(code="B", name="B", credits=3, semester=1, prerequisites=["A"])
        result = PensumService.validate_pensum_structure(Pensum(materias=[m1, m2]))
        assert result["valid"] is False
        assert any("earlier semester" in e for e in result["errors"])

    def test_circular_dependency_detected(self):
        m1 = Materia(code="A", name="A", credits=3, semester=1, prerequisites=["B"])
        m2 = Materia(code="B", name="B", credits=3, semester=2, prerequisites=["A"])
        result = PensumService.validate_pensum_structure(Pensum(materias=[m1, m2]))
        assert result["valid"] is False
        assert any("Circular dependency" in e for e in result["errors"])


class TestDetectCircularDependencies:
    def test_no_cycle(self, pensum_con_prereqs):
        assert PensumService.detect_circular_dependencies(pensum_con_prereqs) is None

    def test_direct_cycle(self):
        m1 = Materia(code="A", name="A", credits=3, semester=1, prerequisites=["B"])
        m2 = Materia(code="B", name="B", credits=3, semester=2, prerequisites=["A"])
        cycle = PensumService.detect_circular_dependencies(Pensum(materias=[m1, m2]))
        assert cycle is not None
        assert set(cycle).issubset({"A", "B"})

    def test_chain_without_cycle(self):
        m1 = Materia(code="A", name="A", credits=3, semester=1)
        m2 = Materia(code="B", name="B", credits=3, semester=2, prerequisites=["A"])
        m3 = Materia(code="C", name="C", credits=3, semester=3, prerequisites=["B"])
        assert PensumService.detect_circular_dependencies(Pensum(materias=[m1, m2, m3])) is None

    def test_empty_pensum(self):
        assert PensumService.detect_circular_dependencies(Pensum()) is None


class TestCanMoveToSemester:
    def test_valid_move(self, m_fis1, pensum_con_prereqs):
        # FIS1 no tiene prereqs ni dependientes; mover al semestre 3 es válido
        result = PensumService.can_move_to_semester(m_fis1, 3, pensum_con_prereqs)
        assert result["can_move"] is True

    def test_blocked_by_prerequisite(self, m_calc2, pensum_con_prereqs):
        # CALC2 tiene CALC1 (sem 1) como prereq; no puede ir a sem 1
        result = PensumService.can_move_to_semester(m_calc2, 1, pensum_con_prereqs)
        assert result["can_move"] is False
        assert len(result["reasons"]) > 0

    def test_blocked_by_dependent(self, m_calc1, pensum_con_prereqs):
        # CALC1 es prereq de CALC2 (sem 2); no puede moverse al sem 2
        result = PensumService.can_move_to_semester(m_calc1, 2, pensum_con_prereqs)
        assert result["can_move"] is False


class TestSimulateCourseLoss:
    def test_course_not_found(self, pensum_simple):
        result = PensumService.simulate_course_loss("NONEXISTENT", pensum_simple)
        assert "error" in result

    def test_no_dependents(self, m_fis1):
        result = PensumService.simulate_course_loss("FIS1", Pensum(materias=[m_fis1]))
        assert result["directly_blocked"] == []
        assert result["indirectly_blocked"] == []
        assert result["total_blocked_courses"] == 0

    def test_direct_dependents(self, pensum_con_prereqs):
        # Perder CALC1 bloquea directamente a CALC2
        result = PensumService.simulate_course_loss("CALC1", pensum_con_prereqs)
        blocked = [c["code"] for c in result["directly_blocked"]]
        assert "CALC2" in blocked

    def test_chain_propagation(self):
        # A → B → C: perder A bloquea B directo y C indirecto
        m1 = Materia(code="A", name="A", credits=3, semester=1)
        m2 = Materia(code="B", name="B", credits=3, semester=2, prerequisites=["A"])
        m3 = Materia(code="C", name="C", credits=3, semester=3, prerequisites=["B"])
        pensum = Pensum(materias=[m1, m2, m3])
        result = PensumService.simulate_course_loss("A", pensum)
        assert [c["code"] for c in result["directly_blocked"]] == ["B"]
        assert [c["code"] for c in result["indirectly_blocked"]] == ["C"]
        assert result["total_blocked_courses"] == 2
        assert result["total_blocked_credits"] == 6

    def test_code_normalized_to_uppercase(self, m_fis1):
        # La función acepta minúsculas y las normaliza
        result = PensumService.simulate_course_loss("fis1", Pensum(materias=[m_fis1]))
        assert "error" not in result


class TestDeleteMateria:
    def test_success(self, m_fis1):
        pensum = Pensum(materias=[m_fis1])
        result = PensumService.delete_materia("FIS1", pensum)
        assert result.get("success") is True
        assert pensum.get_materia("FIS1") is None
        assert pensum.total_credits == 0

    def test_not_found(self, pensum_simple):
        result = PensumService.delete_materia("NONEXISTENT", pensum_simple)
        assert "error" in result

    def test_blocked_by_dependents(self, pensum_con_prereqs):
        # CALC1 es prereq de CALC2; no se puede borrar
        result = PensumService.delete_materia("CALC1", pensum_con_prereqs)
        assert "error" in result
        assert "dependents" in result
        assert "CALC2" in result["dependents"]


class TestCanAddToSemester:
    def test_within_limit(self, pensum_simple):
        # CALC1 (3cr) en sem 1; agregar 10cr → 13cr ≤ 21
        result = PensumService.can_add_to_semester(10, 1, pensum_simple)
        assert result["allowed"] is True
        assert result["new_total"] == 13

    def test_exceeds_limit(self, pensum_simple):
        # CALC1 (3cr) en sem 1; agregar 20cr → 23cr > 21
        result = PensumService.can_add_to_semester(20, 1, pensum_simple)
        assert result["allowed"] is False
        assert result["excess"] == 2

    def test_exactly_at_limit(self, pensum_simple):
        # CALC1 (3cr) en sem 1; agregar 18cr → 21cr = límite exacto
        result = PensumService.can_add_to_semester(18, 1, pensum_simple)
        assert result["allowed"] is True

    def test_custom_max_credits(self, pensum_simple):
        result = PensumService.can_add_to_semester(10, 1, pensum_simple, max_credits=10)
        assert result["allowed"] is False
        assert result["excess"] == 3
