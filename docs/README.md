# Orquetask - Sistema Integrado de Gestão e Conhecimento

**Status do Projeto:** Em Desenvolvimento Ativo 🚧

## Sobre o Projeto

Orquetask é um sistema web integrado construído com Flask e Python. A base atual concentra-se na gestão de conhecimento técnico (repositório de artigos com fluxo de revisão/aprovação) e em um módulo administrativo robusto para organizar usuários e permissões. O código já contém modelos e templates para Processos e Ordens de Serviço, mas esses módulos ainda não estão habilitados na aplicação (o blueprint `processos_bp` não é registrado em `app.py` e não há rotas de OS expostas).

## Funcionalidades Principais

* **Biblioteca de Artigos:**
    * Criação, revisão, aprovação e publicação de artigos com controle de visibilidade.
    * Busca full-text em conteúdo e anexos.
* **Módulo de Administração Global:**
    * Gestão de usuários (campos completos, troca de senha e ativação/inativação).
    * Estrutura Organizacional: CRUD de Estabelecimentos, Setores, Células e Cargos.
    * Permissões: funções associadas a cargos e ajustes individuais por usuário.
* **Página Inicial / Dashboard:** visão geral pós-login com estatísticas de artigos e usuários.
* **Perfil de Usuário:** edição de dados pessoais, foto de perfil e senha.
* **Notificações:** avisos relacionados a artigos e revisões.
* **Temas Claro/Escuro e layout responsivo com sidebar.**
* **Módulos em desenvolvimento:** Processos (modelos e telas administrativas já versionados, porém desativados por padrão) e Ordens de Serviço (modelos utilitários sem rotas ativas).

## Tecnologias Utilizadas

* **Backend:** Python 3, Flask
* **Frontend:** HTML5, CSS3 (Bootstrap 5), JavaScript (Vanilla JS), Quill.js
* **Banco de Dados:** PostgreSQL
* **ORM / Migrations:** SQLAlchemy, Alembic (via Flask-SQLAlchemy, Flask-Migrate)
* **Principais Bibliotecas:** Werkzeug, Jinja2, psycopg2-binary, python-docx, openpyxl, xlrd, odfpy, pdf2image, pytesseract, Pillow, opencv-python, Bleach, python-dotenv.

## Pré-requisitos

