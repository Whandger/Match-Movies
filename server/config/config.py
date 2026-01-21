import os

# Função que monta a URI do banco
def get_database_uri():
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', 5432)
    db_name = os.getenv('DB_NAME')

    # Se faltar algum valor, usa SQLite local (desenvolvimento)
    if not all([db_user, db_password, db_host, db_name]):
        return 'sqlite:///matchmovies.db'

    # URI PostgreSQL para produção
    return f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'

# Chama a função para obter a string
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
