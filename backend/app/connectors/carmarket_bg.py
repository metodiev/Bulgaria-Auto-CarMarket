from app.connectors.gated import GatedConnector


class CarMarketBgConnector(GatedConnector):
    slug = "carmarket-bg"
    base_url = "https://carmarket.bg/"
    access_status = "needs_permission"
    access_reason = (
        "robots.txt разрешава достъп, но Общите условия (т. 7.5 и т. 10.1) "
        "забраняват копиране и разпространение на съдържание за търговски цели "
        "без писмено съгласие. Нужно е изрично разрешение."
    )
