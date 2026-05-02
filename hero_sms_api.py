import httpx
from typing import Dict, List, Optional, Any, Tuple
import json
from config import settings
import logging

logger = logging.getLogger(__name__)

class HeroSMSAPI:
    def __init__(self):
        self.api_key = settings.HEROSMS_API_KEY
        self.base_url = settings.HEROSMS_API_URL
        self.stub_url = settings.HEROSMS_STUB_URL
        self.headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json"
        }
        # Cache untuk menyimpan data sementara
        self._services_cache = None
        self._countries_cache = None
        self._operators_cache = {}
        self._offers_cache = {}
        self._cache_timestamp = {}
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                           data: Dict = None, use_stub: bool = False) -> Dict:
        """Make HTTP request to HeroSMS API with retry logic"""
        base = self.stub_url if use_stub else self.base_url
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):  # Retry up to 3 times
                try:
                    if method.upper() == "GET":
                        if use_stub:
                            response = await client.get(f"{base}", params=params)
                        else:
                            response = await client.get(f"{base}{endpoint}", params=params, headers=self.headers)
                    elif method.upper() == "POST":
                        response = await client.post(f"{base}{endpoint}", json=data, headers=self.headers)
                    elif method.upper() == "DELETE":
                        response = await client.delete(f"{base}{endpoint}", headers=self.headers)
                    
                    response.raise_for_status()
                    
                    # Parse response
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        # Handle plain text responses from SMS-Activate API
                        return {"text_response": response.text}
                        
                except httpx.HTTPError as e:
                    logger.error(f"HeroSMS API Error (attempt {attempt + 1}): {e}")
                    if attempt == 2:  # Last attempt
                        return {"error": str(e)}
                    await asyncio.sleep(1)  # Wait before retry
    
    # ========== Enhanced Activation Offers (REAL-TIME, NO LIMIT) ==========
    async def get_activation_offers_real_time(self, services: Optional[str] = None, 
                                              countries: Optional[str] = None) -> Dict:
        """
        Get ALL activation offers without any limits
        Returns complete data with all price tiers and stock information
        """
        params = {}
        if services:
            params["services"] = services
        if countries:
            params["countries"] = countries
        
        # Force no caching for real-time data
        params["_t"] = int(time.time())
        
        response = await self._make_request("GET", "/activations/offers", params=params)
        
        if "data" in response:
            # Process and enrich the data
            enriched_data = await self._enrich_offers_data(response["data"])
            return {"status": "success", "data": enriched_data}
        
        return response
    
    async def _enrich_offers_data(self, offers_data: Dict) -> Dict:
        """
        Enrich offers data with additional information:
        - Service names
        - Country names
        - Price tier details
        - Stock availability per tier
        """
        enriched = {}
        
        # Get services and countries mapping
        services_map = await self._get_services_map()
        countries_map = await self._get_countries_map()
        
        for service_code, countries in offers_data.items():
            service_name = services_map.get(service_code, service_code)
            
            enriched[service_code] = {
                "service_name": service_name,
                "countries": {}
            }
            
            for country_id, offer_data in countries.items():
                country_name = countries_map.get(int(country_id), f"Country {country_id}")
                
                # Process price tiers
                price_tiers = []
                if "map" in offer_data:
                    for price_str, count in offer_data["map"].items():
                        price = float(price_str)
                        price_tiers.append({
                            "price": price,
                            "available_count": count,
                            "price_per_unit": price
                        })
                    # Sort by price ascending
                    price_tiers.sort(key=lambda x: x["price"])
                
                # Calculate total available
                total_available = sum(tier["available_count"] for tier in price_tiers)
                
                enriched[service_code]["countries"][country_id] = {
                    "country_name": country_name,
                    "prices": {
                        "default": offer_data.get("prices", {}).get("default", 0),
                        "retail": offer_data.get("prices", {}).get("retail", 0),
                        "min": offer_data.get("prices", {}).get("min", 0),
                    },
                    "counts": {
                        "total": offer_data.get("counts", {}).get("total", 0),
                        "physical": offer_data.get("counts", {}).get("physical", 0),
                        "default_price": offer_data.get("counts", {}).get("defaultPrice", 0),
                    },
                    "price_tiers": price_tiers,  # ALL price tiers without limit
                    "total_available": total_available,
                    "has_stock": total_available > 0
                }
        
        return enriched
    
    async def _get_services_map(self) -> Dict[str, str]:
        """Get mapping of service codes to names"""
        if not self._services_cache:
            response = await self.get_services_list()
            self._services_cache = {}
            
            if isinstance(response, dict) and "services" in response:
                for service in response["services"]:
                    self._services_cache[service["code"]] = service["name"]
            elif isinstance(response, list):
                for service in response:
                    if isinstance(service, dict):
                        self._services_cache[service.get("code", "")] = service.get("name", "")
        
        return self._services_cache
    
    async def _get_countries_map(self) -> Dict[int, str]:
        """Get mapping of country IDs to names"""
        if not self._countries_cache:
            response = await self.get_countries()
            self._countries_cache = {}
            
            if isinstance(response, list):
                for country in response:
                    if isinstance(country, dict):
                        self._countries_cache[country.get("id", 0)] = country.get("eng", "Unknown")
        
        return self._countries_cache
    
    # ========== Enhanced Get Number with All Options ==========
    async def get_number_advanced(self, service: str, country: int, 
                                  operator: Optional[str] = None,
                                  max_price: Optional[float] = None,
                                  fixed_price: Optional[str] = None,
                                  ref: Optional[str] = None,
                                  phone_exception: Optional[str] = None) -> Dict:
        """
        Request number with all available parameters
        Returns complete activation information
        """
        params = {
            "action": "getNumberV2",
            "api_key": self.api_key,
            "service": service,
            "country": country
        }
        
        if operator and operator != "any":
            params["operator"] = operator
        if max_price:
            params["maxPrice"] = max_price
        if fixed_price:
            params["fixedPrice"] = fixed_price
        if ref:
            params["ref"] = ref
        if phone_exception:
            params["phoneException"] = phone_exception
        
        response = await self._make_request("GET", "", params=params, use_stub=True)
        
        # Parse response
        if isinstance(response, dict):
            if "activationId" in response:
                return {
                    "status": "success",
                    "data": response
                }
            elif "text_response" in response:
                text = response["text_response"]
                if text.startswith("ACCESS_NUMBER:"):
                    # Parse ACCESS_NUMBER:activation_id:phone_number
                    parts = text.split(":")
                    return {
                        "status": "success",
                        "data": {
                            "activationId": parts[1],
                            "phoneNumber": parts[2]
                        }
                    }
                elif text == "NO_NUMBERS":
                    return {"status": "error", "message": "No numbers available"}
                elif text == "NO_BALANCE":
                    return {"status": "error", "message": "Insufficient balance"}
        
        return response
    
    # ========== Enhanced Get All Services (NO LIMIT) ==========
    async def get_all_services(self) -> Dict:
        """Get complete list of all services without pagination"""
        response = await self.get_services_list()
        
        if isinstance(response, dict) and "services" in response:
            # Return all services sorted alphabetically
            services = response["services"]
            services.sort(key=lambda x: x.get("name", "").lower())
            
            return {
                "status": "success",
                "total": len(services),
                "services": services
            }
        
        return response
    
    # ========== Enhanced Get All Countries (NO LIMIT) ==========
    async def get_all_countries(self) -> Dict:
        """Get complete list of all countries without pagination"""
        response = await self.get_countries()
        
        if isinstance(response, list):
            # Filter visible countries and sort
            visible_countries = [c for c in response if isinstance(c, dict) and c.get("visible", 0) == 1]
            visible_countries.sort(key=lambda x: x.get("eng", ""))
            
            return {
                "status": "success",
                "total": len(visible_countries),
                "countries": visible_countries
            }
        
        return {"status": "error", "message": "Failed to fetch countries"}
    
    # ========== Enhanced Get Operators (NO LIMIT) ==========
    async def get_all_operators(self, country: int) -> Dict:
        """Get all available operators for a country"""
        response = await self.get_operators(country=country)
        
        if isinstance(response, dict) and "countryOperators" in response:
            operators = response["countryOperators"].get(str(country), [])
            
            return {
                "status": "success",
                "country_id": country,
                "total": len(operators),
                "operators": operators
            }
        
        return {"status": "success", "country_id": country, "total": 0, "operators": []}
    
    # ========== Get Complete Price Information ==========
    async def get_complete_prices(self, service: Optional[str] = None, 
                                  country: Optional[int] = None) -> Dict:
        """
        Get complete price information with all variations
        """
        params = {
            "action": "getPrices",
            "api_key": self.api_key
        }
        
        if service:
            params["service"] = service
        if country:
            params["country"] = country
        
        response = await self._make_request("GET", "", params=params, use_stub=True)
        
        if isinstance(response, dict):
            # Process and structure price data
            processed_prices = {}
            
            for country_id, services in response.items():
                if isinstance(services, dict):
                    processed_prices[country_id] = {}
                    for service_code, price_data in services.items():
                        if isinstance(price_data, dict):
                            processed_prices[country_id][service_code] = {
                                "cost": price_data.get("cost", 0),
                                "count": price_data.get("count", 0),
                                "physical_count": price_data.get("physicalCount", 0)
                            }
            
            return {
                "status": "success",
                "data": processed_prices
            }
        
        return response