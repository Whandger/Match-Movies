// ============================================
// VARIÁVEIS GLOBAIS E CONFIGURAÇÕES
// ============================================

let currentMovie = null;
let cardInner = document.querySelector(".cardInner");
let buttonsEnabled = true;
let movieQueue = [];
let isPreloading = false;
let shouldPreload = true;

// ============================================
// SISTEMA DE STREAMING (1 FILME POR VEZ)
// ============================================

async function preloadSingleMovie() {
    if (isPreloading || !shouldPreload) return;
    
    isPreloading = true;
    console.log(`🔄 Iniciando pré-carregamento de 1 filme...`);
    
    try {
        const response = await fetch('/api/movies/random');
        const data = await response.json();
        
        if (data.success && data.movie) {
            movieQueue.push(data.movie);
            console.log(`✅ 1 filme pré-carregado! Total na fila: ${movieQueue.length}`);
            
            if (data.movie.poster_path) {
                const img = new Image();
                img.src = data.movie.poster_path;
            }
        }
    } catch (error) {
        console.log('⚠️ Pré-carregamento falhou:', error);
    } finally {
        isPreloading = false;
        
        if (movieQueue.length < 2 && shouldPreload) {
            setTimeout(preloadSingleMovie, 500);
        }
    }
}

function getNextMovieFromQueue() {
    if (movieQueue.length > 0) {
        const nextMovie = movieQueue.shift();
        console.log(`🎬 Pegando filme da fila. Restantes: ${movieQueue.length}`);
        
        if (movieQueue.length === 0 && shouldPreload) {
            setTimeout(preloadSingleMovie, 300);
        }
        
        return nextMovie;
    }
    return null;
}

// ============================================
// FUNÇÕES PARA CONTROLE DOS BOTÕES
// ============================================

function disableButtons() {
    buttonsEnabled = false;
    const buttons = document.querySelectorAll('.reaction a');
    buttons.forEach(button => {
        button.style.pointerEvents = 'none';
        button.style.opacity = '0.5';
        button.style.cursor = 'not-allowed';
        button.style.filter = 'grayscale(80%)';
    });
}

function enableButtons() {
    buttonsEnabled = true;
    const buttons = document.querySelectorAll('.reaction a');
    buttons.forEach(button => {
        button.style.pointerEvents = 'auto';
        button.style.opacity = '1';
        button.style.cursor = 'pointer';
        button.style.filter = 'none';
    });
}
// ============================================
// ANIMAÇÕES VISUAIS (DA VERSÃO ANTIGA)
// ============================================

