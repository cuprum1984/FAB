# Задача: Добавить asyncio.Semaphore для ограничения параллелизма в мониторинге источников

**Время:** 14:45  
**Дата:** 17.03.2026  
**Приоритет:** 🔴 КРИТИЧНО (SCALABILITY_PLAN.md, раздел 2)  
**Оценка времени:** 1-2 часа  

---

## 📋 Контекст

**Проект:** MyAggryBot (Telegram бот-агрегатор)  
**Документ:** SCALABILITY_PLAN.md (раздел "2. Однопоточный мониторинг — КРИТИЧНО")  
**Текущая проблема:** Все источники проверяются последовательно в цикле `for`, что приводит к:
- Блокировке обработки при медленных источниках
- Невозможности масштабирования на 1000+ админов (12,000 источников)
- Превышению Rate Limit из-за отсутствия контроля параллелизма

**Целевая нагрузка:** 12,000 источников, 40 проверок/сек, максимум 10 одновременных запросов к API

---

## 📁 Файлы для изменения

### 1. `core/settings.py`
**Добавить новую переменную окружения:**

```python
SEMAPHORE_LIMIT: int = int(os.getenv('SEMAPHORE_LIMIT', '10'))
```

### 2. `core/services/monitoring/base.py`
**Метод для рефакторинга:** `check_all_sources()` (строки ~103-145)

---

## 🎯 Требования

### 1. Переменная окружения в `core/settings.py`

Добавить после существующих настроек rate limiting:

```python
# Semaphore для ограничения параллелизма мониторинга
SEMAPHORE_LIMIT: int = int(os.getenv('SEMAPHORE_LIMIT', '10'))
```

### 2. Рефакторинг `check_all_sources()` в `base.py`

#### Текущая логика (упрощённо):
```python
async def check_all_sources(self, session: AsyncSession):
    stmt = select(ContentSource)
    result = await session.execute(stmt)
    sources = result.scalars().all()
    
    for source in sources:  # ← ПОСЛЕДОВАТЕЛЬНЫЙ ЦИКЛ
        try:
            if not await self._check_source_security(source, session):
                continue
            
            if not await self._should_check_source(source):
                continue
            
            if not await self._has_active_assignments(source.source_global_id, session):
                source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.flush()
                continue
            
            if source.source_type == 'telegram':
                await self.telegram_monitor.check_telegram_source(source, session)
            elif source.source_type == 'youtube':
                await self.youtube_monitor.check_youtube_source(source, session)
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки источника {source.source_global_id}: {e}")
            await self._update_source_error_stats(source.source_global_id)
            await session.rollback()
    
    await session.commit()
```

#### Требуемая логика:

```python
async def check_all_sources(self, session: AsyncSession):
    """Проверить все источники с ограничением параллелизма через Semaphore."""
    logger.info("🔍 Проверяю источники...")
    
    try:
        # Загружаем все источники
        stmt = select(ContentSource)
        result = await session.execute(stmt)
        sources = result.scalars().all()
        
        logger.info(f"📊 Найдено источников: {len(sources)}")
        
        # Фильтруем источники, которые нужно проверить
        sources_to_check = []
        for source in sources:
            try:
                if not await self._check_source_security(source, session):
                    logger.warning(f"⏭️ Пропускаю небезопасный источник {source.source_global_id}")
                    continue
                
                if not await self._should_check_source(source):
                    continue
                
                if not await self._has_active_assignments(source.source_global_id, session):
                    logger.debug(f"📭 Пропускаю источник {source.source_global_id}: нет активных назначений")
                    source.last_checked_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                    await session.flush()
                    continue
                
                sources_to_check.append(source)
                
            except Exception as e:
                logger.error(f"❌ Ошибка предпроверки источника {source.source_global_id}: {e}")
                await self._update_source_error_stats(source.source_global_id)
        
        logger.info(f"✅ Источников на проверку: {len(sources_to_check)}")
        
        # Создаём Semaphore для ограничения параллелизма
        semaphore = asyncio.Semaphore(settings.SEMAPHORE_LIMIT)
        
        async def check_with_semaphore(source: ContentSource):
            """Обёртка для проверки источника с Semaphore."""
            async with semaphore:
                try:
                    if source.source_type == 'telegram':
                        await self.telegram_monitor.check_telegram_source(source, session)
                    elif source.source_type == 'youtube':
                        await self.youtube_monitor.check_youtube_source(source, session)
                    else:
                        logger.warning(f"⚠️ Неизвестный тип источника: {source.source_type}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки источника {source.source_global_id}: {e}")
                    await self._update_source_error_stats(source.source_global_id)
                    # Не делаем rollback здесь - это будет сделано в конце цикла
        
        # Запускаем параллельную проверку с ограничением
        tasks = [check_with_semaphore(source) for source in sources_to_check]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Логируем результаты
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        logger.info(f"✅ Проверка завершена: успешно={success_count}, ошибок={error_count}")
        
        # Коммитим все изменения сессии
        await session.commit()
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Критическая ошибка в check_all_sources: {e}")
        raise
```

