from django.urls import re_path
from django.contrib.auth.views import LogoutView
from django.urls import reverse_lazy

from .views import (ParticipantCreateView, TabloListView, TabloDetailView,
                    ParticipantActivateView, ParticipantScoreView,
                    PntElementView, JudgeView, login,
                    JudgeASubmit, JudgeBSubmit, CurrentParticipantScoreView,
                    JudgeCSubmit, JrebiView, TabloPrintView,
                    MonitorView, TabloMonitorView,
                    LanguageViewEn, LanguageViewRu, monitor_stream,
                    has_updated, open_judge, delete_participation,
                    StaffConsoleHome, ConsoleFindParticipant,
                    ConsoleParticipationDetail, ConsoleReopenJudge,
                    ConsoleReopenParticipation, ConsoleWithdraw,
                    ConsoleJudges, ConsoleRetireJudge)

urlpatterns = [
    re_path(r'^tablo/pcreate$', ParticipantCreateView.as_view(), name="paticipant_create"),
    re_path(r'^tablo/list$', TabloListView.as_view(), name="tablo_list"),
    re_path(r'^tablo/detail/(?P<pk>\d+)/$', TabloDetailView.as_view(), name="tablo_detail"),
    re_path(r'^tablo/print/(?P<pk>\d+)/$', TabloPrintView.as_view(), name="tablo_print"),
    re_path(r'^activate$', ParticipantActivateView.as_view(), name="participant_activate"),
    re_path(r'^score/(?P<pk>\d+)/$', ParticipantScoreView.as_view(), name="participant_score"),
    re_path(r'^current/$', CurrentParticipantScoreView.as_view(), name="current_score"),
    re_path(r'^p/(?P<pk>\d+)/$', PntElementView.as_view(), name="pnt_element"),
    re_path(r'^$', JudgeView.as_view(), name="judge_view"),
    re_path(r'^asubmit$', JudgeASubmit.as_view(), name="judgea_submit"),
    re_path(r'^bsubmit$', JudgeBSubmit.as_view(), name="judgeb_submit"),
    re_path(r'^csubmit$', JudgeCSubmit.as_view(), name="judgec_submit"),
    re_path(r'^login/$', login, name="login"),
    re_path(r'^logout/$', LogoutView.as_view(next_page=reverse_lazy('login')), name="logout"),
    re_path(r'^jrebi$', JrebiView.as_view(), name="paticipant_jrebi"),
    re_path(r'^monitor$', MonitorView.as_view(), name="monitor"),
    re_path(r'^monitor/stream$', monitor_stream, name="monitor_stream"),
    re_path(r'^tablo/monitor/(?P<pk>\d+)/$', TabloMonitorView.as_view(), name="tablo_monitor"),
    re_path(r'^language/en$', LanguageViewEn.as_view(), name="lang_en"),
    re_path(r'^language/ru$', LanguageViewRu.as_view(), name="lang_ru"),
    re_path(r'^has_update$', has_updated, name="has_updated"),
    re_path(r'^open_judge/(?P<idx>\d+)/$', open_judge, name="open_judge"),
    re_path(r'^delete_participation/(?P<pk>\d+)/$', delete_participation, name="delete_participation"),

    # Staff console (is_staff only)
    re_path(r'^console/$', StaffConsoleHome.as_view(), name="staff_console"),
    re_path(r'^console/find/$', ConsoleFindParticipant.as_view(), name="console_find"),
    re_path(r'^console/participation/(?P<pk>\d+)/$', ConsoleParticipationDetail.as_view(), name="console_participation"),
    re_path(r'^console/reopen-judge/(?P<pk>\d+)/$', ConsoleReopenJudge.as_view(), name="console_reopen_judge"),
    re_path(r'^console/reopen/(?P<pk>\d+)/$', ConsoleReopenParticipation.as_view(), name="console_reopen_participation"),
    re_path(r'^console/withdraw/(?P<pk>\d+)/$', ConsoleWithdraw.as_view(), name="console_withdraw"),
    re_path(r'^console/judges/$', ConsoleJudges.as_view(), name="console_judges"),
    re_path(r'^console/retire-judge/(?P<pk>\d+)/$', ConsoleRetireJudge.as_view(), name="console_retire_judge"),
]
