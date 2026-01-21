
  const loginIndex = document.getElementById("loginIndex")
  // Abrir modal

  function openModal(id) {
    loginIndex.style.display = "none";
    document.getElementById(id).style.display = "block";
  }

  // Fechar modal
  function closeModal(id) {
    loginIndex.style.display = "flex";
    document.getElementById(id).style.display = "none";
  }

  // Eventos de abrir modais
  document.getElementById("openRegister").onclick = function (e) {
    e.preventDefault();
    openModal("registerModal");
  };

  document.getElementById("openForgot").onclick = function (e) {
    e.preventDefault();
    openModal("forgotModal");
  };

  // Eventos de voltar pro login
  document.getElementById("backToLoginFromRegister").onclick = function (e) {
    e.preventDefault();
    closeModal("registerModal");
  };

  document.getElementById("backToLoginFromForgot").onclick = function (e) {
    e.preventDefault();
    closeModal("forgotModal");
  };

  // Fechar ao clicar no X
  document.querySelectorAll(".close").forEach(btn => {
    btn.addEventListener("click", function () {
      const modalId = btn.getAttribute("data-close");
      closeModal(modalId);
    });
  });

//Começo login registro e forgot


 // Submissão do formulário de login
document.getElementById("loginForm").onsubmit = function (e) {
  e.preventDefault();  // Evita o envio padrão do formulário

  // Coleta os dados do formulário
  const username = document.querySelector('input[name="username"]').value;
  const password = document.querySelector('input[name="password"]').value;

  // Fazendo a requisição para o servidor Flask
  fetch('/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username: username, password: password }),
  })
  .then(response => response.json())  // Espera resposta JSON
  .then(data => {
    if (data.success) {
      // Redireciona para o index se o login for bem-sucedido
      window.location.href = '/'; // ou a URL do seu dashboard, por exemplo
    } else {
      alert('Login inválido');
    }
  })
  .catch(error => {
    console.error('Erro ao fazer login:', error);
    alert('Ocorreu um erro, tente novamente.');
  });
};

//REGISTRO\/
document.getElementById("registerForm").onsubmit = function (e) {
  e.preventDefault();

  const email = document.querySelector('#registerForm input[name="email"]').value;
  const username = document.querySelector('#registerForm input[name="username"]').value;
  const password = document.querySelector('#registerForm input[name="password"]').value;

  fetch('/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, username, password }),
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert('Usuário registrado com sucesso!');
        closeModal("registerModal");
      } else {
        alert(data.message || 'Erro ao registrar usuário');
      }
    })
    .catch(error => {
      console.error('Erro:', error);
      alert('Erro inesperado');
    });
};

//FORGOT
  document.getElementById("forgotForm").onsubmit = function (e) {
    e.preventDefault();
    alert("Email de recuperação enviado");
  };
