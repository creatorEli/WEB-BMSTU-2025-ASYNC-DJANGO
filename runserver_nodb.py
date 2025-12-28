#!/usr/bin/env python
"""
Кастомный запуск сервера Django без проверки базы данных и моделей.
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def main():
    """Основная функция запуска."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'async_calculator.settings')
    
    # Отключаем проверку готовности приложений
    from django.apps import apps
    apps.ready = True
    
    # Модифицируем аргументы командной строки для запуска сервера без проверок
    sys.argv = [sys.argv[0], 'runserver', '0.0.0.0:8085', '--noreload', '--skip-checks']
    
    # Запускаем сервер
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()