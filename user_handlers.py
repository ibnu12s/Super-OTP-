# handlers/user_handlers.py (KODE LENGKAP PERBAIKAN)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from database.db import Database
from services.hero_sms_api import hero_sms_api
from services.qrispy_api import qrispy_api
from keyboards.user_keyboards import (
    get_main_menu_keyboard,
    get_topup_menu_keyboard,
    get_profile_keyboard,
    get_history_keyboard,
    create_services_keyboard_paginated,
    create_countries_keyboard_paginated,
    create_operators_keyboard,
    create_price_tiers_keyboard,
    create_offers_keyboard_detailed
)
import logging
import json
import math
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)
db = Database()

# Constants
ITEMS_PER_PAGE = 10
CACHE_TIMEOUT = 30  # seconds

# Conversation States
(
    # Buy Number Flow
    SELECT_SERVICE_FLOW,
    SEARCH_SERVICE_FLOW,
    SELECT_COUNTRY_FLOW,
    SELECT_OPERATOR_FLOW,
    SELECT_OFFER_FLOW,
    CONFIRM_PURCHASE_FLOW,
    
    # Registration/Login
    REGISTER_PASSWORD,
    LOGIN_PASSWORD,
    
    # Top Up Flow
    TOPUP_AMOUNT,
    TOPUP_PAYMENT,
    
    # Admin
    ADMIN_BROADCAST,
    ADMIN_UPDATE_HEROSMS_KEY,
    ADMIN_UPDATE_QRISPY_TOKEN,
    ADMIN_UPDATE_WEBHOOK_SECRET,
    ADMIN_ADD_USER_BALANCE,
    ADMIN_BAN_USER
) = range(17)

