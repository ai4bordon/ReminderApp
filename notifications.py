from plyer import notification
import platform
import os
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

def send_notification(title: str, message: str, max_retries: int = 3, reminder_id: int = None, main_app=None):
    """
    Отправляет системное уведомление с принудительным использованием видимых методов.

    :param title: Заголовок уведомления.
    :param message: Текст уведомления.
    :param max_retries: Максимальное количество попыток отправки.
    :param reminder_id: ID напоминания для активации кнопок отсрочки.
    :param main_app: Ссылка на главное приложение для активации кнопок.
    :raises RuntimeError: Если не удалось отправить уведомление после всех попыток.
    """
    if not title or not isinstance(title, str):
        raise ValueError("Заголовок уведомления обязателен и должен быть строкой")

    if not message or not isinstance(message, str):
        raise ValueError("Текст уведомления обязателен и должен быть строкой")

    print(f"[УВЕДОМЛЕНИЕ] ОТПРАВКА: {title}")
    print(f"[СООБЩЕНИЕ] {message}")

    # Активируем кнопки отсрочки если передан ID и приложение
    if reminder_id and main_app and hasattr(main_app, 'set_active_notification'):
        try:
            main_app.set_active_notification(reminder_id)
            print(f"[УВЕДОМЛЕНИЯ] Активированы кнопки отсрочки для напоминания ID: {reminder_id}")
        except Exception as e:
            print(f"[УВЕДОМЛЕНИЯ] Ошибка активации кнопок отсрочки: {e}")

    # ПРИНУДИТЕЛЬНО: Tkinter MessageBox (видимое всплывающее окно)
    if _try_tkinter_notification(title, message):
        print("[SUCCESS] Tkinter уведомление показано")
        return

    # Резерв: Попытка через plyer (может не работать)
    if _try_plyer_notification(title, message, max_retries):
        return

    # Последний резерв: Консольное уведомление с звуком
    _show_console_notification(title, message)
    
def _show_console_notification(title: str, message: str):
    """Показывает консольное уведомление со звуком"""
    print(f"\n{'='*60}")
    print(f"[!] КРИТИЧЕСКОЕ НАПОМИНАНИЕ: {title}")
    print(f">>> {message}")
    print(f"[TIME] {time.strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Звуковой сигнал
    try:
        import winsound
        for i in range(3):  # 3 звуковых сигнала
            winsound.Beep(1000, 300)
            time.sleep(0.1)
    except:
        try:
            for i in range(3):
                print("\a", end="", flush=True)
                time.sleep(0.2)
        except:
            pass

def _try_plyer_notification(title: str, message: str, max_retries: int) -> bool:
    """Попытка отправить уведомление через plyer."""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if platform.system() == "Windows":
                # Получаем абсолютный путь к иконке
                try:
                    icon_path = os.path.abspath("assets/icon.ico")
                    if not os.path.exists(icon_path):
                        icon_path = None
                except:
                    icon_path = None

                notification.notify(
                    title=title,
                    message=message,
                    app_name="Напоминалка",
                    app_icon=icon_path,
                    timeout=15
                )
                print("[OK] Plyer уведомление отправлено успешно")
                return True
            else:
                # Для других ОС
                notification.notify(title=title, message=message, timeout=15)
                print("[OK] Plyer уведомление отправлено успешно")
                return True
        except Exception as e:
            last_error = e
            print(f"[ERR] Plyer попытка {attempt + 1} неудачна: {e}")
            time.sleep(1)
    
    print(f"[ERR] Все попытки plyer неудачны. Последняя ошибка: {last_error}")
    return False

def _try_tkinter_notification(title: str, message: str) -> bool:
    """Показать простое всплывающее окно через messagebox (thread-safe)."""
    try:
        # Используем простой messagebox - он thread-safe и не требует отдельного потока
        messagebox.showinfo(title, message)
        print("[OK] Tkinter messagebox уведомление показано")
        return True
    except Exception as e:
        print(f"[ERR] Tkinter уведомление неудачно: {e}")
        return False

if __name__ == '__main__':
    # Пример для тестирования модуля
    print("Отправка тестового уведомления...")
    send_notification(
        "Проверка связи!",
        "Это тестовое уведомление от приложения 'Напоминалка'."
    )
    print("Тестовое уведомление было отправлено. Проверьте центр уведомлений Windows.")