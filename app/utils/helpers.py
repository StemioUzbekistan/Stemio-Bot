from datetime import datetime

def calculate_age(dob_string: str) -> int | None:
    """Рассчитывает возраст по строке с датой рождения (ДД.ММ.ГГГГ)."""
    if not dob_string or '.' not in dob_string:
        return None
    try:
        birth_date = datetime.strptime(dob_string, '%d.%m.%Y')
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except (ValueError, TypeError):
        return None