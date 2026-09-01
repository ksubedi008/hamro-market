import urllib.request, json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    p = json.loads(urllib.request.urlopen('https://raw.githubusercontent.com/abinrimal/nepal-administrative-divisions-json/main/provinces.json', context=ctx).read())
    d = json.loads(urllib.request.urlopen('https://raw.githubusercontent.com/abinrimal/nepal-administrative-divisions-json/main/districts.json', context=ctx).read())
    m = json.loads(urllib.request.urlopen('https://raw.githubusercontent.com/abinrimal/nepal-administrative-divisions-json/main/local_levels.json', context=ctx).read())
    
    result = {}
    for prov in p:
        prov_name = prov['name_en']
        result[prov_name] = {'districts': {}}
        for dist in d:
            if dist['province_code'] == prov['code']:
                dist_name = dist['name_en']
                result[prov_name]['districts'][dist_name] = {'municipalities': []}
                for mun in m:
                    if mun['district_code'] == dist['code']:
                        result[prov_name]['districts'][dist_name]['municipalities'].append(mun['name_en'] + ' ' + mun['type_en'])
    
    with open('c:/Kamal/BN/static/js/locations.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("SUCCESS")
except Exception as e:
    print("ERROR:", e)
