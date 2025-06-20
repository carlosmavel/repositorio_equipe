# Fluxo de Permissões por Funções

Esta versão implementa a herança de permissões a partir do **Cargo**.
Ao abrir o formulário de usuário, as funções do cargo selecionado são marcadas
automaticamente e o administrador pode adicionar funções extras. Somente as
permissões adicionais são salvas em `user_funcoes`.

Durante o login, as permissões efetivas são calculadas pela combinação das
funções do cargo com as personalizadas do usuário. Decisões de acesso,
como o decorador `admin_required`, utilizam `user.get_permissoes()` para
validar se o usuário possui a permissão de código `admin`.
