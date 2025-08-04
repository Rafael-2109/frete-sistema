#!/usr/bin/env python
"""Test script to verify filters in /faturamento/produtos"""

import requests
from urllib.parse import urlencode

# Base URL - adjust if needed
BASE_URL = "http://localhost:5002/faturamento/produtos"

# Test cases for filters
test_cases = [
    {"name": "No filters", "params": {}},
    {"name": "Filter by date range", "params": {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}},
    {"name": "Filter by client name", "params": {"nome_cliente": "COMERCIAL"}},
    {"name": "Filter by product code", "params": {"cod_produto": "432"}},
    {"name": "Filter by state", "params": {"estado": "ES"}},
    {"name": "Filter by vendor", "params": {"vendedor": "VENDEDOR"}},
    {"name": "Filter by incoterm", "params": {"incoterm": "CIF"}},
    {"name": "Filter by municipality", "params": {"municipio": "SERRA"}},
    {"name": "Filter by NF number", "params": {"numero_nf": "20"}},
    {"name": "Combined filters", "params": {
        "data_inicio": "2025-01-01", 
        "data_fim": "2025-01-31",
        "estado": "ES"
    }},
]

def test_filters():
    """Test each filter combination"""
    print("=" * 80)
    print("TESTING FILTERS FOR /faturamento/produtos")
    print("=" * 80)
    
    for test in test_cases:
        print(f"\n🔍 Testing: {test['name']}")
        print(f"   Parameters: {test['params']}")
        
        # Build URL with parameters
        if test['params']:
            url = f"{BASE_URL}?{urlencode(test['params'])}"
        else:
            url = BASE_URL
            
        print(f"   URL: {url}")
        
        try:
            # Make request with session/cookies if needed
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Check if we got HTML response
                if 'text/html' in response.headers.get('content-type', ''):
                    # Look for key indicators in response
                    html = response.text
                    
                    # Check for records found
                    if "Nenhum registro encontrado" in html:
                        print(f"   ✅ Filter working - No records found")
                    elif "registros" in html or "Registros Encontrados" in html:
                        # Try to extract count from HTML
                        import re
                        match = re.search(r'(\d+)\s*[Rr]egistros', html)
                        if match:
                            count = match.group(1)
                            print(f"   ✅ Filter working - {count} records found")
                        else:
                            print(f"   ✅ Filter working - Records found")
                    else:
                        print(f"   ⚠️  Cannot determine record count from HTML")
                else:
                    print(f"   ❌ Unexpected content type: {response.headers.get('content-type')}")
            elif response.status_code == 302:
                print(f"   ⚠️  Redirect to: {response.headers.get('location')} (likely login required)")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("FILTER TESTING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    print("⚠️  Note: Make sure the Flask app is running on localhost:5002")
    print("   You may need to login first to access this page\n")
    test_filters()