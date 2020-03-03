"""mainproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url
from capacityWeb import views as capViews

urlpatterns = [
    path('admin/', admin.site.urls),
    # capacityWEB's TEMPLATE URL
    url(r'^index/', capViews.index),
    url(r'^latestwarn/', capViews.latestwarn),
    url(r'^test/', capViews.test),
    url(r'^addData/', capViews.addData),
    # 用户登录模块
    url('login/', capViews.login, name='login'),
    url('validate/', capViews.validate),
    url('signUp/', capViews.signUp),
    url('change/', capViews.change, name='change'),
    url('doChange/', capViews.doChange),
    url('sendCaptcha/', capViews.sendCaptcha),
    # VIEWS URL
    url(r'^test1/', capViews.test1),
    url(r'^get_count/', capViews.get_count),
    url(r'^startDetectCount_thread/', capViews.startDetectCount_thread),
    url(r'^getCountNum_thread/', capViews.getCountNum_thread),
    url(r'^exitDetectCount_thread/', capViews.exitDetectCount_thread),
    url(r'^getHeatMapNums/', capViews.getHeatMapNums),
    url(r'^getHeatMapScenic/', capViews.getHeatMapScenic),
    url(r'^getHeatMapCamera/', capViews.getHeatMapCamera),
    url(r'^updateCurrentWarn/', capViews.updateCurrentWarn),
    url(r'^updateNumbar/', capViews.updateNumbar),
    url(r'^getWarnDataById/', capViews.getWarnDataById),
    # url(r'^start_run_person/', capViews.start_run_person),
    # url(r'^detect_run_person/', capViews.detect_run_person),
    # url(r'^start_run_fight/', capViews.start_run_fight),
    # url(r'^detect_run_fight/', capViews.detect_run_fight),
    # url(r'^start_run_smoke/', capViews.start_run_smoke),
    # url(r'^detect_run_smoke/', capViews.detect_run_smoke),
    url(r'^get1Adminer/', capViews.get1Adminer),
    # 设置二级路由，请保留
    path('capacityWeb/', include('capacityWeb.urls', namespace='capacityWeb')),

]
