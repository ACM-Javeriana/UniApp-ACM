/**
 * Semester Module - Handles individual semester view and management
 */

const Semester = {
    semesterNumber: null,
    materias: [],
    selectedCourse: null,

    /**
     * Initialize the semester view
     */
    init(semesterNumber) {
        this.semesterNumber = semesterNumber;
        this.loadSemester();
        this.setupEventListeners();
        this.checkUrlParams();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        window.addEventListener('datasynced', () => this.loadSemester());
    },

    /**
     * Check URL parameters for course selection
     */
    checkUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const courseCode = params.get('course');
        if (courseCode) {
            setTimeout(() => this.showCourseModal(courseCode), 100);
        }
    },

    /**
     * Load semester data
     */
    loadSemester() {
        const allMaterias = storage.getMaterias();
        this.materias = allMaterias.filter(m => m.semestre === this.semesterNumber);
        this.renderSemester();
        this.updateStats();
    },

    /**
     * Render the semester view
     */
    renderSemester() {
        const container = document.getElementById('courseList');
        if (!container) return;

        if (this.materias.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                    </svg>
                    <p class="text-lg">No hay materias en este semestre</p>
                    <p class="text-sm mt-2">Agrega materias desde la vista de pensum</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.materias.map(m => this.renderCourseRow(m)).join('');
    },

    /**
     * Render a course row
     */
    renderCourseRow(materia) {
        const calificacion = storage.getCalificacion(materia.codigo);
        const grade = calificacion?.nota;
        
        const statusConfig = {
            'pending': { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', label: 'Pendiente' },
            'enrolled': { bg: 'bg-blue-50', border: 'border-accent', text: 'text-accent', label: 'Inscrita' },
            'passed': { bg: 'bg-green-50', border: 'border-green-400', text: 'text-green-600', label: 'Aprobada' },
            'failed': { bg: 'bg-red-50', border: 'border-red-400', text: 'text-red-600', label: 'Reprobada' },
            'dropped': { bg: 'bg-yellow-50', border: 'border-yellow-400', text: 'text-yellow-600', label: 'Retirada' }
        };

        const status = statusConfig[materia.estado] || statusConfig.pending;
        const hasCustomColor = materia.color && materia.color.startsWith('#');
        const rowBgClass = hasCustomColor ? '' : status.bg;
        const rowBorderClass = hasCustomColor ? '' : status.border;
        const rowStyle = hasCustomColor ? `style="border-color: ${materia.color}; background-color: ${materia.color}15;"` : '';

        return `
            <div class="course-row ${rowBgClass} ${rowBorderClass} border rounded-lg p-4 mb-3 hover:shadow-md transition-shadow cursor-pointer" ${rowStyle}
                 onclick="Semester.showCourseModal('${materia.codigo}')">
                <div class="flex flex-wrap items-center justify-between gap-4">
                    <div class="flex-1 min-w-[200px]">
                        <h3 class="font-semibold text-gray-800">${materia.nombre}</h3>
                        <p class="text-sm text-gray-500">${materia.codigo}</p>
                        ${materia.prerrequisitos?.length ? 
                            `<p class="text-xs text-gray-400 mt-1">Prerrequisitos: ${materia.prerrequisitos.join(', ')}</p>` : ''}
                    </div>
                    
                    <div class="flex items-center gap-4">
                        <div class="text-center">
                            <p class="text-xs text-gray-500">Créditos</p>
                            <p class="font-semibold">${materia.creditos}</p>
                        </div>
                        
                        <div class="text-center min-w-[60px]">
                            <p class="text-xs text-gray-500">Nota</p>
                            <p class="font-semibold ${grade !== undefined ? '' : 'text-gray-300'}">
                                ${grade !== undefined ? grade.toFixed(1) : '--'}
                            </p>
                        </div>
                        
                        <div class="text-center min-w-[80px]">
                            <span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}">
                                ${status.label}
                            </span>
                        </div>
                        
                        <div class="flex gap-2">
                            <button onclick="event.stopPropagation(); Semester.changeStatus('${materia.codigo}')"
                                    class="p-2 text-gray-400 hover:text-accent rounded-full hover:bg-white"
                                    title="Cambiar estado">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                </svg>
                            </button>
                            <button onclick="event.stopPropagation(); Semester.simulateLoss('${materia.codigo}')"
                                    class="p-2 text-gray-400 hover:text-red-500 rounded-full hover:bg-white"
                                    title="Simular pérdida">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Update semester statistics
     */
    updateStats() {
        // Total credits
        const totalCredits = this.materias.reduce((sum, m) => sum + (m.creditos || 0), 0);
        const creditosElement = document.getElementById('totalCreditosSemestre');
        if (creditosElement) creditosElement.textContent = totalCredits;

        // Completed courses
        const completed = this.materias.filter(m => m.estado === 'passed').length;
        const completadasElement = document.getElementById('materiasCompletadas');
        if (completadasElement) completadasElement.textContent = `${completed}/${this.materias.length}`;

        // Calculate semester GPA
        this.updateSemesterGPA();
    },

    /**
     * Calculate semester GPA
     */
    updateSemesterGPA() {
        const calificaciones = storage.getCalificaciones();
        let totalPoints = 0;
        let totalCredits = 0;

        this.materias.forEach(m => {
            const cal = calificaciones.find(c => c.codigo_materia === m.codigo);
            if (cal && cal.nota !== null && cal.nota !== undefined) {
                totalPoints += cal.nota * m.creditos;
                totalCredits += m.creditos;
            }
        });

        const gpa = totalCredits > 0 ? (totalPoints / totalCredits) : 0;
        
        const gpaElement = document.getElementById('gpaSemestre');
        if (gpaElement) {
            gpaElement.textContent = gpa.toFixed(2);
            
            const config = storage.getConfiguracion();
            if (gpa > 0 && gpa < config.umbral_gpa) {
                gpaElement.classList.add('text-red-600');
            } else {
                gpaElement.classList.remove('text-red-600');
            }
        }
    },

    /**
     * Show course details modal
     */
    showCourseModal(codigo) {
        this.selectedCourse = this.materias.find(m => m.codigo === codigo);
        if (!this.selectedCourse) return;

        const modal = document.getElementById('courseModal');
        if (!modal) return;

        // Populate modal
        document.getElementById('modalCourseName').textContent = this.selectedCourse.nombre;
        document.getElementById('modalCourseCode').textContent = this.selectedCourse.codigo;
        document.getElementById('modalCourseCredits').textContent = this.selectedCourse.creditos;
        
        // Set current status
        const statusSelect = document.getElementById('courseStatus');
        if (statusSelect) statusSelect.value = this.selectedCourse.estado || 'pending';

        // Set current grade
        const calificacion = storage.getCalificacion(codigo);
        const gradeInput = document.getElementById('courseGrade');
        if (gradeInput) gradeInput.value = calificacion?.nota ?? '';

        // Show prerequisites
        const prereqsContainer = document.getElementById('coursePrerequisites');
        if (prereqsContainer) {
            if (this.selectedCourse.prerrequisitos?.length) {
                prereqsContainer.innerHTML = this.selectedCourse.prerrequisitos
                    .map(p => `<span class="inline-block bg-gray-100 px-2 py-1 rounded text-sm">${p}</span>`)
                    .join(' ');
            } else {
                prereqsContainer.innerHTML = '<span class="text-gray-400">Ninguno</span>';
            }
        }

        modal.classList.remove('hidden');
    },

    /**
     * Hide course modal
     */
    hideCourseModal() {
        const modal = document.getElementById('courseModal');
        if (modal) modal.classList.add('hidden');
        this.selectedCourse = null;
    },

    /**
     * Save course changes from modal
     */
    saveCourseChanges() {
        if (!this.selectedCourse) return;

        const statusSelect = document.getElementById('courseStatus');
        const gradeInput = document.getElementById('courseGrade');

        // Update status
        if (statusSelect) {
            this.selectedCourse.estado = statusSelect.value;
            storage.saveMateria(this.selectedCourse);
        }

        // Update grade
        if (gradeInput && gradeInput.value !== '') {
            const nota = parseFloat(gradeInput.value);
            if (!isNaN(nota) && nota >= 0 && nota <= 5) {
                storage.saveCalificacion({
                    codigo_materia: this.selectedCourse.codigo,
                    nota: nota,
                    fecha: new Date().toISOString()
                });
            }
        }

        this.hideCourseModal();
        this.loadSemester();
        App.showAlert('Cambios guardados', 'success');
    },

    /**
     * Change course status (cycle through statuses)
     */
    changeStatus(codigo) {
        const materia = this.materias.find(m => m.codigo === codigo);
        if (!materia) return;

        const statusOrder = ['pending', 'enrolled', 'passed', 'failed', 'dropped'];
        const currentIndex = statusOrder.indexOf(materia.estado || 'pending');
        const nextIndex = (currentIndex + 1) % statusOrder.length;
        
        materia.estado = statusOrder[nextIndex];
        storage.saveMateria(materia);
        this.loadSemester();
    },

    /**
     * Simulate losing a course
     */
    simulateLoss(codigo) {
        const materia = this.materias.find(m => m.codigo === codigo);
        if (!materia) return;

        // Find affected courses using Pensum logic
        const allMaterias = storage.getMaterias();
        const affected = [];
        const visited = new Set();

        const findDependents = (code) => {
            allMaterias.forEach(m => {
                if (!visited.has(m.codigo) && m.prerrequisitos?.includes(code)) {
                    visited.add(m.codigo);
                    affected.push(m);
                    findDependents(m.codigo);
                }
            });
        };

        findDependents(codigo);

        if (affected.length === 0) {
            App.showAlert(`Perder ${materia.nombre} no afectará directamente otras materias`, 'info');
        } else {
            const affectedList = affected.map(m => `• ${m.nombre} (Semestre ${m.semestre})`).join('\n');
            App.showAlert(
                `Si pierdes "${materia.nombre}", estas materias se verán afectadas:\n\n${affectedList}\n\nTotal: ${affected.length} materias`,
                'warning'
            );
        }
    },

    /**
     * Simulate GPA with different grades
     */
    simulateGPA() {
        const modal = document.getElementById('gpaSimulatorModal');
        if (!modal) {
            // Simple prompt-based simulation
            const targetGPA = parseFloat(prompt('¿Qué GPA deseas alcanzar?'));
            if (isNaN(targetGPA) || targetGPA < 0 || targetGPA > 5) {
                App.showAlert('GPA inválido', 'error');
                return;
            }

            // Calculate required average for pending courses
            const calificaciones = storage.getCalificaciones();
            const allMaterias = storage.getMaterias();
            
            let completedPoints = 0;
            let completedCredits = 0;
            let pendingCredits = 0;

            allMaterias.forEach(m => {
                const cal = calificaciones.find(c => c.codigo_materia === m.codigo);
                if (cal && cal.nota !== null) {
                    completedPoints += cal.nota * m.creditos;
                    completedCredits += m.creditos;
                } else if (m.estado !== 'dropped') {
                    pendingCredits += m.creditos;
                }
            });

            if (pendingCredits === 0) {
                App.showAlert('No hay materias pendientes para simular', 'info');
                return;
            }

            const totalCredits = completedCredits + pendingCredits;
            const requiredPoints = (targetGPA * totalCredits) - completedPoints;
            const requiredAverage = requiredPoints / pendingCredits;

            if (requiredAverage > 5) {
                App.showAlert(`Es imposible alcanzar un GPA de ${targetGPA} con las materias pendientes.`, 'error');
            } else if (requiredAverage < 0) {
                App.showAlert(`Ya tienes un GPA suficiente para alcanzar ${targetGPA}`, 'success');
            } else {
                App.showAlert(
                    `Para alcanzar un GPA de ${targetGPA}, necesitas un promedio de ${requiredAverage.toFixed(2)} en tus ${pendingCredits} créditos pendientes.`,
                    'info'
                );
            }
        } else {
            modal.classList.remove('hidden');
        }
    },

    /**
     * Export semester data
     */
    exportSemester() {
        const data = {
            semester: this.semesterNumber,
            materias: this.materias,
            calificaciones: storage.getCalificaciones().filter(c => 
                this.materias.some(m => m.codigo === c.codigo_materia)
            ),
            exportDate: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `semestre-${this.semesterNumber}-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        App.showAlert('Semestre exportado', 'success');
    }
};

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Semester };
}
