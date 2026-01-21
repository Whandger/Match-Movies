from flask import current_app
from sqlalchemy import text

def get_user_by_username_or_email(username, email):
    """Busca usuário por username ou email usando SQLAlchemy"""
    try:
        db = current_app.extensions.get('db')
        if db is None:
            print("❌ ERROR: Database não encontrado em current_app.extensions")
            return None
        
        # **IMPORTANTE: Use ASPAS DUPLAS em "MoviesUsers"**
        query = text('SELECT * FROM "MoviesUsers" WHERE username = :username OR email = :email')
        
        result = db.session.execute(
            query,
            {'username': username, 'email': email}
        ).fetchone()
        
        if result:
            print(f"✅ DEBUG: Usuário encontrado: {username}")
            return dict(result._mapping)
        else:
            print(f"⚠️  DEBUG: Usuário NÃO encontrado: {username}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR ao buscar usuário: {e}")
        return None

def insert_user(email, username, hashed_password):
    """Insere novo usuário usando SQLAlchemy"""
    try:
        db = current_app.extensions.get('db')
        if db is None:
            print("❌ ERROR: Database não encontrado em current_app.extensions")
            return False
        
        # **IMPORTANTE: Use ASPAS DUPLAS em "MoviesUsers"**
        query = text('''
            INSERT INTO "MoviesUsers" (email, username, password_hash) 
            VALUES (:email, :username, :password_hash)
        ''')
        
        db.session.execute(
            query,
            {
                'email': email,
                'username': username, 
                'password_hash': hashed_password
            }
        )
        db.session.commit()
        
        print(f"✅ DEBUG: Usuário inserido com sucesso: {username}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR ao inserir usuário: {e}")
        db.session.rollback()
        return False
