# Guia de Instalação e Configuração do Orquetask em Ambiente Windows

Este guia detalha os passos necessários para configurar e executar o projeto Orquetask em um computador com sistema operacional Windows.

## 1. Pré-requisitos de Software

Antes de iniciar, certifique-se de que possui os seguintes softwares instalados em sua máquina:

* **Python:** Versão 3.9 ou superior.
* **Git:** Para controle de versão e clonagem do repositório.
* **PostgreSQL:** Sistema de gerenciamento de banco de dados, versão 12 ou superior.
* **pgAdmin 4:** Interface gráfica para gerenciar o PostgreSQL (geralmente instalada junto com o PostgreSQL).
* **PaddleOCR:** Dependência para reconhecer texto em PDFs digitalizados.
* Um **editor de código** de sua preferência (ex: VS Code, PyCharm, Sublime Text).
* **Acesso à Internet.**
* **Permissões de Administrador** no Windows (podem ser necessárias para algumas instalações).

## 2. Instalação do Python

1.  **Baixe o Python:** Acesse [python.org/downloads/](https://python.org/downloads/) e baixe o instalador para Windows de uma versão estável recente (ex: 3.10, 3.11, 3.12).
2.  **Execute o Instalador:**
    * **MUITO IMPORTANTE:** Na primeira tela do instalador, marque a caixa de seleção **"Add Python X.Y to PATH"** (ou "Add python.exe to PATH"). Isso é crucial para utilizar os comandos `python` e `pip` facilmente no terminal.
    * Prossiga com a instalação. A opção "Install Now" com as configurações padrão geralmente é suficiente.
3.  **Verifique a Instalação:**
    * Abra o **PowerShell** ou o **Prompt de Comando (CMD)**.
    * Digite `python --version` e pressione Enter. A versão instalada do Python deve ser exibida.
    * Digite `pip --version` e pressione Enter. A versão do pip (gerenciador de pacotes do Python) deve ser exibida.

## 3. Instalação do Git

1.  **Baixe o Git:** Acesse [git-scm.com/download/win](https://git-scm.com/download/win) e baixe o instalador para Windows.
2.  **Execute o Instalador:**
    * Você pode seguir com as opções padrão na maioria das telas do instalador.
    * É recomendado incluir a opção "Git Bash Here" na integração com o Windows Explorer.
    * Para o editor padrão do Git, você pode manter o Vim ou escolher outro que já tenha instalado.
    * Na configuração do PATH, a opção recomendada "Git from the command line and also from 3rd-party software" é geralmente a melhor escolha.
3.  **Verifique a Instalação:**
    * Abra um novo PowerShell, CMD, ou preferencialmente o **Git Bash** (instalado com o Git).
    * Digite `git --version` e pressione Enter. A versão instalada do Git deve ser exibida.

## 4. Instalação do PostgreSQL e pgAdmin 4

1.  **Baixe o PostgreSQL:** Acesse [postgresql.org/download/windows/](https://www.postgresql.org/download/windows/) e escolha um instalador (geralmente os fornecidos pela EnterpriseDB são uma boa opção). Selecione uma versão estável (ex: 14, 15, 16).
2.  **Execute o Instalador:**
    * Siga as instruções do assistente de instalação.
    * Selecione os componentes a serem instalados: no mínimo "PostgreSQL Server", "pgAdmin 4", e "Command Line Tools".
    * Defina um diretório para os dados (`Data Directory`) ou mantenha o padrão.
    * **MUITO IMPORTANTE:** Durante a instalação, você será solicitado a definir uma **senha para o superusuário do banco de dados (o usuário `postgres`)**. Escolha uma senha forte e guarde-a em um local seguro, pois você precisará dela para administrar o servidor PostgreSQL.
    * Mantenha a porta padrão (`5432`), a menos que haja um motivo específico para alterá-la.
    * Selecione o Locale (Região) de acordo com sua preferência (ex: `Portuguese, Brazil`).
3.  **Após a Instalação:** O pgAdmin 4 deverá estar disponível no menu Iniciar.

## 5. Configuração do Banco de Dados PostgreSQL para o Orquetask

Após instalar o PostgreSQL, vamos criar um banco de dados dedicado e um usuário específico para a aplicação Orquetask.

1.  **Abra o pgAdmin 4.**
2.  **Conecte-se ao seu Servidor PostgreSQL Local:** Use a senha do superusuário `postgres` que você definiu durante a instalação do PostgreSQL.
3.  **Crie o Banco de Dados (`repositorio_equipe_db`):**
    * No painel esquerdo do pgAdmin, expanda a árvore do seu servidor.
    * Clique com o botão direito em **"Databases"** e selecione **"Create"** -> **"Database..."**.
    * Na aba **"General"**:
        * **Database:** `repositorio_equipe_db` (este é o nome esperado pela aplicação)
        * **Owner:** Deixe como `postgres` (ou o superusuário que você está usando).
    * Na aba **"Definition"** (recomendado):
        * **Encoding:** `UTF8`
        * **Template:** `template0`
        * **LC_COLLATE / LC_CTYPE:** `Portuguese_Brazil.1252` ou, preferencialmente, um equivalente UTF-8 como `pt_BR.UTF-8` (se disponível na sua instalação do PostgreSQL).
    * Clique em **"Save"**.
4.  **Crie um Usuário Dedicado e Seguro para a Aplicação:**
    * No painel esquerdo, sob o seu servidor, clique com o botão direito em **"Login/Group Roles"** e selecione **"Create"** -> **"Login/Group Role..."**.
    * Na aba **"General"**:
        * **Role Name:** Escolha um nome para o usuário da aplicação, por exemplo: `orquetask_user`
    * Na aba **"Definition"**:
        * **Password:** **DIGITE UMA SENHA NOVA, FORTE E ÚNICA AQUI.** Não use senhas fáceis ou reutilizadas.
        * **ANOTE ESTA SENHA em um local seguro.** Você precisará dela no Passo 9 para configurar a variável de ambiente `DATABASE_URI`.
    * Na aba **"Privileges"**:
        * **Can login?:** Marque como `Yes`.
        * Garanta que as outras opções de superusuário (Create DB, Superuser, etc.) estejam como `No`.
    * Clique em **"Save"**.
5.  **Conceda os Privilégios Mínimos Necessários ao Novo Usuário:**
    * **Por que isso é importante?** Para segurança, o usuário da aplicação deve ter apenas as permissões estritamente necessárias para operar (Princípio do Menor Privilégio).
    * **Como fazer:** No pgAdmin, selecione o banco de dados `repositorio_equipe_db`, abra a "Query Tool" (Ferramenta de Consulta SQL) e execute os seguintes comandos, substituindo `orquetask_user` pelo nome exato que você deu ao seu novo usuário no passo anterior:

        ```sql
        -- Permite que orquetask_user se conecte ao banco de dados
        GRANT CONNECT ON DATABASE repositorio_equipe_db TO orquetask_user;

        -- Permite que orquetask_user utilize o schema 'public'
        GRANT USAGE ON SCHEMA public TO orquetask_user;

        -- Permissões de manipulação de dados para tabelas e sequences existentes
        GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public TO orquetask_user;
        GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO orquetask_user;

        -- Permissão para criar novas tabelas (necessário para o Flask-Migrate/Alembic)
        GRANT CREATE ON SCHEMA public TO orquetask_user;

        -- Define permissões padrão para futuras tabelas e sequences criadas neste schema
        -- para o usuário orquetask_user (útil para quando o Alembic cria novas estruturas)
        ALTER DEFAULT PRIVILEGES IN SCHEMA public FOR ROLE orquetask_user 
        GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES, TRIGGER ON TABLES TO orquetask_user;

        ALTER DEFAULT PRIVILEGES IN SCHEMA public FOR ROLE orquetask_user
        GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO orquetask_user;
        ```
    * **Explicação Breve dos `GRANT`s:** Esses comandos permitem que o `orquetask_user` se conecte ao banco, use o schema principal, realize operações de leitura e escrita nas tabelas, utilize as sequências para IDs automáticos e crie novas tabelas quando você rodar as migrações do Alembic. Ele não terá permissão para deletar o banco ou tabelas que não criou, ou realizar ações de superusuário.

## 6. Obter o Código do Projeto (Clonar o Repositório)
1.  Abra o **Git Bash** (ou outro terminal com Git configurado).
2.  Navegue até a pasta onde você deseja salvar os seus projetos (ex: `cd C:/Users/SeuUsuario/Documents/Projetos`).
3.  Clone o repositório do Orquetask (substitua pela URL correta do seu repositório):
    ```bash
    git clone URL_DO_SEU_REPOSITORIO_ORQUETASK.git
    ```
4.  Entre na pasta do projeto que foi clonada:
    ```bash
cd NOME_DA_PASTA_DO_PROJETO_ORQUETASK
```

### (Opcional) Configuração rápida com script
Se estiver em um ambiente baseado em Unix ou usando o **Git Bash**, você pode
executar todas as etapas de criação do ambiente virtual, instalação das
dependências, aplicação das migrações e popular os dados de exemplo com um único
comando:

```bash
./setup.sh
```

O script não define as variáveis de ambiente, portanto siga a próxima seção para
configurá-las corretamente.

## 7. Configurar o Ambiente Virtual Python (venv)
1.  Dentro da pasta raiz do projeto, no terminal:
    ```bash
    python -m venv venv
    ```
2.  Ative o Ambiente Virtual:
    * **No PowerShell:** `.\venv\Scripts\Activate.ps1`
        *(Se houver erro de política de execução, tente: `Set-ExecutionPolicy Unrestricted -Scope Process` nesta sessão do PowerShell e depois ative novamente).*
    * **No Git Bash / CMD:** `source venv/Scripts/activate` ou `venv\Scripts\activate.bat`
    * O prompt do seu terminal deve mudar, mostrando `(venv)` no início.

## 8. Instalar as Dependências Python do Projeto
Com o ambiente virtual (`venv`) ativo:
```bash
pip install -r requirements.txt
```

## 9. Configurar Variáveis de Ambiente Essenciais (no Windows)
Para que o Orquetask funcione corretamente e de forma segura, é crucial configurar algumas **variáveis de ambiente** no seu sistema Windows. Essas variáveis permitem que a aplicação acesse configurações importantes sem que elas precisem estar escritas diretamente no código.

Antes de prosseguir, copie o arquivo `.env.example` que acompanha o projeto para `.env` e preencha os valores de `SENDGRID_API_KEY`, `EMAIL_FROM`, `SECRET_KEY` e `DATABASE_URI` com suas próprias configurações. O Flask carregará essas variáveis automaticamente ao executar `flask run` se o arquivo `.env` estiver na raiz do projeto.

* **Por que usar Variáveis de Ambiente?**
    * **Segurança:** É a forma mais segura de gerenciar informações sensíveis como chaves secretas (`SECRET_KEY`) e credenciais de banco de dados (`DATABASE_URI`), mantendo-as fora do código-fonte que pode ser versionado no Git.
    * **Flexibilidade:** Permite que a mesma aplicação rode em diferentes ambientes (desenvolvimento local, servidor de teste, produção) com configurações diferentes, apenas ajustando as variáveis de ambiente de cada local.
    * **Boas Práticas:** É um padrão amplamente adotado para configurar aplicações.

O arquivo `app.py` do Orquetask está programado para ler essas variáveis do seu ambiente. Para a `SECRET_KEY` e a `DATABASE_URI`, o sistema foi configurado para **exigir** que estas sejam definidas no ambiente, não utilizando mais valores padrão inseguros diretamente do código para essas configurações críticas.

* **Variáveis Essenciais a Serem Definidas:**

    1.  **`FLASK_APP`**:
        * **Propósito:** Informa ao comando `flask` (usado para rodar a aplicação e as migrations) qual é o arquivo Python principal da sua aplicação Flask.
        * **Valor a Definir:** `app.py`

    2.  **`FLASK_DEBUG`**:
        * **Propósito:** Controla o modo de depuração do Flask. Quando ativo (`1`), ele mostra erros detalhados no navegador e recarrega o servidor automaticamente quando você faz alterações no código, o que é muito útil durante o desenvolvimento.
        * **Valor para Desenvolvimento:** `1`
        * *(Em um ambiente de produção, este valor seria `0`)*

    3.  **`SECRET_KEY`**:
        * **Propósito:** Uma chave secreta crucial para a segurança da sua aplicação Flask (usada para assinar cookies de sessão, proteger contra CSRF, etc.).
        * **AÇÃO OBRIGATÓRIA:** Você **DEVE** definir sua própria `SECRET_KEY` forte, longa, aleatória e única no ambiente. A aplicação foi configurada para dar erro se uma `SECRET_KEY` adequada não for fornecida através das variáveis de ambiente.
        * *Como gerar uma `SECRET_KEY` segura:* Abra um terminal Python (digite `python` e Enter) e execute:
            ```python
            import secrets
            print(secrets.token_hex(32))
            ```
        * Copie a longa string hexadecimal que for gerada. Este será o valor da sua variável `SECRET_KEY`.

    4.  **`DATABASE_URI`**:
        * **Propósito:** A string de conexão com o seu banco de dados PostgreSQL.
        * **AÇÃO OBRIGATÓRIA:** Você **DEVE** definir esta variável de ambiente com as credenciais do **novo usuário seguro** que você criou no Passo 5 do guia de configuração do banco de dados. A aplicação Orquetask foi configurada para dar erro se esta variável não for encontrada no ambiente, garantindo que apenas conexões seguras e explicitamente configuradas sejam usadas.
        * **Valor a Definir (exemplo de formato):**
            `postgresql://SEU_NOVO_USUARIO_DO_BANCO:SUA_NOVA_SENHA_FORTE@localhost:5432/repositorio_equipe_db`
            *(Substitua `SEU_NOVO_USUARIO_DO_BANCO` e `SUA_NOVA_SENHA_FORTE` pelos que você criou no Passo 5. Lembre-se de codificar caracteres especiais na senha se houver, como `!` que vira `%21`).*

* **Como Definir as Variáveis de Ambiente Permanentemente no Windows (Recomendado):**

    1.  Na barra de busca do Windows, digite "**variáveis de ambiente**".
    2.  Selecione a opção "**Editar as variáveis de ambiente do sistema**".
    3.  Na janela "Propriedades do Sistema" que abrir, clique no botão "**Variáveis de Ambiente...**".
    4.  Na seção "**Variáveis de usuário para [SeuNomeDeUsuário]**":
        * Clique em "**Novo...**" para adicionar cada uma das variáveis listadas acima (`FLASK_APP`, `FLASK_DEBUG`, `SECRET_KEY`, `DATABASE_URI`).
        * **Nome da variável:** Digite o nome exato (ex: `SECRET_KEY`).
        * **Valor da variável:** Digite/cole o valor correspondente (ex: a chave hexadecimal longa que você gerou para a `SECRET_KEY`).
        * Clique "**OK**" para salvar cada variável.
    5.  Clique "**OK**" em todas as janelas de configuração abertas.
    6.  **MUITO IMPORTANTE:** Você precisará **fechar e reabrir QUALQUER terminal** (PowerShell, CMD, Git Bash) que estiver aberto. O VS Code ou seu editor de código também podem precisar ser reiniciados se tiverem um terminal integrado. Isso é necessário para que eles carreguem as novas variáveis de ambiente permanentes.

    *(Opcionalmente, para testes rápidos, você pode definir variáveis temporariamente em uma sessão do PowerShell usando `$env:NOME_VARIAVEL = "VALOR"`, mas elas não persistirão).*

Com essas variáveis corretamente configuradas, o Orquetask estará pronto para rodar usando configurações seguras e específicas do seu setup.

## 10. Aplicar as Migrações do Banco de Dados
Com o ambiente virtual ativo e as variáveis de ambiente configuradas (especialmente a `DATABASE_URI` correta):
```bash
flask db upgrade
```
Este comando executará todos os scripts de migração na pasta migrations/versions/ e criará todas as tabelas e estruturas necessárias no seu banco de dados repositorio_equipe_db (ou o nome que você configurou na sua DATABASE_URI).

> **Observação:** se você adicionar uma nova coluna marcada como `nullable=True` em modelos existentes (como o `User`), remova previamente os registros ou deixe o campo temporariamente como `nullable=False` para rodar o `flask db upgrade`. Após a migração, altere o campo no banco para aceitar valores nulos, se desejar.

## 11. (Opcional, mas Recomendado) Popular Dados de Exemplo
Execute o script abaixo para criar funções, organização, usuários e artigos básicos:
```bash
python seed.py
```

## 12. Rodar a Aplicação Flask
Finalmente! Para rodar o servidor de desenvolvimento do Flask:
```bash
flask run (ou `python -m flask run`)
```
O terminal deverá exibir mensagens indicando que o servidor está rodando, geralmente em `http://127.0.0.1:5000/`.

Abra seu navegador de internet e acesse `http://127.0.0.1:5000/`. Você deverá ver a página de login do Orquetask ou ser redirecionado para ela.

## 13. Solução de Problemas Comuns no Windows

* **Comandos não encontrados (`python`, `pip`, `flask`, `git`):**
    * Verifique se o software correspondente foi adicionado ao **PATH** do sistema durante sua instalação.
    * Reinicie o terminal (PowerShell, CMD, Git Bash) após instalar um software para que ele reconheça as novas variáveis de PATH.
    * Para o comando `flask`, certifique-se de que o ambiente virtual (`venv`) está ativo.

* **Erro de execução de script no PowerShell ao tentar ativar o `venv` (`Activate.ps1`):**
    * Pode ser necessário alterar a política de execução de scripts para a sessão atual do PowerShell. Execute no PowerShell: `Set-ExecutionPolicy Unrestricted -Scope Process` e tente ativar o `venv` novamente.

* **Erro de Conexão com o Banco de Dados (`psycopg2` ou `SQLAlchemy`):**
    * Verifique se o serviço do PostgreSQL está rodando no seu Windows.
    * Confirme se a `DATABASE_URI` (definida como variável de ambiente) está 100% correta: usuário, senha, host (geralmente `localhost`), porta (geralmente `5432`) e nome do banco de dados.
    * Verifique se o firewall do Windows ou algum software antivírus não está bloqueando a conexão do Python com o PostgreSQL na porta configurada.
    * Confirme no pgAdmin se o usuário especificado na `DATABASE_URI` possui as permissões necessárias (pelo menos `CONNECT`) para o banco de dados especificado.

* **Erro `FLASK_APP not set` ao tentar usar o comando `flask`:**
    * Garanta que a variável de ambiente `FLASK_APP` está definida como `app.py` (ou o nome do seu arquivo principal Flask) e que o terminal foi reiniciado após definir a variável permanentemente.

---

## 14. Configurar Envio de E-mails com SendGrid (Opcional)

Para que o Orquetask possa enviar notificações por e-mail é possível utilizar o
serviço **SendGrid**. Os passos abaixo cobrem a configuração mínima para testes:

1. **Crie e verifique um remetente (Single Sender):**
   1. Acesse o painel do SendGrid e navegue em
      "**Settings > Sender Authentication**".
   2. Escolha **"Create a Single Sender"** e informe nome e endereço de e-mail
      que deseja usar. Um e-mail de verificação será enviado para confirmar o
      remetente.
2. **Gere uma chave de API (API Key):**
   1. No painel do SendGrid, vá em **"Settings > API Keys"**.
   2. Clique em **"Create API Key"**, dê um nome para identificação e selecione
      ao menos a permissão **"Mail Send"**.
   3. Copie o valor da chave gerada – ela será utilizada na variável de ambiente
      `SENDGRID_API_KEY`.
3. **Defina as variáveis de ambiente:**
   * `SENDGRID_API_KEY` – chave gerada no passo anterior.
   * `EMAIL_FROM` – o endereço de e-mail verificado que será usado como
     remetente.
   * Você pode adicioná-las seguindo o mesmo procedimento descrito na etapa 9
     deste guia para variáveis permanentes no Windows.
4. **(Opcional)** Configure a autenticação de domínio no SendGrid para melhorar
   a entrega dos e-mails. Para os primeiros testes, a autenticação de domínio
   não é obrigatória.

Com essas configurações, a função de envio de e-mails presente em `utils.py`
conseguirá utilizar o serviço do SendGrid sempre que necessário.
