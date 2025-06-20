# Gerenciamento de Permissões de Usuário

A partir desta versão, as permissões são definidas por **Funções**. Cada `Cargo` possui um conjunto padrão de funções, mas é possível customizar as permissões de cada usuário.

1. Ao selecionar um cargo no formulário de usuários, as funções vinculadas ao cargo são carregadas automaticamente.
2. O administrador pode marcar ou desmarcar funções para conceder ou remover permissões daquele padrão.
3. As diferenças em relação ao cargo são gravadas na tabela `user_funcoes`.
4. O login e os decoradores de acesso consultam `User.get_permissoes()` para validar as autorizações.

Essa estratégia permite flexibilidade na definição de permissões sem depender exclusivamente do papel (campo `role`).
