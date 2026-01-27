let historyModalIsVisible = false

// abrir modal
async function openModalHistory(id) {
    try {
        const modal = document.getElementById(id);
        if (!modal) {
            console.error(`❌ Modal com ID "${id}" não encontrado`);
            return;
        }
        
        modal.style.display = "flex";
        historyModalIsVisible = true;
        
        console.log("🎬 Modal de histórico aberto - Criando matches...");
        
        // 🎯 PRIMEIRO: Chamar API para criar/verificar matches
        const createResponse = await fetch('/api/movies/check_and_create_matches', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        if (!createResponse.ok) {
            throw new Error(`HTTP ${createResponse.status}`);
        }
        
        const createData = await createResponse.json();
        console.log('📊 Resposta da criação de matches:', createData);
        
        // 🎯 DEPOIS: Carregar os matches para mostrar
        await loadMatches();
        
    } catch (error) {
        console.error('❌ Erro ao abrir modal:', error);
        // Mesmo assim tenta carregar os matches
        await loadMatches();
    }
}

// Fechar modal
function closeModalHistory(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.style.display = "none";
        historyModalIsVisible = false;
    }
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
        console.log("🔍 Carregando matches do banco...");
        const response = await fetch('/api/movies/matches');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📊 Dados recebidos:', data);
        
        const matchesContainer = document.getElementById('matchesContainer');
        if (!matchesContainer) {
            console.error('❌ Elemento matchesContainer não encontrado');
            return;
        }
        
        // Limpar container antes de adicionar novos matches
        matchesContainer.innerHTML = '';
        
        if (data.success && data.matches && data.matches.length > 0) {
            console.log(`✅ Encontrados ${data.matches.length} matches`);
            
            // Para cada match, criar um novo elemento
            data.matches.forEach((match, index) => {
                createMatchElement(match, matchesContainer, index);
            });
        } else {
            console.log('📭 Nenhum match encontrado');
            
            // Mensagem quando não há matches
            matchesContainer.innerHTML = `
                <div style="text-align: center; color: white; padding: 40px;">
                    <p style="font-size: 18px; margin-bottom: 10px;">📭 Ainda não há matches</p>
                    <small>Continue curtindo filmes para encontrar matches com seu parceiro!</small>
                </div>
            `;
        }
    } catch (error) {
        console.error('❌ Erro ao carregar matches:', error);
    }
}

// 🎯 FUNÇÃO PARA CRIAR UM NOVO ELEMENTO DE MATCH
function createMatchElement(match, container, index) {
    console.log(`🎬 Criando elemento para match ${index + 1}:`, match);
    
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

    // Criar informação do parceiro
    const partnerElement = document.createElement('p');
    partnerElement.className = 'match-partner';
    partnerElement.textContent = `Com: ${match.partner_username}`;
    
    // Adicionar elementos ao match
    matchElement.appendChild(imgElement);
    matchElement.appendChild(titleElement);
    matchElement.appendChild(partnerElement);
    
    // Adicionar match ao container
    container.appendChild(matchElement);
    
    // Buscar detalhes do filme (com verificação de elementos)
    fetchMovieDetails(match.movie_id, imgElement, titleElement, matchElement);
}

// 🎯 BUSCAR DETALHES DO FILME (CORRIGIDA)
async function fetchMovieDetails(movieId, imgElement, titleElement, matchElement) {
    try {
        console.log(`🔍 Buscando detalhes do filme ${movieId}...`);
        
        // Verificar se os elementos ainda existem no DOM antes de fazer a requisição
        if (!matchElement || !document.body.contains(matchElement)) {
            console.warn(`⚠️ Elemento do match ${movieId} removido do DOM`);
            return;
        }
        
        const response = await fetch(`https://api.themoviedb.org/3/movie/${movieId}?api_key=941fae9e612c2f209e18d77a5a760269&language=pt-BR`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const movieData = await response.json();
        
        // Verificar novamente se os elementos ainda existem
        if (!document.body.contains(imgElement) || !document.body.contains(titleElement)) {
            console.warn(`⚠️ Elementos do filme ${movieId} removidos durante carregamento`);
            return;
        }
        
        // Atualizar imagem
        if (movieData.poster_path) {
            imgElement.src = `https://image.tmdb.org/t/p/w200${movieData.poster_path}`;
            imgElement.alt = movieData.title;
            console.log(`🖼️ Imagem carregada: ${movieData.title}`);
            
            // Remover estilos de fallback se a imagem carregar
            imgElement.style.backgroundColor = '';
            imgElement.style.display = '';
            imgElement.style.alignItems = '';
            imgElement.style.justifyContent = '';
            imgElement.innerHTML = '';
        } else {
            // Manter fallback se não tiver imagem
            imgElement.style.backgroundColor = '#333';
            imgElement.style.width = '100px';
            imgElement.style.height = '150px';
            imgElement.style.display = 'flex';
            imgElement.style.alignItems = 'center';
            imgElement.style.justifyContent = 'center';
            imgElement.innerHTML = '🎬';
        }
        
        // Atualizar título
        titleElement.textContent = movieData.title;
        
        // Adicionar ano se disponível
        if (movieData.release_date) {
            const year = movieData.release_date.split('-')[0];
            titleElement.textContent = `${movieData.title} (${year})`;
        }
        
    } catch (error) {
        console.error(`❌ Erro ao buscar detalhes do filme ${movieId}:`, error);
        
        // Verificar se os elementos ainda existem antes de modificar
        if (titleElement && document.body.contains(titleElement)) {
            titleElement.textContent = `Filme ID: ${movieId}`;
        }
        
        if (imgElement && document.body.contains(imgElement)) {
            // Manter fallback em caso de erro
            imgElement.style.backgroundColor = '#333';
            imgElement.style.width = '100px';
            imgElement.style.height = '150px';
            imgElement.style.display = 'flex';
            imgElement.style.alignItems = 'center';
            imgElement.style.justifyContent = 'center';
            imgElement.innerHTML = '🎬';
        }
    }
}

// 🎯 FUNÇÃO PARA TESTAR MANUALMENTE (opcional - para debugging)
async function testCreateMatches() {
    try {
        console.log("🧪 Testando criação de matches...");
        const response = await fetch('/api/movies/check_and_create_matches', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ Resultado do teste:', data);
        alert(`Resultado: ${data.message}`);
        
        // Recarregar matches após teste
        await loadMatches();
        
    } catch (error) {
        console.error('❌ Erro no teste:', error);
        alert('Erro ao testar criação de matches');
    }
}

// 🎯 Adicionar CSS básico se não existir
function addBasicStyles() {
    if (!document.getElementById('matches-styles')) {
        const style = document.createElement('style');
        style.id = 'matches-styles';
        style.textContent = `
            .match-item {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 15px;
                margin: 10px 0;
                display: flex;
                align-items: center;
                gap: 15px;
                color: white;
                width: 100%;
                max-width: 500px;
                border-left: 5px solid #00adb5;
            }
            
            .match-cover {
                width: 100px;
                height: 150px;
                border-radius: 10px;
                object-fit: cover;
            }
            
            .match-title {
                font-size: 18px;
                font-weight: bold;
                margin: 0 0 5px 0;
                color: white;
            }
            .match-partner {
                display: none;
                font-size: 14px;
                margin: 0;
                color: #00adb5;
            }
        `;
        document.head.appendChild(style);
    }
}

// 🎯 Inicializar estilos quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    addBasicStyles();
    console.log("✅ JavaScript de matches carregado e pronto!");
});