# Documentação do Sistema Orquetask

## 1. Visão Geral do Orquetask

O **Orquetask** é um sistema web integrado, desenvolvido em Python com o framework Flask. Seu principal objetivo é centralizar e otimizar processos cruciais para uma organização, incluindo a gestão de conhecimento técnico, o futuro gerenciamento de ordens de serviço (OS) e a facilitação da comunicação interna. A plataforma foi projetada com foco na usabilidade, apresentando uma interface moderna e responsiva, com navegação principal através de uma barra lateral global para usuários autenticados.

**Principais Módulos e Objetivos Estratégicos:**
* **Biblioteca de Artigos:** Servir como um repositório centralizado e confiável para toda a documentação técnica, manuais de procedimento, guias e artigos informativos, com um fluxo robusto de criação, revisão colaborativa e aprovação.
* **Gestão de Ordens de Serviço (OS):** Implementar um sistema completo para o ciclo de vida das ordens de serviço, desde a abertura e categorização, passando pela atribuição e acompanhamento de status, até sua resolução e finalização. (Planejado para Fase 3)
* **Kanban de OS:** Oferecer uma interface visual estilo Kanban para o gerenciamento ágil e intuitivo do fluxo de Ordens de Serviço. (Planejado para Fase 3)
* **Administração Global:** Disponibilizar um painel de controle abrangente para administradores do sistema, permitindo o gerenciamento detalhado de usuários, suas permissões e papéis, bem como a configuração da estrutura organizacional base (estabelecimentos, setores, cargos).
* **Página Inicial Personalizada:** Apresentar um dashboard individualizado para cada usuário após o login, com informações relevantes, atalhos para funcionalidades frequentemente utilizadas e um resumo de pendências.
* **Perfil de Usuário Detalhado:** Permitir que os usuários visualizem seus dados cadastrais completos e editem informações pertinentes, incluindo foto de perfil e senha, com mecanismos de segurança e validação.
* **Central de Comunicação (Futuro):** Estabelecer um canal oficial para a divulgação de comunicados da empresa, notícias de setores específicos e uma área de classificados internos para interação entre colaboradores. (Planejado para Fase 4)
* **Sistema de Notificações:** Manter os usuários informados sobre eventos importantes e ações necessárias dentro do sistema através de alertas contextuais.

## 2. Funcionalidades Principais Detalhadas

### 2.1. Módulo de Artigos (Biblioteca)
* **Colaboradores:**
    * Criação e edição de rascunhos de artigos utilizando um editor de texto rico (Quill.js).
    * Submissão de artigos finalizados para um fluxo de revisão e aprovação.
    * Capacidade de anexar múltiplos arquivos relevantes (documentos, planilhas, PDFs, imagens) aos artigos.
* **Administradores de Artigos:**
    * Acesso a uma fila de artigos pendentes de aprovação.
    * Ferramentas para revisar o conteúdo e os anexos dos artigos submetidos.
    * Opções para aprovar artigos para publicação, solicitar ajustes específicos ao autor, ou rejeitar artigos com feedback.
* **Todos os Usuários (Logados):**
    * Busca Full-Text avançada que pesquisa em títulos, conteúdo textual e no texto extraído de arquivos anexados (TXT, DOCX, PDF, XLSX, etc.) dos artigos aprovados.
    * Visualização clara e organizada dos artigos aprovados.
    * Acesso à página "Meus Artigos" para autores gerenciarem suas submissões.

### 2.2. Módulo de Administração Global
* **Gerenciamento de Usuários:**
    * Criação, listagem, visualização detalhada e edição de contas de usuário.
    * Funcionalidade para ativar e desativar usuários.
    * Atribuição de usuários a entidades organizacionais: Estabelecimento, Setor, Célula e Cargo.
    * (Futuro - Fase 2) Associação de Usuários a Perfis de Acesso.
    * (Futuro) Ferramenta para administradores resetarem senhas de usuários.
