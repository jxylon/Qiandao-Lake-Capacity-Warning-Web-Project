from django.contrib import admin
from django.urls import path
from capacityWeb import views

app_name = '[capacityWeb]'
urlpatterns = [
    # 主页
    path('index/', views.index, name='index'),
    # 各景区详细信息
    path('meifeng/', views.meifeng, name='meifeng'),
    path('huangshanjian/', views.huangshanjian, name='huangshanjian'),
    path('tianchi/', views.tianchi, name='tianchi'),
    path('yueguang/', views.yueguang, name='yueguang'),
    path('longshan/', views.longshan, name='longsha'),
    path('yule/', views.yule, name='yule'),
    path('guihua/', views.guihua, name='guihua'),
    path('mishan/', views.mishan, name='mishan'),
    path('updatetodayTouristNums/', views.updatetodayTouristNums),
    path('updatetodayTouristNums2/', views.updatetodayTouristNums2),
    path('getScenicHeartMapData/', views.getScenicHeartMapData),
    # 预警分析
    path('mfanalysis/', views.mf_analysis, name='mfanalysis'),
    path('msanalysis/', views.ms_analysis, name='msanalysis'),
    path('tcanalysis/', views.tc_analysis, name='tcanalysis'),
    path('lsanalysis/', views.ls_analysis, name='lsanalysis'),
    path('ghanalysis/', views.gh_analysis, name='ghanalysis'),
    path('yganalysis/', views.yg_analysis, name='yganalysis'),
    path('ylanalysis/', views.yl_analysis, name='ylanalysis'),
    path('hsanalysis/', views.hs_analysis, name='hsanalysis'),
    # 后台管理
    path('admin/', views.admin, name='admin'),
    path('getAdminData/', views.getAdminData),
    path('deleteAdminData/', views.deleteAdminData),
    path('addAdminData/', views.addAdminData),
    path('getAdminerData/', views.getAdminerData),
    path('deleteAdminerData/', views.deleteAdminerData),
    path('addAdminerData/', views.addAdminerData),
    # 预警管理
    path('admin_warn/', views.admin_warn, name='admin_warn'),
    path('getWarnData/', views.getWarnData),
    path('DetectWarn/', views.DetectWarn),
    path('notice/', views.notice),
]
