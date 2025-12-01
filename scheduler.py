import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from database import Database
from notifications import send_notification

def check_reminders(db: Database, main_app=None):
    """
    Проверяет базу данных на наличие напоминаний, время которых наступило,
    отправляет уведомления и обновляет статусы. Также обновляет просроченные.
    """
    now = datetime.datetime.now()
    print(f"[{now}] Запущена фоновая проверка напоминаний...")
    
    # 1. Обновить все старые "Ожидающие" напоминания на "Просрочено"
    try:
        db.update_overdue_reminders()
    except Exception as e:
        print(f"Ошибка при обновлении просроченных напоминаний: {e}")
        return

    # 2. Получить все активные напоминания
    try:
        pending_reminders = db.get_reminders(status_filter="Ожидает")
    except Exception as e:
        print(f"Ошибка при получении ожидающих напоминаний: {e}")
        return

    # 3. Проверить каждое и отправить уведомление, если время пришло
    for reminder in pending_reminders:
        reminder_id, title, description, due_datetime_str, status = reminder
        
        try:
            # Преобразуем строку ISO 8601 в объект datetime
            try:
                due_datetime = datetime.datetime.fromisoformat(due_datetime_str)
            except ValueError:
                raise ValueError(f"Некорректный формат даты для напоминания ID {reminder_id}: '{due_datetime_str}'")

            # Если время напоминания уже наступило
            if due_datetime <= now:
                print(f"Сработало напоминание ID {reminder_id}: '{title}'")

                # Отправляем уведомление
                try:
                    send_notification(
                        title=f"Напоминание: {title}",
                        message=description or "Время пришло!",
                        reminder_id=reminder_id,
                        main_app=main_app
                    )
                except Exception as notification_error:
                    print(f"Ошибка при отправке уведомления для напоминания ID {reminder_id}: {notification_error}")
                    # Продолжаем выполнение даже если уведомление не отправилось

                # Обновляем статус на "Выполнено"
                try:
                    db.update_reminder_status(reminder_id, "Выполнено")
                except Exception as status_error:
                    print(f"Ошибка при обновлении статуса напоминания ID {reminder_id}: {status_error}")
        except Exception as e:
            print(f"Критическая ошибка при обработке напоминания ID {reminder_id}: {e}")


def start_scheduler(db: Database, main_app=None) -> BackgroundScheduler:
    """
    Инициализирует и запускает фоновый планировщик задач.

    :param db: Экземпляр класса Database для передачи в задачу.
    :param main_app: Ссылка на главное приложение для активации кнопок отсрочки.
    :return: Экземпляр запущенного планировщика.
    """
    scheduler = BackgroundScheduler(daemon=True)
    # Запускать задачу `check_reminders` каждые 30 секунд
    scheduler.add_job(check_reminders, 'interval', seconds=300, args=[db, main_app])
    scheduler.start()
    print("Фоновый планировщик запущен.")
    return scheduler

if __name__ == '__main__':
    # Пример для тестирования модуля
    print("Тестирование модуля планировщика...")
    
    # Создаем временную БД для теста
    test_db = Database("test_scheduler.db")
    
    # Добавляем напоминание, которое сработает через 5 секунд
    due_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
    test_db.add_reminder(
        "Тест планировщика", 
        "Это уведомление должно появиться через несколько секунд.", 
        due_time.isoformat()
    )
    print(f"Тестовое напоминание добавлено на {due_time.isoformat()}")

    # Запускаем планировщик с интервалом в 1 секунду для быстрого теста
    test_scheduler = BackgroundScheduler(daemon=True)
    test_scheduler.add_job(check_reminders, 'interval', seconds=1, args=[test_db])
    test_scheduler.start()

    try:
        # Даем планировщику поработать 10 секунд
        print("Ожидание срабатывания задачи (10 секунд)...")
        time.sleep(10)
    finally:
        # Останавливаем планировщик и закрываем соединение с БД
        print("Остановка планировщика...")
        test_scheduler.shutdown()
        test_db.close()
        # Удаляем тестовую БД
        import os
        os.remove("test_scheduler.db")
        print("Тестовая база данных удалена. Тест завершен.")
