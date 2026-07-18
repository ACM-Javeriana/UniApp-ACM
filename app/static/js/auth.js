/**
 * Auth Manager - Handles Supabase authentication
 */

class AuthManager {
    constructor() {
        this.supabase = null;
        this.currentUser = null;
        this.authListeners = [];
    }

    /**
     * Initialize Supabase client
     */
    async init(supabaseUrl, supabaseKey) {
        if (!supabaseUrl || !supabaseKey) {
            console.warn('Supabase credentials not provided, running in offline mode');
            return false;
        }

        try {
            // Initialize Supabase client
            this.supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
            
            // Check for existing session
            const { data: { session } } = await this.supabase.auth.getSession();
            if (session) {
                this.currentUser = session.user;
                this.notifyListeners(session.user);
                await this.syncOnLogin();
            }

            // Listen for auth changes
            this.supabase.auth.onAuthStateChange(async (event, session) => {
                const user = session?.user || null;
                this.currentUser = user;
                this.notifyListeners(user);

                if (event === 'SIGNED_IN' && user) {
                    await this.syncOnLogin();
                }
            });

            return true;
        } catch (error) {
            console.error('Failed to initialize Supabase:', error);
            return false;
        }
    }

    /**
     * Register a listener for auth state changes
     */
    onAuthChange(callback) {
        this.authListeners.push(callback);
        // Immediately call with current state
        callback(this.currentUser);
    }

    /**
     * Notify all listeners of auth change
     */
    notifyListeners(user) {
        this.authListeners.forEach(cb => cb(user));
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return this.currentUser !== null;
    }

    /**
     * Get current user
     */
    getUser() {
        return this.currentUser;
    }

    translateError(msg) {
        if(!msg) return 'Ocurrio un error inesperado, intenta de nuevo';
        const m = msg.toLowerCase();

        if(m.includes('invalid login credentials') || m.includes('invalid_credentials'))
            return 'Correo o contraseña incorrectos. Verifica tus datos e intenta de nuevo';
        if(m.includes('email not confirmed'))
            return 'Tu correo aun no ha sido verificado. Revisa tu bandeja de entrada'
        if (m.includes('password should be at least') || m.includes('password is too short'))
            return 'La contraseña debe tener al menos 6 caracteres.';
        if (m.includes('unable to validate email') || m.includes('invalid email') || m.includes('invalid format'))
            return 'El formato del correo no es válido.';
        if (m.includes('user already registered') || m.includes('user already exists') || m.includes('already been registered'))
            return 'Ya existe una cuenta con este correo. Intenta iniciar sesión.';
        if(m.includes('email rate limit') || m.includes('too many requests') || m.includes('rate limit'))
            return 'Demasiados intentos seguidos. Espera unos minutos antes de intentar de nuevo';
        if (m.includes('for security purposes, you can only request this after'))
            return 'Por seguridad, debes esperar un momento antes de volver a intentarlo.';
        if (m.includes('signup is disabled'))
            return 'El registro de nuevos usuarios está desactivado temporalmente.';
        if (m.includes('supabase not initialized') || m.includes('not initialized'))
            return 'La sincronización en la nube no está disponible en este momento.';
        if (m.includes('network') || m.includes('fetch') || m.includes('failed to fetch'))
            return 'No se pudo conectar con el servidor. Verifica tu conexión a internet.';
        if (m.includes('jwt') || m.includes('token') || m.includes('session'))
            return 'Tu sesión ha expirado. Por favor inicia sesión de nuevo.';
        if (m.includes('provider') || m.includes('oauth'))
            return 'No se pudo completar el inicio de sesión con el proveedor externo. Intenta de nuevo.';

        return msg.charAt(0).toUpperCase() + msg.slice(1);
    }
    /**
     * Sign up with email and password
     */
    async signUp(email, password) {
        if (!this.supabase) {
            return { success: false, error: this.translateError('supabase not initialized') };
        }

        try {
            const { data, error } = await this.supabase.auth.signUp({
                email,
                password
            });

            if (error) throw error;

            return { 
                success: true, 
                user: data.user,
                message: 'Cuenta creada. Por favor verifica tu email.'
            };
        } catch (error) {
            return { success: false, error: this.translateError(error.message)};
        }
    }

    /**
     * Sign in with email and password
     */
    async signIn(email, password) {
        if (!this.supabase) {
            return { success: false, error: this.translateError('supabase not initialized') };
        }

        try {
            const { data, error } = await this.supabase.auth.signInWithPassword({
                email,
                password
            });

            if (error) throw error;

            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: this.translateError(error.message) };
        }
    }

    /**
     * Sign in with OAuth provider
     */
    async signInWithProvider(provider) {
        if (!this.supabase) {
            return { success: false, error: this.translateError('supabase not initialized') };
        }

        try {
            const { data, error } = await this.supabase.auth.signInWithOAuth({
                provider,
                options: {
                    redirectTo: window.location.origin
                }
            });

            if (error) throw error;

            return { success: true };
        } catch (error) {
            return { success: false, error: this.translateError(error.message) };
        }
    }

    /**
     * Sign out
     */
    async signOut() {
        if (!this.supabase) {
            return { success: false, error: this.translateError('supabase not initialized') };
        }

        try {
            // Sync before signing out
            if (this.isAuthenticated()) {
                await storage.syncToServer();
            }

            const { error } = await this.supabase.auth.signOut();
            if (error) throw error;

            return { success: true };
        } catch (error) {
            return { success: false, error: this.translateError(error.message) };
        }
    }

    /**
     * Reset password
     */
    async resetPassword(email) {
        if (!this.supabase) {
            return { success: false, error: this.translateError('supabase not initialized') };
        }

        try {
            const { error } = await this.supabase.auth.resetPasswordForEmail(email, {
                redirectTo: `${window.location.origin}/reset-password`
            });

            if (error) throw error;

            return { 
                success: true, 
                message: 'Revisa tu email para restablecer tu contraseña'
            };
        } catch (error) {
            return { success: false, error: this.translateError(error.message) };
        }
    }

    /**
     * Sync data on login
     */
    async syncOnLogin() {
        if (!this.isAuthenticated()) return;

        // Initialize storage with Supabase client
        storage.initSupabase(this.supabase, this.currentUser.id);
        
        // Perform full sync (load from server if local empty, then push local to server)
        const result = await storage.fullSync();
        
        if (result.success) {
            console.log('Data synced successfully');
            // Trigger UI refresh
            window.dispatchEvent(new CustomEvent('datasynced'));
        } else {
            console.warn('Sync had issues:', result);
        }
    }

    /**
     * Manual sync trigger
     */
    async manualSync() {
        if (!this.isAuthenticated()) {
            return { success: false, error: 'Not authenticated' };
        }

        return await storage.syncToServer();
    }
}

// Global instance
const auth = new AuthManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuthManager, auth };
}
