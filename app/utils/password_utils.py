from pathlib import Path
from app.schemas.schemas import UserCreate

# Допустимые спецсимволы для паролей
SPECIAL_CHARS = '!@#$%^&*()_-+=№;%:?*'

def password_check(user: UserCreate) -> bool:
    """Проверка сложности пароля и его связи с именем пользователя.

    Возвращает True, если пароль достаточно надёжный, иначе False.
    """
    password = user.password

    # Длина пароля
    if not (8 <= len(password) <= 40):
        return False

    # Пароль не должен содержать имя/фамилию
    try:
        name_parts = user.full_name.split()
        if len(name_parts) < 1:
            return False  # Пустое имя недопустимо
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        if first_name and first_name in password:
            return False
        if last_name and last_name in password:
            return False
    except Exception:
        # На всякий случай не пропускаем странные случаи
        return False

    # Обязательное наличие спецсимвола
    has_special = any(char in SPECIAL_CHARS for char in password)
    if not has_special:
        return False

    # Количество букв (верхний + нижний регистр)
    upper_count = sum(1 for char in password if char.isupper())
    lower_count = sum(1 for char in password if char.islower())
    if upper_count + lower_count <= 2:
        return False

    # Проверка по списку самых популярных / слабых паролей,
    # если рядом с этим модулем есть файл top_passwords.txt
    try:
        passwords_file = Path(__file__).with_name("top_passwords.txt")
        if passwords_file.exists():
            with passwords_file.open("r", encoding="utf-8") as f:
                weak_passwords = {line.strip() for line in f}
            if password in weak_passwords:
                return False
    except Exception:
        # Если что-то пошло не так при чтении файла — не блочим создание пользователя
        pass

    return True
