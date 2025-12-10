import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import time
import random
import requests
import json

from concurrent import futures

logger = logging.getLogger(__name__)


CALLBACK_URL = "http://localhost:8084/api/travel_time"

AUTH_TOKEN = "12345678"

executor = futures.ThreadPoolExecutor(max_workers=1)


def calculate_time_travel(distance: int, biom: str, armies_data: list) -> tuple[int, int, int]:
    """
    Функция расчета времени в пути (аналогичная Go-версии)
    Возвращает: (min_days, max_days, chronical_days) или None при ошибке
    """
    min_speed = float('inf')
    max_speed = -1
    chronicle_speed = 0
    
    # Маппинг биомов на соответствующие поля скорости
    biom_speed_mapping = {
        'Plain': ('MinPlainSpeed', 'MaxPlainSpeed'),
        'Desert': ('MinDesertSpeed', 'MaxDesertSpeed'),
        'River': ('MinRiverSpeed', 'MaxRiverSpeed'),
        #('Forest',): ('MinForestSpeed', 'MaxForestSpeed'),
        'Mount': ('MinMountSpeed', 'MaxMountSpeed'),
        'Forest': ('MinForestSpeed', 'MaxForestSpeed'),
    }
    
    if biom not in biom_speed_mapping:
        logger.error(f"Неизвестный биом: {biom}")
        return None
    
    min_key, max_key = biom_speed_mapping[biom]
    
    for army_data in armies_data:
        army_min_speed = army_data.get(min_key, 0)
        army_max_speed = army_data.get(max_key, 0)
        army_chronicle = army_data.get('KmPerDayChronical', 0)
        
        if army_min_speed < min_speed:
            min_speed = army_min_speed
            max_speed = army_max_speed
            chronicle_speed = army_chronicle
    
    if min_speed == float('inf') or max_speed == -1 or min_speed <= 0 or max_speed <= 0:
        logger.error(f"Некорректные данные скорости: min={min_speed}, max={max_speed}")
        return None
    
    # Расчет дней
    chronical_days = 0
    if chronicle_speed != 0:
        chronical_days = int(math.ceil(distance / chronicle_speed))
    
    min_days = int(math.ceil(distance / max_speed))
    max_days = int(math.ceil(distance / min_speed))
    
    return min_days, max_days, chronical_days



# def health_check(request):
    """
    Health check endpoint для мониторинга
    """
    serializer = StatusResponseSerializer({
        'status': 'ok',
        'service': 'django-async-calculator',
        'timestamp': timezone.now()
    })
    
    return Response(serializer.data)

from typing import Tuple, Optional
import math

def calculate_time_of_army(calc_data):
    """Расчет времени перехода армии с обработкой ошибок"""
    try:
        logger.info(f"Начало расчета для TtID={calc_data.get('TtID')}")
        
        # Имитация задержки
        delay = random.uniform(5, 10)
        time.sleep(delay)
        
        # Извлечение данных
        travel_time_id = calc_data.get('TtID')
        distance = calc_data.get('DistanceTT')
        biom = calc_data.get('ChosenBiomTT')
        armies = calc_data.get('Armies', [])
        
        if not all([travel_time_id, distance, biom, armies]):
            return {
                "travel_time_id": travel_time_id,
                "success": False,
                "error_message": "Не все обязательные поля предоставлены"
            }
        
        # Выполнение расчета
        result = calculate_time_travel(distance, biom, armies)
        
        if result is None:
            return {
                "travel_time_id": travel_time_id,
                "success": False,
                "error_message": "Ошибка расчета: некорректные данные"
            }
        
        min_days, max_days, chronical_days = result
        
        # Случайный успех/неуспех (имитация реальных условий)
        is_success = random.random() < 0.8
        
        if is_success:
            return {
                "travel_time_id": travel_time_id,
                "TtID": travel_time_id,  # Дублируем для обратной совместимости
                "success": True,
                "min_days": min_days,
                "max_days": max_days,
                "chronical_days": chronical_days
            }
        else:
            return {
                "travel_time_id": travel_time_id,
                "success": False,
                "error_message": "Расчет завершился неудачно (случайная ошибка)"
            }
            
    except Exception as e:
        logger.error(f"Ошибка в calculate_time_of_army: {e}")
        return {
            "travel_time_id": calc_data.get('TtID'),
            "success": False,
            "error_message": f"Внутренняя ошибка сервера: {str(e)}"
        }


def calc_callback(task):
    """Callback функция для отправки результатов в Go сервис"""
    try:
        # Получаем результат выполнения задачи
        result = task.result()
        logger.info(f"Результат расчета: {result}")
        
        # Проверяем, что результат содержит ожидаемые данные
        if not isinstance(result, dict):
            logger.error(f"Некорректный формат результата: {result}")
            return
            
        # Формируем данные для отправки в Go
        travel_time_id = result.get("travel_time_id") or result.get("TtID")
        
        if not travel_time_id:
            logger.error("Не найден travel_time_id в результате")
            return
            
        # Определяем успешность расчета
        success = result.get("success", False)
        
        # Формируем тело запроса
        callback_data = {
            "travel_time_id": travel_time_id,
            "success": success,
            "token": AUTH_TOKEN  # Простая авторизация
        }
        
        # Добавляем результаты если расчет успешен
        if success and result.get("min_days") is not None:
            callback_data.update({
                "result_min_tt": result["min_days"],
                "result_max_tt": result["max_days"],
                "result_chronical": result["chronical_days"]
            })
        else:
            # Добавляем сообщение об ошибке
            error_msg = result.get("error_message", "Расчет завершился неудачно")
            callback_data["error_message"] = error_msg
        
        # URL для callback (должен соответствовать Go сервису)
        callback_url = f"{CALLBACK_URL}/{travel_time_id}/update_calc"
        
        # Отправляем результаты в Go сервис
        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                callback_url, 
                json=callback_data, 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Callback успешно отправлен для travel_time_id={travel_time_id}")
            else:
                logger.error(f"Ошибка отправки callback: статус {response.status_code}, ответ: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Ошибка сети при отправке callback: {e}")
            
    except futures.CancelledError:
        logger.warning("Задача расчета была отменена")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в callback: {e}")
    


@api_view(['POST'])
def calculate_time(request):
    if "Travel_time" not in request.data.keys():
        return Response(
            {"error": "поле travel_time обязательно"},
            status=status.HTTP_400_BAD_REQUEST
        )
    calc = request.data["Travel_time"]
    logger.error(f"calc: {calc}")

    #fff_value = request.data.get('fff', [''])[0]
    # datar = json.loads(fff_value)
    # fff_dict = request.data.get('fff')  
    # if fff_dict and isinstance(fff_dict, dict):
    #     hello_value = fff_dict.get('hello')  # 'world'
    #     print(hello_value)

    if "TtID" in calc and "ChosenBiomTT" in calc and "DistanceTT" in calc:
        task = executor.submit(calculate_time_of_army, calc)
        task.add_done_callback(calc_callback)
    else:
        return Response(
            {"error": "поля TtID ChosenBiomTT DistanceTT обязательно"},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"message": "расчет времени перехода армии начат!"},
        status=status.HTTP_200_OK
    )