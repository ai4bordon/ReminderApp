import os
from PIL import Image, ImageDraw

def create_icon():
    """
    Создает и сохраняет файл иконки 'assets/icon.ico' для уведомлений и трея.
    """
    # Создаем директорию, если ее нет
    if not os.path.exists("assets"):
        os.makedirs("assets")

    # Параметры иконки
    img_size = (64, 64)
    bg_color = (255, 255, 255, 0)  # Прозрачный фон
    circle_color = "#1F6AA5"      # Цвет круга (в стиле customtkinter)
    
    # Создаем изображение
    img = Image.new('RGBA', img_size, bg_color)
    draw = ImageDraw.Draw(img)

    # Рисуем простой круг в центре как иконку
    padding = 10
    draw.ellipse(
        (padding, padding, img_size[0] - padding, img_size[1] - padding),
        fill=circle_color,
        outline=circle_color
    )
    
    # Сохраняем файл в формате .ico
    icon_path = "assets/icon.ico"
    # Указываем формат и размеры для .ico файла
    img.save(icon_path, format='ICO', sizes=[(32, 32), (48, 48), (64, 64)])
    print(f"Иконка успешно создана и сохранена в '{icon_path}'")

if __name__ == "__main__":
    create_icon()