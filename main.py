import atexit
import sys
from tkinter import messagebox
from database import Database
from ui import App
from scheduler import start_scheduler, check_reminders
from create_icon import create_icon

def main():
    """
    Главная функция для запуска приложения "Напоминалка".
    """
    # 1. Убедиться, что иконка для трея существует
    # Этот вызов создаст иконку, если ее нет.
    create_icon()

    # 2. Инициализация базы данных
    # Используется один экземпляр на все приложение.
    try:
        db = Database()
        print("База данных инициализирована.")
    except Exception as e:
        print(f"Критическая ошибка: Не удалось инициализировать базу данных: {e}")
        messagebox.showerror("Ошибка базы данных", f"Не удалось подключиться к базе данных: {e}")
        sys.exit(1)

    # 3. Создание графического интерфейса
    # GUI получает доступ к экземпляру БД.
    app = App(db=db)
    print("Графический интерфейс создан.")

    # 4. Запуск фонового планировщика с ссылкой на приложение
    # Планировщик будет проверять напоминания каждые 30 секунд.
    scheduler = start_scheduler(db, main_app=app)

    # 5. Первоначальная проверка статусов при запуске
    # Обновляет просроченные и обрабатывает сработавшие напоминания.
    print("Первоначальная проверка напоминаний при запуске...")
    check_reminders(db, main_app=app)

    # 6. Регистрация функции очистки при выходе
    # Гарантирует, что соединение с БД и планировщик будут корректно закрыты.
    atexit.register(lambda: cleanup(app, db, scheduler))

    # 7. Запуск главного цикла приложения
    app.mainloop()

def cleanup(app, db, scheduler):
    """
    Функция для корректного завершения работы приложения.
    """
    print("Завершение работы приложения...")
    if scheduler.running:
        scheduler.shutdown()
        print("Планировщик остановлен.")
    if db.conn:
        db.close()
        print("Соединение с базой данных закрыто.")
    print("Приложение закрыто.")

if __name__ == "__main__":
    main()

