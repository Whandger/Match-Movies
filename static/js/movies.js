// ============================================
// VARIÁVEIS GLOBAIS E CONFIGURAÇÕES
// ============================================

let currentMovie = null;
let cardInner = document.querySelector(".cardInner");
let buttonsEnabled = true;

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
// FUNÇÕES PARA OVERLAY DE AÇÕES
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
    }
    
    cardInner.style.transform = `translateX(${x}px) rotate(${rotation}deg)`;
    cardInner.style.transition = 'transform 0.3s ease-out';
    
    setTimeout(() => {
        cardInner.style.transform = '';
    }, 500);
}

// ============================================
// FUNÇÕES DE API (COMUNICAÇÃO COM SERVIDOR)
// ============================================

function loadRandomMovie(retryCount = 0) {
    const maxRetries = 10;
    
    fetch('/api/movies/random')
        .then(handleApiResponse)
        .then(data => processMovieData(data, retryCount))
        .catch(error => handleLoadError(error, retryCount, maxRetries));
}

function processMovieData(data, retryCount) {
    if (data.error) {
        throw new Error('RETRY');
    }
    
    if (!data.poster_path) {
        throw new Error('RETRY');
    }
    
    currentMovie = data;
    console.log('✅ Filme carregado:', data.title, `(Tentativa: ${retryCount + 1})`);
    
    updateMovieDisplay(data);
    enableButtons();
}

// ============================================
// FUNÇÕES DE UI (INTERFACE DO USUÁRIO)
// ============================================

function updateMovieDisplay(movieData) {
    updatePosterImage(movieData.poster_path);
    updateRatingInfo(movieData.vote_average, movieData.release_year);
    updateMovieDetails(movieData);
    updateTrailerButtonState(!!movieData.trailer_url);
    resetCardFlip();
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

function showActionFeedback(action) {
    const buttons = document.querySelectorAll('.reaction a');
    
    buttons.forEach(button => {
        if (button.id === action) {
            button.style.transform = 'scale(0.8)';
            button.style.opacity = '0.7';
            
            setTimeout(() => {
                button.style.transform = '';
                button.style.opacity = '';
            }, 300);
        }
    });
    
    showCardColorFeedback(action);
}

// 🔴 FUNÇÃO REMOVIDA/ALTERADA: showActionMessage não faz mais nada
function showActionMessage(action, movieTitle) {
    // Não faz nada - mensagem removida
    // Mantém apenas log no console para debug
    console.log(`Ação: ${action} em "${movieTitle}"`);
}

// ============================================
// REGISTRAR AÇÃO (SEM MENSAGEM NA TELA)
// ============================================

function registerAction(action) {
    if (!currentMovie || !buttonsEnabled) {
        console.log('⛔ Botões bloqueados - ação ignorada');
        return;
    }
    
    console.log('Registrando ação:', action, 'para filme:', currentMovie.id);
    
    disableButtons();
    showActionFeedback(action);
    resetCardPosition();
    
    setTimeout(() => {
        sendActionToServer(action);
    }, 300);
}

function sendActionToServer(action) {
    fetch('/api/movies/action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            movie_id: currentMovie.id,
            action: action
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Ação registrada com sucesso:', data);
        
        // 🔴 NÃO chama showActionMessage() aqui
        // Apenas log no console
        
        setTimeout(() => {
            loadRandomMovie();
        }, 1000);
    })
    .catch(error => {
        console.error('❌ Erro ao registrar ação:', error);
        setTimeout(() => {
            loadRandomMovie();
        }, 1000);
    });
}

// ============================================
// CONFIGURAÇÃO DE EVENTOS
// ============================================

function setupReactionButtons() {
    document.querySelectorAll('.reaction a').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (!buttonsEnabled) {
                console.log('⛔ Clique ignorado - botões desabilitados');
                return;
            }
            
            button.style.transform = 'scale(0.9)';
            setTimeout(() => {
                button.style.transform = '';
            }, 200);
            
            const id = button.id;
            if (id === 'like') {
                registerAction('like');
            } else if (id === 'indicate') {
                registerAction('indicate');
            } else if (id === 'dislike') {
                registerAction('dislike');
            }
        });
    });
}