* **Gerenciamento de Estrutura Organizacional (Fase 1):**
    * CRUD completo (Criar, Ler, Atualizar, Ativar/Desativar) para **Estabelecimentos**, incluindo campos detalhados como CNPJ, razão social, endereço completo, tipo de estabelecimento, etc.
    * CRUD completo para **Setores**, vinculados a um Estabelecimento e status ativo/inativo.
    * CRUD completo para **Células**, vinculadas a um Setor e status ativo/inativo.
    * CRUD completo para **Cargos**, incluindo campo para nível hierárquico e status ativo/inativo.
* **Gerenciamento de Permissões por Funções:**
    * Definição de Funções (permissões granulares) (ex: `pode_criar_os_ti`, `pode_aprovar_artigo_financeiro`).
    * Associação de Funções aos Cargos e possibilidade de adicionar Funções extras a usuários específicos.

### 2.3. Página Inicial do Usuário (Pós-Login)
* Saudação personalizada ao usuário logado.
* Seção de "Acesso Rápido" com botões/cards para as funcionalidades mais utilizadas pelo perfil do usuário (ex: Novo Artigo, Abrir Nova OS [futuro], Pesquisar, Aprovações Pendentes).
* (Futuro) Resumo de pendências personalizadas (ex: OS atribuídas, artigos aguardando ação).
* (Futuro - Fase 4) Exibição dos comunicados mais recentes da empresa.

### 2.4. Perfil do Usuário
* Visualização de todos os dados cadastrais do usuário, incluindo nome, e-mail, matrícula, documentos (CPF, RG), informações de contato (ramal, telefone) e dados organizacionais (estabelecimento, setor, cargo, célula).
* Permissão para o próprio usuário editar suas informações pessoais permitidas (foto, nome completo, telefone de contato, ramal, data de nascimento).
* Funcionalidade de alteração de senha pelo próprio usuário, com validação de senha atual e requisitos de complexidade para a nova senha (feedback visual interativo).

### 2.5. Sistema de Notificações
* Alertas visuais (badge numérico na navbar principal) indicando a quantidade de notificações não lidas.
* Dropdown na navbar listando as notificações recentes, com links diretos para o conteúdo relevante.
* Marcação automática de uma notificação como "lida" (removendo o destaque visual e atualizando o `localStorage`) quando o usuário visita a página de destino da notificação, independentemente de como ele chegou lá.
* Persistência do estado de "lido" das notificações por usuário, utilizando o `localStorage` do navegador.

### 2.6. Funcionalidades Futuras (Roadmap Resumido)
* **Fase 3 (Planejada): Ordens de Serviço (OS) e Kanban**
    * Sistema completo para o ciclo de vida de Ordens de Serviço.
    * Interface Kanban para visualização e gerenciamento do fluxo de OS.
* **Fase 4 (Planejada): Central de Comunicação e Colaboração**
    * Mural de comunicados da empresa, notícias por setor, classificados internos.
    * (Opcional, muito avançado) Ferramenta de chat interno, potencialmente com chamadas de áudio/vídeo.

## 3. Arquitetura e Tecnologias

* **Backend:**
    * Linguagem: Python (3.9+)
    * Framework: Flask
* **Frontend:**
    * HTML5, CSS3, JavaScript (Vanilla)
    * Framework CSS: Bootstrap 5
    * Editor de Texto Rico: Quill.js
