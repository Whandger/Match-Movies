import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv('DATABASE_URL')
print(f"Tentando conectar: {database_url.replace(':51320142018513@', ':********@')}")

try:
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print("✅ Conectado ao PostgreSQL!")
        print(f"Versão: {result.fetchone()[0]}")
        
        # Verificar tabelas
        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).fetchall()
        
        print("\n📊 Tabelas encontradas:")
        for table in tables:
            print(f"  - {table[0]}")
            
except Exception as e:
    print(f"❌ ERRO: {e}")