from app.connectors.gated import GatedConnector


class OlxBgConnector(GatedConnector):
    slug = "olx-bg"
    base_url = "https://www.olx.bg/"
    access_status = "blocked"
    access_reason = (
        "Заявката към robots.txt връща HTTP 403 от CloudFront. Автоматизираният "
        "достъп е блокиран и не се заобикаля."
    )
