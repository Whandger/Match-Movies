from flask import Flask, session
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy  # MUDOU AQUI!
import os

# Carrega variáveis do .env
load_dotenv()

# Instância global do SQLAlchemy  # MUDOU AQUI!
db = SQLAlchemy()

def create_app():
    print("Criando app e registrando blueprints...")

    app = Flask( 
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'template'), # Busca os arquivos html da pagina, linkados no html 
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static') # Busca os arquivos css da pagina, linkados no html
    ) # Exemplo busca no html { href="{{ url_for('static', filename='css/DropDownUser.css') }}"> }

    # Verifica o ambiente (development ou production)
    env = os.getenv('FLASK_ENV', 'development')

    if env == 'production':
        from server.config.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from server.config.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Configura a chave secreta (pode estar na config ou no .env)
    app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta_segura')

    # Inicializa o SQLAlchemy com a app  # MUDOU AQUI!
    db.init_app(app)
    app.extensions['db'] = db

    # Roda script SQL de inicialização apenas em desenvolvimento
    # COMENTADO porque já criamos as tabelas no Supabase
    # if env == 'development':
    #     from server.utils.init_db import run_sql_script
    #     run_sql_script()

    # Registrar blueprints, se ainda não registrados
    print(app.url_map)
    if 'page' not in app.blueprints:
        from server.routes.routes import page_bp
        app.register_blueprint(page_bp)
        print(app.url_map)

    if 'login' not in app.blueprints:
        from server.routes.loginroutes import login_bp
        app.register_blueprint(login_bp)
    
    if 'movies' not in app.blueprints:
        from server.routes.movies import movies_bp
        app.register_blueprint(movies_bp, url_prefix='/api/movies')  # Adicione o url_prefix aqui
        print("Blueprint 'movies' registrado")

    return app

if __name__ == '__main__':
    app = create_app()
    # Rodar app normalmente, debug True só em desenvolvimento
    debug_mode = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, use_reloader=False)