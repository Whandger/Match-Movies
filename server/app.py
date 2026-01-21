from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import create_engine, text
from server.config.config import ProductionConfig, DevelopmentConfig

db = SQLAlchemy()

def create_app():
    print("🚀 Iniciando app Flask...")
    
    app = Flask(__name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'template'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
    )

    env = os.getenv('FLASK_ENV', 'production')
    if env == 'production':
        app.config.from_object(ProductionConfig)
        print("⚙️  Modo: Produção")
    else:
        app.config.from_object(DevelopmentConfig)
        print("⚙️  Modo: Desenvolvimento")
    
    # Mostra a URL (com senha oculta)
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    safe_url = db_url.replace('npg_WdItCG7fEVL9', '***') if 'npg_WdItCG7fEVL9' in db_url else db_url
    print(f"🔗 Database URL: {safe_url}")
    
    # Testa conexão com Neon
    if 'neon.tech' in db_url:
        print("🌐 Conectando ao Neon.tech...")
        try:
            engine = create_engine(db_url, connect_args={"connect_timeout": 10})
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                print(f"✅ PostgreSQL version: {version}")
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                print(f"✅ Database: {db_name}")
        except Exception as e:
            print(f"❌ ERRO na conexão: {str(e)[:150]}")
    
    # Inicializa o SQLAlchemy
    db.init_app(app)
    
    # Criar tabelas se não existirem
    with app.app_context():
        try:
            # Importa e cria todas as tabelas
            db.create_all()
            print("✅ Tabelas verificadas/criadas")
            
            # Verifica se a tabela MoviesUsers existe
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tabelas no banco: {tables}")
            
        except Exception as e:
            print(f"⚠️  Nota sobre tabelas: {str(e)[:100]}")

    # Registrar blueprints
    from server.routes.routes import page_bp
    from server.routes.loginroutes import login_bp
    from server.routes.movies import movies_bp

    app.register_blueprint(page_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(movies_bp, url_prefix='/api/movies')
    
    print("✅ App configurado com sucesso!")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=os.getenv('FLASK_ENV') != 'production')
