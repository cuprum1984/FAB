# Задача: Оптимизировать загрузку CachedMedia — устранить N+1 запросы к БД

**Время:** 15:12  
**Дата:** 17.03.2026  
**Приоритет:** 🟡 СРЕДНИЙ (SCALABILITY_PLAN.md, раздел 3)  
**Оценка времени:** 1-2 часа  

---

## 📋 Контекст

**Проект:** MyAggryBot (Telegram бот-агрегатор)  
**Документ:** SCALABILITY_PLAN.md (раздел "3. N+1 запрос к БД — СРЕДНИЙ ПРИОРИТЕТ")  
**Текущая проблема:** Для КАЖДОГО поста в Telegram-канале выполняется отдельный SQL-запрос к таблице `cached_media` для поиска `file_id`.

**Нагрузка при масштабе:**
- 12,000 источников × 10 постов = **120,000 лишних запросов к БД за цикл**
- При интервале 5 минут = **400 запросов/сек только для CachedMedia**

**Цель:** Уменьшить количество запросов в 10 раз через пакетную загрузку.

---

## ⚠️ ВАЖНОЕ ПРИМЕЧАНИЕ

**Redis НЕ требуется для этой оптимизации!**

Речь идёт об оптимизации SQL-запросов к PostgreSQL, а не о добавлении Redis-кэширования. Таблица `cached_media` остаётся основным хранилищем `file_id`.

| Уровень оптимизации | Нужно ли сейчас? | Когда понадобится? |
|---------------------|------------------|---------------------|
| **Пакетная загрузка (SQL)** | ✅ **ДА, срочно** | Сейчас (этот промпт) |
| **Redis для cached_media** | ❌ Нет | При 5000+ админов (v7.0) |
| **Redis для last_post_id** | ⚠️ Уже используется | Уже есть в коде |

---

## 📁 Файл для изменения

### `core/services/monitoring/telegram_monitor.py`

**Метод для рефакторинга:** `_process_telegram_post()` и вызывающий код в `check_telegram_source()`  
**Текущие строки с проблемой:** ~195-215

---

## 🔍 Текущая проблема (N+1 запросы)

### Упрощённая текущая логика:

```python
async def check_telegram_source(self, source: ContentSource, session: AsyncSession):
    # ... получение новых постов ...
    new_posts = await get_telegram_posts(username, str(last_post_id) if last_post_id else None)
    
    # ❌ N+1 ПРОБЛЕМА: В цикле по постам
    for i, post in enumerate(new_posts, 1):
        post_id = post.get('post_id')
        
        # ... другая логика ...
        
        media_items = post.get('media', [])
        file_id = None
        
        if media_items and len(media_items) > 0:
            media = media_items[0]
            media_url = media.get('url')
            
            if media_url:
                # ❌ ОТДЕЛЬНЫЙ ЗАПРОС ДЛЯ КАЖДОГО ПОСТА
                stmt = select(CachedMedia).where(
                    CachedMedia.source_global_id == source.source_global_id,
                    CachedMedia.post_id == post_id
                )
                result = await session.execute(stmt)
                cached = result.scalar_one_or_none()
                
                if cached:
                    file_id = cached.file_id
                    logger.info(f"✅ Найден file_id в кэше: {file_id}")
                else:
                    logger.debug(f"❌ file_id НЕ НАЙДЕН в кэше")
        
        # ... отправка поста ...
```

**Проблема:**
- Для каждого поста выполняется отдельный `SELECT` запрос к таблице `cached_media`
- При 10 постах на источник = 10 дополнительных запросов
- При 12,000 источников = **120,000 запросов за цикл**

---

## ✅ Требуемое решение (пакетная загрузка)

### Шаг 1: Пакетная загрузка ДО цикла

**Место вставки:** Перед циклом `for post in new_posts:` в методе `check_telegram_source()`

```python
# ✅ ПАКЕТНАЯ ЗАГРУЗКА ВСЕХ CACHEDMEDIA ДЛЯ ТЕКУЩЕГО ИСТОЧНИКА
post_ids = [p['post_id'] for p in new_posts if p.get('post_id')]

cached_media_map = {}
if post_ids:
    from sqlalchemy import select
    stmt = select(CachedMedia).where(
        CachedMedia.source_global_id == source.source_global_id,
        CachedMedia.post_id.in_(post_ids)  # ← КЛЮЧЕВОЕ ИЗМЕНЕНИЕ
    )
    result = await session.execute(stmt)
    cached_media_map = {cm.post_id: cm.file_id for cm in result.scalars()}
    logger.debug(f"📦 Загружено {len(cached_media_map)} file_id из кэша БД для источника {source.source_global_id}")
else:
    logger.debug(f"📭 Нет постов с post_id для загрузки cached_media")
```