* **Template Engine:** Jinja2
* **Banco de Dados:** PostgreSQL (versão 12+)
* **ORM (Mapeamento Objeto-Relacional):** SQLAlchemy (via Flask-SQLAlchemy)
* **Migrations de Banco de Dados:** Alembic (via Flask-Migrate)
* **Servidor de Aplicação WSGI (Sugestão para Produção):** Gunicorn
* **Proxy Reverso / Servidor Web (Sugestão para Produção):** Nginx
* **Principais Bibliotecas Python Adicionais:**
    * `psycopg2-binary` (Driver PostgreSQL)
    * `Werkzeug` (Utilitários WSGI, usado pelo Flask)
    * `python-dotenv` (Gerenciamento de variáveis de ambiente a partir de arquivos `.env`)
    * `bleach` (Sanitização de HTML)
    * `python-docx` (Extração de texto de arquivos `.docx`)
    * `openpyxl` (Extração de texto de arquivos `.xlsx`)
    * `xlrd` (Extração de texto de arquivos `.xls` antigos)
    * `odfpy` (Extração de texto de arquivos `.ods`)
    * `PyPDF2` (Extração de texto de arquivos `.pdf`)

## 4. Estrutura de Diretórios Principal
```text
ORQUETASK_PROJECT_ROOT/
│
├── app.py                     # Aplicação Flask principal
├── database.py                # Configuração SQLAlchemy (db)
├── models.py                  # Modelos de dados
├── enums.py                   # Enumerações (ex: ArticleStatus)
├── utils.py                   # Funções utilitárias
├── requirements.txt           # Dependências Python
├── seed_users.py              # Script para dados iniciais de usuários
├── seed_organizacao.py        # Popula instituições, estabelecimentos e setores
├── .env                       # (Local, não versionado) Variáveis de ambiente
├── .env.example               # (Versionado) Exemplo de variáveis de ambiente
├── .gitignore                 # Arquivos ignorados pelo Git
│
├── migrations/                # Scripts de migração Alembic
│   ├── versions/
│   └── ...
│
├── static/                    # Arquivos estáticos
│   ├── css/
│   │   └── custom.css
│   ├── js/
│   │   └── main.js
│   ├── icons/                 # Ícones (favicon, logo)
│   ├── profile_pics/          # Fotos de perfil dos usuários
│   └── uploads_artigos/       # Anexos de artigos
│
├── templates/                 # Templates Jinja2
│   ├── base.html              # Layout principal com navbar e sidebar
│   ├── login.html
│   ├── pagina_inicial.html
│   ├── perfil.html
│   ├── admin/                 # Templates da área de administração
│   │   ├── dashboard.html
│   │   └── estabelecimentos.html
│   │   └── ...
│   └── partials/
│       └── _flash_messages.html
│   └── (outros templates de artigo, aprovação, etc.)
│
└── venv/                      # Ambiente virtual Python
```

## 5. Modelos de Dados Principais

Uma visão geral dos principais modelos de dados implementados e planejados:

* **User:**
    * Campos: `id`, `username`, `email`, `password_hash`, `nome_completo`, `foto`, `matricula`, `cpf`, `rg`, `ramal`, `data_nascimento`, `data_admissao`, `telefone_contato`, `ativo` (status do usuário).
    * Relacionamentos: `estabelecimento_id`, `setor_id`, `celula_id`, `cargo_id`. Liga-se a Artigos (autor), Notificações, Comentários, etc. As permissões disponíveis para o usuário derivam do cargo e das funções extras cadastradas para ele.
* **Estabelecimento:**
    * Campos: `id`, `codigo`, `nome_fantasia`, `razao_social`, `cnpj`, `inscricao_estadual`, `inscricao_municipal`, `tipo_estabelecimento`, `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado`, `telefone_principal`, `email_contato`, `data_abertura`, `observacoes`, `ativo`.
* **Setor:**
    * Campos: `id`, `nome`, `descricao`, `ativo`.
    * Relacionamentos: `estabelecimento_id` (pertence a um Estabelecimento).
* **Celula:**
    * Campos: `id`, `nome`, `ativo`.
    * Relacionamentos: `estabelecimento_id`, `setor_id`.
* **Cargo:**
    * Campos: `id`, `nome`, `descricao`, `nivel_hierarquico`, `ativo`.
* **Article:** (Existente)
    * Campos: `id`, `titulo`, `texto`, `status` (Enum: Rascunho, Pendente, Aprovado, etc.), `user_id` (autor), `created_at`, `updated_at`.
    * Relacionamentos: Anexos, Comentários de Revisão.
