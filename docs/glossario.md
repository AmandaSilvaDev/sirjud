# Glossário (domínio → código)

Interface em português; código, modelos e tabelas em inglês.

| Termo na interface | No código | Observação |
|---|---|---|
| Cooperativa (singular) | `Cooperative` | o tenant; todo dado de negócio tem `cooperative_id` |
| Central / sistema cooperativo | `CooperativeNetwork` | Sicoob, Sicredi, Unicred… (Fase 1) |
| Agência | `Branch` | |
| Escritório parceiro | `LawFirm` | global; atende várias cooperativas |
| Vínculo cooperativa × escritório | `Engagement` | serviços, capacidade e SLA (Fase 1) |
| Vínculo do usuário | `Membership` | usuário × cooperativa ou escritório × perfil × escopo (Fase 1) |
| Cooperado / devedor / parte | `Debtor` | CPF/CNPJ cifrado + HMAC + mascarado |
| Avalista, fiador, garantidor | `ContractParty.role` | |
| Contrato | `Contract` | o crédito, vindo do core |
| Situação do contrato | `Contract.stage` | disponível, em cobrança, aguardando aceite… |
| Saldo devedor | `Contract.balance` | `Decimal`, nunca float |
| Produto | `Product` | crédito rural, capital de giro… |
| Garantia | `Collateral` | Fase 3 |
| Lote de encaminhamento | `ReferralBatch` | Fase 4 |
| Encaminhamento | `Referral` | Fase 4 |
| Kit de documentos / checklist | `ChecklistTemplate`, `ChecklistItem`, `Document` | Fase 4 |
| Pendência documental | `Pendency` | Fase 4 |
| Processo | `Lawsuit` | número CNJ validado (módulo 97) |
| Polo ativo / passivo | `Lawsuit.pole` | |
| Fase do processo | `Phase` | lista padronizada |
| Movimentação / andamento | `Movement` | DataJud ou manual |
| Comentário | `Comment` | |
| Solicitação | `Request` | pedido de informação, documento, aprovação |
| Prognóstico | `Prognosis` | versionado, revisão obrigatória |
| Cobrança extrajudicial | `CollectionCase` | Fase 6 |
| Sinalização de pagamento | `PaymentSignal` | Fase 6 |
| Baixa | `Contract.stage = settled / written_off` | |
| Valor recuperado | `RecoveryEntry` | base da taxa de recuperação (Fase 3) |
| BNDU (bem não de uso) | `BnduEntry`, `Asset` | fase futura |
| Acordo / parcela | `Agreement`, `Installment` | Fase 6 (básico) e M4 |
| Evento de auditoria | `AuditEvent` | imutável (Fase 2) |
