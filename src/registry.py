from typing import Dict
from cards import CardTemplate, TunnelCardTemplate, CardOpenings, Direction

class TemplateRegistry:
    """
    Глобальный справочник всех карт игры.
    Загружается один раз при старте.
    """
    def __init__(self):
        self.templates: Dict[str, CardTemplate] = {}

    def register(self, template: CardTemplate):
        self.templates[template.id] = template

    def get(self, template_id: str) -> CardTemplate:
        if template_id not in self.templates:
            raise ValueError(f"Шаблон {template_id} не найден в реестре!")
        return self.templates[template_id]

# Глобальный экземпляр для удобства
# (В будущем можно вынести инициализацию в отдельный загрузчик)
REGISTRY = TemplateRegistry()