# Phonebook API

Асинхронний REST API для керування телефонною книгою. Проєкт побудований на
FastAPI та SQLAlchemy і використовує PostgreSQL як базу даних.

## Можливості

- реєстрація користувачів із хешуванням паролів (Argon2);
- аутентифікація та авторизація через JWT (`access_token`);
- верифікація електронної пошти користувача;
- кожен користувач бачить і змінює лише власні контакти;
- обмеження кількості запитів до `/api/users/me` (10 на хвилину);
- оновлення аватара користувача через Cloudinary;
- CORS для REST API;
- створення, перегляд, оновлення та видалення контактів;
- пошук контактів за іменем, прізвищем та email із комбінуванням фільтрів;
- вибірка контактів із днями народження в найближчі N днів;
- пагінація списку контактів через `skip` і `limit`;
- перевірка доступності бази даних через health-check;
- автоматична документація API у Swagger UI та ReDoc.

## Вимоги

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (або
  Docker Engine) із Docker Compose v2 — перевірте командою
  `docker compose version`;
- обліковий запис [Cloudinary](https://cloudinary.com/) (безкоштовного плану
  достатньо) — для аватарів;
- `openssl` — для генерації секретів (є в macOS і Linux);
- лише для запуску без Docker: Python 3.13+ і
  [uv](https://docs.astral.sh/uv/).

## Як підняти проєкт

### Крок 1. Отримайте код

```bash
git clone <url-репозиторію> goit-pythonweb-hw-10
cd goit-pythonweb-hw-10
```

### Крок 2. Створіть файл `.env`

Усі змінні середовища та секрети зберігаються лише у файлі `.env`, який
ігнорується git. Створіть його із шаблону:

```bash
cp .env.example .env
```

Відкрийте `.env` і заповніть значення:

| Змінна                                     | Що вписати                                                                 |
| ------------------------------------------ | -------------------------------------------------------------------------- |
| `POSTGRES_PASSWORD`                        | Будь-який надійний пароль                                                  |
| `DB_URL`                                   | Той самий пароль замість `change-me` (використовується при запуску без Docker) |
| `JWT_SECRET`                               | Результат команди `openssl rand -hex 32`                                   |
| `CLD_NAME`, `CLD_API_KEY`, `CLD_API_SECRET` | Cloudinary → **Settings → API Keys** (Cloud name, API Key, API Secret)     |

Решту змінних можна залишити за замовчуванням:

- `MAIL_*` уже налаштовані на Mailpit, який запускається разом із проєктом.
  Щоб надсилати справжні листи, вкажіть параметри свого SMTP-сервера
  (`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_USE_CREDENTIALS=true`, `MAIL_STARTTLS` або `MAIL_SSL_TLS`).
- `CORS_ORIGINS` — JSON-список дозволених origin фронтенду.
- `APP_BASE_URL` — адреса API, з якої формується посилання в листі
  верифікації.

> Під час запуску в Docker `DB_URL` та `MAIL_SERVER` автоматично
> перевизначаються в `docker-compose.yml` (хости `db` і `mailpit`), тож
> змінювати їх для Docker не потрібно.

### Крок 3. Запустіть сервіси

Переконайтеся, що Docker Desktop запущений, і виконайте:

```bash
docker compose up --build
```

Перший запуск триває кілька хвилин (завантаження образів і встановлення
залежностей). Застосунок сам застосує міграції бази даних. Готовність видно
за рядком у логах:

```
app-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

Щоб запустити у фоні, додайте `-d`: `docker compose up --build -d`.

Будуть запущені три сервіси:

| Сервіс    | Адреса                  | Опис                                      |
| --------- | ----------------------- | ----------------------------------------- |
| `app`     | `http://localhost:8000` | API (міграції застосовуються автоматично) |
| `db`      | `localhost:5432`        | PostgreSQL                                |
| `mailpit` | `http://localhost:8025` | Вебінтерфейс для перегляду листів         |

### Крок 4. Перевірте, що все працює

```bash
curl http://localhost:8000/api/healthchecker
# {"message":"Welcome to FastAPI!"}
```

Документація API:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Далі зареєструйте користувача та підтвердіть email — див. розділ
[Аутентифікація](#аутентифікація).

### Корисні команди

| Команда                                  | Що робить                                              |
| ---------------------------------------- | ------------------------------------------------------ |
| `docker compose ps`                      | Стан контейнерів                                       |
| `docker compose logs -f app`             | Логи застосунку                                        |
| `docker compose stop`                    | Зупинити сервіси (дані зберігаються)                   |
| `docker compose down`                    | Зупинити й видалити контейнери (дані БД зберігаються)  |
| `docker compose down -v`                 | Видалити контейнери **разом із базою даних**           |
| `docker compose up -d --build app`       | Перезібрати застосунок після зміни коду                |
| `docker compose up -d --force-recreate app` | Перезапустити застосунок після зміни `.env`         |
| `docker compose exec db psql -U postgres -d phonebook` | Консоль PostgreSQL                       |

### Можливі проблеми

- **`Cannot connect to the Docker daemon`** — запустіть Docker Desktop і
  повторіть команду.
- **`port is already allocated` для 5432** — порт зайнятий локальним
  PostgreSQL. Зупиніть його або змініть `POSTGRES_PORT` у `.env`
  (наприклад, на `5433`; для запуску без Docker змініть порт і в `DB_URL`).
- **Зайняті порти 8000, 8025 або 1025** — зупиніть процес, що їх використовує,
  або змініть ліве значення відповідного `ports` у `docker-compose.yml`.
- **`validation error for Settings`** у логах — у `.env` бракує змінної або
  вона має неправильний формат; звірте файл з `.env.example`.
- **Аватар повертає 502** — неправильні `CLD_*` у `.env`; виправте та
  перезапустіть застосунок (`docker compose up -d --force-recreate app`).
- **Лист не прийшов** — перевірте `http://localhost:8025` і
  `docker compose logs app`.

## Запуск без Docker (для розробки)

База даних і пошта все одно потрібні — найпростіше підняти лише їх через
Docker, а застосунок запустити локально з автоперезавантаженням:

```bash
docker compose up -d db mailpit   # або власні PostgreSQL та SMTP
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

У цьому режимі використовуються `DB_URL` і `MAIL_SERVER=localhost` з `.env`.
Якщо контейнер `app` уже запущений, спершу зупиніть його
(`docker compose stop app`), щоб звільнити порт 8000.

## Аутентифікація

1. Зареєструйтеся: `POST /api/auth/register`.
2. Відкрийте лист у Mailpit (`http://localhost:8025`) і перейдіть за
   посиланням підтвердження.
3. Увійдіть: `POST /api/auth/login` (form-data `username` і `password`) —
   у відповідь прийде `access_token`.
4. Передавайте токен у заголовку `Authorization: Bearer <access_token>`.
   У Swagger UI натисніть **Authorize** і введіть ім'я користувача та пароль.

Без підтвердженої електронної адреси увійти неможливо.

## API

### Перевірка підключення до бази даних

```http
GET /api/healthchecker
```

### Аутентифікація

| Метод  | Endpoint                          | Опис                                     |
| ------ | --------------------------------- | ---------------------------------------- |
| `POST` | `/api/auth/register`              | Реєстрація (201; 409, якщо email або ім'я зайняті) |
| `POST` | `/api/auth/login`                 | Отримати `access_token` (201; 401 при невірних даних) |
| `GET`  | `/api/auth/confirmed_email/{token}` | Підтвердити електронну адресу          |
| `POST` | `/api/auth/request_email`         | Повторно надіслати лист підтвердження    |

Приклад реєстрації:

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
   -H "Content-Type: application/json" \
   -d '{"username": "ada", "email": "ada@example.com", "password": "secret123"}'
```

Приклад входу:

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
   -d "username=ada&password=secret123"
```

### Користувачі

Потрібна авторизація.

| Метод   | Endpoint            | Опис                                        |
| ------- | ------------------- | ------------------------------------------- |
| `GET`   | `/api/users/me`     | Поточний користувач (не більше 10 запитів/хв, далі 429) |
| `PATCH` | `/api/users/avatar` | Завантажити аватар (multipart, поле `file`) |

```bash
curl -X PATCH "http://localhost:8000/api/users/avatar" \
   -H "Authorization: Bearer $TOKEN" \
   -F "file=@avatar.png"
```

### Контакти

Потрібна авторизація. Усі операції виконуються лише з контактами поточного
користувача; чужий контакт повертає `404 Contact not found`.

| Метод    | Endpoint                     | Опис                      |
| -------- | ---------------------------- | ------------------------- |
| `GET`    | `/api/contacts/`             | Отримати список контактів |
| `GET`    | `/api/contacts/{contact_id}` | Отримати контакт за ID    |
| `POST`   | `/api/contacts/`             | Створити контакт          |
| `PUT`    | `/api/contacts/{contact_id}` | Оновити контакт           |
| `DELETE` | `/api/contacts/{contact_id}` | Видалити контакт          |

Для списку контактів доступні такі query-параметри:

| Параметр           | Тип       | Опис                                             |
| ------------------ | --------- | ------------------------------------------------ |
| `first_name`       | `string`  | Пошук за ім'ям без урахування регістру           |
| `last_name`        | `string`  | Пошук за прізвищем без урахування регістру       |
| `email`            | `string`  | Пошук за email без урахування регістру           |
| `days_to_birthday` | `integer` | День народження в найближчі N днів (0–366)        |
| `skip`             | `integer` | Кількість пропущених записів, за замовчуванням 0 |
| `limit`            | `integer` | Максимум записів, за замовчуванням 100           |

Приклад запиту зі змішаними фільтрами та пагінацією:

```http
GET /api/contacts/?last_name=lovelace&days_to_birthday=30&skip=0&limit=20
```

Фільтри комбінуються між собою: кожен переданий параметр додатково звужує
вибірку. Пошук за іменем, прізвищем та email виконується без урахування
регістру.

`days_to_birthday=N` повертає контакти, чий день народження припадає на
проміжок від сьогодні до `N` днів уперед включно. Перехід через межу року
враховано: наприклад, 28 грудня запит із `N=7` знайде і грудневі, і січневі
дні народження. `N=0` — лише ті, у кого день народження сьогодні. Контакти,
народжені 29 лютого, потрапляють у вибірку лише тоді, коли проміжок накриває
29 лютого високосного року.

Приклад створення контакту через `curl` (`additional_info` — необов'язкове
поле, за замовчуванням `null`):

```bash
curl -X POST "http://localhost:8000/api/contacts/" \
   -H "Authorization: Bearer $TOKEN" \
   -H "Content-Type: application/json" \
   -d '{
      "first_name": "Ada",
      "last_name": "Lovelace",
      "email": "ada@example.com",
      "phone_number": "3805012345",
      "dob": "1815-12-10",
      "additional_info": "Перший програміст"
   }'
```

## CORS

Дозволені origin задаються змінною `CORS_ORIGINS` у `.env` як JSON-список,
наприклад `["http://localhost:3000"]`.

## Міграції

Створення нової міграції:

```bash
uv run alembic revision --autogenerate -m "опис змін"
```

Відкат останньої міграції:

```bash
uv run alembic downgrade -1
```
