from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text
import requests
import random
import os
import json
import math

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

def get_movie_trailer(movie_id):
    """Busca o trailer do filme na API do TMDB"""
    try:
        videos_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
        videos_response = requests.get(
            videos_url,
            params={'api_key': TMDB_API_KEY, 'language': 'pt-BR'},
            timeout=5
        )
        
        if videos_response.status_code == 200:
            videos_data = videos_response.json()
            
            # Procurar por trailers no YouTube
            for video in videos_data.get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    youtube_key = video.get('key')
                    if youtube_key:
                        return f"https://www.youtube.com/watch?v={youtube_key}"
            
            # Fallback: qualquer trailer do YouTube
            for video in videos_data.get('results', []):
                if video.get('site') == 'YouTube' and video.get('key'):
                    youtube_key = video.get('key')
                    return f"https://www.youtube.com/watch?v={youtube_key}"
        
        return None  # Nenhum trailer encontrado
        
    except Exception as e:
        print(f"Erro ao buscar trailer: {e}")
        return None

def weighted_movie_selection(movies):
    """
    Seleção ponderada de filmes baseada na nota (vote_average).
    Filmes com notas mais altas têm maior probabilidade de serem escolhidos.
    """
    if not movies:
        return None
    
    # Ordenar filmes por nota (decrescente)
    sorted_movies = sorted(movies, key=lambda x: x.get('vote_average', 0), reverse=True)
    
    # Criar pesos baseados na posição (os primeiros têm peso maior)
    # Usamos uma função exponencial decrescente
    weights = []
    for i, movie in enumerate(sorted_movies):
        # Peso decai exponencialmente: 1, 0.8, 0.64, 0.512, ...
        weight = math.pow(0.8, i)  # 0.8 é o fator de decaimento
        weights.append(weight)
    
    # Normalizar pesos para soma = 1
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    
    # Escolher filme com base nos pesos
    return random.choices(sorted_movies, weights=normalized_weights, k=1)[0]

# ============================================================================
# SISTEMA DE MATCHES SIMPLIFICADO (ATUALIZADO PARA NEON)
# ============================================================================

