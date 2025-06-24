# Tarefas de Revisão e Testes

Este documento lista ações recomendadas para verificar se o Orquetask está de acordo com o conceito descrito na documentação e para identificar eventuais bugs.

1. **Preparar Ambiente Local**
   - Siga o [Guia de Instalação](./GUIA_DE_INSTALACAO.md) para configurar variáveis de ambiente, dependências e banco de dados.
   - Execute `./setup.sh` (opcional) ou crie o ambiente virtual manualmente.

2. **Executar Testes Automatizados**
   - Rode `python -m pytest -v` e analise as falhas. Corrija erros ou ajustes de configuração necessários.

3. **Revisar Permissões e Acesso**
   - Validar se as verificações `current_user.has_permissao(...)` estão presentes em todas as rotas restritas.
   - Conferir se os cargos possuem as permissões corretas de acordo com `docs/TAREFAS_PERMISSOES.md`.

4. **Testar Fluxos de Cadastro e Autenticação**
   - Criar usuários de exemplo, alterar senhas e testar recuperação de senha.
   - Verificar mensagens de erro e validação de formulários.

5. **Avaliar Módulo de Artigos**
   - Criar, editar, enviar para revisão e aprovar artigos.
   - Testar anexos e a visibilidade por célula, setor, estabelecimento e instituição.

6. **Verificar Administração de Organização**
   - Exercitar o CRUD de Instituições, Estabelecimentos, Setores, Células e Cargos.
   - Confirmar regras de ativação/inativação e vínculos entre entidades.

7. **Analisar Sistema de Notificações**
   - Checar se alertas são exibidos corretamente e se o estado de leitura persiste.

8. **Conferir Migrations e Seeders**
   - Executar migrations em um banco vazio e rodar scripts `seed_*.py` para popular dados.
   - Garantir que o processo finalize sem erros.

9. **Inspecionar Logs e Tratamento de Erros**
   - Revisar logs gerados durante testes e uso manual, procurando exceções ou mensagens inesperadas.

10. **Comparar Implementação com a Documentação**
    - Verificar se todas as funcionalidades descritas em `docs/DOCUMENTACAO_DO_SISTEMA.md` estão implementadas ou sinalizadas como futuras.
    - Atualizar a documentação caso algo esteja divergente.

