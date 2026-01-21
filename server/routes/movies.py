from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text
import requests
import random
import json

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

# ============================================================================
# SISTEMA DE DEBUG E INVESTIGAÇÃO
# ============================================================================

def debug_matches_system():
    """Função para debug completo do sistema de matches"""
    try:
        if 'user_id' not in session:
            return
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            print("❌ Database não encontrado")
            return
        
        print("\n" + "="*80)
        print("🔍 DEBUG COMPLETO DO SISTEMA DE MATCHES")
        print("="*80)
        
        # 1. Verificar usuário atual
        print(f"\n👤 USUÁRIO ATUAL: ID={user_id}")
        
        # 2. Verificar conexões
        connections = db.session.execute(
            text("""
                SELECT id, user1_id, user2_id, match_count, matched_movies 
                FROM "UserConnections" 
                WHERE (user1_id = :user_id OR user2_id = :user_id) AND is_active = TRUE
            """),
            {'user_id': user_id}
        ).fetchall()
        
        print(f"\n🔗 CONEXÕES: {len(connections)} encontradas")
        
        for conn in connections:
            print(f"\n  Conexão ID: {conn[0]}")
            print(f"  User1: {conn[1]}, User2: {conn[2]}")
            print(f"  Match count: {conn[3]}")
            
            # Converter matched_movies
            matched_movies = conn[4]
            if matched_movies is None:
                matches_list = []
            elif isinstance(matched_movies, str):
                try:
                    matches_list = json.loads(matched_movies)
                except:
                    matches_list = []
            else:
                matches_list = matched_movies
            
            print(f"  Matches no banco: {matches_list}")
            print(f"  Quantidade de matches: {len(matches_list)}")
        
        # 3. Verificar filmes curtidos pelo usuário atual
        user_movies = db.session.execute(
            text("""
                SELECT movie_id, action FROM "MoviesReacted" 
                WHERE user_id = :user_id AND action IN ('like', 'indicate')
                ORDER BY reacted_at DESC
                LIMIT 10
            """),
            {'user_id': user_id}
        ).fetchall()
        
        print(f"\n🎬 FILMES CURTIDOS PELO USUÁRIO {user_id} (últimos 10):")
        for movie in user_movies:
            print(f"  ID: {movie[0]}, Ação: {movie[1]}")
        
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"❌ ERROR no debug: {str(e)}")

# ============================================================================
# FUNÇÃO SUPER SIMPLES PARA CRIAR MATCHES
# ============================================================================