### Шаг 2: Замена запроса в цикле на lookup в словаре

**Место замены:** Внутри цикла `for post in new_posts:`, блок с запросом к `CachedMedia`

#### Было (с запросом к БД):
```python
for i, post in enumerate(new_posts, 1):
    post_id = post.get('post_id')
    
    # ... другая логика ...
    
    media_items = post.get('media', [])
    file_id = None
    
    if media_items and len(media_items) > 0:
        media = media_items[0]
        media_url = media.get('url')
        
        if media_url:
            # ❌ ЗАПРОС К БД
            stmt = select(CachedMedia).where(
                CachedMedia.source_global_id == source.source_global_id,
                CachedMedia.post_id == post_id
            )
            result = await session.execute(stmt)
            cached = result.scalar_one_or_none()
            
            if cached:
                file_id = cached.file_id
                logger.info(f"✅ Найден file_id в кэше: {file_id}")
            else:
                logger.debug(f"❌ file_id НЕ НАЙДЕН в кэше")
```

#### Стало (с lookup в словаре):
```python
for i, post in enumerate(new_posts, 1):
    post_id = post.get('post_id')
    
    # ... другая логика ...
    
    media_items = post.get('media', [])
    file_id = None
    
    if media_items and len(media_items) > 0:
        media = media_items[0]
        media_url = media.get('url')
        
        if media_url:
            # ✅ LOOKUP В СЛОВАРЕ (без запроса к БД)
            file_id = cached_media_map.get(post_id)
            
            if file_id:
                logger.debug(f"✅ Найден file_id в кэше БД для поста {post_id}: {file_id}")
            else:
                logger.debug(f"❌ file_id НЕ НАЙДЕН в кэше БД для поста {post_id}")
```

### Шаг 3: Удалить старый код запроса

**Удалить полностью:**
```python
# Удалить эти строки:
stmt = select(CachedMedia).where(
    CachedMedia.source_global_id == source.source_global_id,
    CachedMedia.post_id == post_id
)
result = await session.execute(stmt)
cached = result.scalar_one_or_none()

if cached:
    file_id = cached.file_id
    logger.info(f"✅ Найден file_id в кэше: {file_id}")
else:
    logger.debug(f"❌ file_id НЕ НАЙДЕН в кэше")
```

---

## 🎯 Требования

- ✅ **НЕ добавлять** Redis-кэширование (только оптимизация SQL-запроса)
- ✅ **Сохранить** существующую логику отправки (`send_media_to_assignment` / `send_text_to_assignment`)
- ✅ **Добавить** debug-логирование количества загруженных `file_id`
- ✅ **Использовать** `.in_()` для пакетной загрузки
- ✅ **Обработать** случай пустого списка `post_ids`
- ✅ **Импортировать** `select` из `sqlalchemy` если ещё не импортировано

---

## 🧪 Тесты для проверки

После реализации проверить:

### 1. Проверка запуска без ошибок
```bash
python -m bot.main
# Ожидается: нормальный запуск, нет ошибок импорта
```

### 2. Проверка логирования пакетной загрузки
В логах должно появиться:
```
📦 Загружено X file_id из кэша БД для источника <source_global_id>
```

### 3. Проверка корректности отправки медиа
- Медиафайлы с `file_id` в кэше отправляются как фото/документ
- Медиафайлы без `file_id` отправляются как текст или парсятся заново

### 4. Проверка производительности
Замерить время обработки одного источника:
- **До изменений:** ~100-200мс на источник (с 10 запросами к БД)
- **После изменений:** ~20-50мс на источник (с 1 пакетным запросом)

### 5. Проверка через тесты проекта
```bash
pytest tests/test_monitoring_service.py -v
pytest tests/test_destination_service.py -v
```

---

## 📊 Ожидаемый результат

| Метрика | До изменений | После изменений | Улучшение |
|---------|--------------|-----------------|-----------|
| Запросов к `cached_media` на источник | 10 (по числу постов) | 1 (пакетный) | **в 10 раз** |
| Запросов к `cached_media` за цикл (12,000 источников) | 120,000 | 12,000 | **в 10 раз** |
| Запросов/сек к БД (только CachedMedia) | ~400 | ~40 | **в 10 раз** |
| Время обработки одного источника | ~150мс | ~40мс | **в 3.75 раза** |
| Общая нагрузка на БД | Высокая | Умеренная | **Значительно ниже** |

---

## 📝 Примечания

### Почему это работает быстро:

1. **Индексы в БД:** Таблица `cached_media` должна иметь индекс по `(source_global_id, post_id)` → поиск по этим полям быстрый.

2. **Один запрос вместо N:** SQLAlchemy оптимизирует запрос с `.in_()` и выполняет его за одно обращение к БД.

