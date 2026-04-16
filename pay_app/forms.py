"""Compatibility layer for legacy imports."""

from apps.services.forms import PayForm, DateInput
from apps.cabinets.forms import CabinetForm, CabinetTagAssignForm
from apps.tags.forms import TagForm

__all__ = ['PayForm', 'DateInput', 'CabinetForm', 'CabinetTagAssignForm', 'TagForm']
