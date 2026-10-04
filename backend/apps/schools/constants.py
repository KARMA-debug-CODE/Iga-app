"""Rwanda's 30 districts, grouped by province (Kigali City and the four provinces)."""

PROVINCES = {
    "Kigali City": ["Gasabo", "Kicukiro", "Nyarugenge"],
    "Northern": ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"],
    "Southern": ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango"],
    "Eastern": ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana"],
    "Western": ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro"],
}
DISTRICTS = sorted(d for districts in PROVINCES.values() for d in districts)
DISTRICT_CHOICES = [(d, d) for d in DISTRICTS]
PROVINCE_OF = {d: province for province, districts in PROVINCES.items() for d in districts}
