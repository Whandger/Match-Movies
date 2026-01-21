import os

def get_database_uri():
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', 5432)
    db_name = os.getenv('DB_NAME')

    # Se faltar algum valor, usa SQLite local
    if not all([db_user, db_password, db_host, db_name]):
        return 'sqlite:///matchmovies.db'

    # IMPORTANTE: Adicione um timeout e opções de SSL
    # Isso pode resolver o problema de IPv6
    connection_params = {
        'connect_timeout': 10,
        'sslmode': 'require'
    }
    
    # Construa a URL com parâmetros adicionais
    base_url = f'postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    
    # Adicione os parâmetros de conexão
    return f"{base_url}?{'&'.join([f'{k}={v}' for k, v in connection_params.items()])}"

DATABASE_URI = get_database_uri()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'chave_padrao')
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = DATABASE_URI

# ... resto do código igual
