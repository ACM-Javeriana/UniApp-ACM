/**
 * Schedule Module - Handles schedule generation and management
 */

const Schedule = {
    clases: [],
    franjas: [],
    combinations: [],
    selectedCombination: null,
    filters: {
        maxGaps: null,
        preferredDays: [],
        avoidEarlyMorning: false,
        avoidLateNight: false
    },
    WARN_THRESHOLD: 1000,

    /**
     * Initialize the schedule view
     */
    init() {
        this.loadData();
        this.setupEventListeners();
        this.renderClasesList();
        this.renderFranjasGrid();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        window.addEventListener('datasynced', () => {
            this.loadData();
            this.renderClasesList();
            this.renderFranjasGrid();
        });
    },

    /**
     * Load data from storage
     */
    loadData() {
        this.clases = storage.getClases();
        this.franjas = storage.getFranjas();
        this.selectedCombination = storage.getSelectedSchedule();
    },

    /**
     * Render the list of class sections
     */
    renderClasesList() {
        const container = document.getElementById('clasesList');
        if (!container) return;

        // Get enrolled materias
        const materias = storage.getMaterias().filter(m => m.estado === 'enrolled');
        
        if (materias.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <p>No hay materias inscritas</p>
                    <p class="text-sm mt-2">Marca materias como "Inscrita" en el pensum</p>
                </div>
            `;
            return;
        }

        // Group clases by materia
        const clasesByMateria = {};
        this.clases.forEach(c => {
            if (!clasesByMateria[c.codigo_materia]) {
                clasesByMateria[c.codigo_materia] = [];
            }
            clasesByMateria[c.codigo_materia].push(c);
        });

        let html = '';
        materias.forEach(m => {
            const clases = clasesByMateria[m.codigo] || [];
            html += `
                <div class="materia-section bg-white dark:bg-gray-800 rounded-lg p-4 mb-4 shadow transition-colors">
                    <div class="flex justify-between items-center mb-3">
                        <div>
                            <h3 class="font-semibold text-gray-800 dark:text-gray-100">${m.nombre}</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">${m.codigo} • ${m.creditos} cr</p>
                        </div>
                        <button onclick="Schedule.showAddClaseModal('${m.codigo}')"
                                class="px-3 py-1 text-sm bg-accent text-white rounded hover:bg-accent-dark">
                            + Sección
                        </button>
                    </div>
                    <div class="space-y-2">
                        ${clases.length > 0 ? 
                            clases.map(c => this.renderClaseCard(c)).join('') :
                            '<p class="text-sm text-gray-400 dark:text-gray-500">No hay secciones agregadas</p>'
                        }
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    },

    /**
     * Render a class section card
     */
    renderClaseCard(clase) {
        const dayNames = {
            'monday': 'Lun',
            'tuesday': 'Mar',
            'wednesday': 'Mié',
            'thursday': 'Jue',
            'friday': 'Vie',
            'saturday': 'Sáb'
        };

        const horarios = (clase.bloques_horario || []).map(b => 
            `${dayNames[b.dia] || b.dia} ${b.hora_inicio}-${b.hora_fin}`
        ).join(', ');

        return `
            <div class="clase-card bg-gray-50 dark:bg-gray-700 rounded p-3 border-l-4 border-accent transition-colors">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="font-medium dark:text-gray-100">${clase.nrc || clase.seccion || 'Sección'}</p>
                        <p class="text-sm text-gray-600 dark:text-gray-300">${clase.profesor || 'Sin profesor'}</p>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">${horarios || 'Sin horario'}</p>
                        ${clase.aula ? `<p class="text-xs text-gray-400 dark:text-gray-500">Aula: ${clase.aula}</p>` : ''}
                    </div>
                    <div class="flex gap-1">
                        <button onclick="Schedule.editClase('${clase.id}')"
                                class="p-1.5 text-gray-400 hover:text-accent rounded"
                                title="Editar">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                        </button>
                        <button onclick="Schedule.deleteClase('${clase.id}')"
                                class="p-1.5 text-gray-400 hover:text-red-500 rounded"
                                title="Eliminar">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Render the franjas (time preferences) grid
     */
    renderFranjasGrid() {
        const container = document.getElementById('franjasGrid');
        if (!container) return;

        const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        const dayNames = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
        const hours = [];
        for (let h = 6; h <= 21; h++) {
            hours.push(`${h.toString().padStart(2, '0')}:00`);
        }

        // Create grid
        let html = '<div class="grid grid-cols-7 gap-1 text-xs">';
        
        // Header
        html += '<div class="h-8"></div>';
        dayNames.forEach(d => {
            html += `<div class="h-8 flex items-center justify-center font-medium text-gray-600">${d}</div>`;
        });

        // Time slots
        hours.forEach(hour => {
            html += `<div class="h-8 flex items-center justify-end pr-2 text-gray-400">${hour}</div>`;
            
            days.forEach(day => {
                const franja = this.franjas.find(f => 
                    f.dia === day && 
                    f.hora_inicio <= hour && 
                    f.hora_fin > hour
                );
                
                const bgClass = franja ? 
                    (franja.tipo === 'blocked' ? 'bg-red-200 hover:bg-red-300' : 'bg-green-200 hover:bg-green-300') :
                    'bg-gray-100 hover:bg-gray-200';
                
                html += `
                    <div class="h-8 ${bgClass} rounded cursor-pointer transition-colors"
                         onclick="Schedule.toggleFranja('${day}', '${hour}')"
                         title="${franja ? (franja.tipo === 'blocked' ? 'Bloqueado' : 'Preferido') : 'Click para marcar'}">
                    </div>
                `;
            });
        });

        html += '</div>';
        
        // Legend
        html += `
            <div class="flex gap-4 mt-4 text-sm">
                <div class="flex items-center gap-2">
                    <div class="w-4 h-4 bg-red-200 rounded"></div>
                    <span>Bloqueado</span>
                </div>
                <div class="flex items-center gap-2">
                    <div class="w-4 h-4 bg-green-200 rounded"></div>
                    <span>Preferido</span>
                </div>
                <div class="flex items-center gap-2">
                    <div class="w-4 h-4 bg-gray-100 rounded border"></div>
                    <span>Disponible</span>
                </div>
            </div>
        `;

        container.innerHTML = html;
    },

    /**
     * Toggle a franja (cycle: none -> blocked -> preferred -> none)
     */
    toggleFranja(day, hour) {
        const existing = this.franjas.find(f => 
            f.dia === day && 
            f.hora_inicio === hour
        );

        if (existing) {
            if (existing.tipo === 'blocked') {
                // Change to preferred
                existing.tipo = 'preferred';
                storage.saveFranjas(this.franjas);
            } else {
                // Remove
                this.franjas = this.franjas.filter(f => f.id !== existing.id);
                storage.saveFranjas(this.franjas);
            }
        } else {
            // Add as blocked
            const nextHour = parseInt(hour) + 1;
            const newFranja = {
                id: `franja_${Date.now()}`,
                dia: day,
                hora_inicio: hour,
                hora_fin: `${nextHour.toString().padStart(2, '0')}:00`,
                tipo: 'blocked'
            };
            this.franjas.push(newFranja);
            storage.saveFranjas(this.franjas);
        }

        this.renderFranjasGrid();
    },

    /**
     * Show add class section modal
     */
    showAddClaseModal(codigoMateria) {
        const modal = document.getElementById('addClaseModal');
        if (!modal) return;

        document.getElementById('claseCodigoMateria').value = codigoMateria;
        document.getElementById('claseId').value = '';
        document.getElementById('claseForm').reset();
        document.getElementById('claseCodigoMateria').value = codigoMateria;
        
        // Clear time blocks
        document.getElementById('bloquesContainer').innerHTML = '';
        this.addTimeBlock();

        modal.classList.remove('hidden');
    },

    /**
     * Add a time block input to the form
     */
    addTimeBlock() {
        const container = document.getElementById('bloquesContainer');
        const blockId = Date.now();
        
        const html = `
            <div class="time-block flex gap-2 items-center mb-2" data-block-id="${blockId}">
                <select class="block-day flex-1 rounded border-gray-300 text-sm">
                    <option value="monday">Lunes</option>
                    <option value="tuesday">Martes</option>
                    <option value="wednesday">Miércoles</option>
                    <option value="thursday">Jueves</option>
                    <option value="friday">Viernes</option>
                    <option value="saturday">Sábado</option>
                </select>
                <input type="time" class="block-start rounded border-gray-300 text-sm" value="07:00">
                <span>-</span>
                <input type="time" class="block-end rounded border-gray-300 text-sm" value="09:00">
                <button type="button" onclick="Schedule.removeTimeBlock(${blockId})"
                        class="p-1 text-red-500 hover:text-red-700">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', html);
    },

    /**
     * Remove a time block
     */
    removeTimeBlock(blockId) {
        const block = document.querySelector(`[data-block-id="${blockId}"]`);
        if (block) block.remove();
    },

    /**
     * Save class section from modal
     */
    saveClase() {
        const codigoMateria = document.getElementById('claseCodigoMateria').value;
        const claseId = document.getElementById('claseId').value;
        
        // Gather time blocks
        const bloques = [];
        document.querySelectorAll('.time-block').forEach(block => {
            bloques.push({
                dia: block.querySelector('.block-day').value,
                hora_inicio: block.querySelector('.block-start').value,
                hora_fin: block.querySelector('.block-end').value
            });
        });
        const dayNames = {
            monday: 'lunes', tuesday: 'martes', wednesday: 'miércoles',
            thursday: 'jueves', friday: 'viernes', saturday: 'sábado'
        };

        for (const b of bloques) {
            if (!b.hora_inicio || !b.hora_fin || b.hora_inicio >= b.hora_fin) {
                App.showAlert({
                    title: 'Horario inválido',
                    detail: `El bloque del ${dayNames[b.dia] || b.dia} debe terminar después de comenzar.`
                }, 'error');
                return;
            }
        }

        const overlaps = (a, b) => a.dia === b.dia && a.hora_inicio < b.hora_fin && b.hora_inicio < a.hora_fin;

        for (let i = 0; i < bloques.length; i++) {
            for (let j = i + 1; j < bloques.length; j++) {
                if (overlaps(bloques[i], bloques[j])) {
                    App.showAlert({
                        title: 'Bloques en conflicto',
                        detail: 'Dos bloques de esta misma clase se cruzan en el mismo día.'
                    }, 'error');
                    return;
                }
            }
        }

        for (const newBloque of bloques) {
            for (const existingClase of this.clases) {
                if (existingClase.id === claseId) continue;
                for (const eb of (existingClase.bloques_horario || [])) {
                    if (overlaps(newBloque, eb)) {
                        const materia = storage.getMateria(existingClase.codigo_materia);
                        const nombre = materia ? materia.nombre : existingClase.codigo_materia;
                        App.showAlert({
                            title: 'Conflicto de horario',
                            detail: `El ${dayNames[eb.dia] || eb.dia} de ${eb.hora_inicio} a ${eb.hora_fin} ya está ocupado por "${nombre}".`
                        }, 'error');
                        return;
                    }
                }
            }
        }

        const clase = {
            id: claseId || undefined,
            codigo_materia: codigoMateria,
            nrc: document.getElementById('claseNRC').value,
            seccion: document.getElementById('claseSeccion').value,
            profesor: document.getElementById('claseProfesor').value,
            aula: document.getElementById('claseAula').value,
            bloques_horario: bloques
        };

        storage.saveClase(clase);
        this.loadData();
        this.renderClasesList();
        this.hideAddClaseModal();
        App.showAlert('Sección guardada', 'success');
    },

    /**
     * Edit a class section
     */
    editClase(id) {
        const clase = this.clases.find(c => c.id === id);
        if (!clase) return;

        this.showAddClaseModal(clase.codigo_materia);
        
        document.getElementById('claseId').value = clase.id;
        document.getElementById('claseNRC').value = clase.nrc || '';
        document.getElementById('claseSeccion').value = clase.seccion || '';
        document.getElementById('claseProfesor').value = clase.profesor || '';
        document.getElementById('claseAula').value = clase.aula || '';

        // Clear and rebuild time blocks
        const container = document.getElementById('bloquesContainer');
        container.innerHTML = '';
        
        (clase.bloques_horario || []).forEach(bloque => {
            this.addTimeBlock();
            const blocks = container.querySelectorAll('.time-block');
            const lastBlock = blocks[blocks.length - 1];
            lastBlock.querySelector('.block-day').value = bloque.dia;
            lastBlock.querySelector('.block-start').value = bloque.hora_inicio;
            lastBlock.querySelector('.block-end').value = bloque.hora_fin;
        });

        if ((clase.bloques_horario || []).length === 0) {
            this.addTimeBlock();
        }
    },

    /**
     * Delete a class section
     */
    deleteClase(id) {
        if (!confirm('¿Eliminar esta sección?')) return;
        
        storage.deleteClase(id);
        this.loadData();
        this.renderClasesList();
        App.showAlert('Sección eliminada', 'success');
    },

    /**
     * Hide add class modal
     */
    hideAddClaseModal() {
        const modal = document.getElementById('addClaseModal');
        if (modal) modal.classList.add('hidden');
    },

    /**
     * Generate all possible schedule combinations
     */
    async generateCombinations() {
        const materiasInscritas = storage.getMaterias().filter(m => m.estado === 'enrolled');
        
        if (materiasInscritas.length === 0) {
            App.showAlert('No hay materias inscritas', 'warning');
            return;
        }

        // Check if each materia has at least one clase
        const materiasSinClases = materiasInscritas.filter(m => 
            !this.clases.some(c => c.codigo_materia === m.codigo)
        );

        if (materiasSinClases.length > 0) {
            const nombres = materiasSinClases.map(m => m.nombre).join(', ');
            App.showAlert(`Faltan secciones para: ${nombres}`, 'warning');
            return;
        }

        // Show loading
        const resultsContainer = document.getElementById('combinationsResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="text-center py-8">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-accent mx-auto"></div>
                    <p class="mt-2 text-gray-500">Generando combinaciones...</p>
                </div>
            `;
        }

        // Generate combinations using backtracking
        await new Promise(resolve => setTimeout(resolve, 10)); // Allow UI update
        
        const clasesByMateria = {};
        materiasInscritas.forEach(m => {
            clasesByMateria[m.codigo] = this.clases.filter(c => c.codigo_materia === m.codigo);
        });

        this.combinations = [];
        const codigosList = Object.keys(clasesByMateria);
        
        // Backtracking algorithm
        const backtrack = (index, current) => {
            // Check limit
            if (this.combinations.length >= 10000) return;

            if (index === codigosList.length) {
                // Found a valid combination
                this.combinations.push([...current]);
                return;
            }

            const codigo = codigosList[index];
            const clases = clasesByMateria[codigo];

            for (const clase of clases) {
                if (!this.hasConflict(current, clase)) {
                    current.push(clase);
                    backtrack(index + 1, current);
                    current.pop();
                }
            }
        };

        backtrack(0, []);

        // Filter by franjas and preferences
        this.combinations = this.combinations.filter(comb => this.passesFilters(comb));

        // Show warning if many combinations
        if (this.combinations.length >= this.WARN_THRESHOLD) {
            App.showAlert(
                `Se encontraron ${this.combinations.length} combinaciones. Considera agregar más filtros.`,
                'warning'
            );
        }

        this.renderCombinations();
    },

    /**
     * Check if a clase conflicts with existing clases in a combination
     */
    hasConflict(combination, newClase) {
        for (const existingClase of combination) {
            for (const block1 of existingClase.bloques_horario || []) {
                for (const block2 of newClase.bloques_horario || []) {
                    if (block1.dia === block2.dia) {
                        // Check time overlap
                        const start1 = this.timeToMinutes(block1.hora_inicio);
                        const end1 = this.timeToMinutes(block1.hora_fin);
                        const start2 = this.timeToMinutes(block2.hora_inicio);
                        const end2 = this.timeToMinutes(block2.hora_fin);

                        if (!(end1 <= start2 || end2 <= start1)) {
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    },

    /**
     * Check if a combination passes all filters
     */
    passesFilters(combination) {
        // Check blocked franjas
        for (const clase of combination) {
            for (const block of clase.bloques_horario || []) {
                const blockedFranja = this.franjas.find(f => 
                    f.tipo === 'blocked' &&
                    f.dia === block.dia &&
                    this.timesOverlap(
                        f.hora_inicio, f.hora_fin,
                        block.hora_inicio, block.hora_fin
                    )
                );
                if (blockedFranja) return false;
            }
        }

        // Check other filters
        if (this.filters.avoidEarlyMorning) {
            for (const clase of combination) {
                for (const block of clase.bloques_horario || []) {
                    if (this.timeToMinutes(block.hora_inicio) < this.timeToMinutes('08:00')) {
                        return false;
                    }
                }
            }
        }

        if (this.filters.avoidLateNight) {
            for (const clase of combination) {
                for (const block of clase.bloques_horario || []) {
                    if (this.timeToMinutes(block.hora_fin) > this.timeToMinutes('20:00')) {
                        return false;
                    }
                }
            }
        }

        return true;
    },

    /**
     * Check if two time ranges overlap
     */
    timesOverlap(start1, end1, start2, end2) {
        const s1 = this.timeToMinutes(start1);
        const e1 = this.timeToMinutes(end1);
        const s2 = this.timeToMinutes(start2);
        const e2 = this.timeToMinutes(end2);
        return !(e1 <= s2 || e2 <= s1);
    },

    /**
     * Convert time string to minutes
     */
    timeToMinutes(time) {
        const [h, m] = time.split(':').map(Number);
        return h * 60 + m;
    },

    /**
     * Render combination results
     */
    renderCombinations() {
        const container = document.getElementById('combinationsResults');
        if (!container) return;

        if (this.combinations.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <svg class="w-12 h-12 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p>No se encontraron combinaciones válidas</p>
                    <p class="text-sm mt-1">Revisa los horarios y las franjas bloqueadas</p>
                </div>
            `;
            return;
        }

        // Sort by score (prefer combinations with preferred franjas)
        this.combinations.sort((a, b) => this.scoreCombination(b) - this.scoreCombination(a));

        // Show first 20 combinations
        const toShow = this.combinations.slice(0, 20);
        
        let html = `
            <div class="mb-4 text-sm text-gray-600 dark:text-gray-400">
                ${this.combinations.length} combinaciones encontradas
                ${this.combinations.length > 20 ? ' (mostrando las mejores 20)' : ''}
            </div>
        `;

        toShow.forEach((comb, i) => {
            html += `
                <div class="combination-card bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                     onclick="Schedule.selectCombination(${i})">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-medium dark:text-gray-100">Opción ${i + 1}</span>
                        <span class="text-sm text-gray-500 dark:text-gray-400">Puntuación: ${this.scoreCombination(comb)}</span>
                    </div>
                    <div class="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
                        ${comb.map(clase => {
                            const materia = storage.getMaterias().find(m => m.codigo === clase.codigo_materia);
                            return `
                                <div class="bg-white dark:bg-gray-800 p-2 rounded border dark:border-gray-600 transition-colors">
                                    <p class="font-medium truncate dark:text-gray-100">${materia?.nombre || clase.codigo_materia}</p>
                                    <p class="text-xs text-gray-500 dark:text-gray-400">${clase.nrc || clase.seccion} - ${clase.profesor || 'TBA'}</p>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    },

    /**
     * Score a combination (higher is better)
     */
    scoreCombination(combination) {
        let score = 100;

        for (const clase of combination) {
            for (const block of clase.bloques_horario || []) {
                // Bonus for preferred franjas
                const preferredFranja = this.franjas.find(f =>
                    f.tipo === 'preferred' &&
                    f.dia === block.dia &&
                    this.timesOverlap(
                        f.hora_inicio, f.hora_fin,
                        block.hora_inicio, block.hora_fin
                    )
                );
                if (preferredFranja) score += 10;

                // Penalty for early morning
                if (this.timeToMinutes(block.hora_inicio) < this.timeToMinutes('08:00')) {
                    score -= 5;
                }

                // Penalty for late night
                if (this.timeToMinutes(block.hora_fin) > this.timeToMinutes('19:00')) {
                    score -= 3;
                }
            }
        }

        return score;
    },

    /**
     * Select a combination
     */
    selectCombination(index) {
        this.selectedCombination = this.combinations[index];
        storage.saveSelectedSchedule(this.selectedCombination);
        this.renderScheduleGrid(this.selectedCombination);
        App.showAlert('Horario seleccionado', 'success');
    },

    /**
     * Render the schedule grid for a combination
     */
    renderScheduleGrid(combination) {
        const container = document.getElementById('scheduleGrid');
        if (!container) return;

        if (!combination || combination.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <p>Selecciona una combinación para ver el horario</p>
                </div>
            `;
            return;
        }

        const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        const dayNames = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
        
        // Find time range
        let minHour = 24, maxHour = 0;
        combination.forEach(clase => {
            (clase.bloques_horario || []).forEach(block => {
                const startH = parseInt(block.hora_inicio);
                const endH = parseInt(block.hora_fin);
                minHour = Math.min(minHour, startH);
                maxHour = Math.max(maxHour, endH);
            });
        });
        
        minHour = Math.max(6, minHour - 1);
        maxHour = Math.min(22, maxHour + 1);

        // Build grid
        let html = '<div class="schedule-grid">';
        html += '<div class="grid grid-cols-7 gap-1">';
        
        // Header
        html += '<div class="h-10"></div>';
        dayNames.forEach(d => {
            html += `<div class="h-10 flex items-center justify-center font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded transition-colors">${d}</div>`;
        });

        // Time slots
        for (let h = minHour; h < maxHour; h++) {
            const hour = `${h.toString().padStart(2, '0')}:00`;
            html += `<div class="h-16 flex items-start justify-end pr-2 text-xs text-gray-400 dark:text-gray-500 pt-1">${hour}</div>`;
            
            days.forEach(day => {
                // Find clase block for this slot
                const claseBlock = this.findClaseForSlot(combination, day, hour);
                
                if (claseBlock) {
                    const { clase, block, isStart } = claseBlock;
                    const materia = storage.getMaterias().find(m => m.codigo === clase.codigo_materia);
                    
                    if (isStart) {
                        const duration = this.timeToMinutes(block.hora_fin) - this.timeToMinutes(block.hora_inicio);
                        const slots = Math.ceil(duration / 60);
                        const colors = this.getColorForMateria(clase.codigo_materia);
                        
                        html += `
                            <div class="h-16 ${colors.bg} ${colors.border} border-l-4 rounded p-1 overflow-hidden"
                                 style="grid-row: span ${slots};">
                                <p class="font-medium text-xs truncate ${colors.text}">${materia?.nombre || clase.codigo_materia}</p>
                                <p class="text-xs text-gray-600 truncate">${clase.nrc || ''}</p>
                                <p class="text-xs text-gray-500 truncate">${clase.aula || ''}</p>
                            </div>
                        `;
                    }
                    // Skip cells covered by multi-slot blocks
                } else {
                    html += '<div class="h-16 bg-gray-50 dark:bg-gray-700 rounded transition-colors"></div>';
                }
            });
        }

        html += '</div></div>';

        // Legend
        html += '<div class="flex flex-wrap gap-3 mt-4">';
        combination.forEach(clase => {
            const materia = storage.getMaterias().find(m => m.codigo === clase.codigo_materia);
            const colors = this.getColorForMateria(clase.codigo_materia);
            html += `
                <div class="flex items-center gap-2">
                    <div class="w-4 h-4 ${colors.bg} ${colors.border} border-l-4 rounded"></div>
                    <span class="text-sm">${materia?.nombre || clase.codigo_materia}</span>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    },

    /**
     * Find if there's a clase block for a given day/hour slot
     */
    findClaseForSlot(combination, day, hour) {
        const hourMinutes = this.timeToMinutes(hour);
        
        for (const clase of combination) {
            for (const block of clase.bloques_horario || []) {
                if (block.dia === day) {
                    const startMinutes = this.timeToMinutes(block.hora_inicio);
                    const endMinutes = this.timeToMinutes(block.hora_fin);
                    
                    if (hourMinutes >= startMinutes && hourMinutes < endMinutes) {
                        return {
                            clase,
                            block,
                            isStart: hourMinutes === startMinutes
                        };
                    }
                }
            }
        }
        return null;
    },

    /**
     * Get color classes for a materia
     */
    getColorForMateria(codigo) {
        const materia = storage.getMateria(codigo);
        if (materia && materia.color && materia.color.startsWith('#')) {
            const hex = materia.color.replace('#', '');
            const r = parseInt(hex.substr(0, 2), 16);
            const g = parseInt(hex.substr(2, 2), 16);
            const b = parseInt(hex.substr(4, 2), 16);
            const bgR = Math.round(r + (255 - r) * 0.85);
            const bgG = Math.round(g + (255 - g) * 0.85);
            const bgB = Math.round(b + (255 - b) * 0.85);
            const darkBgR = Math.round(r * 0.3);
            const darkBgG = Math.round(g * 0.3);
            const darkBgB = Math.round(b * 0.3);
            return {
                bg: `bg-[rgb(${bgR},${bgG},${bgB})] dark:bg-[rgb(${darkBgR},${darkBgG},${darkBgB})]`,
                border: `border-[${materia.color}]`,
                text: `text-[${materia.color}]`
            };
        }

        const colors = [
            { bg: 'bg-blue-100', border: 'border-blue-500', text: 'text-blue-800' },
            { bg: 'bg-green-100', border: 'border-green-500', text: 'text-green-800' },
            { bg: 'bg-yellow-100', border: 'border-yellow-500', text: 'text-yellow-800' },
            { bg: 'bg-purple-100', border: 'border-purple-500', text: 'text-purple-800' },
            { bg: 'bg-pink-100', border: 'border-pink-500', text: 'text-pink-800' },
            { bg: 'bg-indigo-100', border: 'border-indigo-500', text: 'text-indigo-800' },
            { bg: 'bg-red-100', border: 'border-red-500', text: 'text-red-800' },
            { bg: 'bg-orange-100', border: 'border-orange-500', text: 'text-orange-800' },
        ];
        
        // Generate consistent color based on codigo hash
        let hash = 0;
        for (let i = 0; i < codigo.length; i++) {
            hash = ((hash << 5) - hash) + codigo.charCodeAt(i);
            hash = hash & hash;
        }
        
        return colors[Math.abs(hash) % colors.length];
    },

    /**
     * Toggle filter
     */
    toggleFilter(filterName) {
        this.filters[filterName] = !this.filters[filterName];
        const btn = document.querySelector(`[data-filter="${filterName}"]`);
        if (btn) {
            btn.classList.toggle('bg-accent');
            btn.classList.toggle('text-white');
        }
    },

    /**
     * Clear selected schedule
     */
    clearSelection() {
        this.selectedCombination = null;
        storage.removeLocal('selectedSchedule');
        this.renderScheduleGrid(null);
    }
};

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Schedule };
}
