Sistema Financeiro Pessoal / Personal Finance System
Sistema Financeiro Pessoal
Aplicação web full stack desenvolvida para controle financeiro pessoal, com foco em segurança, experiência do usuário e visualização de dados.

🛠️ Tecnologias Utilizadas
Front-end: HTML, CSS, JavaScript (puro)

Back-end: Python (Flask)

Banco de Dados: MySQL

🚀 Funcionalidades Principais
Autenticação de Usuário

Telas de login, registro e modal para recuperação de senha (esqueci minha senha em desenvolvimento)

Senhas protegidas com hash seguro

Acesso restrito a usuários autenticados em todas as páginas

Redirecionamento automático para o login caso o usuário não esteja autenticado

Dashboard e Navegação

Após login, o usuário é direcionado à dashboard (index.html), com nome exibido no canto superior direito em um dropdown

Dropdown com opções de Alterar Senha e Logout

Navbar com navegação para Home, Data e menu suspenso com Adicionar Despesa, Adicionar Receita e Gráfico de Dados

Gestão de Receitas e Despesas

Telas específicas para adicionar despesas (categorias como gasto, presente, etc) e receitas (categorias como salário, pix, renda passiva, etc)

Cada lançamento inclui categoria, valor, data e observação

Botão de envio desabilitado durante o processamento, com mensagem de sucesso exibida por 1,5s

Consulta e Edição de Dados

Página data.html exibe registros paginados (10 por página), ordenados por data

UI aprimorada: hover escurece linha, botão X para deletar registro, engrenagem para editar e atualizar informações sem perder o layout

Visualização Gráfica

Página datachart.html exibe gráfico mensal de receitas x despesas, mostrando lucro líquido por mês

Permite seleção de período para análise personalizada

💡 Diferenciais do Projeto
Interface moderna, responsiva e amigável

Feedback visual em todas as ações do usuário

Segurança reforçada com hash de senhas

Estrutura modular e escalável

📦 Como Executar
Clone o repositório

Instale as dependências Python:

bash
Copiar
Editar
pip install -r requirements.txt
Configure as variáveis de ambiente para acesso ao MySQL

Execute o servidor Flask:cd (raiz do projeto) depois run.py
Ou execute o arquivo .bat
Acesse http://localhost:5000 no navegador


English version:

Personal Finance System
A full-stack web application developed for personal financial control, focusing on security, user experience, and data visualization.

🛠️ Technologies Used
Front-end: HTML, CSS, JavaScript (vanilla)

Back-end: Python (Flask)

Database: MySQL

🚀 Main Features
User Authentication

Login, registration, and password recovery modal (forgot password in development)

Passwords protected with secure hashing

Restricted access to authenticated users across all pages

Automatic redirect to login if the user is not authenticated

Dashboard and Navigation

After login, the user is directed to the dashboard (index.html), with the name displayed at the top right in a dropdown

Dropdown with options to Change Password and Logout

Navbar with navigation to Home, Data, and a dropdown menu with Add Expense, Add Income, and Data Graph

Income and Expense Management

Specific screens to add expenses (categories like spending, gift, etc.) and income (categories like salary, pix, passive income, etc.)

Each entry includes category, value, date, and note

Submit button is disabled during processing, with a success message shown for 1.5 seconds

Data Query and Edit

The data.html page displays paginated records (10 per page), sorted by date

Enhanced UI: hover darkens the row, X button to delete record, gear icon to edit and update info without losing layout

Graphical Visualization

The datachart.html page displays a monthly chart of income vs. expenses, showing net profit per month

Allows period selection for customized analysis

💡 Project Highlights
Modern, responsive, and user-friendly interface

Visual feedback for every user action

Strong security with password hashing

Modular and scalable structure

📦 How to Run
Clone the repository

Install the Python dependencies:

bash
Copiar
Editar
pip install -r requirements.txt
Set up environment variables for MySQL access

Run the Flask server:

CD (Your project path)
python run.py

Or execute the .bat archive

Access http://localhost:5000 in your browser