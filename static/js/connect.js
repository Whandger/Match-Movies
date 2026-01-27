let modalIsVisible = false;
let currentConnection = null;

// Modal functions
function openModal(id) {
    document.getElementById(id).style.display = "block";
    modalIsVisible = true;
}

function closeModal(id) {
    document.getElementById(id).style.display = "none";
    modalIsVisible = false;
    document.getElementById("connectInput").value = "";
}

// Event Listeners
document.getElementById("connect").onclick = function (e) {
    e.preventDefault();
    if (modalIsVisible === false) {
        openModal("connectModal");
    } else {
        closeModal("connectModal");
    }
};

document.getElementById("connectButton").onclick = function (e) {
    e.preventDefault();
    connectUsers();
};

// Enter key support
document.getElementById("connectInput").addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        connectUsers();
    }
});

// Connect users function - CORRIGIDA COM PREFIXO /api/movies
async function connectUsers() {
    const targetUserId = document.getElementById("connectInput").value.trim();
    
    if (!targetUserId) {
        alert("Por favor, insira um ID de usuário");
        return;
    }
    
    const connectButton = document.getElementById("connectButton");
    connectButton.textContent = "Conectando...";
    connectButton.disabled = true;
    
    try {
        const response = await fetch('/api/movies/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                target_user_id: targetUserId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert("✅ Conectado com sucesso!");
            closeModal("connectModal");
            // Passa partner_id e partner_username para atualizar a UI
            updateConnectionUI(true, data.partner_id, data.partner_username);
        } else {
            alert("❌ " + data.message);
        }
        
    } catch (error) {
        console.error('Erro:', error);
        alert("❌ Erro de conexão");
    } finally {
        connectButton.textContent = "Connect";
        connectButton.disabled = false;
    }
}

// Update UI when connected
function updateConnectionUI(isConnected, partnerId = null, partnerUsername = null) {
    const connectElement = document.getElementById("connect");
    
    if (isConnected && partnerUsername) {
        connectElement.innerHTML = '<i class="fa-solid fa-link"></i>';
        connectElement.style.color = "rgb(0 0 0)";
        connectElement.style.pointerEvents = "none";
        currentConnection = partnerId;
    }
}

// Check existing connection on page load - CORRIGIDA COM PREFIXO /api/movies
document.addEventListener('DOMContentLoaded', function() {
    checkExistingConnection();
});

async function checkExistingConnection() {
    try {
        const response = await fetch('/api/movies/connections');
        const data = await response.json();
        
        if (data.connections && data.connections.length > 0) {
            const connection = data.connections[0];
            // Agora também passa partner_username se disponível
            updateConnectionUI(true, connection.partner_id, connection.partner_username);
        }
    } catch (error) {
        console.error('Erro ao verificar conexões:', error);
    }
}
