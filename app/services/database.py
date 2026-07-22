"""
Database Service
Handles Supabase connection and operations for authenticated users
"""
import os
from typing import Optional

# Optional Supabase import
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None
    create_client = None

from flask import current_app


class DatabaseService:
    """
    Service for interacting with Supabase database
    Only used when user is authenticated
    """
    
    _client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """
        Get or create Supabase client
        
        Returns:
            Supabase client or None if not configured
        """
        if not SUPABASE_AVAILABLE:
            return None
            
        if cls._client is not None:
            return cls._client
        
        url = os.environ.get('SUPABASE_URL', '')
        key = os.environ.get('SUPABASE_ANON_KEY', '')
        
        if not url or not key:
            return None
        
        try:
            cls._client = create_client(url, key)
            return cls._client
        except Exception as e:
            print(f"Failed to create Supabase client: {e}")
            return None
    
    @classmethod
    def get_authenticated_client(cls, access_token: str) -> Optional[Client]:
        """
        Get a Supabase client authenticated with user's token
        This is needed for RLS policies to work correctly
        
        Args:
            access_token: User's JWT access token
            
        Returns:
            Authenticated Supabase client or None
        """
        if not SUPABASE_AVAILABLE:
            return None
        
        url = os.environ.get('SUPABASE_URL', '')
        key = os.environ.get('SUPABASE_ANON_KEY', '')
        
        if not url or not key:
            return None
        
        try:
            # Create a new client with the user's token in headers
            from supabase import create_client
            client = create_client(url, key)
            # Set the auth token for this client
            client.postgrest.auth(access_token)
            return client
        except Exception as e:
            print(f"Failed to create authenticated client: {e}")
            return None
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Supabase is configured and available"""
        return SUPABASE_AVAILABLE and cls.get_client() is not None

    @classmethod
    def keepalive(cls) -> dict:
        """
        Perform a tiny read against Supabase to keep the project active.

        The query intentionally does not depend on user data being visible. With
        RLS enabled, an anonymous client may receive an empty result, but the
        database still handles the request.
        """
        client = cls.get_client()
        if not client:
            return {'ok': False, 'error': 'Database not configured'}

        try:
            response = client.table('pensums').select('id').limit(1).execute()
            rows = response.data or []
            return {
                'ok': True,
                'checked_table': 'pensums',
                'rows_seen': len(rows)
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}
    
    # ==================== Auth Methods ====================
    
    @classmethod
    def sign_up(cls, email: str, password: str) -> dict:
        """
        Register a new user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Auth response dict
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Supabase no está configurado. Configura SUPABASE_URL y SUPABASE_ANON_KEY en el archivo .env'}
        
        try:
            response = client.auth.sign_up({
                'email': email,
                'password': password
            })
            
            # Convert response objects to serializable dicts
            user_data = None
            session_data = None
            
            if response.user:
                user_data = {
                    'id': response.user.id,
                    'email': response.user.email,
                    'created_at': str(response.user.created_at) if response.user.created_at else None
                }
            
            if response.session:
                session_data = {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_at': response.session.expires_at
                }
            
            return {'user': user_data, 'session': session_data}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def sign_in(cls, email: str, password: str) -> dict:
        """
        Sign in existing user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Auth response dict with user and session
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Supabase no está configurado. Configura SUPABASE_URL y SUPABASE_ANON_KEY en el archivo .env'}
        
        try:
            response = client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            return {
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                },
                'session': {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def refresh_session(cls, refresh_token: str) -> dict:
        """
        Refresh the access token using the refresh token
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New session data or error
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.auth.refresh_session(refresh_token)
            
            if response and response.session:
                return {
                    'session': {
                        'access_token': response.session.access_token,
                        'refresh_token': response.session.refresh_token
                    },
                    'user': {
                        'id': response.user.id,
                        'email': response.user.email
                    } if response.user else None
                }
            else:
                return {'error': 'Could not refresh session'}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def sign_out(cls, access_token: str) -> dict:
        """Sign out user"""
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            client.auth.sign_out()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def get_user(cls, access_token: str) -> dict:
        """Get current user from access token"""
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            # Set the session
            client.auth.set_session(access_token, '')
            user = client.auth.get_user()
            return {'user': {'id': user.user.id, 'email': user.user.email}}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def verify_token(cls, access_token: str, refresh_token: str = None) -> dict:
        """
        Verify email confirmation token and get user session
        
        Args:
            access_token: The access token from email link
            refresh_token: The refresh token from email link
            
        Returns:
            User and session data or error
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Supabase no está configurado', 'error_code': 'not_configured'}
        
        try:
            # Set session with the tokens from the email link
            response = client.auth.set_session(access_token, refresh_token or '')
            
            if response and response.user:
                return {
                    'user': {
                        'id': response.user.id,
                        'email': response.user.email,
                        'email_confirmed_at': str(response.user.email_confirmed_at) if response.user.email_confirmed_at else None
                    },
                    'session': {
                        'access_token': response.session.access_token if response.session else access_token,
                        'refresh_token': response.session.refresh_token if response.session else refresh_token
                    } if response.session else None
                }
            else:
                return {'error': 'No se pudo verificar el token', 'error_code': 'invalid_token'}
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Parse common Supabase errors
            if 'expired' in error_msg or 'otp_expired' in error_msg:
                return {'error': 'El enlace ha expirado', 'error_code': 'otp_expired'}
            elif 'invalid' in error_msg:
                return {'error': 'Enlace inválido', 'error_code': 'invalid_token'}
            elif 'already' in error_msg or 'confirmed' in error_msg:
                return {'error': 'El email ya fue verificado', 'error_code': 'already_confirmed'}
            else:
                return {'error': str(e), 'error_code': 'unknown_error'}
    
    @classmethod
    def resend_verification(cls, email: str) -> dict:
        """
        Resend email verification
        
        Args:
            email: User's email address
            
        Returns:
            Success or error
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Supabase no está configurado'}
        
        try:
            # Use resend method for email verification
            response = client.auth.resend(
                type='signup',
                email=email
            )
            return {'success': True, 'message': 'Email de verificación enviado'}
        except Exception as e:
            error_msg = str(e).lower()
            if 'rate' in error_msg or 'limit' in error_msg:
                return {'error': 'Demasiados intentos. Espera unos minutos antes de reenviar.'}
            elif 'not found' in error_msg or 'no user' in error_msg:
                return {'error': 'No se encontró una cuenta con ese email.'}
            else:
                return {'error': str(e)}
    
    @classmethod
    def report_error(cls, message: str, steps: str = None, diagnostics: dict = None) -> dict:
        """
        Save a problem report to the errors table.

        Args:
            message: Description of the problem
            steps: Steps to reproduce (optional)
            diagnostics: Diagnostic info dict (optional)

        Returns:
            Result dict
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}

        try:
            row = {'message': message}
            if steps:
                row['steps'] = steps
            if diagnostics is not None:
                row['diagnostics'] = diagnostics

            response = client.table('errors').insert(row).execute()
            return {'success': True, 'data': response.data}
        except Exception as e:
            return {'error': str(e)}

    # ==================== Data Methods ====================
    
    @classmethod
    def save_pensum(cls, user_id: str, pensum_data: dict) -> dict:
        """
        Save user's pensum to database
        
        Args:
            user_id: User's ID
            pensum_data: Pensum data dict
            
        Returns:
            Result dict
        """
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            # Upsert pensum data
            response = client.table('pensums').upsert({
                'user_id': user_id,
                'data': pensum_data,
                'updated_at': 'now()'
            }, on_conflict='user_id').execute()
            
            return {'success': True, 'data': response.data}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def get_pensum(cls, user_id: str, access_token: str = None) -> dict:
        """
        Get user's pensum from database
        
        Args:
            user_id: User's ID
            
        Returns:
            Pensum data or error
        """
        client = cls.get_authenticated_client(access_token) if access_token else cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('pensums').select('*').eq('user_id', user_id).single().execute()
            row = response.data or {}
            return {
                'data': row.get('data'),
                'updated_at': str(row.get('updated_at')) if row.get('updated_at') else None
            }
        except Exception as e:
            # No data found is not an error
            if 'No rows' in str(e):
                return {'data': None, 'updated_at': None}
            return {'error': str(e)}
    
    @classmethod
    def save_clases(cls, user_id: str, clases_data: list) -> dict:
        """Save user's classes to database"""
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('clases').upsert({
                'user_id': user_id,
                'data': clases_data,
                'updated_at': 'now()'
            }, on_conflict='user_id').execute()
            
            return {'success': True, 'data': response.data}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def get_clases(cls, user_id: str, access_token: str = None) -> dict:
        """Get user's classes from database"""
        client = cls.get_authenticated_client(access_token) if access_token else cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('clases').select('*').eq('user_id', user_id).single().execute()
            row = response.data or {}
            return {
                'data': row.get('data'),
                'updated_at': str(row.get('updated_at')) if row.get('updated_at') else None
            }
        except Exception as e:
            if 'No rows' in str(e):
                return {'data': None, 'updated_at': None}
            return {'error': str(e)}
    
    @classmethod
    def save_configuracion(cls, user_id: str, config_data: dict) -> dict:
        """Save user's configuration to database"""
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('configuraciones').upsert({
                'user_id': user_id,
                'data': config_data,
                'updated_at': 'now()'
            }, on_conflict='user_id').execute()
            
            return {'success': True, 'data': response.data}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def get_configuracion(cls, user_id: str, access_token: str = None) -> dict:
        """Get user's configuration from database"""
        client = cls.get_authenticated_client(access_token) if access_token else cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('configuraciones').select('*').eq('user_id', user_id).single().execute()
            row = response.data or {}
            return {
                'data': row.get('data'),
                'updated_at': str(row.get('updated_at')) if row.get('updated_at') else None
            }
        except Exception as e:
            if 'No rows' in str(e):
                return {'data': None, 'updated_at': None}
            return {'error': str(e)}
    
    @classmethod
    def save_calificaciones(cls, user_id: str, calificaciones_data: list) -> dict:
        """Save user's grades to database"""
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('calificaciones').upsert({
                'user_id': user_id,
                'data': calificaciones_data,
                'updated_at': 'now()'
            }, on_conflict='user_id').execute()
            
            return {'success': True, 'data': response.data}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def get_calificaciones(cls, user_id: str, access_token: str = None) -> dict:
        """Get user's grades from database"""
        client = cls.get_authenticated_client(access_token) if access_token else cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('calificaciones').select('*').eq('user_id', user_id).single().execute()
            row = response.data or {}
            return {
                'data': row.get('data'),
                'updated_at': str(row.get('updated_at')) if row.get('updated_at') else None
            }
        except Exception as e:
            if 'No rows' in str(e):
                return {'data': None, 'updated_at': None}
            return {'error': str(e)}
    
    @classmethod 
    def save_franjas(cls, user_id: str, franjas_data: list) -> dict:
        """Save user's time slot preferences to database"""
        client = cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('franjas').upsert({
                'user_id': user_id,
                'data': franjas_data,
                'updated_at': 'now()'
            }, on_conflict='user_id').execute()
            
            return {'success': True, 'data': response.data}
        except Exception as e:
            return {'error': str(e)}
    
    @classmethod
    def get_franjas(cls, user_id: str, access_token: str = None) -> dict:
        """Get user's time slot preferences from database"""
        client = cls.get_authenticated_client(access_token) if access_token else cls.get_client()
        if not client:
            return {'error': 'Database not configured'}
        
        try:
            response = client.table('franjas').select('*').eq('user_id', user_id).single().execute()
            row = response.data or {}
            return {
                'data': row.get('data'),
                'updated_at': str(row.get('updated_at')) if row.get('updated_at') else None
            }
        except Exception as e:
            if 'No rows' in str(e):
                return {'data': None, 'updated_at': None}
            return {'error': str(e)}
    
    @classmethod
    def sync_all_data(cls, user_id: str, data: dict, access_token: str = None) -> dict:
        """
        Sync all local data to database (local wins)
        
        Args:
            user_id: User's ID
            data: Dict with all data types
            access_token: User's JWT for authenticated operations
            
        Returns:
            Result dict
        """
        # Use authenticated client if token provided (required for RLS)
        if access_token:
            client = cls.get_authenticated_client(access_token)
        else:
            client = cls.get_client()
            
        if not client:
            return {'error': 'Database not configured'}
        
        results = {}
        
        # Helper function to upsert data
        def upsert_data(table_name: str, data_value) -> dict:
            try:
                response = client.table(table_name).upsert({
                    'user_id': user_id,
                    'data': data_value,
                    'updated_at': 'now()'
                }, on_conflict='user_id').execute()
                return {'success': True, 'data': response.data}
            except Exception as e:
                return {'error': str(e)}
        
        if 'pensum' in data:
            results['pensum'] = upsert_data('pensums', data['pensum'])
        
        if 'clases' in data:
            results['clases'] = upsert_data('clases', data['clases'])
        
        if 'configuracion' in data:
            results['configuracion'] = upsert_data('configuraciones', data['configuracion'])
        
        if 'calificaciones' in data:
            results['calificaciones'] = upsert_data('calificaciones', data['calificaciones'])
        
        if 'franjas' in data:
            results['franjas'] = upsert_data('franjas', data['franjas'])
        
        # Check for errors
        errors = [k for k, v in results.items() if 'error' in v]
        if errors:
            return {'error': f"Failed to sync: {', '.join(errors)}", 'details': results}
        
        return {'success': True, 'results': results}
