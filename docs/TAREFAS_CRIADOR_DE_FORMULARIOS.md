# Tarefas para Implementar o Criador de Formulários

## 1. Planejamento & Configuração Inicial
- Definir branch de desenvolvimento e alinhar padrões de código/permissões.
- Revisar versões de dependências (Flask, Alembic, JS libs) para garantir compatibilidade.

## 2. Modelagem e Migrações do Banco
### 2.1 Cargo
- Atualizar `models.py` adicionando campo `atende_ordem_servico` (Boolean, default False).
- Gerar e aplicar a migration que inclui o campo em cargos.

### 2.2 Formulários
- Criar modelos `Formulario` e `CampoFormulario` com os campos especificados.
- Definir relações (1:N entre `Formulario` e `CampoFormulario`).
- Gerar migrations para criação das tabelas `formulario` e `campo_formulario`.
- Aplicar migrations em ambientes de dev/homolog/produção.

## 3. Permissões e Utilitários
- Criar/ajustar função `user_can_access_form_builder` (ou similar) verificando: usuário logado + `cargo.atende_ordem_servico`.
- Garantir verificação tanto no backend (decoradores/rotas) quanto no template (exibição do menu).

## 4. Rotas e Blueprint "Formulários"
- Criar blueprint `formularios` em `/ordem-servico/formularios`.
- Rotas básicas:
  - Listagem (GET `/`)
  - Criação (GET/POST `/novo`)
  - Edição (GET/POST `/<id>/editar`)
  - Salvamento do JSON da estrutura.
- Aplicar a função de permissão em todas as rotas.

## 5. Interface de Usuário
### 5.1 Menu Lateral
- Inserir item "Criador de Formulários" dentro de "Ordem de Serviço", exibindo apenas quando `user_can_access_form_builder` for verdadeiro.

### 5.2 Página de Listagem
- Tabela/lista dos formulários existentes com botão "Novo Formulário".

### 5.3 Editor
- Form para nome do formulário.
- Componentes para adicionar/ordenar campos dinâmicos (tipo, label, obrigatório, ordem, opções, condicional).
- Pré-visualização dinâmica.
- Botões de salvar/cancelar.

### 5.4 Preenchimento por Etapas e Manual
- Implementar wizard que exiba campos conforme respostas (dependências).
- Adicionar botão "ℹ Manual de Preenchimento" com modal contendo instruções.

## 6. Atualização de `cargos.html`
- Seção "Permissões Ordem de Serviço" com checkbox "Pode atender OS?" ligado ao novo campo.
- Exibir nas telas de cadastro e edição de cargos.

## 7. Testes Automatizados
- Testar migrations (criação dos campos/tabelas).
- Testes de permissão (acesso ao menu, rotas protegidas).
- Testes de criação/edição de formulários e de renderização condicional dos campos.
- Cobrir interface (JS) com testes unitários/funcionais se houver infraestrutura.

## 8. Documentação e Deploy
- Atualizar docs do projeto com instruções de uso, permissões e processo de criação de formulários.
- Preparar script/manual de migração para ambientes de produção.
- Realizar deploy e validar a funcionalidade end-to-end.

**Observação:** Seguindo essa ordem – primeiro banco e modelos, depois permissões, rotas, UI e por fim testes e documentação – evitam-se conflitos de migração e garante-se integração suave entre as camadas do sistema.
