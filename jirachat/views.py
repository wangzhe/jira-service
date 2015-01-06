from django.shortcuts import render
from django.shortcuts import render_to_response
# from django.http import HttpResponse


# Create your views here.
def home(request):
    print request
    return render_to_response("jirachat/home.html", {'hello': "Hello World2"})
