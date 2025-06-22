# Fluxo de Permissões por Funções

Esta versão implementa a herança de permissões a partir do **Cargo**.
Ao abrir o formulário de usuário, as funções do cargo selecionado são marcadas
automaticamente e o administrador pode adicionar funções extras. Somente as
permissões adicionais são salvas em `user_funcoes`.

Durante o login, as permissões efetivas são calculadas pela combinação das
funções do cargo com as personalizadas do usuário. Decisões de acesso,
como o decorador `admin_required`, utilizam `user.get_permissoes()` para
validar se o usuário possui a permissão de código `admin`.

## Hierarquia do Sistema

Instituição → Estabelecimento → Setor → Célula → Cargo → Usuário

As permissões de cada usuário resultam das permissões do cargo somadas às permissões extras que possam ser atribuídas a ele.

## Funções como Permissões

Cada `Funcao` registrada no banco equivale a uma permissão específica, como `artigo_ler`, `artigo_criar` ou `artigo_aprovar_celula`. Um mesmo **Cargo** pode ter várias dessas funções associadas, assim como um usuário pode receber permissões extras além das herdadas do cargo. As checagens de acesso (em rotas ou templates) devem chamar `user.has_permissao(<codigo>)`.

```python
# Criação de funções
ler = Funcao(codigo="artigo_ler", nome="Ler artigos")
criar = Funcao(codigo="artigo_criar", nome="Criar artigos")
aprovar = Funcao(codigo="artigo_aprovar_celula", nome="Aprovar artigos na célula")

db.session.add_all([ler, criar, aprovar])
db.session.commit()

# Associação das permissões a um cargo
# (exemplo de associação de permissões a um cargo)
```

Para uma visão passo a passo das alterações pendentes e ações necessárias para consolidar esse modelo de permissões, consulte o documento [TAREFAS_PERMISSOES.md](./TAREFAS_PERMISSOES.md).
