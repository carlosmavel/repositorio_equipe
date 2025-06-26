# Tarefas para Unificar Permissões

Este checklist organiza as ações necessárias para abandonar a antiga
lógica de **exibição por função** e centralizar o controle de acesso a
partir das permissões cadastradas em `Funcao` e vinculadas aos `Cargos`.

1. **Limpar referências ao modelo antigo**
   - Remover variáveis de sessão ou condicionais nos templates que usem
     `role` ou qualquer outra flag antiga de função.
   - Confirmar que o modelo `User` não possui mais a coluna `role`
     (ver migration `remove_role_column`).

2. **Migration de exclusão das tabelas legadas**
   - Criar uma migration (ex.: `f5c6d7e8a9b0_drop_legacy_role_tables`) que
     elimine tabelas ou colunas do esquema anterior, como `legacy_role` e
     `legacy_role_permissions`.
   - Executar `flask db upgrade` após gerar a migration para aplicar a
     limpeza no banco.

3. **Permissões parametrizadas nos cargos**
   - Manter a tabela `funcao` com todas as funcionalidades do sistema.
   - Exibir checkboxes listando cada `Funcao` nos formulários de criação e
     edição de `Cargo`.
   - Ao selecionar um cargo, carregar as permissões associadas e permitir
     marcar ou desmarcar funções adicionais conforme necessário. Permissões
     extras individuais continuam armazenadas em `user_funcoes`.

4. **Verificações de acesso nas páginas**
   - Todas as rotas e telas devem checar `current_user.has_permissao(<codigo>)`
     antes de liberar ações ou exibir recursos restritos.
   - O decorador `admin_required` permanece apenas para rotas de
     administração geral, exigindo a permissão `admin`.

5. **Lista completa de funções**
   - Criar (ou atualizar) um script de seed que insira na tabela `funcao`
     todas as funções disponíveis no sistema. As permissões ligadas a
     artigos agora são definidas pelo enum `Permissao` em `enums.py`, que
     diferencia cada ação conforme o nível da hierarquia. Exemplos de
     códigos:
       - `ARTIGO_EDITAR_CELULA`
       - `ARTIGO_APROVAR_SETOR`
       - `ARTIGO_REVISAR_ESTABELECIMENTO`
       - `ARTIGO_ASSUMIR_REVISAO_INSTITUICAO`
   - Utilize essa lista para preencher os checkboxes de cargos e dos
     formulários de usuários.
6. **Reorganizar página de Cargos**
   - Alterar `admin/cargos.html` para exibir os cargos seguindo o fluxo de permissão:
     **Instituição → Estabelecimento → Setor → Célula → Cargo**.
   - Cada nível deve agrupar visualmente o próximo para facilitar a localização dos cargos e sua relação dentro da estrutura organizacional.


Com esses passos, todo o acesso passará a ser concedido
exclusivamente pelas permissões configuradas nos cargos, sem depender
da lógica antiga de exibição por função.
