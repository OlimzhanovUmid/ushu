from django.conf.urls import url, patterns, include
from django.contrib.auth.views import logout
from django.core.urlresolvers import reverse_lazy
from .views import (ParticipantCreateView, TabloListView,TabloDetailView,
                    ParticipantActivateView, ParticipantScoreView,
                    PntElementView, JudgeView, login,
                    JudgeASubmit, JudgeBSubmit, CurrentParticipantScoreView,
                    JudgeCSubmit, JrebiView, TabloPrintView,
                    MonitorView, ShowmeView, TabloMonitorView,
                    LanguageViewEn,LanguageViewRu, showme_view,
                    has_updated,open_judge,delete_participation)

urlpatterns = [
    url(r'^tablo/pcreate$', ParticipantCreateView.as_view(), name="paticipant_create"),
    url(r'^tablo/list$', TabloListView.as_view(), name="tablo_list"),
    url(r'^tablo/detail/(?P<pk>\d+)/$', TabloDetailView.as_view(), name="tablo_detail"),
    url(r'^tablo/print/(?P<pk>\d+)/$', TabloPrintView.as_view(), name="tablo_print"),
    url(r'^activate$', ParticipantActivateView.as_view(), name="participant_activate"),
    url(r'^score/(?P<pk>\d+)/$', ParticipantScoreView.as_view(), name="participant_score"),
    url(r'^current/$', CurrentParticipantScoreView.as_view(), name="current_score"),
    url(r'^p/(?P<pk>\d+)/$', PntElementView.as_view(), name="pnt_element"),
    url(r'^$', JudgeView.as_view(), name="judge_view"),
    url(r'^asubmit$', JudgeASubmit.as_view(), name="judgea_submit"),
    url(r'^bsubmit$', JudgeBSubmit.as_view(), name="judgeb_submit"),
    url(r'^csubmit$', JudgeCSubmit.as_view(), name="judgec_submit"),
    url(r'^login/$', login, name="login"),
    url(r'^logout/$', logout, {"next_page": reverse_lazy('login')}, name="logout"),
    url(r'^jrebi$', JrebiView.as_view(), name="paticipant_jrebi"),
    url(r'^monitor$', MonitorView.as_view(), name="monitor"),
    url(r'^showme$', ShowmeView.as_view(), name="showme"),
    url(r'^tablo/monitor/(?P<pk>\d+)/$', TabloMonitorView.as_view(), name="tablo_monitor"),
    url(r'^language/en$', LanguageViewEn.as_view(), name="lang_en"),
    url(r'^language/ru$', LanguageViewRu.as_view(), name="lang_ru"),
    url(r'^showme_view$', showme_view, name="showme_view"),
    url(r'^has_update$', has_updated, name="has_updated"),
    url(r'^open_judge/(?P<idx>\d+)/$', open_judge, name="open_judge"),
    url(r'^delete_participation/(?P<pk>\d+)/$', delete_participation, name="delete_participation"),
]
