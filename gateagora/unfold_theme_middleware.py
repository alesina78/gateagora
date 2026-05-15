# Salve este arquivo como: gateagora/unfold_theme_middleware.py

class UnfoldThemeMiddleware:
    """
    Lê o cookie gate-theme e injeta a preferência de tema do Unfold
    na sessão, para que o admin Django siga o mesmo tema do dashboard.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        gate_theme = request.COOKIES.get("gate-theme", "zaino")
        # "tordilho" = claro, "zaino" = escuro
        unfold_theme = "light" if gate_theme == "tordilho" else "dark"
        # O Unfold lê a preferência da sessão com a chave "theme"
        if request.session.get("theme") != unfold_theme:
            request.session["theme"] = unfold_theme
        response = self.get_response(request)
        return response
