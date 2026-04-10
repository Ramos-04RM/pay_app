# # pay_app/signals.py
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.core.cache import cache
# from .models import Pay
#
# HOME_CACHE_KEY_PREFIX = "views.decorators.cache.cache_page"
#
# @receiver(post_save, sender=Pay)
# @receiver(post_delete, sender=Pay)
# def clear_home_cache(sender, **kwargs):
#     cache.clear()
#
