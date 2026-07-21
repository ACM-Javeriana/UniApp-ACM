/**
 * Pensum Module - Handles pensum visualization and management
 */

const Pensum = {
    materias: [],
    semesterFilter: null,

    /**
     * Initialize the pensum view
     */
    init() {
        this.loadPensum();
        this.setupEventListeners();
    },

    /**
     * Load and display all materias
     */
    loadPensum() {
        this.materias = storage.getMaterias();
        this.renderPensum();
        this.updateStats();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for data sync events
        window.addEventListener('datasynced', () => this.loadPensum());

        // Import file handler
        const importInput = document.getElementById('importFile');
        if (importInput) {
            importInput.addEventListener('change', (e) => this.handleImport(e));
        }
    },

    /**
     * Render the pensum grid by semesters
     */
    renderPensum() {
        const container = document.getElementById('pensumGrid');
        if (!container) return;

        // Group materias by semester
        const bySemester = {};
        this.materias.forEach(m => {
            const sem = m.semestre || 0;
            if (!bySemester[sem]) bySemester[sem] = [];
            bySemester[sem].push(m);
        });

        // Get max semester
        const maxSemester = Math.max(...Object.keys(bySemester).map(Number), 0);

        // Render each semester
        let html = '';
        for (let sem = 1; sem <= Math.max(maxSemester, 10); sem++) {
            const materias = bySemester[sem] || [];
            html += this.renderSemesterColumn(sem, materias);
        }

        container.innerHTML = html;
    },

    /**
     * Render a single semester column
     */
    renderSemesterColumn(semester, materias) {
        const totalCredits = materias.reduce((sum, m) => sum + (m.creditos || 0), 0);
        
        return `
            <div class="semester-column bg-white dark:bg-gray-800 rounded-lg shadow p-4 min-w-[200px] transition-colors">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="font-semibold text-gray-800 dark:text-gray-100">Semestre ${semester}</h3>
                    <span class="text-xs text-gray-500 dark:text-gray-400">${totalCredits} cr</span>
                </div>
                <div class="space-y-2">
                    ${materias.map(m => this.renderCourseCard(m)).join('')}
                </div>
                <a href="/semester/${semester}" 
                   class="block mt-3 text-center text-sm text-accent hover:text-accent-dark">
                    Ver semestre →
                </a>
            </div>
        `;
    },

    /**
     * Render a course card
     */
    renderCourseCard(materia) {
        const statusColors = {
            'pending': 'status-pending',
            'enrolled': 'status-enrolled',
            'passed': 'status-passed',
            'failed': 'status-failed',
            'dropped': 'status-dropped'
        };

        const statusLabels = {
            'pending': 'Pendiente',
            'enrolled': 'Inscrita',
            'passed': 'Aprobada',
            'failed': 'Reprobada',
            'dropped': 'Retirada'
        };

        const statusClass = statusColors[materia.estado] || statusColors.pending;
        const statusLabel = statusLabels[materia.estado] || 'Pendiente';
        const hasCustomColor = materia.color && materia.color.startsWith('#');
        const isFailed = materia.estado === 'failed';
        const useCustomColor = hasCustomColor && !isFailed;
        const cardBorderClass = useCustomColor ? '' : statusClass;
        const cardStyle = useCustomColor ? `style="border-left-color: ${materia.color}; background-color: ${materia.color}15;"` : '';

        // Get grade if exists
        const calificacion = storage.getCalificacion(materia.codigo);
        const gradeDisplay = calificacion ? `<span class="text-xs font-medium">${calificacion.nota.toFixed(1)}</span>` : '';

        return `
            <div class="course-card p-3 rounded border-l-4 ${cardBorderClass} cursor-pointer hover:shadow-md transition-all" ${cardStyle}
                 onclick="Pensum.showCourseDetails('${materia.codigo}')"
                 data-codigo="${materia.codigo}">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="font-medium text-sm text-gray-800 dark:text-gray-100">${materia.nombre}</p>
                        <p class="text-xs text-gray-500 dark:text-gray-400">${materia.codigo}</p>
                    </div>
                    <div class="text-right">
                        <span class="text-xs bg-gray-200 dark:bg-gray-600 px-1.5 py-0.5 rounded">${materia.creditos} cr</span>
                        ${gradeDisplay}
                    </div>
                </div>
                ${materia.prerrequisitos?.length ? 
                    `<p class="text-xs text-gray-400 mt-1">Req: ${materia.prerrequisitos.join(', ')}</p>` : ''}
                <span class="inline-block mt-1 text-xs px-2 py-0.5 rounded-full bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300">${statusLabel}</span>
            </div>
        `;
    },

    /**
     * Update statistics display
     */
    updateStats() {
        // Total credits
        const totalCredits = this.materias.reduce((sum, m) => sum + (m.creditos || 0), 0);
        const creditosElement = document.getElementById('totalCreditos');
        if (creditosElement) creditosElement.textContent = totalCredits;

        // Completed credits
        const completedCredits = this.materias
            .filter(m => m.estado === 'passed')
            .reduce((sum, m) => sum + (m.creditos || 0), 0);
        const completadosElement = document.getElementById('creditosCompletados');
        if (completadosElement) completadosElement.textContent = completedCredits;

        // Progress percentage
        const progressElement = document.getElementById('progresoCarrera');
        if (progressElement && totalCredits > 0) {
            const progress = ((completedCredits / totalCredits) * 100).toFixed(1);
            progressElement.textContent = `${progress}%`;
        }

        // Calculate GPA
        this.updateGPA();
    },

    /**
     * Calculate and display GPA
     */
    updateGPA() {
        const calificaciones = storage.getCalificaciones();
        let totalPoints = 0;
        let totalCredits = 0;

        calificaciones.forEach(cal => {
            const materia = this.materias.find(m => m.codigo === cal.codigo_materia);
            if (materia && cal.nota !== null && cal.nota >= 3.0) {
                totalPoints += cal.nota * materia.creditos;
                totalCredits += materia.creditos;
            }
        });

        const gpa = totalCredits > 0 ? (totalPoints / totalCredits) : 0;
        
        const gpaElement = document.getElementById('gpaAcumulado');
        if (gpaElement) {
            gpaElement.textContent = gpa.toFixed(2);
            
            // Check GPA threshold
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
    showCourseDetails(codigo) {
        const materia = this.materias.find(m => m.codigo === codigo);
        if (!materia) return;

        // Show course modal (implemented in course_modal.html)
        if (typeof showCourseModal === 'function') {
            showCourseModal(materia);
        } else {
            // Navigate to semester view
            window.location.href = `/semester/${materia.semestre}?course=${codigo}`;
        }
    },

    /**
     * Show add course modal
     */
    showAddModal() {
        const modal = document.getElementById('addMateriaModal');
        if (modal) {
            modal.classList.remove('hidden');
            document.getElementById('addMateriaForm')?.reset();
        }
    },

    /**
     * Hide add course modal
     */
    hideAddModal() {
        const modal = document.getElementById('addMateriaModal');
        if (modal) modal.classList.add('hidden');
    },

    /**
     * Add a new course
     */
    addCourse(formData) {
        const materia = {
            codigo: formData.get('codigo'),
            nombre: formData.get('nombre'),
            creditos: parseInt(formData.get('creditos')),
            semestre: parseInt(formData.get('semestre')),
            estado: 'pending',
            prerrequisitos: formData.get('prerrequisitos')?.split(',').map(s => s.trim()).filter(Boolean) || []
        };

        // Validate
        if (!materia.codigo || !materia.nombre || !materia.creditos || !materia.semestre) {
            App.showAlert('Por favor completa todos los campos requeridos', 'error');
            return false;
        }

        // Check if already exists
        if (this.materias.find(m => m.codigo === materia.codigo)) {
            App.showAlert('Ya existe una materia con este código', 'error');
            return false;
        }

        // Save
        storage.saveMateria(materia);
        this.hideAddModal();
        this.loadPensum();
        App.showAlert('Materia agregada correctamente', 'success');
        return true;
    },

    /**
     * Delete a course
     */
    deleteCourse(codigo) {
        if (!confirm('¿Estás seguro de eliminar esta materia?')) return;

        storage.deleteMateria(codigo);
        this.loadPensum();
        App.showAlert('Materia eliminada', 'success');
    },

    /**
     * Simulate losing a course
     */
    simulateLoss(codigo) {
        const materia = this.materias.find(m => m.codigo === codigo);
        if (!materia) return;

        // Find all courses that depend on this one
        const affected = this.getAffectedCourses(codigo);

        if (affected.length === 0) {
            App.showAlert(`Perder ${materia.nombre} no afectará otras materias`, 'info');
            return;
        }

        const affectedNames = affected.map(m => m.nombre).join(', ');
        const message = `Si pierdes ${materia.nombre}, las siguientes materias se verán afectadas:\n\n${affectedNames}\n\nTotal: ${affected.length} materias`;
        
        App.showAlert(message, 'warning');
    },

    /**
     * Get all courses affected by losing a specific course
     */
    getAffectedCourses(codigo) {
        const affected = [];
        const visited = new Set();

        const findDependents = (code) => {
            this.materias.forEach(m => {
                if (!visited.has(m.codigo) && m.prerrequisitos?.includes(code)) {
                    visited.add(m.codigo);
                    affected.push(m);
                    findDependents(m.codigo);
                }
            });
        };

        findDependents(codigo);
        return affected;
    },

    /**
     * Export pensum as JSON
     */
    exportPensum() {
        const data = storage.exportAll();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `pensum-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        App.showAlert('Pensum exportado correctamente', 'success');
    },

    /**
     * Handle file import
     */
    handleImport(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                this.importPensum(data);
            } catch (error) {
                App.showAlert('Error al leer el archivo: formato inválido', 'error');
            }
        };
        reader.readAsText(file);
        
        // Reset input
        event.target.value = '';
    },

    /**
     * Import pensum from JSON data
     */
    importPensum(data) {
        // Check if it's a valid export format
        if (data.data && data.version) {
            // Full export format
            const result = storage.importAll(data, { overwrite: false });
            if (result.success) {
                this.loadPensum();
                App.showAlert(`Importado: ${result.imported.join(', ')}`, 'success');
            } else {
                App.showAlert('Error al importar: ' + result.errors.join(', '), 'error');
            }
        } else if (Array.isArray(data)) {
            // Simple array of materias
            data.forEach(m => storage.saveMateria(m));
            this.loadPensum();
            App.showAlert(`${data.length} materias importadas`, 'success');
        } else {
            App.showAlert('Formato de archivo no reconocido', 'error');
        }
    },

    /**
     * Filter view by status
     */
    filterByStatus(status) {
        const cards = document.querySelectorAll('.course-card');
        cards.forEach(card => {
            const codigo = card.dataset.codigo;
            const materia = this.materias.find(m => m.codigo === codigo);
            
            if (!status || materia?.estado === status) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    },

    /**
     * Search courses
     */
    search(query) {
        const normalizedQuery = query.toLowerCase().trim();
        const cards = document.querySelectorAll('.course-card');
        
        cards.forEach(card => {
            const codigo = card.dataset.codigo;
            const materia = this.materias.find(m => m.codigo === codigo);
            
            if (!normalizedQuery || 
                materia?.nombre.toLowerCase().includes(normalizedQuery) ||
                materia?.codigo.toLowerCase().includes(normalizedQuery)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    }
};

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Pensum };
}
