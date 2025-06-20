# Tarefas para Unificar Permissões

Esta lista resume as etapas necessárias para remover a lógica antiga baseada em `role` e consolidar o controle de acesso através de `Funcoes` vinculadas aos `Cargos`.

1. **Remover dependências de `role`**
   - Eliminar variáveis de sessão `role` e trechos de código que condicionam a exibição de páginas ou links com base nesse campo.
   - Ajustar o modelo `User` removendo a coluna `role` (migration `remove_role_column`).

2. **Gerar migração de limpeza**
   - Criar uma nova migration que exclua do banco quaisquer tabelas ou colunas remanescentes relacionadas ao controle antigo de funções.
   - Executar `flask db upgrade` para aplicar as mudanças.

3. **Permissões via `Funcao`**
   - Manter todas as permissões cadastradas na tabela `funcao`.
   - Incluir checkboxes para cada função nos formulários de criação/edição de `Cargo`.
   - Herdar essas permissões para os usuários conforme o cargo atribuído, permitindo permissões extras individuais (tabela `user_funcoes`).

4. **Checagem de acesso nas rotas**
   - Todas as rotas devem verificar `current_user.has_permissao(<codigo>)` antes de permitir a ação.
   - Utilizar o decorador `admin_required` apenas para rotas administrativas, mantendo o código de permissão `admin` como requisito.

5. **Listar funções disponíveis**
   - Criar um script de seed para popular a tabela `funcao` com todas as funcionalidades do sistema (ex.: `artigo_criar`, `artigo_aprovar`).
   - Garantir que o front-end carregue essa lista para exibir nos checkboxes de cargos e usuários.

Seguindo essas tarefas, a lógica de exibição antiga será removida e todo o sistema passará a conceder acesso exclusivamente pelas permissões configuradas nos cargos.
