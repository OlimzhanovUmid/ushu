from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from tablo.models import Participation, PS_DOING

# Create your views here.
class LoginRequiredMixin(object):
    # def dispatch(self, *args, **kwargs):
    #     return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LoginRequiredMixin, self).get_context_data(**kwargs)
        obj = Participation.objects \
                .filter(state=PS_DOING) \
                .exists()
        context['current_active'] = obj
        return context

