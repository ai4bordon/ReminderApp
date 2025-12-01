import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
from PIL import Image
from pystray import Icon as pystray_Icon, MenuItem as pystray_MenuItem
import threading
import calendar

from database import Database
from notifications import send_notification

# Глобальная переменная для иконки в трее, чтобы избежать сборки мусора
tray_icon = None

class DateTimePickerWidget(ctk.CTkFrame):
    """Виджет для выбора даты и времени с календарем"""
    
    def __init__(self, master, initial_datetime=None):
        super().__init__(master)
        self.current_month = datetime.now().month
        self.current_year = datetime.now().year
        self.selected_date = None
        
        # Устанавливаем начальную дату
        if initial_datetime:
            self.current_month = initial_datetime.month
            self.current_year = initial_datetime.year
            self.selected_date = initial_datetime.date()
        
        self.setup_calendar_ui()
        self.refresh_calendar()
        
    def setup_calendar_ui(self):
        """Создает интерфейс календаря"""
        # Заголовок с навигацией по месяцам
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        self.prev_button = ctk.CTkButton(header_frame, text="<", width=30, command=self.prev_month)
        self.prev_button.pack(side="left", padx=5)
        
        self.month_label = ctk.CTkLabel(header_frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.month_label.pack(side="left", expand=True, fill="x")
        
        self.next_button = ctk.CTkButton(header_frame, text=">", width=30, command=self.next_month)
        self.next_button.pack(side="right", padx=5)
        
        # Дни недели
        weekdays_frame = ctk.CTkFrame(self)
        weekdays_frame.pack(fill="x", padx=5)
        
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, day in enumerate(weekdays):
            label = ctk.CTkLabel(weekdays_frame, text=day, font=ctk.CTkFont(weight="bold"))
            label.grid(row=0, column=i, padx=2, pady=2, sticky="ew")
            weekdays_frame.grid_columnconfigure(i, weight=1)
        
        # Календарная сетка
        self.calendar_frame = ctk.CTkFrame(self)
        self.calendar_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Фрейм для выбора времени
        time_frame = ctk.CTkFrame(self)
        time_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(time_frame, text="Время:").pack(side="left", padx=5)
        
        # Спиннеры для часов и минут
        self.hour_var = ctk.StringVar(value="12")
        self.minute_var = ctk.StringVar(value="00")
        
        hour_frame = ctk.CTkFrame(time_frame)
        hour_frame.pack(side="left", padx=5)
        
        self.hour_entry = ctk.CTkEntry(hour_frame, textvariable=self.hour_var, width=50)
        self.hour_entry.pack(side="left")
        
        ctk.CTkLabel(time_frame, text=":").pack(side="left", padx=2)
        
        minute_frame = ctk.CTkFrame(time_frame)
        minute_frame.pack(side="left", padx=5)
        
        self.minute_entry = ctk.CTkEntry(minute_frame, textvariable=self.minute_var, width=50)
        self.minute_entry.pack(side="left")
        
    def prev_month(self):
        """Переход к предыдущему месяцу"""
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.refresh_calendar()
        
    def next_month(self):
        """Переход к следующему месяцу"""
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.refresh_calendar()
        
    def refresh_calendar(self):
        """Обновляет отображение календаря"""
        # Очищаем старые кнопки
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()
        
        # Обновляем заголовок
        month_name = calendar.month_name[self.current_month]
        self.month_label.configure(text=f"{month_name} {self.current_year}")
        
        # Получаем данные календаря
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        
        # Создаем кнопки дней
        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    # Пустая ячейка
                    label = ctk.CTkLabel(self.calendar_frame, text="")
                    label.grid(row=week_num, column=day_num, padx=1, pady=1, sticky="ew")
                else:
                    # Кнопка дня
                    is_selected = (self.selected_date and
                                 self.selected_date.day == day and
                                 self.selected_date.month == self.current_month and
                                 self.selected_date.year == self.current_year)
                    
                    fg_color = ("gray75", "gray25") if is_selected else None
                    
                    day_button = ctk.CTkButton(
                        self.calendar_frame,
                        text=str(day),
                        width=40,
                        height=35,
                        fg_color=fg_color,
                        command=lambda d=day: self.select_date(d)
                    )
                    day_button.grid(row=week_num, column=day_num, padx=1, pady=1, sticky="ew")
                
                self.calendar_frame.grid_columnconfigure(day_num, weight=1)
    
    def select_date(self, day):
        """Выбирает дату"""
        self.selected_date = datetime(self.current_year, self.current_month, day).date()
        self.refresh_calendar()
        
    def get_selected_datetime(self):
        """Возвращает выбранную дату и время как datetime объект"""
        if not self.selected_date:
            return None
            
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                return None
                
            return datetime.combine(self.selected_date, datetime.min.time().replace(hour=hour, minute=minute))
        except (ValueError, AttributeError):
            return None

class ReminderDialog(ctk.CTkToplevel):
    """
    Диалоговое окно для добавления или редактирования напоминания.
    """
    def __init__(self, master, db: Database, reminder_data=None):
        super().__init__(master)
        self.db = db
        self.reminder_data = reminder_data
        self.result = None

        is_edit = self.reminder_data is not None
        title = "Редактировать напоминание" if is_edit else "Добавить напоминание"
        self.title(title)
        self.geometry("450x650")  # Увеличиваем размер для календаря
        self.transient(master)
        self.grab_set()

        # --- Виджеты ---
        self.title_label = ctk.CTkLabel(self, text="Заголовок:")
        self.title_label.pack(padx=20, pady=(10, 0), anchor="w")
        self.title_entry = ctk.CTkEntry(self, width=360)
        self.title_entry.pack(padx=20, pady=5)

        self.desc_label = ctk.CTkLabel(self, text="Описание:")
        self.desc_label.pack(padx=20, pady=0, anchor="w")
        self.desc_textbox = ctk.CTkTextbox(self, height=100, width=360)
        self.desc_textbox.pack(padx=20, pady=5)

        self.due_label = ctk.CTkLabel(self, text="Выберите дату и время:")
        self.due_label.pack(padx=20, pady=(10, 0), anchor="w")
        
        # Календарный виджет - создаем с учетом режима редактирования
        initial_dt = None
        if is_edit:
            initial_dt = datetime.fromisoformat(self.reminder_data[3])
            
        self.datetime_picker = DateTimePickerWidget(self, initial_datetime=initial_dt)
        self.datetime_picker.pack(padx=20, pady=5, fill="both", expand=True)

        self.save_button = ctk.CTkButton(self, text="Сохранить", command=self.save)
        self.save_button.pack(padx=20, pady=20)

        # --- Заполнение данных при редактировании ---
        if is_edit:
            self.title_entry.insert(0, self.reminder_data[1])
            self.desc_textbox.insert("1.0", self.reminder_data[2] or "")

    def save(self):
        """Сохраняет данные напоминания."""
        title = self.title_entry.get().strip()
        description = self.desc_textbox.get("1.0", "end-1c").strip()
        selected_datetime = self.datetime_picker.get_selected_datetime()

        if not title:
            messagebox.showerror("Ошибка", "Заголовок обязателен.", parent=self)
            return

        if not selected_datetime:
            messagebox.showerror("Ошибка", "Выберите дату и введите корректное время (ЧЧ:ММ).", parent=self)
            return

        due_datetime = selected_datetime.isoformat()

        # Проверяем, что дата не в прошлом
        try:
            due_dt = datetime.fromisoformat(due_datetime)
            if due_dt < datetime.now():
                if not messagebox.askyesno("Предупреждение", "Указанная дата находится в прошлом. Продолжить?", parent=self):
                    return
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректная дата после преобразования.", parent=self)
            return

        if self.reminder_data: # Редактирование
            self.db.update_reminder(self.reminder_data[0], title, description, due_datetime)
        else: # Добавление
            self.db.add_reminder(title, description, due_datetime)
        
        self.result = True
        self.destroy()


class App(ctk.CTk):
    """
    Основной класс приложения.
    """
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

        self.title("Напоминалка")
        self.geometry("1000x600")
        ctk.set_appearance_mode("System")

        # --- Переменные состояния ---
        self.current_filter = ctk.StringVar(value="Все")
        self.sort_order = ctk.StringVar(value="Сначала новые")
        self.selected_reminder_id = None
        self.selected_frame = None
        self.active_notification_id = None  # ID активного уведомления для отсрочки

        # --- Цвета статусов ---
        self.STATUS_COLORS = {
            "Ожидает": "#FFFFFF",
            "Выполнено": "#32a852",
            "Просрочено": "#c94444",
            "Отменено": "#808080"
        }

        # --- Настройка сетки ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Левая панель управления ---
        self.control_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.control_frame.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self.control_frame.grid_rowconfigure(7, weight=1) # Пустая строка для растягивания

        self.add_button = ctk.CTkButton(self.control_frame, text="Добавить напоминание", command=self.open_add_dialog)
        self.add_button.grid(row=0, column=0, padx=20, pady=20)

        self.filter_label = ctk.CTkLabel(self.control_frame, text="Фильтр по статусу:")
        self.filter_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.filter_menu = ctk.CTkSegmentedButton(self.control_frame, 
                                                  values=["Все", "Ожидает", "Выполнено", "Просрочено"],
                                                  command=lambda v: self.refresh_reminders_list(),
                                                  variable=self.current_filter)
        self.filter_menu.grid(row=2, column=0, padx=20, pady=5, sticky="w")

        self.sort_label = ctk.CTkLabel(self.control_frame, text="Сортировка:")
        self.sort_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.sort_menu = ctk.CTkOptionMenu(self.control_frame, 
                                           values=["Сначала новые", "Сначала старые"],
                                           command=lambda v: self.refresh_reminders_list(),
                                           variable=self.sort_order)
        self.sort_menu.grid(row=4, column=0, padx=20, pady=5, sticky="nw")

        self.refresh_button = ctk.CTkButton(self.control_frame, text="Обновить", command=self.refresh_reminders_list)
        self.refresh_button.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        # --- Панель быстрых действий ---
        self.quick_actions_frame = ctk.CTkFrame(self.control_frame)
        self.quick_actions_frame.grid(row=6, column=0, padx=20, pady=(20, 0), sticky="nsew")
        self.quick_actions_frame.grid_columnconfigure((0, 1), weight=1)

        quick_actions_label = ctk.CTkLabel(self.quick_actions_frame, text="Быстрые действия:")
        quick_actions_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="w")

        self.test_notification_button = ctk.CTkButton(
            self.quick_actions_frame,
            text="Тест уведомления",
            command=self._send_test_notification,
            state="disabled"
        )
        self.test_notification_button.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.snooze_45_btn = ctk.CTkButton(self.quick_actions_frame, text="Отложить на 45 мин.", command=lambda: self._snooze_reminder(45))
        self.snooze_45_btn.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="ew")
        
        self.snooze_15_btn = ctk.CTkButton(self.quick_actions_frame, text="Отложить на 15 мин.", command=lambda: self._snooze_reminder(15))
        self.snooze_15_btn.grid(row=2, column=1, padx=(5, 10), pady=5, sticky="ew")
        
        self.snooze_30_btn = ctk.CTkButton(self.quick_actions_frame, text="Отложить на 30 мин.", command=lambda: self._snooze_reminder(30))
        self.snooze_30_btn.grid(row=3, column=0, padx=(10, 5), pady=5, sticky="ew")
        
        self.snooze_60_btn = ctk.CTkButton(self.quick_actions_frame, text="Отложить на 1 час", command=lambda: self._snooze_reminder(60))
        self.snooze_60_btn.grid(row=3, column=1, padx=(5, 10), pady=5, sticky="ew")
        
        # Изначально кнопки отсрочки отключены
        self._set_snooze_buttons_state(False)

        # --- Правая панель со списком ---
        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Список напоминаний")
        self.list_frame.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

        # --- Системный трей ---
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.setup_tray()

        # --- Первоначальное отображение ---
        self.refresh_reminders_list()

    def setup_tray(self):
        """Настраивает иконку в системном трее."""
        global tray_icon
        try:
            # Попытка загрузить иконку. Если не получится, трей не будет создан.
            image = Image.open("assets/icon.ico")
        except FileNotFoundError:
            print("ВНИМАНИЕ: Файл иконки 'assets/icon.ico' не найден. Функционал трея будет отключен.")
            image = None

        if image:
            menu = (
                pystray_MenuItem('Показать', self.show_from_tray, default=True),
                pystray_MenuItem('Создать', self.open_add_dialog),
                pystray_MenuItem('Выход', self.quit_app)
            )
            tray_icon = pystray_Icon("Напоминалка", image, "Напоминалка", menu)
            
            # Запускаем иконку в отдельном потоке, чтобы не блокировать GUI
            threading.Thread(target=tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        """Сворачивает приложение в трей."""
        self.withdraw()

    def show_from_tray(self):
        """Разворачивает приложение из трея."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        """Полностью закрывает приложение."""
        global tray_icon
        if tray_icon:
            tray_icon.stop()
        self.db.close()
        self.destroy()

    def refresh_reminders_list(self):
        """Обновляет список напоминаний в GUI."""
        # Сбрасываем выбор при обновлении
        self.selected_reminder_id = None
        self.selected_frame = None
        self.test_notification_button.configure(state="disabled")

        # Очищаем старый список
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # Получаем данные из БД с учетом фильтров
        status = self.current_filter.get()
        sort = "ASC" if self.sort_order.get() == "Сначала новые" else "DESC"
        reminders = self.db.get_reminders(status_filter=status, sort_order=sort)

        # Создаем виджеты для каждого напоминания
        for i, reminder in enumerate(reminders):
            reminder_id, title, desc, due_str, status = reminder
            
            reminder_frame = ctk.CTkFrame(self.list_frame)
            reminder_frame.pack(fill="x", padx=5, pady=5)
            reminder_frame.grid_columnconfigure(0, weight=1)

            # Привязываем событие клика к фрейму для выбора
            # Также привязываем к дочерним элементам, чтобы клик срабатывал по всей области
            reminder_frame.bind("<Button-1>", lambda event, r=reminder, frame=reminder_frame: self._select_reminder(r, frame))

            # Форматирование даты для отображения
            due_dt = datetime.fromisoformat(due_str)
            due_display = due_dt.strftime('%d.%m.%Y в %H:%M')

            # Основная информация
            info_label = ctk.CTkLabel(reminder_frame, text=f"{title}\n{due_display}", justify="left")
            info_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            info_label.bind("<Button-1>", lambda event, r=reminder, frame=reminder_frame: self._select_reminder(r, frame))

            # Статус
            status_color = self.STATUS_COLORS.get(status, "#FFFFFF")
            status_label = ctk.CTkLabel(reminder_frame, text=status, text_color=status_color, font=ctk.CTkFont(weight="bold"))
            status_label.grid(row=0, column=1, padx=10, pady=5)
            status_label.bind("<Button-1>", lambda event, r=reminder, frame=reminder_frame: self._select_reminder(r, frame))

            # Кнопки управления
            btn_frame = ctk.CTkFrame(reminder_frame, fg_color="transparent")
            btn_frame.grid(row=0, column=2, padx=10, pady=5)

            ctk.CTkButton(btn_frame, text="✏️", width=30, command=lambda r=reminder: self.open_edit_dialog(r)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="🗑️", width=30, command=lambda r_id=reminder_id: self.delete_reminder(r_id)).pack(side="left", padx=2)
            if status == "Ожидает" or status == "Просрочено":
                ctk.CTkButton(btn_frame, text="✔️", width=30, command=lambda r_id=reminder_id: self.update_status(r_id, "Выполнено")).pack(side="left", padx=2)
            if status == "Ожидает":
                ctk.CTkButton(btn_frame, text="❌", width=30, command=lambda r_id=reminder_id: self.update_status(r_id, "Отменено")).pack(side="left", padx=2)

    def open_add_dialog(self):
        """Открывает диалог добавления."""
        self.show_from_tray() # Показываем окно, если оно было в трее
        dialog = ReminderDialog(self, self.db)
        self.wait_window(dialog)
        if dialog.result:
            self.refresh_reminders_list()

    def open_edit_dialog(self, reminder_data):
        """Открывает диалог редактирования."""
        dialog = ReminderDialog(self, self.db, reminder_data=reminder_data)
        self.wait_window(dialog)
        if dialog.result:
            self.refresh_reminders_list()

    def delete_reminder(self, reminder_id: int):
        """Удаляет напоминание после подтверждения."""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить это напоминание?", parent=self):
            self.db.delete_reminder(reminder_id)
            self.refresh_reminders_list()

    def update_status(self, reminder_id: int, status: str):
        """Обновляет статус напоминания."""
        self.db.update_reminder_status(reminder_id, status)
        self.refresh_reminders_list()

    def _snooze_reminder(self, minutes: int):
        """Откладывает активное напоминание на указанное количество минут."""
        if self.active_notification_id is None:
            messagebox.showwarning("Нет активного уведомления",
                                 "Нет активного уведомления для отсрочки.")
            return

        try:
            # Получаем данные активного напоминания
            reminders = self.db.get_reminders()
            active_reminder = None
            for reminder in reminders:
                if reminder[0] == self.active_notification_id:
                    active_reminder = reminder
                    break

            if not active_reminder:
                messagebox.showerror("Ошибка", "Активное напоминание не найдено.")
                self.active_notification_id = None
                self._set_snooze_buttons_state(False)
                return

            # Рассчитываем новое время
            now = datetime.now()
            new_due_time = now + timedelta(minutes=minutes)
            new_due_time_str = new_due_time.isoformat()

            # Обновляем напоминание
            self.db.update_reminder(
                self.active_notification_id,
                active_reminder[1],  # title
                active_reminder[2] + f"\n\nОтложено на {minutes} мин. в {now.strftime('%H:%M:%S')}",  # description
                new_due_time_str
            )

            # Сбрасываем активное уведомление
            self.active_notification_id = None
            self._set_snooze_buttons_state(False)
            
            # Обновляем список
            self.refresh_reminders_list()
            
            messagebox.showinfo("Отсрочка", f"Напоминание отложено на {minutes} минут.")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отложить напоминание: {e}")

    def _set_snooze_buttons_state(self, enabled: bool):
        """Включает или отключает кнопки отсрочки."""
        state = "normal" if enabled else "disabled"
        self.snooze_45_btn.configure(state=state)
        self.snooze_15_btn.configure(state=state)
        self.snooze_30_btn.configure(state=state)
        self.snooze_60_btn.configure(state=state)

    def set_active_notification(self, reminder_id: int):
        """Устанавливает активное уведомление и включает кнопки отсрочки."""
        self.active_notification_id = reminder_id
        self._set_snooze_buttons_state(True)

    def _select_reminder(self, reminder, frame):
        """Обрабатывает выбор напоминания в списке."""
        # Сбрасываем цвет предыдущего выбранного элемента
        if self.selected_frame:
            # Используем get для получения цвета по умолчанию, если он не был установлен
            default_color = ctk.CTkFrame(self).cget("fg_color")
            self.selected_frame.configure(fg_color=default_color)

        # Сохраняем новое выделение (весь объект reminder для простоты)
        self.selected_reminder_id = reminder
        self.selected_frame = frame

        # Выделяем новый элемент цветом
        self.selected_frame.configure(fg_color="#36719F") # Цвет выделения

        # Активируем кнопку "Тест уведомления"
        self.test_notification_button.configure(state="normal")

    def _send_test_notification(self):
        """Отправляет тестовое уведомление для выбранного элемента."""
        if self.selected_reminder_id is not None:
            # Используем доступ по индексам, так как selected_reminder_id - это кортеж
            title = self.selected_reminder_id[1]
            message = self.selected_reminder_id[2]
            send_notification(title, message or "У этого напоминания нет описания.")


if __name__ == '__main__':
    # Для тестирования GUI отдельно
    # Создаем временную БД
    test_db = Database("test_ui.db")
    now = datetime.now()
    test_db.add_reminder("Купить молоко", "Нежирное, 1.5%", (now + timedelta(hours=2)).isoformat())
    test_db.add_reminder("Запись к врачу", "Кардиолог, каб. 302", (now + timedelta(days=1)).isoformat())
    test_db.add_reminder("Просроченная задача", "Это должно было быть сделано вчера", (now - timedelta(days=1)).isoformat())
    test_db.update_overdue_reminders() # Обновляем статус просроченной
    
    app = App(db=test_db)
    app.mainloop()

    # Очистка после закрытия
    import os
    os.remove("test_ui.db")

