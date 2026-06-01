# Платформа торговой сети электроники

Django/DRF backend: головной отдел управляет сетью и каталогом, дилерские центры ведут продажи и остатки. API: `view` → `repo` → `models`. Фоновые задачи: Redis/Celery (пополнение, списание, обнуление выручки, e-mail).

## Как устроена сеть

| Сущность | Назначение |
|----------|------------|
| `RetailPoint` | Торговая точка: **HEAD** (одна в сети) или **DEALER** |
| `RetailPointAddress` | Адрес точки (1:1) |
| `Employee` | Сотрудник точки; доступ к API — через связанного `User` |
| `Product` | Общий каталог сети |
| `DealerStock` | Наличие продукта у дилера |

Правила: у HEAD — один сотрудник; у дилера — не менее двух; суточная выручка на точке через API **не меняется** (PUT с `daily_revenue` → 400).

## Кто что видит в API

1. **Доступ** только у **активного сотрудника** с учётной записью. Без авторизации → **401**; пользователь без `Employee` или без прав на операцию → **403**.
2. **Сотрудник головного отдела** (точка HEAD): все точки; создание/удаление точек и продуктов; `GET .../points/above-avg-revenue/`; остатки любого дилера (`dealer_id` при POST в stock).
3. **Сотрудник дилерского центра**: в `GET /api/v1/points/` — **только своя** точка (массив из одной записи); изменение только своей точки; остатки только своего центра; каталог продуктов — **чтение**; изменение каталога — нет.
4. Один набор URL `/api/v1/...` для всех.

Сотрудник входит **логином и паролем** (токен на 24 ч) **или** персональным **API-ключом** (`X-API-Key`, без срока). Ключ и логин дают **те же права**, что у этого сотрудника (HEAD vs дилер).

## Аутентификация

### Логин и токен

```bash
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"dealer1","password":"dealer1pass"}'
```

Ответ: `{"token":"..."}`. Заголовок для API:

```text
Authorization: Token <token>
```

**Не используйте `Bearer`** — будет 403. Допускается alias `Bearer` в коде, но в Postman надёжнее `Token`.

Токен живёт **24 часа** (`AUTH_TOKEN_TTL`), затем снова `POST /api/auth/login/`.

**Первый вход** (после выдачи пароля `11111111`):

```bash
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user12","password":"11111111"}'
```

Ответ: `token`, `new_password` (12 символов), `password_change_required: true`. Старый пароль перестаёт работать; новый отображается на карточке сотрудника в админке.

Учётные записи `head1` / `head1pass` и `dealer1` / `dealer1pass` создаются при начальном заполнении БД **без** принудительной смены пароля при первом входе.

### API-ключ

Ключ с карточки сотрудника в админке:

```bash
curl -s http://localhost:8000/api/v1/points/ \
  -H "X-API-Key: <ключ_из_админки>"
```

### Проверка: дилер — только своя точка

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"dealer1","password":"dealer1pass"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s http://localhost:8000/api/v1/points/ \
  -H "Authorization: Token $TOKEN"
```

Ожидание: JSON-массив из **одной** точки.

### Проверка: головной отдел — все точки

```bash
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"head1","password":"head1pass"}'

curl -s http://localhost:8000/api/v1/points/ \
  -H "Authorization: Token <token>"
```

## Карта API

| Метод | URL | HEAD | Дилер |
|-------|-----|------|-------|
| POST | `/api/auth/login/` | да | да |
| GET | `/api/v1/points/` | все точки | только своя |
| GET | `/api/v1/points/?city=...` | фильтр по сети | в рамках своей точки |
| GET | `/api/v1/points/?product_id=...` | точки с товаром | если товар есть у себя |
| GET | `/api/v1/points/above-avg-revenue/` | да | 403 |
| GET/PUT/DELETE | `/api/v1/points/{id}/` | любая / PUT / DELETE | только своя / PUT |
| POST | `/api/v1/points/` | создать | 403 |
| GET | `/api/v1/products/` | каталог | каталог |
| POST/PUT/DELETE | `/api/v1/products/...` | да | 403 |
| GET/POST | `/api/v1/stock/` | все / POST + `dealer_id` | только свой склад |
| DELETE | `/api/v1/stock/{id}/` | да | только свои строки |

Примеры:

```bash
# Фильтр по городу
curl -s "http://localhost:8000/api/v1/points/?city=Moscow" -H "Authorization: Token <token>"

# Точки, где есть продукт
curl -s "http://localhost:8000/api/v1/points/?product_id=1" -H "Authorization: Token <token>"

