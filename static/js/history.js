let historyModalIsVisible = false

// abrir modal
function openModalHistory(id) {
    document.getElementById(id).style.display = "flex";
    historyModalIsVisible = true;
    loadMatches();
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

// 🎯 FUNÇÃO PARA CARREGAR MATCHES
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