function showCardColorFeedback(action) {
    const cardInner = document.querySelector('.cardInner');
    if (!cardInner) return;
    
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        border-radius: inherit;
        z-index: 5;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.4s ease-out;
    `;
    
    let color;
    switch(action) {
        case 'like': color = 'rgba(52, 199, 89, 0.6)'; break;
        case 'indicate': color = 'rgba(0, 122, 255, 0.6)'; break;
        case 'dislike': color = 'rgba(255, 59, 48, 0.6)'; break;
    }
    
    overlay.style.background = color;
    cardInner.appendChild(overlay);
    
    setTimeout(() => overlay.style.opacity = '1', 10);
    addCardTiltEffect(action);
    
    setTimeout(() => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 500);
    }, 1000);
}

function addCardTiltEffect(action) {
    const cardInner = document.querySelector('.cardInner');
    if (!cardInner) return;
    
    let x = 0, rotation = 0;
    
    switch(action) {
        case 'like':
            x = -15;
            rotation = -5;
            break;
        case 'dislike':
            x = 15;
            rotation = 5;
            break;
        case 'indicate':
            x = 0;
            rotation = 0;
            break;
    }
    
    cardInner.style.transform = `translateX(${x}px) rotate(${rotation}deg)`;
    cardInner.style.transition = 'transform 0.3s ease-out';
    
    setTimeout(() => {
        cardInner.style.transform = '';
    }, 500);
}

function showButtonAnimation(action) {
    const buttons = document.querySelectorAll('.reaction a');
    
    buttons.forEach(button => {
        if (button.id === action) {
            // Animação de clique no botão
            button.style.transform = 'scale(0.85)';
            button.style.opacity = '0.7';
            
            setTimeout(() => {
                button.style.transform = 'scale(1)';
                button.style.opacity = '1';
            }, 200);
        }
    });
}

// ============================================
// FUNÇÕES DE API
// ============================================

function loadRandomMovie() {
    disableButtons();
    
    const queuedMovie = getNextMovieFromQueue();
    if (queuedMovie) {
        console.log('⚡ Filme carregado da fila (instantâneo)');
        displayMovie(queuedMovie);
        return;
    }
    
    console.log('🔄 Buscando primeiro filme...');
    fetch('/api/movies/random')
        .then(handleApiResponse)
        .then(data => {
            if (data.success && data.movie) {
                console.log('✅ Primeiro filme carregado');
                displayMovie(data.movie);
                
                if (shouldPreload && !isPreloading) {
                    setTimeout(preloadSingleMovie, 800);
                }
            } else {
                handleLoadError(new Error('Filme não encontrado'));
            }
        })
        .catch(error => handleLoadError(error));
}

function displayMovie(movieData) {
    console.log('🎬 Dados COMPLETOS do filme:', movieData);
    console.log('📷 Poster path:', movieData.poster_path);
    console.log('🎭 Gêneros disponíveis:', movieData.genres);
    
    if (!movieData.poster_path) {
        console.error('❌ ERRO: Filme sem poster_path!', movieData);
        handleLoadError(new Error('Filme sem imagem'));
        return;
    }
    
    currentMovie = movieData;
    console.log('🎬 Exibindo:', movieData.title);
    
    updateMovieDisplay(movieData);
    enableButtons();
}

// ============================================
// FUNÇÕES DE UI
// ============================================

function updateMovieDisplay(movieData) {
    updatePosterImage(movieData.poster_path);
    updateRatingInfo(movieData.vote_average, movieData.release_year);
    updateMovieDetails(movieData);
    updateTrailerButtonState(!!movieData.trailer_url);
    resetCardFlip();
    
    if (!movieData.trailer_url) {
        fetchMovieDetails(movieData.id);
    }
}

function updatePosterImage(posterPath) {
    try {
        const moviePicDiv = document.querySelector('.moviePic');
        if (!moviePicDiv) {
            console.error('❌ Elemento .moviePic não encontrado');
            return;
        }
        
        console.log('🖼️ Atualizando imagem para:', posterPath);
        
        if (posterPath && typeof posterPath === 'string' && posterPath.startsWith('http')) {
            moviePicDiv.style.backgroundImage = `url('${posterPath}')`;
            moviePicDiv.style.backgroundSize = 'cover';
            moviePicDiv.style.backgroundPosition = 'center';
            moviePicDiv.innerHTML = '';
        } else {
            console.warn('⚠️ Poster path inválido, usando fallback:', posterPath);
            moviePicDiv.innerHTML = `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-size: 20px;
                    text-align: center;
                    padding: 30px;
                    border-radius: 10px;
                ">
                    🎬 ${currentMovie?.title || 'Filme'}
                </div>
            `;
            moviePicDiv.style.backgroundImage = 'none';
        }
        
        moviePicDiv.style.opacity = '0';
        setTimeout(() => {
            moviePicDiv.style.transition = 'opacity 0.5s ease';
            moviePicDiv.style.opacity = '1';
        }, 100);
        
    } catch (error) {
        console.error('❌ Erro em updatePosterImage:', error);
    }
}

async function fetchMovieDetails(movieId) {
    try {
        const response = await fetch(`/api/movies/movie_details/${movieId}`);
        const data = await response.json();
        
        if (data.success && data.details) {
            if (data.details.trailer_url) {
                currentMovie.trailer_url = data.details.trailer_url;
                updateTrailerButtonState(true);
            }
        }
    } catch (error) {
        console.log('⚠️ Detalhes extras não carregados:', error);
    }
}

function updateGenresDisplay(genres) {
    const genreElement = document.getElementById('genre');
    if (genres && genres.length > 0) {
        const limitedGenres = genres.slice(0, 3);
        genreElement.innerHTML = limitedGenres.map(genre => 
            `<span class="genre-tag">${genre}</span>`
        ).join('');
    }
}

function updateTrailerButtonState(hasTrailer) {
    const trailerBtn = document.querySelector('.trailer button');
    
    if (!hasTrailer) {
        trailerBtn.disabled = true;
        trailerBtn.style.opacity = '0.5';
        trailerBtn.style.cursor = 'not-allowed';
        trailerBtn.title = 'Trailer não disponível';
    } else {
        trailerBtn.disabled = false;
        trailerBtn.style.opacity = '1';
        trailerBtn.style.cursor = 'pointer';
        trailerBtn.title = 'Assistir trailer';
    }
}

function updateRatingInfo(voteAverage, releaseYear) {
    const infoCardDiv = document.querySelector('.infoCard');
    const rating = voteAverage > 0 ? `${voteAverage}/10` : 'N/A';
    
    infoCardDiv.innerHTML = `
        <div class="rating">⭐ ${rating}</div>
        ${releaseYear ? `<div class="release-date">${releaseYear}</div>` : ''}
    `;
}

function updateMovieDetails(movieData) {
    document.getElementById('titleName').textContent = movieData.title;
    document.getElementById('description').textContent = movieData.overview;
    
    const genreElement = document.getElementById('genre');
    
    if (movieData.genres && movieData.genres.length > 0) {
        const limitedGenres = movieData.genres.slice(0, 3);
        genreElement.innerHTML = limitedGenres.map(genre => 
            `<span class="genre-tag">${genre}</span>`
        ).join('');
    } else if (movieData.genre_ids && movieData.genre_ids.length > 0) {
        const genreMap = {
            28: 'Ação', 12: 'Aventura', 16: 'Animação', 35: 'Comédia',
            80: 'Crime', 99: 'Documentário', 18: 'Drama', 10751: 'Família',
            14: 'Fantasia', 36: 'História', 27: 'Terror', 10402: 'Música',
            9648: 'Mistério', 10749: 'Romance', 878: 'Ficção científica',
            10770: 'Cinema TV', 53: 'Thriller', 10752: 'Guerra', 37: 'Faroeste'
        };
        
        const limitedGenres = movieData.genre_ids
            .slice(0, 3)
            .map(id => genreMap[id] || `Gênero ${id}`)
            .filter(Boolean);
        
        if (limitedGenres.length > 0) {
            genreElement.innerHTML = limitedGenres.map(genre => 
                `<span class="genre-tag">${genre}</span>`
            ).join('');
        } else {
            genreElement.innerHTML = '<span class="genre-tag">Gênero desconhecido</span>';
        }
    } else {
        genreElement.innerHTML = '<span class="genre-tag">Gênero desconhecido</span>';
    }
}

// ============================================
// REGISTRAR AÇÃO
// ============================================

// ============================================
// REGISTRAR AÇÃO (CORRIGIDA)
// ============================================

function registerAction(action) {
    if (!currentMovie || !buttonsEnabled) return;
    
    console.log('📝 Registrando ação:', action, 'para filme:', currentMovie.id);
    
    disableButtons();
    
    // Chama TODAS as animações
    showCardColorFeedback(action);      // Feedback de cor no card
    addCardTiltEffect(action);          // Animação de tilt
    showButtonAnimation(action);        // Animação do botão
    resetCardPosition();
    
    setTimeout(() => {
        sendActionToServer(action);
    }, 300);
}
function sendActionToServer(action) {
    fetch('/api/movies/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            movie_id: currentMovie.id,
            action: action
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('✅ Ação registrada');
        
        setTimeout(() => {
            loadRandomMovie();
            
            if (shouldPreload && !isPreloading && movieQueue.length < 2) {
                setTimeout(preloadSingleMovie, 200);
            }
        }, 400);
    })
    .catch(error => {
        console.error('❌ Erro ao registrar ação:', error);
        setTimeout(() => loadRandomMovie(), 500);
    });
}

// ============================================
// ERRO HANDLING
// ============================================

function handleLoadError(error) {
    console.error('❌ Erro ao carregar filme:', error);
    
    const moviePicDiv = document.querySelector('.moviePic');
    if (moviePicDiv) {
        moviePicDiv.innerHTML = `
            <div style="text-align: center; padding: 20px; color: white;">
                <p style="font-size: 18px; margin-bottom: 10px;">🎬 Nenhum filme encontrado</p>
                <p style="margin-bottom: 20px; opacity: 0.8;">Tente novamente</p>
                <button onclick="loadRandomMovie()" style="
                    background: #01b4e4; 
                    color: white; 
                    border: none; 
                    padding: 10px 20px; 
                    border-radius: 5px; 
                    cursor: pointer;
                ">Tentar Novamente</button>
            </div>
        `;
    }
    
    enableButtons();
}

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

function handleApiResponse(response) {
    if (!response.ok) throw new Error('Erro: ' + response.status);
    return response.json();
}

function resetCardPosition() {
    if (cardInner && cardInner.classList.contains('flipped')) {
        cardInner.classList.remove('flipped');
    }
}

function resetCardFlip() {
    if (cardInner) cardInner.classList.remove("flipped");
}

// ============================================
// EVENT LISTENERS
// ============================================

function setupReactionButtons() {
    document.querySelectorAll('.reaction a').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            if (!buttonsEnabled) return;
            
            const id = button.id;
            if (id === 'like') registerAction('like');
            else if (id === 'indicate') registerAction('indicate');
            else if (id === 'dislike') registerAction('dislike');
        });
    });
}

function setupCardFlip() {
    if (cardInner) {
        cardInner.addEventListener("click", (e) => {
            if (!e.target.closest('.reaction')) {
                cardInner.classList.toggle("flipped");
            }
        });
    }
}

function setupTrailerButton() {
    const trailerBtn = document.querySelector('.trailer button');
    if (trailerBtn) {
        trailerBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            
            if (currentMovie && currentMovie.trailer_url) {
                openTrailerInModal(currentMovie.trailer_url, currentMovie.title);
            } else {
                alert('Trailer não disponível');
            }
        });
    }
}

function setupEventListeners() {
    setupCardFlip();
    setupReactionButtons();
    setupTrailerButton();
}

// ============================================
// TRAILER MODAL
// ============================================

function extractYouTubeId(url) {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

function openTrailerInModal(trailerUrl, movieTitle) {
    if (!trailerUrl) {
        alert(`Trailer não disponível para ${movieTitle}`);
        return;
    }

    const videoId = extractYouTubeId(trailerUrl);
    if (!videoId) {
        alert('URL do trailer inválida');
        return;
    }

    const iframe = document.querySelector('.trailer-iframe');
    if (!iframe) {
        alert('Erro ao carregar trailer');
        return;
    }

    iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
    showTrailerModal();
}

function showTrailerModal() {
    const modal = document.querySelector('.trailer-modal');
    if (modal) modal.style.display = 'flex';
}

function closeTrailerModal() {
    const modal = document.querySelector('.trailer-modal');
    const iframe = document.querySelector('.trailer-iframe');
    
    if (modal) modal.style.display = 'none';
    if (iframe) iframe.src = iframe.src.replace('?autoplay=1', '');
}

// ============================================
// CONTROLE DO STREAMING
// ============================================

function startMovieStreaming() {
    shouldPreload = true;
    console.log('🚀 Iniciando streaming de filmes...');
    
    if (movieQueue.length < 2 && !isPreloading) {
        setTimeout(preloadSingleMovie, 1000);
    }
}

function stopMovieStreaming() {
    shouldPreload = false;
    console.log('⏸️ Pausando streaming de filmes...');
}

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando aplicação com streaming...');
    setupEventListeners();
    
    startMovieStreaming();
    loadRandomMovie();
    
    fetch('/api/movies/health')
        .then(response => response.json())
        .then(data => console.log('✅ Status do backend:', data))
        .catch(error => console.error('❌ Erro ao verificar backend:', error));

});