# Выше средней выручки (только HEAD)
curl -s http://localhost:8000/api/v1/points/above-avg-revenue/ -H "Authorization: Token <token>"

# Каталог
curl -s http://localhost:8000/api/v1/products/ -H "Authorization: Token <token>"

# Остатки дилера
curl -s http://localhost:8000/api/v1/stock/ -H "Authorization: Token <token>"
```

## Админ-панель

**Вход:** http://localhost:8000/admin/ — суперпользователь **admin** / **admin**. Разделы Django «Пользователи», «Группы», «Токены» скрыты — учётки сотрудников ведутся в **«Сотрудники и доступ к API»**.

### Торговые точки

Список точек, тип HEAD/DEALER, суточная выручка, город. Inline: адрес и сотрудники.  
**Action «Очистить суточную выручку»:** обнуляет выручку; если выбрано **больше 5** точек — задача уходит в Celery (ответ сразу).

### Сотрудники и доступ к API

1. Создаёте сотрудника (точка, ФИО, уникальные email и телефон, «Активен»).
2. При сохранении: пользователь `user{id}` (или `head1` / `dealer1` для сотрудников из начального набора данных), пароль `11111111`, API-ключ, значения на карточке.
3. Блок **«Доступ к API»:** логин, пароль, токен (24 ч), API-ключ и статус.
4. Кнопки на карточке: **сброс пароля** (случайные 12 символов), **перевыпуск API-ключа**.
5. Массовые actions: сброс пароля, перевыпуск токена, выдача/отзыв ключа.

Сотрудник снаружи использует то же, что на карточке: логин/пароль → login; ключ → `X-API-Key`.

Второго сотрудника на **HEAD** создать нельзя (валидация формы). У дилера нужно **минимум двух** сотрудников.

### Каталог и наличие

- **Продукты** — каталог сети.
- **Наличие у дилеров** — фильтры по наличию и дилеру.

### Celery

При dev-compose поднимаются worker и beat: **09:00** — пополнение нулевых остатков; **каждый час** — списание и выручка; **21:15** — обнуление выручки дилеров; при нулевом остатке — e-mail сотруднику HEAD.

## Запуск

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

- Admin: http://localhost:8000/admin/ → **admin** / **admin**
- API: **head1** / **head1pass**, **dealer1** / **dealer1pass**

Полный сброс БД и начальные данные:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
# или: make reset
```

Локально (Postgres на `localhost:5432`, как в compose):

```bash
cp .env.example .env
export DATABASE_URL=postgres://app:app@127.0.0.1:5432/retail_network
export TEST_DATABASE_URL=postgres://app:app@127.0.0.1:5432/retail_network_test
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

БД `retail_network_test` создаётся при первом `docker compose up` (init-скрипт). Если volume уже был без неё:

```bash
docker compose -f docker-compose.yml exec db psql -U app -d retail_network -c "CREATE DATABASE retail_network_test;"
```

## Postman

1. `POST /api/auth/login/` с JSON `username` / `password`.
2. Скопировать `token` из ответа.
3. Заголовок: `Authorization` = `Token <token>` (не Bearer).
4. `GET http://localhost:8000/api/v1/points/`.

Для API-ключа: заголовок `X-API-Key`.

## Разработка

```bash
make up-build
make down-all
make reset
make test
```

Проверки: `python manage.py test` (БД `TEST_DATABASE_URL`, PostgreSQL).

Приложения: `retail_points`, `products`, `stock`, `access`, `core`.

## Нюансы

- Токен **24 ч**; API-ключ **без TTL**, отзыв в админке.
- В Postman: **`Authorization: Token …`**, не `Bearer` (в коде Bearer тоже принимается).
- Первый login с `11111111` → `new_password` в JSON; `head1`/`dealer1` без принудительной смены.
- Пароль и API-ключ на карточке сотрудника хранятся в открытом виде для удобной выдачи через админку.
- `daily_revenue` нельзя менять через API PUT точки.
- Второй HEAD в сети создать нельзя (ограничение БД).
- У головного отдела **ровно один** сотрудник: второго добавить нельзя (админка, inline, `Employee.clean`, `pre_save`).
- Остатки только у DEALER; у HEAD склада продажи нет.
- Email и телефон сотрудника **уникальны**.
- Суперпользователь `admin` **не** ходит в employee API без записи `Employee`.
- После `docker compose down -v` начальные данные загружаются заново при старте.
- Остальные сотрудники после заполнения БД: **user{N}** / **11111111** (N = id), первый вход меняет пароль.
