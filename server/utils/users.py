from flask import current_app
from sqlalchemy import text

def get_user_by_username_or_email(username, email):
    """Busca usuário por username ou email usando SQLAlchemy"""
    try:
        db = current_app.extensions.get('db')
        if db is None:
            return None
        
        result = db.session.execute(
            text("SELECT * FROM MoviesUsers WHERE username = :username OR email = :email"),
            {'username': username, 'email': email}
        ).fetchone()
        
        return dict(result._mapping) if result else None
        
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return None

def insert_user(email, username, hashed_password):
    """Insere novo usuário usando SQLAlchemy"""
    try:
        db = current_app.extensions.get('db')
        if db is None:
            return False
        
        db.session.execute(
            text("""
                INSERT INTO MoviesUsers (email, username, password_hash) 
                VALUES (:email, :username, :password_hash)
            """),
            {
                'email': email,
                'username': username, 
                'password_hash': hashed_password
            }
        )
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Erro ao inserir usuário: {e}")
        db.session.rollback()
        return False