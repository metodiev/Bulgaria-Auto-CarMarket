from app.connectors.gated import GatedConnector


class BazarBgConnector(GatedConnector):
    slug = "bazar-bg"
    base_url = "https://www.bazar.bg/"
    access_status = "needs_permission"
    access_reason = (
        "robots.txt забранява /обяви/ и редица region-specific пътища за обяви. "
        "Условията не бяха намерени на началната страница. Нужен е ръчен преглед "
        "и потвърждение на разрешения достъп преди включване."
    )
