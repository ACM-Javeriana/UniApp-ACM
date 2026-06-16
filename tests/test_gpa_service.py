import pytest
from app.models.materia import Materia, MateriaStatus, Pensum
from app.models.configuracion import Calificacion, Configuracion
from app.services.gpa_service import GPAService


def make_cal(nota, porcentaje, is_simulation=False):
    return Calificacion(
        id="test-id",
        materia_code="CALC1",
        nombre="Parcial",
        nota=nota,
        porcentaje=porcentaje,
        fecha="2025-01-01",
        is_simulation=is_simulation,
    )


class TestCalculateCourseGrade:
    def test_empty_returns_none(self):
        assert GPAService.calculate_course_grade([]) is None

    def test_all_simulation_returns_none(self):
        assert GPAService.calculate_course_grade([make_cal(4.0, 100, is_simulation=True)]) is None

    def test_single_full_weight(self):
        assert GPAService.calculate_course_grade([make_cal(3.5, 100)]) == 3.5

    def test_weighted_average(self):
        # 30%@4.0 + 70%@3.0 = (120+210)/100 = 3.3
        result = GPAService.calculate_course_grade([make_cal(4.0, 30), make_cal(3.0, 70)])
        assert result == pytest.approx(3.3)

    def test_simulation_grades_excluded(self):
        # Solo el 50% real cuenta; resultado = 4.0*50/50 = 4.0
        cals = [make_cal(4.0, 50), make_cal(0.0, 50, is_simulation=True)]
        assert GPAService.calculate_course_grade(cals) == 4.0


class TestCalculateCourseGradeWithSimulation:
    def test_no_grades_returns_none(self):
        result = GPAService.calculate_course_grade_with_simulation([])
        assert result["actual_grade"] is None
        assert result["simulated_grade"] is None
        assert result["percentage_completed"] == 0

    def test_real_grades_only(self):
        # 60%@4.0 + 40%@3.0 = 3.6
        cals = [make_cal(4.0, 60), make_cal(3.0, 40)]
        result = GPAService.calculate_course_grade_with_simulation(cals)
        assert result["actual_grade"] == pytest.approx(3.6)
        assert result["simulated_grade"] == pytest.approx(3.6)
        assert result["percentage_completed"] == 100.0

    def test_mixed_real_and_simulation(self):
        real = make_cal(4.0, 50)
        sim = make_cal(2.0, 50, is_simulation=True)
        result = GPAService.calculate_course_grade_with_simulation([real, sim])
        assert result["actual_grade"] == 4.0
        assert result["simulated_grade"] == pytest.approx(3.0)  # (4.0*50 + 2.0*50)/100
        assert result["percentage_completed"] == 50.0
        assert result["percentage_remaining"] == 50.0

    def test_exclude_simulation_flag(self):
        real = make_cal(4.0, 50)
        sim = make_cal(2.0, 50, is_simulation=True)
        result = GPAService.calculate_course_grade_with_simulation([real, sim], include_simulation=False)
        assert result["simulated_grade"] is None


class TestCalculateSemesterGpa:
    def test_no_graded_courses(self, m_fis1, config):
        pensum = Pensum(materias=[m_fis1])
        result = GPAService.calculate_semester_gpa(2, pensum, config)
        assert result["gpa"] is None
        assert result["total_credits"] == 3
        assert result["graded_credits"] == 0

    def test_single_graded_course(self, m_calc1, config):
        pensum = Pensum(materias=[m_calc1])
        result = GPAService.calculate_semester_gpa(1, pensum, config)
        assert result["gpa"] == 4.0
        assert result["graded_credits"] == 3
        assert result["passed"] == 1
        assert result["failed"] == 0

    def test_credit_weighted_gpa(self, config):
        # 3cr@4.0 + 4cr@3.0 en semestre 1 → (12+12)/7 ≈ 3.43
        m1 = Materia(code="A", name="A", credits=3, semester=1, grade=4.0, status=MateriaStatus.PASSED)
        m2 = Materia(code="B", name="B", credits=4, semester=1, grade=3.0, status=MateriaStatus.PASSED)
        pensum = Pensum(materias=[m1, m2])
        result = GPAService.calculate_semester_gpa(1, pensum, config)
        assert result["gpa"] == pytest.approx(24 / 7, rel=1e-2)
        assert result["passed"] == 2

    def test_failed_course_counted(self, config):
        m = Materia(code="A", name="A", credits=3, semester=1, grade=2.5, status=MateriaStatus.FAILED)
        pensum = Pensum(materias=[m])
        result = GPAService.calculate_semester_gpa(1, pensum, config)
        assert result["failed"] == 1
        assert result["passed"] == 0


class TestCalculateCumulativeGpa:
    def test_empty_pensum(self, config):
        result = GPAService.calculate_cumulative_gpa(Pensum(), config)
        assert result["cumulative_gpa"] is None
        assert result["total_credits_completed"] == 0
        assert result["progress_percentage"] == 0

    def test_credit_weighted_across_semesters(self, pensum_con_prereqs, config):
        # CALC1 (3cr, 4.0) + CALC2 (4cr, 3.5); FIS1 sin nota
        # GPA = (4.0*3 + 3.5*4) / 7 = 26/7 ≈ 3.71
        result = GPAService.calculate_cumulative_gpa(pensum_con_prereqs, config)
        assert result["cumulative_gpa"] == pytest.approx(26 / 7, rel=1e-2)
        assert result["total_credits_completed"] == 7


