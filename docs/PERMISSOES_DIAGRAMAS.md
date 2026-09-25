# Permissões de diagramas

As permissões abaixo pertencem à categoria **Permissões de Diagramas** e são
materializadas como `Funcao` pelo sincronizador central do catálogo. Não existe
uma tabela de papéis específica para diagramas.

| Código | Ação |
| --- | --- |
| `diagrama_visualizar` | Descobrir o diagrama na biblioteca e abrir cena, metadados, histórico e preview direto. |
| `diagrama_criar` | Criar um diagrama. |
| `diagrama_editar` | Alterar um diagrama próprio (administradores podem alterar qualquer um). |
| `diagrama_arquivar` | Arquivar um diagrama próprio (administradores podem arquivar qualquer um). |
| `diagrama_modelo_gerenciar` | Criar e alterar modelos. |
| `diagrama_renderizar_artigo` | Ver o preview de uma incorporação em um artigo acessível. |

## Incorporação em artigos

A incorporação tem uma regra intencionalmente separada da visualização da
biblioteca. Para renderizá-la, o usuário precisa ter
`diagrama_renderizar_artigo`, poder visualizar o artigo e existir um vínculo
`ArticleDiagram` entre aquele artigo e diagrama.

Essa autorização libera **somente a imagem do preview** pela URL contextual do
artigo. Ela não concede `diagrama_visualizar`, não faz o diagrama aparecer na
biblioteca e não dá acesso à cena JSON, aos metadados, às versões nem ao editor.
Copiar a URL normal do diagrama continua sujeito a `diagrama_visualizar` e ao
escopo do diagrama.
