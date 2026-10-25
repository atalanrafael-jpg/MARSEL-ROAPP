# MARSEL ROAPP — ЕДИНАЯ СИСТЕМА

Дата контрольной ревизии: 2026-09-18

MARSEL и ROAPP — единая система Ювелирной студии MARSEL, а не независимые проекты.

- MARSEL — бизнес-контур: клиенты, заказы, изделия, ремонт, производство, склад, материалы, финансы, продажи и маркетинг.
- ROAPP — технологический контур той же системы: API, данные, интеграции, автоматизация, MCP и CI/CD.
- Каноническая система: **MARSEL ROAPP**.
- Канонический GitHub repository: `atalanrafael-jpg/MARSEL-ROAPP`.
- Техническая каноническая ветка: `main`.
- Ветка `main` является техническим источником истины для системы MARSEL ROAPP. `main-MARSEL-ROAPP` — историческая/legacy-ветка и не является канонической.
- Канонический live audit control plane: `.github/workflows/marsel-unified-control-plane.yml`.
- Исторические реализации находятся в архивном/историческом контуре и не являются текущим источником истины.

## Canonical control plane

`.github/workflows/marsel-unified-control-plane.yml` — единственный канонический live RO App audit workflow. Вспомогательные workflow разрешены только для явно отличающихся инженерных, security или gate-функций и не должны создавать второй live audit path.

Основная цепочка:

`API inventory → data quality → entity audit → product-code review → warehouse contract → safety gate → evidence`

Все live-аудиты RO App выполняются READ-ONLY. Идентификаторы не угадываются. Недостаточные или конфликтующие доказательства дают `REVIEW_REQUIRED`, а не `PASS`.

## Governed AI control plane

AI является надстройкой над доказательствами, а не источником истины.

`OBSERVE → VALIDATE → CLASSIFY → ASSESS_IMPACT → ASSESS_RISK → RECOMMEND → APPROVAL_GATE → ACTION → VERIFY → DOCUMENT`

Автоматизация:

`TRIGGER → VALIDATE → ACTION → LOG → VERIFY → ALERT`

Нормализованный exception engine использует контролируемые категории: `FACTUAL`, `DUPLICATE`, `MISSING_DATA`, `INVALID_RELATION`, `CLASSIFICATION`, `CONFIGURATION`, `API`, `SECURITY`, `INTEGRATION`, `PERFORMANCE`, `LEGAL_TAX`, `UNVERIFIED`.

Текущая AI/control-policy реализация находится в:

- `config/marsel_ai_control_policy.json`
- `scripts/marsel_exception_engine.py`
- `tests/test_exception_engine.py`
- `docs/MARSEL_AI_CONTROL_PLANE.md`

Текущий exception engine не вызывает внешние сервисы и не выполняет production WRITE.

## Canonical implementations

- `scripts/marsel_api_inventory_v20_32.py`
- `scripts/marsel_data_quality_v22_readonly.py`
- `scripts/marsel_entity_audit_v20_35.py`
- `scripts/marsel_product_code_collision_audit_v22_3.py`
- `scripts/marsel_warehouse_contract_v20_48.py`
- `scripts/marsel_api_v2_probe_v1.py`
- `scripts/marsel_api_v2_canonical_registry_v1.py`
- `scripts/marsel_canonical_self_check.py`

Внутренние зависимости API inventory `v20_31` и `v20_29` остаются активными до отдельного рефакторинга и повторной проверки; их нельзя удалять только из-за номера версии.

## Production safety

**Production WRITE остаётся запрещённым.** До рассмотрения controlled write должны существовать прямые доказательства:

`backup/export → restore integrity → schema reconciliation → full READ-ONLY inventory → duplicate/orphan/reference analysis → dry-run → idempotency → rollback → controlled write → post-write verification`

Наличие write-методов, успешного CI или документации не является доказательством выполнения production WRITE или готовности к нему.

## Current external gates

По текущему проверенному состоянию остаются открытыми:

- полнота текущего API/entity coverage;
- официальный live warehouse-list contract;
- классификация/актуальная reconciliation collision findings;
- user-authorized Gmail OAuth read-only verification;
- official RO App MCP authorization;
- credential-exposure remediation evidence;
- GitHub account/ruleset/security controls, которые требуют account-level проверки.

Уже имеющиеся backup/export и независимый restore/integrity evidence не повторяются без причины.

## Control rule

Каждая существенная задача проходит `OBSERVE → MEASURE → FIND → FIX → TEST → VERIFY → DOCUMENT → MONITOR`.

Старые успешные запуски не заменяют свежую проверку текущей технической канонической ветки `main` системы MARSEL ROAPP. `DONE` допускается только при наличии прямого evidence.

## Branch rule

`main` — единственная техническая каноническая интеграционная ветка систем MARSEL ROAPP. `main-MARSEL-ROAPP`, `Main` и `main-MARSEL-ROAPP-PROTECTION` — неканонические compatibility/snapshot branches, синхронизированные с текущим `main`; они не являются отдельными системами.
