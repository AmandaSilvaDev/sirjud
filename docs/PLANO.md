# SIRJUD COOP — Plano técnico das fases 0 a 7

Versão 1 · 11/10/2026 · **aprovado em 11/10/2026, com todas as recomendações
(D-01 a D-37)**. Ainda dependem de informação sua: D-09 (prazos de prescrição),
D-10 (planilha de exemplo) e D-29 (domínio no Cloudflare). D-28: o backup entra
na Fase 2.

Base: `CLAUDE.md`, `docs/requisitos.md` e as 14 telas em `docs/telas/`.
Cada decisão que depende de regra de negócio está marcada com **(D-nn)** e
aparece na seção 6, sempre com uma recomendação. Se você concordar com todas,
basta responder "ok às recomendações".

---

## 1. Princípios que guiam o desenho

1. **Toda tabela de negócio tem `cooperative_id NOT NULL`**, inclusive as tabelas
   filhas (movimentação, comentário, documento…). Isso repete um dado que daria
   para obter por relação, mas simplifica o escopo: o filtro de tenant é sempre
   uma coluna da própria tabela, e nunca depende de um JOIN que alguém esqueça
   de fazer.
2. **O escritório vê um registro só se ele estiver atribuído a ele.** Não basta
   o escritório atender aquela cooperativa: o contrato, o processo ou a cobrança
   precisa ter `law_firm_id` igual ao dele. Por isso as tabelas que o escritório
   enxerga também levam `law_firm_id` (o responsável atual), e o histórico de
   atribuições fica em tabela própria.
3. **Escopo e permissão moram num lugar só** (`apps/core/scoping.py` e
   `apps/core/permissions.py`). As views só declaram `screen` e `action`.
4. **Redes de segurança automáticas nos testes:**
   - um teste percorre todas as URLs e falha se alguma view não declarar `screen`
     e `action` (exceto login, `/healthz` e arquivos estáticos);
   - um teste lê `apps/*/views*.py` e falha se encontrar `.objects.` fora dos
     métodos de escopo;
   - cada recurso tem testes de isolamento (cooperativa B e escritório Y → 404)
     e de permissão (perfil sem a ação → 403).
5. **Modelar já o que vem depois** (acordos, BNDU, passivo, API), mas criar as
   tabelas só na fase em que forem usadas. O que muda agora: nomes de campos e
   relações que não precisarão ser refeitos.

---

## 2. Modelo de dados (fases 0 a 7)

Legenda da coluna **Escopo**:
- **C** = tem `cooperative_id`, filtrado pela cooperativa do usuário (e pela
  agência, quando o vínculo do usuário for limitado por agência);
- **C+E** = além disso, tem `law_firm_id` e o escritório só vê o que for dele;
- **Global** = tabela de referência da plataforma, sem dado de cliente;
- **Sistema** = tabela técnica.

Campos comuns omitidos nas tabelas abaixo: `id`, `created_at`, `updated_at`,
`created_by`, `updated_by` (mixin `TimeStampedModel`). Dinheiro é sempre
`DecimalField(max_digits=14, decimal_places=2)`. Datas e horas são gravadas em
UTC e exibidas em America/Porto_Velho.

### 2.1 `tenants` — cooperativas, agências, escritórios (Fase 1)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `CooperativeNetwork` | nome (Sicoob, Sicredi, Unicred, Cresol, independente) | 1:N Cooperative | Global |
| `Cooperative` | razão social, nome curto, CNPJ, ativa, parâmetros (`stalled_days`, `collection_days_default`, `prognosis_review_days`…) | network | — (é o próprio tenant) |
| `Branch` (agência) | código, nome, município, UF | cooperative | C |
| `LawFirm` | razão social, CNPJ, registro OAB da sociedade, serviços (ajuizamento, cobrança, passivo), comarcas atendidas (M2M `District`) | — | Global* |
| `Engagement` (vínculo cooperativa × escritório) | serviços contratados, capacidade (nº de contratos), SLA: aceite, ajuizamento e resposta (em dias), status (convidado, ativo, suspenso, encerrado), início e fim | cooperative, law_firm | C+E |
| `Court` (tribunal) | código J.TR (ex.: 8.22), sigla (TJRO), alias do DataJud (`api_publica_tjro`) | 1:N District | Global |
| `District` (comarca) | nome, UF | court | Global |
| `Holiday` | data, nome, abrangência (nacional, estadual, municipal), UF, município | — | Global |

\* O escritório é global porque atende várias cooperativas. A cooperativa só
"enxerga" um escritório se houver um `Engagement` entre os dois. Os dados de
negócio do escritório ficam sempre nas tabelas C+E.

### 2.2 `accounts` — usuários e vínculos (Fase 1)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `User` | e-mail (login, único), nome, telefone, nº OAB (para advogados), `is_active`, `is_staff` (só o admin da plataforma) | 1:N Membership | Sistema |
| `Membership` | perfil (ver 3.1), setor (recuperação, jurídico ou BNDU; só para operadores), agências (M2M `Branch`; vazio = todas), ativo, válido até, convidado por | user; **cooperative OU law_firm** (constraint: exatamente um preenchido) | C ou E |
| `Invitation` | e-mail, perfil e escopo propostos, hash do token, expira em, aceito em | cooperative ou law_firm, invited_by | C ou E |
| tabelas do allauth/axes | `EmailAddress`, `Authenticator` (TOTP e códigos de recuperação), `AccessAttempt`, `AccessLog` | user | Sistema |

Uma pessoa pode ter mais de um vínculo (por exemplo, advogada de dois escritórios).
O vínculo ativo fica na sessão e é ele que define o escopo de cada requisição.
Na interface, só aparece um seletor de vínculo quando a pessoa tem mais de um.

