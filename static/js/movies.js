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
// FUNÇÕES PARA CONTROLE DOS BOTÕES (COM ANIMAÇÕES)
// ============================================

function disableButtons() {
    buttonsEnabled = false;
    const buttons = document.querySelectorAll('.reaction a');
    buttons.forEach(button => {
        button.style.pointerEvents = 'none';
        button.style.opacity = '0.5';
        button.style.cursor = 'not-allowed';
        button.style.filter = 'grayscale(80%)';
        button.style.transition = 'all 0.3s ease';
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
        button.style.transition = 'all 0.3s ease';
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
// FUNÇÕES DE API (DA VERSÃO FINAL)
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
    console.log('🎬 Trailer URL:', movieData.trailer_url);
    
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
// FUNÇÕES DE UI (COMBINANDO AMBAS VERSÕES)
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
        
        // Animação de transição suave
        moviePicDiv.style.opacity = '0';
        moviePicDiv.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
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
            
            // Animação de entrada
            moviePicDiv.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            moviePicDiv.style.opacity = '1';
            moviePicDiv.style.transform = 'scale(1)';
        }, 50);
        
    } catch (error) {
        console.error('❌ Erro em updatePosterImage:', error);
    }
}

async function fetchMovieDetails(movieId) {
    try {
        console.log(`🔍 Buscando detalhes do filme ${movieId}...`);
        const response = await fetch(`/api/movies/movie_details/${movieId}`);
        const data = await response.json();
        
        console.log('📊 Resposta dos detalhes:', data);
        
        if (data.success && data.details) {
            if (data.details.trailer_url) {
                console.log(`✅ Trailer encontrado: ${data.details.trailer_url}`);
                currentMovie.trailer_url = data.details.trailer_url;
                updateTrailerButtonState(true);
            } else {
                console.log(`❌ Nenhum trailer nos detalhes`);
                updateTrailerButtonState(false);
            }
        }
    } catch (error) {
        console.log('⚠️ Detalhes extras não carregados:', error);
        updateTrailerButtonState(false);
    }
}

function updateTrailerButtonState(hasTrailer) {
    const trailerBtn = document.querySelector('.trailer button');
    
    if (!trailerBtn) {
        console.error('❌ Botão de trailer não encontrado');
        return;
    }
    
    console.log('🎬 Atualizando botão de trailer:', hasTrailer ? 'ATIVADO' : 'DESATIVADO');
    
    if (!hasTrailer) {
        trailerBtn.disabled = true;
        trailerBtn.style.opacity = '0.5';
        trailerBtn.style.cursor = 'not-allowed';
        trailerBtn.title = 'Trailer não disponível';
        trailerBtn.style.transform = 'scale(1)';
        trailerBtn.textContent = '🎬 Trailer Indisponível';
    } else {
        trailerBtn.disabled = false;
        trailerBtn.style.opacity = '1';
        trailerBtn.style.cursor = 'pointer';
        trailerBtn.title = 'Assistir trailer';
        trailerBtn.textContent = '🎬 Assistir Trailer';
        // Animação de ativação do botão
        trailerBtn.style.transform = 'scale(1.05)';
        setTimeout(() => {
            trailerBtn.style.transform = 'scale(1)';
        }, 300);
    }
}

function updateRatingInfo(voteAverage, releaseYear) {
    const infoCardDiv = document.querySelector('.infoCard');
    const rating = voteAverage > 0 ? `${voteAverage}/10` : 'N/A';
    
    infoCardDiv.innerHTML = `
        <div class="rating">⭐ ${rating}</div>
        ${releaseYear ? `<div class="release-date">${releaseYear}</div>` : ''}
    `;
    
    // Animação dos dados
    infoCardDiv.style.opacity = '0';
    infoCardDiv.style.transform = 'translateY(10px)';
    setTimeout(() => {
        infoCardDiv.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        infoCardDiv.style.opacity = '1';
        infoCardDiv.style.transform = 'translateY(0)';
    }, 100);
}

function updateMovieDetails(movieData) {
    const titleElement = document.getElementById('titleName');
    const descriptionElement = document.getElementById('description');
    const genreElement = document.getElementById('genre');
    
    // Animação de fade out
    titleElement.style.opacity = '0';
    descriptionElement.style.opacity = '0';
    genreElement.style.opacity = '0';
    
    setTimeout(() => {
        // Atualizar conteúdo
        titleElement.textContent = movieData.title;
        descriptionElement.textContent = movieData.overview;
        
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
        
        // Animação de fade in com atraso escalonado
        titleElement.style.transition = 'opacity 0.4s ease 0.1s';
        titleElement.style.opacity = '1';
        
        descriptionElement.style.transition = 'opacity 0.4s ease 0.2s';
        descriptionElement.style.opacity = '1';
        
        genreElement.style.transition = 'opacity 0.4s ease 0.3s';
        genreElement.style.opacity = '1';
    }, 100);
}

// ============================================
// REGISTRAR AÇÃO (COM ANIMAÇÕES COMPLETAS)
// ============================================

