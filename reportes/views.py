from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def panel_reportes(request):
    """La generación y exportación de reportes (HU009/HU010) se implementa en los Sprints 8-9."""
    return render(request, 'reportes/panel.html')
