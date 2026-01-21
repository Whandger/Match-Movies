from flask import Blueprint, jsonify, session, request, current_app
from sqlalchemy import text
import requests
import random
import json

movies_bp = Blueprint('movies', __name__)

TMDB_API_KEY = '941fae9e612c2f209e18d77a5a760269'

# ============================================================================
# FUNÇÃO PRINCIPAL QUE CRIA MATCHES QUANDO O MODAL É ABERTO
# ============================================================================

def create_matches_on_modal_open():
    """Esta função é chamada quando o modal de histórico é aberto"""
    try:
        if 'user_id' not in session:
            print("❌ Usuário não logado")
            return False
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            print("❌ Database não encontrado")
            return False
        
        print(f"\n🎯 MODAL ABERTO - CRIANDO MATCHES PARA USER {user_id}")
        
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
        
        total_matches_created = 0
        
        for conn in connections:
            connection_id = conn[0]
            user1_id = conn[1]
            user2_id = conn[2]
            
            print(f"\n🔍 Processando conexão {connection_id} entre {user1_id} e {user2_id}")
            
            # 1. Buscar filmes que user1 curtiu
            user1_movies_result = db.session.execute(
                text("""
                    SELECT movie_id 
                    FROM "MoviesReacted" 
                    WHERE user_id = :user_id AND action IN ('like', 'indicate')
                """),
                {'user_id': user1_id}
            ).fetchall()
            
            user1_movies = [str(row[0]) for row in user1_movies_result]
            print(f"   User {user1_id} curtiu {len(user1_movies)} filmes")
            
            # 2. Buscar filmes que user2 curtiu
            user2_movies_result = db.session.execute(
                text("""
                    SELECT movie_id 
                    FROM "MoviesReacted" 
                    WHERE user_id = :user_id AND action IN ('like', 'indicate')
                """),
                {'user_id': user2_id}
            ).fetchall()
            
            user2_movies = [str(row[0]) for row in user2_movies_result]
            print(f"   User {user2_id} curtiu {len(user2_movies)} filmes")
            
            # 3. Encontrar filmes em comum
            common_movies = []
            for movie_id in user1_movies:
                if movie_id in user2_movies:
                    common_movies.append(int(movie_id))
            
            print(f"   🎬 Filmes em comum encontrados: {len(common_movies)}")
            print(f"   📋 IDs: {common_movies}")
            
            if common_movies:
                # 4. Salvar no campo matched_movies da tabela UserConnections
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
                print(f"   ✅ {len(common_movies)} matches salvos no banco!")
                total_matches_created += len(common_movies)
            else:
                print("   📭 Nenhum filme em comum")
        
        print(f"\n🎉 TOTAL DE MATCHES CRIADOS: {total_matches_created}")
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao criar matches: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.session.rollback()
        return False

# ============================================================================
# ROTA QUE O FRONTEND CHAMA QUANDO ABRE O MODAL
# ============================================================================

