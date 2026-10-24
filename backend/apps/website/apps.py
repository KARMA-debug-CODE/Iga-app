from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    """The public site around the app: what the legal pages and the pricing section show, the contact form,
    robots.txt and the sitemap."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.website"