* **Attachment, Comment, Notification, RevisionRequest:** (Existentes, conforme detalhado anteriormente).
* **Funcao (Permissão):** `id`, `codigo`, `nome`. Associada a `Cargo` e personalizações de `User`. Os códigos de permissão são definidos no enum `Permissao` (`enums.py`) e seguem o nível hierárquico em que a ação se aplica.
* **(Futuro - Fase 3) OrdemServico, TarefaOS, etc.**
* **(Futuro - Fase 4) Comunicado, Classificado, MensagemChat, etc.**

## 6. Fluxos de Usuário Chave (Alto Nível)

* **Autenticação:** Usuário acessa `/login`, insere credenciais. Se válidas, é redirecionado para `/inicio`. Sessão é criada. Logout via link na navbar/sidebar.
* **Visualização/Edição de Perfil:** Usuário acessa `/perfil`, visualiza seus dados. Pode editar campos permitidos e alterar foto ou senha.
* **Criação de Artigo:** Usuário acessa `/novo_artigo`, preenche formulário, anexa arquivos, salva como rascunho ou envia para revisão.
* **Aprovação de Artigo:** Administrador acessa `/aprovacao`, visualiza artigos pendentes, abre um artigo (`/aprovacao_detail`), revisa, comenta, e aprova, rejeita ou solicita ajustes. Autor é notificado.
* **Administração de Estabelecimentos (Exemplo de CRUD Admin):** Admin acessa `/admin/dashboard`, navega para "Gerenciar Estabelecimentos". Visualiza lista, clica para adicionar novo ou editar existente. Formulário é preenchido/submetido. Lista é atualizada. Pode ativar/desativar.
* **(Futuro) Abertura de OS:** Usuário acessa formulário de OS, preenche detalhes, OS é criada com status inicial e atribuída ou entra em fila para triagem/atribuição. Notificações são geradas.

## 7. Roadmap de Desenvolvimento (Visão Atual)

* **Fase 1 (Em Andamento / Concluída):**
    * Estrutura base do Flask com PostgreSQL.
    * Módulo de Artigos completo (CRUD, fluxo de aprovação, busca, anexos).
    * Sistema de Notificações (badge, dropdown, marcação como lida, localStorage).
    * Layout Global com Navbar Fixa e Sidebar Responsiva (Offcanvas).
    * Página Inicial do Usuário (Dashboard básico).
    * Perfil do Usuário Detalhado (visualização, edição de dados, foto, alteração de senha com UX aprimorada).
    * Estrutura da Área de Administração (Dashboard Admin, início do CRUD de Estabelecimentos).
    * Modelos Organizacionais Base (`Estabelecimento`, `Setor`, `Célula`, `Cargo`) com status "ativo/inativo".
* **Fase 2 (Em Andamento):**
* Finalizar CRUDs da Área de Admin: Setores, Células e Cargos.
    * Gerenciamento Avançado de Usuários pelo Admin.
    * Sistema de permissões baseado em Funções associadas a Cargos e usuários.
    * Aplicar o novo sistema de permissões em todas as rotas e funcionalidades.
* **Fase 3 (Planejada - Funcionalidade Principal):**
    * Desenvolvimento do Módulo de Ordens de Serviço (OS):
        * Modelos de dados para OS, Tarefas da OS, Tipos, Prioridades, Status.
        * Rotas e lógica para todo o ciclo de vida da OS.
        * Interface do usuário para interação com as OS.
    * Desenvolvimento do Kanban de OS para visualização de fluxo.
* **Fase 4 (Planejada - Expansão e Colaboração):**
    * Implementação da Central de Comunicação da Empresa (Mural, Notícias de Setor, Classificados).
    * (Opcional, muito avançado) Desenvolvimento de um Comunicador Interno básico (Chat).

---
