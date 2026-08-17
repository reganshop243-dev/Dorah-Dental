from django.http import JsonResponse

def test_view(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'Test view is working!',
        'method': request.method,
        'path': request.path,
        'user': str(request.user),
        'authenticated': request.user.is_authenticated,
    })
