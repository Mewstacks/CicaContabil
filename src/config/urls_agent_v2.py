from django.urls import path

from apps.intelligence import agent_v2

urlpatterns = [
    path("enroll", agent_v2.enroll, name="agent-v2-enroll"),
    path("heartbeat", agent_v2.heartbeat, name="agent-v2-heartbeat"),
    path("backups/next", agent_v2.next_backup, name="agent-v2-backup-next"),
    path(
        "backups/<uuid:batch_id>/download",
        agent_v2.download_backup,
        name="agent-v2-backup-download",
    ),
    path("sync/<str:capability>", agent_v2.sync_capability, name="agent-v2-sync"),
    path("certificate/renew", agent_v2.renew_certificate, name="agent-v2-renew"),
]
