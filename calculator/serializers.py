from rest_framework import serializers


class CalculationRequestSerializer(serializers.Serializer):
    """Сериализатор для входящих запросов на расчет"""
    travel_time_id = serializers.IntegerField(min_value=1)
    distance = serializers.IntegerField(min_value=1)
    biom = serializers.ChoiceField(choices=[
        ('Plain', 'Равнина'),
        ('Desert', 'Пустыня'),
        ('River', 'Река'),
        ('Forest', 'Лес'),
        ('Mount', 'Горы'),
    ])
    creator_id = serializers.IntegerField(min_value=1)
    moderator_id = serializers.IntegerField(required=False, allow_null=True)
    armies = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_armies(self, value):
        """Дополнительная валидация армий"""
        from .validators import CalculationValidator
        
        for i, army in enumerate(value):
            army_errors = CalculationValidator._validate_army(army, i)
            if army_errors:
                raise serializers.ValidationError(army_errors)
        
        return value


class CalculationResponseSerializer(serializers.Serializer):
    """Сериализатор для ответов расчета"""
    travel_time_id = serializers.IntegerField()
    success = serializers.BooleanField()
    result_min_tt = serializers.IntegerField(required=False, allow_null=True)
    result_max_tt = serializers.IntegerField(required=False, allow_null=True)
    result_chronical = serializers.IntegerField(required=False, allow_null=True)
    error_message = serializers.CharField(required=False, allow_blank=True)


class StatusResponseSerializer(serializers.Serializer):
    """Сериализатор для ответов статуса"""
    status = serializers.CharField()
    service = serializers.CharField()
    timestamp = serializers.DateTimeField()