3. **Словарь в памяти:** Lookup в Python-словаре `{post_id: file_id}` происходит мгновенно (O(1)).

### Что НЕ меняется:

- Структура таблицы `cached_media` остаётся прежней
- Логика сохранения `file_id` при первой загрузке не меняется
- Redis не используется для этой оптимизации
- Миграции БД не требуются

### Следующий шаг:

После этой оптимизации можно аналогично улучшить метод `_get_source_assignments()` в `base.py` для пакетной загрузки назначений для нескольких источников сразу.

---

## 🔗 Связанные документы

- SCALABILITY_PLAN.md (раздел 3: "N+1 запрос к БД — СРЕДНИЙ ПРИОРИТЕТ")
- core/services/monitoring/telegram_monitor.py (текущая реализация)
- core/models/cache.py (модель CachedMedia)

---

## 💡 Пример полного кода после изменений

### Фрагмент `check_telegram_source()`:

```python
# ... получение new_posts ...

logger.info(f"   📬 Парсер вернул {len(new_posts)} постов")

if not new_posts:
    logger.debug(f"📭 Нет новых постов в {source_name}")
    source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()
    await self.monitoring._reset_source_error_stats(source.source_global_id)
    return

logger.info(f"✅ Найдено {len(new_posts)} новых постов в {source_name}")

# ✅ ПАКЕТНАЯ ЗАГРУЗКА CACHEDMEDIA (НОВОЕ)
post_ids = [p['post_id'] for p in new_posts if p.get('post_id')]

cached_media_map = {}
if post_ids:
    from sqlalchemy import select
    stmt = select(CachedMedia).where(
        CachedMedia.source_global_id == source.source_global_id,
        CachedMedia.post_id.in_(post_ids)
    )
    result = await session.execute(stmt)
    cached_media_map = {cm.post_id: cm.file_id for cm in result.scalars()}
    logger.debug(f"📦 Загружено {len(cached_media_map)} file_id из кэша БД")

# Сохраняем текущий last_post_id для проверок во время цикла
current_last_id = source.last_successful_post_id
last_successful_id = None

for i, post in enumerate(new_posts, 1):
    post_id = post.get('post_id')
    logger.info(f"   📝 Обработка поста {i}/{len(new_posts)}: ID={post_id}")

    try:
        # ✅ LOOKUP В СЛОВАРЕ ВМЕСТО ЗАПРОСА К БД
        file_id = cached_media_map.get(post_id)
        
        if file_id:
            logger.debug(f"✅ Найден file_id для поста {post_id}")
        else:
            logger.debug(f"❌ file_id не найден для поста {post_id}")
        
        await self._process_telegram_post(
            post=post,
            source=source,
            assignments=assignments,
            session=session,
            current_last_id=current_last_id,
            file_id=file_id  # ← Передаём file_id напрямую
        )

        if post_id:
            last_successful_id = post_id

        if i < len(new_posts):
            await asyncio.sleep(2.0)

    except Exception as e:
        logger.error(f"❌ Ошибка обработки поста {post_id}: {e}")
        await session.rollback()
        await asyncio.sleep(2.0)
        continue

# ... остальной код ...
```

### Обновлённый `_process_telegram_post()`:

```python
async def _process_telegram_post(
    self,
    post: Dict,
    source: ContentSource,
    assignments: List,
    session: AsyncSession,
    current_last_id: Optional[int] = None,
    file_id: Optional[str] = None  # ← Новый параметр
):
    """Обработать один Telegram пост"""
    from core.services.monitoring.post_sender import PostSender
    
    post_id = post.get('post_id')
    if not post_id:
        return

    try:
        post_id_int = int(post_id)
    except:
        return

    post_key = f"{source.source_global_id}:{post_id_int}"
    if post_key in self.monitoring._processed_posts:
        logger.warning(f"⚠️ Пост {post_id_int} уже обработан")
        return

    self.monitoring._processed_posts.add(post_key)

    if current_last_id and post_id_int <= current_last_id:
        logger.debug(f"⏭️ Пропускаю старый пост {post_id_int} (<= {current_last_id})")
        return

    logger.info(f"📝 Новый пост {post_id_int} из {source.telegram_username}")

    # file_id уже передан извне, не нужно загружать из БД
    media_items = post.get('media', [])
    logger.debug(f"📸 Медиа в посте: {len(media_items)} шт.")

    post_sender = PostSender(self.bot)

    for assignment in assignments:
        try:
            if file_id:
                await post_sender.send_media_to_assignment(
                    post=post,
                    file_id=file_id,
                    assignment=assignment,
                    source=source,
                    session=session
                )
            else:
                await post_sender.send_text_to_assignment(
                    post=post,
                    assignment=assignment,
                    source=source,
                    session=session
                )

            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки поста {post_id_int}: {e}")
```
