from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text
import requests
import random
import json

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

# ============================================================================
# FUNÇÃO ÚNICA E SIMPLES PARA CRIAR MATCHES
# ============================================================================

def create_matches_between_users(user1_id, user2_id, connection_id):
    """Encontra TODOS os filmes que ambos usuários curtiram e cria matches"""
    try:
        db = current_app.extensions.get('db')
        if db is None:
            print("❌ ERROR: Database não encontrado")
            return False
        
        print(f"🎯 CRIANDO MATCHES: user1={user1_id}, user2={user2_id}, connection={connection_id}")
        
        # Buscar filmes que user1 curtiu
        user1_likes = db.session.execute(
            text("""
                SELECT movie_id FROM "MoviesReacted" 
                WHERE user_id = :user_id AND action IN ('like', 'indicate')
            """),
            {'user_id': user1_id}
        ).fetchall()
        
        # Buscar filmes que user2 curtiu  
        user2_likes = db.session.execute(
            text("""
                SELECT movie_id FROM "MoviesReacted" 
                WHERE user_id = :user_id AND action IN ('like', 'indicate')
            """),
            {'user_id': user2_id}
        ).fetchall()
        
        # Converter para conjuntos de strings
        user1_movies = {str(row[0]) for row in user1_likes}
        user2_movies = {str(row[0]) for row in user2_likes}
        
        print(f"📊 User {user1_id} curtiu {len(user1_movies)} filmes")
        print(f"📊 User {user2_id} curtiu {len(user2_movies)} filmes")
        
        # Encontrar filmes em comum
        common_movies = user1_movies.intersection(user2_movies)
        
        print(f"🎬 Filmes em comum encontrados: {len(common_movies)}")
        
        if not common_movies:
            print("📭 Nenhum filme em comum")
            return False
        
        # Converter para lista de inteiros
        matches_list = [int(movie_id) for movie_id in common_movies]
        
        print(f"✅ Criando {len(matches_list)} matches: {matches_list}")
        
        # Atualizar a conexão com todos os matches
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
        print(f"🎉 {len(matches_list)} MATCHES CRIADOS com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR ao criar matches: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return False

# ============================================================================
# ROTA DE CONEXÃO - SIMPLIFICADA
# ============================================================================

@movies_bp.route('/connect', methods=['POST'])
def connect_users():
    """Conecta dois usuários e cria matches imediatamente"""
    try:
        print("🔗 /connect rota chamada")
        
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Usuário não logado'}), 401
        
        current_user_id = session['user_id']
        data = request.get_json()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'ID do usuário alvo é obrigatório'}), 400
        
        try:
            target_user_id = int(target_user_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID do usuário deve ser um número'}), 400
        
        if current_user_id == target_user_id:
            return jsonify({'success': False, 'message': 'Não é possível conectar consigo mesmo'}), 400
        
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'success': False, 'message': 'Database não configurado'}), 500
        
        print(f"🔍 Verificando usuário alvo: {target_user_id}")
        
        target_user = db.session.execute(
            text('SELECT id, username FROM "MoviesUsers" WHERE id = :target_id'),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        print(f"✅ Usuário alvo encontrado: {target_user[1]}")
        
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
        
        print(f"🔗 Criando conexão entre {user1_id} e {user2_id}")
        
        # Criar conexão
        db.session.execute(
            text("""
                INSERT INTO "UserConnections" (user1_id, user2_id, match_count, matched_movies, is_active) 
                VALUES (:user1_id, :user2_id, 0, '[]', TRUE)
                RETURNING id
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        # Buscar ID da conexão
        connection_result = db.session.execute(
            text('SELECT id FROM "UserConnections" WHERE user1_id = :user1_id AND user2_id = :user2_id'),
            {'user1_id': user1_id, 'user2_id': user2_id}
        ).fetchone()
        
        connection_id = connection_result[0]
        
        db.session.commit()
        
        print(f"✅ Conexão criada (ID: {connection_id})")
        
        # 🎯 CRIAR MATCHES IMEDIATAMENTE
        create_matches_between_users(user1_id, user2_id, connection_id)
        
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
        return jsonify({'success': False, 'message': f'Erro interno do servidor: {str(e)[:100]}'}), 500

# ============================================================================
# ROTA PARA VERIFICAR/ATUALIZAR MATCHES
# ============================================================================

@movies_bp.route('/update_matches/<int:connection_id>', methods=['POST'])
def update_matches(connection_id):
    """Atualiza os matches para uma conexão específica"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Verificar se a conexão pertence ao usuário
        connection = db.session.execute(
            text("""
                SELECT user1_id, user2_id FROM "UserConnections" 
                WHERE id = :connection_id AND is_active = TRUE
            """),
            {'connection_id': connection_id}
        ).fetchone()
        
        if not connection:
            return jsonify({'success': False, 'error': 'Conexão não encontrada'}), 404
        
        user1_id = connection[0]
        user2_id = connection[1]
        
        # Verificar se o usuário tem acesso
        if user_id not in [user1_id, user2_id]:
            return jsonify({'success': False, 'error': 'Não autorizado'}), 403
        
        print(f"🔄 Atualizando matches para conexão {connection_id}")
        
        # Buscar matches atuais
        current_matches = db.session.execute(
            text('SELECT matched_movies FROM "UserConnections" WHERE id = :connection_id'),
            {'connection_id': connection_id}
        ).scalar()
        
        # Limpar matches antigos
        db.session.execute(
            text("""
                UPDATE "UserConnections" 
                SET match_count = 0, matched_movies = '[]'
                WHERE id = :connection_id
            """),
            {'connection_id': connection_id}
        )
        
        db.session.commit()
        
        # Recriar todos os matches
        success = create_matches_between_users(user1_id, user2_id, connection_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Matches atualizados com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nenhum match encontrado'
            })
        
    except Exception as e:
        print(f"❌ ERROR ao atualizar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

# ============================================================================
# ROTA PARA MATCHES (SIMPLIFICADA)
# ============================================================================

@movies_bp.route('/matches')
def get_matches():
    """Retorna todos os matches do usuário logado"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"🔍 Buscando matches para user_id={user_id}")
        
        # Buscar conexões com matches
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
                  AND uc.match_count > 0
                ORDER BY uc.last_match_at DESC
            """),
            {'user_id': user_id}
        ).fetchall()
        
        all_matches = []
        
        for row in connections_data:
            connection_id = row[0]
            match_count = row[1]
            last_match_at = row[2]
            matched_movies = row[3]
            partner_id = row[4]
            partner_username = row[5]
            
            # Converter matched_movies para lista
            if matched_movies is None:
                movies_list = []
            elif isinstance(matched_movies, str):
                movies_list = json.loads(matched_movies)
            else:
                movies_list = matched_movies
            
            print(f"📋 Conexão {connection_id} tem {len(movies_list)} matches")
            
            for movie_id in movies_list:
                all_matches.append({
                    'connection_id': connection_id,
                    'movie_id': movie_id,
                    'partner_id': partner_id,
                    'partner_username': partner_username,
                    'match_count': match_count,
                    'last_match_at': last_match_at.isoformat() if last_match_at else None
                })
        
        print(f"✅ Total de matches: {len(all_matches)}")
        
        return jsonify({
            'success': True,
            'matches': all_matches,
            'total_matches': len(all_matches)
        })
        
    except Exception as e:
        print(f"❌ ERROR ao buscar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

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
        
        print(f"🎬 REGISTER ACTION: user={user_id}, movie={movie_id}, action={action}")
        
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
        
        # Se foi like ou indicate, verificar se há novas matches
        if action in ['like', 'indicate']:
            print(f"🔄 Verificando novas matches para filme {movie_id}")
            
            # Buscar todas as conexões do usuário
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
                
                # Verificar se o parceiro também curtiu este filme
                partner_id = user2_id if user1_id == user_id else user1_id
                
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
                    print(f"🎉 Novo match encontrado! Adicionando filme {movie_id} à conexão {connection_id}")
                    
                    # Buscar matches atuais
                    current_matches = db.session.execute(
                        text('SELECT matched_movies FROM "UserConnections" WHERE id = :connection_id'),
                        {'connection_id': connection_id}
                    ).scalar()
                    
                    # Converter para lista
                    if current_matches is None:
                        matches_list = []
                    elif isinstance(current_matches, str):
                        matches_list = json.loads(current_matches)
                    else:
                        matches_list = current_matches
                    
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
                        print(f"✅ Match adicionado!")
        
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
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

# ============================================================================
# ROTAS RESTANTES (mantidas iguais)
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
        
        print(f"🎲 Buscando filme aleatório para user_id={user_id}")
        
        seen_movies_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
        print(f"📊 Usuário já viu {len(seen_movies)} filmes")
        
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
                    
                    print(f"✅ Filme encontrado: {movie.get('title')} (ID: {movie_id})")
                    
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

@movies_bp.route('/movie/<int:movie_id>')
def get_movie_details(movie_id):
    """Retorna detalhes de um filme específico"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Filme não encontrado'}), 404
        
        movie_data = response.json()
        
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
        
        return jsonify({
            'success': True,
            'movie': {
                'id': movie_data.get('id'),
                'title': movie_data.get('title', 'Título não disponível'),
                'overview': movie_data.get('overview', 'Descrição não disponível'),
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path', '')}" if movie_data.get('poster_path') else '',
                'backdrop_path': f"https://image.tmdb.org/t/p/original{movie_data.get('backdrop_path', '')}" if movie_data.get('backdrop_path') else '',
                'release_date': movie_data.get('release_date', ''),
                'vote_average': round(movie_data.get('vote_average', 0), 1),
                'genres': [genre['name'] for genre in movie_data.get('genres', [])],
                'trailer_url': trailer_url
            }
        })
        
    except Exception as e:
        print(f"❌ ERROR ao buscar detalhes do filme: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

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
        
        print(f"🔍 Buscando conexões para user_id={current_user_id}")
        
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
        
        print(f"✅ Encontradas {len(connection_list)} conexões")
        
        return jsonify({'connections': connection_list})
        
    except Exception as e:
        print(f"❌ ERROR ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})
