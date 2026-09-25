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

## Contrato de metadados e capacidades

As respostas de metadados retornam `id`, `title`, `diagram_type`,
`current_version`, `current_version_id`, `cache_token`, `preview_state`,
`preview_url` e as capacidades `can_view`, `can_edit` e `can_open_scene` (também
agrupadas em `capabilities`). `cache_token` e o parâmetro `v` das URLs permitem
invalidar caches quando a versão corrente mudar.

`editor_url` só existe quando `can_edit` é verdadeiro. Uma leitura direta pode
receber `view_url` e `scene_url`; ela nunca é descrita como edição. UUIDs
inexistentes, arquivados ou fora do escopo resultam na mesma resposta 404.

`GET /api/diagramas/metadados` aceita `tipo=diagrama|modelo`, `q`, `page` e
`per_page` e retorna um envelope paginado. A consulta parte obrigatoriamente de
`scoped_diagrams`, portanto pesquisa e paginação não ampliam a descoberta.

O endpoint contextual
`GET /api/artigos/<article_id>/diagramas/<diagram_id>/metadados` não amplia a
política existente: exige artigo visível, vínculo `ArticleDiagram` materializado
e `diagrama_renderizar_artigo`. Ele retorna apenas dados da versão corrente e a
URL do preview raster contextual. `can_edit` e `can_open_scene` são falsos e não
são retornados `editor_url`, `view_url`, `scene_url`, histórico ou dados de
compartilhamento. Não há endpoint contextual de cena.