def create_matches_simple(user1_id, user2_id, connection_id):
    """Versão SUPER SIMPLES para criar matches"""
    try:
        db = current_app.extensions.get('db')
        if db is None:
            print("❌ Database não encontrado")
            return False
        
        print(f"\n🎯 TENTANDO CRIAR MATCHES SIMPLES:")
        print(f"   User1: {user1_id}")
        print(f"   User2: {user2_id}")
        print(f"   Conexão: {connection_id}")
        
        # 1. Buscar filmes do user1
        user1_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user1_id}
        ).fetchall()
        
        user1_movies = []
        for row in user1_result:
            movie_id = row[0]
            # Verificar se é like ou indicate
            action_result = db.session.execute(
                text('SELECT action FROM "MoviesReacted" WHERE user_id = :user_id AND movie_id = :movie_id'),
                {'user_id': user1_id, 'movie_id': movie_id}
            ).scalar()
            
            if action_result in ['like', 'indicate']:
                user1_movies.append(str(movie_id))
        
        print(f"   User1 curtiu {len(user1_movies)} filmes")
        
        # 2. Buscar filmes do user2
        user2_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user2_id}
        ).fetchall()
        
        user2_movies = []
        for row in user2_result:
            movie_id = row[0]
            # Verificar se é like ou indicate
            action_result = db.session.execute(
                text('SELECT action FROM "MoviesReacted" WHERE user_id = :user_id AND movie_id = :movie_id'),
                {'user_id': user2_id, 'movie_id': movie_id}
            ).scalar()
            
            if action_result in ['like', 'indicate']:
                user2_movies.append(str(movie_id))
        
        print(f"   User2 curtiu {len(user2_movies)} filmes")
        
        # 3. Encontrar filmes em comum
        common_movies = []
        for movie1 in user1_movies:
            if movie1 in user2_movies:
                common_movies.append(int(movie1))
        
        print(f"   🎬 FILMES EM COMUM ENCONTRADOS: {len(common_movies)}")
        print(f"   IDs: {common_movies}")
        
        if not common_movies:
            print("   📭 Nenhum filme em comum")
            return False
        
        # 4. Salvar no banco
        db.session.execute(
            text("""
                UPDATE "UserConnections" 
                SET match_count = :match_count,
                    last_match_at = CURRENT_TIMESTAMP,
                    matched_movies = :matched_movies
                WHERE id = :connection_id
            """),
            {
                'match_count': len(common_movies),
                'matched_movies': json.dumps(common_movies),
                'connection_id': connection_id
            }
        )
        
        db.session.commit()
        print(f"   ✅ {len(common_movies)} MATCHES SALVOS NO BANCO!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR no create_matches_simple: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return False

# ============================================================================
# ROTA DE DEBUG
# ============================================================================

@movies_bp.route('/debug')
def debug_route():
    """Rota de debug para verificar tudo"""
    try:
        debug_matches_system()
        return jsonify({'success': True, 'message': 'Debug executado. Verifique os logs do servidor.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================================================
# ROTA PARA FORÇAR CRIAÇÃO DE MATCHES
# ============================================================================

@movies_bp.route('/force_create_matches', methods=['POST'])
def force_create_matches():
    """Força a criação de matches para TODAS as conexões"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"\n🎯 FORÇANDO CRIAÇÃO DE MATCHES PARA USER {user_id}")
        
        # Buscar todas as conexões
        connections = db.session.execute(
            text("""
                SELECT id, user1_id, user2_id 
                FROM "UserConnections" 
                WHERE (user1_id = :user_id OR user2_id = :user_id) 
                AND is_active = TRUE
            """),
            {'user_id': user_id}
        ).fetchall()
        
        results = []
        
        for conn in connections:
            connection_id = conn[0]
            user1_id = conn[1]
            user2_id = conn[2]
            
            print(f"\n  🔍 Processando conexão {connection_id}:")
            print(f"     User1: {user1_id}, User2: {user2_id}")
            
            # Zerar matches existentes
            db.session.execute(
                text("""
                    UPDATE "UserConnections" 
                    SET match_count = 0, matched_movies = '[]'
                    WHERE id = :connection_id
                """),
                {'connection_id': connection_id}
            )
            
            # Criar novos matches
            success = create_matches_simple(user1_id, user2_id, connection_id)
            
            results.append({
                'connection_id': connection_id,
                'success': success,
                'user1': user1_id,
                'user2': user2_id
            })
        
        db.session.commit()
        
        # Fazer debug após atualização
        debug_matches_system()
        
        return jsonify({
            'success': True,
            'message': f'Processadas {len(results)} conexões',
            'results': results
        })
        
    except Exception as e:
        print(f"❌ ERROR em force_create_matches: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA PARA TESTAR MATCHES ESPECÍFICOS
# ============================================================================

@movies_bp.route('/test_matches/<int:target_user_id>')
def test_matches(target_user_id):
    """Testa matches com um usuário específico"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        current_user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"\n🧪 TESTANDO MATCHES ENTRE {current_user_id} E {target_user_id}")
        
        # 1. Filmes do usuário atual
        current_user_movies = db.session.execute(
            text("""
                SELECT movie_id, action 
                FROM "MoviesReacted" 
                WHERE user_id = :user_id 
                AND action IN ('like', 'indicate')
            """),
            {'user_id': current_user_id}
        ).fetchall()
        
        current_movies = [str(row[0]) for row in current_user_movies]
        print(f"   Usuário {current_user_id} curtiu: {len(current_movies)} filmes")
        print(f"   IDs: {current_movies[:10]}...")  # Mostrar só 10
        
        # 2. Filmes do usuário alvo
        target_user_movies = db.session.execute(
            text("""
                SELECT movie_id, action 
                FROM "MoviesReacted" 
                WHERE user_id = :user_id 
                AND action IN ('like', 'indicate')
            """),
            {'user_id': target_user_id}
        ).fetchall()
        
        target_movies = [str(row[0]) for row in target_user_movies]
        print(f"   Usuário {target_user_id} curtiu: {len(target_movies)} filmes")
        print(f"   IDs: {target_movies[:10]}...")  # Mostrar só 10
        
        # 3. Encontrar filmes em comum
        common_movies = []
        for movie_id in current_movies:
            if movie_id in target_movies:
                common_movies.append(int(movie_id))
        
        print(f"\n   🎬 FILMES EM COMUM: {len(common_movies)}")
        print(f"   IDs: {common_movies}")
        
        # 4. Verificar se já existe conexão
        connection = db.session.execute(
            text("""
                SELECT id, match_count, matched_movies 
                FROM "UserConnections" 
                WHERE (user1_id = :user1 AND user2_id = :user2) 
                   OR (user1_id = :user2 AND user2_id = :user1)
            """),
            {'user1': current_user_id, 'user2': target_user_id}
        ).fetchone()
        
        connection_info = None
        if connection:
            matched_movies = connection[2]
            if matched_movies is None:
                existing_matches = []
            elif isinstance(matched_movies, str):
                try:
                    existing_matches = json.loads(matched_movies)
                except:
                    existing_matches = []
            else:
                existing_matches = matched_movies
            
            connection_info = {
                'connection_id': connection[0],
                'match_count_in_db': connection[1],
                'matches_in_db': existing_matches
            }
        
        return jsonify({
            'success': True,
            'current_user_id': current_user_id,
            'target_user_id': target_user_id,
            'current_user_movies_count': len(current_movies),
            'target_user_movies_count': len(target_movies),
            'common_movies_count': len(common_movies),
            'common_movies': common_movies,
            'connection_info': connection_info
        })
        
    except Exception as e:
        print(f"❌ ERROR em test_matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA DE MATCHES SIMPLIFICADA
# ============================================================================

@movies_bp.route('/matches')
def get_matches():
    """Retorna todos os matches do usuário logado - VERSÃO SIMPLIFICADA"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"\n🔍 BUSCANDO MATCHES PARA USER_ID={user_id}")
        
        # Buscar conexões
        connections_data = db.session.execute(
            text("""
                SELECT 
                    uc.id as connection_id,
                    uc.match_count,
                    uc.last_match_at,
                    uc.matched_movies,
                    CASE 
                        WHEN uc.user1_id = :user_id THEN uc.user2_id 
                        ELSE uc.user1_id 
                    END as partner_id,
                    mu.username as partner_username
                FROM "UserConnections" uc
                JOIN "MoviesUsers" mu ON mu.id = CASE 
                    WHEN uc.user1_id = :user_id THEN uc.user2_id 
                    ELSE uc.user1_id 
                END
                WHERE (uc.user1_id = :user_id OR uc.user2_id = :user_id) 
                  AND uc.is_active = TRUE
                ORDER BY uc.last_match_at DESC
            """),
            {'user_id': user_id}
        ).fetchall()
        
        print(f"   Conexões encontradas: {len(connections_data)}")
        
        all_matches = []
        
        for row in connections_data:
            connection_id = row[0]
            match_count = row[1]
            last_match_at = row[2]
            matched_movies = row[3]
            partner_id = row[4]
            partner_username = row[5]
            
            print(f"\n   📋 Conexão {connection_id}:")
            print(f"      Partner: {partner_username} (ID: {partner_id})")
            print(f"      Match count: {match_count}")
            print(f"      Raw matched_movies: {matched_movies}")
            
            # Converter matched_movies para lista
            movies_list = []
            if matched_movies:
                if isinstance(matched_movies, str):
                    try:
                        movies_list = json.loads(matched_movies)
                    except:
                        movies_list = []
                else:
                    movies_list = matched_movies
            
            print(f"      Matches list: {movies_list}")
            print(f"      Quantidade: {len(movies_list)}")
            
            for movie_id in movies_list:
                all_matches.append({
                    'connection_id': connection_id,
                    'movie_id': movie_id,
                    'partner_id': partner_id,
                    'partner_username': partner_username,
                    'match_count': match_count,
                    'last_match_at': last_match_at.isoformat() if last_match_at else None
                })
        
        print(f"\n✅ TOTAL DE MATCHES ENCONTRADOS: {len(all_matches)}")
        
        return jsonify({
            'success': True,
            'matches': all_matches,
            'total_matches': len(all_matches)
        })
        
    except Exception as e:
        print(f"❌ ERROR ao buscar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA PARA REGISTRAR AÇÃO (SIMPLIFICADA)
# ============================================================================

@movies_bp.route('/action', methods=['POST'])
def register_action():
    """Registra a ação do usuário no banco de dados"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        data = request.get_json()
        movie_id = data.get('movie_id')
        action = data.get('action')
        user_id = session['user_id']
        
        if not movie_id or not action:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        print(f"\n🎬 REGISTRANDO AÇÃO: user={user_id}, movie={movie_id}, action={action}")
        
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Converter para string
        movie_id_str = str(movie_id)
        
        # Inserir ou atualizar reação
        db.session.execute(
            text("""
                INSERT INTO "MoviesReacted" (user_id, movie_id, action, reacted_at) 
                VALUES (:user_id, :movie_id, :action, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, movie_id) 
                DO UPDATE SET action = EXCLUDED.action, reacted_at = CURRENT_TIMESTAMP
            """),
            {'user_id': user_id, 'movie_id': movie_id_str, 'action': action}
        )
        
        db.session.commit()
        
        # Se foi like ou indicate, verificar matches
        if action in ['like', 'indicate']:
            print(f"   🔄 Verificando matches para filme {movie_id}")
            
            # Buscar conexões
            connections = db.session.execute(
                text("""
                    SELECT id, user1_id, user2_id 
                    FROM "UserConnections" 
                    WHERE (user1_id = :user_id OR user2_id = :user_id) 
                    AND is_active = TRUE
                """),
                {'user_id': user_id}
            ).fetchall()
            
            for connection in connections:
                connection_id = connection[0]
                user1_id = connection[1]
                user2_id = connection[2]
                
                partner_id = user2_id if user1_id == user_id else user1_id
                
                print(f"   👥 Verificando parceiro {partner_id} na conexão {connection_id}")
                
                # Verificar se o parceiro também curtiu
                partner_reaction = db.session.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM "MoviesReacted" 
                        WHERE user_id = :partner_id 
                        AND movie_id = :movie_id 
                        AND action IN ('like', 'indicate')
                    """),
                    {'partner_id': partner_id, 'movie_id': movie_id_str}
                ).scalar()
                
                if partner_reaction > 0:
                    print(f"   🎉 Parceiro também curtiu! Criando match...")
                    
                    # Buscar matches atuais
                    current_matches = db.session.execute(
                        text('SELECT matched_movies FROM "UserConnections" WHERE id = :connection_id'),
                        {'connection_id': connection_id}
                    ).scalar()
                    
                    # Converter para lista
                    if current_matches is None:
                        matches_list = []
                    elif isinstance(current_matches, str):
                        try:
                            matches_list = json.loads(current_matches)
                        except:
                            matches_list = []
                    else:
                        matches_list = current_matches
                    
                    print(f"   📋 Matches atuais: {matches_list}")
                    
                    # Adicionar se não existir
                    if movie_id not in matches_list:
                        matches_list.append(movie_id)
                        
                        # Atualizar conexão
                        db.session.execute(
                            text("""
                                UPDATE "UserConnections" 
                                SET match_count = :match_count,
                                    last_match_at = CURRENT_TIMESTAMP,
                                    matched_movies = :matched_movies
                                WHERE id = :connection_id
                            """),
                            {
                                'match_count': len(matches_list),
                                'matched_movies': json.dumps(matches_list),
                                'connection_id': connection_id
                            }
                        )
                        
                        db.session.commit()
                        print(f"   ✅ Match adicionado! Total: {len(matches_list)}")
        
        return jsonify({
            'success': True,
            'action': action, 
            'movie_id': movie_id,
            'message': f'Ação {action} registrada com sucesso'
        })
        
    except Exception as e:
        print(f"❌ ERROR na rota /action: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA DE CONEXÃO (SIMPLIFICADA)
# ============================================================================

@movies_bp.route('/connect', methods=['POST'])
def connect_users():
    """Conecta dois usuários"""
    try:
        print("\n🔗 /connect ROTA CHAMADA")
        
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Usuário não logado'}), 401
        
        current_user_id = session['user_id']
        data = request.get_json()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'ID do usuário alvo é obrigatório'}), 400
        
        try:
            target_user_id = int(target_user_id)
        except:
            return jsonify({'success': False, 'message': 'ID do usuário deve ser um número'}), 400
        
        if current_user_id == target_user_id:
            return jsonify({'success': False, 'message': 'Não é possível conectar consigo mesmo'}), 400
        
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'success': False, 'message': 'Database não configurado'}), 500
        
        print(f"   🔍 Verificando usuário alvo: {target_user_id}")
        
        target_user = db.session.execute(
            text('SELECT id, username FROM "MoviesUsers" WHERE id = :target_id'),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        print(f"   ✅ Usuário alvo encontrado: {target_user[1]}")
        
        # Verificar se já existe conexão
        existing_connection = db.session.execute(
            text("""
                SELECT id FROM "UserConnections" 
                WHERE (user1_id = :user1 AND user2_id = :user2) 
                   OR (user1_id = :user2 AND user2_id = :user1)
            """),
            {'user1': current_user_id, 'user2': target_user_id}
        ).fetchone()
        
        if existing_connection:
            return jsonify({'success': False, 'message': 'Já existe uma conexão com este usuário'}), 400
        
        user1_id = min(current_user_id, target_user_id)
        user2_id = max(current_user_id, target_user_id)
        
        print(f"   🔗 Criando conexão entre {user1_id} e {user2_id}")
        
        # Criar conexão
        db.session.execute(
            text("""
                INSERT INTO "UserConnections" (user1_id, user2_id, match_count, matched_movies, is_active) 
                VALUES (:user1_id, :user2_id, 0, '[]', TRUE)
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        db.session.commit()
        
        # Buscar ID da conexão
        connection_result = db.session.execute(
            text('SELECT id FROM "UserConnections" WHERE user1_id = :user1_id AND user2_id = :user2_id'),
            {'user1_id': user1_id, 'user2_id': user2_id}
        ).fetchone()
        
        connection_id = connection_result[0] if connection_result else None
        
        print(f"   ✅ Conexão criada! ID: {connection_id}")
        
        # Criar matches imediatamente
        if connection_id:
            print(f"   🎯 Criando matches para a nova conexão...")
            create_matches_simple(user1_id, user2_id, connection_id)
        
        return jsonify({
            'success': True, 
            'message': 'Conexão estabelecida com sucesso!',
            'partner_id': target_user_id,
            'partner_username': target_user[1],
            'connection_id': connection_id
        })
        
    except Exception as e:
        print(f"❌ ERROR na conexão: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)[:200]}'}), 500

# ============================================================================
# OUTRAS ROTAS (MANTIDAS)
# ============================================================================

@movies_bp.route('/random')
def random_movie():
    """Busca um filme aleatório que o usuário ainda não reagiu"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"\n🎲 Buscando filme aleatório para user_id={user_id}")
        
        seen_movies_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
        print(f"   📊 Usuário já viu {len(seen_movies)} filmes")
        
        categories = {
            "popular": 700,
            "top_rated": 700, 
            "now_playing": 10,
            "upcoming": 10
        }
        
        max_attempts = 10
        
        for attempt in range(max_attempts):
            try:
                chosen_category = random.choice(list(categories.keys()))
                max_page = categories[chosen_category]
                random_page = random.randint(1, max_page)
                
                url = f"https://api.themoviedb.org/3/movie/{chosen_category}?api_key={TMDB_API_KEY}&language=pt-BR&page={random_page}"
                response = requests.get(url, timeout=5)
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                if data.get('results'):
                    valid_movies = [
                        movie for movie in data['results'] 
                        if (movie.get('vote_average', 0) >= 6.0 and 
                            movie.get('poster_path') and
                            movie.get('overview') and
                            str(movie.get('id')) not in seen_movies)
                    ]
                    
                    if not valid_movies:
                        continue
                    
                    movie = random.choice(valid_movies)
                    movie_id = movie.get('id')
                    
                    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
                    details_response = requests.get(details_url, timeout=5)
                    
                    if details_response.status_code != 200:
                        continue
                    
                    details_data = details_response.json()
                    
                    genres = []
                    if details_data.get('genres'):
                        genres = [genre['name'] for genre in details_data['genres']]
                    
                    # Buscar trailer
                    trailer_url = None
                    videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
                    videos_response = requests.get(
                        videos_url,
                        params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
                        timeout=5
                    )
                    
                    if videos_response.status_code == 200:
                        videos_data = videos_response.json()
                        for video in videos_data.get('results', []):
                            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                                youtube_key = video.get('key')
                                if youtube_key:
                                    trailer_url = f"https://www.youtube.com/watch?v={youtube_key}"
                                    break
                    
                    vote_average = movie.get('vote_average', 0)
                    if vote_average is None:
                        vote_average = 0
                        
                    release_date = movie.get('release_date', '')
                    release_year = release_date.split('-')[0] if release_date else ''
                    
                    print(f"   ✅ Filme encontrado: {movie.get('title')} (ID: {movie_id})")
                    
                    return jsonify({
                        'success': True,
                        'title': movie.get('title', 'Título não disponível'),
                        'backdrop_path': f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path', '')}" if movie.get('backdrop_path') else '',
                        'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get('poster_path') else '',
                        'overview': movie.get('overview', 'Descrição não disponível'),
                        'id': movie_id,
                        'vote_average': round(vote_average, 1),
                        'release_year': release_year,
                        'genres': genres,
                        'category': chosen_category,
                        'trailer_url': trailer_url,
                        'attempts': attempt + 1,
                        'total_seen': len(seen_movies)
                    })
                    
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                continue
        
        return jsonify({
            'success': False,
            'error': 'Você já reagiu a todos os filmes disponíveis!',
            'total_seen': len(seen_movies)
        }), 404
        
    except Exception as e:
        print(f"❌ ERROR crítico: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@movies_bp.route('/connections')
def get_user_connections():
    """Retorna as conexões ativas do usuário"""
    try:
        if 'user_id' not in session:
            return jsonify({'connections': []})
        
        current_user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'connections': []})
        
        connections = db.session.execute(
            text("""
                SELECT 
                    uc.id,
                    CASE 
                        WHEN uc.user1_id = :user_id THEN uc.user2_id 
                        ELSE uc.user1_id 
                    END as partner_id,
                    mu.username as partner_username,
                    uc.connected_at,
                    uc.match_count
                FROM "UserConnections" uc
                JOIN "MoviesUsers" mu ON mu.id = CASE 
                    WHEN uc.user1_id = :user_id THEN uc.user2_id 
                    ELSE uc.user1_id 
                END
                WHERE (uc.user1_id = :user_id OR uc.user2_id = :user_id) AND uc.is_active = TRUE
                ORDER BY uc.connected_at DESC
            """),
            {'user_id': current_user_id}
        ).fetchall()
        
        connection_list = []
        for conn in connections:
            connection_list.append({
                'connection_id': conn[0],
                'partner_id': conn[1],
                'partner_username': conn[2],
                'connected_at': conn[3].isoformat() if conn[3] else None,
                'match_count': conn[4] or 0
            })
        
        return jsonify({'connections': connection_list})
        
    except Exception as e:
        print(f"❌ ERROR ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})