// ============================================
// ERRO HANDLING
// ============================================

function handleLoadError(error, retryCount, maxRetries) {
    if (error.message === 'RETRY' && retryCount < maxRetries) {
        console.log(`🔄 Tentativa ${retryCount + 1} falhou, tentando novamente em 1 segundo...`);
        setTimeout(() => {
            loadRandomMovie(retryCount + 1);
        }, 1000);
    } else {
        console.error('❌ Erro ao carregar filme:', error);
        showError('Erro de conexão com o servidor. Recarregue a página.');
        enableButtons();
    }
}

// ============================================
// FUNÇÕES AUXILIARES (MANTIDAS)
// ============================================

function extractYouTubeId(url) {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

function handleApiResponse(response) {
    if (!response.ok) {
        throw new Error('Erro na requisição: ' + response.status);
    }
    return response.json();
}

function updatePosterImage(posterPath) {
    const moviePicDiv = document.querySelector('.moviePic');
    moviePicDiv.style.backgroundImage = `url('${posterPath}')`;
    moviePicDiv.style.backgroundSize = 'cover';
    moviePicDiv.style.backgroundPosition = 'center';
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
    } else {
        genreElement.textContent = 'Gêneros não disponíveis';
    }
}

function resetCardPosition() {
    if (cardInner && cardInner.classList.contains('flipped')) {
        cardInner.classList.remove('flipped');
    }
}

function resetCardFlip() {
    if (cardInner) {
        cardInner.classList.remove("flipped");
    }
}

function showError(message) {
    const moviePicDiv = document.querySelector('.moviePic');
    moviePicDiv.innerHTML = createErrorHTML(message);
    moviePicDiv.style.display = 'flex';
    moviePicDiv.style.justifyContent = 'center';
    moviePicDiv.style.alignItems = 'center';
    moviePicDiv.style.background = '#f0f0f0';
    
    enableButtons();
}

function createErrorHTML(message) {
    return `
        <div style="text-align: center; padding: 20px; color: red;">
            <p>❌ ${message}</p>
            <button onclick="loadRandomMovie()" style="
                background: #01b4e4; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer;
                margin-top: 10px;
            ">Tentar Novamente</button>
        </div>
    `;
}

// ============================================
// OUTRAS FUNÇÕES (OPCIONAIS - PODE REMOVER)
// ============================================

// 🔴 Estas funções não são mais usadas, pode remover se quiser:

function createOverlayElements() {
    // Não é mais necessária
}

function getOrCreateMessageElement() {
    // Não é mais necessária
    return null;
}

function getActionMessage(action, movieTitle) {
    // Não é mais necessária
    return { message: '', color: '#000' };
}

// ============================================
// CONFIGURAÇÃO DE EVENTOS RESTANTES
// ============================================

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
    document.querySelector('.trailer button').addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (this.disabled) {
            return;
        }
        
        this.style.transform = 'scale(0.9)';
        setTimeout(() => {
            this.style.transform = '';
        }, 200);
        
        if (currentMovie && currentMovie.trailer_url) {
            openTrailerInModal(currentMovie.trailer_url, currentMovie.title);
        } else {
            alert('Trailer não disponível para este filme');
        }
    });
}

function setupEventListeners() {
    setupCardFlip();
    setupReactionButtons();
    setupTrailerButton();
}

// ============================================
// FUNÇÕES DO MODAL DE TRAILER (MANTIDAS)
// ============================================

function openTrailerInModal(trailerUrl, movieTitle) {
    console.log(`Abrindo trailer de: ${movieTitle} no modal`);
    
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
        console.error('Iframe do trailer não encontrado');
        alert('Erro ao carregar trailer');
        return;
    }

    iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
    showTrailerModal();
}

function showTrailerModal() {
    const modal = document.querySelector('.trailer-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeTrailerModal() {
    const modal = document.querySelector('.trailer-modal');
    const iframe = document.querySelector('.trailer-iframe');
    
    if (modal) {
        modal.style.display = 'none';
    }
    
    if (iframe) {
        iframe.src = iframe.src.replace('?autoplay=1', '');
    }
}

// ============================================
// INICIALIZAÇÃO DA APLICAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadRandomMovie();
});