class TestSimulateGrades:
    def test_skips_already_graded_course(self, pensum_simple, config):
        result = GPAService.simulate_grades(pensum_simple, {"CALC1": 2.0}, config)
        assert result["simulated_courses"] == []

    def test_simulates_ungraded_course(self, pensum_simple, config):
        # pensum_simple: CALC1 graded 4.0/3cr, FIS1 ungraded/3cr
        # Simular FIS1 en 3.0 → new_gpa = (4.0*3 + 3.0*3)/6 = 3.5
        result = GPAService.simulate_grades(pensum_simple, {"FIS1": 3.0}, config)
        assert result["simulated_gpa"] == pytest.approx(3.5)
        assert len(result["simulated_courses"]) == 1
        assert result["simulated_courses"][0]["code"] == "FIS1"

    def test_gpa_improvement_detected(self, pensum_simple, config):
        # FIS1 a 4.5 → new_gpa = (4.0*3 + 4.5*3)/6 = 4.25 > 4.0
        result = GPAService.simulate_grades(pensum_simple, {"FIS1": 4.5}, config)
        assert result["gpa_improved"] is True


class TestGetNeededGradeForTarget:
    def test_achievable_target(self, pensum_simple, config):
        # Actual: 4.0 GPA en 3cr. Target 3.5 con FIS1 (3cr)
        # needed = (3.5*6 - 4.0*3)/3 = (21-12)/3 = 3.0
        result = GPAService.get_needed_grade_for_target(pensum_simple, 3.5, ["FIS1"], config)
        assert result["achievable"] is True
        assert result["needed_average"] == pytest.approx(3.0)

    def test_not_achievable_target(self, pensum_simple, config):
        # Target 5.0: needed = (5.0*6 - 4.0*3)/3 = 6.0 > escala de 5.0
        result = GPAService.get_needed_grade_for_target(pensum_simple, 5.0, ["FIS1"], config)
        assert result["achievable"] is False

    def test_no_remaining_courses(self, pensum_simple, config):
        result = GPAService.get_needed_grade_for_target(pensum_simple, 3.5, [], config)
        assert result["needed_average"] is None

    def test_already_graded_course_ignored(self, pensum_simple, config):
        # CALC1 ya tiene nota; no cuenta como "remaining"
        result = GPAService.get_needed_grade_for_target(pensum_simple, 3.5, ["CALC1"], config)
        assert result["needed_average"] is None


class TestCheckGpaAlerts:
    def test_no_alerts_when_gpa_above_threshold(self, pensum_simple, config):
        # CALC1 con nota 4.0 > umbral 3.0
        alerts = GPAService.check_gpa_alerts(pensum_simple, config)
        assert all(a["type"] != "cumulative_gpa_low" for a in alerts)

    def test_low_cumulative_gpa_alert(self, config):
        m = Materia(code="A", name="A", credits=3, semester=1,
                    grade=2.0, status=MateriaStatus.FAILED)
        alerts = GPAService.check_gpa_alerts(Pensum(materias=[m]), config)
        assert any(a["type"] == "cumulative_gpa_low" for a in alerts)

    def test_failed_courses_alert(self, config):
        m = Materia(code="A", name="A", credits=3, semester=1,
                    grade=2.0, status=MateriaStatus.FAILED)
        alerts = GPAService.check_gpa_alerts(Pensum(materias=[m]), config)
        assert any(a["type"] == "failed_courses" for a in alerts)


class TestGpaTrend:
    def test_insufficient_data_empty(self):
        assert GPAService._calculate_gpa_trend({}) == "insufficient_data"

    def test_insufficient_data_single_semester(self):
        assert GPAService._calculate_gpa_trend({1: {"gpa": 4.0}}) == "insufficient_data"

    def test_improving(self):
        semesters = {1: {"gpa": 3.0}, 2: {"gpa": 3.5}, 3: {"gpa": 4.0}}
        assert GPAService._calculate_gpa_trend(semesters) == "improving"

    def test_declining(self):
        semesters = {1: {"gpa": 4.0}, 2: {"gpa": 3.5}, 3: {"gpa": 3.0}}
        assert GPAService._calculate_gpa_trend(semesters) == "declining"

    def test_stable(self):
        # Diferencia de 0.05 < umbral de 0.1
        semesters = {1: {"gpa": 3.8}, 2: {"gpa": 3.85}}
        assert GPAService._calculate_gpa_trend(semesters) == "stable"

    def test_ignores_semesters_without_gpa(self):
        semesters = {1: {"gpa": 3.0}, 2: {"gpa": None}, 3: {"gpa": 4.0}}
        assert GPAService._calculate_gpa_trend(semesters) == "improving"
