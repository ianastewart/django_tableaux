In django_tableaux utils.py
Implement a new way of saving and loading column settings to replace save_columns_dict and
load_columns_dict in 

If the user is loggen in user the settings are saved in the database using the UserTableSettings model.
If the user is anonymous the settings are saved in the session as before.

Whenever a breakpoint change is detected if settings for that breakpoint are in the database, use them, 
otherwise use the current settings. 