### 2.3 `audit` — auditoria imutável (Fase 2)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `AuditEvent` | `occurred_at`, usuário (FK sem cascata, `DO_NOTHING`) + cópia do e-mail e do perfil no momento, membership_id, ação (`login`, `login_failed`, `logout`, `view`, `list`, `create`, `update`, `delete`, `download`, `export`, `approve`, `reject`, `permission_change`, `ai_query`), tipo e id do objeto, descrição do objeto, `changes` JSON `{campo: [antes, depois]}`, `extra` JSON (filtros, quantidade de registros), IP, user-agent, navegador resumido, país (do Cloudflare), request_id, `prev_hash` e `hash` (encadeamento) | cooperative_id e law_firm_id **nullable** (eventos da plataforma não têm tenant) | C (leitura) |
| `SecurityAlert` | tipo (logins falhos, download em massa, login de outro país, mudança de permissão, consulta em massa), detalhes JSON, severidade, reconhecido por e em | user, cooperative (nullable) | C |

Para a imutabilidade:
- um trigger `BEFORE UPDATE OR DELETE` e um trigger `BEFORE TRUNCATE` levantam
  exceção;
- o usuário de banco da aplicação **não é dono** da tabela e tem só
  `INSERT, SELECT`. Assim ele também não consegue desligar o trigger (D-27);
- o hash encadeado (`hash = sha256(prev_hash + conteúdo)`) permite provar que
  ninguém apagou ou editou eventos nem por fora da aplicação. Um comando
  `verify_audit_chain` confere a cadeia.

Usuários nunca são apagados, só desativados, para não quebrar a FK.

### 2.4 `documents` — arquivos no R2 (Fase 3 para importações, Fase 4 para kits)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `Document` | tipo (item do checklist, comprovante, relatório, planilha de importação), chave no R2 (UUID aleatório, nunca o nome original), nome original, tamanho, MIME verificado pelo conteúdo, SHA-256, versão, enviado por e em | `supersedes` (FK para a versão anterior), alvo: referral / lawsuit / payment_signal / import_batch (FKs explícitas nullable, constraint: exatamente um) | C+E |

Não há exclusão de documento: corrigir um arquivo é subir uma nova versão
(SEG-33).

### 2.5 `portfolio` — carteira (Fase 3)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `Debtor` (pessoa/parte) | tipo (PF/PJ), nome, `document_encrypted` (AES-256-GCM), `document_hmac` (HMAC-SHA256 dos dígitos; único por cooperativa), `document_masked` (`***.456.789-**`, para listas), endereços (JSON), telefones e e-mails | cooperative | C |
| `Product` | código, nome (crédito rural, capital de giro, consignado, cartão…) | cooperative | C |
| `Contract` | número (único por cooperativa), id no core, produto, agência, valor original, saldo devedor, data do saldo, vencimento da parcela inadimplente mais antiga, dias de atraso, data de assinatura, **situação** (ver abaixo), escritório responsável atual (`law_firm_id`, nullable), `last_activity_at` | cooperative, branch, product, debtor principal, import_batch | C+E |
| `ContractParty` | papel (devedor, avalista, fiador, garantidor, cônjuge) | contract, debtor | C |
| `Collateral` (garantia) | tipo (alienação fiduciária, hipoteca, penhor, cessão de recebíveis…), descrição, matrícula ou placa, valor de avaliação, data | contract; mais tarde, FK para `Asset` (bem/BNDU) | C |
| `ImportBatch` | arquivo (Document), status (pré-visualização, aplicado, com erro, cancelado), totais (linhas, novos, atualizados, com erro), erros (JSON, linha a linha), mapeamento de colunas | cooperative | C |
| `RecoveryEntry` (valor recuperado) | data, valor, origem (pagamento sinalizado, parcela de acordo, leilão, venda de BNDU, core) | contract, objeto de origem | C+E |
| `Assignment` (histórico de atribuição) | tipo (cobrança, ajuizamento, passivo), início, fim, motivo do fim (concluído, transferido, devolvido) | contract ou lawsuit, law_firm | C+E |

**Situação do contrato** (`Contract.stage`), que alimenta a coluna "Fase" da
Carteira e o painel "Carteira por fase":
`disponível` → `em cobrança extrajudicial` → `aguardando aceite` →
`com pendência documental` → `aguardando ajuizamento` → `judicial` (nesse caso,
a tela mostra a fase do processo) → `baixado – pago` / `baixado – perda` /
`devolvido à cooperativa`. Os serviços de cada fase atualizam esse campo; nada
é calculado na hora da listagem. Quando o contrato tem mais de um processo,
vale a regra da D-07.

`RecoveryEntry` é o livro-caixa do recuperado. A taxa de recuperação, o
"recuperado no mês" e o "previsto × realizado" saem daqui, e acordos, leilões e
BNDU só acrescentam novas origens.

### 2.6 `referrals` — encaminhamento (Fase 4)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `ActionType` | código (execução, monitória, busca e apreensão, cobrança), nome, prazo de prescrição em anos (D-09) | — | Global |
| `ChecklistTemplate` | ativo, versão | cooperative, action_type | C |
| `ChecklistItem` | nome, descrição, obrigatório, obrigatório acima de valor (ex.: pesquisa de bens acima de R$ 20 mil), aceita documento do cadastro do escritório (ex.: procuração), ordem | template | C |
| `ReferralBatch` (lote) | código (`2026-42`), setor, status (rascunho, enviado, concluído), enviado em, prazo de aceite, prazo de ajuizamento (cópia do `Engagement` na hora do envio) | cooperative, law_firm, engagement | C+E |
| `Referral` (contrato no lote) | tipo de ação, status (rascunho, enviado, aceito, recusado, devolvido com pendência, reenviado, ajuizado, cancelado, transferido), prazo de aceite, respondido por e em, motivo da recusa, prazo para ajuizar, data de prescrição | batch, contract, law_firm | C+E |
| `ReferralEvent` (protocolo, RF-04) | de/para status, por quem, quando, documentos com hash naquele momento (JSON), observação | referral | C+E |
| `Pendency` (pendência documental, RF-06) | itens do checklist pendentes, descrição, aberta por (escritório), prazo, escalonada em, resolvida em e por | referral | C+E |
| `PowerOfAttorney` (procuração, RF-137) | validade, documento, outorgados | cooperative, law_firm | C+E |