class UserHandlers:
    """Complete User Handlers with Real-time Data & Infinite Scroll"""
    
    # ========================================================================
    # START & AUTHENTICATION
    # ========================================================================
    
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        telegram_id = user.id
        
        # Check if user exists
        existing_user = await db.get_user_by_telegram_id(telegram_id)
        
        if existing_user:
            if existing_user.status.value == "banned":
                await update.message.reply_text(
                    "❌ *Akun Diblokir*\n\n"
                    "Akun Anda telah dibanned.\n"
                    "Hubungi admin untuk informasi lebih lanjut.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return ConversationHandler.END
            
            # Check if user is admin
            if existing_user.is_admin:
                await update.message.reply_text(
                    f"👑 *Selamat Datang Admin!*\n\n"
                    f"Nama: {existing_user.first_name}\n"
                    f"Saldo: Rp {existing_user.balance:,.0f}\n\n"
                    "Gunakan /admin untuk panel admin.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_menu_keyboard(is_admin=True)
                )
            else:
                await update.message.reply_text(
                    f"👋 *Selamat Datang Kembali!*\n\n"
                    f"Nama: {existing_user.first_name}\n"
                    f"Saldo: Rp {existing_user.balance:,.0f}\n"
                    f"Status: {existing_user.status.value}\n\n"
                    "Silakan pilih menu di bawah:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_menu_keyboard()
                )
            return ConversationHandler.END
        
        else:
            # New user registration
            await update.message.reply_text(
                "🌟 *Selamat Datang di HeroSMS Bot!*\n\n"
                "📱 Layanan SMS Activation Terpercaya\n"
                "💳 Pembayaran via QRIS\n"
                "🌍 Nomor dari berbagai negara\n\n"
                "*Silakan daftar terlebih dahulu.*\n"
                "Masukkan password untuk akun Anda:",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['registration'] = {
                'telegram_id': telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            return REGISTER_PASSWORD
    
    @staticmethod
    async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle registration password input"""
        password = update.message.text.strip()
        
        if len(password) < 4:
            await update.message.reply_text(
                "❌ Password terlalu pendek! Minimal 4 karakter.\n"
                "Silakan masukkan password yang lebih kuat:"
            )
            return REGISTER_PASSWORD
        
        if len(password) > 50:
            await update.message.reply_text(
                "❌ Password terlalu panjang! Maksimal 50 karakter.\n"
                "Silakan masukkan password yang lebih pendek:"
            )
            return REGISTER_PASSWORD
        
        reg_data = context.user_data['registration']
        
        # Create user
        user_data = {
            'telegram_id': reg_data['telegram_id'],
            'username': reg_data.get('username'),
            'first_name': reg_data.get('first_name'),
            'last_name': reg_data.get('last_name'),
            'password': password,
            'balance': 0.0
        }
        
        user = await db.create_user(user_data)
        
        if user:
            # Clear registration data
            context.user_data.pop('registration', None)
            
            await update.message.reply_text(
                "✅ *Pendaftaran Berhasil!*\n\n"
                f"Selamat bergabung, {user.first_name}!\n\n"
                "💡 *Tips:*\n"
                "• Gunakan /buy untuk beli nomor\n"
                "• Gunakan /topup untuk isi saldo\n"
                "• Gunakan /profile untuk lihat profil\n\n"
                "Selamat menggunakan layanan kami! 🚀",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Gagal mendaftar. Silakan coba lagi dengan /start"
            )
            return ConversationHandler.END
    
    @staticmethod
    async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle login"""
        await update.message.reply_text(
            "🔐 *Login*\n\n"
            "Masukkan password Anda:",
            parse_mode=ParseMode.MARKDOWN
        )
        return LOGIN_PASSWORD
    
    @staticmethod
    async def verify_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Verify login password"""
        password = update.message.text.strip()
        telegram_id = update.effective_user.id
        
        user = await db.get_user_by_telegram_id(telegram_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User tidak ditemukan!\n"
                "Silakan daftar terlebih dahulu dengan /start"
            )
            return ConversationHandler.END
        
        if user.password == password:
            context.user_data['authenticated'] = True
            context.user_data['user'] = {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'balance': user.balance,
                'is_admin': user.is_admin
            }
            
            await update.message.reply_text(
                f"✅ *Login Berhasil!*\n\n"
                f"👋 Selamat datang, {user.first_name}!\n"
                f"💰 Saldo: Rp {user.balance:,.0f}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ *Password Salah!*\n\n"
                "Silakan coba lagi dengan /login",
                parse_mode=ParseMode.MARKDOWN
            )
        
        return ConversationHandler.END
    
    # ========================================================================
    # BUY NUMBER FLOW (REAL-TIME, NO LIMIT)
    # ========================================================================
    
    @staticmethod
    async def buy_number_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initialize buy number session with real-time data"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return ConversationHandler.END
        
        # Loading message
        loading_msg = await update.message.reply_text(
            "🔄 *Mengambil data layanan...*\n"
            "Mohon tunggu sebentar.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Initialize buy session
        context.user_data['buy_session'] = {
            'step': 'service',
            'services_page': 0,
            'countries_page': 0,
            'offers_page': 0,
            'selected_service': None,
            'selected_country': None,
            'selected_operator': None,
            'selected_tier': None,
            'timestamp': time.time(),
            'cache': {}
        }
        
        # Get ALL services in real-time
        services_response = await hero_sms_api.get_all_services()
        
        # Delete loading message
        await loading_msg.delete()
        
        if services_response.get("status") == "success":
            all_services = services_response['services']
            total_services = services_response['total']
            
            # Store in session
            context.user_data['buy_session']['all_services'] = all_services
            
            # Show paginated services
            await update.message.reply_text(
                f"📱 *Pilih Layanan*\n\n"
                f"📊 Total layanan tersedia: *{total_services}*\n"
                f"🔄 Data real-time\n\n"
                "Anda dapat:\n"
                "• Mencari dengan kata kunci\n"
                "• Memilih dari daftar\n"
                "• Navigasi halaman untuk lihat semua",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_services_keyboard_paginated(
                    all_services,
                    page=0,
                    items_per_page=ITEMS_PER_PAGE
                )
            )
            return SELECT_SERVICE_FLOW
        else:
            await update.message.reply_text(
                "❌ *Gagal Mengambil Data*\n\n"
                "Tidak dapat mengambil daftar layanan.\n"
                "Silakan coba lagi nanti.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
    
    @staticmethod
    async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle service selection with pagination and search"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        session = context.user_data.get('buy_session', {})
        
        if not session:
            await query.message.edit_text(
                "❌ Sesi telah berakhir. Silakan mulai ulang dengan /buy",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # ====== HANDLE PAGINATION ======
        if data.startswith("services_page_"):
            new_page = int(data.replace("services_page_", ""))
            session['services_page'] = new_page
            all_services = session.get('all_services', [])
            
            await query.message.edit_reply_markup(
                reply_markup=create_services_keyboard_paginated(
                    all_services,
                    page=new_page,
                    items_per_page=ITEMS_PER_PAGE
                )
            )
            return SELECT_SERVICE_FLOW
        
        # ====== HANDLE SEARCH ======
        if data == "search_service":
            await query.message.edit_text(
                "🔍 *Cari Layanan*\n\n"
                "Ketik nama atau kode layanan:\n"
                "Contoh: `telegram`, `whatsapp`, `google`\n\n"
                "Kirim /cancel untuk membatalkan.",
                parse_mode=ParseMode.MARKDOWN
            )
            return SEARCH_SERVICE_FLOW
        
        # ====== HANDLE SERVICE SELECTION ======
        if data.startswith("service_"):
            service_code = data.replace("service_", "")
            
            # Find service in all services
            all_services = session.get('all_services', [])
            service_info = next(
                (s for s in all_services if s['code'] == service_code),
                {'code': service_code, 'name': service_code}
            )
            
            session['selected_service'] = service_info
            
            # Show loading
            loading_msg = await query.message.reply_text(
                "🔄 *Mengambil data negara...*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Get REAL-TIME offers for this service
            offers_response = await hero_sms_api.get_activation_offers_real_time(
                services=service_code
            )
            
            await loading_msg.delete()
            
            if offers_response.get("status") == "success" and offers_response.get("data"):
                service_offers = offers_response["data"].get(service_code, {})
                countries_offers = service_offers.get("countries", {})
                
                if countries_offers:
                    # Build countries list with real-time stock info
                    countries_list = []
                    for country_id_str, offer_info in countries_offers.items():
                        country_id = int(country_id_str)
                        
                        countries_list.append({
                            'id': country_id,
                            'name': offer_info.get('country_name', f'Country {country_id}'),
                            'has_stock': offer_info.get('has_stock', False),
                            'total_available': offer_info.get('total_available', 0),
                            'default_price': offer_info.get('prices', {}).get('default', 0),
                            'min_price': offer_info.get('prices', {}).get('min', 0),
                            'total_count': offer_info.get('counts', {}).get('total', 0),
                            'physical_count': offer_info.get('counts', {}).get('physical', 0),
                            'price_tiers_count': len(offer_info.get('price_tiers', []))
                        })
                    
                    # Sort by price (cheapest first)
                    countries_list.sort(key=lambda x: (x['default_price'], -x['total_available']))
                    
                    # Store in session
                    session['available_countries'] = countries_list
                    session['countries_page'] = 0
                    
                    # Show countries
                    await query.message.edit_text(
                        f"🌍 *Pilih Negara*\n\n"
                        f"📱 Layanan: *{service_info['name']}*\n"
                        f"🔢 Kode: `{service_code}`\n"
                        f"🌐 Negara tersedia: *{len(countries_list)}*\n"
                        f"📊 Diurutkan: Harga termurah\n\n"
                        "*Pilih negara untuk melihat operator:*",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=create_countries_keyboard_paginated(
                            countries_list,
                            page=0,
                            items_per_page=ITEMS_PER_PAGE,
                            service_code=service_code
                        )
                    )
                    return SELECT_COUNTRY_FLOW
                else:
                    await query.message.edit_text(
                        f"❌ *Tidak Tersedia*\n\n"
                        f"Layanan *{service_info['name']}* tidak memiliki nomor tersedia saat ini.\n\n"
                        "Silakan pilih layanan lain.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=create_services_keyboard_paginated(
                            session.get('all_services', []),
                            page=0,
                            items_per_page=ITEMS_PER_PAGE
                        )
                    )
                    return SELECT_SERVICE_FLOW
            else:
                await query.message.edit_text(
                    "❌ Gagal mengambil data penawaran.\n"
                    "Silakan coba lagi.",
                    reply_markup=create_services_keyboard_paginated(
                        session.get('all_services', []),
                        page=0,
                        items_per_page=ITEMS_PER_PAGE
                    )
                )
                return SELECT_SERVICE_FLOW
        
        # ====== HANDLE BACK TO MAIN ======
        if data == "back_to_main":
            await query.message.edit_text(
                "🏠 *Menu Utama*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
            context.user_data.pop('buy_session', None)
            return ConversationHandler.END
        
        return SELECT_SERVICE_FLOW
    
    @staticmethod
    async def handle_service_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text search for services with real-time filtering"""
        search_query = update.message.text.strip().lower()
        
        if search_query == "/cancel":
            session = context.user_data.get('buy_session', {})
            await update.message.reply_text(
                "❌ Pencarian dibatalkan.",
                reply_markup=create_services_keyboard_paginated(
                    session.get('all_services', []),
                    page=0,
                    items_per_page=ITEMS_PER_PAGE
                )
            )
            return SELECT_SERVICE_FLOW
        
        session = context.user_data.get('buy_session', {})
        all_services = session.get('all_services', [])
        
        if not all_services:
            await update.message.reply_text(
                "❌ Data layanan tidak tersedia. Gunakan /buy untuk memulai ulang."
            )
            return ConversationHandler.END
        
        # Search with scoring
        scored_services = []
        for service in all_services:
            name_lower = service.get('name', '').lower()
            code_lower = service.get('code', '').lower()
            
            score = 0
            
            # Exact match
            if search_query == code_lower:
                score = 100
            elif search_query == name_lower:
                score = 90
            
            # Starts with
            elif code_lower.startswith(search_query):
                score = 80
            elif name_lower.startswith(search_query):
                score = 70
            
            # Contains
            elif search_query in code_lower:
                score = 60
            elif search_query in name_lower:
                score = 50
            
            # Partial word match
            elif any(word.startswith(search_query) for word in name_lower.split()):
                score = 40
            
            if score > 0:
                scored_services.append({
                    **service,
                    'search_score': score
                })
        
        # Sort by score
        scored_services.sort(key=lambda x: x['search_score'], reverse=True)
        
        if scored_services:
            # Update session with search results
            session['all_services'] = scored_services
            session['services_page'] = 0
            session['search_query'] = search_query
            
            await update.message.reply_text(
                f"🔍 *Hasil Pencarian: '{search_query}'*\n\n"
                f"📊 Ditemukan: *{len(scored_services)}* layanan\n\n"
                "*Pilih layanan:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_services_keyboard_paginated(
                    scored_services,
                    page=0,
                    items_per_page=ITEMS_PER_PAGE,
                    show_search=True
                )
            )
            return SELECT_SERVICE_FLOW
        else:
            await update.message.reply_text(
                f"❌ *Tidak Ditemukan*\n\n"
                f"Tidak ada layanan dengan kata kunci '*{search_query}*'.\n\n"
                "💡 *Tips:*\n"
                "• Coba kata kunci lain\n"
                "• Gunakan kode layanan (contoh: tg, wa)\n"
                "• Gunakan nama layanan (contoh: telegram)\n\n"
                "Ketik ulang pencarian atau /cancel untuk kembali.",
                parse_mode=ParseMode.MARKDOWN
            )
            return SEARCH_SERVICE_FLOW
    
    @staticmethod
    async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle country selection with real-time stock data"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        session = context.user_data.get('buy_session', {})
        
        if not session:
            await query.message.edit_text(
                "❌ Sesi telah berakhir. Gunakan /buy untuk memulai.",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # ====== HANDLE PAGINATION ======
        if data.startswith("countries_page_"):
            new_page = int(data.replace("countries_page_", ""))
            session['countries_page'] = new_page
            countries = session.get('available_countries', [])
            service_code = session.get('selected_service', {}).get('code', '')
            
            await query.message.edit_reply_markup(
                reply_markup=create_countries_keyboard_paginated(
                    countries,
                    page=new_page,
                    items_per_page=ITEMS_PER_PAGE,
                    service_code=service_code
                )
            )
            return SELECT_COUNTRY_FLOW
        
        # ====== HANDLE COUNTRY SELECTION ======
        if data.startswith("country_"):
            country_id = int(data.replace("country_", ""))
            
            countries = session.get('available_countries', [])
            country_info = next(
                (c for c in countries if c['id'] == country_id),
                {'id': country_id, 'name': f'Country {country_id}'}
            )
            
            session['selected_country'] = country_info
            
            # Show loading
            loading_msg = await query.message.reply_text(
                "🔄 *Mengambil data operator...*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Get REAL-TIME operators for this country
            operators_response = await hero_sms_api.get_all_operators(country_id)
            
            await loading_msg.delete()
            
            operators = operators_response.get("operators", [])
            session['available_operators'] = operators
            
            service_name = session.get('selected_service', {}).get('name', 'Unknown')
            
            await query.message.edit_text(
                f"📡 *Pilih Operator*\n\n"
                f"📱 Layanan: *{service_name}*\n"
                f"🌍 Negara: *{country_info['name']}* (ID: {country_id})\n"
                f"📊 Operator tersedia: *{len(operators)}*\n"
                f"📦 Total stok: *{country_info.get('total_available', 0):,}*\n"
                f"💵 Harga mulai: *${country_info.get('min_price', 0):.4f}*\n\n"
                "*Pilih operator atau gunakan 'Any Operator':*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_operators_keyboard(
                    operators,
                    country_id=country_id,
                    service_code=session.get('selected_service', {}).get('code', '')
                )
            )
            return SELECT_OPERATOR_FLOW
        
        # ====== HANDLE BACK ======
        if data == "back_to_services":
            all_services = session.get('all_services', [])
            await query.message.edit_text(
                "📱 *Pilih Layanan*\n\n"
                "Pilih layanan atau cari dengan kata kunci:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_services_keyboard_paginated(
                    all_services,
                    page=session.get('services_page', 0),
                    items_per_page=ITEMS_PER_PAGE
                )
            )
            return SELECT_SERVICE_FLOW
        
        return SELECT_COUNTRY_FLOW
    
    @staticmethod
    async def handle_operator_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle operator selection and show ALL price tiers in real-time"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        session = context.user_data.get('buy_session', {})
        
        if not session:
            await query.message.edit_text(
                "❌ Sesi telah berakhir. Gunakan /buy untuk memulai.",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # ====== HANDLE OPERATOR SELECTION ======
        if data == "any_operator":
            session['selected_operator'] = None
            operator_name = "Any Operator"
        elif data.startswith("operator_"):
            operator_name = data.replace("operator_", "")
            session['selected_operator'] = operator_name
        elif data == "back_to_countries":
            countries = session.get('available_countries', [])
            service_code = session.get('selected_service', {}).get('code', '')
            
            await query.message.edit_text(
                "🌍 *Pilih Negara*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_countries_keyboard_paginated(
                    countries,
                    page=session.get('countries_page', 0),
                    items_per_page=ITEMS_PER_PAGE,
                    service_code=service_code
                )
            )
            return SELECT_COUNTRY_FLOW
        else:
            return SELECT_OPERATOR_FLOW
        
        # Show loading
        loading_msg = await query.message.reply_text(
            "🔄 *Mengambil data penawaran real-time...*\n"
            "Mengambil semua tier harga yang tersedia.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Get REAL-TIME offers with ALL price tiers
        service_code = session.get('selected_service', {}).get('code', '')
        country_id = session.get('selected_country', {}).get('id', 0)
        
        offers_response = await hero_sms_api.get_activation_offers_real_time(
            services=service_code,
            countries=str(country_id)
        )
        
        await loading_msg.delete()
        
        if offers_response.get("status") == "success" and offers_response.get("data"):
            service_offers = offers_response["data"].get(service_code, {})
            country_offers = service_offers.get("countries", {}).get(str(country_id), {})
            
            if country_offers and country_offers.get("price_tiers"):
                price_tiers = country_offers["price_tiers"]
                total_stock = sum(t.get("available_count", 0) for t in price_tiers)
                
                # Store in session
                session['current_offers'] = country_offers
                session['price_tiers'] = price_tiers
                
                service_name = session.get('selected_service', {}).get('name', 'Unknown')
                country_name = session.get('selected_country', {}).get('name', 'Unknown')
                
                await query.message.edit_text(
                    f"💰 *Penawaran Tersedia*\n\n"
                    f"📱 Layanan: *{service_name}*\n"
                    f"🌍 Negara: *{country_name}*\n"
                    f"📡 Operator: *{operator_name}*\n"
                    f"📊 Total Stok: *{total_stock:,}*\n"
                    f"💵 Harga Default: *${country_offers.get('prices', {}).get('default', 0):.4f}*\n"
                    f"📈 Tier Harga: *{len(price_tiers)}*\n\n"
                    "*Pilih Tier Harga:*\n"
                    "🟢 Banyak (>1000) | 🟡 Sedang (>100) | 🟠 Sedikit (>0) | 🔴 Habis",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=create_price_tiers_keyboard(
                        price_tiers,
                        service_code=service_code,
                        country_id=country_id
                    )
                )
                return SELECT_OFFER_FLOW
            else:
                await query.message.edit_text(
                    "❌ *Tidak Ada Penawaran*\n\n"
                    "Tidak ada nomor tersedia untuk kombinasi ini.\n"
                    "Silakan pilih negara atau layanan lain.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=create_operators_keyboard(
                        session.get('available_operators', []),
                        country_id=country_id,
                        service_code=service_code
                    )
                )
                return SELECT_OPERATOR_FLOW
        else:
            await query.message.edit_text(
                "❌ Gagal mengambil data penawaran.\nSilakan coba lagi.",
                reply_markup=create_operators_keyboard(
                    session.get('available_operators', []),
                    country_id=country_id,
                    service_code=service_code
                )
            )
            return SELECT_OPERATOR_FLOW
    
    @staticmethod
    async def handle_offer_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle price tier selection and confirm purchase"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        session = context.user_data.get('buy_session', {})
        
        if not session:
            await query.message.edit_text(
                "❌ Sesi telah berakhir. Gunakan /buy untuk memulai.",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # ====== HANDLE BACK ======
        if data == "back_to_operators":
            operators = session.get('available_operators', [])
            country_id = session.get('selected_country', {}).get('id', 0)
            service_code = session.get('selected_service', {}).get('code', '')
            
            await query.message.edit_text(
                "📡 *Pilih Operator*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_operators_keyboard(
                    operators,
                    country_id=country_id,
                    service_code=service_code
                )
            )
            return SELECT_OPERATOR_FLOW
        
        # ====== HANDLE TIER SELECTION ======
        if data.startswith("tier_"):
            try:
                tier_json = data.replace("tier_", "")
                tier_data = json.loads(tier_json)
                
                session['selected_tier'] = tier_data
                
                service_name = session.get('selected_service', {}).get('name', 'Unknown')
                country_name = session.get('selected_country', {}).get('name', 'Unknown')
                operator_name = session.get('selected_operator', 'Any')
                
                price = tier_data.get('price', 0)
                available = tier_data.get('available_count', 0)
                
                await query.message.edit_text(
                    f"📋 *Konfirmasi Pembelian*\n\n"
                    f"📱 Layanan: *{service_name}*\n"
                    f"🌍 Negara: *{country_name}*\n"
                    f"📡 Operator: *{operator_name}*\n"
                    f"💰 Harga: *${price:.4f}*\n"
                    f"📊 Stok Tersedia: *{available:,}*\n\n"
                    "*Konfirmasi pembelian?*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Konfirmasi", callback_data="confirm_purchase"),
                            InlineKeyboardButton("❌ Batal", callback_data="cancel_purchase")
                        ],
                        [InlineKeyboardButton("◀️ Kembali ke Tier", callback_data="back_to_tiers")]
                    ])
                )
                return CONFIRM_PURCHASE_FLOW
            except json.JSONDecodeError:
                await query.answer("❌ Data tier tidak valid", show_alert=True)
                return SELECT_OFFER_FLOW
        
        return SELECT_OFFER_FLOW
    
    @staticmethod
    async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process purchase with real-time number request"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        session = context.user_data.get('buy_session', {})
        
        if data == "cancel_purchase":
            await query.message.edit_text(
                "❌ *Pembelian Dibatalkan*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
            context.user_data.pop('buy_session', None)
            return ConversationHandler.END
        
        if data == "back_to_tiers":
            price_tiers = session.get('price_tiers', [])
            service_code = session.get('selected_service', {}).get('code', '')
            country_id = session.get('selected_country', {}).get('id', 0)
            
            await query.message.edit_text(
                "💰 *Pilih Tier Harga*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_price_tiers_keyboard(
                    price_tiers,
                    service_code=service_code,
                    country_id=country_id
                )
            )
            return SELECT_OFFER_FLOW
        
        if data == "confirm_purchase":
            user = await UserHandlers._get_authenticated_user(update, context)
            if not user:
                await query.message.edit_text(
                    "❌ Silakan login terlebih dahulu dengan /login"
                )
                return ConversationHandler.END
            
            tier = session.get('selected_tier', {})
            price = tier.get('price', 0)
            
            # Check balance
            if user.balance < price:
                await query.message.edit_text(
                    f"❌ *Saldo Tidak Mencukupi*\n\n"
                    f"💰 Saldo: Rp {user.balance:,.0f}\n"
                    f"💵 Harga: ${price:.4f}\n\n"
                    "Silakan top up terlebih dahulu dengan /topup",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_menu_keyboard()
                )
                return ConversationHandler.END
            
            # Show processing message
            processing_msg = await query.message.reply_text(
                "🔄 *Memproses pembelian...*\n"
                "Mengambil nomor dari HeroSMS.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Request number from HeroSMS
            service_code = session.get('selected_service', {}).get('code', '')
            country_id = session.get('selected_country', {}).get('id', 0)
            operator = session.get('selected_operator')
            
            number_response = await hero_sms_api.get_number_advanced(
                service=service_code,
                country=country_id,
                operator=operator,
                max_price=price
            )
            
            await processing_msg.delete()
            
            if number_response.get("status") == "success" and number_response.get("data"):
                number_data = number_response["data"]
                activation_id = number_data.get("activationId")
                phone_number = number_data.get("phoneNumber")
                actual_cost = number_data.get("activationCost", price)
                
                # Save to database
                activation_record = await db.create_activation({
                    'user_id': user.telegram_id,
                    'activation_id': activation_id,
                    'service_code': service_code,
                    'service_name': session.get('selected_service', {}).get('name', ''),
                    'country_id': country_id,
                    'country_name': session.get('selected_country', {}).get('name', ''),
                    'operator': operator or 'any',
                    'phone_number': phone_number,
                    'cost': actual_cost,
                    'currency': number_data.get('currency', 840),
                    'status': 'pending'
                })
                
                # Update balance
                new_balance = user.balance - actual_cost
                await db.update_user_balance(user.telegram_id, new_balance)
                
                # Create transaction
                await db.create_transaction({
                    'user_id': user.telegram_id,
                    'type': 'purchase',
                    'amount': -actual_cost,
                    'balance_before': user.balance,
                    'balance_after': new_balance,
                    'description': f"Pembelian {service_code} - {session.get('selected_country', {}).get('name', '')}",
                    'status': 'completed'
                })
                
                # Clear session
                context.user_data.pop('buy_session', None)
                
                # Success message with all details
                success_text = (
                    f"✅ *Pembelian Berhasil!*\n\n"
                    f"📱 *Nomor:* `{phone_number}`\n"
                    f"🆔 *ID Aktivasi:* `{activation_id}`\n"
                    f"📡 *Layanan:* {session.get('selected_service', {}).get('name', '')}\n"
                    f"🌍 *Negara:* {session.get('selected_country', {}).get('name', '')}\n"
                    f"💵 *Harga:* ${actual_cost:.4f}\n"
                    f"💰 *Sisa Saldo:* Rp {new_balance:,.0f}\n\n"
                    f"⏰ *Status:* Menunggu SMS\n\n"
                    "📋 *Perintah Berguna:*\n"
                    f"`/status` - Cek status aktivasi\n"
                    f"`/sms {activation_id}` - Lihat SMS\n"
                    f"`/cancel_activation {activation_id}` - Batalkan"
                )
                
                await query.message.edit_text(
                    success_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📱 Beli Lagi", callback_data="buy_number")],
                        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
                    ])
                )
                
                logger.info(f"Purchase successful: User {user.telegram_id}, Activation {activation_id}")
                return ConversationHandler.END
            else:
                error_msg = number_response.get("message", "Gagal mendapatkan nomor")
                
                await query.message.edit_text(
                    f"❌ *Pembelian Gagal*\n\n"
                    f"Alasan: {error_msg}\n\n"
                    "Silakan coba lagi atau pilih tier lain.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_menu_keyboard()
                )
                return ConversationHandler.END
    
    # ========================================================================
    # TOP UP FLOW
    # ========================================================================
    
    @staticmethod
    async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start top up flow"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"💰 *Top Up Saldo*\n\n"
            f"💳 Saldo saat ini: Rp {user.balance:,.0f}\n\n"
            "*Pilih nominal atau masukkan nominal khusus:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_topup_menu_keyboard()
        )
        return TOPUP_AMOUNT
    
    @staticmethod
    async def topup_amount_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle top up amount selection"""
        query = update.callback_query
        
        if query:
            await query.answer()
            data = query.data
            
            if data == "custom_amount":
                await query.message.edit_text(
                    "💵 *Masukkan Nominal*\n\n"
                    "Masukkan nominal top up:\n"
                    "• Minimal: Rp 10,000\n"
                    "• Maksimal: Rp 10,000,000\n\n"
                    "Contoh: `50000`\n"
                    "Kirim /cancel untuk membatalkan.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return TOPUP_AMOUNT
            
            if data == "back_to_main":
                await query.message.edit_text(
                    "🏠 Menu Utama",
                    reply_markup=get_main_menu_keyboard()
                )
                return ConversationHandler.END
            
            amount = int(data)
            return await UserHandlers._process_topup(query.message, context, amount)
        
        return TOPUP_AMOUNT
    
    @staticmethod
    async def topup_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle custom top up amount input"""
        text = update.message.text.strip()
        
        if text == "/cancel":
            await update.message.reply_text(
                "❌ Top up dibatalkan.",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        try:
            amount = int(text)
            
            if amount < 10000:
                await update.message.reply_text(
                    "❌ Minimal top up Rp 10,000.\n"
                    "Silakan masukkan nominal yang valid:"
                )
                return TOPUP_AMOUNT
            
            if amount > 10000000:
                await update.message.reply_text(
                    "❌ Maksimal top up Rp 10,000,000.\n"
                    "Silakan masukkan nominal yang valid:"
                )
                return TOPUP_AMOUNT
            
            return await UserHandlers._process_topup(update.message, context, amount)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Masukkan angka yang valid.\n"
                "Contoh: 50000"
            )
            return TOPUP_AMOUNT
    
    @staticmethod
    async def _process_topup(message, context: ContextTypes.DEFAULT_TYPE, amount: int):
        """Process top up with Qrispy payment"""
        user = await UserHandlers._get_authenticated_user(message, context)
        if not user:
            return ConversationHandler.END
        
        # Generate unique payment reference
        payment_ref = f"TOPUP-{user.telegram_id}-{amount}-{int(time.time())}"
        
        loading_msg = await message.reply_text(
            "🔄 *Membuat QRIS...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Generate QRIS
        qris_response = await qrispy_api.generate_qris(
            amount=amount,
            payment_reference=payment_ref
        )
        
        await loading_msg.delete()
        
        if qris_response.get("status") == "success":
            qris_data = qris_response["data"]
            qris_id = qris_data.get("qris_id")
            qris_image_url = qris_data.get("qris_image_url")
            expired_at = qris_data.get("expired_at", "15 menit")
            
            # Save to database
            await db.create_topup({
                'user_id': user.telegram_id,
                'amount': amount,
                'qris_id': qris_id,
                'qris_image_url': qris_image_url,
                'expired_at': expired_at,
                'status': 'pending'
            })
            
            # Send QRIS image
            await message.reply_photo(
                photo=qris_image_url,
                caption=(
                    f"💳 *QRIS Payment*\n\n"
                    f"📦 Nominal: *Rp {amount:,.0f}*\n"
                    f"🆔 QRIS ID: `{qris_id}`\n"
                    f"📊 Status: *Menunggu Pembayaran*\n"
                    f"⏰ Kadaluarsa: {expired_at}\n\n"
                    "📱 *Cara Bayar:*\n"
                    "1. Buka aplikasi e-wallet/m-banking\n"
                    "2. Scan QRIS di atas\n"
                    "3. Konfirmasi pembayaran\n\n"
                    "⏳ Saldo akan otomatis bertambah setelah pembayaran berhasil."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔄 Cek Status", callback_data=f"check_topup_{qris_id}"),
                        InlineKeyboardButton("❌ Batal", callback_data=f"cancel_topup_{qris_id}")
                    ]
                ])
            )
            return ConversationHandler.END
        else:
            await message.reply_text(
                "❌ *Gagal Membuat QRIS*\n\n"
                "Silakan coba lagi nanti.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
    
    @staticmethod
    async def check_topup_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check top up payment status"""
        query = update.callback_query
        await query.answer()
        
        qris_id = query.data.replace("check_topup_", "")
        
        status_response = await qrispy_api.check_qris_status(qris_id)
        
        if status_response.get("status") == "success":
            payment_status = status_response.get("data", {}).get("status", "pending")
            
            if payment_status == "paid":
                # Update database
                await db.update_topup_status(qris_id, "completed")
                
                topup = await db.get_topup_by_qris_id(qris_id)
                if topup:
                    user = await db.get_user_by_telegram_id(topup.user_id)
                    new_balance = user.balance + topup.amount
                    await db.update_user_balance(topup.user_id, new_balance)
                    
                    await db.create_transaction({
                        'user_id': topup.user_id,
                        'type': 'topup',
                        'amount': topup.amount,
                        'balance_before': user.balance,
                        'balance_after': new_balance,
                        'description': f"Top up via QRIS",
                        'status': 'completed',
                        'payment_reference': qris_id
                    })
                
                await query.message.reply_text(
                    f"✅ *Pembayaran Berhasil!*\n\n"
                    f"💰 Top Up: Rp {topup.amount:,.0f}\n"
                    f"💳 Saldo Sekarang: Rp {new_balance:,.0f}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif payment_status == "pending":
                await query.answer(
                    "⏰ Pembayaran masih pending. Silakan selesaikan pembayaran.",
                    show_alert=True
                )
            elif payment_status in ["expired", "cancelled"]:
                await db.update_topup_status(qris_id, payment_status)
                await query.message.reply_text(
                    f"❌ QRIS telah {payment_status}.\nSilakan buat top up baru dengan /topup"
                )
        else:
            await query.answer(
                "❌ Gagal mengecek status. Silakan coba lagi.",
                show_alert=True
            )
    
    @staticmethod
    async def cancel_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel pending top up"""
        query = update.callback_query
        await query.answer()
        
        qris_id = query.data.replace("cancel_topup_", "")
        
        await qrispy_api.cancel_qris(qris_id)
        await db.update_topup_status(qris_id, "cancelled")
        
        await query.message.edit_caption(
            caption=f"{query.message.caption}\n\n❌ *DIBATALKAN*",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========================================================================
    # USER INFO & PROFILE
    # ========================================================================
    
    @staticmethod
    async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check user balance"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        await update.message.reply_text(
            f"💳 *Saldo Anda*\n\n"
            f"💰 Saldo: *Rp {user.balance:,.0f}*\n"
            f"👤 Nama: {user.first_name}\n"
            f"📊 Status: {user.status.value}\n\n"
            "Gunakan /topup untuk isi saldo.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_profile_keyboard()
        )
    
    @staticmethod
    async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user profile"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        # Get stats
        total_activations = await db.get_user_activation_count(user.telegram_id)
        total_transactions = await db.get_user_transaction_count(user.telegram_id)
        
        profile_text = (
            f"👤 *Profil Anda*\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"📱 Telegram ID: `{user.telegram_id}`\n"
            f"👤 Username: @{user.username or 'Tidak ada'}\n"
            f"📝 Nama: {user.first_name} {user.last_name or ''}\n"
            f"💰 Saldo: Rp {user.balance:,.0f}\n"
            f"📊 Status: {user.status.value}\n"
            f"📱 Total Aktivasi: {total_activations}\n"
            f"💳 Total Transaksi: {total_transactions}\n"
            f"📅 Bergabung: {user.created_at.strftime('%d %B %Y') if user.created_at else 'N/A'}"
        )
        
        await update.message.reply_text(
            profile_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_profile_keyboard()
        )
    
    @staticmethod
    async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show history menu"""
        await update.message.reply_text(
            "📜 *Riwayat*\n\n"
            "Pilih jenis riwayat:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_history_keyboard()
        )
    
    @staticmethod
    async def activation_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show activation history"""
        query = update.callback_query
        await query.answer()
        
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        activations = await db.get_user_activations(user.telegram_id, limit=20)
        
        if activations:
            history_text = "*📱 Riwayat Aktivasi*\n\n"
            
            for i, act in enumerate(activations, 1):
                status_emoji = {
                    'pending': '⏳',
                    'waiting_code': '🔄',
                    'code_received': '📨',
                    'completed': '✅',
                    'cancelled': '❌',
                    'expired': '⏰'
                }.get(act.status.value if hasattr(act.status, 'value') else str(act.status), '❓')
                
                history_text += (
                    f"{i}. {status_emoji} *{act.service_name}* - {act.country_name}\n"
                    f"   📱 `{act.phone_number or 'N/A'}`\n"
                    f"   🆔 `{act.activation_id or 'N/A'}`\n"
                    f"   💵 ${act.cost or 0:.4f}\n"
                    f"   📅 {act.created_at.strftime('%d/%m/%Y %H:%M') if act.created_at else 'N/A'}\n\n"
                )
        else:
            history_text = "📱 Belum ada aktivasi.\nGunakan /buy untuk membeli nomor."
        
        await query.message.edit_text(
            history_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Riwayat Transaksi", callback_data="transaction_history")],
                [InlineKeyboardButton("◀️ Kembali", callback_data="back_to_main")]
            ])
        )
    
    @staticmethod
    async def transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show transaction history"""
        query = update.callback_query
        await query.answer()
        
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        transactions = await db.get_user_transactions(user.telegram_id, limit=20)
        
        if transactions:
            history_text = "*💰 Riwayat Transaksi*\n\n"
            
            for i, trx in enumerate(transactions, 1):
                emoji = "🟢" if trx.amount > 0 else "🔴"
                status_emoji = "✅" if trx.status.value == "completed" else "⏳"
                
                history_text += (
                    f"{i}. {emoji} *{trx.type.value.upper()}*\n"
                    f"   {status_emoji} Rp {abs(trx.amount):,.0f}\n"
                    f"   📝 {trx.description or 'N/A'}\n"
                    f"   📅 {trx.created_at.strftime('%d/%m/%Y %H:%M') if trx.created_at else 'N/A'}\n\n"
                )
        else:
            history_text = "💰 Belum ada transaksi.\nGunakan /topup untuk isi saldo."
        
        await query.message.edit_text(
            history_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Riwayat Aktivasi", callback_data="activation_history")],
                [InlineKeyboardButton("◀️ Kembali", callback_data="back_to_main")]
            ])
        )
    
    # ========================================================================
    # ACTIVATION MANAGEMENT
    # ========================================================================
    
    @staticmethod
    async def check_activation_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check all active activation statuses"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        loading_msg = await update.message.reply_text(
            "🔄 *Mengambil status aktivasi...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Get active activations from HeroSMS
        active_response = await hero_sms_api.get_active_activations()
        
        await loading_msg.delete()
        
        if active_response.get("status") == "success" and active_response.get("data"):
            activations = active_response["data"]
            
            status_text = "*📊 Status Aktivasi Aktif*\n\n"
            
            for act in activations:
                status_code = act.get('activationStatus', '?')
                status_map = {
                    '1': '⏳ Menunggu',
                    '2': '🔄 Proses',
                    '3': '📡 Request SMS',
                    '4': '📨 SMS Diterima',
                    '5': '🔄 Resend',
                    '6': '✅ Selesai',
                    '7': '❌ Batal',
                    '8': '🚫 Dibatalkan'
                }
                
                status_name = status_map.get(str(status_code), f'Status {status_code}')
                
                status_text += (
                    f"🆔 `{act.get('activationId', 'N/A')}`\n"
                    f"📱 `{act.get('phoneNumber', 'N/A')}`\n"
                    f"📡 {act.get('serviceCode', 'N/A')}\n"
                    f"🌍 {act.get('countryName', 'N/A')}\n"
                    f"📊 {status_name}\n"
                    f"💵 ${act.get('activationCost', 0)}\n\n"
                )
            
            # Create keyboard for each activation
            keyboard = []
            for act in activations:
                activation_id = act.get('activationId')
                keyboard.append([
                    InlineKeyboardButton(
                        f"📨 SMS {activation_id}", 
                        callback_data=f"sms_{activation_id}"
                    ),
                    InlineKeyboardButton(
                        f"✅ Selesai {activation_id}",
                        callback_data=f"finish_{activation_id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="check_status")])
            keyboard.append([InlineKeyboardButton("◀️ Kembali", callback_data="back_to_main")])
            
            await update.message.reply_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                "📊 Tidak ada aktivasi aktif saat ini.\n\n"
                "Gunakan /buy untuk membeli nomor baru.",
                reply_markup=get_main_menu_keyboard()
            )
    
    @staticmethod
    async def get_sms_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get all SMS for an activation"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ *Gunakan:* `/sms <activation_id>`\n"
                "Contoh: `/sms 635468024`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        activation_id = context.args[0]
        
        loading_msg = await update.message.reply_text(
            "🔄 *Mengambil SMS...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        sms_response = await hero_sms_api.get_all_sms(int(activation_id))
        
        await loading_msg.delete()
        
        if sms_response.get("data"):
            sms_list = sms_response["data"]
            
            sms_text = f"*📨 SMS untuk Aktivasi #{activation_id}*\n\n"
            
            for i, sms in enumerate(sms_list, 1):
                sms_type = sms.get('type', 'sms')
                type_emoji = "📱" if sms_type == "sms" else "📞"
                
                sms_text += (
                    f"{i}. {type_emoji} *{sms.get('phoneFrom', 'Unknown')}*\n"
                    f"   📝 `{sms.get('text', 'No text')}`\n"
                    f"   🔢 Kode: `{sms.get('code', 'No code')}`\n"
                    f"   📅 {sms.get('date', 'Unknown')}\n\n"
                )
            
            if not sms_list:
                sms_text += "Belum ada SMS diterima.\n"
        else:
            sms_text = "❌ Tidak ada SMS atau aktivasi tidak ditemukan."
        
        await update.message.reply_text(
            sms_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"sms_{activation_id}")],
                [InlineKeyboardButton("◀️ Kembali", callback_data="check_status")]
            ])
        )
    
    @staticmethod
    async def finish_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Complete an activation"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        # Handle both command and callback
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            activation_id = query.data.replace("finish_", "")
            message = query.message
        else:
            if not context.args:
                await update.message.reply_text(
                    "❌ Gunakan: `/finish <activation_id>`\n"
                    "Contoh: `/finish 635468024`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            activation_id = context.args[0]
            message = update.message
        
        response = await hero_sms_api.finish_activation(int(activation_id))
        
        if response.get("status") == "success":
            await db.update_activation_status(activation_id, "completed")
            
            await message.reply_text(
                f"✅ *Aktivasi Selesai!*\n\n"
                f"🆔 ID: `{activation_id}`\n"
                f"Status: *COMPLETED*\n\n"
                "Terima kasih telah menggunakan layanan kami!",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text(
                f"❌ Gagal menyelesaikan aktivasi.\n{response.get('message', '')}"
            )
    
    @staticmethod
    async def cancel_activation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel an activation"""
        user = await UserHandlers._get_authenticated_user(update, context)
        if not user:
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Gunakan: `/cancel_activation <activation_id>`\n"
                "Contoh: `/cancel_activation 635468024`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        activation_id = context.args[0]
        
        response = await hero_sms_api.cancel_activation(int(activation_id))
        
        if response.get("status") == "success":
            await db.update_activation_status(activation_id, "cancelled")
            
            # Get activation cost for refund
            activation = await db.get_activation_by_id(activation_id)
            if activation and activation.cost:
                # Refund
                new_balance = user.balance + activation.cost
                await db.update_user_balance(user.telegram_id, new_balance)
                
                await db.create_transaction({
                    'user_id': user.telegram_id,
                    'type': 'refund',
                    'amount': activation.cost,
                    'balance_before': user.balance,
                    'balance_after': new_balance,
                    'description': f"Refund aktivasi {activation_id}",
                    'status': 'completed'
                })
            
            await update.message.reply_text(
                f"❌ *Aktivasi Dibatalkan*\n\n"
                f"🆔 ID: `{activation_id}`\n"
                f"💰 Dana dikembalikan: ${activation.cost if activation else 0:.4f}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ Gagal membatalkan aktivasi.\n{response.get('message', '')}"
            )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    async def _get_authenticated_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get authenticated user from context or database"""
        if update.callback_query:
            telegram_id = update.callback_query.from_user.id
        else:
            telegram_id = update.effective_user.id
        
        # Check cached user
        if context.user_data.get('user', {}).get('telegram_id') == telegram_id:
            user_data = context.user_data['user']
            user = await db.get_user_by_telegram_id(telegram_id)
            if user and user.status.value == 'active':
                return user
        
        # Get from database
        user = await db.get_user_by_telegram_id(telegram_id)
        
        if not user:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "❌ Anda belum terdaftar! Gunakan /start untuk mendaftar."
                )
            else:
                await update.message.reply_text(
                    "❌ Anda belum terdaftar! Gunakan /start untuk mendaftar."
                )
            return None
        
        if user.status.value == "banned":
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "❌ Akun Anda telah dibanned!"
                )
            else:
                await update.message.reply_text(
                    "❌ Akun Anda telah dibanned!"
                )
            return None
        
        # Cache user data
        context.user_data['user'] = {
            'id': user.id,
            'telegram_id': user.telegram_id,
            'username': user.username,
            'first_name': user.first_name,
            'balance': user.balance,
            'is_admin': user.is_admin
        }
        
        return user
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        help_text = (
            "📚 *Bantuan HeroSMS Bot*\n\n"
            "*Perintah Utama:*\n"
            "/start - Mulai bot\n"
            "/buy - Beli nomor baru\n"
            "/topup - Isi saldo\n"
            "/balance - Cek saldo\n"
            "/profile - Lihat profil\n"
            "/history - Riwayat\n"
            "/status - Status aktivasi\n\n"
            "*Manajemen Aktivasi:*\n"
            "/sms `<id>` - Lihat SMS\n"
            "/finish `<id>` - Selesaikan aktivasi\n"
            "/cancel_activation `<id>` - Batalkan aktivasi\n\n"
            "*Admin:*\n"
            "/admin - Panel admin\n\n"
            "📞 Butuh bantuan? Hubungi: @admin_herosms"
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
    
    @staticmethod
    async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Back to main menu"""
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "🏠 *Menu Utama*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    if update.callback_query:
        await update.callback_query.message.reply_text(
            "❌ Operasi dibatalkan.",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Operasi dibatalkan.",
            reply_markup=get_main_menu_keyboard()
        )
    return ConversationHandler.END