@movies_bp.route('/check_and_create_matches', methods=['POST'])
def check_and_create_matches_route():
    """Rota chamada quando o modal de histórico é aberto"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Usuário não logado'}), 401
        
        print("\n📞 FRONTEND CHAMOU: Modal de histórico aberto!")
        
        # Chamar a função que cria os matches
        success = create_matches_on_modal_open()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Matches verificados e criados com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao criar matches'
            })
        
    except Exception as e:
        print(f"❌ ERRO na rota: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTA PARA BUSCAR MATCHES (chamada pelo frontend para mostrar no modal)
# ============================================================================

@movies_bp.route('/matches')
def get_matches():
    """Retorna todos os matches do usuário logado - PARA MOSTRAR NO MODAL"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não logado'}), 401
        
        user_id = session['user_id']
        db = current_app.extensions.get('db')
        
        if db is None:
            return jsonify({'error': 'Database não configurado'}), 500
        
        print(f"\n🔍 Buscando matches para user_id={user_id}")
        
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
        
        print(f"📊 Conexões com matches: {len(connections_data)}")
        
        all_matches = []
        
        for row in connections_data:
            connection_id = row[0]
            match_count = row[1]
            last_match_at = row[2]
            matched_movies = row[3]
            partner_id = row[4]
            partner_username = row[5]
            
            print(f"\n📋 Conexão {connection_id}:")
            print(f"   Parceiro: {partner_username} (ID: {partner_id})")
            print(f"   Match count: {match_count}")
            
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
            
            print(f"   Matches: {movies_list}")
            print(f"   Quantidade: {len(movies_list)}")
            
            for movie_id in movies_list:
                all_matches.append({
                    'connection_id': connection_id,
                    'movie_id': movie_id,
                    'partner_id': partner_id,
                    'partner_username': partner_username,
                    'match_count': match_count,
                    'last_match_at': last_match_at.isoformat() if last_match_at else None
                })
        
        print(f"\n✅ TOTAL DE MATCHES: {len(all_matches)}")
        
        return jsonify({
            'success': True,
            'matches': all_matches,
            'total_matches': len(all_matches)
        })
        
    except Exception as e:
        print(f"❌ ERRO ao buscar matches: {str(e)}")
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# JAVASCRIPT ATUALIZADO PARA O FRONTEND
# ============================================================================
"""
// history.js ATUALIZADO

let historyModalIsVisible = false

// abrir modal
function openModalHistory(id) {
    document.getElementById(id).style.display = "flex";
    historyModalIsVisible = true;
    
    // 🎯 PRIMEIRO: Chamar API para criar matches
    fetch('/api/movies/check_and_create_matches', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Matches criados:', data);
        
        // 🎯 DEPOIS: Carregar os matches para mostrar
        loadMatches();
    })
    .catch(error => {
        console.error('Erro ao criar matches:', error);
        // Mesmo assim tenta carregar os matches
        loadMatches();
    });
}

// Fechar modal
function closeModalHistory(id) {
    document.getElementById(id).style.display = "none";
    historyModalIsVisible = false;
}

// Eventos de abrir modal e fechar
document.getElementById("history").onclick = function (e) {
    e.preventDefault();

    if (historyModalIsVisible === false) {
        openModalHistory("historyModal");
    } else {
        closeModalHistory("historyModal");
    }
};

// 🎯 FUNÇÃO PARA CARREGAR MATCHES (chamada DEPOIS de criar matches)
async function loadMatches() {
    try {
        const response = await fetch('/api/movies/matches');
        const data = await response.json();
        
        const matchesContainer = document.getElementById('matchesContainer');
        
        // Limpar container antes de adicionar novos matches
        matchesContainer.innerHTML = '';
        
        if (data.success && data.matches.length > 0) {
            // Para cada match, criar um novo elemento
            data.matches.forEach((match, index) => {
                createMatchElement(match, matchesContainer, index);
            });
        } else {
            // Mensagem quando não há matches
            matchesContainer.innerHTML = `
                <div style="text-align: center; color: white; padding: 40px;">
                    <p style="font-size: 18px; margin-bottom: 10px;">📭 Ainda não há matches</p>
                    <small>Continue curtindo filmes para encontrar matches com seu parceiro!</small>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar matches:', error);
    }
}

// 🎯 FUNÇÃO PARA CRIAR UM NOVO ELEMENTO DE MATCH
function createMatchElement(match, container, index) {
    // Criar a div principal do match
    const matchElement = document.createElement('div');
    matchElement.className = 'match-item';
    
    // Criar a imagem do filme
    const imgElement = document.createElement('img');
    imgElement.className = 'match-cover';
    imgElement.alt = "Imagem Do filme que deu match";
    
    // Criar o título do filme
    const titleElement = document.createElement('p');
    titleElement.className = 'match-title';
    titleElement.textContent = `Carregando...`;
    
    // Adicionar elementos ao match
    matchElement.appendChild(imgElement);
    matchElement.appendChild(titleElement);
    
    // Adicionar match ao container
    container.appendChild(matchElement);
    
    // Buscar detalhes do filme
    fetchMovieDetails(match.movie_id, imgElement, titleElement);
}

// 🎯 BUSCAR DETALHES DO FILME
async function fetchMovieDetails(movieId, imgElement, titleElement) {
    try {
        const response = await fetch(`https://api.themoviedb.org/3/movie/${movieId}?api_key=941fae9e612c2f209e18d77a5a760269&language=pt-BR`);
        const movieData = await response.json();
        
        // Atualizar imagem
        if (movieData.poster_path) {
            imgElement.src = `https://image.tmdb.org/t/p/w200${movieData.poster_path}`;
            imgElement.alt = movieData.title;
        } else {
            imgElement.style.backgroundColor = '#333';
        }
        
        // Atualizar título
        titleElement.textContent = movieData.title;
        
    } catch (error) {
        console.error('Erro ao buscar detalhes do filme:', error);
        titleElement.textContent = `Filme ID: ${movieId}`;
    }
}
"""

# ============================================================================
# ROTAS PARA REGISTRAR AÇÃO DE FILMES (mantidas)
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
        
        print(f"\n🎬 Registrando ação: user={user_id}, movie={movie_id}, action={action}")
        
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
        
        return jsonify({
            'success': True,
            'action': action, 
            'movie_id': movie_id,
            'message': f'Ação {action} registrada com sucesso'
        })
        
    except Exception as e:
        print(f"❌ ERRO na rota /action: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)[:200]}), 500

# ============================================================================
# ROTAS DE CONEXÃO (mantidas)
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
        
        target_user = db.session.execute(
            text('SELECT id, username FROM "MoviesUsers" WHERE id = :target_id'),
            {'target_id': target_user_id}
        ).fetchone()
        
        if not target_user:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
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
        
        # Criar conexão
        db.session.execute(
            text("""
                INSERT INTO "UserConnections" (user1_id, user2_id, match_count, matched_movies, is_active) 
                VALUES (:user1_id, :user2_id, 0, '[]', TRUE)
            """),
            {'user1_id': user1_id, 'user2_id': user2_id}
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Conexão estabelecida com sucesso!',
            'partner_id': target_user_id,
            'partner_username': target_user[1]
        })
        
    except Exception as e:
        print(f"❌ ERRO na conexão: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)[:200]}'}), 500

# ============================================================================
# OUTRAS ROTAS IMPORTANTES (mantidas)
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
        
        seen_movies_result = db.session.execute(
            text('SELECT movie_id FROM "MoviesReacted" WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).fetchall()
        
        seen_movies = [str(row[0]) for row in seen_movies_result]
        
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
        print(f"❌ ERRO crítico: {str(e)}")
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
        print(f"❌ ERRO ao buscar conexões: {str(e)}")
        return jsonify({'connections': []})