O "escritório sugerido" é um cálculo, não um campo gravado: atende a comarca do
devedor + capacidade livre + SLA dos últimos 90 dias (D-35).

### 2.7 `lawsuits` — processo e linha do tempo (Fase 5)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `Phase` | código, nome, ordem, polo (ativo/passivo), terminal (sim/não) | — | Global (D-06) |
| `Lawsuit` | número CNJ (validado, único por cooperativa), polo (**ativo/passivo** desde já), classe, assunto, vara, valor da causa, data de ajuizamento, fase atual, fase sugerida pelo tribunal, fase confirmada por e em, status (ativo, suspenso, arquivado, encerrado), motivo do encerramento, segredo de justiça, `last_movement_at`, `last_comment_at`, `last_capture_at`, `last_capture_status`, `capture_failures` | cooperative, court, district, law_firm (nullable: passivo ainda não distribuído), advogado responsável (Membership), contratos (N:N via `LawsuitContract`) | C+E |
| `LawsuitContract` | — | lawsuit, contract | C |
| `PhaseChange` | fase de/para, origem (advogado, sugestão do tribunal, cooperativa), por quem, quando | lawsuit | C+E |
| `Movement` | data, código TPU do CNJ, nome, complementos (JSON), origem (DataJud, manual), hash para evitar duplicata (único por processo), capturado em | lawsuit | C+E |
| `MovementPhaseRule` | código TPU → fase sugerida; exige comentário do advogado (RF-23) | phase | Global |
| `Comment` | texto, lado (cooperativa/escritório), menções (M2M User), evento-chave | lawsuit, author | C+E |
| `Request` (solicitação, RF-21) | tipo (pedido de informação, pedido de documento, aprovação, comentário obrigatório, outro), título, texto, de qual lado para qual lado, destinatário (usuário, nullable), prazo, status (aberta, respondida, aprovada, recusada, cancelada), resposta, respondida por e em | lawsuit | C+E |
| `Prognosis` | probabilidade de recebimento (0–100), valor esperado, mês esperado, observação, revisar até, vigente (só a última) | lawsuit, author | C+E |
| `CaptureRun` | início, fim, total, sucesso, erro, ignorados | — | Sistema |
| `CaptureAttempt` | resultado, erro, tentativa nº, próxima tentativa em | run, lawsuit | C |

Ninguém altera um prognóstico: cada revisão grava uma linha nova. Para o polo
passivo (fase futura), a classificação de risco será uma tabela própria
(`PassiveRiskAssessment`), também versionada, ligada a `Lawsuit`.

### 2.8 `collections` — cobrança extrajudicial (Fase 6)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `CollectionCase` | entrou em, prazo, status (ativo, regularizado, devolvido, enviado para ajuizamento, encerrado), encerrado em, motivo | cooperative, contract, law_firm, engagement | C+E |
| `ContactAttempt` | canal (telefone, WhatsApp, e-mail, visita, carta), data e hora, resultado, observação | case, author | C+E |
| `PaymentPromise` | data prometida, valor, status (pendente, cumprida, quebrada) | case | C+E |
| `PaymentSignal` | tipo (quitação total, parcela de acordo, pagamento parcial), valor, data do pagamento, comprovante (Document), status (aguardando conferência, confirmado, contestado), conferência no core (confere / valor diverge / não encontrado), motivo da contestação, conferido por e em | case; `installment` (nullable, para acordos futuros) | C+E |

Acordo extrajudicial (RF-101): veja a D-16. Minha recomendação é criar já na
Fase 6 o app `agreements` com `Agreement` e `Installment` genéricos (servem para
acordo extrajudicial e judicial), sem a régua de alçadas, que entra no módulo M4.

### 2.9 `notifications` — alertas e resumo diário (Fase 4 em diante)

| Entidade | Campos principais | Relações | Escopo |
|---|---|---|---|
| `Notification` | tipo (prazo de aceite, pendência vencida, processo parado, prognóstico a revisar, menção, pagamento sinalizado…), título, link, lida em, incluída no resumo em | user, objeto | C+E |

A Fase 4 envia e-mail de prazo de aceite e de ajuizamento por evento. Na Fase 7,
tudo passa para o resumo diário (Resend grátis = 100 e-mails/dia).

### 2.10 Fases seguintes (só para orientar nomes e relações; nada é criado agora)

| App futuro | Entidades | Já preparado em |
|---|---|---|
| `agreements` (M4) | `Agreement` (valor, desconto, entrada, alçada exigida, aprovado por), `Installment`, `ApprovalRule` (alçada por valor, desconto e perfil) | `PaymentSignal.installment`, `RecoveryEntry.origem`, `Request` do tipo aprovação |
| `assets` (M5/BNDU) | `Asset` (bem: tipo, matrícula ou placa, avaliação, situação), `Auction`, `BnduEntry` (origem, valor de entrada, prazo regulatório), `BnduExtension`, `BnduCost` | `Collateral` → `Asset`, `RecoveryEntry` |
| `lawsuits` (M12) | `PassiveRiskAssessment` (risco, perda estimada, tese, revisão) | `Lawsuit.pole`, `law_firm` nullable |
| `api` (M13) | `ApiToken` (cooperativa, escopos, hash, expiração, último uso); endpoints `/v1/...` | `updated_at` indexado em todas as tabelas (carga incremental) |
| M7 ranking | sem tabela nova: consultas sobre `Engagement`, `Request`, `Referral` e `RecoveryEntry` | — |