function registerAction(action) {
    if (!currentMovie || !buttonsEnabled) return;
    
    console.log('📝 Registrando ação:', action, 'para filme:', currentMovie.id);
    
    disableButtons();
    showButtonAnimation(action);        // Animação do botão
    showCardColorFeedback(action);      // Animação do card (cores + tilt)
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
// ERRO HANDLING (COM ANIMAÇÃO)
// ============================================

function handleLoadError(error) {
    console.error('❌ Erro ao carregar filme:', error);
    
    const moviePicDiv = document.querySelector('.moviePic');
    if (moviePicDiv) {
        // Animação de shake para erro
        moviePicDiv.style.animation = 'shake 0.5s ease-in-out';
        
        setTimeout(() => {
            moviePicDiv.style.animation = '';
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
                        transition: transform 0.2s ease;
                    " onmouseover="this.style.transform='scale(1.05)'" 
                     onmouseout="this.style.transform='scale(1)'"
                     onclick="loadRandomMovie()">Tentar Novamente</button>
                </div>
            `;
        }, 500);
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
// EVENT LISTENERS (COM ANIMAÇÕES DE HOVER)
// ============================================

function setupReactionButtons() {
    document.querySelectorAll('.reaction a').forEach(button => {
        // Efeito hover
        button.addEventListener('mouseenter', () => {
            if (buttonsEnabled) {
                button.style.transform = 'scale(1.1)';
                button.style.transition = 'transform 0.2s ease';
            }
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'scale(1)';
        });
        
        // Clique
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
                // Animação de flip
                cardInner.style.transition = 'transform 0.6s ease';
            }
        });
    }
}

function setupTrailerButton() {
    const trailerBtn = document.querySelector('.trailer button');
    if (trailerBtn) {
        console.log('🎬 Configurando botão de trailer...');
        
        // Efeito hover
        trailerBtn.addEventListener('mouseenter', function() {
            if (!this.disabled) {
                this.style.transform = 'scale(1.05)';
                this.style.transition = 'transform 0.2s ease';
            }
        });
        
        trailerBtn.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
        
        // Clique
        trailerBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('🎬 Botão de trailer clicado');
            
            if (this.disabled) {
                console.log('❌ Botão desativado - trailer não disponível');
                return;
            }
            
            // Animação de clique
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 200);
            
            if (currentMovie && currentMovie.trailer_url) {
                console.log('🎬 Abrindo trailer:', currentMovie.trailer_url);
                openTrailerInModal(currentMovie.trailer_url, currentMovie.title);
            } else {
                console.log('❌ Nenhum trailer disponível');
                alert('Trailer não disponível para este filme');
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
// TRAILER MODAL (CORREÇÃO COMPLETA)
// ============================================

function extractYouTubeId(url) {
    if (!url) {
        console.log('❌ URL vazia em extractYouTubeId');
        return null;
    }
    
    console.log('🔍 Analisando URL:', url);
    
    // Remove espaços e limpa a URL
    url = url.trim();
    
    // Padrões comuns do YouTube
    const patterns = [
        // youtube.com/watch?v=ID
        /youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/,
        // youtu.be/ID
        /youtu\.be\/([a-zA-Z0-9_-]{11})/,
        // youtube.com/embed/ID
        /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
        // youtube.com/v/ID
        /youtube\.com\/v\/([a-zA-Z0-9_-]{11})/,
        // URL com outros parâmetros: ?v=ID&...
        /[?&]v=([a-zA-Z0-9_-]{11})/
    ];
    
    for (let i = 0; i < patterns.length; i++) {
        const match = url.match(patterns[i]);
        if (match && match[1]) {
            console.log(`✅ ID encontrado com padrão ${i}: ${match[1]}`);
            return match[1];
        }
    }
    
    console.log('❌ Nenhum ID do YouTube encontrado');
    console.log('🔄 Tentando extração manual...');
    
    // Fallback: tenta encontrar qualquer sequência de 11 caracteres alfanuméricos
    const manualMatch = url.match(/([a-zA-Z0-9_-]{11})/);
    if (manualMatch && manualMatch[1]) {
        console.log(`✅ ID extraído manualmente: ${manualMatch[1]}`);
        return manualMatch[1];
    }
    
    console.log('❌ Falha total na extração do ID');
    return null;
}

function openTrailerInModal(trailerUrl, movieTitle) {
    console.log('🎬 ===========================================');
    console.log('🎬 INICIANDO ABERTURA DO TRAILER');
    console.log('🎬 Filme:', movieTitle);
    console.log('🎬 URL recebida:', trailerUrl);
    console.log('🎬 ===========================================');
    
    if (!trailerUrl) {
        console.log('❌ ERRO: trailerUrl é null ou undefined');
        alert(`Trailer não disponível para "${movieTitle}"`);
        return;
    }
    
    if (typeof trailerUrl !== 'string') {
        console.log('❌ ERRO: trailerUrl não é uma string:', typeof trailerUrl);
        alert('Erro: URL do trailer inválida');
        return;
    }
    
    const videoId = extractYouTubeId(trailerUrl);
    console.log('🎬 Video ID extraído:', videoId);
    
    if (!videoId) {
        console.log('❌ Não foi possível extrair o ID do YouTube');
        console.log('🔄 Tentando fallback: abrir em nova aba...');
        
        try {
            window.open(trailerUrl, '_blank', 'noopener,noreferrer');
            console.log('✅ Aberto em nova aba com sucesso');
        } catch (error) {
            console.error('❌ Erro ao abrir em nova aba:', error);
            alert(`Não foi possível abrir o trailer para "${movieTitle}"`);
        }
        return;
    }
    
    const iframe = document.querySelector('.trailer-iframe');
    if (!iframe) {
        console.error('❌ ERRO CRÍTICO: Elemento .trailer-iframe não encontrado!');
        console.error('Verifique se o HTML contém: <iframe class="trailer-iframe"></iframe>');
        alert('Erro interno: Player de trailer não encontrado');
        return;
    }
    
    console.log('🎬 Iframe encontrado, configurando...');
    
    // Limpa o iframe primeiro
    iframe.src = '';
    
    // Cria a URL de embed
    const embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1`;
    console.log('🎬 URL de embed:', embedUrl);
    
    // Pequeno delay para garantir que o DOM está pronto
    setTimeout(() => {
        iframe.src = embedUrl;
        console.log('✅ Iframe configurado com sucesso');
        showTrailerModal();
    }, 100);
}

function showTrailerModal() {
    console.log('🎬 Mostrando modal do trailer');
    const modal = document.querySelector('.trailer-modal');
    
    if (!modal) {
        console.error('❌ ERRO: Elemento .trailer-modal não encontrado!');
        console.error('Verifique se o HTML contém a estrutura do modal');
        return;
    }
    
    modal.style.display = 'flex';
    modal.style.opacity = '0';
    
    // Pequeno delay para garantir transição suave
    setTimeout(() => {
        modal.style.transition = 'opacity 0.3s ease';
        modal.style.opacity = '1';
        console.log('✅ Modal exibido com sucesso');
    }, 50);
}

function closeTrailerModal() {
    console.log('🎬 Fechando modal do trailer');
    const modal = document.querySelector('.trailer-modal');
    const iframe = document.querySelector('.trailer-iframe');
    
    if (modal) {
        modal.style.opacity = '0';
        
        setTimeout(() => {
            modal.style.display = 'none';
            console.log('✅ Modal escondido');
        }, 300);
    }
    
    if (iframe) {
        iframe.src = '';
        console.log('✅ Iframe limpo (vídeo pausado)');
    }
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
    console.log('🚀 Inicializando aplicação com streaming e animações...');
    console.log('🔧 Verificando elementos do DOM...');
    
    // Verifica elementos essenciais
    const essentialElements = [
        '.cardInner',
        '.moviePic',
        '.trailer button',
        '.trailer-iframe',
        '.trailer-modal',
        '#titleName',
        '#description',
        '#genre'
    ];
    
    essentialElements.forEach(selector => {
        const element = document.querySelector(selector);
        console.log(`${element ? '✅' : '❌'} ${selector}: ${element ? 'Encontrado' : 'NÃO ENCONTRADO'}`);
    });
    
    setupEventListeners();
    
    // Adicionar CSS para animações extras
    addAnimationStyles();
    
    startMovieStreaming();
    loadRandomMovie();
    
    fetch('/api/movies/health')
        .then(response => response.json())
        .then(data => console.log('✅ Status do backend:', data))
        .catch(error => console.error('❌ Erro ao verificar backend:', error));
});

// ============================================
// CSS PARA ANIMAÇÕES ADICIONAIS
// ============================================

function addAnimationStyles() {
    if (!document.getElementById('animations-styles')) {
        const style = document.createElement('style');
        style.id = 'animations-styles';
        style.textContent = `
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .genre-tag {
                animation: fadeInUp 0.5s ease forwards;
                opacity: 0;
                transform: translateY(10px);
            }
            
            .genre-tag:nth-child(1) { animation-delay: 0.1s; }
            .genre-tag:nth-child(2) { animation-delay: 0.2s; }
            .genre-tag:nth-child(3) { animation-delay: 0.3s; }
            
            .reaction a {
                transition: all 0.3s ease !important;
            }
            
            .trailer button {
                transition: all 0.3s ease !important;
            }
            
            .moviePic {
                transition: opacity 0.5s ease, transform 0.5s ease !important;
            }
            
            .cardInner {
                transition: transform 0.6s ease !important;
            }
            
            /* Estilos para o modal de trailer */
            .trailer-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.9);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            
            .trailer-modal-content {
                width: 90%;
                max-width: 900px;
                position: relative;
            }
            
            .trailer-iframe {
                width: 100%;
                height: 500px;
                border: none;
                border-radius: 10px;
            }
            
            .close-trailer {
                position: absolute;
                top: -40px;
                right: 0;
                background: #ff4757;
                color: white;
                border: none;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                font-size: 20px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s ease;
            }
            
            .close-trailer:hover {
                transform: scale(1.1);
            }
        `;
        document.head.appendChild(style);
        console.log('✅ Estilos de animação adicionados');
    }
}
