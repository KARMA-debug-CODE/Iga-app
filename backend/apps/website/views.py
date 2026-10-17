"""The public site around the app: site information, the contact form, robots.txt and the sitemap."""

import logging
from xml.sax.saxutils import escape

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import legal, password_reset
from apps.accounts.throttles import IPThrottle
from apps.core import audit, maintenance, security_log
from apps.core.permissions import IsPlatformAdmin, RecentAuthentication
from apps.core.utils import request_language
from apps.schools.billing import price_list

from . import notify
from .models import ContactMessage
from .serializers import AdminContactSerializer, ContactSerializer, HandleSerializer

log = logging.getLogger(__name__)

# The public pages, for the sitemap (the app's own routes: frontend/src/App.jsx).
PUBLIC_PAGES = ["/", "/register", "/contact", "/terms", "/privacy"]
# App routes that only make sense signed in: crawlers have nothing to read there.
PRIVATE_PREFIXES = [
    "/api/",
    "/django-admin/",
    "/learn",
    "/lessons/",
    "/labs",
    "/practice",
    "/attempts/",
    "/classes",
    "/groups",
    "/leaderboard",
    "/profile",
    "/search",
    "/playground",
    "/calculator",
    "/ask",
    "/children/",
    "/teach",
    "/marking",
    "/admin",
    "/school",
    "/reset-password",
    "/team",
]


class SiteInfoView(APIView):
    """GET -> what the public pages show besides their own text: the legal pages' version, owner and contact,
    how long records are kept, the price list (from the settings, as on the school's billing page), and whether
    maintenance mode is on. Public, the same for everyone."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "legal": legal.public_info(),
                "retention": legal.retention_info(),
                "pricing": price_list(),
                "maintenance": maintenance.maintenance_on(),
            }
        )


class ContactThrottle(IPThrottle):
    """Per client IP (signed in or not): messages sent with the contact form."""

    scope = "contact"


class ContactView(APIView):
    """POST {name, email, school?, message} -> 201: a message for the Iga team, kept for platform admins
    (Admin -> Messages) and emailed to CONTACT_EMAIL when set. Anyone may write; the sender's account is
    recorded when they are signed in."""

    permission_classes = [AllowAny]
    throttle_classes = [ContactThrottle]

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        thanks = Response({"detail": _("Thank you. We will answer you by email soon.")}, status=status.HTTP_201_CREATED)
        if data.get("website"):
            # Only robots fill in the hidden field: thank them as usual and keep nothing.
            security_log.event(request, "contact_spam", None, level=logging.WARNING, audit_every=600)
            return thanks
        user = request.user if request.user.is_authenticated else None
        message = ContactMessage.objects.create(
            name=data["name"],
            email=data["email"],
            school=data.get("school", ""),
            message=data["message"],
            language=request_language(request),
            user=user,
        )
        audit.record(request, "contact_message", message)
        if settings.CONTACT_EMAIL:
            transaction.on_commit(lambda: password_reset.deliver(notify.new_message, message.pk))
        return thanks


class AdminContactViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Platform admins: the contact-form messages (?status=open, the default, handled or all), and marking
    one as handled or open again."""

    permission_classes = [IsPlatformAdmin, RecentAuthentication]
    serializer_class = AdminContactSerializer

    def get_queryset(self):
        messages = ContactMessage.objects.select_related("user", "handled_by").order_by("-created_at")
        if self.action != "list":
            return messages
        wanted = self.request.query_params.get("status", "open")
        if wanted == "open":
            messages = messages.filter(handled_at__isnull=True)
        elif wanted == "handled":
            messages = messages.filter(handled_at__isnull=False)
        return messages

    @action(detail=True, methods=["post"])
    def handle(self, request, pk=None):
        message = self.get_object()
        serializer = HandleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handled = serializer.validated_data["handled"]
        message.handled_at = timezone.now() if handled else None
        message.handled_by = request.user if handled else None
        message.save(update_fields=["handled_at", "handled_by"])
        audit.record(request, "contact_handled" if handled else "contact_reopened", message)
        return Response(AdminContactSerializer(message).data)


# --- robots.txt and the sitemap --------------------------------------------------------------------------


class TextRenderer(BaseRenderer):
    media_type = "text/plain"
    format = "txt"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data.encode("utf-8") if isinstance(data, str) else data


class XMLRenderer(TextRenderer):
    media_type = "application/xml"
    format = "xml"


class FirstRenderer(BaseContentNegotiation):
    """Crawlers send all sorts of Accept headers: answer in the view's one format whatever they ask for."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class _PublicFile(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    content_negotiation_class = FirstRenderer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "public, max-age=3600"
        return response


class RobotsView(_PublicFile):
    """GET /robots.txt: crawlers may read the public pages, not the API or the signed-in app."""

    renderer_classes = [TextRenderer]

    def get(self, request):
        lines = ["User-agent: *", "Allow: /$"]
        lines += [f"Allow: {page}" for page in PUBLIC_PAGES if page != "/"]
        lines += [f"Disallow: {prefix}" for prefix in PRIVATE_PREFIXES]
        lines += ["", f"Sitemap: {settings.FRONTEND_URL}/sitemap.xml", ""]
        return Response("\n".join(lines))


class SitemapView(_PublicFile):
    """GET /sitemap.xml: the public pages, at the site's public address (FRONTEND_URL)."""

    renderer_classes = [XMLRenderer]

    def get(self, request):
        version = legal.current_version()
        urls = []
        for page in PUBLIC_PAGES:
            entry = f"  <url><loc>{escape(settings.FRONTEND_URL + page)}</loc>"
            if page in ("/terms", "/privacy") and len(version) == 10:
                entry += f"<lastmod>{escape(version)}</lastmod>"
            urls.append(entry + "</url>")
        body = "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
                *urls,
                "</urlset>",
                "",
            ]
        )
        return Response(body)