---

## 3. Matriz de permissões

### 3.1 Perfis

| Código | Perfil | Vínculo | Escopo |
|---|---|---|---|
| GES | Gestor da cooperativa | cooperativa | toda a cooperativa |
| OP-R / OP-J / OP-B | Operador (recuperação / jurídico / BNDU) | cooperativa + setor | toda a cooperativa, ou só as agências do vínculo |
| CON | Consulta (ex.: gerente de agência) | cooperativa | só as agências do vínculo |
| AUD | Auditoria | cooperativa | toda a cooperativa + logs |
| E-CO | Coordenador do escritório | escritório | tudo o que estiver atribuído ao escritório, em todas as cooperativas atendidas |
| E-ADV | Advogado do escritório | escritório | ver D-04 |
| E-AP | Apoio do escritório | escritório | igual ao advogado, com menos ações |
| BI | Integração BI | token de API (fase futura) | cooperativa do token, só leitura |
| ADM | Administrador da plataforma | `is_staff`, sem vínculo | tabelas globais e cadastro de tenants; **nenhum dado de negócio** |

### 3.2 Ações

**C** consultar · **I** criar · **A** alterar · **E** excluir · além de duas
ações que proponho separar, porque são sensíveis e entram na auditoria e nos
alertas: **Ap** aprovar/confirmar e **X** exportar/baixar arquivo. "—" = sem
acesso (resposta 403, ou 404 quando o objeto é de outro escopo).

### 3.3 Matriz (telas das fases 0 a 7)

| Tela / recurso (fase) | GES | OP-R | OP-J | OP-B | CON | AUD | E-CO | E-ADV | E-AP |
|---|---|---|---|---|---|---|---|---|---|
| Login, MFA, minha conta (1) | todos | | | | | | | | |
| Usuários da cooperativa (1) | C I A E¹ | — | — | — | — | C | — | — | — |
| Equipe do escritório (1) | — | — | — | — | — | — | C I A E¹ | C | C |
| Escritórios parceiros: vínculo, capacidade, SLA (4) | C I A | C | C | C | C | C | — | — | — |
| Configurações: checklists, prazos, dias para "parado" (4) | C A | C | C | — | — | C | — | — | — |
| Auditoria: log (2) | C² | — | — | — | — | C X | — | — | — |
| Alertas de segurança (2) | C A³ | — | — | — | — | C A³ | — | — | — |
| Carteira (3) | C X | C X | C X | C | C | C X | — | — | — |
| Importar carteira (3) | C I | C I | — | — | — | C | — | — | — |
| Ver CPF/CNPJ completo (3) | C⁴ | C⁴ | C⁴ | — | — | — | C⁴ | C⁴ | — |
| Novo encaminhamento / lotes (4) | C I A E⁵ | C I A E⁵ | C | — | C | C | — | — | — |
| Encaminhamentos recebidos: aceitar, recusar, devolver (4) | — | — | — | — | — | — | C A | C | C |
| Pendência documental: responder (4) | C A | C A | C | — | — | C | C I | C I | C I |
| Documentos: enviar / baixar (4) | I X | I X | I X | X | — | X | I X | I X | I X |
| Processo e linha do tempo (5) | C | C | C | C | C | C | C | C | C |
| Registrar CNJ, fase e dados do processo (5) | — | — | A⁶ | — | — | — | I A | I A | — |
| Distribuir processo entre advogados (5) | — | — | — | — | — | — | A | — | — |
| Comentar (5) | I | I | I | I | — | — | I | I | I |
| Solicitações: abrir / responder (5) | I A | I A | I A | — | — | — | I A | I A | A |
| Aprovar solicitação de aprovação (5) | Ap | — | — | — | — | — | — | — | — |
| Prognóstico: registrar ou revisar (5) | C | C | C | — | C | C | I | I | — |
| Cobrança extrajudicial: tela da cooperativa (6) | C X | C I A | C | — | C | C X | — | — | — |
| Enviar carteira para cobrança, devolver, mandar para ajuizamento (6) | I A | I A | — | — | — | — | — | — | — |
| Confirmar baixa / contestar pagamento (6) | Ap | Ap | — | — | — | — | — | — | — |
| Contatos e promessas (6) | C | C | — | — | — | C | C I A | C I A | C I A |
| Sinalizar pagamento com comprovante (6) | — | — | — | — | — | — | I | I | I⁷ |
| Painel da cooperativa (7) | C | C | C | C | C⁸ | C | — | — | — |
| Fila de trabalho (7) | — | — | — | — | — | — | C A⁹ | C | C |
| Relatório mensal ao cliente em PDF (7) | — | — | — | — | — | — | C X | C X | — |
| Telas futuras: Acordos, BNDU, Passivo, Ranking, API | escondidas do menu até a fase correspondente | | | | | | | | |

Notas:
1. "Excluir" usuário = desativar e revogar a sessão. Ninguém apaga usuário.
2. Gestor vê o log da própria cooperativa sem os eventos de outros gestores? Ver D-20.
3. "Alterar" um alerta = marcar como tratado, com justificativa.
4. Na tela de detalhe, por clique em "mostrar", e cada clique é registrado. Em
   listas e painéis o CPF aparece sempre mascarado (D-25).
5. Excluir só lote em rascunho. Depois do envio, só cancelar, com motivo.
6. O jurídico da cooperativa corrige dados cadastrais (vara, valor da causa). A
   fase é do advogado (RF-12).
7. Se você preferir que o apoio só registre contatos, tiro esse I (D-17).
8. Com os números limitados às agências do vínculo.
9. "Alterar" = redistribuir tarefas e processos entre os advogados (RF-91).