### 3. Логирование

Добавить информативные логи:
- ✅ Количество найденных источников
- ✅ Количество источников на проверку (после фильтрации)
- ✅ Количество одновременных задач (SEMAPHORE_LIMIT)
- ✅ Результаты выполнения (успешно/ошибки)
- ⏱️ Опционально: время выполнения всего цикла

---

## ⚠️ Ограничения

- **НЕ менять** логику внутри `check_telegram_source()` и `check_youtube_source()`
- **НЕ менять** метод `_should_check_source()` (там уже есть интервал 30 мин для YouTube)
- **Сохранить** обработку ошибок через `try/except` с `rollback` сессии
- **Максимум 10** одновременных запросов к API (настраивается через `SEMAPHORE_LIMIT`)
- **Использовать** `return_exceptions=True` в `asyncio.gather()` для устойчивости

---

## 🧪 Тесты для проверки

После реализации проверить:

1. **Бот запускается без ошибок:**
   ```bash
   python -m bot.main
   # Ожидается: нормальный запуск, нет импортов ошибок
   ```

2. **Источники проверяются параллельно:**
   - В логах должно быть видно несколько одновременных проверок
   - Максимум `SEMAPHORE_LIMIT` задач выполняются одновременно

3. **Ошибки отдельных источников не ломают весь цикл:**
   - При ошибке одного источника остальные продолжают проверяться
   - В логах: `успешно=X, ошибок=Y`

4. **Интервалы проверки соблюдаются:**
   - YouTube проверяется раз в 30 минут (уже реализовано в `_should_check_source()`)
   - Telegram проверяется раз в 5 минут

5. **Rate Limit не превышается:**
   - Максимум 10 одновременных запросов к Telegram API
   - Максимум 10 одновременных запросов к YouTube API

---

## 📝 Примечания

- Метод `_get_source_assignments()` останется с N+1 проблемой — это будет исправлено в следующем промпте (оптимизация SQL запросов)
- Сначала реализуем Semaphore, потом оптимизацию SQL запросов
- Переменная `SEMAPHORE_LIMIT` должна быть добавлена в `.env.example` и `.env.production`
- Для продакшена рекомендуется `SEMAPHORE_LIMIT=10`, для тестов можно меньше

---

## 🔗 Связанные документы

- SCALABILITY_PLAN.md (раздел 2: "Однопоточный мониторинг — КРИТИЧНО")
- core/services/monitoring/base.py (текущая реализация)
- core/settings.py (конфигурация проекта)

---

## 📊 Ожидаемый результат

| Метрика | До изменений | После изменений |
|---------|--------------|-----------------|
| Параллелизм | 1 (последовательно) | 10 (параллельно) |
| Время цикла (12,000 источников) | ~60,000 сек (16 часов) | ~6,000 сек (1.6 часа) |
| Блокировки | Частые | Отсутствуют |
| Устойчивость к ошибкам | Низкая | Высокая |
| Соответствие Rate Limit | ❌ Превышение | ✅ Соблюдение |
