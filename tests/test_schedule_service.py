import pytest
from app.models.clase import Clase, BloqueHorario, DayOfWeek
from app.models.horario import HorarioCombination, Franja, FranjaStatus
from app.services.schedule_service import ScheduleService


def make_block(day: str, start: str, end: str) -> BloqueHorario:
    return BloqueHorario(day=DayOfWeek(day), start=start, end=end)


def make_clase(materia_code: str, class_code: str, *blocks: BloqueHorario) -> Clase:
    return Clase(materia_code=materia_code, class_code=class_code, schedule=list(blocks))


def make_combo(id, free_days, gaps_count=0, gaps_minutes=0,
               earliest_start="08:00", latest_end="18:00") -> HorarioCombination:
    return HorarioCombination(
        id=id,
        free_days=free_days,
        gaps_count=gaps_count,
        gaps_minutes=gaps_minutes,
        earliest_start=earliest_start,
        latest_end=latest_end,
    )


class TestBloqueHorarioOverlap:
    def test_same_day_overlap(self):
        b1 = make_block("L", "08:00", "10:00")
        b2 = make_block("L", "09:00", "11:00")
        assert b1.overlaps_with(b2) is True

    def test_same_day_adjacent_no_overlap(self):
        b1 = make_block("L", "08:00", "10:00")
        b2 = make_block("L", "10:00", "12:00")
        assert b1.overlaps_with(b2) is False

    def test_different_day_no_overlap(self):
        b1 = make_block("L", "08:00", "10:00")
        b2 = make_block("M", "08:00", "10:00")
        assert b1.overlaps_with(b2) is False

    def test_contained_block_overlaps(self):
        b1 = make_block("L", "08:00", "12:00")
        b2 = make_block("L", "09:00", "11:00")
        assert b1.overlaps_with(b2) is True

    def test_overlap_is_symmetric(self):
        b1 = make_block("L", "08:00", "10:00")
        b2 = make_block("L", "09:00", "11:00")
        assert b1.overlaps_with(b2) == b2.overlaps_with(b1)