**ADM** tem o Django Admin num caminho não óbvio, com novo MFA a cada sessão
administrativa (SEG-13). Lá ele vê só: cooperativas, agências, escritórios,
tribunais, comarcas, feriados, fases, tipos de ação, regras TPU→fase e o
cadastro do primeiro gestor de cada cooperativa e do primeiro coordenador de
cada escritório. Os modelos de negócio **não são registrados** no admin, e os
managers com escopo devolvem vazio para quem não tem vínculo.

### 3.4 Como isso vira código

```text
apps/core/permissions.py
  MATRIX = {Role.COOP_MANAGER: {Screen.PORTFOLIO: {"view", "export"}, ...}, ...}
  SECTOR_SCREENS = {Sector.BNDU: {...}}       # limita as telas do operador por setor

apps/core/scoping.py
  class ScopedQuerySet(QuerySet):
      def visible_to(self, membership): ...   # sem vínculo → .none()

apps/core/views.py
  class ScopedViewMixin:                      # toda view de negócio herda
      screen = None; action = None            # obrigatório; teste garante
      def get_queryset(self): return self.model.objects.visible_to(self.request.membership)
      # get_object() parte desse queryset → objeto de outro escopo = 404
```

A matriz fica no código, versionada e testada. Ajustes por usuário (como
"aprovar acordos até 10%", que aparece na tela de auditoria) entram junto com o
M4. Uma segunda camada de defesa com Row Level Security no PostgreSQL fica como
opção para antes da segunda cooperativa.

---

## 4. Estrutura de pastas e apps

```text
sirjud/
├── CLAUDE.md
├── pyproject.toml · uv.lock · .python-version (3.12)
├── manage.py
├── Dockerfile                    # multi-stage: tailwind → deps (uv) → runtime
├── docker-compose.yml            # só o Postgres 16 local, para desenvolvimento
├── .env.example                  # nomes das variáveis, sem valores
├── railway/                      # config-as-code de cada serviço
│   ├── web.toml
│   ├── cron-capture.toml
│   ├── cron-daily.toml
│   └── cron-digest.toml
├── .github/workflows/ci.yml      # ruff, pytest, bandit, pip-audit, gitleaks, check --deploy
├── config/
│   ├── settings/  base.py · dev.py · test.py · prod.py   # staging = prod com outras variáveis
│   ├── urls.py · wsgi.py
├── apps/
│   ├── core/          # TimeStampedModel, escopo, permissões, CNJ, dinheiro, criptografia,
│   │                  # dias úteis, /healthz, middleware de sessão de 8 h, comando seed_demo
│   ├── accounts/      # User, Membership, Invitation, MFA obrigatório, login
│   ├── tenants/       # Cooperative, Branch, LawFirm, Engagement, Court, District, Holiday
│   ├── audit/         # AuditEvent, SecurityAlert, middleware, signals, trigger
│   ├── documents/     # Document, upload para o R2 com SHA-256, download com link temporário   (novo, D-33)
│   ├── portfolio/     # Debtor, Contract, Collateral, ImportBatch, RecoveryEntry, Assignment
│   ├── referrals/     # ActionType, Checklist*, ReferralBatch, Referral, Pendency
│   ├── lawsuits/      # Lawsuit, Movement, Comment, Request, Prognosis, capture_movements
│   ├── collections/   # CollectionCase, ContactAttempt, PaymentPromise, PaymentSignal
│   ├── agreements/    # (Fase 6, se a D-16 for aprovada)
│   ├── notifications/ # Notification, alertas de prazo, send_daily_digest                       (novo, D-33)
│   ├── dashboards/    # painel da cooperativa, portal e fila do escritório, PDF mensal
│   └── api/           # (fase futura) DRF + drf-spectacular
├── templates/
│   ├── base.html · base_portal.html · components/ (botões, tabelas, badges, paginação)
│   └── <app>/...
├── static/
│   ├── src/input.css             # tokens da marca extraídos das telas
│   ├── vendor/htmx.min.js · alpine-csp.min.js   # versões fixas, servidas pelo próprio app
│   ├── fonts/                    # Montagu Slab e Lato hospedadas localmente (D-32)
│   └── img/logo.png · logo-branco.png
├── tests/                        # testes que cruzam apps: matriz de permissão, URLs sem proteção,
│                                 # isolamento entre tenants; os demais ficam em apps/<app>/tests/
└── docs/
    ├── requisitos.md · telas/ · PLANO.md · PROGRESSO.md · glossario.md
    └── railway.md                # passo a passo do Railway, inclusive desligar o acesso público ao banco
```

Sobre o nome `collections`: ele colide com o módulo `collections` da biblioteca
padrão do Python. Como todos os apps ficam no pacote `apps/`, o caminho de
importação é `apps.collections` e não há conflito, por isso mantive o nome do
`CLAUDE.md`.

Front-end: o Alpine.js usa a **build CSP** (`@alpinejs/csp`), porque a build
padrão usa `eval` e exigiria `unsafe-eval` na CSP. O HTMX roda com
`allowEval=false` e sem os estilos inline do indicador. A CSP fica
`default-src 'self'`, sem CDN.

---

## 5. Railway: serviços e variáveis

### 5.1 Ambientes

| Ambiente | Origem do deploy | Dados | Observação |
|---|---|---|---|
| `production` | branch `main`, com "Wait for CI" ligado | reais (só depois do aceite da cooperativa) | sem sleep |
| `staging` | base dos **PR Environments** do Railway: cada PR abre um ambiente temporário, que some ao fechar o PR | só `seed_demo` | serverless (dorme após 5 min) para gastar pouco |

O critério "PR aprovado sobe no staging" fica atendido porque o PR ganha um
ambiente próprio, com URL, antes do merge (D-30). O ambiente `staging`
permanente acompanha a `main` com dados falsos, como vitrine.

### 5.2 Serviços em cada ambiente

