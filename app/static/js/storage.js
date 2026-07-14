/**
 * Storage Manager - Handles localStorage and Supabase sync
 * Priority: localStorage (works offline) -> Supabase sync on auth
 */

class StorageManager {
    constructor() {
        this.prefix = 'uniapp_';
        this.supabase = null;
        this.userId = null;
        this.syncInProgress = false;
        this.localUpdatedAtKey = this.prefix + 'localUpdatedAt';
        this.lastCloudSyncAtKey = this.prefix + 'lastCloudSyncAt';
    }

    // ==================== LOCAL STORAGE ====================
    
    /**
     * Get data from localStorage
     */
    getLocal(key) {
        try {
            const data = localStorage.getItem(this.prefix + key);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.error(`Error reading ${key} from localStorage:`, error);
            return null;
        }
    }

    /**
     * Set data in localStorage
     */
    setLocal(key, value) {
        try {
            localStorage.setItem(this.prefix + key, JSON.stringify(value));
            this.markForSync(key);
            if (typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('storageChanged', { detail: { key } }));
            }
            return true;
        } catch (error) {
            console.error(`Error writing ${key} to localStorage:`, error);
            return false;
        }
    }

    /**
     * Remove data from localStorage
     */
    removeLocal(key) {
        try {
            localStorage.removeItem(this.prefix + key);
            this.markForSync(key);
            if (typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('storageChanged', { detail: { key } }));
            }
            return true;
        } catch (error) {
            console.error(`Error removing ${key} from localStorage:`, error);
            return false;
        }
    }

    /**
     * Mark a key as needing sync to server
     */
    markForSync(key) {
        const pendingSync = this.getLocal('_pendingSync') || [];
        if (!pendingSync.includes(key)) {
            pendingSync.push(key);
            localStorage.setItem(this.prefix + '_pendingSync', JSON.stringify(pendingSync));
        }
        if (this.shouldTrackLocalChange(key)) {
            localStorage.setItem(this.localUpdatedAtKey, new Date().toISOString());
        }
    }

    shouldTrackLocalChange(key) {
        return !key.startsWith('_') && key !== 'lastCloudSyncAt' && key !== 'localUpdatedAt';
    }

    /**
     * Clear pending sync markers
     */
    clearSyncMarkers() {
        localStorage.removeItem(this.prefix + '_pendingSync');
    }

    // ==================== PLANES DE ESTUDIO (STUDY PLANS) ====================

    /**
     * Get all study plans
     */
    getPlanes() {
        const planes = this.getLocal('planes');
        if (!planes || planes.length === 0) {
            // Create default plan if none exist
            const defaultPlan = {
                id: 'default',
                nombre: 'Mi Plan de Estudios',
                descripcion: 'Plan de estudios base',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            this.setLocal('planes', [defaultPlan]);
            this.setLocal('planActivo', 'default');
            this.setLocal('planPrincipal', 'default');
            return [defaultPlan];
        }
        return planes;
    }

    /**
     * Save all study plans
     */
    savePlanes(planes) {
        return this.setLocal('planes', planes);
    }

    /**
     * Get a single study plan by ID
     */
    getPlan(planId) {
        return this.getPlanes().find(p => p.id === planId);
    }

    /**
     * Get the active study plan ID
     */
    getPlanActivo() {
        const planActivo = this.getLocal('planActivo');
        if (planActivo && this.getPlan(planActivo)) {
            return planActivo;
        }

        const planPrincipal = this.getPlanPrincipal();
        this.setLocal('planActivo', planPrincipal);
        return planPrincipal;
    }

    /**
     * Set the active study plan
     */
    setPlanActivo(planId) {
        const plan = this.getPlan(planId);
        if (plan) {
            this.setLocal('planActivo', planId);
            window.dispatchEvent(new CustomEvent('planChanged', { detail: { planId } }));
            return true;
        }
        return false;
    }

    /**
     * Get the main study plan ID
     */
    getPlanPrincipal() {
        const planes = this.getPlanes();
        const planPrincipal = this.getLocal('planPrincipal');
        if (planPrincipal && planes.some(p => p.id === planPrincipal)) {
            return planPrincipal;
        }

        const fallback = planes.some(p => p.id === 'default') ? 'default' : planes[0]?.id;
        if (fallback) {
            this.setLocal('planPrincipal', fallback);
            return fallback;
        }
        return 'default';
    }

    /**
     * Set the main study plan
     */
    setPlanPrincipal(planId) {
        const plan = this.getPlan(planId);
        if (plan) {
            this.setLocal('planPrincipal', planId);
            window.dispatchEvent(new CustomEvent('planPrincipalChanged', { detail: { planId } }));
            return true;
        }
        return false;
    }

    /**
     * Create a new study plan
     */
    createPlan(nombre, descripcion = '', copiarDatosDe = null) {
        const planes = this.getPlanes();
        const id = `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        const newPlan = {
            id,
            nombre,
            descripcion,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        
        planes.push(newPlan);
        this.savePlanes(planes);
        
        // Initialize empty data for the new plan (using plan prefix format: planId_key)
        this.setLocal(`${id}_materias`, []);
        this.setLocal(`${id}_calificaciones`, []);
        this.setLocal(`${id}_clases`, []);
        
        // Optionally copy data from another plan
        if (copiarDatosDe) {
            const sourcePrefix = copiarDatosDe === 'default' ? '' : `${copiarDatosDe}_`;
            const materias = this.getLocal(`${sourcePrefix}materias`) || [];
            const calificaciones = this.getLocal(`${sourcePrefix}calificaciones`) || [];
            const clases = this.getLocal(`${sourcePrefix}clases`) || [];
            
            this.setLocal(`${id}_materias`, JSON.parse(JSON.stringify(materias)));
            this.setLocal(`${id}_calificaciones`, JSON.parse(JSON.stringify(calificaciones)));
            this.setLocal(`${id}_clases`, JSON.parse(JSON.stringify(clases)));
        }
        
        return newPlan;
    }

    /**
     * Update a study plan
     */
    updatePlan(planId, updates) {
        const planes = this.getPlanes();
        const index = planes.findIndex(p => p.id === planId);
        
        if (index >= 0) {
            planes[index] = {
                ...planes[index],
                ...updates,
                updatedAt: new Date().toISOString()
            };
            this.savePlanes(planes);
            return planes[index];
        }
        return null;
    }

    /**
     * Delete a study plan
     */
    deletePlan(planId) {
        if (planId === this.getPlanPrincipal()) {
            console.error('Cannot delete the base plan');
            return false;
        }
        
        const planes = this.getPlanes().filter(p => p.id !== planId);
        this.savePlanes(planes);
        
        // Remove associated data (using plan prefix format: planId_key)
        this.removeLocal(`${planId}_materias`);
        this.removeLocal(`${planId}_calificaciones`);
        this.removeLocal(`${planId}_clases`);
        
        const fallbackPlanId = planes.some(p => p.id === 'default') ? 'default' : planes[0]?.id;

        // If deleted plan was main, switch main plan to default or first available
        if (this.getPlanPrincipal() === planId && fallbackPlanId) {
            this.setPlanPrincipal(fallbackPlanId);
        }

        // If deleted plan was active, switch to main plan
        if (this.getPlanActivo() === planId) {
            this.setPlanActivo(this.getPlanPrincipal());
        }
        
        return true;
    }

    /**
     * Get the storage key prefix for the active plan
     */
    _getPlanPrefix() {
        const planActivo = this.getPlanActivo();
        return planActivo === 'default' ? '' : `${planActivo}_`;
    }

    /**
     * Migrate existing data to use plan-based storage (run once)
     */
    migrateToPlans() {
        const migrated = this.getLocal('_plansMigrated');
        if (migrated) return;
        
        // Ensure default plan exists
        this.getPlanes();
        
        // Existing data stays as is (for 'default' plan which uses no prefix)
        // New plans will use prefixed keys
        
        this.setLocal('_plansMigrated', true);
        console.log('Storage migrated to support multiple plans');
    }

    // ==================== MATERIAS (COURSES) ====================

    /**
     * Get all materias for the active plan
     */
    getMaterias() {
        const prefix = this._getPlanPrefix();
        return this.getLocal(`${prefix}materias`) || [];
    }

    /**
     * Save all materias for the active plan
     */
    saveMaterias(materias) {
        const prefix = this._getPlanPrefix();
        return this.setLocal(`${prefix}materias`, materias);
    }

    /**
     * Get a single materia by code
     */
    getMateria(codigo) {
        const materias = this.getMaterias();
        return materias.find(m => m.codigo === codigo);
    }

    /**
     * Add or update a materia
     */
    saveMateria(materia) {
        const materias = this.getMaterias();
        const index = materias.findIndex(m => m.codigo === materia.codigo);
        
        if (index >= 0) {
            materias[index] = { ...materias[index], ...materia };
        } else {
            materias.push(materia);
        }
        
        return this.saveMaterias(materias);
    }

    /**
     * Delete a materia
     */
    deleteMateria(codigo) {
        const materias = this.getMaterias().filter(m => m.codigo !== codigo);
        return this.saveMaterias(materias);
    }

    // ==================== CLASES (CLASS SECTIONS) ====================

    /**
     * Get all clases for the active plan
     */
    getClases() {
        const prefix = this._getPlanPrefix();
        return this.getLocal(`${prefix}clases`) || [];
    }

    /**
     * Save all clases
     */
    saveClases(clases) {
        return this.setLocal('clases', clases);
    }

    /**
     * Get clases for a specific materia
     */
    getClasesByMateria(codigoMateria) {
        return this.getClases().filter(c => c.codigo_materia === codigoMateria);
    }

    /**
     * Save all clases for the active plan
     */
    saveClases(clases) {
        const prefix = this._getPlanPrefix();
        return this.setLocal(`${prefix}clases`, clases);
    }

    /**
     * Add or update a clase
     */
    saveClase(clase) {
        const clases = this.getClases();
        const id = clase.id || `clase_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const index = clases.findIndex(c => c.id === id);
        
        const claseWithId = { ...clase, id };
        
        if (index >= 0) {
            clases[index] = claseWithId;
        } else {
            clases.push(claseWithId);
        }
        
        this.saveClases(clases);
        return claseWithId;
    }

    /**
     * Delete a clase
     */
    deleteClase(id) {
        const clases = this.getClases().filter(c => c.id !== id);
        return this.saveClases(clases);
    }

    // ==================== FRANJAS (TIME PREFERENCES) ====================

    /**
     * Get all franjas
     */
    getFranjas() {
        return this.getLocal('franjas') || [];
    }

    /**
     * Save all franjas
     */
    saveFranjas(franjas) {
        return this.setLocal('franjas', franjas);
    }

    /**
     * Add a franja
     */
    addFranja(franja) {
        const franjas = this.getFranjas();
        const id = franja.id || `franja_${Date.now()}`;
        franjas.push({ ...franja, id });
        return this.saveFranjas(franjas);
    }

    /**
     * Remove a franja
     */
    removeFranja(id) {
        const franjas = this.getFranjas().filter(f => f.id !== id);
        return this.saveFranjas(franjas);
    }

    // ==================== CALIFICACIONES (GRADES) ====================

    /**
     * Get all calificaciones for the active plan
     */
    getCalificaciones() {
        const prefix = this._getPlanPrefix();
        return this.getLocal(`${prefix}calificaciones`) || [];
    }

    /**
     * Save all calificaciones for the active plan
     */
    saveCalificaciones(calificaciones) {
        const prefix = this._getPlanPrefix();
        return this.setLocal(`${prefix}calificaciones`, calificaciones);
    }

    /**
     * Get calificacion for a specific materia
     */
    getCalificacion(codigoMateria) {
        return this.getCalificaciones().find(c => c.codigo_materia === codigoMateria);
    }

    /**
     * Save or update calificacion
     */
    saveCalificacion(calificacion) {
        const calificaciones = this.getCalificaciones();
        const index = calificaciones.findIndex(c => c.codigo_materia === calificacion.codigo_materia);
        
        const calWithTimestamp = {
            ...calificacion,
            fecha: calificacion.fecha || new Date().toISOString()
        };
        
        if (index >= 0) {
            calificaciones[index] = calWithTimestamp;
        } else {
            calificaciones.push(calWithTimestamp);
        }
        
        return this.saveCalificaciones(calificaciones);
    }

    // ==================== CONFIGURACION ====================

    /**
     * Get configuration
     */
    getConfiguracion() {
        return this.getLocal('configuracion') || {
            max_creditos_semestre: 24,
            umbral_gpa: 2.0,
            mostrar_alertas: true,
            tema: 'light'
        };
    }

    /**
     * Save configuration
     */
    saveConfiguracion(config) {
        return this.setLocal('configuracion', config);
    }

    // ==================== SELECTED SCHEDULE ====================

    /**
     * Get the currently selected schedule combination
     */
    getSelectedSchedule() {
        return this.getLocal('selectedSchedule');
    }

    /**
     * Save the selected schedule combination
     */
    saveSelectedSchedule(schedule) {
        return this.setLocal('selectedSchedule', schedule);
    }

    // ==================== SUPABASE SYNC ====================

    /**
     * Initialize Supabase client
     */
    initSupabase(supabaseClient, userId) {
        this.supabase = supabaseClient;
        this.userId = userId;
    }

    /**
     * Check if user is authenticated and sync is available
     */
    canSync() {
        return this.supabase !== null && this.userId !== null;
    }

    /**
     * Sync local data to Supabase (local wins on conflict)
     */
    async syncToServer() {
        if (!this.canSync() || this.syncInProgress) {
            return { success: false, reason: 'Cannot sync or sync in progress' };
        }

        this.syncInProgress = true;
        const results = { success: true, synced: [], errors: [] };

        try {
            // Sync each data type
            const dataTypes = ['materias', 'clases', 'franjas', 'calificaciones', 'configuracion', 'selectedSchedule'];
            
            for (const dataType of dataTypes) {
                try {
                    const localData = this.getLocal(dataType);
                    if (localData !== null) {
                        const { error } = await this.supabase
                            .from('user_data')
                            .upsert({
                                user_id: this.userId,
                                data_type: dataType,
                                data: localData,
                                updated_at: new Date().toISOString()
                            }, {
                                onConflict: 'user_id,data_type'
                            });
                        
                        if (error) throw error;
                        results.synced.push(dataType);
                    }
                } catch (error) {
                    results.errors.push({ dataType, error: error.message });
                    results.success = false;
                }
            }

            if (results.success) {
                this.clearSyncMarkers();
                const syncedAt = new Date().toISOString();
                localStorage.setItem(this.lastCloudSyncAtKey, syncedAt);
                localStorage.setItem(this.localUpdatedAtKey, syncedAt);
            }
        } catch (error) {
            results.success = false;
            results.errors.push({ error: error.message });
        } finally {
            this.syncInProgress = false;
        }

        return results;
    }

    /**
     * Load data from Supabase (only if local is empty)
     */
    async loadFromServer() {
        if (!this.canSync()) {
            return { success: false, reason: 'Cannot sync' };
        }

        const results = { success: true, loaded: [], errors: [] };

        try {
            const { data, error } = await this.supabase
                .from('user_data')
                .select('data_type, data')
                .eq('user_id', this.userId);

            if (error) throw error;

            for (const row of data || []) {
                // Only load from server if local is empty (local priority)
                const localData = this.getLocal(row.data_type);
                if (localData === null || (Array.isArray(localData) && localData.length === 0)) {
                    localStorage.setItem(this.prefix + row.data_type, JSON.stringify(row.data));
                    results.loaded.push(row.data_type);
                }
            }

            if (results.loaded.length > 0) {
                const syncedAt = new Date().toISOString();
                localStorage.setItem(this.lastCloudSyncAtKey, syncedAt);
                localStorage.setItem(this.localUpdatedAtKey, syncedAt);
            }
        } catch (error) {
            results.success = false;
            results.errors.push({ error: error.message });
        }

        return results;
    }

    /**
     * Full sync - load from server (if local empty), then push local to server
     */
    async fullSync() {
        const loadResult = await this.loadFromServer();
        const syncResult = await this.syncToServer();
        
        return {
            load: loadResult,
            sync: syncResult,
            success: loadResult.success && syncResult.success
        };
    }

    // ==================== EXPORT / IMPORT ====================

    /**
     * Export all data as JSON
     */
    exportAll() {
        return {
            version: '1.0',
            exportDate: new Date().toISOString(),
            data: {
                materias: this.getMaterias(),
                clases: this.getClases(),
                franjas: this.getFranjas(),
                calificaciones: this.getCalificaciones(),
                configuracion: this.getConfiguracion(),
                selectedSchedule: this.getSelectedSchedule()
            }
        };
    }

    /**
     * Import data from JSON (merges with existing)
     */
    importAll(exportData, options = { overwrite: false }) {
        const results = { success: true, imported: [], errors: [] };

        try {
            if (!exportData.data) {
                throw new Error('Invalid export format');
            }

            const { data } = exportData;

            // Import materias
            if (data.materias) {
                if (options.overwrite) {
                    this.saveMaterias(data.materias);
                } else {
                    // Merge: add new ones, don't overwrite existing
                    const existing = this.getMaterias();
                    const existingCodes = new Set(existing.map(m => m.codigo));
                    const newMaterias = data.materias.filter(m => !existingCodes.has(m.codigo));
                    this.saveMaterias([...existing, ...newMaterias]);
                }
                results.imported.push('materias');
            }

            // Import clases
            if (data.clases) {
                if (options.overwrite) {
                    this.saveClases(data.clases);
                } else {
                    const existing = this.getClases();
                    const existingIds = new Set(existing.map(c => c.id));
                    const newClases = data.clases.filter(c => !existingIds.has(c.id));
                    this.saveClases([...existing, ...newClases]);
                }
                results.imported.push('clases');
            }

            // Import franjas
            if (data.franjas) {
                if (options.overwrite) {
                    this.saveFranjas(data.franjas);
                } else {
                    const existing = this.getFranjas();
                    this.saveFranjas([...existing, ...data.franjas]);
                }
                results.imported.push('franjas');
            }

            // Import calificaciones
            if (data.calificaciones) {
                if (options.overwrite) {
                    this.saveCalificaciones(data.calificaciones);
                } else {
                    const existing = this.getCalificaciones();
                    const existingCodes = new Set(existing.map(c => c.codigo_materia));
                    const newCals = data.calificaciones.filter(c => !existingCodes.has(c.codigo_materia));
                    this.saveCalificaciones([...existing, ...newCals]);
                }
                results.imported.push('calificaciones');
            }

            // Import configuracion (always overwrite if provided)
            if (data.configuracion) {
                this.saveConfiguracion(data.configuracion);
                results.imported.push('configuracion');
            }

        } catch (error) {
            results.success = false;
            results.errors.push(error.message);
        }

        return results;
    }

    /**
     * Clear all local data
     */
    clearAll() {
        const keys = ['materias', 'clases', 'franjas', 'calificaciones', 'configuracion', 'selectedSchedule', '_pendingSync'];
        keys.forEach(key => localStorage.removeItem(this.prefix + key));
    }

    // ==================== ALIASES ====================
    
    // Shorthand aliases for common methods
    getConfig() { return this.getConfiguracion(); }
    saveConfig(config) { return this.saveConfiguracion(config); }
}

