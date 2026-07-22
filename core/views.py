from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.utils.decorators import method_decorator

from tablo.models import Participation, PS_DOING


# Create your views here.
class LoginRequiredMixin(object):
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


class StaffRequiredMixin(LoginRequiredMixin):
    """Restrict a view to the main judge / secretary (``is_staff``).

    Anonymous users are redirected to login (via LoginRequiredMixin); an
    authenticated non-staff user gets 403.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            return HttpResponseForbidden('Staff only')
        return super(StaffRequiredMixin, self).dispatch(request, *args, **kwargs)


def staff_required(view):
    """Function-view equivalent of StaffRequiredMixin."""
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden('Staff only')
        return view(request, *args, **kwargs)
    return wrapped
