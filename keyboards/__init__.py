"""
Keyboards package for HeroSMS Bot
Contains all InlineKeyboard layouts for:
- User menus (main, services, countries, operators, offers)
- Admin panel menus
- Payment menus
- Navigation keyboards
"""

from keyboards.user_keyboards import (
    get_main_menu_keyboard,
    get_topup_menu_keyboard,
    get_profile_keyboard,
    get_history_keyboard,
    create_services_keyboard_paginated,
    create_countries_keyboard_paginated,
    create_operators_keyboard,
    create_price_tiers_keyboard,
    create_offers_keyboard_detailed,
)

from keyboards.admin_keyboards import (
    get_admin_main_keyboard,
    get_admin_users_keyboard,
    get_admin_settings_keyboard,
    get_admin_stats_keyboard,
    get_admin_herosms_settings_keyboard,
    get_admin_qrispy_settings_keyboard,
)

__all__ = [
    # User keyboards
    'get_main_menu_keyboard',
    'get_topup_menu_keyboard',
    'get_profile_keyboard',
    'get_history_keyboard',
    'create_services_keyboard_paginated',
    'create_countries_keyboard_paginated',
    'create_operators_keyboard',
    'create_price_tiers_keyboard',
    'create_offers_keyboard_detailed',
    
    # Admin keyboards
    'get_admin_main_keyboard',
    'get_admin_users_keyboard',
    'get_admin_settings_keyboard',
    'get_admin_stats_keyboard',
    'get_admin_herosms_settings_keyboard',
    'get_admin_qrispy_settings_keyboard',
]

__version__ = '1.0.0'