def check_and_create_matches(user_id, movie_id, action):
    """Verifica e cria matches quando dois usuários reagem ao mesmo filme"""
    try:
        # Só verifica matches para likes e indicações
        if action not in ['like', 'indicate']:
            return
        
        db = current_app.extensions.get('db')
        if db is None:
            print("❌ ERROR: Database não encontrado em check_and_create_matches")
            return
        
        print(f"🔄 DEBUG: Verificando matches para user_id={user_id}, movie_id={movie_id}, action={action}")
        
        # Buscar conexões ativas do usuário
        connections = db.session.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN user1_id = :user_id THEN user2_id 
                        ELSE user1_id 
                    END as partner_id,
                    id as connection_id
                FROM "UserConnections" 
                WHERE (user1_id = :user_id OR user2_id = :user_id) AND is_active = TRUE
            """),
            {'user_id': user_id}
        ).fetchall()
        
        print(f"🔄 DEBUG: Encontradas {len(connections)} conexões ativas")
        
        for connection in connections:
            partner_id = connection[0]
            connection_id = connection[1]
            
            # Verificar se o parceiro também curtiu/indicou este filme
            partner_reaction = db.session.execute(
                text("""
                    SELECT action FROM "MoviesReacted" 
                    WHERE user_id = :partner_id AND movie_id = :movie_id 
                    AND action IN ('like', 'indicate')
                """),
                {'partner_id': partner_id, 'movie_id': movie_id}
            ).fetchone()
            
            if partner_reaction:
                print(f"✅ DEBUG: MATCH ENCONTRADO! user_id={user_id} e partner_id={partner_id} reagiram ao filme {movie_id}")
                # 🎉 MATCH ENCONTRADO! Atualizar a conexão
                update_connection_with_match(db, connection_id, movie_id)
        
        db.session.commit()
        
    except Exception as e:
        print(f"❌ ERROR ao verificar matches: {str(e)}")
        if 'db' in locals():
            db.session.rollback()

def update_connection_with_match(db, connection_id, movie_id):
    """Atualiza a conexão com um novo match usando JSON"""
    try:
        print(f"🔄 DEBUG: Atualizando match para connection_id={connection_id}, movie_id={movie_id}")
        
        # Buscar matches atuais
        result = db.session.execute(
            text('SELECT matched_movies FROM "UserConnections" WHERE id = :connection_id'),
            {'connection_id': connection_id}
        ).fetchone()
        
        if result:
            current_matches = result[0] or '[]'
            matches_list = json.loads(current_matches)
            
            print(f"🔄 DEBUG: Matches atuais: {matches_list}")
            
            # Adicionar novo match se não existir
            if movie_id not in matches_list:
                matches_list.append(movie_id)
                
                # Atualizar a conexão
                db.session.execute(
                    text("""
                        UPDATE "UserConnections" 
                        SET match_count = match_count + 1,
                            last_match_at = CURRENT_TIMESTAMP,
                            matched_movies = :matched_movies
                        WHERE id = :connection_id
                    """),
                    {
                        'matched_movies': json.dumps(matches_list),
                        'connection_id': connection_id
                    }
                )
                
                print(f"🎉 SUCCESS: NOVO MATCH - Conexão {connection_id} - Filme {movie_id}")
                
    except Exception as e:
        print(f"❌ ERROR ao atualizar match: {str(e)}")

# ============================================================================
# SISTEMA DE CONEXÃO ENTRE USUÁRIOS (ATUALIZADO PARA NEON)
# ============================================================================

@movies_bp.route('/connect', methods=['POST'])
def connect_users():
    """Conecta dois usuários para compartilhar matches"""
    try:
        print("🎯 DEBUG: /connect rota chamada")
        
        # Verificar se usuário está logado
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Usuário não logado'}), 401
        
        current_user_id = session['user_id']
        data = request.get_json()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            return jsonify({'success': False, 'message': 'ID do usuário alvo é obrigatório'}), 400
        
        # CONVERTER PARA INTEIRO
        try:
            target_user_id = int(target_user_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'ID do usuário deve ser um número'}), 400
        
        # Verificar se não está tentando conectar consigo mesmo
        if current_user_id == target_user_id:
            return jsonify({'success': False, 'message': 'Não é possível conectar consigo mesmo'}), 400
        
        # Acessar Database (SQLAlchemy)
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'success': False, 'message': 'Database não configurado'}), 500
        
        print(f"🔄 DEBUG: Verificando existência do usuário alvo: {target_user_id}")
        
        # Verificar se o usuário alvo existe
        target_user = db.session.execute(
            text('SELECT id, username FROM "MoviesUsers" WHERE id = :target_id'),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        print(f"🔄 DEBUG: Usuário alvo encontrado: {target_user[1]}")
        
        # Verificar se já existe conexão entre os usuários
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
        
        # Criar nova conexão COM CAMPOS DE MATCH
        user1_id = min(current_user_id, target_user_id)
        user2_id = max(current_user_id, target_user_id)
        
        print(f"🔄 DEBUG: Criando conexão entre {user1_id} e {user2_id}")
        
        db.session.execute(
            text("""
                INSERT INTO "UserConnections" (user1_id, user2_id, match_count, matched_movies, is_active) 
                VALUES (:user1_id, :user2_id, 0, '[]', TRUE)
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        db.session.commit()
        
        print(f"✅ SUCCESS: Conexão criada entre {current_user_id} e {target_user_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Conexão estabelecida com sucesso!',
            'partner_id': target_user_id,
            'partner_username': target_user[1]
        })
        
    except Exception as e:
        print(f"❌ ERROR na conexão: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro interno do servidor: {str(e)[:100]}'}), 500

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
        
        print(f"🔄 DEBUG: Buscando conexões para user_id={current_user_id}")
        
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
        
        print(f"✅ DEBUG: Encontradas {len(connection_list)} conexões")
        
        return jsonify({'connections': connection_list})
        
    except Exception as e:
        print(f"❌ ERROR ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})

# ============================================================================
# ROTA PARA BUSCAR MATCHES
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
        
        print(f"🔄 DEBUG: Buscando matches para user_id={user_id}")
        
        # Buscar matches do usuário
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
        
        # Processar os dados para o frontend
        matches = []
        for row in connections_data:
            matched_movies = json.loads(row[3] or '[]')
            
            print(f"🔄 DEBUG: Connection {row[0]} tem {len(matched_movies)} matches")
            
            for movie_id in matched_movies:
                matches.append({
                    'connection_id': row[0],
                    'total_matches': row[1],
                    'last_match_at': row[2].isoformat() if row[2] else None,
                    'movie_id': movie_id,
                    'partner_id': row[4],
                    'partner_username': row[5]
                })
        
        print(f"✅ DEBUG: Total de matches encontrados: {len(matches)}")
        
        return jsonify({
            'success': True,
            'matches': matches,
            'total_matches': len(matches)
        })
        
    except Exception as e:
        print(f"❌ ERROR ao buscar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:100]}), 500

# ============================================================================
# SISTEMA DE FILMES (ATUALIZADO PARA PRIORIZAR NOTAS ALTAS)
# ============================================================================

@movies_bp.route('/random')
def random_movie():
    """Busca um filme aleatório que o usuário ainda não reagiu, priorizando filmes com notas altas"""
    try:
        # Verificar se usuário está logado
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        
        # Acessar Database
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"🔄 DEBUG: Buscando filme aleatório para user_id={user_id}")
        
        # Buscar filmes que o usuário já reagiu
        seen_movies_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
        print(f"🔄 DEBUG: Usuário já viu {len(seen_movies)} filmes")
        
        # Categorias otimizadas para notas altas
        # Usar mais "top_rated" e "popular" que geralmente têm notas melhores
        categories = {
            "top_rated": 800,    # Filmes melhor avaliados
            "popular": 700,      # Filmes populares (geralmente bem avaliados)
            "now_playing": 100,  # Filmes em cartaz
            "upcoming": 50       # Próximos lançamentos
        }
        
        # Tentar até 15 vezes buscar um filme válido E não visto
        max_attempts = 15
        
        for attempt in range(max_attempts):
            try:
                # Priorizar categorias com filmes melhor avaliados
                # 60% chance de escolher top_rated, 30% popular, 10% outras
                category_weights = {
                    "top_rated": 0.6,
                    "popular": 0.3,
                    "now_playing": 0.05,
                    "upcoming": 0.05
                }
                
                chosen_category = random.choices(
                    list(categories.keys()), 
                    weights=[category_weights[cat] for cat in categories.keys()],
                    k=1
                )[0]
                
                max_page = categories[chosen_category]
                # Para top_rated, usar páginas iniciais (notas mais altas)
                if chosen_category == "top_rated":
                    # Páginas 1-50 têm os filmes melhor avaliados
                    random_page = random.randint(1, min(50, max_page))
                else:
                    random_page = random.randint(1, max_page)
                
                print(f"🔄 DEBUG: Tentativa {attempt+1}: Categoria {chosen_category}, Página {random_page}")
                
                url = f"https://api.themoviedb.org/3/movie/{chosen_category}?api_key={TMDB_API_KEY}&language=pt-BR&page={random_page}"
                response = requests.get(url, timeout=5)
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                
                if data.get('results'):
                    # Filtrar filmes válidos E não vistos
                    valid_movies = []
                    for movie in data['results']:
                        # Critérios mais rigorosos para qualidade
                        vote_average = movie.get('vote_average', 0)
                        vote_count = movie.get('vote_count', 0)
                        poster_path = movie.get('poster_path')
                        overview = movie.get('overview')
                        movie_id_str = str(movie.get('id'))
                        
                        # Apenas filmes com:
                        # - Nota mínima 6.5 (aumentado de 6.0)
                        # - Pelo menos 100 votos (para ter credibilidade)
                        # - Poster e descrição disponíveis
                        # - Não visto antes
                        if (vote_average >= 6.5 and 
                            vote_count >= 100 and 
                            poster_path and 
                            overview and 
                            len(overview) > 50 and  # Descrição razoável
                            movie_id_str not in seen_movies):
                            
                            # Adicionar com peso baseado na nota
                            # Filmes com nota mais alta têm "peso" maior
                            movie['selection_weight'] = vote_average * vote_count / 1000
                            valid_movies.append(movie)
                    
                    if not valid_movies:
                        print(f"🔄 DEBUG: Tentativa {attempt+1}: Nenhum filme válido na categoria {chosen_category}")
                        continue
                    
                    print(f"🔄 DEBUG: Encontrados {len(valid_movies)} filmes válidos")
                    
                    # Ordenar por nota (decrescente) para priorizar os melhores
                    valid_movies.sort(key=lambda x: x.get('vote_average', 0), reverse=True)
                    
                    # Escolher filme: 70% chance de pegar um dos 3 melhores, 30% chance aleatória
                    if len(valid_movies) >= 3 and random.random() < 0.7:
                        # Escolher entre os 3 melhores
                        movie = random.choice(valid_movies[:3])
                    else:
                        # Seleção ponderada por nota
                        movie = weighted_movie_selection(valid_movies)
                    
                    movie_id = movie.get('id')
                    
                    # Buscar detalhes
                    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
                    details_response = requests.get(details_url, timeout=5)
                    
                    if details_response.status_code != 200:
                        continue
                    
                    details_data = details_response.json()
                    
                    # Extrair gêneros
                    genres = []
                    if details_data.get('genres'):
                        genres = [genre['name'] for genre in details_data['genres']]
                    
                    # BUSCAR TRAILER
                    trailer_url = get_movie_trailer(movie_id)
                    
                    # Tratamento de campos
                    vote_average = movie.get('vote_average', 0)
                    vote_count = movie.get('vote_count', 0)
                    if vote_average is None:
                        vote_average = 0
                        
                    release_date = movie.get('release_date', '')
                    release_year = release_date.split('-')[0] if release_date else ''
                    
                    # Calcular "score de qualidade" (nota ajustada pelo número de votos)
                    quality_score = vote_average * (1 + math.log10(max(vote_count, 1)) / 10)
                    
                    print(f"✅ SUCCESS: Filme encontrado - {movie.get('title')} (Nota: {vote_average}, Votos: {vote_count}, Score: {quality_score:.2f})")
                    
                    return jsonify({
                        'success': True,
                        'title': movie.get('title', 'Título não disponível'),
                        'backdrop_path': f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path', '')}" if movie.get('backdrop_path') else '',
                        'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get('poster_path') else '',
                        'overview': movie.get('overview', 'Descrição não disponível'),
                        'id': movie_id,
                        'vote_average': round(vote_average, 1),
                        'vote_count': vote_count,
                        'quality_score': round(quality_score, 2),
                        'release_year': release_year,
                        'genres': genres,
                        'category': chosen_category,
                        'trailer_url': trailer_url,
                        'attempts': attempt + 1,
                        'total_seen': len(seen_movies),
                        'selection_strategy': 'weighted_by_rating'
                    })
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ WARNING: Timeout na tentativa {attempt+1}")
                continue
            except Exception as e:
                print(f"⚠️ WARNING: Erro na tentativa {attempt+1}: {str(e)[:100]}")
                continue
        
        # Se chegou aqui, não encontrou filmes novos com critérios rigorosos
        # Tentar com critérios mais relaxados
        print(f"⚠️ WARNING: Nenhum filme novo encontrado após {max_attempts} tentativas. Relaxando critérios...")
        return jsonify({
            'success': False,
            'error': 'Você já reagiu a todos os filmes disponíveis que atendem aos critérios de qualidade!',
            'total_seen': len(seen_movies),
            'suggestion': 'Tente conectar com mais amigos para descobrir novos filmes!'
        }), 404
        
    except Exception as e:
        print(f"❌ ERROR crítico: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@movies_bp.route('/action', methods=['POST'])
def register_action():
    """Registra a ação do usuário no banco de dados E verifica matches"""
    try:
        # Verificar se usuário está logado
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        data = request.get_json()
        movie_id = data.get('movie_id')
        action = data.get('action')
        user_id = session['user_id']
        
        print(f"🔄 DEBUG: Registrando ação - user_id={user_id}, movie_id={movie_id}, action={action}")
        
        # Acessar Database
        db = current_app.extensions.get('db')
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        # Inserir ou atualizar a reação
        # PostgreSQL usa ON CONFLICT
        db.session.execute(
            text("""
                INSERT INTO "MoviesReacted" (user_id, movie_id, action, reacted_at) 
                VALUES (:user_id, :movie_id, :action, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, movie_id) 
                DO UPDATE SET action = EXCLUDED.action, reacted_at = CURRENT_TIMESTAMP
            """),
            {'user_id': user_id, 'movie_id': movie_id, 'action': action}
        )
        
        db.session.commit()
        
        print(f"✅ SUCCESS: Ação registrada para movie_id={movie_id}")
        
        # 🎯 CHECAR MATCHES APÓS REGISTRAR AÇÃO
        if action in ['like', 'indicate']:
            print(f"🔄 DEBUG: Verificando matches para ação {action}")
            check_and_create_matches(user_id, movie_id, action)
        
        return jsonify({
            'success': True,
            'action': action, 
            'movie_id': movie_id,
            'message': f'Ação {action} registrada com sucesso'
        })
        
    except Exception as e:
        print(f"❌ ERROR na rota /action: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)[:100]}), 500