class TestCheckConflicts:
    def test_no_conflicts(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        c2 = make_clase("MAT2", "B1", make_block("L", "10:00", "12:00"))
        assert ScheduleService.check_conflicts([c1, c2]) == []

    def test_overlap_detected(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        c2 = make_clase("MAT2", "B1", make_block("L", "09:00", "11:00"))
        conflicts = ScheduleService.check_conflicts([c1, c2])
        assert len(conflicts) > 0
        assert conflicts[0]["class1"]["materia"] == "MAT1"
        assert conflicts[0]["class2"]["materia"] == "MAT2"

    def test_different_days_no_conflict(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        c2 = make_clase("MAT2", "B1", make_block("M", "08:00", "10:00"))
        assert ScheduleService.check_conflicts([c1, c2]) == []

    def test_single_class_no_conflict(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        assert ScheduleService.check_conflicts([c1]) == []

    def test_empty_list(self):
        assert ScheduleService.check_conflicts([]) == []


class TestGenerateCombinations:
    def test_single_course_single_section(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        result = ScheduleService.generate_combinations({"MAT1": [c1]})
        assert result["total_generated"] == 1
        assert result["total_possible"] == 1
        assert result["warning"] is None

    def test_two_compatible_courses(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        c2 = make_clase("MAT2", "B1", make_block("L", "10:00", "12:00"))
        result = ScheduleService.generate_combinations({"MAT1": [c1], "MAT2": [c2]})
        assert result["total_generated"] == 1
        assert result["total_possible"] == 1

    def test_conflict_filtered_out(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        c2 = make_clase("MAT2", "B1", make_block("L", "09:00", "11:00"))
        result = ScheduleService.generate_combinations({"MAT1": [c1], "MAT2": [c2]})
        assert result["total_generated"] == 0
        assert result["total_possible"] == 1

    def test_multiple_sections_correct_count(self):
        # MAT1: A1(L 8-10), A2(M 8-10) | MAT2: B1(L 9-11 conflicto con A1), B2(W 8-10)
        # Válidas: (A1,B2), (A2,B1), (A2,B2) → 3 de 4
        a1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        a2 = make_clase("MAT1", "A2", make_block("M", "08:00", "10:00"))
        b1 = make_clase("MAT2", "B1", make_block("L", "09:00", "11:00"))
        b2 = make_clase("MAT2", "B2", make_block("W", "08:00", "10:00"))
        result = ScheduleService.generate_combinations({"MAT1": [a1, a2], "MAT2": [b1, b2]})
        assert result["total_generated"] == 3
        assert result["total_possible"] == 4

    def test_blocked_slot_excludes_combination(self):
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        blocked = Franja(day=DayOfWeek.MONDAY, start="07:00", end="11:00",
                         status=FranjaStatus.BLOCKED)
        result = ScheduleService.generate_combinations({"MAT1": [c1]}, franjas=[blocked])
        assert result["total_generated"] == 0

    def test_preferred_slot_not_excluded(self):
        # Un slot PREFERRED no bloquea cursos
        c1 = make_clase("MAT1", "A1", make_block("L", "08:00", "10:00"))
        preferred = Franja(day=DayOfWeek.MONDAY, start="07:00", end="11:00",
                           status=FranjaStatus.PREFERRED)
        result = ScheduleService.generate_combinations({"MAT1": [c1]}, franjas=[preferred])
        assert result["total_generated"] == 1

    def test_warning_on_large_combination_space(self):
        # 33 × 33 = 1089 > umbral de 1000
        sections_a = [
            make_clase("MAT1", f"A{i}", make_block("L", "08:00", "09:00"))
            for i in range(33)
        ]
        sections_b = [
            make_clase("MAT2", f"B{i}", make_block("L", "08:00", "09:00"))
            for i in range(33)
        ]
        result = ScheduleService.generate_combinations(
            {"MAT1": sections_a, "MAT2": sections_b},
            max_combinations=5,
        )
        assert result["warning"] is not None
        assert result["total_possible"] == 33 * 33

    def test_max_combinations_limits_output(self):
        # 4 secciones × 4 secciones = 16 combinaciones válidas (días distintos)
        sections_a = [
            make_clase("MAT1", f"A{i}", make_block("L", f"{8+i:02d}:00", f"{9+i:02d}:00"))
            for i in range(4)
        ]
        sections_b = [
            make_clase("MAT2", f"B{i}", make_block("M", f"{8+i:02d}:00", f"{9+i:02d}:00"))
            for i in range(4)
        ]
        result = ScheduleService.generate_combinations(
            {"MAT1": sections_a, "MAT2": sections_b},
            max_combinations=3,
        )
        assert result["total_generated"] <= 3

    def test_empty_courses(self):
        # itertools.product() sin args produce una tupla vacía → 1 "combinación" de 0 cursos
        result = ScheduleService.generate_combinations({})
        assert result["total_generated"] == 1
        assert result["total_possible"] == 1

    def test_total_credits_summed_correctly(self):
        # Clase con credits=3 y otra con credits=4 → total_credits=7
        c1 = Clase(materia_code="MAT1", class_code="A1", credits=3,
                   schedule=[make_block("L", "08:00", "10:00")])
        c2 = Clase(materia_code="MAT2", class_code="B1", credits=4,
                   schedule=[make_block("L", "10:00", "12:00")])
        result = ScheduleService.generate_combinations({"MAT1": [c1], "MAT2": [c2]})
        assert result["total_generated"] == 1
        assert result["combinations"][0].total_credits == 7


class TestFilterCombinations:
    def test_filter_by_min_free_days(self):
        c1 = make_combo("c1", free_days=2)
        c2 = make_combo("c2", free_days=4)
        result = ScheduleService.filter_combinations([c1, c2], {"min_free_days": 3})
        assert len(result) == 1
        assert result[0].id == "c2"

    def test_filter_by_max_gaps(self):
        c1 = make_combo("c1", free_days=3, gaps_count=5)
        c2 = make_combo("c2", free_days=3, gaps_count=1)
        result = ScheduleService.filter_combinations([c1, c2], {"max_gaps": 2})
        assert len(result) == 1
        assert result[0].id == "c2"

    def test_sort_by_free_days_descending(self):
        combos = [make_combo(f"c{i}", free_days=i) for i in [2, 4, 1]]
        result = ScheduleService.filter_combinations(combos, {"sort_by": "free_days", "sort_order": "desc"})
        assert [r.free_days for r in result] == [4, 2, 1]

    def test_empty_filters_returns_all(self):
        combos = [make_combo(f"c{i}", free_days=i) for i in range(3)]
        result = ScheduleService.filter_combinations(combos, {})
        assert len(result) == 3

    def test_no_matches_returns_empty(self):
        combos = [make_combo("c1", free_days=1), make_combo("c2", free_days=2)]
        result = ScheduleService.filter_combinations(combos, {"min_free_days": 5})
        assert result == []


class TestValidateClassData:
    def test_valid_data(self):
        data = {
            "materia_code": "MAT1",
            "class_code": "A1",
            "schedule": [{"day": "L", "start": "08:00", "end": "10:00"}],
        }
        result = ScheduleService.validate_class_data(data)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_materia_code(self):
        data = {"class_code": "A1", "schedule": [{"day": "L", "start": "08:00", "end": "10:00"}]}
        result = ScheduleService.validate_class_data(data)
        assert result["valid"] is False
        assert any("Course code" in e for e in result["errors"])

    def test_missing_class_code(self):
        data = {"materia_code": "MAT1", "schedule": [{"day": "L", "start": "08:00", "end": "10:00"}]}
        result = ScheduleService.validate_class_data(data)
        assert result["valid"] is False

    def test_empty_schedule(self):
        data = {"materia_code": "MAT1", "class_code": "A1", "schedule": []}
        result = ScheduleService.validate_class_data(data)
        assert result["valid"] is False
        assert any("time block" in e for e in result["errors"])

    def test_end_before_start(self):
        data = {
            "materia_code": "MAT1",
            "class_code": "A1",
            "schedule": [{"day": "L", "start": "10:00", "end": "08:00"}],
        }
        result = ScheduleService.validate_class_data(data)
        assert result["valid"] is False
        assert any("End time must be after start time" in e for e in result["errors"])

    def test_missing_day_in_block(self):
        data = {
            "materia_code": "MAT1",
            "class_code": "A1",
            "schedule": [{"start": "08:00", "end": "10:00"}],
        }
        result = ScheduleService.validate_class_data(data)
        assert result["valid"] is False