Para rodar este projeto em um ambiente de desenvolvimento, você precisará ter instalado:
* Python (versão 3.11 recomendada – 3.10 também é compatível)
* Git
* PostgreSQL (versão 12 ou superior)
* (Opcional, mas recomendado para gerenciamento do DB) pgAdmin 4
* Poppler (utilitário para conversão de PDFs) – [download](https://github.com/oschwartz10612/poppler-windows/releases)
* Tesseract OCR – [download](https://github.com/UB-Mannheim/tesseract/wiki)

Consulte o passo a passo de instalação dessas dependências e a configuração do
`PATH` em nosso [Guia de Instalação](./GUIA_DE_INSTALACAO.md#6-instalacao-do-poppler-e-do-tesseract-dependencias-de-ocr).

## Como Rodar o Projeto (Desenvolvimento)

1.  **Clone o repositório:**
    ```bash
    git clone SEU_LINK_PARA_O_REPOSITORIO_GIT_AQUI
    cd NOME_DA_PASTA_DO_PROJETO
    ```

    > **Dica Rápida:** em sistemas Unix ou usando o Git Bash você pode
    > automatizar os passos de criação do ambiente virtual, instalação das
    > dependências, aplicação de migrações e inclusão de dados de exemplo
    > executando:
    > ```bash
    > ./setup.sh
    > ```
    > Após a execução do script, lembre-se apenas de configurar suas variáveis
    > de ambiente conforme o guia.

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
    # O arquivo `requirements.txt` já impõe `numpy<2`, garantindo uma versão suportada.
    # Caso ocorra erro envolvendo NumPy ou lxml em Python 3.11,
    # reinstale os pacotes compilados:
    pip install --force-reinstall lxml "numpy<2" opencv-python python-docx
    ```

4.  **Configure o Banco de Dados PostgreSQL e Variáveis de Ambiente:**

    * Siga as instruções detalhadas no nosso **[Guia de Instalação e Configuração](./GUIA_DE_INSTALACAO.md)** para criar o banco de dados, o usuário do banco com as permissões corretas, e para configurar as variáveis de ambiente essenciais (`FLASK_APP`, `FLASK_DEBUG`, `SECRET_KEY`, `DATABASE_URI`).
    * Para habilitar o envio de e-mails, consulte a seção [Configurar Envio de E-mails com SendGrid](./GUIA_DE_INSTALACAO.md#14-configurar-envio-de-e-mails-com-sendgrid-opcional) e defina `SENDGRID_API_KEY` e `EMAIL_FROM` no seu ambiente.

5.  **Aplique as migrações do banco de dados:**
    ```bash
    flask db upgrade
    ```
    > A pasta `migrations/` já inclui uma revisão de merge para que o comando funcione
    > em um repositório recém-clonado sem conflitos de cabeças.
    > Se suas migrações incluírem novas colunas com `nullable=True` em tabelas já existentes (ex.: `User`), remova os registros atuais ou defina o campo como `nullable=False` temporariamente para que a migração execute sem erros. Depois do `flask db upgrade`, ajuste o campo para permitir nulos, se for o caso.

6.  **(Opcional) Popule dados de exemplo (funções, organização, usuários e artigos):**
    ```bash
    python -m seeds.seed
    ```

7.  **Rode a aplicação Flask:**
    ```bash
    flask run
    ```
    Acesse em seu navegador: `http://127.0.0.1:5000`

Para instruções de instalação e configuração **completas e detalhadas**, consulte:
* **[Guia de Instalação Completo](./GUIA_DE_INSTALACAO.md)**
* **[Guia de Implantação em Produção](./DEPLOY.md)**

## OCR de alta qualidade

Para extrair texto de imagens e PDFs com maior precisão, garanta que as
dependências de OCR estejam instaladas e configuradas corretamente.

### Instalação do Tesseract e Poppler

- **Debian/Ubuntu:** `sudo apt-get install tesseract-ocr poppler-utils`
- **Windows:** baixe os instaladores do
  [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) e do
  [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)
  e adicione os binários ao `PATH`.

### Variáveis de ambiente

- `OCR_LANG`: idiomas a serem usados pelo Tesseract. Ex.: `por+eng`.
- `OCR_PSMS`: lista de *Page Segmentation Modes* testados automaticamente. Ex.:
  `6,3`.

### Metadados retornados

As funções `extract_text_from_image` e `extract_text` retornam, além do texto,
um dicionário com informações como:

- `best_psm` — PSM selecionado.
- `candidates` — estatísticas de cada PSM testado.
- `angle` — rotação detectada.
- `processing_time` — tempo total de processamento.

### Teste de integração

O teste `tests/test_utils.py::test_extract_text_integration` é ignorado por
padrão. Para habilitá-lo:

1. Defina `OCR_TEST_FILE` com o caminho de um PDF ou imagem contendo texto.
2. Execute `pytest` normalmente; o teste será incluído na suíte.

## Estrutura do Projeto (Simplificada)
```text
/repositorio_equipe/
├── app.py
├── config.py
├── core/
│   ├── models.py
│   ├── enums.py
│   └── utils.py
├── blueprints/
│   ├── admin.py
│   ├── articles.py
│   └── auth.py
├── migrations/
├── static/
├── templates/
│   ├── admin/
│   ├── articles/
│   └── auth/
├── seeds/
│   ├── seed.py
│   ├── seed_demonstration.py
│   └── seed_processos.py
└── requirements.txt
```

## Módulo Processos

O módulo **Processos** (em desenvolvimento) define fluxos operacionais
reutilizáveis. Os modelos, seeds e templates estão versionados, mas o blueprint
`processos_bp` não é registrado em `app.py`, portanto as rotas de gestão de
processos ficam desativadas por padrão. Ative-o manualmente se precisar testar
o fluxo em ambiente controlado.

Diagrama simplificado:
```text
Processo → EtapaProcesso → CampoEtapa → RespostaEtapaOS
```

Exemplo de fluxo (`Onboarding de Novo Colaborador`):
1. **RH - Cadastro**
2. **TI - Acesso**
3. **Gestor - Boas-vindas**

Para cadastrar um processo, habilite o blueprint e use a interface de
administração ou os scripts de seed (`python -m seeds.seed`). Cada etapa pode
estar vinculada a um cargo e setor para controle de responsáveis. A integração
com Ordens de Serviço ainda não possui rotas ativas; o relacionamento permanece
no nível de modelo para evolução futura.

## Tema, Modo Escuro e Acessibilidade

### Variáveis de cor

As cores do projeto são controladas por variáveis CSS declaradas em
`static/css/custom.css`. O bloco `:root` define as cores para o tema claro e o
seletor `[data-bs-theme="dark"]` sobrescreve os valores quando o modo escuro é
ativo. Utilize essas variáveis em novos componentes para herdar automaticamente
os estilos de ambos os temas:

```html
<div class="p-3" style="background-color: var(--bg-default); color: var(--text-default);">
  Exemplo com variáveis de cor
</div>
```

Caso precise de novas cores, adicione variáveis correspondentes nos dois blocos
para garantir contraste adequado em todos os temas.

### Adicionando novos elementos

Evite usar valores hexadecimais fixos como `#fff` ou `#000`. Prefira sempre as
variáveis existentes (`var(--bg-default)`, `var(--text-default)` etc.). Se um
componente exigir uma cor específica, crie uma nova variável e forneça a versão
para o modo escuro em `[data-bs-theme="dark"]`.

### Toggle de tema

O modo escuro é alternado por um script simples que persiste a preferência no
`localStorage`:

```javascript
const THEME_KEY = "theme";

function applyTheme(theme) {
  if (theme === "dark") {
    document.documentElement.setAttribute("data-bs-theme", "dark");
  } else {
    document.documentElement.removeAttribute("data-bs-theme");
  }
}

function toggleTheme() {
  const newTheme = localStorage.getItem(THEME_KEY) === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, newTheme);
  applyTheme(newTheme);
}

document.getElementById("themeToggle")?.addEventListener("click", function (e) {
  e.preventDefault();
  toggleTheme();
});
```

### Dicas de acessibilidade

* Mantenha contraste mínimo de **4.5:1** entre texto e fundo, conforme as
  recomendações da [WCAG](https://www.w3.org/TR/WCAG21/).
* Não dependa apenas de cores para transmitir informação; utilize também ícones
  ou texto.
* Verifique o contraste com ferramentas como o WebAIM Contrast Checker ou o
  Lighthouse.

## Integração Contínua

O repositório conta com um workflow do **GitHub Actions** localizado em
`.github/workflows/ci.yml`. Ele instala as dependências e executa os
testes automatizados com `pytest` a cada `push` ou `pull request`,
ajudando a prevenir regressões.

## Licença

Este projeto está licenciado sob a Licença GNU GPLv3 - veja o arquivo [LICENSE](LICENSE) para detalhes.

---
