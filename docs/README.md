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
    * Gerenciamento de Estrutura Organizacional: CRUD de Estabelecimentos, Setores, Células e Cargos.
    * Definição de permissões por meio de Funções associadas aos Cargos e ajustes individuais por usuário.
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
* **Principais Bibliotecas:** Werkzeug, Jinja2, psycopg2-binary, python-docx, openpyxl, xlrd, odfpy, pdf2image, pytesseract, Bleach, python-dotenv.

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

### Ajuste de DPI para OCR

Ao extrair texto de PDFs baseados em imagem, cada página é convertida em imagem
antes de passar pelo Tesseract. O DPI (*dots per inch*) utilizado nessa etapa
impacta diretamente o resultado: valores maiores tendem a gerar reconhecimento
mais preciso, porém aumentam o tempo de processamento e o consumo de memória.

O sistema utiliza por padrão **300 DPI**, mas é possível ajustar esse valor por
meio da variável de ambiente `PDF_OCR_DPI` ou passando o parâmetro `pdf_dpi` para
as funções utilitárias de extração de texto.

### Opções de pré-processamento para OCR

Além do DPI, é possível controlar etapas de pré-processamento das páginas antes
de enviá-las ao Tesseract. As funções `preprocess_image` e
`extract_text_from_pdf` possuem os parâmetros `apply_sharpen` e
`apply_threshold` que podem ser combinados conforme o tipo de documento:

* `apply_sharpen=True` e `apply_threshold=True` *(padrão)* – indicado para
  digitalizações comuns com texto pouco nítido.
* `apply_sharpen=False` e `apply_threshold=True` – útil quando o documento já é
  nítido, mas a binarização ajuda a remover ruídos.
* `apply_sharpen=False` e `apply_threshold=False` – preserva cores e detalhes de
  imagens ou recibos onde a binarização poderia eliminar informações.

Exemplo de uso:

```python
from core.utils import extract_text_from_pdf

texto = extract_text_from_pdf(
    "documento.pdf", apply_sharpen=False, apply_threshold=False
)
```


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
    python seed.py
    ```

7.  **Rode a aplicação Flask:**
    ```bash
    flask run
    ```
    Acesse em seu navegador: `http://127.0.0.1:5000`

Para instruções de instalação e configuração **completas e detalhadas**, por favor, consulte nosso:
* **[Guia de Instalação Completo](./GUIA_DE_INSTALACAO.md)**
* **[Documentação Geral do Sistema](./DOCUMENTACAO_DO_SISTEMA.md)**
* **[Tarefas de Revisão e Testes](./TAREFAS_REVISAO_SISTEMA.md)**
* **[Guia de Implantação em Produção](./DEPLOY.md)**

## Estrutura do Projeto (Simplificada)
```text
/ORQUETASK_PROJECT_ROOT/
├── app.py
├── models.py
├── requirements.txt
├── migrations/
├── static/
└── templates/
├── admin/
└── base.html
```

## Módulo Processos

O módulo **Processos** define fluxos operacionais reutilizáveis dentro do sistema.
Um processo é composto por diversas etapas ligadas a cargos e setores, cada uma
com campos personalizados que devem ser preenchidos quando a etapa é executada.

Diagrama simplificado:
```text
Processo → EtapaProcesso → CampoEtapa → RespostaEtapaOS
```

Exemplo de fluxo (`Onboarding de Novo Colaborador`):
1. **RH - Cadastro**
2. **TI - Acesso**
3. **Gestor - Boas-vindas**

Para cadastrar um processo, utilize a interface de administração ou scripts de
seed. Cada etapa pode estar vinculada a um cargo e setor para controle de
responsáveis. Uma Ordem de Serviço pode selecionar um `processo_id` e avançar
entre as etapas conforme as permissões do usuário.

Os processos se integram ao módulo de Ordem de Serviço, que está em constante
construção, além de Artigos e permissões por meio das notificações e da
atribuição de cargos responsáveis.

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
