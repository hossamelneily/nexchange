from django.contrib.auth import login
from loginurl.utils import create as create_user_key
from django.utils.crypto import get_random_string
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from accounts.models import Profile


def _create_anonymous_user(request):
    def _create_username():
        _username = 'Anonymous{}'.format(User.objects.last().pk + 1)
        exists = len(User.objects.filter(username=_username))
        while exists == 1:
            _username += get_random_string(length=5)
            exists = len(User.objects.filter(username=_username))
        return _username

    username = _create_username()
    user_data = {}
    profile_data = {}
    user_data['username'] = username
    profile_data.update({
        'disabled': True,
        'anonymous_login': True
    })

    user = User(**user_data)
    user.save()
    profile_data['user'] = user
    profile = Profile(**profile_data)
    profile.save()
    next_uri = reverse('accounts.change_password')
    key = create_user_key(user, usage_left=None, next=next_uri)
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    return key
