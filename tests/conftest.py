import pytest
from app.models.materia import Materia, MateriaStatus, Pensum
from app.models.configuracion import Configuracion


@pytest.fixture
def config():
    return Configuracion()


@pytest.fixture
def m_calc1():
    return Materia(code="CALC1", name="Cálculo I", credits=3, semester=1,
                   grade=4.0, status=MateriaStatus.PASSED)


@pytest.fixture
def m_calc2():
    return Materia(code="CALC2", name="Cálculo II", credits=4, semester=2,
                   prerequisites=["CALC1"], grade=3.5, status=MateriaStatus.PASSED)


@pytest.fixture
def m_fis1():
    return Materia(code="FIS1", name="Física I", credits=3, semester=2,
                   status=MateriaStatus.PENDING)


@pytest.fixture
def pensum_simple(m_calc1, m_fis1):
    """CALC1 (graded 4.0, sem 1, 3cr) + FIS1 (ungraded, sem 2, 3cr)"""
    return Pensum(materias=[m_calc1, m_fis1])


@pytest.fixture
def pensum_con_prereqs(m_calc1, m_calc2, m_fis1):
    """CALC1 → CALC2 prereq chain, FIS1 sin dependencias"""
    return Pensum(materias=[m_calc1, m_calc2, m_fis1])
