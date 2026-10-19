from app.connectors.gated import GatedConnector


class AutoBgConnector(GatedConnector):
    slug = "auto-bg"
    base_url = "https://www.auto.bg/"
    access_status = "needs_permission"
    access_reason = (
        "robots.txt разрешава достъп, но Общите условия (чл. 5) определят данните "
        "от сайта като собственост на „Булинфо“ ООД и допускат търговско ползване "
        "само от упълномощени лица срещу заплащане. Нужно е изрично разрешение."
    )
