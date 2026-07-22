/**
 * Main App Module - Entry point and global utilities
 */

const App = {
    /**
     * Initialize the application
     */
    async init() {
        console.log('Uni-App initializing...');
        
        // Initialize auth (will work in offline mode if no credentials)
        await this.initAuth();
        
        // Setup global event listeners
        this.setupEventListeners();
        this.updateGlobalGPA();
        
        // Initialize page-specific modules
        this.initPage();
        
        // Setup service worker for PWA (optional)
        this.registerServiceWorker();
        
        console.log('Uni-App ready!');
    },

    /**
     * Initialize authentication
     */
    async initAuth() {
        // Get Supabase credentials from meta tags or config
        const supabaseUrl = document.querySelector('meta[name="supabase-url"]')?.content;
        const supabaseKey = document.querySelector('meta[name="supabase-key"]')?.content;
        
        if (supabaseUrl && supabaseKey) {
            await auth.init(supabaseUrl, supabaseKey);
        }
        
        // Update UI based on auth state
        auth.onAuthChange((user) => this.updateAuthUI(user));
    },

    /**
     * Update UI based on authentication state
     */
    updateAuthUI(user) {
        const authButton = document.getElementById('authButton');
        const userInfo = document.getElementById('userInfo');
        const syncStatus = document.getElementById('syncStatus');
        if (user) {
            if (typeof dismissSplash === 'function' && document.getElementById('splash-screen')) {
                setTimeout(dismissSplash, 300);
            }
            if (authButton) {
                authButton.textContent = 'Cerrar Sesión';
                authButton.onclick = () => this.logout();
            }
            if (userInfo) {
                userInfo.textContent = user.email;
                userInfo.classList.remove('hidden');
            }
            if (syncStatus) {
                syncStatus.classList.remove('hidden');
                syncStatus.innerHTML = '<span class="text-green-500">●</span> Sincronizado';
            }
        } else {
            if (authButton) {
                authButton.textContent = 'Iniciar Sesión';
                authButton.onclick = () => this.showAuthModal();
            }
            if (userInfo) {
                userInfo.classList.add('hidden');
            }
            if (syncStatus) {
                syncStatus.innerHTML = '<span class="text-gray-400">●</span> Local';
            }
        }
    },

    /**
     * Show authentication modal
     */
    showAuthModal() {
        const modal = document.getElementById('authModal');
        if (modal) {
            modal.classList.remove('hidden');
            this.switchAuthTab('login');
        }
    },

    /**
     * Hide authentication modal
     */
    hideAuthModal() {
        const modal = document.getElementById('authModal');
        if (modal) modal.classList.add('hidden');
    },

    /**
     * Switch between login and register tabs
     */
    switchAuthTab(tab) {
        const loginTab = document.getElementById('loginTab');
        const registerTab = document.getElementById('registerTab');
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        
        if (tab === 'login') {
            loginTab?.classList.add('border-accent', 'text-accent');
            loginTab?.classList.remove('border-transparent');
            registerTab?.classList.remove('border-accent', 'text-accent');
            registerTab?.classList.add('border-transparent');
            loginForm?.classList.remove('hidden');
            registerForm?.classList.add('hidden');
        } else {
            registerTab?.classList.add('border-accent', 'text-accent');
            registerTab?.classList.remove('border-transparent');
            loginTab?.classList.remove('border-accent', 'text-accent');
            loginTab?.classList.add('border-transparent');
            registerForm?.classList.remove('hidden');
            loginForm?.classList.add('hidden');
        }
    },

    /**
     * Handle login form submission
     */
    async login(event) {
        event.preventDefault();
        
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        const errorEl = document.getElementById('loginError');
        
        if (!email || !password) {
            if (errorEl) errorEl.textContent = 'Por favor completa todos los campos';
            return;
        }
        
        const result = await auth.signIn(email, password);
        
        if (result.success) {
            this.hideAuthModal();
            this.showAlert('¡Bienvenido!', 'success');
            if (typeof dismissSplash === 'function') dismissSplash();
        } else {
            if (errorEl) errorEl.textContent = result.error;
        }
    },

    /**
     * Handle register form submission
     */
    async register(event) {
        event.preventDefault();
        
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const errorEl = document.getElementById('registerError');
        
        if (!email || !password || !confirmPassword) {
            if (errorEl) errorEl.textContent = 'Por favor completa todos los campos';
            return;
        }
        
        if (password !== confirmPassword) {
            if (errorEl) errorEl.textContent = 'Las contraseñas no coinciden';
            return;
        }
        
        if (password.length < 6) {
            if (errorEl) errorEl.textContent = 'La contraseña debe tener al menos 6 caracteres';
            return;
        }
        
        const result = await auth.signUp(email, password);
        
        if (result.success) {
            this.hideAuthModal();
            this.showAlert(result.message || 'Cuenta creada correctamente', 'success');
            if (typeof dismissSplash === 'function') dismissSplash();
        } else {
            if (errorEl) errorEl.textContent = result.error;
        }
    },

    /**
     * Handle logout
     */
    async logout() {
        if (confirm('¿Cerrar sesión? Tus datos locales se mantendrán.')) {
            await auth.signOut();
            this.showAlert('Sesión cerrada', 'info');
        }
    },

    /**
     * Handle Google login
     */
    async loginWithGoogle() {
        const result = await auth.signInWithProvider('google');
        if (!result.success) {
            this.showAlert(result.error, 'error');
        }
    },

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Close modals on backdrop click
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    backdrop.classList.add('hidden');
                }
            });
        });

        // Close modals on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(modal => {
                    modal.classList.add('hidden');
                });
            }
        });
        
        // Mobile nav toggle
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const mobileMenu = document.getElementById('mobileMenu');
        if (mobileMenuBtn && mobileMenu) {
            mobileMenuBtn.addEventListener('click', () => {
                mobileMenu.classList.toggle('hidden');
            });
        }

        // Handle file imports
        document.querySelectorAll('input[type="file"][data-import]').forEach(input => {
            input.addEventListener('change', (e) => {
                const importType = e.target.dataset.import;
                if (importType === 'backup') {
                    Export.importBackup(e.target.files[0]);
                } else if (importType === 'pensum') {
                    Pensum.handleImport(e);
                }
            });
        });

        const refreshGlobalGPA = () => this.updateGlobalGPA();
        window.addEventListener('storageChanged', refreshGlobalGPA);
        window.addEventListener('planChanged', refreshGlobalGPA);
        window.addEventListener('planPrincipalChanged', refreshGlobalGPA);
    },

    /**
     * Update the GPA indicator shown in the top navigation.
     */
    updateGlobalGPA() {
        const gpaEl = document.getElementById('cumulative-gpa');
        if (!gpaEl || typeof storage === 'undefined') return;

        const materias = storage.getMaterias();
        const calificaciones = storage.getCalificaciones();
        let totalPoints = 0;
        let gradedCredits = 0;

        calificaciones.forEach(cal => {
            const materia = materias.find(m => m.codigo === cal.codigo_materia);
            const nota = Number(cal.nota);
            const creditos = Number(materia?.creditos || 0);

            if (materia && Number.isFinite(nota) && nota >= 3.0 && creditos > 0) {
                totalPoints += nota * creditos;
                gradedCredits += creditos;
            }
        });

        const gpa = gradedCredits > 0 ? totalPoints / gradedCredits : 0;
        gpaEl.textContent = gpa > 0 ? gpa.toFixed(2) : '--';
        gpaEl.classList.toggle('text-red-600', gpa > 0 && gpa < 3.0);
        gpaEl.classList.toggle('text-accent-600', !(gpa > 0 && gpa < 3.0));
    },

    /**
     * Initialize page-specific modules based on current route
     */
    initPage() {
        const path = window.location.pathname;
        
        if (path === '/' || path === '/pensum' || path === '/pensum/') {
            if (typeof Pensum !== 'undefined') {
                Pensum.init();
            }
        } else if (path.startsWith('/semester/')) {
            const semesterMatch = path.match(/\/semester\/(\d+)/);
            if (semesterMatch && typeof Semester !== 'undefined') {
                Semester.init(parseInt(semesterMatch[1]));
            }
        } else if (path === '/schedule' || path === '/schedule/') {
            if (typeof Schedule !== 'undefined') {
                Schedule.init();
            }
        }
    },

    /**
     * Show an alert message
     */
    showAlert(message, type = 'info', options = {}) {
        // Remove existing alerts
        document.querySelectorAll('.app-alert').forEach(el => el.remove());
        const title= (message && typeof message === 'object') ? message.title : message;
        const detail = (message && typeof message === 'object' ? message.detail: (options.detail || null));
        const action = options.action || null;
        
        const colors = {
            success: 'bg-green-50 border-green-300 text-green-900 dark:bg-green-950 dark:border-green-700 dark:text-green-100',
            error: 'bg-red-50 border-red-300 text-red-900 dark:bg-red-950 dark:border-red-700 dark:text-red-100',
            warning: 'bg-yellow-50 border-yellow-300 text-yellow-900 dark:bg-yellow-950 dark:border-yellow-700 dark:text-yellow-100',
            info: 'bg-blue-50 border-blue-300 text-blue-900 dark:bg-blue-950 dark:border-blue-700 dark:text-blue-100'
        };
        
        const icons = {
            success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>',
            error: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>',
            warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>',
            info: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>'
        };
        
        const durations = { error: 9000, warning: 7000, success: 4000, info: 5000 };

        const alertEl = document.createElement('div');
        alertEl.className = `app-alert fixed top-4 right-4 z-50 max-w-sm w-full p-4 rounded-xl border shadow-lg transition-all duration-300 translate-x-full ${colors[type] || colors.info}`;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'w-5 h-5 flex-shrink-0 mt-0.5');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('viewBox', '0 0 24 24');
        const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        pathEl.setAttribute('stroke-linecap', 'round');
        pathEl.setAttribute('stroke-linejoin', 'round');
        pathEl.setAttribute('stroke-width', '2');
        pathEl.setAttribute('d', (icons[type] || icons.info).match(/d="([^"]+)"/)[1]);
        svg.appendChild(pathEl);

        const textDiv = document.createElement('div');
        textDiv.className = 'flex-1 min-w-0';

        const titleEl = document.createElement('p');
        titleEl.className = 'text-sm font-semibold leading-snug';
        titleEl.textContent = title;
        textDiv.appendChild(titleEl);

        if (detail) {
            const detailEl = document.createElement('p');
            detailEl.className = 'text-xs mt-1 opacity-80 leading-snug';
            detailEl.textContent = detail;
            textDiv.appendChild(detailEl);
        }

        if (action) {
            const actionBtn = document.createElement('button');
            actionBtn.className = 'text-xs mt-2 font-semibold underline underline-offset-2 hover:no-underline block';
            actionBtn.textContent = action.label;
            actionBtn.addEventListener('click', () => { action.fn(); dismiss(); });
            textDiv.appendChild(actionBtn);
        }

        const closeBtn = document.createElement('button');
        closeBtn.className = 'flex-shrink-0 ml-3 p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors';
        closeBtn.setAttribute('aria-label', 'Cerrar');
        closeBtn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`;

        const row = document.createElement('div');
        row.className = 'flex items-start gap-3';
        row.appendChild(svg);
        row.appendChild(textDiv);
        row.appendChild(closeBtn);
        alertEl.appendChild(row);

        const dismiss = () => {
            alertEl.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => alertEl.remove(), 300);
        };
        closeBtn.addEventListener('click', dismiss);

        document.body.appendChild(alertEl);
        requestAnimationFrame(() => alertEl.classList.remove('translate-x-full'));
        setTimeout(dismiss, durations[type] ?? 5000);
    },

    /**
     * Manual sync trigger
     */
    async syncNow() {
        if (!auth.isAuthenticated()) {
            this.showAlert('Inicia sesión para sincronizar', 'info');
            return;
        }
        
        this.showAlert('Sincronizando...', 'info');
        const result = await auth.manualSync();
        
        if (result.success) {
            this.showAlert('Datos sincronizados correctamente', 'success');
        } else {
            this.showAlert({ title: 'No se pudo sincronizar', detail: result.error || 'Verifica tu conexión e intenta de nuevo.' }, 'error');
        }
    },

    /**
     * Clear stale service workers/caches.
     * The app does not ship a sw.js file, so an old registration can serve cached UI.
     */
    async registerServiceWorker() {
        if (!('serviceWorker' in navigator)) return;

        try {
            const registrations = await navigator.serviceWorker.getRegistrations();
            await Promise.all(registrations.map(registration => registration.unregister()));

            if ('caches' in window) {
                const cacheNames = await caches.keys();
                await Promise.all(cacheNames.map(cacheName => caches.delete(cacheName)));
            }
        } catch (error) {
            console.warn('Could not clear stale service worker cache:', error);
        }
    },

    /**
     * Utility: Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Utility: Format date for display
     */
    formatDate(date) {
        return new Date(date).toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { App };
}
