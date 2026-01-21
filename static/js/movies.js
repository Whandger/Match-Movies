// ============================================
// VARIÁVEIS GLOBAIS E CONFIGURAÇÕES
// ============================================

let currentMovie = null;
let cardInner = document.querySelector(".cardInner");

// ============================================
// FUNÇÕES DO MODAL DE TRAILER
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
// FUNÇÕES DE API (COMUNICAÇÃO COM SERVIDOR)
// ============================================

function loadRandomMovie(retryCount = 0) {
    const maxRetries = 10;
    
    fetch('/api/movies/random')
        .then(handleApiResponse)
        .then(data => processMovieData(data, retryCount))
        .catch(error => handleLoadError(error, retryCount, maxRetries));
}

function registerAction(action) {
    if (!currentMovie) return;
    
    console.log('Registrando ação:', action, 'para filme:', currentMovie.id);
    
    showActionFeedback(action);
    resetCardPosition();
    
    setTimeout(() => {
        sendActionToServer(action);
    }, 300);
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
}

function showActionMessage(action, movieTitle) {
    const messageElement = getOrCreateMessageElement();
    const { message, emoji } = getActionMessage(action, movieTitle);
    
    messageElement.innerHTML = `${emoji}<br>${message}`;
    messageElement.style.display = 'block';
    
    setTimeout(() => {
        messageElement.style.display = 'none';
    }, 2000);
}

function showError(message) {
    const moviePicDiv = document.querySelector('.moviePic');
    moviePicDiv.innerHTML = createErrorHTML(message);
    moviePicDiv.style.display = 'flex';
    moviePicDiv.style.justifyContent = 'center';
    moviePicDiv.style.alignItems = 'center';
    moviePicDiv.style.background = '#f0f0f0';
}

// ============================================
// FUNÇÕES AUXILIARES (UTILITIES)
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
}

function handleLoadError(error, retryCount, maxRetries) {
    if (error.message === 'RETRY' && retryCount < maxRetries) {
        console.log(`🔄 Tentativa ${retryCount + 1} falhou, tentando novamente em 1 segundo...`);
        setTimeout(() => {
            loadRandomMovie(retryCount + 1);
        }, 1000);
    } else {
        console.error('❌ Erro ao carregar filme:', error);
        showError('Erro de conexão com o servidor. Recarregue a página.');
    }
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
        showActionMessage(action, currentMovie.title);
        
        setTimeout(() => {
            loadRandomMovie();
        }, 1000);
    })
    .catch(error => {
        console.error('❌ Erro ao registrar ação:', error);
        loadRandomMovie();
    });
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

function getOrCreateMessageElement() {
    let messageElement = document.getElementById('actionMessage');
    if (!messageElement) {
        messageElement = document.createElement('div');
        messageElement.id = 'actionMessage';
        messageElement.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9);
            color: white;
            padding: 20px 30px;
            border-radius: 10px;
            font-size: 1.2rem;
            font-weight: bold;
            z-index: 1000;
            text-align: center;
        `;
        document.body.appendChild(messageElement);
    }
    return messageElement;
}

function getActionMessage(action, movieTitle) {
    const messages = {
        'like': { message: `Você curtiu "${movieTitle}"! 🎬`, emoji: '❤️' },
        'dislike': { message: `Você não curtiu "${movieTitle}"! 👎`, emoji: '😞' },
        'indicate': { message: `Você indicou "${movieTitle}"! 📤`, emoji: '👉' }
    };
    
    return messages[action] || { message: '', emoji: '' };
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
// CONFIGURAÇÃO DE EVENTOS
// ============================================

function setupEventListeners() {
    setupCardFlip();
    setupReactionButtons();
    setupTrailerButton();
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

function setupReactionButtons() {
    document.querySelectorAll('.reaction a').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            
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


// ============================================
// INICIALIZAÇÃO DA APLICAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadRandomMovie();
});