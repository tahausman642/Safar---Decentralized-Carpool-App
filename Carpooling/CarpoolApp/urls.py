from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('Login/', views.Login, name='Login'),
    path('Register/', views.Register, name='Register'),
    path('Signup/', views.Signup, name='Signup'),
    path('UserLogin/', views.UserLogin, name='UserLogin'),
    path('UserScreen/', views.UserScreen, name='UserScreen'),
    path('DriverScreen/', views.DriverScreen, name='DriverScreen'),
    path('AddRide/', views.AddRide, name='AddRide'),
    path('schedule_ride/', views.schedule_ride, name='schedule_ride'),
    path('get_scheduled_rides/', views.get_scheduled_rides, name='get_scheduled_rides'),
    path('RideCompleteAction/', views.RideCompleteAction, name='RideCompleteAction'),
    path('ViewDrivers/', views.ViewDrivers, name='ViewDrivers'),
    path('ShareLocationAction/', views.ShareLocationAction, name='ShareLocationAction'),
    path('Ratings/', views.Ratings, name='Ratings'),
    path('RatingsAction/', views.RatingsAction, name='RatingsAction'),
    path('verify_user/', views.verify_user, name='verify_user'),
    path('emergency_contact/', views.emergency_contact, name='emergency_contact'),
    path('distribute_tokens/', views.distribute_tokens, name='distribute_tokens'),
    path('get_user_token_balance/', views.get_user_token_balance, name='get_user_token_balance'),
    path('get_pending_payments/', views.get_pending_payments, name='get_pending_payments'),
    path('get_driver_wallet/', views.get_driver_wallet, name='get_driver_wallet'),  # CHANGED: removed parameter
    path('provide_token_info/', views.provide_token_info, name='provide_token_info'),
    path('verify_token_payment/', views.verify_token_payment, name='verify_token_payment'),
    path('map_view/', views.map_view, name='map_view'),
    path('get_completed_rides_for_passenger/', views.get_completed_rides_for_passenger, name='get_completed_rides_for_passenger'),
    path('notify_passenger_payment/', views.notify_passenger_payment, name='notify_passenger_payment'),
    path('logout/', views.logout_view, name='logout'),  # ADDED: logout endpoint
	path('get_completed_paid_rides/', views.get_completed_paid_rides, name='get_completed_paid_rides'),
    ]