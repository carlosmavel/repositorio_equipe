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

Cada `Funcao` registrada no banco equivale a uma permissão específica.
O arquivo `enums.py` define o enum `Permissao`, que concentra todos os
códigos ligados a artigos e diferencia cada ação pelo nível hierárquico
em que se aplica. Um mesmo **Cargo** pode ter várias dessas funções
associadas e o usuário ainda pode receber permissões extras além das
herdadas do cargo. As checagens de acesso (em rotas ou templates) devem
chamar `user.has_permissao(<codigo>)`.

```python
# Criação de funções básicas de edição e aprovação
from enums import Permissao

f1 = Funcao(codigo=Permissao.ARTIGO_EDITAR_CELULA.value, nome="Editar na célula")
f2 = Funcao(codigo=Permissao.ARTIGO_APROVAR_SETOR.value, nome="Aprovar no setor")

db.session.add_all([f1, f2])
db.session.commit()

# Associação das permissões a um cargo
# (exemplo de associação utilizando o enum)
```

Para uma visão passo a passo das alterações pendentes e ações necessárias para consolidar esse modelo de permissões, consulte o documento [TAREFAS_PERMISSOES.md](./TAREFAS_PERMISSOES.md).