// ==================== HISTORY MANAGER ====================

/**
 * History Manager - Handles undo/redo functionality
 * Tracks changes to materias and calificaciones
 */
class HistoryManager {
    constructor(storageManager) {
        this.storage = storageManager;
        this.historyKey = 'uniapp_history';
        this.maxEntries = 50;
        this.history = this.loadHistory();
        this.currentIndex = this.history.length - 1;
        this.isUndoRedo = false; // Flag to prevent recording during undo/redo
    }

    /**
     * Load history from localStorage
     */
    loadHistory() {
        try {
            const data = localStorage.getItem(this.historyKey);
            return data ? JSON.parse(data) : [];
        } catch (error) {
            console.error('Error loading history:', error);
            return [];
        }
    }

    /**
     * Save history to localStorage
     */
    saveHistory() {
        try {
            // Trim history if exceeds max
            if (this.history.length > this.maxEntries) {
                this.history = this.history.slice(-this.maxEntries);
                this.currentIndex = this.history.length - 1;
            }
            localStorage.setItem(this.historyKey, JSON.stringify(this.history));
        } catch (error) {
            console.error('Error saving history:', error);
        }
    }

    /**
     * Generate unique ID for history entry
     */
    generateId() {
        return `hist_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Push a new history entry
     * @param {string} action - Action type (materia:add, materia:update, etc.)
     * @param {string} description - Human-readable description
     * @param {object} before - State before change
     * @param {object} after - State after change
     * @param {array} batch - For batch operations, array of {type, codigo, before, after}
     */
    push(action, description, before, after, batch = null) {
        if (this.isUndoRedo) return; // Don't record during undo/redo

        // If we're not at the end of history, remove future entries
        if (this.currentIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.currentIndex + 1);
        }

        const entry = {
            id: this.generateId(),
            timestamp: new Date().toISOString(),
            action,
            description,
            before,
            after,
            batch
        };

        this.history.push(entry);
        this.currentIndex = this.history.length - 1;
        this.saveHistory();
        
        // Dispatch event for UI updates
        window.dispatchEvent(new CustomEvent('historyChanged', { 
            detail: { canUndo: this.canUndo(), canRedo: this.canRedo() }
        }));
    }

    /**
     * Check if undo is possible
     */
    canUndo() {
        return this.currentIndex >= 0;
    }

    /**
     * Check if redo is possible
     */
    canRedo() {
        return this.currentIndex < this.history.length - 1;
    }

    /**
     * Undo the last action
     */
    undo() {
        if (!this.canUndo()) return false;

        this.isUndoRedo = true;
        const entry = this.history[this.currentIndex];

        try {
            if (entry.batch) {
                // Batch operation - restore all items
                entry.batch.forEach(item => {
                    this.restoreState(item.type, item.before);
                });
            } else {
                // Single operation
                if (entry.before.materia !== undefined) {
                    this.restoreState('materia', entry.before.materia);
                }
                if (entry.before.calificacion !== undefined) {
                    this.restoreState('calificacion', entry.before.calificacion);
                }
            }

            this.currentIndex--;
            
            // Dispatch event for UI updates
            window.dispatchEvent(new CustomEvent('historyChanged', { 
                detail: { canUndo: this.canUndo(), canRedo: this.canRedo(), action: 'undo' }
            }));
            
            return true;
        } catch (error) {
            console.error('Error during undo:', error);
            return false;
        } finally {
            this.isUndoRedo = false;
        }
    }

    /**
     * Redo the last undone action
     */
    redo() {
        if (!this.canRedo()) return false;

        this.isUndoRedo = true;
        this.currentIndex++;
        const entry = this.history[this.currentIndex];

        try {
            if (entry.batch) {
                // Batch operation - apply all items
                entry.batch.forEach(item => {
                    this.restoreState(item.type, item.after);
                });
            } else {
                // Single operation
                if (entry.after.materia !== undefined) {
                    this.restoreState('materia', entry.after.materia);
                }
                if (entry.after.calificacion !== undefined) {
                    this.restoreState('calificacion', entry.after.calificacion);
                }
            }
            
            // Dispatch event for UI updates
            window.dispatchEvent(new CustomEvent('historyChanged', { 
                detail: { canUndo: this.canUndo(), canRedo: this.canRedo(), action: 'redo' }
            }));
            
            return true;
        } catch (error) {
            console.error('Error during redo:', error);
            this.currentIndex--;
            return false;
        } finally {
            this.isUndoRedo = false;
        }
    }

    /**
     * Restore state for a specific type
     */
    restoreState(type, state) {
        if (type === 'materia') {
            if (state === null) {
                // Item was added, so we need to remove it - but we need the codigo
                // This case is handled by storing the full object in 'after' when adding
            } else {
                const materias = this.storage.getMaterias();
                const index = materias.findIndex(m => m.codigo === state.codigo);
                
                if (state._deleted) {
                    // Item should be deleted
                    if (index >= 0) {
                        materias.splice(index, 1);
                    }
                } else if (index >= 0) {
                    // Update existing
                    materias[index] = state;
                } else {
                    // Re-add deleted item
                    materias.push(state);
                }
                
                this.storage.saveMaterias(materias);
            }
        } else if (type === 'calificacion') {
            if (state === null) {
                // No grade existed before
            } else {
                const calificaciones = this.storage.getCalificaciones();
                const index = calificaciones.findIndex(c => c.codigo_materia === state.codigo_materia);
                
                if (state._deleted) {
                    if (index >= 0) {
                        calificaciones.splice(index, 1);
                    }
                } else if (index >= 0) {
                    calificaciones[index] = state;
                } else {
                    calificaciones.push(state);
                }
                
                this.storage.saveCalificaciones(calificaciones);
            }
        }
    }

    /**
     * Get history entries for display
     */
    getHistory() {
        return this.history.map((entry, index) => ({
            ...entry,
            isCurrent: index === this.currentIndex,
            canRestore: index <= this.currentIndex
        }));
    }

    /**
     * Get recent history (last N entries from current position)
     */
    getRecentHistory(count = 10) {
        const start = Math.max(0, this.currentIndex - count + 1);
        return this.history.slice(start, this.currentIndex + 1).reverse();
    }

    /**
     * Clear all history
     */
    clearHistory() {
        this.history = [];
        this.currentIndex = -1;
        localStorage.removeItem(this.historyKey);
        
        window.dispatchEvent(new CustomEvent('historyChanged', { 
            detail: { canUndo: false, canRedo: false }
        }));
    }

    /**
     * Get human-readable time ago string
     */
    static timeAgo(timestamp) {
        const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
        
        if (seconds < 60) return 'Hace un momento';
        if (seconds < 3600) return `Hace ${Math.floor(seconds / 60)} min`;
        if (seconds < 86400) return `Hace ${Math.floor(seconds / 3600)} horas`;
        return `Hace ${Math.floor(seconds / 86400)} días`;
    }
}

// Global instance
const storage = new StorageManager();
const historyManager = new HistoryManager(storage);

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { StorageManager, storage, HistoryManager, historyManager };
}
