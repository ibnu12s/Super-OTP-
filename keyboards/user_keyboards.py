# keyboards/user_keyboards.py (perbaikan lengkap)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Optional
import math
import json

ITEMS_PER_PAGE = 10

def create_services_keyboard_paginated(services: List[Dict], page: int = 0, 
                                       items_per_page: int = ITEMS_PER_PAGE,
                                       show_search: bool = True) -> InlineKeyboardMarkup:
    """
    Create paginated services keyboard with search functionality
    Shows ALL services with infinite pagination
    """
    total_pages = math.ceil(len(services) / items_per_page)
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(services))
    
    keyboard = []
    
    # Search button (optional)
    if show_search:
        keyboard.append([
            InlineKeyboardButton("🔍 Cari Layanan", callback_data="search_service")
        ])
    
    # Service buttons for current page
    for service in services[start_idx:end_idx]:
        keyboard.append([
            InlineKeyboardButton(
                f"📱 {service['name']} ({service['code']})",
                callback_data=f"service_{service['code']}"
            )
        ])
    
    # Pagination controls
    if total_pages > 1:
        pagination_row = []
        
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton("◀️ Sebelumnya", callback_data=f"services_page_{page - 1}")
            )
        
        pagination_row.append(
            InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop")
        )
        
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton("Selanjutnya ▶️", callback_data=f"services_page_{page + 1}")
            )
        
        keyboard.append(pagination_row)
    
    # Navigation
    keyboard.append([
        InlineKeyboardButton("🏠 Menu Utama", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_countries_keyboard_paginated(countries: List[Dict], page: int = 0,
                                        items_per_page: int = ITEMS_PER_PAGE,
                                        service_code: str = "") -> InlineKeyboardMarkup:
    """
    Create paginated countries keyboard
    Shows ALL countries with stock information
    """
    total_pages = math.ceil(len(countries) / items_per_page)
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(countries))
    
    keyboard = []
    
    # Country buttons for current page
    for country in countries[start_idx:end_idx]:
        # Stock indicator
        stock_icon = "🟢" if country.get("has_stock", False) else "🔴"
        stock_info = f"({country.get('total_available', 0):,})"
        price_info = f"${country.get('default_price', 0):.4f}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{stock_icon} {country['name']} {stock_info} - {price_info}",
                callback_data=f"country_{country['id']}"
            )
        ])
    
    # Pagination controls
    if total_pages > 1:
        pagination_row = []
        
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton("◀️", callback_data=f"countries_page_{page - 1}")
            )
        
        pagination_row.append(
            InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="noop")
        )
        
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton("▶️", callback_data=f"countries_page_{page + 1}")
            )
        
        keyboard.append(pagination_row)
    
    # Navigation
    keyboard.append([
        InlineKeyboardButton("◀️ Kembali ke Layanan", callback_data="back_to_services")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_operators_keyboard(operators: List[str], country_id: int = None,
                              service_code: str = "") -> InlineKeyboardMarkup:
    """
    Create operators keyboard
    Shows ALL operators without limit
    """
    keyboard = []
    
    # Any operator option
    keyboard.append([
        InlineKeyboardButton("📡 Any Operator (Recommended)", callback_data="any_operator")
    ])
    
    # All operators (no limit)
    for i in range(0, len(operators), 2):
        row = []
        for operator in operators[i:i+2]:
            row.append(
                InlineKeyboardButton(
                    f"📱 {operator}",
                    callback_data=f"operator_{operator}"
                )
            )
        keyboard.append(row)
    
    # Navigation
    keyboard.append([
        InlineKeyboardButton("◀️ Kembali ke Negara", callback_data="back_to_countries")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_price_tiers_keyboard(price_tiers: List[Dict], service_code: str = "",
                                country_id: int = 0) -> InlineKeyboardMarkup:
    """
    Create keyboard with ALL price tiers
    Shows complete pricing information with stock
    """
    keyboard = []
    
    # Summary header
    total_stock = sum(tier.get("available_count", 0) for tier in price_tiers)
    keyboard.append([
        InlineKeyboardButton(
            f"📊 Total Stok: {total_stock:,} | {len(price_tiers)} Tier",
            callback_data="noop"
        )
    ])
    
    # All price tiers (no limit)
    for tier in price_tiers:
        price = tier.get("price", 0)
        available = tier.get("available_count", 0)
        
        # Stock level indicator
        if available > 1000:
            stock_level = "🟢"
        elif available > 100:
            stock_level = "🟡"
        elif available > 0:
            stock_level = "🟠"
        else:
            stock_level = "🔴"
        
        tier_data = json.dumps({
            "price": price,
            "available_count": available
        })
        
        keyboard.append([
            InlineKeyboardButton(
                f"{stock_level} ${price:.4f} | Stok: {available:,}",
                callback_data=f"tier_{tier_data}"
            )
        ])
    
    # Navigation
    keyboard.append([
        InlineKeyboardButton("◀️ Kembali ke Operator", callback_data="back_to_operators")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_offers_keyboard_detailed(offers_data: Dict) -> InlineKeyboardMarkup:
    """
    Create detailed offers keyboard with all price tiers
    (Alternative view for offers)
    """
    keyboard = []
    
    service_name = offers_data.get("service_name", "")
    country_name = offers_data.get("country_name", "")
    price_tiers = offers_data.get("price_tiers", [])
    
    # Header
    keyboard.append([
        InlineKeyboardButton(
            f"📱 {service_name} - 🌍 {country_name}",
            callback_data="noop"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"📊 {len(price_tiers)} Tiers | Total: {sum(t.get('available_count', 0) for t in price_tiers):,}",
            callback_data="noop"
        )
    ])
    
    # All price tiers
    for tier in price_tiers:
        price = tier.get("price", 0)
        available = tier.get("available_count", 0)
        
        tier_data = json.dumps({
            "price": price,
            "available_count": available
        })
        
        keyboard.append([
            InlineKeyboardButton(
                f"💵 ${price:.4f} | Stok: {available:,}",
                callback_data=f"tier_{tier_data}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Kembali", callback_data="back_to_operators")
    ])
    
    return InlineKeyboardMarkup(keyboard)