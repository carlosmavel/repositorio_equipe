# Orquetask - Sistema Integrado de Gestão e Conhecimento

**Status do Projeto:** Em Desenvolvimento Ativo 🚧

## Sobre o Projeto

Orquetask é um sistema web integrado construído com Flask e Python, projetado para centralizar e otimizar a gestão de conhecimento técnico (através de um repositório de artigos com fluxo de aprovação), ordens de serviço (planejado) e comunicação interna em organizações. O objetivo é fornecer uma plataforma robusta, intuitiva e eficiente para diversas operações do dia a dia.

## Funcionalidades Principais (Atuais e Planejadas)

* **Biblioteca de Artigos:**
    * Criação, revisão, aprovação e publicação de artigos.
    * Busca Full-Text em conteúdo e anexos.
* **Módulo de Administração Global:**
    * Gerenciamento de Usuários (com campos detalhados e status ativo/inativo).
    * Gerenciamento de Estrutura Organizacional: Estabelecimentos, Centros de Custo, Setores e Cargos.
    * (Planejado) Gestão de Perfis de Acesso e Permissões (Funções).
* **Página Inicial Personalizada:** Dashboard do usuário pós-login.
* **Perfil de Usuário Detalhado:** Visualização e edição de dados, foto e senha.
* **Sistema de Notificações Contextuais.**
* **Layout Responsivo com Sidebar Global.**
* **(Planejado - Fase 3) Módulo de Ordens de Serviço (OS).**
* **(Planejado - Fase 3) Kanban de OS.**
* **(Planejado - Fase 4) Central de Comunicação Interna.**

## Tecnologias Utilizadas

* **Backend:** Python 3, Flask
* **Frontend:** HTML5, CSS3 (Bootstrap 5), JavaScript (Vanilla JS), Quill.js
* **Banco de Dados:** PostgreSQL
* **ORM / Migrations:** SQLAlchemy, Alembic (via Flask-SQLAlchemy, Flask-Migrate)
* **Principais Bibliotecas:** Werkzeug, Jinja2, psycopg2-binary, python-docx, openpyxl, xlrd, odfpy, PyPDF2, Bleach, python-dotenv.

## Pré-requisitos

Para rodar este projeto em um ambiente de desenvolvimento, você precisará ter instalado:
* Python (versão 3.9 ou superior recomendado)
* Git
* PostgreSQL (versão 12 ou superior)
* (Opcional, mas recomendado para gerenciamento do DB) pgAdmin 4

## Como Rodar o Projeto (Desenvolvimento)

1.  **Clone o repositório:**
    ```bash
    git clone SEU_LINK_PARA_O_REPOSITORIO_GIT_AQUI
    cd NOME_DA_PASTA_DO_PROJETO
    ```

2.  **Crie e ative um ambiente virtual Python:**
    ```bash
    python -m venv venv
    # No Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    # No Linux/macOS (ou Git Bash no Windows):
    # source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure o Banco de Dados PostgreSQL e Variáveis de Ambiente:**
    * Siga as instruções detalhadas no nosso **[Guia de Instalação e Configuração](./docs/GUIA_DE_INSTALACAO.md)** para criar o banco de dados, o usuário do banco com as permissões corretas, e para configurar as variáveis de ambiente essenciais (`FLASK_APP`, `FLASK_DEBUG`, `SECRET_KEY`, `DATABASE_URI`).

5.  **Aplique as migrações do banco de dados:**
    ```bash
    flask db upgrade
    ```

6.  **(Opcional) Popule dados iniciais (usuários de exemplo):**
    ```bash
    python seed_users.py
    ```

7.  **Rode a aplicação Flask:**
    ```bash
    flask run
    ```
    Acesse em seu navegador: `http://127.0.0.1:5000`

Para instruções de instalação e configuração **completas e detalhadas**, por favor, consulte nosso:
* **[Guia de Instalação Completo](./docs/GUIA_DE_INSTALACAO.md)**
* **[Documentação Geral do Sistema](./docs/DOCUMENTACAO_DO_SISTEMA.md)**

## Estrutura do Projeto (Simplificada)

/ORQUETASK_PROJECT_ROOT/
├── app.py
├── models.py
├── requirements.txt
├── migrations/
├── static/
└── templates/
├── admin/
└── base.html

## Licença

Este projeto está licenciado sob a Licença GNU GPLv3 - veja o arquivo [LICENSE](LICENSE) para detalhes.

---