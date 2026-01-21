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
                # Teste 1: Versão do PostgreSQL
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                print(f"✅ PostgreSQL version: {version}")
                
                # Teste 2: Nome do banco
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                print(f"✅ Database: {db_name}")
                
                # Teste 3: Tabelas existentes
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result.fetchall()]
                print(f"📊 Tabelas no banco: {tables}")
                
                # Teste 4: Acesso à tabela MoviesUsers
                if 'MoviesUsers' in tables:
                    result = conn.execute(text('SELECT COUNT(*) FROM "MoviesUsers"'))
                    count = result.scalar()
                    print(f"✅ Tabela MoviesUsers tem {count} registro(s)")
                else:
                    print("❌ Tabela MoviesUsers NÃO encontrada!")
                    
        except Exception as e:
            print(f"❌ ERRO na conexão: {str(e)[:150]}")
    
    # Inicializa o SQLAlchemy
    db.init_app(app)
    app.extensions['db'] = db
    
    print("✅ SQLAlchemy inicializado")
    print("✅ Tabelas já criadas manualmente via SQL (Neon)")
    
    # Registrar blueprints
    from server.routes.routes import page_bp
    from server.routes.loginroutes import login_bp
    from server.routes.movies import movies_bp

    app.register_blueprint(page_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(movies_bp, url_prefix='/api/movies')
    
    print("✅ Blueprints registrados")
    print("✅ App configurado com sucesso!")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=os.getenv('FLASK_ENV') != 'production')
