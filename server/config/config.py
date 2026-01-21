import os

def get_database_uri():
    # Tenta obter a URL completa primeiro
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        return database_url
    
    # Fallback para SQLite se não houver DATABASE_URL
    return 'sqlite:///matchmovies.db'

DATABASE_URI = get_database_uri()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave_padrao')
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = DATABASE_URI


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
