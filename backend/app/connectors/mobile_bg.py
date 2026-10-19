from app.connectors.gated import GatedConnector


class MobileBgConnector(GatedConnector):
    slug = "mobile-bg"
    base_url = "https://www.mobile.bg/"
    access_status = "needs_permission"
    access_reason = (
        "robots.txt разрешава достъп, но Общите условия (чл. 4) определят данните "
        "от сайта като собственост на „Резон“ ООД и допускат търговско ползване "
        "само от упълномощени лица срещу заплащане. Нужно е изрично разрешение."
    )