| Serviço | Imagem / comando | Agenda (UTC) | Fase |
|---|---|---|---|
| `web` | Dockerfile · pre-deploy: `python manage.py migrate --noinput` (+ `seed_demo --if-empty` só no staging) · start: `gunicorn config.wsgi -b 0.0.0.0:$PORT -w 2 --threads 4` · healthcheck `/healthz` · 0,5 vCPU / 1 GB | — | 0 |
| `Postgres` | PostgreSQL 16 do Railway, **sem TCP Proxy público** | — | 0 |
| `cron-daily` | mesma imagem · `python manage.py run_daily_jobs` (prazos de aceite e ajuizamento, pendências vencidas, processos parados, prognósticos a revisar, `clearsessions`) | `30 10 * * *` (06:30 em Porto Velho) | 4 |
| `cron-capture` | `python manage.py capture_movements` | `0 10 * * *` (06:00 em Porto Velho) | 5 |
| `cron-digest` | `python manage.py send_daily_digest` | `0 11 * * 1-5` (07:00, dias úteis) | 7 |
| `cron-backup` (proposta) | `pg_dump` criptografado para um bucket R2 separado, fora do Railway | `0 7 * * *` | 0 ou 2 (D-28) |

Os serviços Cron do Railway sobem o container, rodam o comando e encerram, então
só cobram enquanto rodam. Os alertas de segurança (logins falhos, download em
massa, país diferente) não precisam de cron: disparam na própria requisição.

O `/healthz` faz `SELECT 1` e responde 200 ou 503. Ele fica fora do
redirecionamento para HTTPS (`SECURE_REDIRECT_EXEMPT`), e o host do healthcheck
do Railway entra em `ALLOWED_HOSTS`.

**Desligar o acesso público ao banco** (vai para `docs/railway.md` na Fase 0):
Postgres → Settings → Networking → remover o *TCP Proxy* (domínio público).
Depois, conferir que o `DATABASE_URL` do `web` aponta para
`postgres.railway.internal`, que o Railway fornece pela variável
`${{Postgres.DATABASE_URL}}`. Quando for preciso acessar o banco manualmente,
religar o proxy temporariamente e desligar de novo; o evento fica registrado no
log do projeto no Railway.

### 5.3 Variáveis de ambiente

