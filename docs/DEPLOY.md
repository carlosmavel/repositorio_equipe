# Guia de Implantação do OrqueTask

Este documento descreve os passos para implantar a aplicação **OrqueTask** em um ambiente de produção. Siga a ordem dos tópicos para garantir uma instalação segura e estável.

Esta versão inclui o módulo **Processos**, que define fluxos compostos por etapas e campos dinâmicos. Certifique-se de aplicar as migrações mais recentes antes de executar o sistema.

## 1. Pré-requisitos
 - Python 3.11 (ou 3.10) instalado
- Git
- PostgreSQL 12 ou superior (recomenda-se o uso do pgAdmin para administração)
- Poppler para conversão de PDFs
- Tesseract OCR

Estes itens são os mesmos listados na seção de pré-requisitos do projeto【F:docs/README.md†L34-L47】.

## 2. Instalação do ambiente
1. **Clone o repositório** e acesse a pasta:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd repositorio_equipe
   ```
   Se desejar automatizar a criação do ambiente virtual e a instalação de dependências, execute o script `setup.sh` conforme indicado na documentação do projeto【F:docs/README.md†L56-L63】.
2. **Crie um ambiente virtual** e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Aplique as migrações do banco** e (opcionalmente) rode os seeds:
   ```bash
   flask db upgrade
   python seed.py  # opcional - inclui exemplo do processo de onboarding
   ```

## 3. Configuração do `.env`
Copie o arquivo `.env.example` para `.env` e defina os valores das variáveis `SENDGRID_API_KEY`, `EMAIL_FROM`, `SECRET_KEY` e `DATABASE_URI`. Essas variáveis são obrigatórias para a aplicação【F:docs/GUIA_DE_INSTALACAO.md†L174-L188】【F:docs/GUIA_DE_INSTALACAO.md†L188-L230】. Um exemplo de `.env` pode ser visto abaixo:
```bash
SENDGRID_API_KEY=seu_token_sendgrid
EMAIL_FROM=notificacoes@exemplo.com
SECRET_KEY=<sua_chave_aleatoria>
DATABASE_URI=postgresql://usuario:senha@localhost:5432/repositorio_equipe_db
```
Garanta também que `FLASK_APP=app.py` e `FLASK_DEBUG=0` estejam configurados para execução em produção.

## 4. Execução em produção
Recomenda-se executar o Flask através do **Gunicorn** ou outro servidor WSGI. Um exemplo simples:
```bash
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
Crie um serviço systemd para iniciar automaticamente o Gunicorn após a inicialização do servidor e assegurar reinícios quando necessário.

## 5. Configuração de firewall
- Abra a porta utilizada pelo Gunicorn/Nginx (ex.: 80 ou 8000) para tráfego HTTP.
- Caso o banco de dados PostgreSQL esteja em outro servidor, libere a porta 5432 apenas para o IP da aplicação. A documentação do projeto alerta para verificar se o firewall não bloqueia essa porta【F:docs/GUIA_DE_INSTALACAO.md†L268-L274】.

## 6. Logs da aplicação
A aplicação utiliza o módulo `logging` do Python e envia as saídas para o `stdout`. Ao executar com Gunicorn ou systemd, redirecione essas saídas para arquivos ou use `journalctl` para visualizá-las. Monitore erros e avisos durante a inicialização, principalmente mensagens referentes às variáveis de ambiente obrigatórias mostradas em `app.py`【F:app.py†L118-L159】.

## 7. Tarefas agendadas (opcional)
Não há jobs definidos no repositório, mas recomenda-se criar tarefas cron para:
- Rotacionar ou remover logs antigos.
- Executar rotinas de backup.

## 8. Backup do banco de dados
Realize backups periódicos utilizando o `pg_dump`:
```bash
pg_dump -U usuario -h localhost repositorio_equipe_db > /caminho/para/backup.sql
```
Agende a execução diária desse comando e garanta cópias externas em local seguro.

## 9. FAQ – Dúvidas Frequentes
**Q1: A aplicação não inicia e exibe erro sobre SECRET_KEY ou DATABASE_URI.**
- Certifique-se de que o arquivo `.env` está correto e que as variáveis foram exportadas, conforme descrito na seção de configuração.

**Q2: Não consigo conectar ao banco de dados.**
- Verifique se o serviço PostgreSQL está ativo e se a `DATABASE_URI` contém usuário, senha, host e porta corretos【F:docs/GUIA_DE_INSTALACAO.md†L268-L274】.

**Q3: Falha ao enviar e-mails.**
- Confira se `SENDGRID_API_KEY` e `EMAIL_FROM` estão preenchidos e válidos. Consulte o guia de instalação para detalhes de configuração do SendGrid【F:docs/GUIA_DE_INSTALACAO.md†L268-L320】.

Com estas orientações, a equipe de infraestrutura poderá implantar o OrqueTask em produção com segurança.
