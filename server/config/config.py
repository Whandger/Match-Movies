import os

# FUNÇÃO separada que sempre retorna string
def get_database_uri():
    uri = os.getenv('DATABASE_URL')
    
    if not uri:
        # Local development - SQLite
        return 'sqlite:///matchmovies.db'
    
    # If Supabase in production, add SSL
    if 'supabase' in uri and 'sslmode' not in uri:
        return uri + '?sslmode=require'
    
    return uri

# CHAMA a função para obter a string
DATABASE_URI = get_database_uri()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave_padrao')
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = DATABASE_URI  # STRING, não property!

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False