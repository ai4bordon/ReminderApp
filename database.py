import sqlite3
import threading
from typing import List, Tuple, Optional
import datetime

DB_FILE = "reminders.db"

class Database:
    """
    Класс для управления базой данных SQLite для напоминаний.
    """

    def __init__(self, db_file: str = DB_FILE):
        """
        Инициализирует соединение с базой данных и создает таблицу, если она не существует.

        :param db_file: Путь к файлу базы данных.
        """
        try:
            self.conn = sqlite3.connect(db_file, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.create_table()
            self.lock = threading.Lock()
        except sqlite3.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")
            self.conn = None
            self.cursor = None

    def create_table(self):
        """
        Создает таблицу 'reminders' в базе данных, если она еще не создана.
        """
        if not self.cursor:
            return
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_datetime TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблицы: {e}")

    def add_reminder(self, title: str, description: str, due_datetime: str) -> Optional[int]:
        """
        Добавляет новое напоминание в базу данных.

        :param title: Заголовок напоминания.
        :param description: Описание напоминания.
        :param due_datetime: Дата и время срабатывания в формате ISO 8601.
        :return: ID добавленного напоминания или None в случае ошибки.
        :raises ValueError: Если входные данные невалидны.
        """
        if not self.conn:
            raise RuntimeError("Соединение с базой данных не установлено")

        # Валидация входных данных
        if not title or not isinstance(title, str):
            raise ValueError("Заголовок обязателен и должен быть строкой")
        if not due_datetime or not isinstance(due_datetime, str):
            raise ValueError("Дата и время обязательны и должны быть строкой")

        try:
            # Проверка формата даты
            datetime.datetime.fromisoformat(due_datetime)
        except ValueError:
            raise ValueError(f"Некорректный формат даты: {due_datetime}. Ожидается ISO 8601")

        try:
            sql = "INSERT INTO reminders (title, description, due_datetime, status) VALUES (?, ?, ?, ?)"
            self.cursor.execute(sql, (title, description or "", due_datetime, "Ожидает"))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"Ошибка при добавлении напоминания: {e}")

    def get_reminders(self, status_filter: Optional[str] = None, sort_order: str = "ASC") -> List[Tuple]:
        """
        Получает список напоминаний из базы данных.

        :param status_filter: Фильтр по статусу. Если None, возвращает все.
        :param sort_order: Порядок сортировки по дате ('ASC' или 'DESC').
        :return: Список кортежей с данными напоминаний.
        :raises ValueError: Если параметры невалидны.
        :raises RuntimeError: При ошибках базы данных.
        """
        if not self.cursor:
            raise RuntimeError("Курсор базы данных не инициализирован")

        # Валидация параметров
        if sort_order not in ("ASC", "DESC"):
            raise ValueError("Параметр sort_order должен быть 'ASC' или 'DESC'")

        if status_filter and status_filter != "Все" and status_filter not in ("Ожидает", "Выполнено", "Просрочено", "Отменено"):
            raise ValueError(f"Некорректный статус фильтра: {status_filter}")

        with self.lock:
            try:
                sql = "SELECT * FROM reminders"
                params = []
                if status_filter and status_filter != "Все":
                    sql += " WHERE status = ?"
                    params.append(status_filter)

                sql += " ORDER BY due_datetime " + sort_order
                self.cursor.execute(sql, params)
                return self.cursor.fetchall()
            except sqlite3.Error as e:
                raise RuntimeError(f"Ошибка при получении напоминаний: {e}")

    def update_reminder(self, reminder_id: int, title: str, description: str, due_datetime: str):
        """
        Обновляет данные существующего напоминания.

        :param reminder_id: ID напоминания для обновления.
        :param title: Новый заголовок.
        :param description: Новое описание.
        :param due_datetime: Новая дата и время.
        :raises ValueError: Если входные данные невалидны.
        :raises RuntimeError: При ошибках базы данных.
        """
        if not self.conn:
            raise RuntimeError("Соединение с базой данных не установлено")

        # Валидация входных данных
        if not title or not isinstance(title, str):
            raise ValueError("Заголовок обязателен и должен быть строкой")
        if reminder_id is None or not isinstance(reminder_id, int) or reminder_id <= 0:
            raise ValueError("Некорректный ID напоминания")
        if not due_datetime or not isinstance(due_datetime, str):
            raise ValueError("Дата и время обязательны и должны быть строкой")

        try:
            # Проверка формата даты
            datetime.datetime.fromisoformat(due_datetime)
        except ValueError:
            raise ValueError(f"Некорректный формат даты: {due_datetime}. Ожидается ISO 8601")

        try:
            sql = "UPDATE reminders SET title = ?, description = ?, due_datetime = ? WHERE id = ?"
            self.cursor.execute(sql, (title, description or "", due_datetime, reminder_id))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"Ошибка при обновлении напоминания: {e}")

    def update_reminder_status(self, reminder_id: int, status: str):
        """
        Обновляет статус напоминания.

        :param reminder_id: ID напоминания.
        :param status: Новый статус.
        """
        if not self.conn:
            return
        try:
            sql = "UPDATE reminders SET status = ? WHERE id = ?"
            self.cursor.execute(sql, (status, reminder_id))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении статуса: {e}")

    def delete_reminder(self, reminder_id: int):
        """
        Удаляет напоминание из базы данных.

        :param reminder_id: ID напоминания для удаления.
        """
        if not self.conn:
            return
        try:
            sql = "DELETE FROM reminders WHERE id = ?"
            self.cursor.execute(sql, (reminder_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при удалении напоминания: {e}")

    def update_overdue_reminders(self):
        """
        Обновляет статус ожидающих напоминаний на 'Просрочено', если их время истекло.
        Добавляет буферное время (2 минуты) для корректного срабатывания уведомлений.

        :raises RuntimeError: При ошибках базы данных.
        """
        if not self.conn:
            raise RuntimeError("Соединение с базой данных не установлено")

        with self.lock:
            try:
                # Буферное время: помечаем просроченными только те напоминания,
                # которые просрочены более чем на 2 минуты
                buffer_time = datetime.datetime.now() - datetime.timedelta(minutes=2)
                buffer_iso = buffer_time.isoformat()
                sql = "UPDATE reminders SET status = 'Просрочено' WHERE status = 'Ожидает' AND due_datetime < ?"
                updated_count = self.cursor.execute(sql, (buffer_iso,)).rowcount
                self.conn.commit()
                if updated_count > 0:
                    print(f"[DEBUG] Помечено просроченными {updated_count} напоминаний")
            except sqlite3.Error as e:
                self.conn.rollback()
                raise RuntimeError(f"Ошибка при обновлении просроченных напоминаний: {e}")

    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        # Добавление нового напоминания
        dt = (datetime.datetime.now() + datetime.timedelta(minutes=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание", "Это тестовое сообщение", dt)
        print(f"Добавлено напоминание с ID: {r_id}")

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")



    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

    def create_demo_data(self):
        """
        Создает демонстрационные данные для приложения.
        Очищает существующие данные и добавляет реальные напоминания.
        """
        print("Создание демонстрационных данных...")
        
        # Очистка существующих данных
        with self.lock:
            try:
                self.cursor.execute("DELETE FROM reminders")
                self.conn.commit()
                print("Старые данные удалены")
            except sqlite3.Error as e:
                print(f"Ошибка при очистке данных: {e}")
                return
        
        # Создание новых напоминаний
        now = datetime.datetime.now()
        
        # 10 реальных напоминаний с разнообразными датами
        reminders_data = [
            {
                "title": "Встреча с клиентом",
                "description": "Обсуждение нового проекта и подписание договора. Подготовить презентацию и коммерческое предложение.",
                "due_time": now - datetime.timedelta(days=3, hours=2)  # 3 дня назад
            },
            {
                "title": "Поход к врачу",
                "description": "Плановый осмотр у терапевта. Не забыть взять медкарту и результаты анализов.",
                "due_time": now - datetime.timedelta(days=1, hours=5, minutes=30)  # Вчера
            },
            {
                "title": "Оплатить коммунальные услуги",
                "description": "Оплата за электричество, воду и отопление через онлайн-банк или в отделении банка.",
                "due_time": now - datetime.timedelta(days=5, hours=10)  # 5 дней назад
            },
            {
                "title": "Забрать заказ из интернет-магазина",
                "description": "Получить посылку в пункте выдачи. Код получения: 4521. Работает до 21:00.",
                "due_time": now - datetime.timedelta(days=2, hours=4)  # 2 дня назад
            },
            {
                "title": "Созвон с командой разработки",
                "description": "Еженедельное планирование спринта. Обсудить задачи на следующую неделю и прогресс по текущим.",
                "due_time": now + datetime.timedelta(days=3, hours=9, minutes=15)  # Через 3 дня
            },
            {
                "title": "День рождения мамы",
                "description": "Поздравить маму с днем рождения! Подготовить подарок и букет цветов. Не забыть позвонить утром.",
                "due_time": now + datetime.timedelta(days=12, hours=8)  # Через 12 дней
            },
            {
                "title": "Подача отчета в налоговую",
                "description": "Подать квартальную декларацию НДС через электронную подпись. Крайний срок - до 25 числа.",
                "due_time": now + datetime.timedelta(days=15, hours=12)  # Через 15 дней
            },
            {
                "title": "Запись на техосмотр автомобиля",
                "description": "Записаться на диагностику в автосервис. Проверить тормоза, подвеску и световые приборы.",
                "due_time": now + datetime.timedelta(days=7, hours=13, minutes=45)  # Через неделю
            },
            {
                "title": "Покупка продуктов на выходные",
                "description": "Составить список покупок и съездить в супермаркет. Купить продукты для семейного ужина в воскресенье.",
                "due_time": now + datetime.timedelta(days=4, hours=17, minutes=20)  # Через 4 дня
            },
            {
                "title": "Обновление резюме",
                "description": "Актуализировать информацию о работе и навыках. Добавить последние проекты и достижения.",
                "due_time": now + datetime.timedelta(days=10, hours=20)  # Через 10 дней
            }
        ]
        
        created_ids = []
        
        for reminder_data in reminders_data:
            reminder_id = self.add_reminder(
                title=reminder_data["title"],
                description=reminder_data["description"],
                due_datetime=reminder_data["due_time"].isoformat()
            )
            created_ids.append(reminder_id)
            print(f"[OK] Создано: {reminder_data['title']} (ID: {reminder_id})")
        
        # Помечаем первые 4 напоминания как выполненные (те, что в прошлом)
        completed_titles = [
            "Встреча с клиентом",
            "Поход к врачу",
            "Оплатить коммунальные услуги",
            "Забрать заказ из интернет-магазина"
        ]
        
        for i in range(min(4, len(created_ids))):
            reminder_id = created_ids[i]
            self.update_reminder_status(reminder_id, "Выполнено")
            print(f"[OK] Помечено как выполненное: {completed_titles[i]} (ID: {reminder_id})")
        
        # Статистика
        all_reminders = self.get_reminders()
        completed_count = len([r for r in all_reminders if r[4] == "Выполнено"])
        pending_count = len([r for r in all_reminders if r[4] == "Ожидает"])
        
        print(f"\n=== Итоговая статистика ===")
        print(f"Всего напоминаний: {len(all_reminders)}")
        print(f"Ожидает выполнения: {pending_count}")
        print(f"Выполнено: {completed_count}")
        print("[SUCCESS] База данных заполнена демонстрационными данными!")

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")
        print("\nТестовая база данных удалена.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")


        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")



    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")
        print("\nТестовая база данных удалена.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")



    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

    def close(self):
        """
        Закрывает соединение с базой данных.
        """
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Пример использования и тестирования
    db = Database("test_reminders.db")
    if db.conn:
        print("База данных успешно инициализирована.")

        # Добавление
        dt1 = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        r_id = db.add_reminder("Тестовое напоминание 1", "Описание для теста 1", dt1)
        print(f"Добавлено напоминание с ID: {r_id}")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")
        print("\nТестовая база данных удалена.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")

        dt2 = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        r_id2 = db.add_reminder("Просроченное", "Это должно стать просроченным", dt2)
        print(f"Добавлено напоминание с ID: {r_id2}")

        # Получение всех
        print("\nВсе напоминания:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление просроченных
        db.update_overdue_reminders()
        print("\nПосле обновления просроченных:")
        reminders = db.get_reminders()
        for r in reminders:
            print(r)

        # Обновление статуса
        if r_id:
            db.update_reminder_status(r_id, "Выполнено")
            print(f"\nСтатус напоминания {r_id} обновлен.")

        # Получение выполненных
        print("\nВыполненные напоминания:")
        reminders = db.get_reminders(status_filter="Выполнено")
        for r in reminders:
            print(r)

        # Удаление
        if r_id:
            db.delete_reminder(r_id)
            print(f"\nНапоминание {r_id} удалено.")

        # Проверка удаления
        print("\nВсе напоминания после удаления:")
        reminders = db.get_reminders()
        print(reminders)

        db.close()
        # Очистка тестовой БД
        import os
        os.remove("test_reminders.db")
        print("\nТестовая база данных удалена.")