| Variável | Para quê | Fase | Staging × produção |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | 0 | igual |
| `DJANGO_ENV` | `staging` / `production` (liga `seed_demo` e bloqueia comandos perigosos em produção) | 0 | diferente |
| `DJANGO_SECRET_KEY` | chave do Django | 0 | **diferente** |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` | domínios e links nos e-mails | 0 | diferente |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (rede privada) | 0 | referência |
| `DATABASE_OWNER_URL` | papel dono das tabelas, usado só no pre-deploy `migrate`; o app roda com papel limitado | 2 | referência |
| `WEB_CONCURRENCY` | workers do gunicorn | 0 | igual |
| `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL` | convites, troca de senha, desbloqueio | 1 | staging pode usar o backend de console |
| `SECURITY_ALERT_EMAILS` | quem recebe os alertas de segurança | 2 | diferente |
| `TRUST_CLOUDFLARE_HEADERS` | usar `CF-Connecting-IP` e `CF-IPCountry` (só se o Cloudflare estiver na frente) | 2 | — |
| `FIELD_ENCRYPTION_KEYS` | chaves AES-256 (lista com id, para rotação) | 3 | **diferente** |
| `SEARCH_HMAC_KEY` | chave do HMAC de CPF/CNPJ | 3 | **diferente** |
| `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` | Cloudflare R2 (um bucket por ambiente, privado) | 3 | **diferente** |
| `DATAJUD_API_KEY`, `DATAJUD_BASE_URL` | API Pública do DataJud | 5 | igual (staging usa números CNJ de teste) |
| `BACKUP_*` | bucket e chave de criptografia do backup | D-28 | só produção |

`PORT` vem do Railway. Nenhum valor real vai para o repositório; o
`.env.example` traz só os nomes.

---

## 6. Dúvidas de regra de negócio (com recomendação)

### Acesso e usuários

- **D-01 · Login em uma ou duas etapas.** A tela `Login.dc.html` mostra e-mail,
  senha e código MFA no mesmo formulário. O allauth faz em duas etapas: senha e,
  na tela seguinte, o código. Fazer em uma etapa exige reescrever parte do
  allauth e informa se a senha está certa só depois do código.
  **Recomendo duas etapas**, com o visual idêntico ao da tela (o segundo passo
  mostra só o campo do código).
- **D-02 · Botão "Entrar com Microsoft (Entra ID)".** O SEG-05 é da fase de
  produção. **Recomendo esconder o botão no piloto**, assim como qualquer outro
  botão de recurso ainda inexistente ("Importar andamentos (planilha)", itens do
  menu de fases futuras). Botão que não funciona confunde o usuário.
- **D-03 · Quem cria quem.** **Recomendo:** o ADM cadastra a cooperativa, o
  escritório, o primeiro gestor e o primeiro coordenador; o gestor convida os
  usuários da cooperativa e liga os escritórios (Engagement); o coordenador
  convida a própria equipe. Não há cadastro público. O convite expira em 72 h e
  o primeiro acesso já obriga a configurar o MFA.
- **D-04 · O que o advogado vê.** Toda a carteira do escritório ou só os
  processos em que é responsável? **Recomendo:** vê toda a carteira do escritório
  (lendo), mas a fila de trabalho mostra só o que é dele; o apoio, idem. Assim um
  advogado cobre o colega de férias sem precisar de redistribuição.
- **D-05 · Transferência de carteira (RF-64).** O escritório antigo continua
  vendo o histórico do que saiu dele? **Recomendo que não**: perde o acesso no
  dia da transferência. O histórico fica preservado para a cooperativa e para o
  novo escritório.

### Carteira, fases e prazos

- **D-06 · Lista de fases.** Proponho uma lista global da plataforma, extraída
  das telas: *aguardando citação, citado, penhora/constrição, leilão, acordo em
  andamento, suspenso/sem bens, sentenciado, arquivado, encerrado*. Rótulos por
  cooperativa ficam para depois. Confirma a lista? Falta alguma fase (por
  exemplo, "embargos" ou "recurso")?
- **D-07 · Contrato com mais de um processo.** Qual fase aparece na Carteira?
  **Recomendo a fase do processo mais avançado** que não esteja encerrado.
- **D-08 · Dias úteis ou corridos.** A tela fala em "2 dias úteis" para o aceite
  e em "15 dias" para ajuizar. **Recomendo:** prazos de aceite, pendência e
  resposta em dias úteis (feriados nacionais, estaduais de RO e municipais
  cadastrados pelo ADM); prazo de ajuizamento e de cobrança em dias corridos.
  Confirma?
- **D-09 · Alerta de prescrição (RF-07).** O prazo depende do título (cédula de
  crédito: 3 anos para executar; monitória: 5 anos). **Recomendo** um prazo em
  anos por tipo de ação, contado do vencimento, com alertas a 180, 90 e 30 dias.
  Quem me passa os prazos certos: o jurídico da cooperativa?
- **D-10 · Formato da importação.** Ainda não sabemos o core da cooperativa
  piloto. **Recomendo** um modelo de planilha nosso (CSV ou XLSX), com uma
  coluna por campo do `Contract`, do `Debtor` e dos avalistas, e mapeamento de
  colunas na tela de pré-visualização. Você consegue uma planilha real (pode ser
  com os dados trocados) da cooperativa piloto?
- **D-11 · Reimportação.** Reimportar um contrato que já existe atualiza saldo,
  atraso e garantias, mas não mexe na situação nem no escritório? **Recomendo
  que sim.** Um contrato que sumiu da planilha não é apagado; ele fica marcado
  para conferência.

### Encaminhamento

- **D-12 · Quem configura o checklist.** **Recomendo o gestor** (por tipo de
  ação), partindo de um modelo padrão que a plataforma fornece.
- **D-13 · Quem do escritório aceita o encaminhamento.** **Recomendo só o
  coordenador** no piloto.
- **D-14 · Pendência documental (RF-06).** Qual o prazo da cooperativa para
  resolver, e para quem escala? **Recomendo:** 3 dias úteis para o operador; se
  vencer, avisa o gestor (e o item aparece no painel "Precisa de atenção").
- **D-15 · Recusa.** Um contrato recusado volta para "disponível" e pode ser
  encaminhado a outro escritório? **Recomendo que sim**, com o motivo da recusa
  visível no novo encaminhamento.

### Cobrança extrajudicial

- **D-16 · Acordo extrajudicial na Fase 6.** O RF-101 pede registro de acordos
  extrajudiciais (a tela mostra "Parcela 2/6"). **Recomendo** criar já o app
  `agreements` com acordo e parcelas, em que o acordo do escritório fica
  "proposto" até um gestor aprovar (alçada única). As faixas de alçada entram no
  M4. Ou você prefere, no piloto, só registrar o acordo como texto no
  `ContactAttempt`?
- **D-17 · Quem sinaliza pagamento.** Coordenador e advogado sinalizam. O apoio
  também? **Recomendo que sim**, porque o comprovante é obrigatório e a
  recuperação confere antes da baixa.
- **D-18 · Efeito da baixa.** Confirmar uma **quitação total** muda o contrato
  para "baixado – pago" e encerra a cobrança; **pagamento parcial e parcela**
  só lançam o valor em `RecoveryEntry` (o saldo continua vindo do core na próxima
  importação). E a contestação volta como pendência para o escritório, com prazo
  de 3 dias úteis. Confirma?
- **D-19 · Prazo padrão em cobrança.** A tela destaca "mais de 90 dias sem
  solução = candidato a ajuizamento". **Recomendo** 90 dias como padrão por
  cooperativa, ajustável no `Engagement`. Ao vencer, o contrato só aparece como
  candidato; a decisão de ajuizar é sempre do operador.

### Auditoria e segurança

- **D-20 · Quem vê o log.** **Recomendo:** a Auditoria vê e exporta tudo da
  cooperativa, inclusive as ações dos escritórios nos dados dela; o gestor vê o
  log, mas não exporta; o ADM vê só os eventos de segurança (logins, bloqueios,
  mudanças de permissão), sem o antes/depois dos dados de negócio.
- **D-21 · Download em massa.** A tela mostra "214 documentos em 6 min · conta
  suspensa". **Recomendo:** mais de 50 downloads em 10 minutos gera alerta **e
  suspende** a conta até a Auditoria ou o gestor reativar. Confirma o limite e a
  suspensão automática?
- **D-22 · Login de outro país.** A tela mostra só um aviso ("Portugal · MFA
  confirmado"). **Recomendo** apenas alertar, sem bloquear. Isso depende de o
  Cloudflare estar na frente (D-29), porque o país vem do cabeçalho
  `CF-IPCountry`; assim não preciso de base de GeoIP nem de dependência nova.
- **D-23 · Consulta em massa.** O requisito fala em "usuário consultando
  milhares de registros". **Recomendo** registrar cada listagem com a quantidade
  de linhas retornadas e cada exportação, e alertar quando alguém exportar mais
  de 500 linhas em uma hora.
- **D-24 · Senha vazada (SEG-02).** A checagem de senha vazada usa a API do
  Have I Been Pwned por k-anonimato (só os 5 primeiros caracteres do hash saem do
  servidor). **Posso usar?** A alternativa é só a lista de senhas comuns do
  Django.
- **D-25 · Quem vê o CPF completo.** **Recomendo:** gestor, operadores de
  recuperação e jurídico e o escritório responsável (que precisa dele para
  ajuizar) veem o CPF completo no detalhe, clicando em "mostrar", e cada clique
  é registrado. Consulta, Auditoria e todas as listas veem o CPF mascarado.
- **D-26 · Retenção.** No piloto, nada é apagado (log, documentos, contratos
  baixados). A política de retenção e descarte da LGPD entra antes da produção.
  Confirma?

### Infraestrutura e dependências

- **D-27 · Dois papéis no banco.** Para cumprir o SEG-22 e tornar a auditoria
  realmente imutável, proponho que o app rode com um papel sem superusuário e
  sem ser dono das tabelas; só o `migrate` usa o papel dono. Isso exige criar o
  papel uma vez pelo console do Railway (eu documento os comandos). Posso fazer
  assim a partir da Fase 2?
- **D-28 · Backup fora do Railway.** O requisito pede dump diário fora do
  provedor. **Recomendo** o `cron-backup` com `pg_dump` criptografado num bucket
  R2 separado (o R2 é grátis até 10 GB). Entra na Fase 0 ou na Fase 2?
- **D-29 · Cloudflare e domínio.** O SEG-41/42 coloca o Cloudflare na frente do
  Railway. Você já tem um domínio (por exemplo, `sirjudcoop.com.br`) no
  Cloudflare? Sem ele, o staging e o piloto rodam no `*.up.railway.app` e o
  alerta de país (D-22) fica desligado.
- **D-30 · PR Environments.** Ligar os PR Environments do Railway (um ambiente
  temporário por PR, com banco próprio que some ao fechar o PR) custa um pouco
  mais do que um staging fixo. **Recomendo ligar.** A alternativa é um staging
  fixo que segue uma branch `staging`, para onde eu faço merge do PR antes de
  você aprovar.
- **D-31 · Dependências fora da lista do `CLAUDE.md`.** Preciso da sua
  autorização para:

  | Pacote | Por quê |
  |---|---|
  | `django-environ` | já citado no prompt (settings por ambiente) |
  | `psycopg[binary]` | driver do PostgreSQL (indispensável) |
  | `argon2-cffi` | hash Argon2 exigido pelo `CLAUDE.md` |
  | `cryptography` | AES-256-GCM e HMAC dos campos sensíveis (já entra indiretamente pelo `allauth[mfa]`) |
  | `boto3` | exigido pelo `django-storages` para o R2 |
  | `httpx` **ou** só `urllib` da biblioteca padrão | chamadas ao DataJud e ao HIBP; recomendo `urllib`, sem dependência nova |
  | `pytest-cov` (só desenvolvimento) | cobertura no CI |

  Sem `python-magic` (o tipo do arquivo é conferido pelos primeiros bytes) e sem
  GeoIP (vem do Cloudflare).
- **D-32 · Fontes locais.** **Recomendo** servir Montagu Slab e Lato a partir do
  próprio app, e não do Google Fonts: evita mandar o IP do usuário ao Google
  (LGPD) e mantém a CSP fechada. As duas fontes têm licença OFL.
- **D-33 · Dois apps a mais.** `documents` (arquivos usados por encaminhamento,
  processo, cobrança e importação) e `notifications` (alertas e resumo diário)
  não estão na lista do `CLAUDE.md`. Posso criá-los? Se aprovar, atualizo a lista
  no `CLAUDE.md`.

### Painel e previsão

- **D-34 · Previsão de recebimento.** A tela diz "baseada no prognóstico". Somo o
  **valor esperado × probabilidade** no mês esperado, ou o valor esperado cheio?
  **Recomendo ponderar pela probabilidade** e mostrar o valor cheio no detalhe.
  Acordos e leilões entram quando os módulos existirem.
- **D-35 · Escritório sugerido.** **Recomendo**, nesta ordem: atende a comarca
  do contrato → tem capacidade livre → melhor SLA nos últimos 90 dias. O operador
  sempre pode escolher outro.
- **D-36 · "Processo parado".** O painel usa 60 dias, o portal 30 dias sem
  comentário e a cobrança 90 dias. **Recomendo** três parâmetros por cooperativa,
  com esses padrões. Confirma?
- **D-37 · Revisão do prognóstico e comentário obrigatório.** **Recomendo**
  revisão obrigatória a cada 90 dias e também após sentença, penhora, leilão ou
  acordo (quando a captura identifica o evento, abre uma solicitação para o
  advogado, com prazo de 5 dias úteis). Isso também cobre o RF-23 (comentário
  obrigatório em eventos-chave). Entra na Fase 5?

---

## 7. Observações sobre o repositório

- Os documentos estavam em `sirjud-coop-kit/sirjud-coop-kit/docs/`. Copiei
  `requisitos.md` e `telas/` para `docs/`, como o prompt pede; o kit original
  ficou intacto e pode ser apagado quando você quiser.
- O `git status` mostra o `README.md` apagado na sua cópia de trabalho. Não
  mexi nele.
- Nesta máquina não há `python` nem `uv` no PATH (só o lançador `py`). Na Fase 0,
  vou precisar do `uv` instalado (`winget install astral-sh.uv`). O Docker
  Desktop já está instalado e será usado para o Postgres local.
- Os documentos citados no `CLAUDE.md` que ainda não existem (`docs/glossario.md`,
  `docs/PROGRESSO.md`, `docs/railway.md`) são criados na Fase 0.

---

## 8. Sequência depois da aprovação

Uma branch e um PR por fase (`fase-0-fundacao`, `fase-1-acesso`, …). Ao fim de
cada fase: testes verdes, `docs/PROGRESSO.md` atualizado, PR aberto explicando
permissões, consultas e uploads. Sem merge, e eu paro para sua validação.
